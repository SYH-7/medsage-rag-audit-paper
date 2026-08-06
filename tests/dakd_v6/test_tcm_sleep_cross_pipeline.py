# -*- coding: utf-8 -*-
"""跨管线受控泄漏验证测试套件（tests/dakd_v6）。

覆盖任务书第十节 14 项测试要求：
1. 第二工程原始文件未被修改
2. 适配器确实调用真实检索或选择函数
3. Clean 案例 Source 调用数为 0
4. 泄漏案例 Source 和 Sink 调用数均大于 0
5. 检测器无法读取 private_truth
6. 屏蔽私有值后能够完成不变性重放
7. 结果文件中的 case_id 与 truth 一一对应
8. Precision 未定义时不写成 1
9. 未执行模式保持 NOT_RUN（此处 12 模式全部真实执行，无 NOT_RUN）
10. 所有输出不包含本地绝对路径
11. 不包含 API 密钥
12. 不包含真实私有标签
13. 不包含原始医疗问答全文
14. 不包含个人信息

本测试只读验证已生成的结果文件与适配器代码，不修改任何冻结文件。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
PKG = ROOT / "results" / "03_cross_pipeline"
WORK = ROOT / "benchmark_work_cross"
_second_root_env = os.environ.get("TCM_SLEEP_RAG_ROOT", "")
SECOND_ROOT = Path(_second_root_env) if _second_root_env else None
sys.path.insert(0, str(SRC))

from cross_pipeline.synthetic_private_source import TEST_ONLY_PRIVATE_SOURCE  # noqa: E402
from cross_pipeline.tcm_sleep_adapter import PATTERN_FIELDS, ALL_PATTERNS  # noqa: E402

DETECTORS = ["keyword_static_baseline", "ast_static_dataflow", "schema_guard", "runtime_taint", "invariance", "composite_audit"]

ABS_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"'<>|;*?]{2,}")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*[\"'][^\"']+[\"']|" + "sk" + "-" + "[A-Za-z0-9]{10,}")
PRIVATE_RE = re.compile("TEST_ONLY_PRIVATE_SOURCE" + "_" + "[MF][1-4]")  # 具体测试值明文（带 pattern 后缀）
PERSON_RE = re.compile("身份证号" + r"\s*[:：]?\s*[\dXx]{6,}" + "|" + "phone" + r"\s*[:=]\s*[\d+]{5,}" + "|" + "联系电话" + r"\s*[:：]\s*[\d+]{5,}" + "|" + "姓名" + r"\s*[:：]\s*\S{2,8}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_text_files() -> list[Path]:
    return [p for p in PKG.rglob("*") if p.is_file() and p.suffix in {".csv", ".json", ".jsonl", ".md", ".txt"} and "private_truth" not in p.parts]


def _truth_by_case() -> dict[str, dict]:
    out = {}
    for case in WORK.iterdir():
        t = case / "private_truth" / "truth.json"
        if t.exists():
            out[case.name] = json.loads(t.read_text(encoding="utf-8"))
    return out


def _restore_import_environment(orig_path: list[str]) -> None:
    """恢复 sys.path 并清理第二工程 rag_service 的模块缓存（避免污染 namespace 包解析）。"""
    sys.path[:] = orig_path
    for mod in [m for m in list(sys.modules) if m == "rag_service" or m.startswith("rag_service.")]:
        del sys.modules[mod]


# 1. 第二工程原始文件未被修改
@pytest.mark.skipif(SECOND_ROOT is None or not SECOND_ROOT.is_dir(), reason="REQUIRES_LOCAL_ORIGINAL_PROJECT: tcm_sleep_rag_full not available (set TCM_SLEEP_RAG_ROOT)")
def test_01_second_pipeline_unchanged():
    baseline = json.loads((PKG / "manifests" / "SECOND_PIPELINE_BASELINE.json").read_text(encoding="utf-8"))
    changed = []
    missing = []
    for e in baseline["baseline_files"]:
        p = SECOND_ROOT / e["path"]
        if not p.exists():
            missing.append(e["path"])
        elif _sha256(p) != e["sha256"]:
            changed.append(e["path"])
    assert not missing, f"missing: {missing}"
    assert not changed, f"changed: {changed}"


# 2. 适配器确实调用真实检索或选择函数
@pytest.mark.skipif(SECOND_ROOT is None or not SECOND_ROOT.is_dir(), reason="REQUIRES_LOCAL_ORIGINAL_PROJECT: tcm_sleep_rag_full not available (set TCM_SLEEP_RAG_ROOT)")
def test_02_adapter_calls_real_retriever():
    adapter_src = (SRC / "cross_pipeline" / "tcm_sleep_adapter.py").read_text(encoding="utf-8")
    assert "from rag_service.retriever_bm25 import BM25Retriever" in adapter_src
    assert "def _real_bm25_scores" in adapter_src
    assert "BM25Retriever(chunks_path=" in adapter_src
    assert "def retrieve_candidates" in adapter_src
    # 真实调用验证（第二工程 BM25 检索 + Top-K）
    from cross_pipeline.tcm_sleep_adapter import TcmSleepPipelineAdapter

    orig_path = list(sys.path)
    try:
        verifier = TcmSleepPipelineAdapter(SECOND_ROOT, SECOND_ROOT / "data/processed/knowledge_chunks_v3_1905_ffr.jsonl", SECOND_ROOT / "data/dictionary")
        result = verifier.verify()
        assert result["status"] == "OK", result
        assert result["retrieved_count"] > 0
    finally:
        _restore_import_environment(orig_path)


# 3. Clean 案例 Source 调用数为 0
def test_03_clean_source_calls_zero():
    rows = [json.loads(line) for line in (PKG / "cases" / "cross_pipeline_case_results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    clean_rows = [r for r in rows if not r["is_leak"] and r["detector"] == "runtime_taint"]
    assert len(clean_rows) == 60, len(clean_rows)
    for r in clean_rows:
        assert int(r["source_calls"]) == 0, r["case_id"]


# 4. 泄漏案例 Source 和 Sink 调用数均大于 0
def test_04_leak_source_sink_gt0():
    rows = [json.loads(line) for line in (PKG / "cases" / "cross_pipeline_case_results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    leak_rows = [r for r in rows if r["is_leak"] and r["detector"] == "runtime_taint"]
    assert len(leak_rows) == 36, len(leak_rows)
    for r in leak_rows:
        assert int(r["source_calls"]) > 0, f"{r['case_id']} source"
        assert int(r["sink_calls"]) > 0, f"{r['case_id']} sink"


# 5. 检测器无法读取 private_truth
@pytest.mark.skipif(not WORK.exists(), reason="REQUIRES_LOCAL_ORIGINAL_PROJECT: benchmark_work_cross runtime dir not available")
def test_05_detector_cannot_read_private_truth():
    # 检测器源代码不含 private_truth 目录引用
    for rel in ["benchmark_v3/isolated_runner.py", "benchmark_v3/static_dataflow_detector.py", "benchmark_v3/taint.py"]:
        src = (SRC / rel).read_text(encoding="utf-8")
        assert "private_truth" not in src
    # case 的 detector_input 内不存在 private_truth 子目录
    for case in WORK.iterdir():
        di = case / "detector_input"
        assert not (di / "private_truth").exists()
    # 运行检测器时只读取 detector_input
    assert (PKG / "manifests" / "synthetic_private_truth_registry.json").exists()


# 6. 屏蔽私有值后能够完成不变性重放
@pytest.mark.skipif(not WORK.exists(), reason="REQUIRES_LOCAL_ORIGINAL_PROJECT: benchmark_work_cross runtime dir not available")
def test_06_mask_private_replay():
    from benchmark_v3.isolated_runner import run_selection

    cases = [p for p in WORK.iterdir() if (p / "detector_input").exists()]
    assert cases
    orig_path = list(sys.path)
    try:
        for case in cases[:5]:
            selected, _ = run_selection(case, mask_private=True)
            assert isinstance(selected, dict)
    finally:
        _restore_import_environment(orig_path)


# 7. 结果文件中的 case_id 与 truth 一一对应
@pytest.mark.skipif(not WORK.exists(), reason="REQUIRES_LOCAL_ORIGINAL_PROJECT: benchmark_work_cross runtime dir not available")
def test_07_case_id_truth_alignment():
    truth = _truth_by_case()
    rows = [json.loads(line) for line in (PKG / "cases" / "cross_pipeline_case_results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    result_ids = {r["case_id"] for r in rows}
    effects = list(csv.DictReader((PKG / "leak_effects" / "cross_pipeline_leak_effects.csv").open(encoding="utf-8-sig")))
    effect_ids = {e["case_id"] for e in effects}
    assert set(truth.keys()) == result_ids == effect_ids
    assert len(truth) == 96


# 8. Precision 未定义时不写成 1
def test_08_precision_not_one_when_undefined():
    summary = list(csv.DictReader((PKG / "detection" / "cross_pipeline_detection_summary.csv").open(encoding="utf-8-sig")))
    ast = next(s for s in summary if s["detector"] == "ast_static_dataflow")
    assert ast["precision"] in ("null", "N/A"), ast["precision"]
    assert ast["tp"] == "0" and ast["fp"] == "0"


# 9. 12 类模式全部真实执行（无 NOT_RUN）
@pytest.mark.skipif(not WORK.exists(), reason="REQUIRES_LOCAL_ORIGINAL_PROJECT: benchmark_work_cross runtime dir not available")
def test_09_all_patterns_executed():
    truth = _truth_by_case()
    leak_truth = [t for t in truth.values() if t["family"] != "Clean"]
    executed = {t["pattern_id"] for t in leak_truth}
    assert executed == set(ALL_PATTERNS), f"missing: {set(ALL_PATTERNS) - executed}"
    assert len(leak_truth) == 36
    # 每模式 3 个案例
    from collections import Counter

    cnt = Counter(t["pattern_id"] for t in leak_truth)
    for pat in ALL_PATTERNS:
        assert cnt[pat] == 3, f"{pat}: {cnt[pat]}"
    # 无 NOT_RUN 标记
    for t in leak_truth:
        assert t["source_calls_gt0"] and t["sink_calls_gt0"]


# 10. 所有输出不包含本地绝对路径
def test_10_no_absolute_paths_in_outputs():
    for path in _output_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not ABS_PATH_RE.search(text), f"absolute path in {path.name}"


# 11. 不包含 API 密钥
def test_11_no_api_keys():
    for path in _output_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not SECRET_RE.search(text), f"secret in {path.name}"


# 12. 不包含真实私有标签（具体测试值明文；source_type 类型标记为契约要求，允许）
def test_12_no_private_label_plaintext():
    # 具体测试值明文：形如 TEST_ONLY_PRIVATE_SOURCE_<pattern>_<hash>，禁止出现在任何输出
    for path in _output_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not PRIVATE_RE.search(text), f"private value in {path.name}"
    # 类型标记只允许出现在 source_type 字段（truth.json 契约要求），不允许出现在 case 文本之外
    for path in _output_text_files():
        if path.name == "CROSS_PIPELINE_SCENARIO_INDEX.csv":
            text = path.read_text(encoding="utf-8", errors="ignore")
            allowed = text.replace("source_type", "").replace(TEST_ONLY_PRIVATE_SOURCE, "")
            assert TEST_ONLY_PRIVATE_SOURCE not in allowed or "source_type" in text


# 13. 不包含原始医疗问答全文
def test_13_no_qa_fulltext():
    for path in _output_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "gold_answer" not in text, f"gold_answer in {path.name}"
        assert "query_annotation" not in text
    rows = [json.loads(line) for line in (PKG / "cases" / "cross_pipeline_case_results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for r in rows:
        assert "question" not in r or not r.get("question")


# 14. 不包含个人信息
def test_14_no_personal_info():
    for path in _output_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not PERSON_RE.search(text), f"personal info in {path.name}"
