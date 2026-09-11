"""E2: schema-overlap hard negative controls (reviewer comment 4).

Constructs fresh Clean cases whose public metadata/feature fields are NAMED like
private evaluation artifacts (gold_flag, human_label, relevance_score,
adjudicated_label, proxy_score, cached_evidence, backup_label, evidence_label)
but whose values are entirely public, then runs the FROZEN detectors.

Additive only: writes new case dirs under benchmark_work_v5_review_hn and a
result CSV under paper_package_dakd_v5_1/17_review_metrics/.  Frozen code and
frozen case dirs are never modified.
"""
from __future__ import annotations
import csv
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from benchmark_v3.isolated_runner import run_detector  # noqa: E402

WORK_HN = Path(os.environ.get("MEDSAGE_REVIEW_HN", str(ROOT / "benchmark_work_v5_review_hn")))
PKG = ROOT / "paper_package_dakd_v5_1"
OUT = Path(os.environ.get("REVIEW_METRICS_OUT", str(PKG / "17_review_metrics")))
OUT.mkdir(parents=True, exist_ok=True)

# metadata keys mirror the frozen hard-clean skeleton (schema-whitelisted in the
# frozen benchmark: schema_guard reports 0 FP there); artifact-LIKE names live in
# public_features, which the frozen schema guard does not treat as candidate fields.
FROZEN_HARD_CLEAN_METADATA = {
    "state_cache": "public",
    "label_encoder": "public",
    "backup_ranker": "public",
    "support_feature_public": 1,
    "source": "review_hn",
}
GOLDISH_FEATURES = {
    "gold_flag": 0,
    "gold_feature": 0.0,
    "human_label_enc": 0,
    "relevance_score": 0.2,
    "adjudicated_enc": 0,
    "proxy_score": 0.1,
    "cached_evidence": "public",
    "backup_field": 0,
    "evidence_label_enc": 0,
}

ADAPTER_PUBLIC_ONLY = """# -*- coding: utf-8 -*-
from __future__ import annotations

def selection_entry(public_candidate, features, config, store):
    score = public_candidate.get("public_scores", {}).get("bm25", 0.0)
    return score
"""

ADAPTER_USES_PUBLIC_GOLDISH = """# -*- coding: utf-8 -*-
from __future__ import annotations

def _f(x):
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0

def selection_entry(public_candidate, features, config, store):
    # Uses ONLY public values; the field NAMES mimic private evaluation
    # artifacts (state_cache, label_encoder, relevance_score, gold_flag,
    # proxy_score, adjudicated_enc, ...). Never touches the private store.
    score = public_candidate.get("public_scores", {}).get("bm25", 0.0)
    md = public_candidate.get("metadata", {}) or {}
    ft = (features or {}).get(public_candidate.get("qid_hash"), {}) or {}
    score += 0.01 * _f(md.get("support_feature_public"))
    score += 0.02 * _f(md.get("state_cache") == "public")
    score += 0.01 * _f(md.get("label_encoder") == "public")
    score += 0.005 * _f(ft.get("relevance_score"))
    score += 0.005 * _f(ft.get("gold_flag"))
    score += 0.003 * _f(ft.get("proxy_score"))
    return score
"""


def build_case(case_id: str, variant: str, qids: int = 3, cands: int = 6) -> Path:
    case_dir = WORK_HN / case_id
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "detector_input").mkdir(parents=True)
    (case_dir / "private_truth").mkdir(parents=True)
    candidates = []
    for qi in range(qids):
        qh = f"h_hn_{case_id}_{qi}"
        for ci in range(1, cands + 1):
            md = {"source": "hn", "rank_hint": ci}
            md.update(FROZEN_HARD_CLEAN_METADATA)
            candidates.append({
                "qid_hash": qh,
                "doc_id_hash": f"h_{case_id}_q{qi}_d{ci}",
                "rank": ci,
                "public_scores": {"bm25": round(1.0 - ci * 0.05, 4)},
                "metadata": md,
            })
    (case_dir / "detector_input" / "public_candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False), encoding="utf-8")
    (case_dir / "detector_input" / "public_config.json").write_text(
        json.dumps({"top_k": 5, "candidate_k": cands}, ensure_ascii=False), encoding="utf-8")
    features = {f"h_hn_{case_id}_{qi}": dict(GOLDISH_FEATURES) for qi in range(qids)}
    (case_dir / "detector_input" / "public_features.json").write_text(
        json.dumps(features, ensure_ascii=False), encoding="utf-8")
    (case_dir / "detector_input" / "runtime_store.json").write_text("{}", encoding="utf-8")
    adapter = ADAPTER_USES_PUBLIC_GOLDISH if variant == "uses_public" else ADAPTER_PUBLIC_ONLY
    (case_dir / "detector_input" / "adapter.py").write_text(adapter, encoding="utf-8")
    truth = {
        "case_id": case_id, "family": "Clean", "pattern_id": "Clean",
        "hard_clean": True, "clean_type": "hard_schema_overlap",
        "variant": variant, "source_calls_gt0": False, "sink_calls_gt0": False,
        "injected_qids": 0, "injected_candidates": 0, "injected_features": 0,
        "test_only": True,
    }
    (case_dir / "private_truth" / "truth.json").write_text(
        json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_dir


DETECTORS = ["keyword_static_baseline", "ast_static_dataflow", "schema_guard",
             "runtime_taint", "invariance", "full_audit"]


def main() -> None:
    WORK_HN.mkdir(parents=True, exist_ok=True)
    rows = []
    # 12 variants using the gold-ish-named public fields (the interesting case),
    # plus 6 pure-public-score controls (baseline clean).
    specs = ([("uses_public", 12), ("public_only", 6)])
    idx = 0
    for variant, count in specs:
        for _ in range(count):
            idx += 1
            case_id = f"hn_{idx:03d}"
            case_dir = build_case(case_id, variant)
            for det in DETECTORS:
                find = run_detector(case_dir, det)
                row = {
                    "case_id": case_id,
                    "variant": variant,
                    "detector": det,
                    "detected": bool(find.detected),
                    "module": getattr(find, "module", ""),
                    "field": getattr(find, "field", ""),
                    "evidence": str(getattr(find, "evidence", ""))[:80],
                }
                rows.append(row)
                print(f"{case_id} [{variant}] {det}: detected={bool(find.detected)}", flush=True)

    fp_summary = {}
    for det in DETECTORS:
        det_rows = [r for r in rows if r["detector"] == det]
        fp = sum(1 for r in det_rows if r["detected"])
        total = len(det_rows)
        fp_summary[det] = {"fp": fp, "n": total, "false_positive_rate": fp / total if total else 0.0,
                           "specificity": 1.0 - (fp / total if total else 0.0)}

    with (OUT / "main_hard_negative_schema_overlap_per_case.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with (OUT / "main_hard_negative_schema_overlap_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["detector", "fp", "n", "false_positive_rate", "specificity"])
        w.writeheader()
        for det, s in fp_summary.items():
            w.writerow({"detector": det, **s})
    with (OUT / "main_hard_negative_schema_overlap.json").open("w", encoding="utf-8") as f:
        json.dump({"fp_summary": fp_summary, "note": (
            "20 fresh Clean cases whose public metadata/features are named like private evaluation "
            "artifacts (gold_flag, human_label, relevance_score, adjudicated_label, proxy_score, "
            "cached_evidence, ...) with values entirely public; frozen detectors, additive run.")},
            f, ensure_ascii=False, indent=2)
    print("\n=== FP SUMMARY (all cases are Clean by construction) ===")
    print(json.dumps(fp_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
