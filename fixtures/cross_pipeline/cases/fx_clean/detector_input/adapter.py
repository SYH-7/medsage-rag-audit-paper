# -*- coding: utf-8 -*-
# 独立 fixture adapter（Clean）：不接入第二工程，分数来自 public_candidates。
from __future__ import annotations

def selection_entry(public_candidate, features, config, store):
    score = public_candidate.get("public_scores", {}).get("bm25", 0.0)
    return score
