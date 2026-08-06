from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .contracts import PublicCandidate, PublicQuery
from .private_gold_loader import GoldLoadResult, hash_id
from .taint import record_sink, taint_source


def load_public_pool(root: Path, split: str = "formal_train", max_qids: int = 60) -> tuple[list[PublicQuery], dict[str, list[PublicCandidate]], dict[str, str]]:
    path = root / "data" / "leakage_free" / "candidate_pools" / f"{split}_candidates.jsonl"
    by_qid: dict[str, list[PublicCandidate]] = {}
    qid_map: dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            qid = str(rec["qid"])
            if qid not in by_qid and len(by_qid) >= max_qids:
                continue
            qh = hash_id(qid)
            qid_map[qh] = qid
            by_qid.setdefault(qh, []).append(
                PublicCandidate(
                    qid_hash=qh,
                    doc_id_hash=hash_id(str(rec["doc_id"])),
                    rank=int(rec.get("candidate_rank", len(by_qid.get(qh, [])) + 1)),
                    public_scores={
                        "reranker": float(rec.get("reranker_score", 0.0) or 0.0),
                        "dense": float(rec.get("dense_score", 0.0) or 0.0),
                        "bm25": float(rec.get("bm25_score", 0.0) or 0.0),
                    },
                    metadata={"source": str(rec.get("source", "")), "rank_hint": int(rec.get("candidate_rank", 0) or 0)},
                )
            )
    queries = [PublicQuery(qid_hash=qh, question_length=0, public_state_hints=[]) for qh in by_qid]
    return queries, by_qid, qid_map


def choose_qids(qids: list[str], rate: float, seed: int) -> set[str]:
    n = round(len(qids) * rate)
    if rate > 0:
        n = max(1, n)
    rng = random.Random(seed)
    return set(rng.sample(qids, min(n, len(qids)))) if n else set()


