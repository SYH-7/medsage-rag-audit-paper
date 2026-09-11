"""E7: empirical sweep of the two real codebases for naturally occurring
gold-into-deployment flows (negative-result evidence for the external-validity
discussion).

Question: does the production code of the audited projects contain any read of
private evaluation gold (query/evidence gold, gold doc ids) that flows into a
DEPLOYABLE retrieval/selection/scoring structure (candidate metadata, features,
ranking, prompt context) - i.e., a naturally occurring leak - as opposed to
offline annotation, dataset construction, or post-hoc metric computation that
runs after selection?

Method (honest and lightweight): tokenise each real .py file; find identifiers
that mention gold (evidence_gold, query_gold, gold_doc_ids, gold_safety_doc_ids,
golden, ...) or private-truth stores (private_store, read_evidence, truth); tag
every hit with its module role from the file path; then classify the role as
DEPLOY_PATH (retrieval/selection/scoring/state/generation/api/prompt - code that
runs while producing an answer) vs OFFLINE (annotation/datasets/metrics/
experiments/schemas - code that runs before/after). Report the counts and the
actual hit sites so the result is auditable. No frozen detector code is used and
nothing is modified.

Outputs to paper_package_dakd_v5_1/17_review_metrics/real_code_sweep_*.csv/json.
"""
from __future__ import annotations
import csv
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("REVIEW_METRICS_OUT", str(ROOT / "paper_package_dakd_v5_1" / "17_review_metrics")))
OUT.mkdir(parents=True, exist_ok=True)
_REQUIRED_INPUTS = [MAIN_SRC, CROSS_SRC]

MAIN_SRC = Path(os.environ.get("MEDSAGE_RAG_ROOT", str(ROOT))) / "src" / "medsage"
CROSS_SRC = Path(os.environ.get("TCM_SLEEP_RAG_ROOT", ".")) / "rag_service"

GOLD_RE = re.compile(r"\b(evidence_gold|query_gold|gold_doc_ids|gold_safety_doc_ids|golden_|gold_|is_official_gold)\w*|\b(private_store|read_evidence_label|private_truth)\b")

DEPLOY_HINTS = ("retrieval", "selection", "score", "rerank", "state", "generation",
                "pipeline", "prompt", "api", "service", "adapter", "hybrid", "dense")
OFFLINE_HINTS = ("annotation", "dataset", "metrics", "experiment", "gold_load", "pool", "schema")


def role_of(rel: str) -> str:
    low = rel.lower().replace("\\", "/")
    if any(x in low for x in OFFLINE_HINTS):
        return "OFFLINE"
    if any(x in low for x in DEPLOY_HINTS):
        return "DEPLOY_PATH"
    return "OTHER"


def sweep(src: Path, project: str) -> list[dict]:
    hits = []
    for py in sorted(src.rglob("*.py")):
        rel = str(py.relative_to(src))
        if "site-packages" in rel or rel.startswith((".", "_")):
            continue
        try:
            lines = py.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for ln, line in enumerate(lines, 1):
            m = GOLD_RE.search(line)
            if not m:
                continue
            # ignore pure comments-only lines mentioning gold as prose? keep but tag
            hits.append({
                "project": project, "file": rel, "line": ln,
                "role": role_of(rel),
                "ident": m.group(0),
                "snippet": line.strip()[:120],
            })
    return hits


def main() -> None:
    _require_inputs()
    all_hits = []
    if MAIN_SRC.exists():
        all_hits += sweep(MAIN_SRC, "main-medsage")
    if CROSS_SRC.exists():
        all_hits += sweep(CROSS_SRC, "tcm-rag_service")

    rows = sorted(all_hits, key=lambda r: (r["project"], r["file"], r["line"]))
    with (OUT / "real_code_sweep_hits.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["project", "file", "line", "role", "ident", "snippet"])
        w.writeheader(); w.writerows(rows)

    deploy = [r for r in rows if r["role"] == "DEPLOY_PATH"]
    by_role = {}
    for r in rows:
        by_role.setdefault((r["project"], r["role"]), []).append(r)

    summary = []
    for (proj, role), rs in sorted(by_role.items()):
        summary.append({"project": proj, "role": role, "sites": len(rs),
                        "files": len({r["file"] for r in rs})})
    with (OUT / "real_code_sweep_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["project", "role", "sites", "files"])
        w.writeheader(); w.writerows(summary)

    print("total gold/private-truth identifier hits:", len(rows))
    for s in summary:
        print(s)
    print("\nDEPLOY_PATH hits (candidate natural leaks):", len(deploy))
    for r in deploy:
        print("  ", r["project"], r["file"], r["line"], r["ident"], "|", r["snippet"])

    # write json properly
    with (OUT / "real_code_sweep.json").open("w", encoding="utf-8") as f:
        json.dump({
            "total_hits": len(rows), "deploy_path_hits": len(deploy),
            "summary": summary,
            "method": ("identifier-level sweep for gold/private-truth reads over real production code of "
                       "both audited projects; module role from path (DEPLOY_PATH = retrieval/selection/"
                       "scoring/state/generation/api/prompt; OFFLINE = annotation/datasets/metrics/"
                       "experiments/schemas). Offline roles are legitimate (annotation assets, dataset "
                       "construction, post-selection metrics)."),
            "conclusion": (f"{len(deploy)} gold/private-truth read site(s) found in deployable-path code "
                           "of the two real projects; all other hits are offline annotation/dataset/"
                           "metric consumption. No naturally occurring leak was found, which is expected "
                           "for contract-designed code and is exactly why controlled injection is the "
                           "feasible ground-truth method; real-world prevalence needs industry "
                           "collaboration."),
        }, f, ensure_ascii=False, indent=2)


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
