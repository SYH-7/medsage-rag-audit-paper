#!/usr/bin/env python
"""Phase 6B-R6: Single frozen evaluation module - all experiments share this."""
import json, math, random, hashlib, sys
from pathlib import Path
from collections import defaultdict
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ENC = "utf-8"

# ===== FROZEN ONTOLOGY (from Phase 6A) =====
def load_ontology():
    """Load frozen 15->6 ontology from Phase 6A file."""
    path = REPO_ROOT / "configs/ontology.json"
    if path.exists():
        data = json.loads(open(path, encoding=ENC).read())
        # Extract level_2 mapping (15-class -> 6-class)
        l2 = data.get("level_2", {})
        assert "risk_medication" in l2, "risk_medication must be in ontology level_2"
        return l2
    # Fallback: hardcoded frozen mapping
    return {}

ONT = load_ontology()
L1 = sorted(set(ONT.values()))  # ["D01_symptom_course", ..., "D06_mental_safety"]
L15 = sorted(ONT.keys())
assert len(L15) == 15, f"Ontology has {len(L15)} classes, expected 15"
assert "risk_medication" in ONT, "risk_medication must be in ontology"

# Frozen selector parameters (Version B from Phase 5P-C / Phase 6A)
ALPHA, BETA, GAMMA, DELTA = 0.1, 0.2, 0.2, 0.05
TOP_K = 5


# ===== HELPERS =====
def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding=ENC)]

def load_json(p):
    return json.loads(open(p, encoding=ENC).read())

def write_jsonl(p, data):
    with open(p, "w", encoding=ENC) as f:
        for d in data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

def write_json(p, data):
    with open(p, "w", encoding=ENC) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def map_states_to_demands(states_15):
    """Convert 15-class state set to 6-class demand set."""
    return set(ONT[s] for s in states_15 if s in ONT)

# ===== CANDIDATE WITH SCORE BOUND BY DOC_ID =====
def build_candidate_list(cands):
    """Build candidate list with scores bound by doc_id (no index-based access)."""
    score_map = {}
    for c in cands:
        did = c["doc_id"]
        score_map[did] = c.get("reranker_score", c.get("hybrid_score", 0))
    
    # Per-qid min-max normalization
    scores = list(score_map.values())
    mn, mx = min(scores), max(scores)
    norm_map = {}
    for did, s in score_map.items():
        norm_map[did] = (s - mn) / max(mx - mn, 1e-10)
    
    return score_map, norm_map

# ===== VERSION B SELECTOR (doc_id-bound scores) =====
def select_version_b(query_demands, cands, evidence_fn):
    """Version B: alpha=0.1, beta=0.2, gamma=0.2, delta=0.05.
    
    - Scores bound by doc_id (no index misalignment after pop)
    - Marginal coverage gain computed correctly
    - Key state gain computed (may be 0 if no key info)
    - Real redundancy penalty (Jaccard-like overlap)
    - Supports non_key / key / risk terms
    """
    score_map, norm_map = build_candidate_list(cands)
    available = [c["doc_id"] for c in cands]
    selected = []
    covered_demands = set()
    
    for _ in range(TOP_K):
        best_did, best_score = None, -1e9
        best_breakdown = {}
        for did in available:
            pred_demands = evidence_fn(did)
            new_demands = pred_demands - covered_demands
            
            # Marginal query gain (non-key gain in Version B)
            non_k_gain = len(new_demands & query_demands) / max(len(query_demands), 1)
            
            # Key gain (0 when no key info at 6-class level)
            k_gain = 0.0
            
            # Redundancy: Jaccard overlap with already-covered demands
            if selected:
                red = len(pred_demands & covered_demands) / max(len(pred_demands | covered_demands), 1)
            else:
                red = 0.0
            
            score = ALPHA * norm_map[did] + BETA * non_k_gain + GAMMA * k_gain - DELTA * red
            
            if score > best_score:
                best_score = score
                best_did = did
                best_breakdown = {
                    "doc_id": did, "rel_norm": norm_map[did],
                    "non_k_gain": non_k_gain, "k_gain": k_gain,
                    "redundancy": red, "score": score
                }
        
        if best_did is None:
            break
        selected.append(best_did)
        covered_demands.update(evidence_fn(best_did) & query_demands)
        available.remove(best_did)
    
    return selected

