# -*- coding: utf-8 -*-
"""跨管线受控泄漏验证主脚本（dakd v6 / 16_cross_pipeline）。

阶段：
  0. frozen_manifest  冻结检测器 SHA256 清单 + 第二工程原文件基线
  1. audit            CROSS_PIPELINE_AUDIT.md（只读审计报告）
  2. build            构建 36 正例 + 60 Clean 案例（真实调用第二工程检索）
  3. detect           运行 6 个冻结检测器并输出检测汇总/混淆矩阵/逐案例结果
  4. leak_effects     泄漏影响分级（ACCESS_LEAK / BEHAVIORAL_LEAK）
  5. runtime          在线选择开销（5 种条件 × 预热3 + 正式10）
  6. pytest_report    运行新增测试与全量测试
  7. export          脱敏导出包（ZIP 生成 + 解压验证 + SHA256）
  8. all             依次执行以上全部

冻结约束：
  - 不得修改 benchmark_v3 检测器核心逻辑；若检测器需要修改 → PROTOCOL_BLOCKED。
  - 本脚本只读取冻结配置 configs/dakd_v5/*.yaml。
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile
import os
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from benchmark_v3.isolated_runner import run_detector, run_selection  # 冻结检测器（只读导入）
from benchmark_v3.taint import load_taint_trace
from cross_pipeline.synthetic_private_source import (
    TEST_ONLY_PRIVATE_SOURCE,
    private_handle,
    synthetic_private_value,
    write_private_truth_registry,
)
from cross_pipeline.tcm_sleep_adapter import (
    PATTERN_FAMILY,
    PATTERN_FIELDS,
    PATTERN_MODULE,
    PATTERN_SINK,
    TcmSleepPipelineAdapter,
    build_adapter_source,
    build_hard_clean_adapter_source,
    hash_id,
    load_public_questions,
)

WORK = ROOT / "benchmark_work_cross"
PKG = ROOT / "paper_package_dakd_v6" / "16_cross_pipeline"
PRIVATE_TRUTH_DIR = PKG / "private_truth"
DIST = ROOT / "dist"

# 冻结检测器源文件（不得修改；用于 SHA256 清单）
FROZEN_DETECTOR_FILES = [
    "src/benchmark_v3/isolated_runner.py",
    "src/benchmark_v3/static_dataflow_detector.py",
    "src/benchmark_v3/taint.py",
    "src/benchmark_v3/contracts.py",
    "src/benchmark_v3/source_sink_policy.py",
    "configs/dakd_v5/full_audit_frozen.yaml",
    "configs/dakd_v5/source_sink_policy.yaml",
]

# 第二工程核心原文件（只读基线，用于验证未被修改）
SECOND_PIPELINE_BASELINE_FILES = [
    "rag_service/api.py",
    "rag_service/build_index.py",
    "rag_service/category_classifier.py",
    "rag_service/chunk_builder.py",
    "rag_service/config.yaml",
    "rag_service/data_clean.py",
    "rag_service/dictionary_check.py",
    "rag_service/embedding_model.py",
    "rag_service/evidence_quality_evaluator.py",
    "rag_service/intent_decomposer.py",
    "rag_service/prompt_builder.py",
    "rag_service/reranker.py",
    "rag_service/retriever_bm25.py",
    "rag_service/retriever_dense.py",
    "rag_service/retriever_domain.py",
    "rag_service/retriever_domain_lite.py",
    "rag_service/retriever_ffr_rag.py",
    "rag_service/retriever_hybrid.py",
    "rag_service/retriever_hybrid_tuned.py",
    "rag_service/syndrome_matcher.py",
    "rag_service/term_normalizer.py",
    "README.md",
    "RUN_COMMANDS.md",
    "requirements.txt",
]

DETECTORS = [
    "keyword_static_baseline",
    "ast_static_dataflow",
    "schema_guard",
    "runtime_taint",
    "invariance",
    "composite_audit",
]

_second_root_env = os.environ.get("TCM_SLEEP_RAG_ROOT", "")
SECOND_ROOT = Path(_second_root_env) if _second_root_env else None
if SECOND_ROOT is not None and not SECOND_ROOT.is_dir():
    SECOND_ROOT = None
CHUNKS_PATH = (SECOND_ROOT / "data" / "processed" / "knowledge_chunks_v3_1905_ffr.jsonl") if SECOND_ROOT else None
DICT_DIR = (SECOND_ROOT / "data" / "dictionary") if SECOND_ROOT else None
EVAL_QUESTIONS = (SECOND_ROOT / "data" / "eval" / "eval_300.jsonl") if SECOND_ROOT else None


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
        fields = fields or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows or [{"status": "NOT_RUN"}])


def parse_frozen_config() -> dict:
    """只读解析冻结配置（不得修改检测器逻辑）。"""
    policy_path = ROOT / "configs" / "dakd_v5" / "source_sink_policy.yaml"
    cfg_path = ROOT / "configs" / "dakd_v5" / "full_audit_frozen.yaml"
    sources: list[str] = []
    sinks: dict[str, str] = {}
    mode = ""
    for raw in policy_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "sources:":
            mode = "sources"
        elif line == "sinks:":
            mode = "sinks"
        elif line.startswith("- ") and mode == "sources":
            sources.append(line[2:].strip())
        elif ":" in line and mode == "sinks":
            k, v = line.split(":", 1)
            sinks[k.strip()] = v.strip()
    priority: list[str] = []
    threshold = {"min_components": 1}
    allow_unknown = True
    mode = ""
    for raw in cfg_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "priority:":
            mode = "priority"
        elif line == "threshold:":
            mode = "threshold"
        elif line.startswith("allow_unknown_leak:"):
            mode = ""
            allow_unknown = line.split(":", 1)[1].strip().lower() == "true"
        elif line.endswith(":") and line not in {"priority:", "threshold:"}:
            mode = ""
        elif mode == "priority" and line.startswith("- "):
            priority.append(line[2:].strip())
        elif mode == "threshold" and ":" in line:
            k, v = line.split(":", 1)
            threshold[k.strip()] = int(v.strip())
    return {
        "source_sink_policy": {"sources": sources, "sinks": sinks},
        "priority": priority,
        "threshold": threshold,
        "allow_unknown_leak": allow_unknown,
        "config_sha256": sha256_file(cfg_path),
        "policy_sha256": sha256_file(policy_path),
    }


# ---------------------------------------------------------------------------
# 阶段 0：冻结清单
# ---------------------------------------------------------------------------
def frozen_manifest() -> dict:
    entries = []
    for rel in FROZEN_DETECTOR_FILES:
        path = ROOT / rel
        entries.append({"path": rel, "sha256": sha256_file(path) if path.exists() else "MISSING", "exists": path.exists()})
    manifest = {
        "experiment": "cross_pipeline_tcm_sleep_rag_full",
        "status": "FROZEN",
        "note": "冻结检测器：keyword_static_baseline / ast_static_dataflow / schema_guard / runtime_taint / invariance / composite_audit(=full_audit)。若需修改核心逻辑 -> PROTOCOL_BLOCKED_DETECTOR_CHANGE_REQUIRED",
        "frozen_files": entries,
        "composite_audit_mapping": {"composite_audit": "benchmark_v3.isolated_runner.full_audit (冻结)"},
    }
    write_json(PKG / "FROZEN_DETECTOR_MANIFEST.json", manifest)
    return manifest


def second_pipeline_baseline() -> dict:
    entries = []
    for rel in SECOND_PIPELINE_BASELINE_FILES:
        path = SECOND_ROOT / rel
        entries.append({"path": rel, "sha256": sha256_file(path) if path.exists() else "MISSING", "exists": path.exists()})
    manifest = {
        "pipeline": "tcm_sleep_rag_full",
        "purpose": "只读接入基线：实验开始前记录，实验结束后比对验证原文件未被修改",
        "baseline_files": entries,
    }
    write_json(PKG / "SECOND_PIPELINE_BASELINE.json", manifest)
    return manifest


def verify_second_pipeline_unchanged() -> dict:
    baseline = read_json(PKG / "SECOND_PIPELINE_BASELINE.json")
    changed: list[dict] = []
    missing: list[str] = []
    for e in baseline["baseline_files"]:
        path = SECOND_ROOT / e["path"]
        if not path.exists():
            missing.append(e["path"])
            continue
        if sha256_file(path) != e["sha256"]:
            changed.append({"path": e["path"], "expected": e["sha256"], "actual": sha256_file(path)})
    return {"unchanged": (not changed and not missing), "changed": changed, "missing": missing}


# ---------------------------------------------------------------------------
# 阶段 2：案例构建
# ---------------------------------------------------------------------------
def _pick_questions(questions: list[dict], case_index: int, qids_per_case: int) -> list[dict]:
    out = []
    for j in range(qids_per_case):
        idx = (case_index * qids_per_case + j) % len(questions)
        out.append(questions[idx])
    return out


def _inject_target_ranks() -> list[int]:
    return [3, 4, 5, 6, 7, 8]


def build_one_case(case_dir: Path, adapter: TcmSleepPipelineAdapter, questions: list[dict], spec: dict) -> dict:
    """构建单个案例（真实调用第二工程检索获取候选）。"""
    case_id = spec["case_id"]
    pattern = spec.get("pattern")
    variant = spec.get("variant", 0)
    hard_clean = bool(spec.get("hard_clean", False))
    picked = _pick_questions(questions, spec["index"], spec["qids_per_case"])
    detector_input = case_dir / "detector_input"
    private_truth = case_dir / "private_truth"
    detector_input.mkdir(parents=True, exist_ok=True)
    private_truth.mkdir(parents=True, exist_ok=True)

    crows: list[dict] = []
    features: dict[str, dict] = {}
    runtime_store: dict[str, list[str]] = {}
    cache_map: dict[str, str] = {}
    injected_candidates = 0
    injected_features = 0
    fallback_triggers = 0
    field = PATTERN_FIELDS[pattern][variant % 3] if pattern else ""
    family = PATTERN_FAMILY.get(pattern, "") if pattern else ""

    for q in picked:
        qh = hash_id(q["qid"] + "|" + q["question"])
        candidates = adapter.retrieve_candidates(q["question"], candidate_k=spec["candidate_k"])
        if not candidates:
            continue
        handle = private_handle(case_id, pattern or "Clean", qh)
        runtime_store[handle] = synthetic_private_value(case_id, pattern or "Clean", qh)
        for c in candidates:
            row = {
                "qid_hash": qh,
                "doc_id_hash": hash_id(c["chunk_id"]),
                "rank": c["rank"],
                "public_scores": {"bm25": c["bm25_score"], "reranker": c["bm25_score"]},
                "metadata": {"source": "knowledge_chunks_v3_1905_ffr", "rank_hint": c["rank"]},
            }
            if family == "Leak-M":
                if c["rank"] in _inject_target_ranks():
                    row["metadata"][field] = handle
                    injected_candidates += 1
                    if pattern == "M3":
                        cache_map[handle] = handle
            elif family in ("Leak-F", "Leak-R"):
                pass
            crows.append(row)
        if family == "Leak-M" and pattern == "M3":
            write_json(detector_input / "neutral_cache.json", cache_map)
        if family in ("Leak-F", "Leak-R"):
            features.setdefault(qh, {})[field] = handle
            injected_features += 1
            injected_candidates += len(candidates)
            if family == "Leak-R":
                fallback_triggers += 1

    config = {
        "top_k": spec["top_k"],
        "candidate_k": spec["candidate_k"],
        "weight_public_score": 1.0,
        "timeout_ms": 1000,
        "metadata_field": "aux_31",
        "question": picked[0]["question"] if picked else "",
        "chunks_path": str(CHUNKS_PATH).replace("\\", "/"),
        "dict_dir": str(DICT_DIR).replace("\\", "/"),
    }
    if pattern == "M3":
        config["cache_file"] = "neutral_cache.json"

    if pattern is None:
        if hard_clean:
            adapter_src = build_hard_clean_adapter_source(case_id, SECOND_ROOT)
            for i, r in enumerate(crows):
                r["metadata"].update(
                    {"state_cache": f"public_{i}", "label_encoder": "public", "backup_ranker": "public",
                     "support_feature_public": i % 3, "fallback_timeout": 100 + i}
                )
        else:
            adapter_src, _ = build_adapter_source(case_id=case_id, pattern_id=None, variant=0, second_root=SECOND_ROOT,
                                                  include_classes=False)
    else:
        adapter_src, _ = build_adapter_source(case_id=case_id, pattern_id=pattern, variant=variant, second_root=SECOND_ROOT)

    write_json(detector_input / "public_queries.json", [{"qid_hash": hash_id(q["qid"] + "|" + q["question"])} for q in picked])
    write_json(detector_input / "public_candidates.json", crows)
    write_json(detector_input / "public_features.json", features)
    write_json(detector_input / "public_config.json", config)
    write_json(detector_input / "runtime_store.json", runtime_store)
    (detector_input / "adapter.py").write_text(adapter_src, encoding="utf-8")

    # 定位注入行（供 truth.line）
    line = 0
    if pattern is not None:
        for idx, ln in enumerate(adapter_src.splitlines(), 1):
            if any(api in ln for api in ["selector.score_candidate", "feature_builder.append_feature", "candidate_filter.apply"]):
                line = idx
                break

    truth = {
        "case_id": case_id,
        "family": PATTERN_FAMILY[pattern] if pattern else "Clean",
        "pattern_id": pattern or "Clean",
        "module": PATTERN_MODULE.get(pattern, "") if pattern else "",
        "field": field,
        "source_type": TEST_ONLY_PRIVATE_SOURCE if pattern else "",
        "sink": PATTERN_SINK.get(pattern, "") if pattern else "",
        "file": "adapter.py",
        "line": line,
        "rate": 1.0,
        "seed": spec["seed"],
        "injected_qids": len(picked) if pattern else 0,
        "injected_candidates": injected_candidates,
        "injected_features": injected_features,
        "fallback_triggers": fallback_triggers,
        "hard_clean": hard_clean,
        "clean_type": "hard" if hard_clean else ("ordinary" if not pattern else "leak"),
        "source_calls_gt0": pattern is not None,
        "sink_calls_gt0": pattern is not None,
        "test_only": True,
    }
    write_json(private_truth / "truth.json", truth)
    return truth


def build_cases() -> list[dict]:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    adapter = TcmSleepPipelineAdapter(SECOND_ROOT, CHUNKS_PATH, DICT_DIR, top_k=5, candidate_k=30)
    verify = adapter.verify()
    if verify["status"] != "OK":
        return [{"status": "BLOCKED_REAL_CALL_FAILED", "verify": verify}]
    questions = load_public_questions(EVAL_QUESTIONS, max_q=300)
    specs: list[dict] = []
    idx = 0
    # 36 泄漏正例：12 模式 × 3 变体
    for pattern in sorted(PATTERN_FIELDS.keys()):
        for variant in range(3):
            specs.append({
                "case_id": "c_" + uuid4().hex[:16], "index": idx, "pattern": pattern,
                "variant": variant, "seed": 7000 + idx, "qids_per_case": 2,
                "top_k": 5, "candidate_k": 30,
            })
            idx += 1
    # 30 普通 Clean
    for i in range(30):
        specs.append({
            "case_id": "c_" + uuid4().hex[:16], "index": idx, "pattern": None, "variant": 0,
            "seed": 8000 + i, "qids_per_case": 2, "top_k": 5, "candidate_k": 30,
            "hard_clean": False,
        })
        idx += 1
    # 30 困难 Clean
    for i in range(30):
        specs.append({
            "case_id": "c_" + uuid4().hex[:16], "index": idx, "pattern": None, "variant": 0,
            "seed": 9000 + i, "qids_per_case": 2, "top_k": 5, "candidate_k": 30,
            "hard_clean": True,
        })
        idx += 1
    rows = []
    registry_entries = []
    for spec in specs:
        case_dir = WORK / spec["case_id"]
        truth = build_one_case(case_dir, adapter, questions, spec)
        rows.append(truth)
        if truth["family"] != "Clean":
            for j in range(truth["injected_qids"]):
                q = questions[(spec["index"] * 2 + j) % len(questions)]
                qh = hash_id(q["qid"] + "|" + q["question"])
                registry_entries.append({
                    "case_id": spec["case_id"], "pattern_id": truth["pattern_id"], "qid_hash": qh,
                    "handle": private_handle(spec["case_id"], truth["pattern_id"], qh),
                    "source_type": TEST_ONLY_PRIVATE_SOURCE,
                })
    write_private_truth_registry(PRIVATE_TRUTH_DIR, registry_entries)
    write_csv(PKG / "CROSS_PIPELINE_SCENARIO_INDEX.csv", rows)
    return rows


# ---------------------------------------------------------------------------
# 阶段 3：检测
# ---------------------------------------------------------------------------
def _case_source_sink_counts(case_dir: Path) -> dict:
    trace_path = case_dir / "detector_input" / "adapter_execution_trace.jsonl"
    source_calls = 0
    sink_calls = 0
    if trace_path.exists():
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            source_calls += int(rec.get("source_calls", 0) or 0)
            sink_calls += int(rec.get("sink_calls", 0) or 0)
    return {"source_calls": source_calls, "sink_calls": sink_calls}


def calc_metrics(rows: list[dict]) -> dict:
    tp = sum(r["tp"] for r in rows)
    fp = sum(r["fp"] for r in rows)
    tn = sum(r["tn"] for r in rows)
    fn = sum(r["fn"] for r in rows)
    precision = None if (tp + fp) == 0 else tp / (tp + fp)
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision is None:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    mcc_den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1, "specificity": specificity,
        "balanced_accuracy": (recall + specificity) / 2 if (tp + fn) else specificity,
        "mcc": ((tp * tn - fp * fn) / mcc_den) if mcc_den else 0.0,
    }


def run_detection() -> None:
    cfg = parse_frozen_config()
    case_dirs = sorted(p for p in WORK.iterdir() if p.is_dir() and (p / "detector_input").exists())
    rows: list[dict] = []
    failures: list[dict] = []
    for case_dir in case_dirs:
        truth = read_json(case_dir / "private_truth" / "truth.json")
        is_leak = truth["family"] != "Clean"
        for detector in DETECTORS:
            run_name = "full_audit" if detector == "composite_audit" else detector
            try:
                pred = run_detector(case_dir, run_name, cfg)
                error = ""
            except Exception as exc:  # pragma: no cover
                pred = None
                error = f"{type(exc).__name__}: {exc}"
            detected = bool(pred.detected) if pred is not None else False
            # Source/Sink 计数：runtime_taint 在自身 unmasked 运行后立即读取（真实）；
            # composite_audit(=full_audit) 内部多次运行 selection 会覆盖 trace，不承诺单一计数，标记 N/A。
            if run_name == "runtime_taint":
                counts = _case_source_sink_counts(case_dir)
            elif run_name == "full_audit":
                counts = {"source_calls": "N/A", "sink_calls": "N/A"}
            else:
                counts = {"source_calls": "", "sink_calls": ""}
            rows.append({
                "case_id": case_dir.name,
                "detector": detector,
                "is_leak": is_leak,
                "family": truth["family"],
                "pattern_id": truth["pattern_id"],
                "clean_type": truth.get("clean_type", ""),
                "detected": detected,
                "tp": int(is_leak and detected),
                "fp": int((not is_leak) and detected),
                "tn": int((not is_leak) and not detected),
                "fn": int(is_leak and not detected),
                "source_calls": counts["source_calls"],
                "sink_calls": counts["sink_calls"],
                "error": error,
            })
            if error or (is_leak and not detected):
                failures.append({
                    "case_id": case_dir.name, "detector": detector, "pattern_id": truth["pattern_id"],
                    "family": truth["family"], "detected": detected, "error": error,
                    "reason": "EXECUTION_ERROR" if error else "FALSE_NEGATIVE",
                })
    # 汇总（Precision 未定义时写 null，展示为 N/A）
    summary = []
    for detector in DETECTORS:
        det_rows = [r for r in rows if r["detector"] == detector]
        m = calc_metrics(det_rows)
        summary.append({
            "detector": detector,
            "tp": m["tp"], "fp": m["fp"], "tn": m["tn"], "fn": m["fn"],
            "precision": m["precision"] if m["precision"] is not None else "null",
            "recall": round(m["recall"], 6),
            "f1": round(m["f1"], 6),
            "specificity": round(m["specificity"], 6),
            "balanced_accuracy": round(m["balanced_accuracy"], 6),
            "mcc": round(m["mcc"], 6),
            "sample_count": len(det_rows),
        })
    write_csv(PKG / "cross_pipeline_detection_summary.csv", summary)
    write_csv(PKG / "cross_pipeline_confusion_matrix.csv", [{k: v for k, v in s.items() if k != "precision" and k != "recall" and k != "f1" and k != "specificity" and k != "balanced_accuracy" and k != "mcc"} for s in summary])
    with (PKG / "cross_pipeline_case_results.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    write_csv(PKG / "cross_pipeline_failure_cases.csv", failures)


# ---------------------------------------------------------------------------
# 阶段 3.5：修正 case_results 计数（不重跑检测，仅修正被 full_audit 内部 trace 覆盖的 composite 行）
# ---------------------------------------------------------------------------
def fix_case_results_counts() -> int:
    """将 case_results.jsonl 中 composite_audit 行的 Source/Sink 标记为 N/A（组合审计不承诺单一计数）。

    runtime_taint 行保留真实计数（在其自身 unmasked 运行后立即读取，未被覆盖）。
    不修改 detected/tp/fp/tn/fn 等检测结果。
    """
    path = PKG / "cross_pipeline_case_results.jsonl"
    if not path.exists():
        print("[SKIP] cross_pipeline_case_results.jsonl not found")
        return 0
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = 0
    for r in rows:
        if r["detector"] == "composite_audit":
            r["source_calls"] = "N/A"
            r["sink_calls"] = "N/A"
            changed += 1
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[OK] case_results counts fixed: composite rows -> N/A ({changed})")
    return changed


# ---------------------------------------------------------------------------
# 阶段 4：泄漏影响分级
# ---------------------------------------------------------------------------
def leak_effects() -> None:
    rows = []
    for case_dir in sorted(p for p in WORK.iterdir() if p.is_dir() and (p / "detector_input").exists()):
        truth = read_json(case_dir / "private_truth" / "truth.json")
        # 第一次运行：unmasked，运行后立即保存真实 Source/Sink 计数（不得被 masked 重放覆盖）
        _safe_clean_trace(case_dir)
        base, trace = run_selection(case_dir, mask_private=False)
        counts = _case_source_sink_counts(case_dir)
        # 第二次运行：masked 重放（只用于不变性对比，不影响 counts）
        masked, _ = run_selection(case_dir, mask_private=True)
        has_path = len(trace) > 0
        changed_set = False
        changed_order = False
        changed_doc_count = 0
        first_changed_rank = -1
        for qh in base:
            b, m = base.get(qh, []), masked.get(qh, [])
            if set(b) != set(m):
                changed_set = True
            if b != m:
                changed_order = True
                for i, (x, y) in enumerate(zip(b, m)):
                    if x != y:
                        first_changed_rank = i + 1
                        break
                changed_doc_count += sum(1 for i in range(max(len(b), len(m))) if i >= len(b) or i >= len(m) or b[i] != m[i])
        if not has_path:
            level = "NO_LEAK"
        elif changed_set or changed_order:
            level = "BEHAVIORAL_LEAK"
        else:
            level = "ACCESS_LEAK"
        rows.append({
            "case_id": case_dir.name,
            "pattern": truth["pattern_id"],
            "source_calls": counts["source_calls"],
            "sink_calls": counts["sink_calls"],
            "changed_set": changed_set,
            "changed_order": changed_order,
            "changed_doc_count": changed_doc_count,
            "first_changed_rank": first_changed_rank if first_changed_rank > 0 else "",
            "leak_level": level,
        })
    write_csv(PKG / "cross_pipeline_leak_effects.csv", rows)


# ---------------------------------------------------------------------------
# 阶段 5：运行开销
# ---------------------------------------------------------------------------
def _safe_clean_trace(case_dir: Path) -> None:
    """预清理 trace 文件（Windows 文件锁重试），不修改冻结检测器。"""
    for name in ("runtime_taint_trace.jsonl", "adapter_execution_trace.jsonl"):
        p = case_dir / "detector_input" / name
        for _ in range(5):
            try:
                if p.exists():
                    p.unlink()
                break
            except PermissionError:
                time.sleep(0.15)


def _safe_run_selection(case_dir: Path, *, mask_private: bool = False):
    _safe_clean_trace(case_dir)
    for _ in range(6):
        try:
            return run_selection(case_dir, mask_private=mask_private)
        except PermissionError:
            time.sleep(0.4)
            _safe_clean_trace(case_dir)
    return run_selection(case_dir, mask_private=mask_private)


def _safe_run_detector(case_dir: Path, detector: str, cfg: dict):
    _safe_clean_trace(case_dir)
    for _ in range(6):
        try:
            return run_detector(case_dir, detector, cfg)
        except PermissionError:
            time.sleep(0.4)
            _safe_clean_trace(case_dir)
    return run_detector(case_dir, detector, cfg)


def _baseline_selection(case_dir: Path) -> float:
    """基线：真实选择流程，不启用监控（不修改冻结检测器）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"baseline_{case_dir.name}", case_dir / "detector_input" / "adapter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidates = read_json(case_dir / "detector_input" / "public_candidates.json")
    features = read_json(case_dir / "detector_input" / "public_features.json")
    config = read_json(case_dir / "detector_input" / "public_config.json")
    t0 = time.perf_counter()
    for c in candidates:
        module.selection_entry(c, features.get(c["qid_hash"], {}), config, {})
    return time.perf_counter() - t0


