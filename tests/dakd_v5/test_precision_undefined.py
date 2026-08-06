# -*- coding: utf-8 -*-
"""v2.0.4: precision-undefined regression tests (TP+FP=0)."""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
REPO = os.path.join(os.path.dirname(__file__), "..", "..")

from benchmark_v3.blind_evaluator import metrics  # noqa: E402

AST_ROWS = [{"tp": 0, "fp": 0, "tn": 60, "fn": 36}]


def test_precision_none_when_no_positive():
    m = metrics(AST_ROWS)
    assert m["precision"] is None  # TP+FP=0 -> undefined, not 1.0


def test_precision_defined_flag():
    m = metrics(AST_ROWS)
    assert m["precision_defined"] is False
    m2 = metrics([{"tp": 5, "fp": 1, "tn": 59, "fn": 31}])
    assert m2["precision_defined"] is True
    assert m2["precision"] == 5 / 6


def test_f1_zero_when_no_positive():
    m = metrics(AST_ROWS)
    assert m["f1"] == 0.0
    assert m["recall"] == 0.0
    assert m["specificity"] == 1.0


def test_csv_export_is_not_1_0():
    # DictWriter writes None as an empty field, never "1.0".
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["detector", "precision", "precision_defined"])
    w.writeheader()
    m = metrics(AST_ROWS)
    w.writerow({"detector": "ast_static_dataflow", "precision": m["precision"],
                "precision_defined": m["precision_defined"]})
    out = buf.getvalue()
    assert "1.0" not in out
    assert "ast_static_dataflow,," in out  # precision empty field


def test_public_table_render_em_dash():
    # Human-readable rendering: undefined precision displays as an em dash,
    # and the machine table (TABLE_04) stores an empty/NA value, not 1.0.
    tbl = os.path.join(REPO, "results", "01_main_audit", "author_tables", "TABLE_04_DETECTION_MAIN.csv")
    with open(tbl, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["detector"] == "ast_static_dataflow":
                assert row["precision"] in ("", "NA", "NaN", "null")
                assert row["precision"] != "1.0"
                assert row["precision_defined"] == "False"
                assert row["f1"] == "0.0"
                assert row["specificity"] == "1.0"


def test_cross_pipeline_ast_precision_not_1_0():
    tbl = os.path.join(REPO, "results", "03_cross_pipeline", "detection",
                       "cross_pipeline_detection_summary.csv")
    with open(tbl, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["detector"] == "ast_static_dataflow":
                assert row["precision"] in ("", "NA", "NaN", "null")
                assert row["precision"] != "1.0"
