# -*- coding: utf-8 -*-
"""跨管线只读适配器：真实调用 tcm_sleep_rag_full 的检索与 Top-K 选择流程。

约束（见任务书第二、五节）：
- 只读接入 tcm_sleep_rag_full：不修改、不移动、不删除第二工程任何文件；
- 适配器必须调用第二工程原有真实流程（BM25Retriever.retrieve 等），
  禁止简化排序器冒充、禁止固定输出模拟 selected_doc_ids；
- 每个 case 生成的 adapter.py 被冻结检测器（benchmark_v3.isolated_runner）
  加载执行，泄漏注入只通过受控私有读取接口进行。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

TEST_ONLY_SOURCE_TYPE = "TEST_ONLY_PRIVATE_SOURCE"

# 12 类泄漏模式 → 注入字段名（每模式 3 个受控变异）
PATTERN_FIELDS: dict[str, list[str]] = {
    "M1": ["aux_11", "aux_12", "aux_13"],
    "M2": ["aux_17", "aux_18", "aux_19"],
    "M3": ["aux_23", "aux_24", "aux_25"],
    "M4": ["aux_31", "aux_32", "aux_33"],
    "F1": ["aux_41", "aux_42", "aux_43"],
    "F2": ["aux_45", "aux_46", "aux_47"],
    "F3": ["aux_49", "aux_50", "aux_51"],
    "F4": ["aux_53", "aux_54", "aux_55"],
    "R1": ["aux_61", "aux_62", "aux_63"],
    "R2": ["aux_67", "aux_68", "aux_69"],
    "R3": ["aux_71", "aux_72", "aux_73"],
    "R4": ["aux_75", "aux_76", "aux_77"],
}

PATTERN_SINK: dict[str, str] = {
    "M1": "candidate_scoring", "M2": "candidate_scoring", "M3": "candidate_scoring", "M4": "candidate_scoring",
    "F1": "feature_matrix", "F2": "feature_matrix", "F3": "feature_matrix", "F4": "feature_matrix",
    "R1": "fallback_selection", "R2": "fallback_selection", "R3": "fallback_selection", "R4": "candidate_filter",
}

PATTERN_MODULE: dict[str, str] = {
    "M1": "candidate_metadata", "M2": "candidate_metadata", "M3": "cache_layer", "M4": "config",
    "F1": "feature_matrix", "F2": "feature_matrix", "F3": "feature_matrix", "F4": "cache_layer",
    "R1": "fallback_selector", "R2": "exception_fallback", "R3": "closure_default", "R4": "candidate_filter",
}

PATTERN_FAMILY: dict[str, str] = {
    "M1": "Leak-M", "M2": "Leak-M", "M3": "Leak-M", "M4": "Leak-M",
    "F1": "Leak-F", "F2": "Leak-F", "F3": "Leak-F", "F4": "Leak-F",
    "R1": "Leak-R", "R2": "Leak-R", "R3": "Leak-R", "R4": "Leak-R",
}

ALL_PATTERNS = list(PATTERN_FIELDS.keys())


def hash_id(value: str) -> str:
    """与主工程冻结检测器一致的 doc/qid 哈希格式（h_ + sha256 前 16 位）。"""
    return "h_" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


class TcmSleepPipelineAdapter:
    """只读封装：真实调用 tcm_sleep_rag_full 的 BM25 检索与 Top-K 选择流程。"""

    def __init__(
        self,
        second_root: str | Path,
        chunks_path: str | Path,
        dict_dir: str | Path,
        top_k: int = 5,
        candidate_k: int = 30,
    ) -> None:
        self.second_root = Path(second_root)
        self.chunks_path = str(chunks_path)
        self.dict_dir = str(dict_dir)
        self.top_k = top_k
        self.candidate_k = candidate_k
        self._retriever = None

    def _ensure_importable(self) -> None:
        root = str(self.second_root)
        if root not in sys.path:
            sys.path.insert(0, root)

    def _get_retriever(self):
        if self._retriever is None:
            self._ensure_importable()
            from rag_service.retriever_bm25 import BM25Retriever  # 第二工程真实检索器

            self._retriever = BM25Retriever(chunks_path=self.chunks_path, dict_dir=self.dict_dir)
        return self._retriever

    def verify(self) -> dict[str, Any]:
        """验证真实调用链可用（不修改第二工程任何文件）。"""
        try:
            res = self._get_retriever().retrieve("失眠应该怎么调理", top_k=5)
            items = res.get("retrieved", [])
            return {
                "status": "OK" if items else "EMPTY",
                "method": res.get("method", "bm25"),
                "retrieved_count": len(items),
                "latency_ms": res.get("retrieval_latency_ms"),
                "sample_chunk_id": items[0].get("chunk_id") if items else None,
            }
        except Exception as exc:  # pragma: no cover
            return {"status": "FAILED", "error": str(exc)}

    def retrieve_candidates(self, question: str, candidate_k: int | None = None) -> list[dict[str, Any]]:
        """真实调用第二工程 BM25 检索获取候选（含真实分数）。"""
        result = self._get_retriever().retrieve(question, top_k=candidate_k or self.candidate_k)
        out: list[dict[str, Any]] = []
        for item in result.get("retrieved", []):
            out.append({
                "rank": int(item.get("rank", 0) or 0),
                "chunk_id": str(item.get("chunk_id", "")),
                "doc_id": str(item.get("doc_id", "")),
                "content_hash": hash_id(str(item.get("content", ""))),
                "bm25_score": float(item.get("bm25_score", 0.0) or 0.0),
            })
        return out

    def run_real_selection(self, question: str, top_k: int | None = None) -> list[str]:
        """真实调用第二工程 Top-K 选择流程，返回 selected_doc_id（哈希）。"""
        result = self._get_retriever().retrieve(question, top_k=top_k or self.top_k)
        return [hash_id(str(item.get("chunk_id", ""))) for item in result.get("retrieved", [])]


# ---------------------------------------------------------------------------
# 案例 adapter.py 生成（冻结检测器加载执行的单元）
# ---------------------------------------------------------------------------

_ADAPTER_HEADER = '''# -*- coding: utf-8 -*-
# Cross-pipeline adapter: 真实调用 tcm_sleep_rag_full 的 BM25 检索 + Top-K 选择流程。
# case={case_id} pattern={pattern_id} 只读接入，不修改第二工程。
from __future__ import annotations
import hashlib
import json
import sys

SECOND_PIPELINE_ROOT = "{second_root}"
if SECOND_PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, SECOND_PIPELINE_ROOT)

from rag_service.retriever_bm25 import BM25Retriever  # 第二工程真实流程入口
'''

_ADAPTER_CLASSES = '''
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

def neutral_wrap2(x):
    return neutral_wrap(x)
'''

_ADAPTER_REAL = '''
_retriever = None
_real_scores_cache = {}


def _doc_hash(value):
    return "h_" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def _real_bm25_scores(config):
    """真实调用第二工程 BM25Retriever.retrieve：检索候选 + 归一化打分 + Top-K 排序。"""
    global _retriever
    key = config.get("chunks_path", "")
    if key in _real_scores_cache:
        return _real_scores_cache[key]
    if _retriever is None:
        _retriever = BM25Retriever(chunks_path=config.get("chunks_path"), dict_dir=config.get("dict_dir"))
    result = _retriever.retrieve(config.get("question", ""), top_k=int(config.get("candidate_k", 30)))
    mapping = {}
    for item in result.get("retrieved", []):
        mapping[_doc_hash(str(item.get("chunk_id", "")))] = (
            int(item.get("rank", 0) or 0),
            float(item.get("bm25_score", 0.0) or 0.0),
        )
    _real_scores_cache[key] = mapping
    return mapping
'''

_SELECTION_HEAD = '''


def selection_entry(public_candidate, features, config, store):
    score = _real_bm25_scores(config).get(public_candidate.get("doc_id_hash", ""), (0, 0.0))[1]
'''

_SELECTION_TAIL = '''
    return score
'''

# 每模式 3 个受控变体（字段/包装结构不同，调用相同的冻结 sink API）
_INJECTION_BODIES: dict[str, list[str]] = {
    "M1": [
        "    a = public_candidate.get('metadata', {}).get('{field}')\n    b = private_store.read_evidence_label(a, store)\n    score += selector.score_candidate(b)",
        "    a = public_candidate.get('metadata', {}).get('{field}')\n    v = private_store.read_evidence_label(a, store)\n    score += selector.score_candidate(v)",
        "    handle = public_candidate.get('metadata', {}).get('{field}')\n    val = private_store.read_evidence_label(handle, store)\n    score += selector.score_candidate(val)",
    ],
    "M2": [
        "    z0 = public_candidate.get('metadata', {}).get('{field}')\n    z1 = z0\n    z2 = private_store.read_evidence_label(z1, store)\n    score += selector.score_candidate(z2)",
        "    z0 = public_candidate.get('metadata', {}).get('{field}')\n    z1 = neutral_wrap(z0)\n    z2 = private_store.read_evidence_label(z1, store)\n    score += selector.score_candidate(z2)",
        "    z0 = public_candidate.get('metadata', {}).get('{field}')\n    z1 = [z0][0]\n    z2 = private_store.read_evidence_label(z1, store)\n    score += selector.score_candidate(z2)",
    ],
    "M3": [
        "    with open(config.get('cache_file'), 'r', encoding='utf-8') as fh:\n        cache = json.load(fh)\n    k = public_candidate.get('metadata', {}).get('{field}')\n    score += selector.score_candidate(private_store.read_evidence_label(cache.get(k), store))",
        "    with open(config.get('cache_file'), 'r', encoding='utf-8') as fh:\n        cache = json.load(fh)\n    k = public_candidate.get('metadata', {}).get('{field}')\n    score += selector.score_candidate(private_store.read_evidence_label(cache.get(k, k), store))",
        "    cache = json.load(open(config.get('cache_file'), 'r', encoding='utf-8'))\n    k = public_candidate.get('metadata', {}).get('{field}')\n    score += selector.score_candidate(private_store.read_evidence_label(cache[k], store))",
    ],
    "M4": [
        "    idx = config.get('metadata_field')\n    ref = public_candidate.get('metadata', {}).get(idx)\n    score += selector.score_candidate(private_store.read_evidence_label(ref, store))",
        "    idx = config.get('weight_public_score')\n    ref = public_candidate.get('metadata', {}).get('{field}')\n    score += selector.score_candidate(private_store.read_evidence_label(ref, store))",
        "    idx = config.get('timeout_ms')\n    ref = public_candidate.get('metadata', {}).get('{field}')\n    score += selector.score_candidate(private_store.read_evidence_label(ref, store))",
    ],
    "F1": [
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    vec = feature_builder.append_feature([], val)\n    score += sum(vec)",
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    vec = feature_builder.append_feature([], val)\n    score += sum(vec or [0])",
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    vec = feature_builder.append_feature([], val)\n    score += sum(vec)",
    ],
    "F2": [
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    feature_builder.append_feature([], val)\n    flag = bool(val)\n    score += int(flag)",
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    feature_builder.append_feature([], val)\n    score += 1 if val else 0",
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    feature_builder.append_feature([], val)\n    score += int(val is not None)",
    ],
    "F3": [
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    feature_builder.append_feature([], val)\n    cnt = len(val or [])\n    ratio = cnt / 10\n    score += ratio",
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    feature_builder.append_feature([], val)\n    cnt = len(val or []) + 1\n    score += cnt / 20",
        "    ref = features.get('{field}')\n    val = private_store.read_evidence_label(ref, store)\n    feature_builder.append_feature([], val)\n    score += len(val or []) / 5",
    ],
    "F4": [
        "    def layer1(x): return neutral_wrap(x)\n    def layer2(y): return private_store.read_evidence_label(layer1(y), store)\n    score += selector.score_candidate(layer2(features.get('{field}')))",
        "    def layer1(x): return neutral_wrap2(x)\n    def layer2(y): return private_store.read_evidence_label(layer1(y), store)\n    score += selector.score_candidate(layer2(features.get('{field}')))",
        "    def layer1(x): return [x][0]\n    def layer2(y): return private_store.read_evidence_label(layer1(y), store)\n    score += selector.score_candidate(layer2(features.get('{field}')))",
    ],
    "R1": [
        "    pred = features.get('missing_prediction')\n    if pred is None:\n        score += selector.score_candidate(private_store.read_evidence_label(features.get('{field}'), store))",
        "    pred = features.get('missing_prediction')\n    if not pred:\n        score += selector.score_candidate(private_store.read_evidence_label(features.get('{field}'), store))",
        "    pred = features.get('missing_prediction')\n    if pred is None:\n        score += selector.score_candidate(private_store.read_evidence_label(features.get('{field}'), store))",
    ],
    "R2": [
        "    try:\n        raise RuntimeError('simulated public failure')\n    except RuntimeError:\n        score += selector.score_candidate(private_store.read_evidence_label(features.get('{field}'), store))",
        "    try:\n        x = 1 / 0\n    except ZeroDivisionError:\n        score += selector.score_candidate(private_store.read_evidence_label(features.get('{field}'), store))",
        "    try:\n        raise ValueError('simulated public failure')\n    except Exception:\n        score += selector.score_candidate(private_store.read_evidence_label(features.get('{field}'), store))",
    ],
    "R3": [
        "    def delayed(ref=features.get('{field}')):\n        return private_store.read_evidence_label(ref, store)\n    score += selector.score_candidate(delayed())",
        "    def delayed(ref=features.get('{field}')):\n        return private_store.read_evidence_label(ref, store)\n    score += selector.score_candidate(delayed())",
        "    def delayed(ref=features.get('{field}')):\n        return private_store.read_evidence_label(ref, store)\n    score += selector.score_candidate(delayed())",
    ],
    "R4": [
        "    gate = private_store.read_evidence_label(features.get('{field}'), store)\n    if candidate_filter.apply(gate):\n        score += 1.0",
        "    gate = private_store.read_evidence_label(features.get('{field}'), store)\n    if candidate_filter.apply(gate):\n        score += 0.5",
        "    gate = private_store.read_evidence_label(features.get('{field}'), store)\n    if candidate_filter.apply(gate):\n        score += 0.2",
    ],
}


def build_adapter_source(
    *,
    case_id: str,
    pattern_id: str | None,
    variant: int,
    second_root: str | Path,
    include_classes: bool = True,
) -> tuple[str, str]:
    """生成案例 adapter.py 源码，返回 (源码, 注入字段名)。"""
    second_root = str(Path(second_root)).replace("\\", "/")
    header = _ADAPTER_HEADER.format(case_id=case_id, pattern_id=pattern_id or "Clean", second_root=second_root)
    classes = _ADAPTER_CLASSES if include_classes else ""
    real = _ADAPTER_REAL
    if pattern_id is None:
        body = _SELECTION_HEAD
        # 普通 Clean：仅真实 BM25 分数；困难 Clean 由调用方在 body 后追加字段读取
        return header + classes + real + body + _SELECTION_TAIL, ""
    field = PATTERN_FIELDS[pattern_id][variant % 3]
    injection = _INJECTION_BODIES[pattern_id][variant % 3].replace("{field}", field)
    body = _SELECTION_HEAD + injection + _SELECTION_TAIL
    return header + classes + real + body, field


def build_hard_clean_adapter_source(case_id: str, second_root: str | Path) -> str:
    """困难 Clean：代码含 state/label/cache 等词，取值全部来自 Public 输入，Source=0。"""
    second_root = str(Path(second_root)).replace("\\", "/")
    header = _ADAPTER_HEADER.format(case_id=case_id, pattern_id="Clean", second_root=second_root)
    body = '''


def selection_entry(public_candidate, features, config, store):
    score = _real_bm25_scores(config).get(public_candidate.get("doc_id_hash", ""), (0, 0.0))[1]
    state_cache = public_candidate.get('metadata', {}).get('state_cache')
    label_encoder = public_candidate.get('metadata', {}).get('label_encoder')
    backup_ranker = public_candidate.get('metadata', {}).get('backup_ranker')
    if state_cache and label_encoder and backup_ranker:
        score += 0.0
    return score
'''
    return header + _ADAPTER_CLASSES + _ADAPTER_REAL + body


def load_public_questions(eval_path: str | Path, max_q: int = 300) -> list[dict[str, str]]:
    """从第二工程公开评测问题集加载 (qid, question)。不读取 gold_answer/gold_doc_ids。"""
    out: list[dict[str, str]] = []
    with open(eval_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            qid = str(rec.get("qid", ""))
            question = str(rec.get("question", ""))
            if qid and question.strip():
                out.append({"qid": qid, "question": question.strip()})
    return out[:max_q]
