# -*- coding: utf-8 -*-
"""Claim-consistency tests for the revision-round evidence (E1-E7).

These tests read only the frozen, sanitized outputs shipped in
``results/04_revision_metrics/`` plus the scripts in ``scripts/review_metrics/``.
They require no private data and enforce that the numbers quoted in the manuscript
and the response letter are exactly the numbers in the published artifacts.

Mapping: docs/REVISION_EVIDENCE_MAPPING.md
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVID = ROOT / "results" / "04_revision_metrics"
SCRIPTS = ROOT / "scripts" / "review_metrics"


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def by(rows: list[dict], **kw) -> dict:
    """Return the single row matching all key=value filters."""
    hits = [r for r in rows if all(str(r.get(k)) == str(v) for k, v in kw.items())]
    assert len(hits) == 1, f"expected exactly one row for {kw}, got {len(hits)}"
    return hits[0]


# --------------------------------------------------------------------------- E1

def test_e1_labels_reproduced_and_split():
    rows = load_csv(EVID / "main_four_layer_metrics_summary.csv")
    assert len(rows) == 3
    access = by(rows, **{"class": "ACCESS_LEAK"})
    behavioral = by(rows, **{"class": "BEHAVIORAL_LEAK"})
    allpos = by(rows, **{"class": "ALL_LEAK_POSITIVES"})
    assert (int(access["cases"]), int(access["repro_ok"])) == (28, 28)
    assert (int(behavioral["cases"]), int(behavioral["repro_ok"])) == (8, 8)
    assert (int(allpos["cases"]), int(allpos["repro_ok"])) == (36, 36)


def test_e1_access_quantification_matches_paper():
    rows = load_csv(EVID / "main_four_layer_metrics_summary.csv")
    access = by(rows, **{"class": "ACCESS_LEAK"})
    # manuscript: 5.8% of evaluated documents, mean |delta| 0.079, max 5.0, Kendall tau 1.0
    assert abs(float(access["frac_score_changed_docs_mean"]) - 0.058) < 0.001
    assert abs(float(access["mean_abs_score_delta_mean"]) - 0.079) < 0.001
    assert float(access["max_abs_score_delta_max"]) == 5.0
    assert float(access["mean_kendall_tau_mean"]) == 1.0
    # Top-K identical at K = 3/5/7 for all 28 ACCESS cases
    for k in (3, 5, 7):
        assert int(access[f"cases_set_changed_K{k}"]) == 0
        assert int(access[f"cases_order_changed_K{k}"]) == 0
        assert int(access[f"total_replaced_docs_K{k}"]) == 0


def test_e1_behavioral_changes_match_paper():
    rows = load_csv(EVID / "main_four_layer_metrics_summary.csv")
    behavioral = by(rows, **{"class": "BEHAVIORAL_LEAK"})
    # manuscript: order changes at every K; set changes 8/8 at K=3 and 4/8 at K=5
    for k in (3, 5, 7):
        assert int(behavioral[f"cases_order_changed_K{k}"]) == 8
    assert int(behavioral["cases_set_changed_K3"]) == 8
    assert int(behavioral["cases_set_changed_K5"]) == 4
    assert int(behavioral["total_replaced_docs_K3"]) == 20
    assert int(behavioral["total_replaced_docs_K5"]) == 16


# --------------------------------------------------------------------------- E2

def test_e2_schema_overlap_specificity():
    rows = load_csv(EVID / "main_hard_negative_schema_overlap_summary.csv")
    assert len(rows) == 6
    for det in ("ast_static_dataflow", "schema_guard", "runtime_taint", "invariance", "full_audit"):
        r = by(rows, detector=det)
        assert int(r["n"]) == 18
        assert int(r["fp"]) == 0
        assert float(r["specificity"]) == 1.0
    kw = by(rows, detector="keyword_static_baseline")
    assert (int(kw["fp"]), float(kw["specificity"])) == (18, 0.0)


# --------------------------------------------------------------------------- E3

def test_e3_new_operators_main_pipeline():
    rows = load_csv(EVID / "new_operators_main_summary.csv")
    for det in ("runtime_taint", "full_audit", "ast_static_dataflow"):
        r = by(rows, detector=det)
        assert (int(r["tp"]), int(r["fp"]), int(r["positives"]), int(r["negatives"])) == (12, 0, 12, 6)
    for det in ("schema_guard", "invariance"):
        r = by(rows, detector=det)
        assert (int(r["tp"]), int(r["fp"])) == (0, 0)
    kw = by(rows, detector="keyword_static_baseline")
    assert (int(kw["tp"]), int(kw["fp"])) == (12, 6)


def test_e3_new_operators_second_pipeline():
    rows = load_csv(EVID / "new_operators_cross_summary.csv")
    for det in ("runtime_taint", "full_audit", "ast_static_dataflow"):
        r = by(rows, detector=det)
        assert (int(r["tp"]), int(r["fp"]), int(r["positives"]), int(r["negatives"])) == (12, 0, 12, 4)
    for det in ("schema_guard", "invariance"):
        r = by(rows, detector=det)
        assert (int(r["tp"]), int(r["fp"])) == (0, 0)


def test_e3_cross_artifact_has_no_internal_absolute_path():
    data = load_json(EVID / "new_operators_cross.json")
    assert "source" not in data, "internal absolute source path must be redacted"
    assert data.get("source_case") == "benchmark_work_cross/<frozen-cross-case>"


# --------------------------------------------------------------------------- E4

def test_e4_retrieval_method_independence():
    rows = load_csv(EVID / "retrieval_independence_summary.csv")
    for method in ("dense", "bm25"):
        for det in ("runtime_taint", "full_audit", "ast_static_dataflow"):
            r = by(rows, method=method, detector=det)
            assert (int(r["tp"]), int(r["fp"]), int(r["positives"]), int(r["negatives"])) == (8, 0, 8, 2), (method, det)
            assert float(r["specificity"]) == 1.0


# --------------------------------------------------------------------------- E5

def test_e5_composite_exceeds_runtime_on_dormant_leaks():
    rows = load_csv(EVID / "latent_gate_summary.csv")
    dormant = [r for r in rows if r["group"] == "dormant"]
    assert by(dormant, detector="runtime_taint")["detected"] == "0/3"
    assert by(dormant, detector="ast_static_dataflow")["detected"] == "3/3"
    assert by(dormant, detector="full_audit")["detected"] == "3/3"
    active = [r for r in rows if r["group"] == "active"]
    assert by(active, detector="runtime_taint")["detected"] == "3/3"
    assert by(active, detector="full_audit")["detected"] == "3/3"


def test_e5_clean_controls_have_no_false_positive():
    rows = load_csv(EVID / "latent_gate_summary.csv")
    clean = [r for r in rows if r["group"] == "clean"]
    for det in ("ast_static_dataflow", "schema_guard", "runtime_taint", "invariance", "full_audit"):
        assert by(clean, detector=det)["detected"] == "0/3", det


# --------------------------------------------------------------------------- E6

def test_e6_out_of_band_channels_are_out_of_scope():
    rows = load_csv(EVID / "boundary_channels_summary.csv")
    for channel in ("env", "sidefile"):
        for det in ("ast_static_dataflow", "schema_guard", "runtime_taint", "invariance", "full_audit"):
            assert by(rows, channel=channel, detector=det)["detected"] == "0/3", (channel, det)
    clean = [r for r in rows if r["channel"] == "clean"]
    assert by(clean, detector="full_audit")["detected"] == "0/2"


# --------------------------------------------------------------------------- E7

def test_e7_real_code_sweep_negative_result():
    data = load_json(EVID / "real_code_sweep.json")
    assert data["deploy_path_hits"] == 0
    assert data["total_hits"] == 41
    sites = load_csv(EVID / "real_code_sweep_summary.csv")
    assert all(r["role"] == "OFFLINE" for r in sites), "no gold read may sit on a deployable path"


# --------------------------------------------------------------- privacy / hygiene

def test_revision_scripts_carry_no_real_absolute_paths():
    """Repository policy: zero real absolute local paths in published material."""
    pattern = re.compile(r"[A-Za-z]:\\")
    offenders = []
    for path in sorted(SCRIPTS.glob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.name}:{lineno}")
    assert not offenders, f"absolute Windows paths found: {offenders}"


def test_all_experiment_scripts_present():
    expected = {
        "run_main_four_layer_metrics.py",
        "run_schema_overlap_hardnegatives.py",
        "run_new_leak_operators.py",
        "run_cross_new_leak_operators.py",
        "run_retrieval_independence.py",
        "run_latent_gate.py",
        "run_boundary_channels.py",
        "sweep_real_code.py",
    }
    present = {p.name for p in SCRIPTS.glob("*.py")}
    assert expected <= present, f"missing scripts: {sorted(expected - present)}"


def test_scripts_soft_exit_without_local_inputs():
    """Scripts needing local/private inputs must ship the REQUIRES_LOCAL_ORIGINAL_PROJECT guard."""
    for name in ("run_main_four_layer_metrics.py", "run_new_leak_operators.py",
                 "run_latent_gate.py", "run_boundary_channels.py",
                 "run_retrieval_independence.py", "run_cross_new_leak_operators.py",
                 "sweep_real_code.py"):
        text = (SCRIPTS / name).read_text(encoding="utf-8")
        assert "REQUIRES_LOCAL_ORIGINAL_PROJECT" in text, name
        assert "_require_inputs()" in text, name
