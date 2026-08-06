# -*- coding: utf-8 -*-
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
