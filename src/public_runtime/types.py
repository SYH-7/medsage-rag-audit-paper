#!/usr/bin/env python
"""Public runtime data types - NO GOLD FIELDS ALLOWED."""
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class PublicQuery:
    qid: str
    question: str
    # NO: query_states, query_demands, key_states, key_demands, relevance, risk_types

@dataclass(frozen=True)
class PublicCandidate:
    qid: str
    doc_id: str
    title: str = ""
    content: str = ""
    reranker_score: float = 0.0
    # NO: supported_states, supported_demands, risk_types, relevance, gold_doc_ids

@dataclass(frozen=True)
class QueryPrediction:
    qid: str
    predicted_demands: frozenset = field(default_factory=frozenset)
    # NO: gold fields

@dataclass(frozen=True)
class EvidencePrediction:
    qid: str
    doc_id: str
    predicted_demands: frozenset = field(default_factory=frozenset)
    # NO: gold fields

# Column deny list for public files
DENY_COLUMNS = [
    "query_states", "query_demands_gold", "key_states", "key_demands_gold",
    "supported_states", "supported_demands_gold", "relevance", "risk_types",
    "oracle", "gold", "state_doc_map", "gold_doc_ids", "adjudication"
]

def validate_public_dict(d, source=""):
    """Check dict has no gold-tainted keys."""
    for key in d:
        key_lower = key.lower()
        for deny in DENY_COLUMNS:
            if deny in key_lower:
                raise ValueError(f"FORBIDDEN FIELD '{key}' in {source}")
