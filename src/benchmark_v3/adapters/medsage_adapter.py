from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark_v3.scenario_builder import baseline_select, load_public_pool


class MedSageAdapter:
    def __init__(self, root: Path, qid_count: int = 20):
        self.root = root
        self.queries, self.candidates, self.qid_map = load_public_pool(root, max_qids=qid_count)
        self.selected: dict[str, list[str]] = {}

    def load_public_queries(self) -> list[dict[str, Any]]:
        return [q.__dict__ for q in self.queries]

    def load_public_candidates(self) -> list[dict[str, Any]]:
        return [c.__dict__ for rows in self.candidates.values() for c in rows]

    def run_baseline_selection(self) -> dict[str, list[str]]:
        self.selected = baseline_select(self.candidates)
        return self.selected

    def inject_test_fault(self, fault: dict[str, Any]) -> None:
        self.fault = fault

    def run_selection(self) -> dict[str, list[str]]:
        return self.run_baseline_selection()

    def get_selected_doc_ids(self) -> dict[str, list[str]]:
        return self.selected