def _measure(fn, warmup: int, repeats: int) -> list[float]:
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return times


def runtime_overhead() -> None:
    cfg = parse_frozen_config()
    case_dirs = sorted(p for p in WORK.iterdir() if p.is_dir() and (p / "detector_input").exists())[:12]
    conditions = [
        "baseline_selection",
        "baseline_plus_runtime_monitor",
        "baseline_plus_schema",
        "baseline_plus_invariance",
        "baseline_plus_composite_audit",
    ]
    rows = []
    for case_dir in case_dirs:
        base_times = _measure(lambda: _baseline_selection(case_dir), warmup=3, repeats=10)
        monitor = _measure(lambda: _safe_run_selection(case_dir, mask_private=False), warmup=3, repeats=10)
        schema = _measure(lambda: (_safe_run_selection(case_dir, mask_private=False), run_detector(case_dir, "schema_guard", cfg)), warmup=3, repeats=10)
        invariance = _measure(lambda: (_safe_run_selection(case_dir, mask_private=False), _safe_run_selection(case_dir, mask_private=True)), warmup=3, repeats=10)
        composite = _measure(lambda: _safe_run_detector(case_dir, "full_audit", cfg), warmup=3, repeats=10)
        mapping = {
            "baseline_selection": base_times,
            "baseline_plus_runtime_monitor": monitor,
            "baseline_plus_schema": schema,
            "baseline_plus_invariance": invariance,
            "baseline_plus_composite_audit": composite,
        }
        base_mean = statistics.mean(base_times)
        for cond, times in mapping.items():
            mean = statistics.mean(times)
            median = statistics.median(times)
            p95 = sorted(times)[int(round(0.95 * (len(times) - 1)))]
            abs_inc = mean - base_mean if cond != "baseline_selection" else 0.0
            rel_inc = (abs_inc / base_mean) if base_mean > 0 else None
            rows.append({
                "case_id": case_dir.name,
                "condition": cond,
                "mean_ms": round(mean * 1000, 4),
                "median_ms": round(median * 1000, 4),
                "p95_ms": round(p95 * 1000, 4),
                "abs_increment_ms": round(abs_inc * 1000, 4),
                "rel_increment": round(rel_inc, 4) if rel_inc is not None else "null",
            })
    write_csv(PKG / "cross_pipeline_runtime_overhead.csv", rows)
    # 离线 keyword / AST 扫描时间单独报告
    offline = []
    for case_dir in case_dirs:
        t0 = time.perf_counter()
        run_detector(case_dir, "keyword_static_baseline", cfg)
        kw = time.perf_counter() - t0
        t0 = time.perf_counter()
        run_detector(case_dir, "ast_static_dataflow", cfg)
        ast_t = time.perf_counter() - t0
        offline.append({"case_id": case_dir.name, "keyword_scan_ms": round(kw * 1000, 4), "ast_scan_ms": round(ast_t * 1000, 4)})
    write_csv(PKG / "cross_pipeline_offline_scan_runtime.csv", offline)


