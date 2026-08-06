from __future__ import annotations

import csv
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
PKG = ROOT / "paper_package_dakd_v5"
RESULT_ROOT = ROOT / "results" / "01_main_audit"
BUNDLE_MODE = not PKG.exists() and (RESULT_ROOT / "author_tables").exists()


def rows(path: pathlib.Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def result_path(*parts: str) -> pathlib.Path:
    if BUNDLE_MODE:
        mapping = {
            "01_gold": "gold_reports",
            "02_scenarios": "author_tables",
            "03_detection": "detection_results",
            "04_unseen": "unseen_results",
            "05_localization": "localization_results",
            "06_runtime": "runtime_results",
            "07_cross_pipeline": "cross_pipeline",
            "08_behavior": "behavior",
            "09_adapter_execution": "adapter_execution",
        }
        return RESULT_ROOT / mapping.get(parts[0], parts[0]) / pathlib.Path(*parts[1:])
    return PKG.joinpath(*parts)


def test_formal_code_has_no_rank_based_gold_construction():
    texts = []
    for base in [ROOT / "src", ROOT / "scripts", ROOT / "configs"]:
        for p in base.rglob("*"):
            if p.suffix.lower() in {".py", ".yaml", ".yml"} and "legacy" not in p.parts:
                texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    code = "\n".join(texts)
    assert "rows[:3]" not in code
    assert "synthetic_rows" not in code


def test_all_12_adapter_patterns_executed():
    summary = rows(result_path("09_adapter_execution", "ADAPTER_PATTERN_SUMMARY.csv"))
    positive = [r for r in summary if r["pattern_id"] != "Clean"]
    assert len({r["pattern_id"] for r in positive}) == 12
    assert all(int(r["executed_cases"]) > 0 for r in positive)
    assert all(int(r["adapter_calls"]) > 0 for r in positive)


def test_runtime_monitor_depends_on_executed_adapter_paths():
    summary = rows(result_path("09_adapter_execution", "ADAPTER_PATTERN_SUMMARY.csv"))
    source_positive = [r for r in summary if r["pattern_id"] != "Clean"]
    assert all(int(r["source_calls"]) > 0 for r in source_positive)
    assert all(int(r["sink_calls"]) > 0 for r in source_positive)


def test_offline_and_online_runtime_are_separated():
    offline = rows(result_path("06_runtime", "OFFLINE_AUDIT_RUNTIME.csv"))
    online = rows(result_path("06_runtime", "ONLINE_SELECTION_RUNTIME.csv"))
    assert {r["condition"] for r in offline} >= {"config_load", "keyword_scan", "ast_scan"}
    assert {r["condition"] for r in online} >= {
        "baseline_selection",
        "baseline_plus_schema",
        "baseline_plus_runtime_monitor",
        "baseline_plus_invariance",
        "baseline_plus_full_online_audit",
    }
    assert all(r["incremental_ms"] != "N/A_OFFLINE" for r in online)


def test_full_audit_uses_frozen_config_sha():
    frozen = rows(result_path("03_detection", "FROZEN_POLICY_SHA256.csv"))
    detection = rows(result_path("03_detection", "DETECTOR_OUTPUT_INDEX.csv"))
    cfg_hash = next(r["config_sha256"] for r in frozen if r["config_file"].endswith("full_audit_frozen.yaml"))
    assert all(r["config_sha256"] == cfg_hash for r in detection)


def test_second_pipeline_is_honestly_marked():
    status = rows(result_path("07_cross_pipeline", "CROSS_PIPELINE_STATUS.csv"))[0]
    assert status["status"] in {"NOT_RUN", "REPRODUCED"}
    if status["status"] == "NOT_RUN":
        assert status["clean_cases"] == "0"
        assert status["metadata_variants"] == "0"
        assert status["reason"]


def test_fixture_reproduction_assets_present():
    fixture = ROOT / "reproduction_fixture"
    if fixture.exists():
        expected = json.loads((fixture / "EXPECTED_FIXTURE_CASES.json").read_text(encoding="utf-8"))
        assert expected
        assert all((fixture / "benchmark_work" / r["case_id"] / "detector_input" / "adapter.py").exists() for r in expected)
