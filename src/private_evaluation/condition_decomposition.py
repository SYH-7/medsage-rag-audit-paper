"""B0-D3 condition decomposition - exact paper protocol."""
import os, sys, json, math, itertools
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src/private_evaluation"))

# Use relative data paths
DATA_ROOT = Path(os.environ.get("MEDSAGE_DATA_ROOT", str(REPO_ROOT / "data")))

from core import (
    select_version_b, select_b0, compute_demand_cov, compute_ndcg,
    map_states_to_demands, ONT, TOP_K
)

def load_candidates(pool_path):
    pool = {}
    with open(pool_path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            q = str(r["qid"])
            if q not in pool: pool[q] = []
            pool[q].append(r)
    return pool

def exact_max_coverage(query_demands, cands, gold_ev, qid, k=5):
    if len(cands) <= k:
        # Compute real coverage, not just 1.0
        cov = set()
        for did in [c["doc_id"] for c in cands]:
            for st in gold_ev.get(qid, {}).get(did, set()):
                if st in ONT and ONT[st] in query_demands:
                    cov.add(ONT[st])
        score = len(cov) / max(len(query_demands), 1) if query_demands else 0.0
        return [c["doc_id"] for c in cands], score
    best_score, best_ids = -1, []
    doc_ids = [c["doc_id"] for c in cands]
    for combo in itertools.combinations(range(len(cands)), k):
        sel_ids = [doc_ids[i] for i in combo]
        cov = set()
        for did in sel_ids:
            for st in gold_ev.get(qid, {}).get(did, set()):
                if st in ONT and ONT[st] in query_demands:
                    cov.add(ONT[st])
        score = len(cov) / max(len(query_demands), 1) if query_demands else 0
        if score > best_score:
            best_score = score
            best_ids = sel_ids
    return best_ids, best_score

__all__ = ["load_candidates", "exact_max_coverage", "select_version_b", "select_b0",
           "compute_demand_cov", "compute_ndcg", "map_states_to_demands", "ONT", "TOP_K"]
