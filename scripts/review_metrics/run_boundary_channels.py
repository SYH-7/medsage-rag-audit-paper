"""E6: boundary-channel probes - out-of-band smuggling measured honestly.

runtime_taint tags values ONLY when they leave the store through the instrumented
private_store.read_evidence_label surface. If private payload is smuggled through
an out-of-band channel (environment variable, side file/cache read with raw JSON
I/O), no detector that relies on the instrumented read surface can see it. These
probes MEASURE that boundary instead of pretending it does not exist: they are
constructed so that the private doc list reaches a deployment sink, and we report
exactly which components fire (expected: none of runtime/ast/schema/invariance/
composite; keyword only if forbidden words appear in the smuggled text).

New case dirs under benchmark_work_v5_review_boundary. Outputs to
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

WORK = ROOT / "benchmark_work_v5_review_boundary"
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

# NOTE: intentionally NO private_store/selector/feature_builder class names in the
# body (so keyword_static_baseline has no forbidden vocabulary to latch onto) --
# we still call module-level hooks that run_selection instruments at runtime.
HEADER_MIN = []  # no class private_store -> nothing to instrument; adapter self-contained

ENV_BODY = [
    "import json as _json",
    "import os as _os",
    "def selection_entry(public_candidate, features, config, store):",
    "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
    "    hnd = _os.environ.get('REVIEW_PROBE_HANDLE')",
    "    if hnd:",
    "        raw = _json.loads(open(config['store_path'], 'r', encoding='utf-8').read())",
    "        val = raw.get(hnd)",
    "        if val is not None:",
    "            score += sum(1 for _ in val)",
    "    return score",
]
FILE_BODY = [
    "import json as _json",
    "def selection_entry(public_candidate, features, config, store):",
    "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
    "    side = config.get('side_path')",
    "    if side:",
    "        raw = _json.loads(open(side, 'r', encoding='utf-8').read())",
    "        hnd = config.get('side_handle')",
    "        val = raw.get(hnd)",
    "        if val is not None:",
    "            score += sum(1 for _ in val)",
    "    return score",
]
CLEAN_BODY = [
    "def selection_entry(public_candidate, features, config, store):",
    "    score = public_candidate.get('public_scores', {}).get('reranker', 0.0)",
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


def build_case(case_id: str, channel: str, kind: str, qids) -> Path:
    case_dir = WORK / case_id
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "detector_input").mkdir(parents=True)
    (case_dir / "private_truth").mkdir(parents=True)
    crows, qrows = [], []
    feature_matrix = {}
    runtime_store = {}
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
            handle = f"probe_{case_id}_{qi}"
            runtime_store[handle] = docs
    config = {"top_k": 5, "candidate_k": 8, "timeout_ms": 1000}
    if kind == "leak":
        if channel == "env":
            os.environ["REVIEW_PROBE_HANDLE"] = next(iter(runtime_store))
            config["store_path"] = str(case_dir / "detector_input" / "runtime_store.json")
            body = ENV_BODY
        elif channel == "sidefile":
            side = case_dir / "detector_input" / "side_cache.json"
            side.write_text(json.dumps(runtime_store), encoding="utf-8")
            config["side_path"] = str(side)
            config["side_handle"] = next(iter(runtime_store))
            body = FILE_BODY
        else:
            raise ValueError(channel)
    else:
        body = CLEAN_BODY
        os.environ.pop("REVIEW_PROBE_HANDLE", None)
    (case_dir / "detector_input" / "adapter.py").write_text("\n".join(body) + "\n", encoding="utf-8")
    (case_dir / "detector_input" / "public_queries.json").write_text(json.dumps(qrows), encoding="utf-8")
    (case_dir / "detector_input" / "public_candidates.json").write_text(json.dumps(crows), encoding="utf-8")
    (case_dir / "detector_input" / "public_features.json").write_text(json.dumps(feature_matrix), encoding="utf-8")
    (case_dir / "detector_input" / "public_config.json").write_text(json.dumps(config), encoding="utf-8")
    (case_dir / "detector_input" / "runtime_store.json").write_text(json.dumps(runtime_store), encoding="utf-8")
    truth = {
        "case_id": case_id,
        "family": "Leak-Boundary" if kind == "leak" else "Clean",
        "pattern_id": channel if kind == "leak" else "Clean",
        "module": "review_boundary_channel", "field": channel if kind == "leak" else "",
        "source_type": "OUT_OF_BAND_SMUGGLE" if kind == "leak" else "",
        "sink": "candidate_scoring", "file": "adapter.py", "line": 0,
        "injected_qids": len(qids) if kind == "leak" else 0,
        "injected_candidates": len(crows) if kind == "leak" else 0,
        "test_only": True,
        "note": "private doc list reaches the scoring sink through raw env/file I/O, bypassing the "
                "instrumented read surface on purpose; expected to be invisible to surface-bound auditors.",
    }
    (case_dir / "private_truth" / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_dir


def main() -> None:
    _require_inputs()
    WORK.mkdir(parents=True, exist_ok=True)
    rows = []
    specs = ([f"bound_env_{i}" for i in range(1, 4)] +
             [f"bound_file_{i}" for i in range(1, 4)] +
             [f"bound_clean_{i}" for i in range(1, 3)])
    for cid in specs:
        qids = load_qids(POOL, max_qids=6, start=hashlib.md5(cid.encode()).digest()[0] % 60)
        if cid.startswith("bound_env"):
            case_dir = build_case(cid, "env", "leak", qids)
        elif cid.startswith("bound_file"):
            case_dir = build_case(cid, "sidefile", "leak", qids)
        else:
            case_dir = build_case(cid, "clean", "clean", qids)
        for det in DETECTORS:
            find = run_detector(case_dir, det)
            rows.append({"case_id": cid, "kind": "leak" if "clean" not in cid else "clean",
                         "channel": "env" if cid.startswith("bound_env") else
                                    ("sidefile" if cid.startswith("bound_file") else "clean"),
                         "detector": det, "detected": bool(find.detected)})
        base, _ = run_selection(case_dir, mask_private=False)
        masked, _ = run_selection(case_dir, mask_private=True)
        changed = sum(1 for q in base if masked.get(q) != base[q])
        rows.append({"case_id": cid, "kind": "leak" if "clean" not in cid else "clean",
                     "channel": "env" if cid.startswith("bound_env") else
                                ("sidefile" if cid.startswith("bound_file") else "clean"),
                     "detector": "invariance_class", "detected": changed > 0})
        print(f"done {cid}", flush=True)

    summary = []
    for ch in ("env", "sidefile", "clean"):
        for det in DETECTORS:
            hit = sum(1 for r in rows if r["channel"] == ch and r["detector"] == det and r["detected"])
            n = sum(1 for r in rows if r["channel"] == ch and r["detector"] == det)
            summary.append({"channel": ch, "detector": det, "detected": f"{hit}/{n}"})
    with (OUT / "boundary_channels_per_case.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with (OUT / "boundary_channels_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
    with (OUT / "boundary_channels.json").open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "note": (
            "Out-of-band smuggling probes (env var / side cache file) that reach the scoring sink "
            "without the instrumented read API. Expected: surface-bound components (runtime/ast/schema/"
            "invariance/composite) are blind (0/3). keyword may fire only on name-level tokens in "
            "configuration paths (e.g., 'cache' inside side_cache.json), which is a name alarm, not a "
            "data-flow detection. This measures the audit boundary honestly: coverage holds for flows "
            "through the instrumented surface; raw file/env I/O smuggling is out of scope and is why "
            "deployment hygiene (whitelists, module isolation, dummy replacement) is recommended.")},
            f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY (boundary channels) ===")
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
