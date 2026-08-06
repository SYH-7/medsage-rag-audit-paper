from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

csv.field_size_limit(10_000_000)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_id(value: str) -> str:
    return "h_" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def canonicalize_label_set(value: str | list[str]) -> tuple[str, ...]:
    if isinstance(value, list):
        raw_parts: list[str] = []
        for item in value:
            raw_parts.extend(re.split(r"[,，;；|]", str(item)))
    else:
        raw_parts = re.split(r"[,，;；|]", str(value))
    labels = {part.strip().lower() for part in raw_parts if part.strip()}
    return tuple(sorted(labels))


@dataclass
class GoldLoadResult:
    status: str
    query_gold: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence_gold: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    source_rows: list[dict[str, Any]] = field(default_factory=list)
    alignment_rows: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    unresolved_pairs: list[dict[str, Any]] = field(default_factory=list)
    used_rows: list[dict[str, Any]] = field(default_factory=list)
    query_stats: dict[str, int] = field(default_factory=dict)
    evidence_stats: dict[str, int] = field(default_factory=dict)
    adjudication_status: str = "NOT_FOUND"


def row_hash(row: dict[str, Any]) -> str:
    safe = {k: row.get(k, "") for k in sorted(row) if k not in {"question", "content"}}
    return hashlib.sha256(json.dumps(safe, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _parse_relevance(value: Any) -> int | None:
    text = str(value if value is not None else "").strip()
    if text == "":
        return None
    return int(float(text))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _find_human_adjudication(ann_dir: Path) -> dict[str, Any]:
    candidates = [
        ann_dir / "adjudication_queries_template.csv",
        ann_dir / "adjudication_evidence_template.csv",
        ann_dir / "adjudication_queries_final.csv",
        ann_dir / "adjudication_evidence_final.csv",
        ann_dir / "query_adjudication_final.csv",
        ann_dir / "evidence_adjudication_final.csv",
    ]
    found = []
    for path in candidates:
        if not path.exists():
            continue
        rows = _read_csv_rows(path)[:50]
        adjudicators = {str(r.get("adjudicator", "")).strip().upper() for r in rows}
        is_ai = any("AI" in a or "DRAFT" in a or "REVIEW" in a for a in adjudicators if a)
        has_final = any(k.startswith("final_") for k in (rows[0].keys() if rows else []))
        if has_final and rows and not is_ai:
            found.append(str(path))
    return {"status": "FOUND" if found else "NOT_FOUND", "files": found}


def load_human_gold(root: Path, candidate_pool: Path, out_dir: Path) -> GoldLoadResult:
    ann_dir = root / "data" / "annotations" / "formal300"
    query_files = [ann_dir / "query_annotation_a.csv", ann_dir / "query_annotation_b.csv"]
    evidence_files = [ann_dir / "evidence_annotation_a.csv", ann_dir / "evidence_annotation_b.csv"]
    qids_in_pool: set[str] = set()
    pairs_in_pool: set[tuple[str, str]] = set()
    with candidate_pool.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            qid, doc = str(rec["qid"]), str(rec["doc_id"])
            qids_in_pool.add(qid)
            pairs_in_pool.add((qid, doc))

    result = GoldLoadResult(status="REPRODUCED")
    adjudication = _find_human_adjudication(ann_dir)
    result.adjudication_status = str(adjudication["status"])
    query_by_annotator: dict[str, dict[str, dict[str, str]]] = {}
    for path in query_files:
        if not path.exists():
            continue
        annotator = "A" if path.stem.lower().endswith("_a") else "B"
        result.source_rows.append({"source_file": str(path), "sha256": sha256_file(path), "annotation_version": "formal300", "kind": "query"})
        for row in _read_csv_rows(path):
            qid = str(row.get("qid", ""))
            if qid in qids_in_pool and row.get("query_states", "") != "":
                query_by_annotator.setdefault(qid, {})[annotator] = row

    query_reanalysis = []
    normalization_recovered = []
    true_unresolved = []
    query_stats = {
        "query_annotation_total_qids": len(query_by_annotator),
        "query_raw_conflict_qids": 0,
        "query_normalized_consistent_qids": 0,
        "query_adjudicated_usable_qids": 0,
        "query_unresolved_qids": 0,
        "query_states_real_conflict_qids": 0,
        "risk_types_real_conflict_qids": 0,
        "query_fully_consistent_qids": 0,
        "query_normalization_recovered_qids": 0,
    }
    for qid, ann in sorted(query_by_annotator.items()):
        a, b = ann.get("A"), ann.get("B")
        if not a or not b:
            reason = "missing_query_annotator"
            query_stats["query_unresolved_qids"] += 1
            row = {"qid_hash": hash_id(qid), "doc_id_hash": "", "level": "query", "category": reason, "row_hash": row_hash(a or b or {})}
            query_reanalysis.append(row)
            true_unresolved.append(row)
            continue
        a_states, b_states = canonicalize_label_set(a.get("query_states", "")), canonicalize_label_set(b.get("query_states", ""))
        a_risk, b_risk = canonicalize_label_set(a.get("risk_types", "")), canonicalize_label_set(b.get("risk_types", ""))
        raw_diff = (a.get("query_states", "") != b.get("query_states", "")) or (a.get("risk_types", "") != b.get("risk_types", ""))
        if raw_diff:
            query_stats["query_raw_conflict_qids"] += 1
        if a_states == b_states and a_risk == b_risk:
            query_stats["query_normalized_consistent_qids"] += 1
            query_stats["query_adjudicated_usable_qids"] += 1
            if raw_diff:
                category = "raw_string_diff_normalized_same"
                query_stats["query_normalization_recovered_qids"] += 1
                normalization_recovered.append({"qid_hash": hash_id(qid), "doc_id_hash": "", "level": "query", "category": category, "row_hash": row_hash(b)})
            else:
                category = "fully_consistent"
                query_stats["query_fully_consistent_qids"] += 1
            result.query_gold[qid] = {"query_states": a_states, "risk_types": a_risk}
            query_reanalysis.append({"qid_hash": hash_id(qid), "doc_id_hash": "", "level": "query", "category": category, "row_hash": row_hash(b)})
        else:
            reasons = []
            if a_states != b_states:
                reasons.append("query_states_real_conflict")
                query_stats["query_states_real_conflict_qids"] += 1
            if a_risk != b_risk:
                reasons.append("risk_types_real_conflict")
                query_stats["risk_types_real_conflict_qids"] += 1
            query_stats["query_unresolved_qids"] += 1
            for reason in reasons:
                row = {"qid_hash": hash_id(qid), "doc_id_hash": "", "level": "query", "category": reason, "row_hash": row_hash(b)}
                query_reanalysis.append(row)
                true_unresolved.append(row)
                result.unresolved_pairs.append({"qid_hash": hash_id(qid), "doc_id_hash": "", "reason": reason, "row_hash": row_hash(b)})

    evidence_by_annotator: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    evidence_source: dict[tuple[str, str], dict[str, str]] = {}
    for path in evidence_files:
        if not path.exists():
            continue
        annotator = "A" if path.stem.lower().endswith("_a") else "B"
        result.source_rows.append({"source_file": str(path), "sha256": sha256_file(path), "annotation_version": "formal300", "kind": "evidence"})
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                qid, doc = str(row.get("qid", "")), str(row.get("doc_id", ""))
                if (qid, doc) in pairs_in_pool and row.get("relevance", "") != "":
                    evidence_by_annotator.setdefault((qid, doc), {})[annotator] = row
                    evidence_source.setdefault((qid, doc), {"source_file": str(path), "row_hash": row_hash(row)})

    evidence_reanalysis = []
    evidence_stats = {
        "evidence_annotation_raw_pairs": len(evidence_by_annotator),
        "evidence_raw_conflict_pairs": 0,
        "evidence_normalized_consistent_pairs": 0,
        "evidence_adjudicated_usable_pairs": 0,
        "evidence_unresolved_pairs": 0,
        "evidence_relevance_conflict_pairs": 0,
        "evidence_supported_states_conflict_pairs": 0,
        "evidence_fully_consistent_pairs": 0,
        "evidence_normalization_recovered_pairs": 0,
    }
    for (qid, doc), ann in sorted(evidence_by_annotator.items()):
        a, b = ann.get("A"), ann.get("B")
        qh, dh = hash_id(qid), hash_id(doc)
        if not a or not b:
            reason = "missing_evidence_annotator"
            evidence_stats["evidence_unresolved_pairs"] += 1
            row = {"qid_hash": qh, "doc_id_hash": dh, "level": "evidence", "category": reason, "row_hash": row_hash(a or b or {})}
            evidence_reanalysis.append(row)
            true_unresolved.append(row)
            continue
        a_rel, b_rel = _parse_relevance(a.get("relevance")), _parse_relevance(b.get("relevance"))
        a_states = canonicalize_label_set(a.get("covered_states") or a.get("supported_states") or "")
        b_states = canonicalize_label_set(b.get("covered_states") or b.get("supported_states") or "")
        raw_states_diff = (a.get("covered_states", "") != b.get("covered_states", ""))
        raw_diff = a.get("relevance", "") != b.get("relevance", "") or raw_states_diff
        if raw_diff:
            evidence_stats["evidence_raw_conflict_pairs"] += 1
        if a_rel != b_rel:
            reason = "relevance_conflict"
            evidence_stats["evidence_relevance_conflict_pairs"] += 1
            evidence_stats["evidence_unresolved_pairs"] += 1
            row = {"qid_hash": qh, "doc_id_hash": dh, "level": "evidence", "category": reason, "row_hash": row_hash(b)}
            evidence_reanalysis.append(row)
            true_unresolved.append(row)
            result.unresolved_pairs.append({"qid_hash": qh, "doc_id_hash": dh, "reason": reason, "row_hash": row_hash(b)})
        elif a_states != b_states:
            reason = "supported_states_real_conflict"
            evidence_stats["evidence_supported_states_conflict_pairs"] += 1
            evidence_stats["evidence_unresolved_pairs"] += 1
            row = {"qid_hash": qh, "doc_id_hash": dh, "level": "evidence", "category": reason, "row_hash": row_hash(b)}
            evidence_reanalysis.append(row)
            true_unresolved.append(row)
            result.unresolved_pairs.append({"qid_hash": qh, "doc_id_hash": dh, "reason": reason, "row_hash": row_hash(b)})
        else:
            evidence_stats["evidence_normalized_consistent_pairs"] += 1
            evidence_stats["evidence_adjudicated_usable_pairs"] += 1
            if raw_states_diff:
                category = "raw_string_diff_normalized_same"
                evidence_stats["evidence_normalization_recovered_pairs"] += 1
                normalization_recovered.append({"qid_hash": qh, "doc_id_hash": dh, "level": "evidence", "category": category, "row_hash": row_hash(b)})
            else:
                category = "fully_consistent"
                evidence_stats["evidence_fully_consistent_pairs"] += 1
            result.evidence_gold[(qid, doc)] = {"relevance": a_rel, "supported_states": a_states}
            evidence_reanalysis.append({"qid_hash": qh, "doc_id_hash": dh, "level": "evidence", "category": category, "row_hash": row_hash(b)})

    result.query_stats = query_stats
    result.evidence_stats = evidence_stats

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        out_dir / "GOLD_CONFLICT_REANALYSIS.csv",
        [*query_reanalysis, *evidence_reanalysis],
        ["qid_hash", "doc_id_hash", "level", "category", "row_hash"],
    )
    _write_csv(
        out_dir / "NORMALIZATION_RECOVERED_ROWS.csv",
        normalization_recovered,
        ["qid_hash", "doc_id_hash", "level", "category", "row_hash"],
    )
    _write_csv(
        out_dir / "TRUE_UNRESOLVED_ROWS.csv",
        true_unresolved,
        ["qid_hash", "doc_id_hash", "level", "category", "row_hash"],
    )
    _write_csv(
        out_dir / "QUERY_CONFLICT_SUMMARY.csv",
        [{"metric": k, "value": v} for k, v in query_stats.items()] + [{"metric": "human_adjudication_status", "value": result.adjudication_status}],
        ["metric", "value"],
    )
    _write_csv(
        out_dir / "EVIDENCE_CONFLICT_SUMMARY.csv",
        [{"metric": k, "value": v} for k, v in evidence_stats.items()] + [{"metric": "human_adjudication_status", "value": result.adjudication_status}],
        ["metric", "value"],
    )
    with (out_dir / "GOLD_SOURCE_MAP.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["source_file", "sha256", "annotation_version", "kind"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result.source_rows)
    aligned = []
    for (qid, doc), val in result.evidence_gold.items():
        aligned.append({"qid_hash": hash_id(qid), "doc_id_hash": hash_id(doc), "has_evidence_gold": True})
    result.alignment_rows = aligned
    with (out_dir / "GOLD_CANDIDATE_ALIGNMENT.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["qid_hash", "doc_id_hash", "has_evidence_gold"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(aligned)
    summary = {
        "status": result.status if result.query_gold and result.evidence_gold else "BLOCKED_MISSING_HUMAN_GOLD",
        "candidate_pool_qids": len(qids_in_pool),
        "query_annotation_total_qids": query_stats["query_annotation_total_qids"],
        "query_normalized_consistent_qids": query_stats["query_normalized_consistent_qids"],
        "query_adjudicated_usable_qids": query_stats["query_adjudicated_usable_qids"],
        "query_unresolved_qids": query_stats["query_unresolved_qids"],
        "query_gold_qids": len(result.query_gold),
        "evidence_annotation_raw_pairs": evidence_stats["evidence_annotation_raw_pairs"],
        "evidence_normalized_consistent_pairs": evidence_stats["evidence_normalized_consistent_pairs"],
        "evidence_adjudicated_usable_pairs": evidence_stats["evidence_adjudicated_usable_pairs"],
        "evidence_unresolved_pairs": evidence_stats["evidence_unresolved_pairs"],
        "evidence_gold_pairs": len(result.evidence_gold),
        "aligned_pairs": len(aligned),
        "human_adjudication_status": result.adjudication_status,
    }
    (out_dir / "GOLD_COVERAGE_SUMMARY.csv").write_text(
        "metric,value\n" + "\n".join(f"{k},{v}" for k, v in summary.items()) + "\n",
        encoding="utf-8-sig",
    )
    with (out_dir / "GOLD_HASH_MANIFEST.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["qid_hash", "doc_id_hash", "source"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for qid, doc in result.evidence_gold:
            writer.writerow({"qid_hash": hash_id(qid), "doc_id_hash": hash_id(doc), "source": "formal300_human_annotation"})
    with (out_dir / "GOLD_EXCLUDED_UNRESOLVED.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["qid_hash", "doc_id_hash", "reason", "row_hash"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result.unresolved_pairs)
    used = []
    for (qid, doc), src in evidence_source.items():
        if (qid, doc) in result.evidence_gold:
            used.append({"qid_hash": hash_id(qid), "doc_id_hash": hash_id(doc), "source_file": src["source_file"], "row_hash": src["row_hash"], "gold_status": "REAL_HUMAN_GOLD_BENCHMARK"})
    result.used_rows = used
    with (out_dir / "GOLD_USED_IN_BENCHMARK.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["qid_hash", "doc_id_hash", "source_file", "row_hash", "gold_status"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(used)
    with (out_dir / "GOLD_USAGE_TRACE.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["source_id", "qid_hash", "doc_id_hash", "source_file", "row_hash", "usage_scope"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for idx, row in enumerate(used, 1):
            writer.writerow({"source_id": f"human_gold_{idx:06d}", **{k: row[k] for k in ["qid_hash", "doc_id_hash", "source_file", "row_hash"]}, "usage_scope": "injector_and_evaluator_only"})
    (out_dir / "GOLD_PROVENANCE.md").write_text(
        "# Gold Provenance\n\n- status: REAL_HUMAN_GOLD_BENCHMARK\n- source: formal300 human query/evidence annotations\n- conflict_policy: conflicting query qids and evidence pairs are excluded\n- query_gold_participates_in_injection: false\n- evidence_gold_pairs_entering_benchmark: "
        f"{len(result.evidence_gold)}\n- human_adjudication_status: {result.adjudication_status}\n- label_normalization: split on comma/Chinese comma/semicolon/Chinese semicolon/pipe; strip; deduplicate; lower-case controlled labels; sort\n- rank_based_gold_construction: false\n- exported_private_label_values: false\n",
        encoding="utf-8",
    )
    (out_dir / "GOLD_LOADING_STATUS.md").write_text(
        f"# Gold Loading Status\n\n- status: {summary['status']}\n- query_gold_qids: {summary['query_gold_qids']}\n- evidence_gold_pairs: {summary['evidence_gold_pairs']}\n- exported_private_label_values: false\n",
        encoding="utf-8",
    )
    result.status = str(summary["status"])
    return result
