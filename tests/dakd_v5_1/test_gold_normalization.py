from __future__ import annotations

import csv
import json
import shutil
import uuid
from pathlib import Path

from benchmark_v3.private_gold_loader import canonicalize_label_set, load_human_gold


ROOT = Path(__file__).resolve().parents[2]


def local_tmp() -> Path:
    path = ROOT / ".local_test_tmp" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_tmp(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_root(tmp_path: Path, *, qa: str, qb: str, ra: str = "", rb: str = "", ea: str = "1", eb: str = "1") -> tuple[Path, Path]:
    root = tmp_path
    ann = root / "data" / "annotations" / "formal300"
    pool = root / "pool.jsonl"
    pool.write_text(json.dumps({"qid": "q1", "doc_id": "d1"}, ensure_ascii=False) + "\n", encoding="utf-8")
    qbase = {"qid": "q1", "question": "q", "key_states": "", "complexity_type": "", "annotator": "", "notes": ""}
    ebase = {"annotation_id": "q1__d1", "qid": "q1", "question": "q", "doc_id": "d1", "content": "c", "risk_types": "", "necessary_safety": "", "annotator": "", "notes": ""}
    write_csv(ann / "query_annotation_a.csv", [qbase | {"query_states": qa, "risk_types": ra}])
    write_csv(ann / "query_annotation_b.csv", [qbase | {"query_states": qb, "risk_types": rb}])
    write_csv(ann / "evidence_annotation_a.csv", [ebase | {"relevance": ea, "covered_states": qa}])
    write_csv(ann / "evidence_annotation_b.csv", [ebase | {"relevance": eb, "covered_states": qb}])
    return root, pool


def test_label_order_does_not_create_conflict():
    tmp_path = local_tmp()
    root, pool = make_root(tmp_path, qa="symptom;duration", qb="duration;symptom")
    result = load_human_gold(root, pool, tmp_path / "out")
    clean_tmp(tmp_path)
    assert "q1" in result.query_gold
    assert ("q1", "d1") in result.evidence_gold


def test_duplicate_labels_do_not_create_conflict():
    tmp_path = local_tmp()
    root, pool = make_root(tmp_path, qa="symptom;symptom;duration", qb="duration;symptom")
    result = load_human_gold(root, pool, tmp_path / "out")
    clean_tmp(tmp_path)
    assert result.query_gold["q1"]["query_states"] == ("duration", "symptom")


def test_whitespace_does_not_create_conflict():
    tmp_path = local_tmp()
    root, pool = make_root(tmp_path, qa=" symptom \uff1b duration ", qb="duration;symptom")
    result = load_human_gold(root, pool, tmp_path / "out")
    clean_tmp(tmp_path)
    assert "q1" in result.query_gold


def test_relevance_difference_is_real_conflict():
    tmp_path = local_tmp()
    root, pool = make_root(tmp_path, qa="symptom", qb="symptom", ea="1", eb="2")
    result = load_human_gold(root, pool, tmp_path / "out")
    clean_tmp(tmp_path)
    assert ("q1", "d1") not in result.evidence_gold
    assert any(r["reason"] == "relevance_conflict" for r in result.unresolved_pairs)


def test_supported_state_set_difference_is_real_conflict():
    tmp_path = local_tmp()
    root, pool = make_root(tmp_path, qa="symptom;duration", qb="symptom")
    result = load_human_gold(root, pool, tmp_path / "out")
    clean_tmp(tmp_path)
    assert ("q1", "d1") not in result.evidence_gold
    assert any(r["reason"] == "supported_states_real_conflict" for r in result.unresolved_pairs)


def test_no_annotator_silent_overwrite():
    tmp_path = local_tmp()
    root, pool = make_root(tmp_path, qa="symptom", qb="duration")
    result = load_human_gold(root, pool, tmp_path / "out")
    clean_tmp(tmp_path)
    assert "q1" not in result.query_gold
    assert any(r["reason"] == "query_states_real_conflict" for r in result.unresolved_pairs)


def test_canonicalize_label_set_splitters_and_tuple():
    assert canonicalize_label_set("B\uff0ca;A\uff1bb|c") == ("a", "b", "c")
