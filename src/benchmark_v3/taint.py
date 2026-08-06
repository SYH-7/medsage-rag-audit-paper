from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class Taint:
    source_id: str
    source_type: str
    qid_hash: str
    transform_chain: list[str] = field(default_factory=list)
    current_module: str = ""
    current_field: str = ""
    sink: str = ""
    timestamp: float = field(default_factory=time.time)

    def transform(self, name: str, *, module: str = "", field: str = "") -> "Taint":
        return Taint(
            source_id=self.source_id,
            source_type=self.source_type,
            qid_hash=self.qid_hash,
            transform_chain=[*self.transform_chain, name],
            current_module=module or self.current_module,
            current_field=field or self.current_field,
            sink=self.sink,
        )


class TaintedValue:
    def __init__(self, value: Any, taints: Iterable[Taint] | None = None):
        self.value = value
        self.taints = list(taints or [])

    def transform(self, name: str, *, module: str = "", field: str = "") -> "TaintedValue":
        return self.__class__(self.value, [t.transform(name, module=module, field=field) for t in self.taints])

    def to_jsonable(self) -> dict[str, Any]:
        return {"value": self.value, "_taints": [t.__dict__ for t in self.taints]}

    @classmethod
    def from_jsonable(cls, data: Any) -> "TaintedValue":
        if isinstance(data, dict) and "_taints" in data:
            return cls(data.get("value"), [Taint(**t) for t in data["_taints"]])
        return cls(data, [])

    def __bool__(self) -> bool:
        return bool(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __int__(self) -> int:
        return int(self.value)


class TaintedScalar(TaintedValue):
    pass


class TaintedBool(TaintedValue):
    pass


class TaintedNumber(TaintedValue):
    pass


class TaintedList(TaintedValue):
    def __iter__(self):
        return iter(self.value)

    def __len__(self) -> int:
        return len(self.value)


class TaintedSet(TaintedValue):
    pass


class TaintedDict(TaintedValue):
    def get(self, key: Any, default: Any = None) -> Any:
        value = self.value.get(key, default)
        return TaintedValue(value, self.taints).transform("dict_get", field=str(key)) if self.taints else value

    def items(self):
        return self.value.items()


def taint_source(value: Any, *, source_id: str, source_type: str, qid_hash: str, field: str) -> TaintedValue:
    taint = Taint(source_id=source_id, source_type=source_type, qid_hash=qid_hash, current_field=field)
    if isinstance(value, bool):
        return TaintedBool(value, [taint])
    if isinstance(value, (int, float)):
        return TaintedNumber(value, [taint])
    if isinstance(value, list):
        return TaintedList(value, [taint])
    if isinstance(value, set):
        return TaintedSet(value, [taint])
    if isinstance(value, dict):
        return TaintedDict(value, [taint])
    return TaintedScalar(value, [taint])


def collect_taints(value: Any) -> list[Taint]:
    if isinstance(value, TaintedValue):
        return value.taints
    if isinstance(value, dict):
        out: list[Taint] = []
        for v in value.values():
            out.extend(collect_taints(v))
        return out
    if isinstance(value, (list, tuple, set)):
        out: list[Taint] = []
        for v in value:
            out.extend(collect_taints(v))
        return out
    return []


def record_sink(value: Any, *, sink: str, module: str, field: str, trace_path: Path) -> int:
    taints = collect_taints(value)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    import sys
    frame = sys._getframe(1)
    adapter_frame = None
    while frame:
        if frame.f_code.co_filename.endswith("adapter.py"):
            adapter_frame = frame
            break
        frame = frame.f_back
    with trace_path.open("a", encoding="utf-8") as f:
        for taint in taints:
            row = taint.transform("enter_sink", module=module, field=field)
            row.sink = sink
            row.timestamp = time.time()
            payload = row.__dict__
            if adapter_frame is not None:
                payload = payload | {
                    "adapter_file": "adapter.py",
                    "adapter_function": adapter_frame.f_code.co_name,
                    "adapter_line": adapter_frame.f_lineno,
                }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            count += 1
    return count

def serialize_with_taint(path: Path, obj: Any) -> None:
    def convert(v: Any) -> Any:
        if isinstance(v, TaintedValue):
            return v.to_jsonable()
        if isinstance(v, dict):
            return {k: convert(val) for k, val in v.items()}
        if isinstance(v, list):
            return [convert(x) for x in v]
        return v
    path.write_text(json.dumps(convert(obj), ensure_ascii=False, indent=2), encoding="utf-8")

def load_taint_trace(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
