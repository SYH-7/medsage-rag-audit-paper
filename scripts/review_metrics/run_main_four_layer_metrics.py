"""Main-benchmark four-layer metric driver (reviewer comment 3).

Additive analysis ONLY:
- reads frozen case dirs in benchmark_work_v5 on TEMP copies (never modifies frozen files),
- recomputes masked/unmasked full rankings using the frozen adapter + instrumentation,
- emits per-case and per-class metrics for:
    layer 1 boundary violation, layer 2 retrieval perturbation (score/order),
    layer 3 evidence-selection change at K in {3,5,7}, and flags for layer 4.
Outputs go to paper_package_dakd_v5_1/17_review_metrics/  (new dir; additive).
"""
from __future__ import annotations
import csv
import json
import os
import math
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from benchmark_v3.isolated_runner import PrivateStoreProxy, _load_adapter, _instrument_adapter  # noqa: E402

PKG = ROOT / "paper_package_dakd_v5_1"
WORK = Path(os.environ.get("MEDSAGE_V5_CASES", str(ROOT / "benchmark_work_v5")))
OUT = Path(os.environ.get("REVIEW_METRICS_OUT", str(PKG / "17_review_metrics")))
OUT.mkdir(parents=True, exist_ok=True)
_REQUIRED_INPUTS = [WORK]


def full_rank(case_dir: Path, *, mask_private: bool) -> dict[str, list[tuple[float, str]]]:
    """Mirror isolated_runner.run_selection but return FULL descending ranking per qid."""
    inp = case_dir / "detector_input"
    import json as _json

    def _load(p):
        return _json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    candidates = _load(inp / "public_candidates.json")
    if isinstance(candidates, dict):  # tolerate dict form
        rows = [c for q in candidates.values() for c in q]
    else:
        rows = candidates
    features = _load(inp / "public_features.json")
    runtime_store = _load(inp / "runtime_store.json")
    config = _load(inp / "public_config.json")
    if config.get("cache_file"):
        config = dict(config)
        config["cache_file"] = str(inp / config["cache_file"])
    trace_path = inp / "runtime_taint_trace.jsonl"
    if trace_path.exists():
        trace_path.unlink()
    module = _load_adapter(case_dir)
    proxy = PrivateStoreProxy(runtime_store, trace_path, mask_private=mask_private)
    _instrument_adapter(module, proxy)
    by_q: dict[str, list[dict]] = {}
    for c in rows:
        by_q.setdefault(c["qid_hash"], []).append(c)
    ranked: dict[str, list[tuple[float, str]]] = {}
    for qh, qrows in by_q.items():
        scored = []
        for row in qrows:
            frow = features.get(qh, {}) if isinstance(features, dict) else {}
            field = next((k for k, v in row.get("metadata", {}).items()
                          if isinstance(v, str) and v in runtime_store), "")
            if not field:
                field = next((k for k, v in frow.items()
                              if isinstance(v, str) and v in runtime_store), "")
            proxy.context(qid_hash=qh, field=field)
            try:
                score = module.selection_entry(row, frow, config, proxy)
            except Exception:
                score = float("-inf")
            if score is None:
                score = row["public_scores"].get("reranker", 0.0)
            scored.append((float(score), -int(row.get("rank", 0) or 0), row["doc_id_hash"]))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        ranked[qh] = [(s, d) for s, _, d in scored]
    return ranked


