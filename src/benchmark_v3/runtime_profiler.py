from __future__ import annotations

import statistics
import time
import tracemalloc
from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class RuntimeMeasurement:
    name: str
    elapsed_ms: float
    peak_memory_kb: float


def measure_once(name: str, fn: Callable[[], Any]) -> tuple[Any, RuntimeMeasurement]:
    tracemalloc.start()
    start = time.perf_counter_ns()
    result = fn()
    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, RuntimeMeasurement(name, elapsed_ms, peak / 1024)


def summarize_measurements(name: str, values: list[RuntimeMeasurement], baseline_ms: float = 0.0, baseline_kb: float = 0.0) -> dict[str, float | str]:
    times = [v.elapsed_ms for v in values]
    mem = [v.peak_memory_kb for v in values]
    return {
        "detector": name,
        "repeat_count": len(values),
        "mean_ms": statistics.mean(times),
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
        "median_ms": statistics.median(times),
        "p50_ms": statistics.median(times),
        "p95_ms": sorted(times)[max(0, int(len(times) * 0.95) - 1)],
        "min_ms": min(times),
        "max_ms": max(times),
        "peak_memory_kb": max(mem),
        "relative_time_overhead": (statistics.mean(times) / baseline_ms - 1.0) if baseline_ms else 0.0,
        "relative_memory_overhead": (max(mem) / baseline_kb - 1.0) if baseline_kb else 0.0,
        "status": "REPRODUCED",
    }