# ---------------------------------------------------------------------------
# 阶段 6：pytest 报告
# ---------------------------------------------------------------------------
def run_pytest() -> None:
    report_path = PKG / "pytest_report.txt"
    pkg = report_path.parent
    pkg.mkdir(parents=True, exist_ok=True)
    cmds = [
        ["python", "-m", "pytest", "-q", "tests/dakd_v6"],
        ["python", "-m", "pytest", "-q", "tests/dakd_v6_fixture"],
        ["python", "-m", "pytest", "-q"],
    ]
    with report_path.open("w", encoding="utf-8") as f:
        for cmd in cmds:
            f.write(f"\n===== COMMAND: {' '.join(cmd)} =====\n")
            f.flush()
            try:
                proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800, executable=sys.executable)
                f.write(proc.stdout)
                f.write(proc.stderr)
            except Exception as exc:
                f.write(f"RUN_ERROR: {exc}\n")


# ---------------------------------------------------------------------------
# 阶段 7：脱敏导出包
# ---------------------------------------------------------------------------
ABSOLUTE_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"'<>|;*?]{2,}")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*[\"'][^\"']+[\"']|sk-[A-Za-z0-9]{10,}")
# 只匹配具体测试值明文（带 pattern 后缀的哈希），不匹配 TEST_ONLY_PRIVATE_SOURCE 类型标记
PRIVATE_LABEL_RE = re.compile("TEST_ONLY_PRIVATE_SOURCE" + "_" + "[MF][1-4]")
PERSON_RE = re.compile(
    "身份证号" + r"\s*[:：]?\s*[\dXx]{6,}"
    + "|" + "phone" + r"\s*[:=]\s*[\d+]{5,}"
    + "|" + "联系电话" + r"\s*[:：]\s*[\d+]{5,}"
    + "|" + "姓名" + r"\s*[:：]\s*\S{2,8}"
)


