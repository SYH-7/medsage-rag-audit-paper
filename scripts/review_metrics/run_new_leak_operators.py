"""Path A: new 'unseen mechanism' leakage operators on the main benchmark.

Adds 4 new operators NOT present in the frozen 12 (N1 embedding-derived,
N2 cross-module serialization round-trip, N3 hot config-swap fallback,
N4 >=3-hop derived proxy), x3 cases each = 12 positives, plus 6 clean
controls. Case dirs are generated additively from the real formal_train
candidate pool into benchmark_work_v5_review_newops. FROZEN detector code,
frozen policies, and frozen case dirs/results are untouched. Outputs go to
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

WORK = ROOT / "benchmark_work_v5_review_newops"
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

# Each mechanism emits code that reads the private handle (tainted) through a
# DIFFERENT transform route and finally feeds selector.score_candidate /
# feature_builder so the frozen instrumentation records the sink.
BODIES = {
    "N1": [
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
        "    ref = features.get('n1_embedding')",
        "    raw = private_store.read_evidence_label(ref, store)          # source read (tainted evidence list)",
        "    if raw is not None:                                          # project evidence into embedding slot",
        "        encoded = [raw] + [0.0] * 4                              # nested taint survives; no value math",
        "    else:",
        "        encoded = [0.0] * 5",
        "    vec = feature_builder.append_feature([], encoded)            # feature sink receives tainted vector",
        "    score += sum(vec)",
        "    return score",
    ],
    "N2": [
        "import json as _json",
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
        "    ref = features.get('n2_roundtrip')",
        "    blob = _json.dumps({'k': ref})                               # serialize",
        "    back = _json.loads(blob)['k']                                # deserialize",
        "    val = private_store.read_evidence_label(back, store)         # source read after round trip",
        "    score += selector.score_candidate(val)                       # scoring sink",
        "    return score",
    ],
    "N3": [
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
        "    cfg = dict(config or {})                                     # hot config copy",
        "    idx = cfg.get('n3_field', 'aux_31')",
        "    ref = public_candidate.get('metadata', {}).get(idx)",
        "    if ref is None:                                              # runtime reload path",
        "        ref = features.get('n3_fallback')",
        "    val = private_store.read_evidence_label(ref, store)          # source read (fallback)",
        "    score += selector.score_candidate(val)                       # scoring sink",
        "    return score",
    ],
    "N4": [
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
        "    ref = features.get('n4_proxy')",
        "    hop1 = {'inner': ref}                                        # 3-hop nesting",
        "    hop2 = [hop1]",
        "    hop3 = {'deep': hop2}",
        "    val = private_store.read_evidence_label(hop3['deep'][0]['inner'], store)",
        "    score += selector.score_candidate(val)                       # scoring sink",
        "    return score",
    ],
}

CLEAN_ADAPTER = HEADER + [
    "def selection_entry(public_candidate, features, config, store):",
    "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
    "    md = public_candidate.get('metadata', {}) or {}",
    "    score += 0.01 * (1 if md.get('gold_flag') == 'public' else 0)",
    "    return score",
]


def h(prefix, text):
    return f"h_{prefix}_{hashlib.md5(str(text).encode('utf-8')).hexdigest()[:12]}"


def load_qids(pool_path: Path, max_qids: int = 8, start: int = 0) -> list[dict]:
    rows_by_q = {}
    with pool_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            q = str(rec.get("qid", ""))
            rows_by_q.setdefault(q, []).append(rec)
    qids = list(rows_by_q.keys())[start:start + max_qids]
    return [(q, rows_by_q[q]) for q in qids]


def build_case(case_id: str, kind: str, mechanism: str | None) -> Path:
    case_dir = WORK / case_id
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "detector_input").mkdir(parents=True)
    (case_dir / "private_truth").mkdir(parents=True)

    qids = load_qids(POOL, max_qids=6, start=hashlib.md5(case_id.encode()).digest()[0] % 50)
    crows, qrows = [], []
    feature_matrix = {}
    runtime_store = {}
    n_qids = max(2, len(qids))
    per_q = 8
    for qi, (q, rows) in enumerate(qids[:n_qids]):
        qh = h("q", q)
        qrows.append({"qid_hash": qh, "question_length": 0, "public_state_hints": []})
        sel = rows[:per_q]
        docs = [h("d", f"{q}-{r.get('doc_id','')}-{r.get('candidate_rank','')}") for r in sel]
        for r, d in zip(sel, docs):
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
            handle = f"src_{case_id}_{qi}"
            runtime_store[handle] = docs
            if mechanism in ("N1", "N2", "N4"):
                feature_matrix.setdefault(qh, {})[{  # mapping per mechanism
                    "N1": "n1_embedding", "N2": "n2_roundtrip", "N4": "n4_proxy"}[mechanism]] = handle
            else:  # N3: hot config-swap fallback.
                # The configured public field ('aux_31' via config n3_field) is deliberately
                # ABSENT from candidate metadata, so the runtime fallback route (feature
                # n3_fallback, populated from the private cache) fires. Distinct from frozen
                # M4, which finds the handle directly in candidate metadata.
                feature_matrix.setdefault(qh, {})["n3_fallback"] = handle

    config = {"top_k": 5, "candidate_k": per_q, "metadata_field": "aux_31",
              "n3_field": "aux_31", "timeout_ms": 1000}
    adapter_code = "\n".join((HEADER + BODIES[mechanism]) if kind == "leak" else CLEAN_ADAPTER) + "\n"
    (case_dir / "detector_input" / "adapter.py").write_text(adapter_code, encoding="utf-8")
    (case_dir / "detector_input" / "public_queries.json").write_text(json.dumps(qrows), encoding="utf-8")
    (case_dir / "detector_input" / "public_candidates.json").write_text(json.dumps(crows), encoding="utf-8")
    (case_dir / "detector_input" / "public_features.json").write_text(json.dumps(feature_matrix), encoding="utf-8")
    (case_dir / "detector_input" / "public_config.json").write_text(json.dumps(config), encoding="utf-8")
    (case_dir / "detector_input" / "runtime_store.json").write_text(json.dumps(runtime_store), encoding="utf-8")
    truth = {
        "case_id": case_id,
        "family": "Leak-N" if kind == "leak" else "Clean",
        "pattern_id": mechanism if kind == "leak" else "Clean",
        "module": "review_new_operator", "field": mechanism if kind == "leak" else "",
        "source_type": "EvidenceGold" if kind == "leak" else "",
        "sink": "candidate_scoring", "file": "adapter.py", "line": 0,
        "injected_qids": len(qids[:n_qids]) if kind == "leak" else 0,
        "injected_candidates": len(crows) if kind == "leak" else 0,
        "injected_features": 0, "fallback_triggers": 0,
        "source_sink_paths": [] if kind == "clean" else [{"source_type": "EvidenceGold",
                                                           "transform_chain": [mechanism], "sink": "candidate_scoring", "field": mechanism}],
        "hard_clean": kind == "clean", "clean_type": "ordinary" if kind == "clean" else "",
        "test_only": True,
    }
    (case_dir / "private_truth" / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_dir


def main() -> None:
    _require_inputs()
    WORK.mkdir(parents=True, exist_ok=True)
    rows = []
    specs = []
    for mech in ("N1", "N2", "N3", "N4"):
        for seed in (1, 2, 3):
            specs.append((f"{mech}_{seed}", "leak", mech))
    for i in range(6):
        specs.append((f"clean_{i + 1}", "clean", None))

    for case_id, kind, mech in specs:
        case_dir = build_case(case_id, kind, mech)
        # frozen detector results
        for det in DETECTORS:
            find = run_detector(case_dir, det)
            rows.append({"case_id": case_id, "kind": kind, "pattern_id": mech or "Clean",
                         "detector": det, "detected": bool(find.detected),
                         "evidence": str(getattr(find, "evidence", ""))[:60]})
        # invariance class (masked vs unmasked) for leak cases
        if kind == "leak":
            base, _ = run_selection(case_dir, mask_private=False)
            masked, _ = run_selection(case_dir, mask_private=True)
            changed = sum(1 for q in base if masked.get(q) != base[q])
            rows.append({"case_id": case_id, "kind": "class", "pattern_id": mech,
                         "detector": "invariance_class", "detected": changed > 0,
                         "evidence": f"changed_qids={changed}"})
        print(f"done {case_id} [{mech or 'Clean'}]", flush=True)

    # per-detector summary over the 12 leak + 6 clean
    leaks = [r for r in rows if r["kind"] == "leak" and r["detector"] != "invariance_class"]
    cleans = [r for r in rows if r["kind"] == "clean"]
    summary = []
    for det in DETECTORS:
        tp = sum(1 for r in leaks if r["detector"] == det and r["detected"])
        fp = sum(1 for r in cleans if r["detector"] == det and r["detected"])
        npos = sum(1 for r in leaks if r["detector"] == det)
        nneg = sum(1 for r in cleans if r["detector"] == det)
        summary.append({"detector": det, "tp": tp, "fp": fp, "positives": npos, "negatives": nneg,
                        "recall": tp / npos if npos else 0.0,
                        "specificity": 1.0 - fp / nneg if nneg else 1.0})
    classes = [r for r in rows if r["kind"] == "class"]
    nbeh = sum(1 for r in classes if r["detected"])
    summary.append({"detector": "leak_class(tp=behavioral,fp=access)",
                    "tp": nbeh, "fp": len(classes) - nbeh, "positives": len(classes),
                    "negatives": 0, "recall": "", "specificity": ""})

    with (OUT / "new_operators_main_per_case.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with (OUT / "new_operators_main_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)
    with (OUT / "new_operators_main.json").open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "note": (
            "4 new unseen-mechanism operators (N1 embedding-derived, N2 serialization round-trip, "
            "N3 hot config-swap fallback, N4 3-hop proxy), x3 = 12 positives + 6 clean; case dirs "
            "built additively from the real formal_train pool; frozen detectors only.")},
            f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY (new operators, main) ===")
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
