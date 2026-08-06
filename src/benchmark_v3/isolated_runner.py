from __future__ import annotations

import json
import importlib.util
import inspect
import traceback
from pathlib import Path
from typing import Any

from .contracts import DetectorFinding, PUBLIC_CANDIDATE_FIELDS, PUBLIC_METADATA_FIELDS, UNKNOWN_LEAK
from .static_dataflow_detector import detect_tree
from .taint import load_taint_trace, record_sink, TaintedValue, taint_source


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _restore(v: Any) -> Any:
    if isinstance(v, dict) and "_taints" in v:
        return TaintedValue.from_jsonable(v)
    if isinstance(v, dict):
        return {k: _restore(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_restore(x) for x in v]
    return v


class PrivateStoreProxy:
    def __init__(self, store: dict[str, Any], trace_path: Path, *, mask_private: bool = False):
        self.store = store
        self.trace_path = trace_path
        self.mask_private = mask_private
        self.current_qid = ""
        self.current_field = ""
        self.source_calls = 0
        self.sink_calls = 0
        self.branch_calls: dict[str, int] = {}

    def context(self, *, qid_hash: str, field: str = "") -> None:
        self.current_qid = qid_hash
        self.current_field = field

    def read_evidence_label(self, handle: Any) -> Any:
        self.branch_calls["private_store.read_evidence_label"] = self.branch_calls.get("private_store.read_evidence_label", 0) + 1
        if self.mask_private:
            return None
        if isinstance(handle, str) and handle in self.store:
            self.source_calls += 1
            return taint_source(self.store[handle], source_id=handle, source_type="EvidenceGold", qid_hash=self.current_qid, field=self.current_field)
        return None

    def sink(self, value: Any, *, sink: str, module: str, field: str) -> None:
        self.branch_calls[f"{module}.{sink}"] = self.branch_calls.get(f"{module}.{sink}", 0) + 1
        self.sink_calls += record_sink(value, sink=sink, module=module, field=field or self.current_field, trace_path=self.trace_path)


def _load_adapter(case_dir: Path):
    path = case_dir / "detector_input" / "adapter.py"
    spec = importlib.util.spec_from_file_location(f"dakd_adapter_{case_dir.name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _instrument_adapter(module: Any, proxy: PrivateStoreProxy) -> None:
    if hasattr(module, "private_store"):
        module.private_store.read_evidence_label = staticmethod(lambda handle, _store=None: proxy.read_evidence_label(handle))
    if hasattr(module, "selector"):
        def score_candidate(value):
            proxy.sink(value, sink="candidate_scoring", module="selector", field=proxy.current_field)
            try:
                return len(value or [])
            except TypeError:
                return 0
        module.selector.score_candidate = staticmethod(score_candidate)
    if hasattr(module, "feature_builder"):
        def append_feature(vec, value):
            proxy.sink(value, sink="feature_matrix", module="feature_builder", field=proxy.current_field)
            vec.append(len(value or []) if value else 0)
            return vec
        module.feature_builder.append_feature = staticmethod(append_feature)
    if hasattr(module, "candidate_filter"):
        def apply(value):
            proxy.sink(value, sink="candidate_filter", module="candidate_filter", field=proxy.current_field)
            return bool(value)
        module.candidate_filter.apply = staticmethod(apply)


def run_selection(case_dir: Path, *, mask_private: bool = False) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    inp = case_dir / "detector_input"
    candidates = _load(inp / "public_candidates.json")
    features = _load(inp / "public_features.json")
    runtime_store = _load(inp / "runtime_store.json") if (inp / "runtime_store.json").exists() else {}
    config = _load(inp / "public_config.json") if (inp / "public_config.json").exists() else {}
    if config.get("cache_file"):
        config = dict(config)
        config["cache_file"] = str(inp / config["cache_file"])
    trace_path = inp / "runtime_taint_trace.jsonl"
    exec_path = inp / "adapter_execution_trace.jsonl"
    if trace_path.exists():
        trace_path.unlink()
    if exec_path.exists():
        exec_path.unlink()
    module = _load_adapter(case_dir)
    proxy = PrivateStoreProxy(runtime_store, trace_path, mask_private=mask_private)
    _instrument_adapter(module, proxy)
    by_q: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        by_q.setdefault(c["qid_hash"], []).append(c)
    selected = {}
    failures: list[dict[str, Any]] = []
    for qh, rows in by_q.items():
        scored = []
        for row in rows:
            frow = features.get(qh, {})
            field = next((k for k, v in row.get("metadata", {}).items() if isinstance(v, str) and v in runtime_store), "")
            if not field:
                field = next((k for k, v in frow.items() if isinstance(v, str) and v in runtime_store), "")
            proxy.context(qid_hash=qh, field=field)
            before_sources = proxy.source_calls
            before_sinks = proxy.sink_calls
            status = "EXECUTED"
            error = ""
            try:
                score = module.selection_entry(row, frow, config, proxy)
                if score is None:
                    score = row["public_scores"].get("reranker", 0.0)
            except Exception as exc:
                status = "EXECUTION_FAILURE"
                error = "".join(traceback.format_exception_only(type(exc), exc)).strip()
                failures.append({"qid_hash": qh, "doc_id_hash": row.get("doc_id_hash", ""), "error": error})
                score = float("-inf")
            with exec_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "qid_hash": qh,
                    "doc_id_hash": row.get("doc_id_hash", ""),
                    "status": status,
                    "source_calls": proxy.source_calls - before_sources,
                    "sink_calls": proxy.sink_calls - before_sinks,
                    "error": error,
                }, ensure_ascii=False) + "\n")
            scored.append((score, -int(row.get("rank", 0) or 0), row["doc_id_hash"]))
        selected[qh] = [doc for _, _, doc in sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)[:5]]
    return selected, load_taint_trace(trace_path)


