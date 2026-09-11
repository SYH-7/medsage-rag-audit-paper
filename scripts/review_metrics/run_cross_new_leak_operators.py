"""Path B: same new unseen-mechanism operators over real TCM BM25 candidates.

Sources REAL public candidates/features/config from an existing frozen cross
case dir (TCM BM25 retrieval outputs; read-only), and injects TEST_ONLY
private handles through the N1-N4 mechanisms (embedding-derived, serialization
round-trip, hot config-swap, 3-hop proxy). Case dirs are new under
benchmark_work_cross_review_newops. Frozen detectors only; no frozen file
modified. Outputs to paper_package_dakd_v5_1/17_review_metrics/.
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

SRC_CASE = Path(os.environ.get("MEDSAGE_CROSS_CASES", str(ROOT / "benchmark_work_cross")))
WORK = ROOT / "benchmark_work_cross_review_newops"
PKG = ROOT / "paper_package_dakd_v5_1"
OUT = Path(os.environ.get("REVIEW_METRICS_OUT", str(PKG / "17_review_metrics")))
OUT.mkdir(parents=True, exist_ok=True)
_REQUIRED_INPUTS = [SRC_CASE]
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
BODIES = {
    "N1": [
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('bm25', 0.0)",
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
        "    score = public_candidate.get('public_scores', {}).get('bm25', 0.0)",
        "    ref = features.get('n2_roundtrip')",
        "    back = _json.loads(_json.dumps({'k': ref}))['k']",
        "    val = private_store.read_evidence_label(back, store)",
        "    score += selector.score_candidate(val)",
        "    return score",
    ],
    "N3": [
        "def selection_entry(public_candidate, features, config, store):",
        "    score = public_candidate.get('public_scores', {}).get('bm25', 0.0)",
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
        "    score = public_candidate.get('public_scores', {}).get('bm25', 0.0)",
        "    ref = features.get('n4_proxy')",
        "    val = private_store.read_evidence_label({'deep': [{'inner': ref}]}['deep'][0]['inner'], store)",
        "    score += selector.score_candidate(val)",
        "    return score",
    ],
}
CLEAN_ADAPTER = HEADER + [
    "def selection_entry(public_candidate, features, config, store):",
    "    score = public_candidate.get('public_scores', {}).get('bm25', 0.0)",
    "    md = public_candidate.get('metadata', {}) or {}",
    "    score += 0.01 * (1 if md.get('gold_flag') == 'public' else 0)",
    "    return score",
]


def h(prefix, text):
    return f"h_{prefix}_{hashlib.md5(str(text).encode('utf-8')).hexdigest()[:12]}"


def source_candidates(src_dir: Path) -> list[dict]:
    """Take real candidate rows from an existing frozen cross case dir."""
    inp = src_dir / "detector_input"
    cands = json.loads((inp / "public_candidates.json").read_text(encoding="utf-8"))
    if isinstance(cands, dict):
        cands = [c for rows in cands.values() for c in rows]
    feats = json.loads((inp / "public_features.json").read_text(encoding="utf-8"))
    cfg = json.loads((inp / "public_config.json").read_text(encoding="utf-8"))
    return cands, feats, cfg


def build_case(case_id: str, kind: str, mechanism: str | None, cands, feats) -> Path:
    case_dir = WORK / case_id
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "detector_input").mkdir(parents=True)
    (case_dir / "private_truth").mkdir(parents=True)
    qids = sorted({c["qid_hash"] for c in cands})[:6]
    qids = qids[: max(2, len(qids))]
    # deep-copy real rows so source objects are never mutated across case builds
    crows = [json.loads(json.dumps(c)) for c in cands if c["qid_hash"] in qids]
    qrows = [{"qid_hash": q} for q in qids]
    feature_matrix = {q: dict(feats.get(q, {})) for q in qids}
    runtime_store = {}
    for qi, qh in enumerate(qids):
        docs = [c["doc_id_hash"] for c in crows if c["qid_hash"] == qh][:10]
        if kind == "leak":
            handle = f"test_{case_id}_{qi}"
            runtime_store[handle] = docs
            key = {"N1": "n1_embedding", "N2": "n2_roundtrip", "N4": "n4_proxy"}.get(mechanism)
            if key:
                feature_matrix.setdefault(qh, {})[key] = handle
            else:  # N3: hot config-swap fallback (configured public field absent from metadata)
                feature_matrix.setdefault(qh, {})["n3_fallback"] = handle
    config = {"top_k": 5, "candidate_k": 10, "metadata_field": "aux_31", "n3_field": "aux_31"}
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
        "module": "tcm_cross_review_newop", "field": mechanism if kind == "leak" else "",
        "source_type": "TEST_ONLY_PRIVATE_SOURCE" if kind == "leak" else "",
        "sink": "candidate_scoring", "file": "adapter.py", "line": 0,
        "injected_qids": len(qids) if kind == "leak" else 0,
        "injected_candidates": len(crows) if kind == "leak" else 0,
        "hard_clean": kind == "clean", "test_only": True,
        "real_bm25_candidates_source": str(SRC_CASE),
    }
    (case_dir / "private_truth" / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_dir


def main() -> None:
    _require_inputs()
    WORK.mkdir(parents=True, exist_ok=True)
    # pick source candidate dirs from frozen cross cases (real TCM BM25 outputs)
    src_dirs = sorted([d for d in SRC_CASE.iterdir() if (d / "detector_input" / "public_candidates.json").exists()])
    if not src_dirs:
        print("no cross source dirs found"); return
    cands, feats, _ = source_candidates(src_dirs[0])
    print('source case:', src_dirs[0].name, 'cands:', len(cands), 'qids:', len({c['qid_hash'] for c in cands}))

    rows = []
    specs = []
    for mech in ("N1", "N2", "N3", "N4"):
        for seed in (1, 2, 3):
            specs.append((f"x{mech}_{seed}", "leak", mech))
    for i in range(4):
        specs.append((f"xclean_{i + 1}", "clean", None))

    for case_id, kind, mech in specs:
        case_dir = build_case(case_id, kind, mech, cands, feats)
        for det in DETECTORS:
            find = run_detector(case_dir, det)
            rows.append({"case_id": case_id, "kind": kind, "pattern_id": mech or "Clean",
                         "detector": det, "detected": bool(find.detected),
                         "evidence": str(getattr(find, "evidence", ""))[:60]})
        if kind == "leak":
            base, _ = run_selection(case_dir, mask_private=False)
            masked, _ = run_selection(case_dir, mask_private=True)
            changed = sum(1 for q in base if masked.get(q) != base[q])
            rows.append({"case_id": case_id, "kind": "class", "pattern_id": mech,
                         "detector": "invariance_class", "detected": changed > 0,
                         "evidence": f"changed_qids={changed}"})
        print(f"done {case_id} [{mech or 'Clean'}]", flush=True)

    leaks = [r for r in rows if r["kind"] == "leak" and r["detector"] != "invariance_class"]
    cleans = [r for r in rows if r["kind"] == "clean"]
    summary = []
    for det in DETECTORS:
        tp = sum(1 for r in leaks if r["detector"] == det and r["detected"])
        fp = sum(1 for r in cleans if r["detector"] == det and r["detected"])
        npos = len(leaks) and sum(1 for r in leaks if r["detector"] == det)
        nneg = sum(1 for r in cleans if r["detector"] == det)
        summary.append({"detector": det, "tp": tp, "fp": fp, "positives": npos, "negatives": nneg,
                        "recall": round(tp / npos, 4) if npos else 0.0,
                        "specificity": round(1.0 - fp / nneg, 4) if nneg else 1.0})
    cls = [r for r in rows if r["kind"] == "class"]
    nbeh = sum(1 for r in cls if r["detected"])
    summary.append({"detector": "leak_class(tp=behavioral,fp=access)",
                    "tp": nbeh, "fp": len(cls) - nbeh, "positives": len(cls),
                    "negatives": 0, "recall": "", "specificity": ""})

    with (OUT / "new_operators_cross_per_case.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with (OUT / "new_operators_cross_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
    with (OUT / "new_operators_cross.json").open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "source_case": f"benchmark_work_cross/{src_dirs[0].name}", "note": (
            "N1-N4 new unseen mechanisms over REAL TCM BM25 candidate rows (frozen cross case source, "
            "read-only) with TEST_ONLY_PRIVATE_SOURCE handles; frozen detectors only.")},
            f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY (new operators, TCM cross) ===")
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
