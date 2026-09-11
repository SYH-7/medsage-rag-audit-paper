"""E4: retrieval-method independence of the frozen detector suite.

Reruns the four unseen N-operators (plus ordinary clean controls) on candidate
sub-pools that are restricted to ONE real retrieval method (dense-only or
BM25-only, ranked by that method's real rank in the formal_train pool). Frozen
detector code/policies and frozen case dirs are untouched; new case dirs under
benchmark_work_v5_review_method. Outputs go to
paper_package_dakd_v5_1/17_review_metrics/.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from benchmark_v3.isolated_runner import run_detector, run_selection  # noqa: E402

WORK = ROOT / "benchmark_work_v5_review_method"
PKG = ROOT / "paper_package_dakd_v5_1"
OUT = Path(os.environ.get("REVIEW_METRICS_OUT", str(PKG / "17_review_metrics")))
POOL = Path(os.environ.get(
    "MEDSAGE_FORMAL_TRAIN_POOL",
    str(ROOT / "data" / "leakage_free" / "candidate_pools" / "formal_train_candidates.jsonl"),
))
OUT.mkdir(parents=True, exist_ok=True)
_REQUIRED_INPUTS = [POOL]
DETECTORS = ["keyword_static_baseline", "ast_static_dataflow", "schema_guard",
             "runtime_taint", "invariance", "full_audit"]

HEADER = [
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
N_BODIES = {
    "N1": [
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
        "    ref = features.get('n1_embedding')",
        "    raw = private_store.read_evidence_label(ref, store)",
        "    if raw is not None:",
        "        encoded = [raw] + [0.0] * 4",
        "    else:",
        "        encoded = [0.0] * 5",
        "    vec = feature_builder.append_feature([], encoded)",
        "    score += sum(vec)",
        "    return score",
    ],
    "N2": [
        "import json as _json",
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
        "    ref = features.get('n2_roundtrip')",
        "    blob = _json.dumps({'k': ref})",
        "    back = _json.loads(blob)['k']",
        "    val = private_store.read_evidence_label(back, store)",
        "    score += selector.score_candidate(val)",
        "    return score",
    ],
    "N3": [
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
        "    cfg = dict(config or {})",
        "    idx = cfg.get('n3_field', 'aux_31')",
        "    ref = public_candidate.get('metadata', {}).get(idx)",
        "    if ref is None:",
        "        ref = features.get('n3_fallback')",
        "    val = private_store.read_evidence_label(ref, store)",
        "    score += selector.score_candidate(val)",
        "    return score",
    ],
    "N4": [
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
        "    ref = features.get('n4_proxy')",
        "    hop1 = {'inner': ref}",
        "    hop2 = [hop1]",
        "    hop3 = {'deep': hop2}",
        "    val = private_store.read_evidence_label(hop3['deep'][0]['inner'], store)",
        "    score += selector.score_candidate(val)",
        "    return score",
    ],
}
CLEAN_ADAPTER = HEADER + [
    "def selection_entry(public_candidate, features, config, store):",
    "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
    "    return score",
]


def h(prefix, text):
    return f"h_{prefix}_{hashlib.md5(str(text).encode('utf-8')).hexdigest()[:12]}"


def load_pool(pool_path: Path) -> dict[str, list[dict]]:
    by_q: dict[str, list[dict]] = {}
    with pool_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            by_q.setdefault(str(rec.get("qid", "")), []).append(rec)
    return by_q


def method_rows(by_q: dict, method: str, max_q: int = 6, per_q: int = 8) -> list[tuple[str, list[dict]]]:
    """Keep rows that this method actually retrieved (rank >= 1), sorted by it."""
    out = []
    for q, rows in by_q.items():
        ranked = [r for r in rows if r.get(f"{method}_rank") is not None and int(r[f"{method}_rank"]) >= 1]
        ranked.sort(key=lambda r: int(r.get(f"{method}_rank", 10**6)))
        if len(ranked) >= 3:
            out.append((q, ranked[:per_q]))
        if len(out) >= max_q:
            break
    return out


def build_case(case_id: str, kind: str, mechanism: str | None, groups: list[tuple[str, list[dict]]], method: str) -> Path:
    case_dir = WORK / case_id
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "detector_input").mkdir(parents=True)
    (case_dir / "private_truth").mkdir(parents=True)
    crows, qrows, feature_matrix, runtime_store = [], [], {}, {}
    for qi, (q, rows) in enumerate(groups):
        qh = h("q", f"{method}-{q}")
        qrows.append({"qid_hash": qh, "question_length": 0, "public_state_hints": []})
        docs = [h("d", f"{method}-{q}-{r.get('doc_id','')}-{r.get('candidate_rank','')}") for r in rows]
        for r, d in zip(rows, docs):
            crows.append({
                "qid_hash": qh, "doc_id_hash": d,
                "rank": int(r.get("candidate_rank", 0) or 0),
                "public_scores": {"reranker": float(r.get("reranker_score", 0.0) or 0.0),
                                  "bm25": float(r.get("bm25_score", 0.0) or 0.0),
                                  "dense": float(r.get("dense_score", 0.0) or 0.0)},
                "metadata": {"source": str(r.get("source", "")),
                             "rank_hint": int(r.get("candidate_rank", 0) or 0)},
            })
        if kind == "leak":
            handle = f"m_{case_id}_{qi}"
            runtime_store[handle] = docs
            if mechanism in ("N1", "N2", "N4"):
                feature_matrix.setdefault(qh, {})[{"N1": "n1_embedding", "N2": "n2_roundtrip", "N4": "n4_proxy"}[mechanism]] = handle
            else:
                feature_matrix.setdefault(qh, {})["n3_fallback"] = handle
    config = {"top_k": 5, "candidate_k": len(groups[0][1]) if groups else 8,
              "metadata_field": "aux_31", "n3_field": "aux_31", "timeout_ms": 1000}
    adapter = "\n".join((HEADER + N_BODIES[mechanism]) if kind == "leak" else CLEAN_ADAPTER) + "\n"
    (case_dir / "detector_input" / "adapter.py").write_text(adapter, encoding="utf-8")
    (case_dir / "detector_input" / "public_queries.json").write_text(json.dumps(qrows), encoding="utf-8")
    (case_dir / "detector_input" / "public_candidates.json").write_text(json.dumps(crows), encoding="utf-8")
    (case_dir / "detector_input" / "public_features.json").write_text(json.dumps(feature_matrix), encoding="utf-8")
    (case_dir / "detector_input" / "public_config.json").write_text(json.dumps(config), encoding="utf-8")
    (case_dir / "detector_input" / "runtime_store.json").write_text(json.dumps(runtime_store), encoding="utf-8")
    truth = {
        "case_id": case_id, "family": "Leak-N" if kind == "leak" else "Clean",
        "pattern_id": mechanism if kind == "leak" else "Clean",
        "module": f"retrieval_independence_{method}", "field": mechanism if kind == "leak" else "",
        "source_type": "EvidenceGold" if kind == "leak" else "", "sink": "candidate_scoring",
        "file": "adapter.py", "line": 0, "retrieval_method": method,
        "injected_qids": len(groups) if kind == "leak" else 0,
        "injected_candidates": len(crows) if kind == "leak" else 0,
        "test_only": True,
    }
    (case_dir / "private_truth" / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_dir


def main() -> None:
    _require_inputs()
    WORK.mkdir(parents=True, exist_ok=True)
    by_q = load_pool(POOL)
    rows = []
    for method in ("dense", "bm25"):
        groups = method_rows(by_q, method)
        print(f"[{method}] groups={len(groups)}", flush=True)
        for mech in ("N1", "N2", "N3", "N4"):
            for seed in (1, 2):
                cid = f"{method}_N{mech[1]}_{seed}"
                case_dir = build_case(cid, "leak", mech, groups, method)
                for det in DETECTORS:
                    find = run_detector(case_dir, det)
                    rows.append({"case_id": cid, "kind": "leak", "pattern_id": mech, "method": method,
                                 "detector": det, "detected": bool(find.detected)})
                base, _ = run_selection(case_dir, mask_private=False)
                masked, _ = run_selection(case_dir, mask_private=True)
                changed = sum(1 for q in base if masked.get(q) != base[q])
                rows.append({"case_id": cid, "kind": "class", "pattern_id": mech, "method": method,
                             "detector": "invariance_class", "detected": changed > 0})
                print(f"  done {cid}", flush=True)
        for i in range(2):
            cid = f"{method}_clean_{i + 1}"
            ccase_dir = build_case(cid, "clean", None, groups, method)
            for det in DETECTORS:
                find = run_detector(ccase_dir, det)
                rows.append({"case_id": cid, "kind": "clean", "pattern_id": "Clean", "method": method,
                             "detector": det, "detected": bool(find.detected)})
            print(f"  done {cid}", flush=True)

    summary = []
    for method in ("dense", "bm25"):
        for det in DETECTORS:
            tp = sum(1 for r in rows if r["method"] == method and r["kind"] == "leak" and r["detector"] == det and r["detected"])
            fp = sum(1 for r in rows if r["method"] == method and r["kind"] == "clean" and r["detector"] == det and r["detected"])
            npos = sum(1 for r in rows if r["method"] == method and r["kind"] == "leak" and r["detector"] == det)
            nneg = sum(1 for r in rows if r["method"] == method and r["kind"] == "clean" and r["detector"] == det)
            summary.append({"method": method, "detector": det, "tp": tp, "fp": fp,
                            "positives": npos, "negatives": nneg,
                            "recall": round(tp / npos, 4) if npos else 0.0,
                            "specificity": round(1.0 - fp / nneg, 4) if nneg else 1.0})
    with (OUT / "retrieval_independence_per_case.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with (OUT / "retrieval_independence_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
    with (OUT / "retrieval_independence.json").open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "note": (
            "N1-N4 unseen operators on dense-only and BM25-only candidate sub-pools (real per-method "
            "ranks from formal_train); frozen detectors only; case dirs in benchmark_work_v5_review_method.")},
            f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY (retrieval independence) ===")
    for s in summary:
        print(s)


def _require_inputs() -> None:
    """Soft-fail when the local/private inputs of the audited projects are absent.

    This repository ships the frozen outputs; re-executing a script additionally
    needs the local original projects (see scripts/review_metrics/README.md).
    """
    missing = [str(p) for p in _REQUIRED_INPUTS if not Path(p).exists()]
    if missing:
        print("REQUIRES_LOCAL_ORIGINAL_PROJECT: missing local input(s):")
        for m in missing:
            print("  -", m)
        print("Set the documented environment variables (scripts/review_metrics/README.md).")
        raise SystemExit(0)


if __name__ == "__main__":
    main()
