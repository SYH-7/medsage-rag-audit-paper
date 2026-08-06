"""Test that condition decomposition functions load correctly."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def test_core_imports():
    from private_evaluation.core import select_b0, select_version_b, compute_demand_cov, compute_ndcg, map_states_to_demands
    assert callable(select_b0)
    assert callable(select_version_b)
    assert callable(compute_demand_cov)
    assert callable(compute_ndcg)
    assert callable(map_states_to_demands)

def test_condition_decomposition_imports():
    from private_evaluation.condition_decomposition import load_candidates, exact_max_coverage
    assert callable(load_candidates)
    assert callable(exact_max_coverage)

def test_metrics_imports():
    from metrics.retrieval import retrieval_metrics
    from metrics.state import state_coverage_metrics
    from metrics.significance import paired_bootstrap_ci, wilcoxon_paired, mcnemar_exact, holm_adjust
    assert callable(retrieval_metrics)
    assert callable(state_coverage_metrics)
    assert callable(paired_bootstrap_ci)
    assert callable(wilcoxon_paired)
    assert callable(mcnemar_exact)
    assert callable(holm_adjust)

def test_exact_max_coverage_definition():
    """Verify exact_max_coverage returns a tuple (ids, score)."""
    from private_evaluation.condition_decomposition import exact_max_coverage
    cands = [{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "c"}]
    result = exact_max_coverage({"D01"}, cands, {}, "q0", k=2)
    assert isinstance(result, tuple)
    assert len(result) == 2
