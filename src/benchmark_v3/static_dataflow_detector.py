from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .contracts import DetectorFinding


LEGACY_SOURCE_CALLS = {"load_" + "private_source"}
LEGACY_SINK_CALLS = {
    "record_" + "candidate_score": "candidate_scoring",
    "record_" + "feature_matrix": "feature_matrix",
    "record_" + "fallback": "fallback",
}
DEFAULT_SOURCE_CALLS = {"private_store.read_evidence_label", *LEGACY_SOURCE_CALLS}
DEFAULT_SINK_CALLS = {
    "selector.score_candidate": "candidate_scoring",
    "feature_builder.append_feature": "feature_matrix",
    "candidate_filter.apply": "candidate_filter",
    **LEGACY_SINK_CALLS,
}


class DataflowVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, sources: set[str], sinks: dict[str, str]):
        self.path = path
        self.sources = sources
        self.sinks = sinks
        self.tainted: set[str] = set()
        self.tainted_functions: set[str] = set()
        self.function_stack: list[str] = []
        self.finding: DetectorFinding | None = None

    def visit_Assign(self, node: ast.Assign) -> Any:
        value_tainted = self.expr_tainted(node.value)
        for target in node.targets:
            for name in self.target_names(target):
                if value_tainted:
                    self.tainted.add(name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Return(self, node: ast.Return) -> Any:
        if self.function_stack and node.value is not None and self.expr_tainted(node.value):
            self.tainted_functions.add(self.function_stack[-1])
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        if isinstance(node.target, ast.Name) and node.target.id == "score" and self.expr_tainted(node.value):
            self.finding = self.finding or DetectorFinding(
                True,
                predicted_family="UNKNOWN_LEAK",
                source_type="PrivateSource",
                sink="selection_weight",
                module="ast_static_dataflow",
                field="score",
                file=self.path.name,
                line=node.lineno,
                path_valid=True,
                evidence="tainted value updates score",
            )
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> Any:
        if self.expr_tainted(node.test):
            self.finding = self.finding or DetectorFinding(
                True,
                predicted_family="UNKNOWN_LEAK",
                source_type="PrivateSource",
                sink="candidate_filter",
                module="ast_static_dataflow",
                field="condition",
                file=self.path.name,
                line=node.lineno,
                path_valid=True,
                evidence="tainted value controls branch",
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        func = self.call_name(node.func)
        if func in self.sinks and any(self.expr_tainted(arg) for arg in node.args):
            self.finding = DetectorFinding(
                True,
                predicted_family="UNKNOWN_LEAK",
                source_type="PrivateSource",
                sink=self.sinks[func],
                module="ast_static_dataflow",
                field="DATAFLOW_PATH",
                file=self.path.name,
                line=node.lineno,
                path_valid=True,
                evidence=f"tainted argument flows to {func}",
            )
        self.generic_visit(node)

    def expr_tainted(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self.tainted
        if isinstance(node, ast.Call):
            func = self.call_name(node.func)
            return func in self.sources or func in self.tainted_functions or any(self.expr_tainted(a) for a in node.args)
        if isinstance(node, ast.Subscript):
            return self.expr_tainted(node.value)
        if isinstance(node, ast.Attribute):
            return self.expr_tainted(node.value)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return any(self.expr_tainted(e) for e in node.elts)
        if isinstance(node, ast.Dict):
            return any(self.expr_tainted(v) for v in node.values)
        if isinstance(node, ast.BinOp):
            return self.expr_tainted(node.left) or self.expr_tainted(node.right)
        if isinstance(node, ast.BoolOp):
            return any(self.expr_tainted(v) for v in node.values)
        if isinstance(node, ast.Compare):
            return self.expr_tainted(node.left) or any(self.expr_tainted(c) for c in node.comparators)
        return False

    def target_names(self, node: ast.AST) -> list[str]:
        if isinstance(node, ast.Name):
            return [node.id]
        if isinstance(node, (ast.Tuple, ast.List)):
            out: list[str] = []
            for elt in node.elts:
                out.extend(self.target_names(elt))
            return out
        return []

    def call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self.call_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return ""


def detect_path(path: Path, policy: dict[str, object] | None = None) -> DetectorFinding:
    if policy:
        sources = set(policy.get("sources", DEFAULT_SOURCE_CALLS))  # type: ignore[arg-type]
        sinks = dict(policy.get("sinks", DEFAULT_SINK_CALLS))  # type: ignore[arg-type]
    else:
        sources = set(DEFAULT_SOURCE_CALLS)
        sinks = dict(DEFAULT_SINK_CALLS)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return DetectorFinding(False)
    visitor = DataflowVisitor(path, sources, sinks)
    visitor.visit(tree)
    return visitor.finding or DetectorFinding(False)


def detect_tree(root: Path, policy: dict[str, object] | None = None) -> DetectorFinding:
    for path in sorted(root.rglob("*.py")):
        finding = detect_path(path, policy=policy)
        if finding.detected:
            return finding
    return DetectorFinding(False)