def private_source_read(handle: Any, store: dict[str, Any], qid_hash: str, field: str) -> Any:
    if isinstance(handle, str) and handle in store:
        return taint_source(store[handle], source_id=handle, source_type="EvidenceGold", qid_hash=qid_hash, field=field)
    return _restore(handle)


def keyword_static_baseline(case_dir: Path) -> DetectorFinding:
    terms = ["gold", "label", "state", "cache", "fallback", "backup", "private"]
    for path in (case_dir / "detector_input").rglob("*"):
        if path.suffix.lower() not in {".py", ".json", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in terms:
            if term in text:
                return DetectorFinding(True, UNKNOWN_LEAK, module="keyword_static_baseline", field=term, file=path.name, evidence=f"keyword:{term}")
    return DetectorFinding(False)


def ast_static_dataflow(case_dir: Path, config: dict[str, Any] | None = None) -> DetectorFinding:
    return detect_tree(case_dir / "detector_input", policy=(config or {}).get("source_sink_policy"))


def schema_guard(case_dir: Path) -> DetectorFinding:
    inp = case_dir / "detector_input"
    for row in _load(inp / "public_candidates.json"):
        for key in row:
            if key not in PUBLIC_CANDIDATE_FIELDS:
                return DetectorFinding(True, UNKNOWN_LEAK, module="schema_guard", field=key, evidence="extra candidate field")
        for key in row.get("metadata", {}):
            if key not in PUBLIC_METADATA_FIELDS:
                return DetectorFinding(True, UNKNOWN_LEAK, module="schema_guard", field=key, evidence="extra metadata field")
    return DetectorFinding(False)


def runtime_taint(case_dir: Path) -> DetectorFinding:
    _, trace = run_selection(case_dir, mask_private=False)
    if trace:
        row = trace[0]
        return DetectorFinding(True, UNKNOWN_LEAK, source_type=row.get("source_type", ""), sink=row.get("sink", ""), module=row.get("current_module", ""), field=row.get("current_field", ""), file="runtime_taint_trace.jsonl", path_valid=True, evidence="taint reached deployment sink")
    return DetectorFinding(False)


def invariance(case_dir: Path) -> DetectorFinding:
    base, _ = run_selection(case_dir, mask_private=False)
    masked, _ = run_selection(case_dir, mask_private=True)
    changed = [qid for qid in base if base[qid] != masked.get(qid)]
    if changed:
        return DetectorFinding(True, UNKNOWN_LEAK, sink="selected_doc_ids", module="invariance", field="selected_doc_ids", file="selection", path_valid=True, evidence=f"changed_qids={len(changed)}")
    return DetectorFinding(False)


def full_audit(case_dir: Path, config: dict[str, Any]) -> DetectorFinding:
    components = {
        "ast_static_dataflow": ast_static_dataflow(case_dir, config),
        "schema_guard": schema_guard(case_dir),
        "runtime_taint": runtime_taint(case_dir),
        "invariance": invariance(case_dir),
    }
    priority = config.get("priority") or ["runtime_taint", "ast_static_dataflow", "schema_guard", "invariance"]
    allow_unknown = bool(config.get("allow_unknown_leak", True))
    for name in priority:
        finding = components.get(name)
        if finding and finding.detected and (allow_unknown or finding.predicted_family != UNKNOWN_LEAK):
            finding.evidence = f"full_audit_component={name}; {finding.evidence}"
            return finding
    detected = [v for v in components.values() if v.detected and (allow_unknown or v.predicted_family != UNKNOWN_LEAK)]
    if not detected:
        return DetectorFinding(False)
    return detected[0]

def run_detector(case_dir: Path, detector: str, config: dict[str, Any] | None = None) -> DetectorFinding:
    config = config or {}
    if detector == "audit_off":
        run_selection(case_dir, mask_private=False)
        return DetectorFinding(False)
    if detector == "keyword_static_baseline":
        return keyword_static_baseline(case_dir)
    if detector == "ast_static_dataflow":
        return ast_static_dataflow(case_dir, config)
    if detector == "schema_guard":
        return schema_guard(case_dir)
    if detector == "runtime_taint":
        return runtime_taint(case_dir)
    if detector == "invariance":
        return invariance(case_dir)
    if detector == "full_audit":
        return full_audit(case_dir, config)
    raise ValueError(detector)
