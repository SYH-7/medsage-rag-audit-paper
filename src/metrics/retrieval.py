from __future__ import annotations

import math
from typing import Sequence


def retrieval_metrics(retrieved: Sequence[str], gold: Sequence[str], k: int = 5) -> dict[str, float]:
    gold_set = set(gold)
    top = list(retrieved[:k])
    if not gold_set:
        return {f"hit@{k}": 0.0, f"recall@{k}": 0.0, "mrr@10": 0.0, "ndcg@10": 0.0}
    hits = [1 if d in gold_set else 0 for d in retrieved[:10]]
    hit = float(any(d in gold_set for d in top))
    recall = len(gold_set & set(top)) / len(gold_set)
    rr = next((1.0 / (i + 1) for i, d in enumerate(retrieved[:10]) if d in gold_set), 0.0)
    dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(hits))
    ideal_hits = [1] * min(len(gold_set), 10)
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_hits))
    return {f"hit@{k}": hit, f"recall@{k}": recall, "mrr@10": rr, "ndcg@10": dcg / idcg if idcg else 0.0}