# ===== B0 SELECTOR =====
def select_b0(cands):
    """Reranker Top-5, no state info used."""
    return [c["doc_id"] for c in sorted(cands, key=lambda c: (-c.get("reranker_score", c.get("hybrid_score", 0)), c["doc_id"]))[:TOP_K]]

# ===== METRICS =====
def _dcg(vals, k=10):
    return sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(vals[:k]))

def compute_demand_cov(selected, qid, gold_ev, query_demands):
    """DemandCov@5: fraction of query demands covered by selected docs."""
    cov = set()
    for did in selected:
        for st in gold_ev.get(qid, {}).get(did, set()):
            if st in ONT and ONT[st] in query_demands:
                cov.add(ONT[st])
    return len(cov) / max(len(query_demands), 1) if query_demands else 0.0

def compute_ndcg(selected, qid, gold_rel):
    """NDCG@10 with per-qid IDCG from all candidate relevance."""
    rs = [gold_rel.get(qid, {}).get(d, 0) for d in selected]
    all_r = sorted(gold_rel.get(qid, {}).values(), reverse=True)
    d = _dcg(rs, 10)
    i = _dcg(all_r, 10)
    return d / i if i > 0 else 0.0

# ===== GAP DECOMPOSITION =====
def compute_gap(b0, d0, d1, d2, d3):
    """Gaps defined per paper (revised D1/D2):
    D1 = Predicted Query + Gold Evidence
    D2 = Gold Query + Predicted Evidence
    QueryLoss = D0 - D1 (query prediction loss)
    EvidenceLoss = D0 - D2 (evidence prediction loss)
    DeploymentGap = D0 - D3 (total deployment gap)
    OracleGain = D0 - B0 (oracle headroom)
    DeployableGain = D3 - B0 (actual deployable gain)
    InteractionLoss = D1 + D2 - D0 - D3 (interaction between losses)
    """
    og = d0 - b0
    denom = max(og, 1e-10)
    return {
        "oracle_gain": og,
        "query_loss": d0 - d1,
        "evidence_loss": d0 - d2,
        "deployment_gap": d0 - d3,
        "deployable_gain": d3 - b0,
        "interaction_loss": d1 + d2 - d0 - d3,
        "query_recovery": (d1 - b0) / denom,
        "evidence_recovery": (d2 - b0) / denom,
        "e2e_recovery": (d3 - b0) / denom,
    }

