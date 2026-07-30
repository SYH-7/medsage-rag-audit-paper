from __future__ import annotations

from typing import Mapping, Sequence
import numpy as np
from scipy.stats import wilcoxon


def paired_bootstrap_ci(differences: Sequence[float], iterations: int = 10000, seed: int = 42, alpha: float = 0.05):
    d = np.asarray(differences, dtype=float)
    if len(d) == 0:
        raise ValueError("No paired differences")
    rng = np.random.default_rng(seed)
    samples = rng.choice(d, size=(iterations, len(d)), replace=True).mean(axis=1)
    return float(d.mean()), float(np.quantile(samples, alpha / 2)), float(np.quantile(samples, 1 - alpha / 2))


def wilcoxon_paired(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Paired samples differ in length")
    diff = np.asarray(a) - np.asarray(b)
    if np.allclose(diff, 0):
        return 1.0
    return float(wilcoxon(diff).pvalue)


def mcnemar_exact(a: Sequence[int], b: Sequence[int]) -> float:
    from scipy.stats import binomtest
    n01 = sum(x == 0 and y == 1 for x, y in zip(a, b))
    n10 = sum(x == 1 and y == 0 for x, y in zip(a, b))
    n = n01 + n10
    return 1.0 if n == 0 else float(binomtest(min(n01, n10), n=n, p=0.5, alternative="two-sided").pvalue)


def holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    items = sorted(p_values.items(), key=lambda x: x[1])
    m = len(items)
    adjusted = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        value = min(1.0, (m - rank) * p)
        running = max(running, value)
        adjusted[name] = running
    return adjusted