def kendall_tau(a: list[str], b: list[str]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 1.0
    posb = {d: i for i, d in enumerate(b)}
    try:
        idx = [posb[d] for d in a]
    except KeyError:
        return float("nan")
    n = len(idx)
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            if idx[i] < idx[j]:
                concordant += 1
            elif idx[i] > idx[j]:
                discordant += 1
    return (concordant - discordant) / (concordant + discordant) if (concordant + discordant) else 1.0


def topk_changes(full_a: list[str], full_b: list[str], k: int) -> tuple[bool, bool, int]:
    sa, sb = set(full_a[:k]), set(full_b[:k])
    set_changed = sa != sb
    order_changed = full_a[:k] != full_b[:k]
    dropped = len(sa - sb)  # docs in base top-k that fall out after masking
    return set_changed, order_changed, dropped


def main() -> None:
    _require_inputs()
    # load frozen per-case classes for the 36 leak positives
    frozen = {}
    p = PKG / "08_behavior" / "BEHAVIORAL_EFFECT_PER_CASE.csv"
    with p.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["leak_class"] in ("ACCESS_LEAK", "BEHAVIORAL_LEAK"):
                frozen[r["case_id"]] = r

    rows = []
    ks = (3, 5, 7)
    for case_id, meta in sorted(frozen.items()):
        case_dir = WORK / case_id
        if not (case_dir / "detector_input" / "adapter.py").exists():
            continue
        with tempfile.TemporaryDirectory(prefix="ksens_") as td:
            tmp = Path(td) / case_id
            shutil.copytree(case_dir, tmp)
            rank_nomask = full_rank(tmp, mask_private=False)
            rank_mask = full_rank(tmp, mask_private=True)
        n_qid = len(rank_nomask)
        n_docs = sum(len(v) for v in rank_nomask.values())

        score_changed_docs = 0
        abs_deltas: list[float] = []
        taus: list[float] = []
        order_changed_qids_anyK: dict[int, int] = {}
        set_changed_qids_anyK: dict[int, int] = {}
        replaced_docs: dict[int, int] = {}
        for qh in rank_nomask:
            a = rank_nomask[qh]
            b = rank_mask.get(qh, a)
            ta = [d for _, d in a]
            tb = [d for _, d in b]
            sa = {d: s for s, d in a}
            sb = {d: s for s, d in b}
            for d in set(sa) | set(sb):
                if abs(sa.get(d, float("nan")) - sb.get(d, float("nan"))) > 1e-12:
                    score_changed_docs += 1
                if d in sa and d in sb:
                    abs_deltas.append(abs(sa[d] - sb[d]))
            tau = kendall_tau(ta, tb)
            if not math.isnan(tau):
                taus.append(tau)
            for k in ks:
                set_ch, ord_ch, dropped = topk_changes(ta, tb, k)
                set_changed_qids_anyK[k] = set_changed_qids_anyK.get(k, 0) + (1 if set_ch else 0)
                order_changed_qids_anyK[k] = order_changed_qids_anyK.get(k, 0) + (1 if ord_ch else 0)
                replaced_docs[k] = replaced_docs.get(k, 0) + dropped

        changed_k5 = sum(1 for qh in rank_nomask
                         if [d for _, d in rank_mask.get(qh, [])][:5] !=
                            [d for _, d in rank_nomask[qh]][:5])
        leak = "BEHAVIORAL_LEAK" if changed_k5 else "ACCESS_LEAK"
        row = {
            "case_id": case_id,
            "family": meta.get("family", ""),
            "pattern_id": meta.get("pattern_id", ""),
            "frozen_class": meta["leak_class"],
            "recomputed_class_k5": leak,
            "repro_ok": leak == meta["leak_class"],
            "n_qids": n_qid,
            "n_docs": n_docs,
            "frac_score_changed_docs": (score_changed_docs / n_docs if n_docs else 0.0),
            "mean_abs_score_delta": (statistics.mean(abs_deltas) if abs_deltas else 0.0),
            "max_abs_score_delta": (max(abs_deltas) if abs_deltas else 0.0),
            "mean_kendall_tau": (statistics.mean(taus) if taus else 1.0),
            "min_kendall_tau": (min(taus) if taus else 1.0),
        }
        for k in ks:
            row[f"set_changed_qids_K{k}"] = set_changed_qids_anyK[k]
            row[f"order_changed_qids_K{k}"] = order_changed_qids_anyK[k]
            row[f"replaced_docs_K{k}"] = replaced_docs[k]
        rows.append(row)
        print(f"done {case_id}: {leak} (frozen {meta['leak_class']})", flush=True)

    # per-class summaries
    def summarize(class_rows: list[dict], label: str) -> dict:
        n = len(class_rows)
        if not n:
            return {}
        return {
            "class": label,
            "cases": n,
            "repro_ok": sum(1 for r in class_rows if r["repro_ok"]),
            "frac_score_changed_docs_mean": statistics.mean(r["frac_score_changed_docs"] for r in class_rows),
            "mean_abs_score_delta_mean": statistics.mean(r["mean_abs_score_delta"] for r in class_rows),
            "max_abs_score_delta_max": max(r["max_abs_score_delta"] for r in class_rows),
            "mean_kendall_tau_mean": statistics.mean(r["mean_kendall_tau"] for r in class_rows),
            **{f"cases_set_changed_K{k}": sum(1 for r in class_rows if r[f"set_changed_qids_K{k}"] > 0) for k in ks},
            **{f"cases_order_changed_K{k}": sum(1 for r in class_rows if r[f"order_changed_qids_K{k}"] > 0) for k in ks},
            **{f"total_replaced_docs_K{k}": sum(r[f"replaced_docs_K{k}"] for r in class_rows) for k in ks},
        }

    summ = []
    for label in ("ACCESS_LEAK", "BEHAVIORAL_LEAK"):
        cls = [r for r in rows if r["recomputed_class_k5"] == label]
        summ.append(summarize(cls, label))
    allrows = summarize(rows, "ALL_LEAK_POSITIVES")

    with (OUT / "main_four_layer_metrics_per_case.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with (OUT / "main_four_layer_metrics_summary.csv").open("w", encoding="utf-8", newline="") as f:
        keys = list(summ[0].keys())
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for s in summ:
            w.writerow({k: s.get(k, "") for k in keys})
        w.writerow({k: allrows.get(k, "") for k in keys})
    with (OUT / "main_four_layer_metrics.json").open("w", encoding="utf-8") as f:
        json.dump({"summary": summ, "all": allrows, "cases": len(rows), "note": (
            "Computed on temp copies of benchmark_work_v5 case dirs with the frozen adapters; "
            "frozen detector logic untouched.")}, f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY ===")
    print(json.dumps({"summary": summ, "all": allrows}, ensure_ascii=False, indent=2))


def _require_inputs() -> None:
    """Soft-fail when the local/private inputs of the audited projects are absent.

    This repository ships the frozen outputs; re-executing a script additionally
    needs the local original projects (see scripts/review_metrics/README.md).
    """
    missing = [str(p) for p in _REQUIRED_INPUTS if not Path(p).exists()]
    if missing:
        print("REQUIRES_LOCAL_ORIGINAL_PROJECT: missing local input(s):")
        for m in missing:
            print("  -", m)
        print("Set the documented environment variables (scripts/review_metrics/README.md).")
        raise SystemExit(0)


if __name__ == "__main__":
    main()
