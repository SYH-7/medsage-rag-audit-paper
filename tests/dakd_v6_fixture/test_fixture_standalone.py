# -*- coding: utf-8 -*-
"""独立 fixture-only 最小复现测试（tests/dakd_v6_fixture）。

全新解压后（无第二工程）可直接运行：
    python scripts/dakd_v6/run_tcm_sleep_cross_pipeline.py --fixture-only
    pytest -q tests/dakd_v6_fixture

fixture 不含第二工程原始医疗语料、不含私有 truth 明文；
仅验证冻结检测器（benchmark_v3）在脱敏 fixture 上的可复现性，
不等同于第二工程 Dense/Hybrid/Domain 管线验证。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _load_main():
    spec = importlib.util.spec_from_file_location(
        "run_tcm_sleep_cross_pipeline", ROOT / "scripts" / "dakd_v6" / "run_tcm_sleep_cross_pipeline.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MAIN = _load_main()
FIXTURE_ROOT = MAIN.FIXTURE_ROOT

ABS_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"'<>|;*?]{2,}")
PRIVATE_VALUE_RE = re.compile("TEST_ONLY_PRIVATE_SOURCE" + "_" + "[MF][1-4]")


def _fixture_text_files() -> list[Path]:
    return [p for p in FIXTURE_ROOT.rglob("*") if p.is_file() and p.suffix in {".py", ".json", ".md"}]


def test_01_fixture_reproduction_matches_expected():
    """运行 fixture 检测，结果与固化预期一致（可复现）。"""
    out = MAIN.run_fixture_only()
    assert out["status"] == "OK", out.get("mismatches")
    assert out["case_count"] == 2
    assert out["detector_count"] == 6


def test_02_fixture_no_second_pipeline_import():
    """fixture adapter 不接入第二工程（不含 rag_service import）。"""
    for p in (FIXTURE_ROOT / "cases").rglob("adapter.py"):
        text = p.read_text(encoding="utf-8")
        assert "rag_service" not in text
        assert "BM25Retriever" not in text


def test_03_fixture_no_private_plaintext():
    """fixture 不含测试私有值明文（TEST_ONLY_PRIVATE_SOURCE_<pattern> 形态）。"""
    for p in _fixture_text_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        assert not PRIVATE_VALUE_RE.search(text), p


def test_04_fixture_no_abs_paths():
    """fixture 不含本地绝对路径。"""
    for p in _fixture_text_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        assert not ABS_PATH_RE.search(text), p


def test_05_fixture_expected_valid():
    """预期结果：泄漏 fixture 被 runtime_taint/composite 检出，Clean 全部不检出。"""
    expected = json.loads((FIXTURE_ROOT / "expected.json").read_text(encoding="utf-8"))
    exp = {f"{e['case_id']}|{e['detector']}": bool(e["detected"]) for e in expected["cases"]}
    assert exp["fx_leak_m1|runtime_taint"] is True
    assert exp["fx_leak_m1|composite_audit"] is True
    for det in ["keyword_static_baseline", "ast_static_dataflow", "schema_guard", "runtime_taint", "invariance", "composite_audit"]:
        assert exp[f"fx_clean|{det}"] is False


def test_06_fixture_no_original_qa_text():
    """fixture 不含原始医疗问答全文/真实业务数据。"""
    for p in (FIXTURE_ROOT / "cases").rglob("*"):
        if p.is_file() and p.suffix in {".json", ".py", ".md"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            assert "gold_answer" not in text
            assert "知识_chunks" not in text and "knowledge_chunks" not in text
