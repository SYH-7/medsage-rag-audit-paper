from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .localization import evaluate_localization


def load_truth(case_dir: Path) -> dict[str, Any]:
    return json.loads((case_dir / "private_truth" / "truth.json").read_text(encoding="utf-8"))


def score_prediction(case_dir: Path, detector: str, pred: dict[str, Any]) -> dict[str, Any]:
    truth = load_truth(case_dir)
    is_leak = truth["family"] != "Clean"
    detected = bool(pred.get("detected"))
    loc = evaluate_localization(pred, truth)
    return {
        "case_id": case_dir.name,
        "detector": detector,
        "is_leak": is_leak,
        "family": truth["family"],
        "pattern_id": truth["pattern_id"],
        "rate": truth["rate"],
        "seed": truth["seed"],
        "hard_clean": truth.get("hard_clean", False),
        "detected": detected,
        "tp": int(is_leak and detected),
        "fp": int((not is_leak) and detected),
        "tn": int((not is_leak) and not detected),
        "fn": int(is_leak and not detected),
        "injected_qids": truth["injected_qids"],
        "injected_candidates": truth["injected_candidates"],
        "injected_features": truth["injected_features"],
        "fallback_triggers": truth["fallback_triggers"],
        **loc,
    }


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(r["tp"] for r in rows)
    fp = sum(r["fp"] for r in rows)
    tn = sum(r["tn"] for r in rows)
    fn = sum(r["fn"] for r in rows)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    mcc_den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
        "balanced_accuracy": (recall + specificity) / 2 if (tp + fn) else specificity,
        "mcc": ((tp * tn - fp * fn) / mcc_den) if mcc_den else 0.0,
    }