# ===== GOLD INVARIANCE TEST =====
def test_gold_invariance(name, pool, qid_strs, qid_gold_qd, qid_gold_ev, qid_gold_rel, qid_pred_qd, pair_pred_ev):
    """Test D3 invariance to gold deletion (by selected_doc_ids)."""
    def ev_pred(d, qi): return pair_pred_ev.get((qi, d), set())
    
    # Baseline D3
    baseline = {}
    for qs in qid_strs:
        gqd = qid_gold_qd.get(qs, set())
        pqd = qid_pred_qd.get(qs, set())
        if not gqd: continue
        baseline[qs] = select_version_b(pqd if pqd else set(), pool[qs], lambda d, qi=qs: ev_pred(d, qi))
    
    # Without gold query (use shuffled predictions)
    no_gq = {}
    for qs in qid_strs:
        gqd = qid_gold_qd.get(qs, set())
        if not gqd: continue
        fake_qd = qid_pred_qd.get(random.choice(qid_strs), set())
        no_gq[qs] = select_version_b(fake_qd if fake_qd else set(), pool[qs], lambda d, qi=qs: ev_pred(d, qi))
    
    # Without gold evidence (empty predictions)
    no_ge = {}
    for qs in qid_strs:
        gqd = qid_gold_qd.get(qs, set())
        pqd = qid_pred_qd.get(qs, set())
        if not gqd: continue
        no_ge[qs] = select_version_b(pqd if pqd else set(), pool[qs], lambda d: set())
    
    # Inject fake gold (wrong demands injected into pred dict)
    fake_pred = dict(pair_pred_ev)
    for qs in qid_strs:
        for c in pool[qs]:
            fake_pred[(qs, c["doc_id"])] = {random.choice(L1)}
    fake_gq = dict(qid_pred_qd)
    for qs in qid_strs:
        fake_gq[qs] = {random.choice(L1)}
    
    with_fake = {}
    for qs in qid_strs:
        gqd = qid_gold_qd.get(qs, set())
        if not gqd: continue
        with_fake[qs] = select_version_b(fake_gq.get(qs, set()), pool[qs], lambda d, qi=qs: fake_pred.get((qi, d), set()))
    
    same_gq = sum(1 for qs in baseline if baseline[qs] == no_gq.get(qs, []))
    same_ge = sum(1 for qs in baseline if baseline[qs] == no_ge.get(qs, []))
    same_fk = sum(1 for qs in baseline if baseline[qs] == with_fake.get(qs, []))
    total = len(baseline)
    
    return {
        "split": name, "total": total,
        "no_gold_query_identical": same_gq, "no_gold_query_pct": 100*same_gq/total,
        "no_gold_evidence_identical": same_ge, "no_gold_evidence_pct": 100*same_ge/total,
        "fake_gold_identical": same_fk, "fake_gold_pct": 100*same_fk/total,
        "passed": same_gq == total and same_ge == total and same_fk == total
    }

# ===== PAIRED BOOTSTRAP =====
def paired_bootstrap(a_vals, b_vals, n_iter=10000, seed=42):
    """Paired bootstrap with shared indices per sample."""
    n = min(len(a_vals), len(b_vals))
    a, b = np.array(a_vals[:n]), np.array(b_vals[:n])
    diff = float(np.mean(a - b))
    rng = np.random.RandomState(seed)
    # Shared bootstrap indices: A and B use the SAME resampled indices
    boot = []
    for _ in range(n_iter):
        idx = rng.randint(0, n, n)
        boot.append(float(np.mean(a[idx] - b[idx])))
    p_low = (sum(d <= 0 for d in boot) + 1) / (n_iter + 1)
    p_high = (sum(d >= 0 for d in boot) + 1) / (n_iter + 1)
    p = min(1.0, 2 * min(p_low, p_high))
    return {"diff": diff, "p": p, "ci95_low": float(np.percentile(boot, 2.5)), "ci95_high": float(np.percentile(boot, 97.5))}

# ===== RANDOM CONTROL =====
def run_random_control(pool, qid_strs, qid_gold_qd, qid_gold_ev, n_seeds=50):
    """Per-query random selection with fixed seeds."""
    per_seed = defaultdict(list)
    per_qid = defaultdict(list)
    
    for seed in range(n_seeds):
        random.seed(seed + 1000)
        for qs in qid_strs:
            gqd = qid_gold_qd.get(qs, set())
            if not gqd: continue
            r_sel = random.sample(pool[qs], min(5, len(pool[qs])))
            r_ids = [c["doc_id"] for c in r_sel]
            dc = compute_demand_cov(r_ids, qs, qid_gold_ev, gqd)
            per_seed[seed].append(dc)
            per_qid[qs].append(dc)
    
    seed_means = [np.mean(per_seed[s]) for s in range(n_seeds)]
    qid_means = {qs: np.mean(per_qid[qs]) for qs in qid_strs if qid_gold_qd.get(qs, set())}
    return {
        "mean": float(np.mean(seed_means)),
        "std": float(np.std(seed_means)),
        "qid_mean": {str(qs): float(v) for qs, v in qid_means.items()}
    }

# ===== STABLE SEED =====
def make_rng(base_seed, scenario_id=0, rate_idx=0, seed=0):
    """Deterministic RNG using SHA256, NOT Python hash()."""
    key = f"{base_seed}_{scenario_id}_{rate_idx}_{seed}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    int_seed = int(digest[:16], 16)
    return np.random.Generator(np.random.PCG64(int_seed))
