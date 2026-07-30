from __future__ import annotations

from typing import Mapping, Sequence


def state_coverage_metrics(
    retrieved: Sequence[str],
    state_doc_map: Mapping[str, Sequence[str]],
    risk_types: Sequence[str],
    gold_safety_doc_ids: Sequence[str],
    k: int = 5,
) -> dict[str, float]:
    top = set(retrieved[:k])
    states = list(state_doc_map)
    covered = sum(bool(top & set(state_doc_map[s])) for s in states)
    intent_cov = covered / len(states) if states else 0.0
    all_hit = float(bool(states) and covered == len(states))
    safety = float(bool(risk_types) and bool(top & set(gold_safety_doc_ids))) if risk_types else 1.0
    return {
        f"state_cov@{k}": intent_cov,
        f"all_state_hit@{k}": all_hit,
        f"gold_safety_recall@{k}": safety,
        "state_eval_applicable": float(bool(states)),
        "gold_safety_applicable": float(bool(risk_types)),
    }
