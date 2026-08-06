# -*- coding: utf-8 -*-
"""TEST_ONLY_PRIVATE_SOURCE —— 跨管线受控泄漏验证的合成私有测试源。

约束（见任务书第三、五节）：
- 该值仅用于验证"私有值能否经数据流进入证据选择"，不构成 EvidenceGold / QueryGold；
- 不计算 DemandCov、NDCG 或任何医学检索效果指标；
- 不混入 tcm_sleep_rag_full 的真实业务数据；
- 明文不出现在脱敏导出包中。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

TEST_ONLY_PRIVATE_SOURCE = "TEST_ONLY_PRIVATE_SOURCE"


def _tag(case_id: str, pattern_id: str, qid_hash: str) -> str:
    return hashlib.sha256(f"{case_id}|{pattern_id}|{qid_hash}".encode("utf-8")).hexdigest()[:12]


def synthetic_private_value(case_id: str, pattern_id: str, qid_hash: str) -> list[str]:
    """生成确定性的测试专用私有值（仅用于数据传播验证，非医学真值）。"""
    return [f"{TEST_ONLY_PRIVATE_SOURCE}_{pattern_id}_{_tag(case_id, pattern_id, qid_hash)}"]


def private_handle(case_id: str, pattern_id: str, qid_hash: str) -> str:
    """生成私有 store 的受控读取句柄（检测器运行时通过 proxy 读取具体值）。"""
    return "tst_" + hashlib.sha256(f"{case_id}|{pattern_id}|{qid_hash}".encode("utf-8")).hexdigest()[:14]


def write_private_truth_registry(out_dir: Path, entries: list[dict[str, Any]]) -> Path:
    """将测试私有源注册表写入 private_truth/（本地保留，不进脱敏导出包）。

    检测器运行时不会读取该目录；只有实验脚本通过 synthetic_private_value /
    private_handle 接口访问具体测试值。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "synthetic_private_truth_registry.json"
    payload = {
        "marker": TEST_ONLY_PRIVATE_SOURCE,
        "note": "TEST-ONLY synthetic private source registry for cross-pipeline validation. "
                "Not EvidenceGold, not QueryGold, no medical retrieval metrics are derived from it.",
        "entries": entries,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
