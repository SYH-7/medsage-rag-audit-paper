from __future__ import annotations

PATTERN_DEFS = [
    ("M1", "Leak-M", "candidate_metadata", "aux_11", "candidate_scoring"),
    ("M2", "Leak-M", "candidate_metadata", "aux_17", "candidate_scoring"),
    ("M3", "Leak-M", "cache_layer", "aux_23", "candidate_scoring"),
    ("M4", "Leak-M", "config", "aux_31", "candidate_scoring"),
    ("F1", "Leak-F", "feature_matrix", "aux_41", "feature_matrix"),
    ("F2", "Leak-F", "feature_matrix", "aux_43", "feature_matrix"),
    ("F3", "Leak-F", "feature_matrix", "aux_47", "feature_matrix"),
    ("F4", "Leak-F", "cache_layer", "aux_53", "feature_matrix"),
    ("R1", "Leak-R", "fallback_selector", "aux_61", "fallback_selection"),
    ("R2", "Leak-R", "exception_fallback", "aux_67", "fallback_selection"),
    ("R3", "Leak-R", "closure_default", "aux_71", "fallback_selection"),
    ("R4", "Leak-R", "candidate_filter", "aux_73", "candidate_filter"),
]

PATTERNS = [
    {"pattern_id": pid, "family": fam, "module": module, "field": field, "sink": sink}
    for pid, fam, module, field, sink in PATTERN_DEFS
]

