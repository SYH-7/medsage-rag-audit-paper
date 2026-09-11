"""E5: latent (configuration-gated) leakage -> composite_audit > runtime_taint.

runtime_taint only sees EXECUTED source->sink flows. A private handle whose read
sits behind a configuration flag that is OFF in the audited run is invisible to
runtime taint yet still present in the deployable adapter code. ast_static_dataflow
(and therefore full_audit/composite) sees it because static analysis does not need
the branch to run. This gives a measured case where the composite audit adds value
over runtime taint alone. Same adapter code with the flag ON is caught by runtime
too, showing the mechanism is real and the only difference is execution.

New case dirs under benchmark_work_v5_review_latent. Frozen detectors/code/case
dirs untouched. Outputs to paper_package_dakd_v5_1/17_review_metrics/.
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

WORK = ROOT / "benchmark_work_v5_review_latent"
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

# The read happens ONLY under a config flag. config['latent_gold'] is absent/false
# in dormant runs and true in active runs -> identical code, different execution.
LATENT_BODY = [
    "def selection_entry(public_candidate, features, config, store):",
    "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
    "    if config.get('latent_gold', False):",
    "        ref = features.get('lat_handle')",
    "        val = private_store.read_evidence_label(ref, store)",
    "        score += selector.score_candidate(val)",
    "    return score",
]
CLEAN_BODY = [
    "def selection_entry(public_candidate, features, config, store):",
    "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
    "    if config.get('latent_gold', False):",
    "        ref = features.get('lat_note', None)",
    "        score += 0.01 if ref else 0.0",
    "    return score",
]


def h(prefix, text):
    return f"h_{prefix}_{hashlib.md5(str(text).encode('utf-8')).hexdigest()[:12]}"


def load_qids(pool_path: Path, max_qids: int = 6, start: int = 0) -> list[tuple[str, list[dict]]]:
    by_q: dict[str, list[dict]] = {}
    with pool_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            by_q.setdefault(str(rec.get("qid", "")), []).append(rec)
    keys = list(by_q.keys())[start:start + max_qids]
    return [(q, by_q[q]) for q in keys]


def build_case(case_id: str, kind: str, gate: bool, body_lines: list[str], qids) -> Path:
    case_dir = WORK / case_id
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "detector_input").mkdir(parents=True)
    (case_dir / "private_truth").mkdir(parents=True)
    crows, qrows, feature_matrix, runtime_store = [], [], {}, {}
    for qi, (q, rows) in enumerate(qids):
        qh = h("q", q)
        qrows.append({"qid_hash": qh, "question_length": 0, "public_state_hints": []})
        sel = rows[:8]
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
            handle = f"lat_{case_id}_{qi}"
            runtime_store[handle] = docs
            feature_matrix.setdefault(qh, {})["lat_handle"] = handle
    config = {"top_k": 5, "candidate_k": 8, "timeout_ms": 1000, "latent_gold": gate}
    adapter = "\n".join(HEADER + body_lines) + "\n"
    (case_dir / "detector_input" / "adapter.py").write_text(adapter, encoding="utf-8")
    (case_dir / "detector_input" / "public_queries.json").write_text(json.dumps(qrows), encoding="utf-8")
    (case_dir / "detector_input" / "public_candidates.json").write_text(json.dumps(crows), encoding="utf-8")
    (case_dir / "detector_input" / "public_features.json").write_text(json.dumps(feature_matrix), encoding="utf-8")
    (case_dir / "detector_input" / "public_config.json").write_text(json.dumps(config), encoding="utf-8")
    (case_dir / "detector_input" / "runtime_store.json").write_text(json.dumps(runtime_store), encoding="utf-8")
    truth = {
        "case_id": case_id,
        "family": "Leak-Latent" if kind == "leak" else "Clean",
        "pattern_id": "LAT" if kind == "leak" else "Clean",
        "module": "review_latent_gate", "field": "lat_handle" if kind == "leak" else "",
        "source_type": "EvidenceGold" if kind == "leak" else "", "sink": "candidate_scoring",
        "file": "adapter.py", "line": 0, "config_gate": bool(gate),
        "injected_qids": len(qids) if kind == "leak" else 0,
        "injected_candidates": len(crows) if kind == "leak" else 0,
        "test_only": True,
        "note": "read gated by config['latent_gold'] (off=dormant, on=active); static analysis sees the "
                "flow even when dormant, executed-path taint does not.",
    }
    (case_dir / "private_truth" / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_dir


def main() -> None:
    _require_inputs()
    WORK.mkdir(parents=True, exist_ok=True)
    rows = []
    specs = ([f"latent_dormant_{i}" for i in range(1, 4)] +
             [f"latent_active_{i}" for i in range(1, 4)] +
             [f"latent_clean_{i}" for i in range(1, 4)])
    kind_of = {s: ("leak" if "clean" not in s else "clean") for s in specs}
    gate_of = {s: ("active" in s) for s in specs}
    for cid in specs:
        qids = load_qids(POOL, max_qids=6, start=hashlib.md5(cid.encode()).digest()[0] % 60)
        body = CLEAN_BODY if kind_of[cid] == "clean" else LATENT_BODY
        case_dir = build_case(cid, kind_of[cid], gate_of[cid], body, qids)
        for det in DETECTORS:
            find = run_detector(case_dir, det)
            rows.append({"case_id": cid, "kind": kind_of[cid], "gate": gate_of[cid],
                         "detector": det, "detected": bool(find.detected)})
        base, _ = run_selection(case_dir, mask_private=False)
        masked, _ = run_selection(case_dir, mask_private=True)
        changed = sum(1 for q in base if masked.get(q) != base[q])
        rows.append({"case_id": cid, "kind": kind_of[cid], "gate": gate_of[cid],
                     "detector": "invariance_class", "detected": changed > 0})
        print(f"done {cid} gate={gate_of[cid]} kind={kind_of[cid]}", flush=True)

    # key summary rows per group/detector
    summary = []
    for group, label in (("dormant", "latent_dormant_"), ("active", "latent_active_"), ("clean", "latent_clean_")):
        for det in DETECTORS:
            tp = sum(1 for r in rows if r["case_id"].startswith(label) and r["detector"] == det and r["detected"])
            n = sum(1 for r in rows if r["case_id"].startswith(label) and r["detector"] == det)
            summary.append({"group": group, "detector": det, "detected": f"{tp}/{n}"})
    with (OUT / "latent_gate_per_case.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with (OUT / "latent_gate_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
    with (OUT / "latent_gate.json").open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "note": (
            "Dormant = config gate OFF: runtime_taint misses (nothing executed), ast_static_dataflow sees "
            "the flow, full_audit(composite) detects -> composite > runtime. Active = same code, gate ON: "
            "runtime also detects. Clean = gated branch reads only public metadata.")},
            f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY (latent gate) ===")
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