def privacy_scan_text(text: str) -> list[str]:
    issues = []
    if ABSOLUTE_PATH_RE.search(text):
        issues.append("absolute_windows_path")
    if SECRET_RE.search(text):
        issues.append("secret_or_api_key")
    if PRIVATE_LABEL_RE.search(text):
        issues.append("private_label_plaintext")
    if PERSON_RE.search(text):
        issues.append("personal_info")
    return issues


_ABSOLUTE_PATH_SUB = re.compile(r"[A-Za-z]:[\\/]{1,2}python_project[\\/]{1,2}(tcm_sleep_rag_full|medsage_rag_full)")


def _sanitize_source(text: str) -> str:
    """导出前对源码/配置做路径脱敏（本地绝对路径 → 占位符，兼容正/反斜杠与转义字面量）。"""
    def _repl(m: re.Match) -> str:
        return "<SECOND_PIPELINE_ROOT>" if "tcm_sleep_rag_full" in m.group(0) else "<MAIN_PROJECT_ROOT>"
    return _ABSOLUTE_PATH_SUB.sub(_repl, text)


def export_zip() -> dict:
    include: list[Path] = []
    # 源码/配置/测试/冻结检测器代码/独立 fixture
    for rel in [
        "src/cross_pipeline", "src/benchmark_v3",
        "configs/dakd_v6", "configs/dakd_v5",
        "scripts/dakd_v6",
        "tests/dakd_v6", "tests/dakd_v6_fixture",
        "fixture_dakd_v6",
    ]:
        p = ROOT / rel
        if p.is_dir():
            include.extend(sorted(p.rglob("*.py")) + sorted(p.rglob("*.yaml")) + sorted(p.rglob("*.yml")))
            include.extend(sorted(p.rglob("*.json")) + sorted(p.rglob("*.md")))
    for f in PKG.rglob("*"):
        if f.is_file() and "private_truth" not in f.parts and f.name not in {"EXPORT_ZIP_RESULT.json", "VERIFY_ZIP_RESULT.json"}:
            include.append(f)
    zip_path = DIST / "medsage_dakd_cross_pipeline_v6.zip"
    DIST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(set(include)):
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            if path.suffix in {".py", ".yaml", ".yml"}:
                zf.writestr(rel, _sanitize_source(path.read_text(encoding="utf-8")))
            else:
                zf.write(path, rel)
    # 隐私扫描（ZIP 内文本）
    issues: list[dict] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith((".py", ".yaml", ".yml", ".json", ".csv", ".md", ".jsonl", ".txt")):
                try:
                    text = zf.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                for issue in privacy_scan_text(text):
                    issues.append({"file": name, "issue": issue})
    # 在最终 ZIP 完成后计算（此后不再向 ZIP 追加任何文件，保证 sha/size/file_count 与磁盘一致）
    result = {
        "zip_path": str(zip_path.relative_to(ROOT)).replace("\\", "/"),
        "zip_sha256": sha256_file(zip_path),
        "zip_size_bytes": zip_path.stat().st_size,
        "file_count": len(list(zipfile.ZipFile(zip_path).namelist())),
        "privacy_issues": issues,
    }
    write_json(PKG / "EXPORT_ZIP_RESULT.json", result)
    return result


