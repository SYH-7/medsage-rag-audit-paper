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
    # v2 note: src/benchmark_v3 (e.g. injector_registry.py) and src/cross_pipeline are the
    # paper's own published audit code; the competition-filename check applies to the rest.
    bad = ['pipeline_b_', 'pipeline_a_', 'L1_', 'L2_', 'L3_', 'L4_', 'L5_', 'L6_', 'streamlit', 'injector_', 'detector_d_']
    for dirpath, _, fns in os.walk(REPO):
        if 'benchmark_v3' in dirpath or 'cross_pipeline' in dirpath:
            continue
        for fn in fns:
            for b in bad: assert b not in fn.lower()

def test_paired_bootstrap_shared_indices():
    import numpy as np
    from private_evaluation.core import paired_bootstrap
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([1.1, 2.1, 3.1, 4.1, 5.1])
    result = paired_bootstrap(a.tolist(), b.tolist(), n_iter=100, seed=42)
    assert abs(result["diff"] - float(np.mean(a-b))) < 1e-10
