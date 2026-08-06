from __future__ import annotations

from typing import Any


def evaluate_localization(pred: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    detected = bool(pred.get("detected"))
    is_leak = truth.get("family") != "Clean"
    line_pred = pred.get("line", "")
    line_truth = truth.get("line", "")
    try:
        line_distance = abs(int(line_pred) - int(line_truth))
    except Exception:
        line_distance = None
    return {
        "detection_correct": detected == is_leak,
        "family_exact": detected and pred.get("predicted_family") == truth.get("family"),
        "source_exact": detected and pred.get("source_type") == truth.get("source_type"),
        "sink_exact": detected and pred.get("sink") == truth.get("sink"),
        "module_exact": detected and pred.get("module") == truth.get("module"),
        "field_exact": detected and pred.get("field") == truth.get("field"),
        "code_location_exact": detected and pred.get("file") == truth.get("file") and str(line_pred) == str(line_truth),
        "code_location_within_3": detected and pred.get("file") == truth.get("file") and line_distance is not None and line_distance <= 3,
        "path_valid": bool(pred.get("path_valid")),
    }

