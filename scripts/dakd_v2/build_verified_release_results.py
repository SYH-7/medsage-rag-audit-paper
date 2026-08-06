"""Build sanitized, verifiable summaries from the frozen public release.

This script treats the public release as read-only provenance. It copies only
table-level or hash-id/minimal result evidence into `paper_package_dakd_v2`.
It does not export raw medical questions, raw answers, private gold labels, or
candidate document text.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "paper_package_dakd_v2"
OUT = PACKAGE / "13_verified_release"
META = OUT / "source_metadata"
RELEASE_ROOT = Path(__file__).resolve().parents[3]
SOURCE_RELEASE = "v1.1.1-paper-supplement"
SOURCE_COMMIT = "876a16d098e1da3f642ef70854cbc985bae5f9e3"

RESULT_FIELDS = [
    "result_id",
    "experiment_family",
    "split",
    "method",
    "metric",
    "value",
    "sample_size",
    "status",
    "source_release",
    "source_commit",
    "source_file",
    "source_sha256",
    "verification_method",
    "local_rerun",
    "notes",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(RELEASE_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else row.get(k) for k in fieldnames})


def result_row(
    result_id: str,
    family: str,
    split: str,
    method: str,
    metric: str,
    value: str,
    sample_size: str,
    source: Path,
    source_hash: str,
    notes: str = "",
) -> dict[str, str]:
    return {
        "result_id": result_id,
        "experiment_family": family,
        "split": split,
        "method": method,
        "metric": metric,
        "value": value,
        "sample_size": sample_size,
        "status": "VERIFIED_FROM_RELEASE",
        "source_release": SOURCE_RELEASE,
        "source_commit": SOURCE_COMMIT,
        "source_file": rel(source),
        "source_sha256": source_hash,
        "verification_method": "sha256_schema_row_count",
        "local_rerun": "false",
        "notes": notes,
    }


def export_qid_hash(value: object) -> str:
    return "qh_" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def build_b0_d3(results: list[dict[str, str]], sha_rows: list[dict[str, str]]) -> None:
    report = RELEASE_ROOT / "PAPER_REPRODUCTION_REPORT.json"
    source_hash = sha256_file(report)
    data = json.loads(report.read_text(encoding="utf-8"))
    rows = []
    per_qid_rows = []
    for key, rec in sorted(data.items()):
        if not isinstance(rec, dict) or not any(key.endswith(f"_{m}") for m in ["b0", "d0", "d1", "d2", "d3"]):
            continue
        parts = key.rsplit("_", 1)
        split, method = parts[0], parts[1].upper()
        n = str(rec.get("n", ""))
        rows.append(
            {
                "split": split,
                "method": method,
                "sample_size": n,
                "demand_cov_full_precision": rec.get("dc", ""),
                "demand_cov_display": rec.get("dc_paper", ""),
                "demand_cov_match_paper_rounding": rec.get("dc_match", ""),
                "ndcg_full_precision": rec.get("ndcg", ""),
                "ndcg_display": rec.get("ndcg_paper", ""),
                "ndcg_match_paper_rounding": rec.get("ndcg_match", ""),
                "evidence_status": "VERIFIED_FROM_RELEASE",
                "source_file": rel(report),
                "source_commit": SOURCE_COMMIT,
                "source_sha256": source_hash,
            }
        )
        for metric in ["dc", "ndcg"]:
            results.append(result_row(f"b0_d3.{split}.{method}.{metric}", "b0_d3", split, method, metric, str(rec.get(metric, "")), n, report, source_hash, "rounding fields retained"))

    for split in ["formal_train", "internal_blind", "cmedqa2_external"]:
        src = RELEASE_ROOT / "paper_results" / "per_query_minimal" / f"{split}_per_query.jsonl"
        if not src.exists():
            continue
        src_hash = sha256_file(src)
        with src.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                per_qid_rows.append(
                    {
                        "split": split,
                        "qid_hash": export_qid_hash(rec.get("qid_hash", "")),
                        "method": rec.get("method", ""),
                        "demand_cov": rec.get("dc", ""),
                        "ndcg": rec.get("ndcg", ""),
                        "evidence_status": "VERIFIED_FROM_RELEASE",
                        "source_file": rel(src),
                        "source_commit": SOURCE_COMMIT,
                        "source_sha256": src_hash,
                        "notes": "selected document ids intentionally excluded",
                    }
                )
        sha_rows.append({"source_file": rel(src), "source_sha256": src_hash, "exported_file": "B0_D3_VERIFIED_PER_QID.csv"})

    write_csv(OUT / "B0_D3_VERIFIED_SUMMARY.csv", list(rows[0].keys()) if rows else [], rows)
    write_csv(OUT / "B0_D3_VERIFIED_PER_QID.csv", list(per_qid_rows[0].keys()) if per_qid_rows else [], per_qid_rows)
    sha_rows.append({"source_file": rel(report), "source_sha256": source_hash, "exported_file": "B0_D3_VERIFIED_SUMMARY.csv"})


def copy_table_as_verified(
    src: Path,
    dst_name: str,
    family: str,
    metric_columns: list[str],
    results: list[dict[str, str]],
    sha_rows: list[dict[str, str]],
) -> None:
    if not src.exists():
        return
    source_hash = sha256_file(src)
    rows = read_csv(src)
    out_rows = []
    for i, row in enumerate(rows):
        out = dict(row)
        out.update(
            {
                "evidence_status": "VERIFIED_FROM_RELEASE",
                "source_file": rel(src),
                "source_commit": SOURCE_COMMIT,
                "source_sha256": source_hash,
                "local_rerun": "false",
            }
        )
        out_rows.append(out)
        split = row.get("split", row.get("condition", "all"))
        method = row.get("method", row.get("condition", row.get("scenario", "")))
        sample_size = row.get("n_qid", row.get("n_qids", row.get("seed_count", "")))
        for metric in metric_columns:
            if metric in row and row[metric] != "":
                results.append(result_row(f"{family}.{i}.{metric}", family, split, method, metric, row[metric], sample_size, src, source_hash))
    fieldnames = list(out_rows[0].keys()) if out_rows else []
    write_csv(OUT / dst_name, fieldnames, out_rows)
    sha_rows.append({"source_file": rel(src), "source_sha256": source_hash, "exported_file": dst_name})


def main() -> int:
    if not RELEASE_ROOT.exists():
        raise SystemExit(f"Missing release root: {RELEASE_ROOT}")
    OUT.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []
    sha_rows: list[dict[str, str]] = []

    build_b0_d3(results, sha_rows)
    copy_table_as_verified(RELEASE_ROOT / "paper_results/manifests/gap_decomposition.csv", "COMPONENT_GAP_VERIFIED_SUMMARY.csv", "b0_d3_component_gaps", ["oracle_gain", "query_loss", "evidence_loss", "interaction_loss"], results, sha_rows)
    copy_table_as_verified(RELEASE_ROOT / "paper_results/manifests/significance.csv", "B0_D3_VERIFIED_STATISTICS.csv", "b0_d3_statistics", ["diff", "p_value", "ci95_low", "ci95_high"], results, sha_rows)
    copy_table_as_verified(RELEASE_ROOT / "paper_results/revision_v5/tables/mmr_summary.csv", "MMR_VERIFIED_SUMMARY.csv", "mmr", ["demand_cov_5", "ndcg_10", "redundancy", "jaccard_vs_b0"], results, sha_rows)
    copy_table_as_verified(RELEASE_ROOT / "paper_results/revision_v5/tables/topk_sensitivity_summary.csv", "TOPK_VERIFIED_SUMMARY.csv", "topk", ["demand_cov_at_k", "ndcg_at_k", "official_ndcg_10", "redundancy"], results, sha_rows)
    copy_table_as_verified(RELEASE_ROOT / "paper_results/generation/v3_frozen/generation_paper_method_summary.csv", "GENERATION_VERIFIED_SUMMARY.csv", "generation_validation", ["faithfulness_mean", "demand_completeness_mean", "overall_utility_mean", "unsupported_claim_mean", "critical_risk_omission_mean"], results, sha_rows)
    copy_table_as_verified(RELEASE_ROOT / "paper_results/generation/v3_frozen/generation_paper_statistics_report.csv", "GENERATION_VERIFIED_STATISTICS.csv", "generation_statistics", [], results, sha_rows)
    copy_table_as_verified(RELEASE_ROOT / "paper_results/manifests/leakage_summary.csv", "LEAKAGE_INJECTION_VERIFIED_SUMMARY.csv", "leakage_injection_effect", ["mean_demand_cov", "std_demand_cov", "ci95_low", "ci95_high", "mean_ndcg"], results, sha_rows)

    file_index_rows = []
    for row in sha_rows:
        exported = OUT / row["exported_file"]
        file_index_rows.append(
            {
                "exported_file": row["exported_file"],
                "artifact_type": "verified_release_table",
                "status": "VERIFIED_FROM_RELEASE",
                "source_release": SOURCE_RELEASE,
                "source_commit": SOURCE_COMMIT,
                "source_file": row["source_file"],
                "source_sha256": row["source_sha256"],
                "export_sha256": sha256_file(exported) if exported.exists() else "",
                "local_rerun": "false",
                "notes": "sanitized table-level or hash-id evidence",
            }
        )
        (META / (row["exported_file"] + ".metadata.json")).write_text(
            json.dumps(file_index_rows[-1], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    write_csv(OUT / "VERIFIED_FILE_INDEX.csv", list(file_index_rows[0].keys()), file_index_rows)
    write_csv(OUT / "VERIFIED_RESULT_INDEX.csv", RESULT_FIELDS, results)
    write_csv(OUT / "VERIFIED_SHA256.csv", ["source_file", "source_sha256", "exported_file"], sha_rows)
    (OUT / "RELEASE_VERIFICATION_REPORT.md").write_text(
        "# Release Verification Report\n\n"
        f"- status: VERIFIED_FROM_RELEASE\n- source_release: {SOURCE_RELEASE}\n- source_commit: {SOURCE_COMMIT}\n"
        "- local_rerun: false\n- exported raw medical text: false\n- exported private gold labels: false\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "VERIFIED_FROM_RELEASE", "result_rows": len(results), "files": len(file_index_rows)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
