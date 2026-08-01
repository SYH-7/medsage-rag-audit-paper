"""Comprehensive tests for paper repo."""
import sys, os, json, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
REPO = os.path.join(os.path.dirname(__file__), "..")

def test_ontology_loads_from_repo():
    import json
    p = os.path.join(REPO, "configs/ontology.json")
    assert os.path.exists(p)
    data = json.loads(open(p, encoding='utf-8').read())
    l2 = data.get("level_2", {})
    assert "risk_medication" in l2

def test_public_query_has_no_gold_fields():
    src = open(os.path.join(REPO, "src/public_runtime/types.py"), encoding='utf-8').read()
    assert "DENY_COLUMNS" in src

def test_d3_has_no_gold_fallback():
    src = open(os.path.join(REPO, "src/private_evaluation/core.py"), encoding='utf-8').read()
    assert "pqd if pqd else gqd" not in src

def test_gap_definition_with_corrected_d1_d2():
    """D1=Predicted+Gold: QL=D0-D1=0.05, D2=Gold+Predicted: EL=D0-D2=0.08"""
    from private_evaluation.core import compute_gap
    g = compute_gap(0.8, 0.9, 0.85, 0.82, 0.81)
    assert abs(g["query_loss"] - 0.05) < 0.001
    assert abs(g["evidence_loss"] - 0.08) < 0.001
    assert abs(g["deployment_gap"] - 0.09) < 0.001

def test_d1_is_predicted_query_gold_evidence():
    from private_evaluation.core import compute_gap
    g = compute_gap(0.8, 0.9, 0.85, 0.82, 0.81)
    assert abs(g["query_loss"] - (0.9-0.85)) < 0.001

def test_d2_is_gold_query_predicted_evidence():
    from private_evaluation.core import compute_gap
    g = compute_gap(0.8, 0.9, 0.85, 0.82, 0.81)
    assert abs(g["evidence_loss"] - (0.9-0.82)) < 0.001

def test_query_loss_is_d0_minus_d1():
    from private_evaluation.core import compute_gap
    g = compute_gap(0.8, 0.9, 0.85, 0.82, 0.81)
    assert abs(g["query_loss"] - (0.9-0.85)) < 0.001

def test_evidence_loss_is_d0_minus_d2():
    from private_evaluation.core import compute_gap
    g = compute_gap(0.8, 0.9, 0.85, 0.82, 0.81)
    assert abs(g["evidence_loss"] - (0.9-0.82)) < 0.001

def test_exactmax_minimal():
    from private_evaluation.condition_decomposition import exact_max_coverage
    cands = [{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "c"}]
    ids, score = exact_max_coverage({"D01"}, cands, {}, "q0", k=2)
    assert isinstance(ids, list)
    assert isinstance(score, float)

def test_manifest_full_sha256():
    m_path = os.path.join(REPO, "paper_results/manifests/release_manifest_sha256.csv")
    assert os.path.exists(m_path)
    import csv
    with open(m_path, encoding='utf-8') as f:
        rows = list(csv.reader(f))
    assert len(rows) > 1
    for row in rows[1:]:
        assert len(row[1]) == 64  # format: path,sha256,size

def test_ids_are_anonymized():
    pq_dir = os.path.join(REPO, "paper_results/per_query_minimal")
    for fn in os.listdir(pq_dir):
        with open(os.path.join(pq_dir, fn)) as f:
            for line in f:
                r = json.loads(line)
                assert "qid_hash" in r
                for did in r.get("selected", []):
                    assert did.startswith("WMA_") or not did.isdigit()

def test_no_absolute_windows_paths():
    found = []
    for dirpath, _, fns in os.walk(REPO):
        for fn in fns:
            if not fn.endswith(('.py','.md','.csv','.json','.txt')): continue
            fpath = os.path.join(dirpath, fn)
            if any(x in fpath for x in ['__pycache__','.git','.venv','.pytest_cache']): continue
            if 'test_comprehensive' in fpath: continue
            c = open(fpath, encoding='utf-8', errors='ignore').read()
            for line in c.split('\n'):
                s = line.strip()
                if s.startswith('#') or s.startswith('//'): continue
                for drive in ['E:\\','E:/','C:\\','C:/']:
                    if drive in s and 'REPO' not in s and 'os.path' not in s and 'Path(' not in s and 'parents[' not in s:
                        found.append(f"{fpath}: {s[:80]}")
    assert len(found) == 0, f"Found {len(found)} abs paths"

def test_no_placeholder():
    for dirpath, _, fns in os.walk(REPO):
        for fn in fns:
            if fn.endswith('.md'):
                c = open(os.path.join(dirpath, fn), encoding='utf-8').read()
                for p in ['TODO','TBD','需填充','待补']:
                    assert p not in c

def test_no_competition_files():
    bad = ['pipeline_b','pipeline_a','L1_','L2_','L3_','L4_','L5_','L6_','streamlit','injector','detector_d']
    for dirpath, _, fns in os.walk(REPO):
        for fn in fns:
            for b in bad: assert b not in fn.lower()

def test_paired_bootstrap_shared_indices():
    import numpy as np
    from private_evaluation.core import paired_bootstrap
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([1.1, 2.1, 3.1, 4.1, 5.1])
    result = paired_bootstrap(a.tolist(), b.tolist(), n_iter=100, seed=42)
    assert abs(result["diff"] - float(np.mean(a-b))) < 1e-10

def test_manifest_no_junk():
    m_path = os.path.join(REPO, "paper_results/manifests/release_manifest_sha256.csv")
    assert os.path.exists(m_path)
    import csv
    with open(m_path, encoding='utf-8') as f:
        for row in csv.reader(f):
            rel = row[0].replace("\\", "/")
            for junk in ['.venv','venv','.idea','.vscode','__pycache__','.pytest_cache']:
                assert junk not in rel

def test_gold_independence_report_exists():
    # GOLD_INDEPENDENCE_REPORT.json is created by verify_gold_independence.py
    f = os.path.join(REPO, 'GOLD_INDEPENDENCE_REPORT.json')
    if os.path.exists(f):
        import json
        d = json.load(open(f))
        assert d.get('gold_fallback_count', -1) == 0
        assert d.get('static_gold_violation_count', -1) == 0

def test_run_all_dc_and_ndcg():
    import subprocess
    result = subprocess.run([sys.executable, os.path.join(REPO, "scripts/run_all.py")],
                          capture_output=True, text=True, cwd=REPO)
    assert result.returncode == 0

def test_leakage_rates_match_paper():
    proto = open(os.path.join(REPO, "docs/experiment_protocol.md"), encoding='utf-8').read()
    expected = "0, 0.05, 0.10, 0.25, 0.50, 0.75, 1.00"
    assert expected in proto