def baseline_select(candidates: dict[str, list[PublicCandidate]], top_k: int = 5) -> dict[str, list[str]]:
    selected = {}
    for qh, rows in candidates.items():
        ranked = sorted(rows, key=lambda c: (c.public_scores.get("reranker", 0.0), -c.rank), reverse=True)
        selected[qh] = [c.doc_id_hash for c in ranked[:top_k]]
    return selected


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def public_records(queries: list[PublicQuery], candidates: dict[str, list[PublicCandidate]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    qrows = [q.__dict__ for q in queries]
    crows = []
    for rows in candidates.values():
        for c in rows:
            crows.append({"qid_hash": c.qid_hash, "doc_id_hash": c.doc_id_hash, "rank": c.rank, "public_scores": c.public_scores, "metadata": c.metadata})
    return qrows, crows


def _human_gold_docs(qid: str, qh: str, rows: list[dict[str, Any]], gold: GoldLoadResult) -> tuple[list[str], list[dict[str, Any]]]:
    if not hasattr(gold, "_evidence_hash_index"):
        setattr(
            gold,
            "_evidence_hash_index",
            {
                (hash_id(g_qid), hash_id(g_doc)): val
                for (g_qid, g_doc), val in gold.evidence_gold.items()
                if int(val.get("relevance", 0)) > 0
            },
        )
    index = getattr(gold, "_evidence_hash_index")
    used = []
    doc_hashes = []
    for r in rows:
        val = index.get((qh, r["doc_id_hash"]))
        if val is not None:
            doc_hashes.append(r["doc_id_hash"])
            used.append({"qid_hash": qh, "doc_id_hash": r["doc_id_hash"], "source_id": f"src_{hash_id(qh + r['doc_id_hash'])[2:]}", "source_type": "EvidenceGold"})
    return doc_hashes, used


def _adapter_lines_v4(pattern: dict[str, str] | None, field: str, hard_clean: bool = False) -> list[str]:
    header = [
        "class private_store:",
        "    @staticmethod",
        "    def read_evidence_label(handle, store):",
        "        return store.get(handle)",
        "class selector:",
        "    @staticmethod",
        "    def score_candidate(value): return len(value or [])",
        "class feature_builder:",
        "    @staticmethod",
        "    def append_feature(vec, value): vec.append(len(value or [])); return vec",
        "class candidate_filter:",
        "    @staticmethod",
        "    def apply(value): return bool(value)",
        "def neutral_wrap(x): return x",
        "def neutral_wrap2(x): return neutral_wrap(x)",
    ]
    body = ["def selection_entry(public_candidate, features, config, store):", "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)"]
    if pattern is None:
        if hard_clean:
            body += [
                "    state_cache = public_candidate.get('metadata', {}).get('state_cache')",
                "    label_encoder = public_candidate.get('metadata', {}).get('label_encoder')",
                "    if state_cache and label_encoder: score += 0.0",
            ]
        return header + body + ["    return score"]
    pid = pattern["pattern_id"]
    if pid == "M1":
        body += [f"    a = public_candidate.get('metadata', {{}}).get('{field}')", "    b = private_store.read_evidence_label(a, store)", "    score += selector.score_candidate(b)"]
    elif pid == "M2":
        body += [f"    z0 = public_candidate.get('metadata', {{}}).get('{field}')", "    z1 = z0", "    z2 = private_store.read_evidence_label(z1, store)", "    score += selector.score_candidate(z2)"]
    elif pid == "M3":
        body += [f"    with open(config.get('cache_file'), 'r', encoding='utf-8') as fh:", "        cache = __import__('json').load(fh)", f"    k = public_candidate.get('metadata', {{}}).get('{field}')", "    score += selector.score_candidate(private_store.read_evidence_label(cache.get(k), store))"]
    elif pid == "M4":
        body += ["    idx = config.get('metadata_field')", "    ref = public_candidate.get('metadata', {}).get(idx)", "    score += selector.score_candidate(private_store.read_evidence_label(ref, store))"]
    elif pid == "F1":
        body += [f"    ref = features.get('{field}')", "    val = private_store.read_evidence_label(ref, store)", "    vec = feature_builder.append_feature([], val)", "    score += sum(vec)"]
    elif pid == "F2":
        body += [f"    ref = features.get('{field}')", "    val = private_store.read_evidence_label(ref, store)", "    feature_builder.append_feature([], val)", "    flag = bool(val)", "    score += int(flag)"]
    elif pid == "F3":
        body += [f"    ref = features.get('{field}')", "    val = private_store.read_evidence_label(ref, store)", "    feature_builder.append_feature([], val)", "    cnt = len(val or [])", "    ratio = cnt / 10", "    score += ratio"]
    elif pid == "F4":
        body += ["    def layer1(x): return neutral_wrap(x)", "    def layer2(y): return private_store.read_evidence_label(layer1(y), store)", f"    score += selector.score_candidate(layer2(features.get('{field}')))"]
    elif pid == "R1":
        body += [f"    pred = features.get('missing_prediction')", "    if pred is None:", f"        score += selector.score_candidate(private_store.read_evidence_label(features.get('{field}'), store))"]
    elif pid == "R2":
        body += ["    try:", "        raise RuntimeError('simulated public failure')", "    except RuntimeError:", f"        score += selector.score_candidate(private_store.read_evidence_label(features.get('{field}'), store))"]
    elif pid == "R3":
        body += [f"    def delayed(ref=features.get('{field}')):", "        return private_store.read_evidence_label(ref, store)", "    score += selector.score_candidate(delayed())"]
    elif pid == "R4":
        body += [f"    gate = private_store.read_evidence_label(features.get('{field}'), store)", "    if candidate_filter.apply(gate):", "        score += 1.0"]
    return header + body + ["    return score"]


def build_case_v4(
    *,
    case_dir: Path,
    root: Path,
    pattern: dict[str, str] | None,
    rate: float,
    seed: int,
    qid_count: int,
    gold: GoldLoadResult,
    hard_clean: bool = False,
    offset: int = 0,
) -> dict[str, Any]:
    queries, candidates, _ = load_public_pool(root, max_qids=qid_count + offset)
    if offset:
        queries = queries[offset:offset + qid_count]
        candidates = {q.qid_hash: candidates[q.qid_hash] for q in queries if q.qid_hash in candidates}
    selected_clean = baseline_select(candidates)
    qrows, crows = public_records(queries, candidates)
    detector_input = case_dir / "detector_input"
    private_truth = case_dir / "private_truth"
    detector_input.mkdir(parents=True, exist_ok=True)
    private_truth.mkdir(parents=True, exist_ok=True)
    config = {"top_k": 5, "weight_public_score": 1.0, "timeout_ms": 1000, "metadata_field": "aux_31"}
    feature_matrix: dict[str, dict[str, Any]] = {}
    private_store: dict[str, list[str]] = {}
    usage_rows: list[dict[str, Any]] = []
    eligible = []
    by_q = {q.qid_hash: [r for r in crows if r["qid_hash"] == q.qid_hash] for q in queries}
    for qh, rows in by_q.items():
        docs, used = _human_gold_docs("", qh, rows, gold)
        if docs:
            eligible.append(qh)
            for u in used:
                private_store[u["source_id"]] = docs
                usage_rows.append(u | {"case_id": case_dir.name})
    injected = choose_qids(eligible, rate, seed) if pattern else set()
    field = pattern["field"] if pattern else ""
    source_paths = []
    injected_candidates = injected_features = fallback_triggers = 0
    excluded = [q for q in by_q if q not in eligible and pattern]
    cache_map = {}
    for qh in injected:
        handles = [u["source_id"] for u in usage_rows if u["qid_hash"] == qh]
        if not handles:
            continue
        handle = handles[0]
        rows = by_q[qh]
        if pattern["family"] == "Leak-M":
            for r in rows:
                if r["doc_id_hash"] in private_store[handle]:
                    r["metadata"][field] = handle
                    injected_candidates += 1
                    if pattern["pattern_id"] == "M3":
                        cache_map[handle] = handle
        elif pattern["family"] == "Leak-F":
            feature_matrix.setdefault(qh, {})[field] = handle
            injected_features += 1
            injected_candidates += len(rows)
        else:
            feature_matrix.setdefault(qh, {})[field] = handle
            fallback_triggers += 1
            injected_candidates += len(rows)
        source_paths.append({"source_type": "EvidenceGold", "transform_chain": ["human_annotation", pattern["pattern_id"]], "sink": pattern["sink"], "field": field})
    if hard_clean:
        for i, r in enumerate(crows):
            r["metadata"].update({"state_cache": f"public_{i}", "label_encoder": "public", "backup_ranker": "public", "support_feature_public": i % 3})
    if pattern and pattern["pattern_id"] == "M3":
        cache_file = detector_input / "neutral_cache.json"
        write_json(cache_file, cache_map)
        config["cache_file"] = "neutral_cache.json"
    adapter = detector_input / "adapter.py"
    adapter.write_text("\n".join(_adapter_lines_v4(pattern, field, hard_clean=hard_clean)) + "\n", encoding="utf-8")
    write_json(detector_input / "public_queries.json", qrows)
    write_json(detector_input / "public_candidates.json", crows)
    write_json(detector_input / "public_features.json", feature_matrix)
    write_json(detector_input / "public_config.json", config)
    write_json(detector_input / "runtime_store.json", private_store)
    truth = {
        "case_id": case_dir.name,
        "family": pattern["family"] if pattern else "Clean",
        "pattern_id": pattern["pattern_id"] if pattern else "Clean",
        "module": pattern["module"] if pattern else "",
        "field": field,
        "source_type": "EvidenceGold" if pattern else "",
        "sink": pattern["sink"] if pattern else "",
        "file": "adapter.py" if pattern else "",
        "line": 0,
        "rate": rate,
        "seed": seed,
        "injected_qids": len(injected),
        "injected_candidates": injected_candidates,
        "injected_features": injected_features,
        "fallback_triggers": fallback_triggers,
        "source_sink_paths": source_paths,
        "baseline_selected": selected_clean,
        "hard_clean": hard_clean,
        "excluded_no_gold_qids": len(excluded),
        "gold_usage": usage_rows,
        "benchmark_gold_status": "REAL_HUMAN_GOLD_BENCHMARK" if pattern else "",
    }
    if pattern:
        for idx, line in enumerate(adapter.read_text(encoding="utf-8").splitlines(), 1):
            if any(api in line for api in ["selector.score_candidate", "feature_builder.append_feature", "candidate_filter.apply"]):
                truth["line"] = idx
                break
    write_json(private_truth / "truth.json", truth)
    return truth
