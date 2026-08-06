from __future__ import annotations

from pathlib import Path


class TcmSleepAdapter:
    def __init__(self, root: Path):
        self.root = root
        self.status = "CROSS_PIPELINE_ENGINEERING_VALIDATION" if root.exists() else "BLOCKED_SECOND_PIPELINE"

    def load_public_queries(self):
        return []

    def load_public_candidates(self):
        return []

    def run_baseline_selection(self):
        return {}

    def inject_test_fault(self, fault):
        self.fault = fault

    def run_selection(self):
        return {}

    def get_selected_doc_ids(self):
        return {}