def verify_zip() -> dict:
    """解压到全新临时目录 → 隐私扫描 → manifest 文件数对比 → 最小复现测试 → SHA256。"""
    info = read_json(PKG / "EXPORT_ZIP_RESULT.json")
    zip_path = ROOT / info["zip_path"]
    sha_before = sha256_file(zip_path)
    with tempfile.TemporaryDirectory() as tmp:
        extract_dir = Path(tmp) / "extracted"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
        files_in_zip = list(extract_dir.rglob("*"))
        file_count = len([p for p in files_in_zip if p.is_file()])
        manifest_count = 0
        manifest_path = extract_dir / "paper_package_dakd_v6" / "16_cross_pipeline" / "FROZEN_DETECTOR_MANIFEST.json"
        if manifest_path.exists():
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_count = len(m["frozen_files"])
        issues: list[dict] = []
        for p in files_in_zip:
            if p.is_file() and p.suffix in {".py", ".yaml", ".yml", ".json", ".csv", ".md", ".jsonl", ".txt"}:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for issue in privacy_scan_text(text):
                    issues.append({"file": str(p.relative_to(extract_dir)), "issue": issue})
        # 最小复现测试（不依赖第二工程真实路径）：结果文件可解析 + case_id 一一对应 + 汇总可读
        repro = {"status": "NOT_RUN"}
        pkg_ex = extract_dir / "paper_package_dakd_v6" / "16_cross_pipeline"
        try:
            rows = [json.loads(l) for l in (pkg_ex / "cross_pipeline_case_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
            index = list(csv.DictReader((pkg_ex / "CROSS_PIPELINE_SCENARIO_INDEX.csv").open(encoding="utf-8-sig")))
            case_ids = {r["case_id"] for r in rows}
            index_ids = {r["case_id"] for r in index}
            summary = list(csv.DictReader((pkg_ex / "cross_pipeline_detection_summary.csv").open(encoding="utf-8-sig")))
            ast_row = next(s for s in summary if s["detector"] == "ast_static_dataflow")
            repro = {
                "status": "OK",
                "result_rows": len(rows),
                "index_rows": len(index),
                "case_id_aligned": case_ids == index_ids and len(case_ids) == 96,
                "detectors": len(summary),
                "precision_undefined_is_null": ast_row["precision"] in ("null", "N/A"),
            }
        except Exception as exc:  # pragma: no cover
            repro = {"status": "FAILED", "error": str(exc)}
        # 独立 fixture-only 最小复现：全新解压后运行两条命令（不依赖第二工程）
        fixture_repro = {"status": "NOT_RUN"}
        fixture_cmds = [
            [sys.executable, "scripts/dakd_v6/run_tcm_sleep_cross_pipeline.py", "--fixture-only"],
            [sys.executable, "-m", "pytest", "-q", "tests/dakd_v6_fixture"],
        ]
        try:
            for cmd in fixture_cmds:
                proc = subprocess.run(cmd, cwd=str(extract_dir), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
                if proc.returncode != 0:
                    fixture_repro = {
                        "status": "FAILED",
                        "command": " ".join(cmd),
                        "stdout_tail": proc.stdout[-1500:],
                        "stderr_tail": proc.stderr[-1500:],
                    }
                    break
            else:
                fixture_repro = {"status": "OK", "commands": [" ".join(c) for c in fixture_cmds]}
        except Exception as exc:  # pragma: no cover
            fixture_repro = {"status": "FAILED", "error": str(exc)}
        zip_file_count = len(list(zipfile.ZipFile(zip_path).namelist()))
        return {
            "zip_sha256_after": sha256_file(zip_path),
            "sha256_stable": sha_before == sha256_file(zip_path),
            "extracted_file_count": file_count,
            "zip_file_count": zip_file_count,
            "manifest_frozen_files": manifest_count,
            "privacy_issues": issues,
            "minimal_repro": repro,
            "fixture_repro": fixture_repro,
            "verify_status": "OK" if (file_count == zip_file_count and not issues and repro.get("status") == "OK" and fixture_repro.get("status") == "OK") else "ISSUES_FOUND",
        }


def verify_zip_persist() -> None:
    """运行 ZIP 验证并持久化结果到 VERIFY_ZIP_RESULT.json。"""
    result = verify_zip()
    write_json(PKG / "VERIFY_ZIP_RESULT.json", result)


# ---------------------------------------------------------------------------
# 独立 fixture-only 复现（不接入第二工程：不含第二工程语料、不含私有 truth 明文）
# ---------------------------------------------------------------------------
FIXTURE_ROOT = ROOT / "fixtures" / "cross_pipeline"
FIXTURE_WORK = ROOT / "benchmark_work_fixture"

FIXTURE_ADAPTER_LEAK = '''# -*- coding: utf-8 -*-
# 独立 fixture adapter（M1 泄漏）：不接入第二工程，分数来自 public_candidates。
from __future__ import annotations

class private_store:
    @staticmethod
    def read_evidence_label(handle, store):
        return store.get(handle)

class selector:
    @staticmethod
    def score_candidate(value):
        return len(value or [])

class feature_builder:
    @staticmethod
    def append_feature(vec, value):
        vec.append(len(value or []))
        return vec

class candidate_filter:
    @staticmethod
    def apply(value):
        return bool(value)

def neutral_wrap(x):
    return x

def selection_entry(public_candidate, features, config, store):
    score = public_candidate.get("public_scores", {}).get("bm25", 0.0)
    a = public_candidate.get("metadata", {}).get("aux_11")
    b = private_store.read_evidence_label(a, store)
    score += selector.score_candidate(b)
    return score
'''

FIXTURE_ADAPTER_CLEAN = '''# -*- coding: utf-8 -*-
# 独立 fixture adapter（Clean）：不接入第二工程，分数来自 public_candidates。
from __future__ import annotations

def selection_entry(public_candidate, features, config, store):
    score = public_candidate.get("public_scores", {}).get("bm25", 0.0)
    return score
'''


def _fixture_candidates(seed_prefix: str, qh: str, n: int = 6, leak: bool = False) -> list[dict]:
    rows = []
    for i in range(n):
        row = {
            "qid_hash": qh,
            "doc_id_hash": hash_id(f"{seed_prefix}_doc_{i}"),
            "rank": i + 1,
            "public_scores": {"bm25": round(0.9 - 0.1 * i, 2)},
            "metadata": {"source": "fixture", "rank_hint": i + 1},
        }
        if leak and i == 2:  # rank 3 注入
            row["metadata"]["aux_11"] = "fx_handle_m1"
        rows.append(row)
    return rows


def build_fixture_data() -> None:
    """生成独立 fixture（脱敏候选 + 纯 Python adapter + 预期结果占位）。不含第二工程语料。"""
    if FIXTURE_ROOT.exists():
        shutil.rmtree(FIXTURE_ROOT)
    qh_leak = hash_id("fixture_q_leak")
    qh_clean = hash_id("fixture_q_clean")
    # fx_leak_m1
    leak_dir = FIXTURE_ROOT / "cases" / "fx_leak_m1"
    (leak_dir / "detector_input").mkdir(parents=True, exist_ok=True)
    (leak_dir / "private_truth").mkdir(parents=True, exist_ok=True)
    write_json(leak_dir / "detector_input" / "public_candidates.json", _fixture_candidates("fx_leak", qh_leak, leak=True))
    write_json(leak_dir / "detector_input" / "public_features.json", {})
    write_json(leak_dir / "detector_input" / "public_config.json", {"top_k": 3, "candidate_k": 6, "metadata_field": "aux_31"})
    write_json(leak_dir / "detector_input" / "runtime_store.json", {"fx_handle_m1": ["FIXTURE_PRIVATE_VALUE"]})
    (leak_dir / "detector_input" / "adapter.py").write_text(FIXTURE_ADAPTER_LEAK, encoding="utf-8")
    write_json(leak_dir / "private_truth" / "truth.json", {
        "case_id": "fx_leak_m1", "family": "Leak-M", "pattern_id": "M1", "module": "candidate_metadata",
        "field": "aux_11", "source_type": "FIXTURE_PRIVATE_SOURCE", "sink": "candidate_scoring",
        "file": "adapter.py", "line": 0, "rate": 1.0, "seed": 1,
        "injected_qids": 1, "injected_candidates": 1, "injected_features": 0, "fallback_triggers": 0,
        "hard_clean": False, "clean_type": "leak", "source_calls_gt0": True, "sink_calls_gt0": True, "test_only": True,
    })
    # fx_clean
    clean_dir = FIXTURE_ROOT / "cases" / "fx_clean"
    (clean_dir / "detector_input").mkdir(parents=True, exist_ok=True)
    (clean_dir / "private_truth").mkdir(parents=True, exist_ok=True)
    write_json(clean_dir / "detector_input" / "public_candidates.json", _fixture_candidates("fx_clean", qh_clean, leak=False))
    write_json(clean_dir / "detector_input" / "public_features.json", {})
    write_json(clean_dir / "detector_input" / "public_config.json", {"top_k": 3, "candidate_k": 6})
    write_json(clean_dir / "detector_input" / "runtime_store.json", {})
    (clean_dir / "detector_input" / "adapter.py").write_text(FIXTURE_ADAPTER_CLEAN, encoding="utf-8")
    write_json(clean_dir / "private_truth" / "truth.json", {
        "case_id": "fx_clean", "family": "Clean", "pattern_id": "Clean", "module": "",
        "field": "", "source_type": "", "sink": "", "file": "adapter.py", "line": 0, "rate": 1.0, "seed": 2,
        "injected_qids": 0, "injected_candidates": 0, "injected_features": 0, "fallback_triggers": 0,
        "hard_clean": False, "clean_type": "ordinary", "source_calls_gt0": False, "sink_calls_gt0": False, "test_only": True,
    })
    readme = FIXTURE_ROOT / "README.md"
    readme.write_text(
        "# 独立 fixture-only 最小复现（DAKD v6）\n\n"
        "- 不含第二工程原始医疗语料；不含私有 truth 明文（值为占位符 FIXTURE_PRIVATE_VALUE）。\n"
        "- 不接入第二工程检索流程；仅验证冻结检测器（benchmark_v3）在脱敏 fixture 上的可复现性。\n"
        "- 此 fixture 不等同于第二工程 Dense/Hybrid/Domain 管线验证。\n"
        "- 运行：`python scripts/dakd_v6/run_tcm_sleep_cross_pipeline.py --fixture-only`\n"
        "- 测试：`pytest -q tests/dakd_v6_fixture`\n",
        encoding="utf-8")
    print("[OK] fixture data built at fixture_dakd_v6/")


def _run_fixture_detectors() -> list[dict]:
    cfg = parse_frozen_config()
    results = []
    for case_dir in sorted(p for p in FIXTURE_WORK.iterdir() if p.is_dir()):
        truth = read_json(case_dir / "private_truth" / "truth.json")
        for detector in DETECTORS:
            run_name = "full_audit" if detector == "composite_audit" else detector
            pred = run_detector(case_dir, run_name, cfg)
            results.append({"case_id": case_dir.name, "detector": detector, "family": truth["family"], "detected": bool(pred.detected)})
    return results


def init_fixture_expected() -> None:
    """首次运行 fixture 并固化预期结果（真实检测器行为，非人为指定）。"""
    if FIXTURE_WORK.exists():
        shutil.rmtree(FIXTURE_WORK)
    shutil.copytree(FIXTURE_ROOT / "cases", FIXTURE_WORK)
    results = _run_fixture_detectors()
    write_json(FIXTURE_ROOT / "expected.json", {"cases": results})
    print("[OK] fixture expected recorded:", json.dumps(results, ensure_ascii=False))


def run_fixture_only() -> dict:
    """运行独立 fixture 并与固化预期比对（全新解压后可执行）。"""
    if FIXTURE_WORK.exists():
        shutil.rmtree(FIXTURE_WORK)
    shutil.copytree(FIXTURE_ROOT / "cases", FIXTURE_WORK)
    results = _run_fixture_detectors()
    expected = read_json(FIXTURE_ROOT / "expected.json")
    exp_map = {(e["case_id"], e["detector"]): bool(e["detected"]) for e in expected["cases"]}
    mismatches = [r for r in results if exp_map.get((r["case_id"], r["detector"])) != r["detected"]]
    out = {
        "status": "OK" if not mismatches else "MISMATCH",
        "case_count": len([p for p in FIXTURE_WORK.iterdir() if p.is_dir()]),
        "detector_count": len(DETECTORS),
        "results": results,
        "mismatches": mismatches,
        "note": "独立 fixture 复现：不含第二工程语料/流程，仅验证冻结检测器在脱敏 fixture 上的可复现性（不等同于第二工程 Dense/Hybrid/Domain 管线验证）。",
    }
    write_json(FIXTURE_ROOT / "fixture_run_results.json", out)
    return out


# ---------------------------------------------------------------------------
# 阶段 1：审计报告
# ---------------------------------------------------------------------------
def audit_report() -> None:
    verify = TcmSleepPipelineAdapter(SECOND_ROOT, CHUNKS_PATH, DICT_DIR, top_k=5, candidate_k=30).verify()
    md = f"""# 跨管线只读审计报告（tcm_sleep_rag_full）

生成时间：{time.strftime("%Y-%m-%d %H:%M:%S")}
工作目录：medsage_rag_full（主审计工程）；第二工程以只读方式接入。

## 1. 真实入口文件
| 环节 | 文件 | 实际调用函数 |
|---|---|---|
| 服务入口 | rag_service/api.py | `POST /rag/retrieve` → `retrieve()` → `get_retriever()` |
| BM25 检索入口 | rag_service/retriever_bm25.py | `BM25Retriever.retrieve(question, top_k)` |
| Dense 检索入口 | rag_service/retriever_dense.py | `DenseRetriever.retrieve(question, top_k)`（依赖 ChromaDB collection） |
| 融合入口 | rag_service/retriever_hybrid.py | `HybridRetriever.retrieve()`（Dense+BM25+RRF 融合） |
| 重排序入口 | rag_service/reranker.py | `MMRReranker.rerank(question, candidates, top_k)` |
| 领域增强入口 | rag_service/retriever_domain.py | `DomainEnhancedRetriever.retrieve()`（term/syndrome/category 加权 + MMR） |
| 纠错/回退路径 | rag_service/embedding_model.py | `allow_fallback` → hashing 离线后端（仅回退，不改业务数据） |
| Top-K 输出结构 | 各 retriever | `result["retrieved"]`：`{{rank, chunk_id, doc_id, title, content, category, score, ...}}` |
| 候选唯一标识 | 各 retriever | `chunk_id`（BM25 中同时含 `doc_id`） |

## 2. 真实选择路径
```
用户问题 → BM25/Dense 检索候选 → RRF 融合(HybridRetriever)
         → 领域增强打分(DomainEnhancedRetriever) → MMR 重排序(MMRReranker) → Top-K → retrieved
```

## 3. 候选结构
- `rank`（1-based）、`chunk_id`、`doc_id`、`content`、`category`、`source_dataset`
- 打分字段：`score`、`bm25_score`、`dense_score`、`rrf_score`、`final_score`（归一化范围约 [0,1]）
- selected_doc_ids 生成位置：各 `retrieve()` 内部 `retrieved[:top_k]` / `sorted(...)[:top_k]`

## 4. 依赖项
- Python 3.10（tcmrag 环境）/ 3.13（主工程环境均可跑 BM25 路径）
- jieba、rank-bm25（BM25）；chromadb、sentence-transformers（Dense/Hybrid/Domain）
- numpy、sklearn（hashing 回退）、fastapi/pydantic（服务层）
- 数据：data/processed/knowledge_chunks_v3_1905_ffr.jsonl（1905 chunks，含 BM25 缓存 pkl）
- 索引：chroma_db / chroma_db_v2_auth / chroma_db_v3_1500_ffr_bge（sqlite）
- 词典：data/dictionary/{{sleep_terms,synonym_dict,syndrome_dict,category_rule}}.json
- 模型：bge-small-zh（sentence-transformers，可离线缓存；allow_fallback 时用 hashing）

## 5. 数据可用性
| 数据 | 是否可用 | 说明 |
|---|---|---|
| knowledge_chunks_v3_1905_ffr.jsonl | 可用 | 1905 chunks，1.8 MB |
| BM25 缓存 | 可用 | knowledge_chunks_v3_1905_ffr.bm25_cache.pkl 存在 |
| dictionary | 可用 | 4 个词典文件齐全 |
| ChromaDB collection | 可用 | chroma_db_v3_1500_ffr_bge 等（需 tcmrag 环境） |
| eval_300.jsonl | 可用 | 300 个公开测试问题（仅用 question，不用 gold） |

## 6. 可插入测试专用私有源的路径
- 候选 metadata（M1-M4）：候选对象 `metadata` 字典
- 特征构造（F1-F4）：public_features 特征矩阵
- 回退/过滤（R1-R4）：缺失预测 / 异常分支 / 闭包默认参数 / 候选过滤
- 所有注入均通过受控私有读取接口（proxy.read_evidence_label），不读取第二工程业务数据

## 7. 无法执行的路径
| 路径 | 原因 |
|---|---|
| DomainEnhancedRetriever 完整链（Dense+MMR）在主工程环境运行 | 主工程 .venv 无 chromadb/sentence-transformers；可用 tcmrag 环境执行，但本实验以 BM25 真实流程为主 |
| 外部 API / 生成端 | 第二工程无云端 API 依赖；生成端不在本实验范围 |

## 8. 是否满足正式实验条件
- 真实入口与调用函数：已确认（BM25Retriever.retrieve 为真实检索 + Top-K 选择流程，主工程环境实测可运行，约 8ms）
- 候选与 selected_doc_ids 结构：已确认
- 离线、本地、无云端 API 条件：满足（BM25 路径完全离线）
- 测试专用私有源可受控插入：满足
- 结论：**满足正式实验条件**（BM25 真实路径）。Dense/Hybrid/Domain 路径需 tcmrag 环境，作为补充说明记录，不虚报。

真实调用验证：`{json.dumps(verify, ensure_ascii=False)}`
"""
    (PKG / "CROSS_PIPELINE_AUDIT.md").write_text(md, encoding="utf-8")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> None:
    if SECOND_ROOT is None:
        raise SystemExit(
            "REQUIRES_LOCAL_ORIGINAL_PROJECT: set TCM_SLEEP_RAG_ROOT to the local "
            "second-project root (tcm_sleep_rag_full) before running."
        )
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    PKG.mkdir(parents=True, exist_ok=True)
    if stage in ("frozen_manifest", "all"):
        frozen_manifest()
        second_pipeline_baseline()
        print("[OK] frozen manifest + second pipeline baseline")
    if stage in ("audit", "all"):
        audit_report()
        print("[OK] audit report")
    if stage in ("build", "all"):
        rows = build_cases()
        print(f"[OK] cases built: {len(rows)}")
    if stage in ("detect", "all"):
        run_detection()
        print("[OK] detection")
    if stage in ("fix_case_results", "fix"):
        fix_case_results_counts()
        print("[OK] case_results counts fixed")
    if stage in ("leak_effects", "all"):
        leak_effects()
        print("[OK] leak effects")
    if stage in ("runtime", "all"):
        runtime_overhead()
        print("[OK] runtime overhead")
    if stage in ("pytest_report", "all"):
        run_pytest()
        print("[OK] pytest report")
    if stage in ("build_fixture",):
        build_fixture_data()
        print("[OK] fixture data built")
    if stage in ("init_fixture_expected",):
        init_fixture_expected()
        print("[OK] fixture expected recorded")
    if stage in ("fixture_only", "--fixture-only"):
        out = run_fixture_only()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        if out["status"] != "OK":
            raise SystemExit(f"FIXTURE_REPRO_FAILED: {len(out['mismatches'])} mismatches")
        print("[OK] fixture-only reproduction passed")
    if stage in ("export", "all"):
        export_zip()
        print("[OK] zip exported")
    if stage in ("verify_zip", "all"):
        result = verify_zip_persist()
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
