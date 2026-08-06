from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_REPRODUCED = "REPRODUCED"
UNKNOWN_LEAK = "UNKNOWN_LEAK"
PUBLIC_QUERY_FIELDS = {"qid_hash", "question_length", "public_state_hints"}
PUBLIC_CANDIDATE_FIELDS = {"qid_hash", "doc_id_hash", "rank", "public_scores", "metadata"}
PUBLIC_METADATA_FIELDS = {
    "source",
    "rank_hint",
    "public_note",
    "state_cache",
    "risk_score",
    "label_encoder",
    "backup_ranker",
    "private_mode_name",
    "support_feature_public",
    "fallback_timeout",
}
PUBLIC_FEATURE_FIELDS = {"public_rank", "public_score", "public_length_bucket", "public_feature_sum"}
PUBLIC_CONFIG_FIELDS = {"top_k", "weight_public_score", "timeout_ms", "metadata_field"}
DEPLOYMENT_SINKS = {
    "candidate_filter",
    "candidate_scoring",
    "feature_matrix",
    "query_prediction_input",
    "evidence_prediction_input",
    "reranker_input",
    "selection_weight",
    "fallback_selection",
    "selected_doc_ids",
    "topk_order",
}
PRIVATE_SOURCE_TYPES = {
    "QueryGold",
    "EvidenceGold",
    "RelevanceLabel",
    "SupportedDemand",
    "RiskType",
    "AdjudicationLabel",
}


@dataclass
class PublicQuery:
    qid_hash: str
    question_length: int
    public_state_hints: list[str] = field(default_factory=list)


@dataclass
class PublicCandidate:
    qid_hash: str
    doc_id_hash: str
    rank: int
    public_scores: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectorFinding:
    detected: bool
    predicted_family: str = ""
    source_type: str = ""
    sink: str = ""
    module: str = ""
    field: str = ""
    file: str = ""
    line: int | str = ""
    path_valid: bool | str = ""
    evidence: str = ""


@dataclass
class TruthRecord:
    case_id: str
    pattern_id: str
    family: str
    source_type: str
    sink: str
    module: str
    field: str
    file: str
    line: int
    injected_qids: int
    injected_candidates: int
    injected_features: int
    fallback_triggers: int
    known_for_lopo: bool

