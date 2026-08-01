#!/usr/bin/env python
"""v5f_common.py — MMR/Top-K 修复版共享工具（revision_v5_mmr_topk_fixed）。

相对 v5_common 的四类修复：
1. paired_bootstrap_ci：改为 qid 级配对重采样（diff= a-b，同一组索引 idx，mean(diff[idx])）；
2. gold_ev_demands：15 类 state -> 6 类 demand（ONT[s] 映射）；
3. mmr_select_tfidf：显式确定性 tie-break（MMR score desc, reranker desc, doc_id asc），
   不依赖候选文件原始顺序；
4. 全精度：逐 qid/汇总/统计全部使用 float64，禁止中途 round；CSV 输出 ≥8 位小数
   （极小值用 repr 保留）；论文表最后 round4。

其余口径与 v5 一致（候选池/gold/官方指标/MMR-TFIDF 命名）。
"""
import sys, json, io, math, logging, hashlib, csv
from pathlib import Path
from collections import defaultdict
import numpy as np

ROOT = Path(__file__).resolve().parents[3]  # scripts/ -> revision_v5_mmr_topk_fixed -> outputs -> 项目根
sys.path.insert(0, str(ROOT / "experiments/common"))
from frozen_medsage_evaluation import (
    load_jsonl, load_json, load_ontology, map_states_to_demands,
    select_b0, _dcg, compute_demand_cov, compute_ndcg,
    build_candidate_list,
)

ONT = load_ontology()
L1 = sorted(set(ONT.values()))          # 6 demand labels
L15 = sorted(ONT.keys())                 # 15 state labels
ALPHA, BETA, GAMMA, DELTA = 0.1, 0.2, 0.2, 0.05

SEED = 42
N_BOOT = 10000
K_LIST = [3, 5, 7]
LAMBDAS = [0.5, 0.6, 0.7, 0.8, 0.9]

LF = ROOT / "data/leakage_free"
OLD_V5 = ROOT / "outputs/revision_v5_mmr_topk"       # 旧版目录（只读缓存，不覆盖）
V5 = ROOT / "outputs/revision_v5_mmr_topk_fixed"     # 本版输出目录
TAB = V5 / "tables"
FIG = V5 / "figures"
LOGS = V5 / "logs"
TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)

def get_logger(name):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
    return logging.getLogger(name)

# ============ 输出助手（全精度：≥8 位小数，极小值 repr） ============

def fmt(v):
    """float -> 8 位小数；极小非零值用 repr 保留；其余原样。"""
    if isinstance(v, float):
        if v == 0.0:
            return "0.00000000"
        if abs(v) < 1e-9:
            return repr(v)
        return f"{v:.8f}"
    return str(v)

def write_csv(path, rows, cols=None):
    if not rows:
        with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
            f.write("")
        return
    if cols is None:
        cols = list(rows[0].keys())
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(r.get(k, "")) for k in cols})

def write_md(path, lines):
    with io.open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

# ============ 数据加载 ============

def load_pools(splits):
    pool = {}
    for sp in splits:
        d = defaultdict(list)
        for r in load_jsonl(LF / "candidate_pools" / f"{sp}_candidates.jsonl"):
            d[str(r["qid"])].append(r)
        pool[sp] = dict(d)
    return pool

def load_annotations():
    ann = {}
    for r in load_jsonl(LF / "private_annotations" / "formal300_annotations.jsonl"):
        ann[str(r["qid"])] = r
    return ann

def load_phase6b_gold(split):
    qg = {}
    for r in load_jsonl(LF / "phase6b_gold" / f"{split}_query_gold.jsonl"):
        qg[str(r["qid"])] = r
    eg = load_jsonl(LF / "phase6b_gold" / f"{split}_evidence_gold.jsonl")
    return qg, eg

def build_gold(split, ann=None, qg=None, eg=None):
    if split in ("formal_train", "formal_dev"):
        gqd, gev, grel = {}, defaultdict(lambda: defaultdict(set)), defaultdict(dict)
        for qs, g in ann.items():
            gd = map_states_to_demands(set(g.get("query_states", [])))
            if gd:
                gqd[qs] = gd
            gold_ids = set(g.get("gold_doc_ids", []))
            for s, ds in (g.get("state_doc_map") or {}).items():
                for d in ds:
                    gev[qs][d].add(s)
                    grel[qs][d] = 2 if d in gold_ids else (1 if s else 0)
        return gqd, {k: dict(v) for k, v in gev.items()}, dict(grel)
    else:
        gqd = {qs: set(r.get("query_demands_6", [])) for qs, r in qg.items()}
        gev, grel = defaultdict(lambda: defaultdict(set)), defaultdict(dict)
        for r in eg:
            q, d = str(r["qid"]), str(r.get("candidate_doc_id") or r.get("doc_id"))
            gev[q][d].update(r.get("supported_states_15", []))
            grel[q][d] = r.get("relevance", 0)
        return gqd, {k: dict(v) for k, v in gev.items()}, dict(grel)

def gold_ev_demands(split, gev):
    """qid -> doc_id -> set(6-class demand labels)（修复：ONT[s] 映射）。"""
    out = defaultdict(dict)
    for q, dd in gev.items():
        for d, states in dd.items():
            out[q][d] = {ONT[s] for s in states if s in ONT}
    return dict(out)

# ============ 选择器（参数化 K，doc_id 绑定） ============

def select_b0_k(cands, k):
    return [c["doc_id"] for c in sorted(cands, key=lambda c: (-c.get("reranker_score", c.get("hybrid_score", 0)), c["doc_id"]))[:k]]

def select_version_b_k(query_demands, cands, evidence_fn, k):
    score_map, norm_map = build_candidate_list(cands)
    available = [c["doc_id"] for c in cands]
    selected = []
    covered_demands = set()
    for _ in range(k):
        best_did, best_score = None, -1e9
        for did in available:
            pred_demands = evidence_fn(did)
            new_demands = pred_demands - covered_demands
            non_k_gain = len(new_demands & query_demands) / max(len(query_demands), 1)
            k_gain = 0.0
            if selected:
                red = len(pred_demands & covered_demands) / max(len(pred_demands | covered_demands), 1)
            else:
                red = 0.0
            score = ALPHA * norm_map[did] + BETA * non_k_gain + GAMMA * k_gain - DELTA * red
            if score > best_score:
                best_score, best_did = score, did
        if best_did is None:
            break
        selected.append(best_did)
        covered_demands.update(evidence_fn(best_did) & query_demands)
        available.remove(best_did)
    return selected

# ============ TF-IDF 相似度（MMR-TFIDF 代理，float64 全精度） ============

_tfidf_cache = {}

def _pool_text(cands):
    return {c["doc_id"]: (c.get("content") or c.get("candidate_text") or c.get("text") or "") for c in cands}

def build_sim_matrix(cands):
    """Return (doc_order, n x n cosine matrix) — float64 全精度。"""
    texts = _pool_text(cands)
    key = tuple(sorted(c["doc_id"] for c in cands))
    if key in _tfidf_cache:
        return _tfidf_cache[key]
    from sklearn.feature_extraction.text import TfidfVectorizer
    ids = [c["doc_id"] for c in cands]
    v = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2,
                        max_features=50000, dtype=np.float64, sublinear_tf=True)
    X = v.fit_transform([texts.get(i, "") for i in ids]).toarray()
    n = X.shape[0]
    M = np.zeros((n, n), dtype=np.float64)
    norms = np.linalg.norm(X, axis=1)
    for i in range(n):
        if norms[i] == 0:
            continue
        for j in range(i + 1, n):
            if norms[j] == 0:
                continue
            c = float(np.dot(X[i], X[j]) / (norms[i] * norms[j]))
            M[i, j] = M[j, i] = c
    np.fill_diagonal(M, 1.0)
    _tfidf_cache[key] = (ids, M)
    return ids, M

def mmr_select_tfidf(cands, lam, k, pool_sim=None):
    """MMR-TFIDF Top-K（显式确定性 tie-break）。

    Rel = qid 内 min-max 归一化 reranker_score（全相同则 0.5）
    Sim = char 2-4gram TF-IDF 余弦（float64）
    首文档 = 候选池最高 reranker_score（tie doc_id asc）== B0 top-1
    候选比较严格按：MMR score desc -> reranker_score desc -> doc_id asc
    """
    scores = np.array([float(c.get("reranker_score", c.get("hybrid_score", 0.0)) or 0.0) for c in cands], dtype=np.float64)
    mn, mx = float(scores.min()), float(scores.max())
    rel = np.full_like(scores, 0.5) if mx - mn < 1e-12 else (scores - mn) / max(mx - mn, 1e-12)
    if pool_sim is not None:
        ids, M = pool_sim
        assert ids == [c["doc_id"] for c in cands], "sim matrix doc order mismatch"
    else:
        ids, M = build_sim_matrix(cands)
    n = len(cands)
    # 首文档：(-reranker, doc_id) 最小者（与 B0 top-1 一致）
    idx0 = min(range(n), key=lambda i: (-scores[i], str(cands[i]["doc_id"])))
    selected_idx = [idx0]
    for _ in range(1, k):
        best_i, best_key = None, None
        for i in range(n):
            if i in selected_idx:
                continue
            maxsim = max(float(M[i, j]) for j in selected_idx)
            s = lam * rel[i] - (1 - lam) * maxsim   # float64 全精度
            key = (-s, -scores[i], str(cands[i]["doc_id"]))
            if best_key is None or key < best_key:
                best_key, best_i = key, i
        if best_i is None:
            break
        selected_idx.append(best_i)
    return [cands[i]["doc_id"] for i in selected_idx]

# ============ 官方指标（全精度） ============

def dc_at_k(sel, qid, gold_ev, gqd, k):
    qd = gqd.get(qid, set()) if isinstance(gqd, dict) else gqd
    return compute_demand_cov(sel[:k], qid, gold_ev, qd)

def ndcg_at_k(sel, qid, gold_rel, k):
    rs = [gold_rel.get(qid, {}).get(d, 0) for d in sel[:k]]
    all_r = sorted(gold_rel.get(qid, {}).values(), reverse=True)
    d = _dcg(rs, k)
    i = _dcg(all_r, k)
    return d / i if i > 0 else 0.0

def ndcg10(sel, qid, gold_rel):
    return compute_ndcg(sel, qid, gold_rel)

def unique_demand_count(sel, ev_dem, qid):
    s = set()
    for d in sel:
        s |= ev_dem.get(qid, {}).get(d, set())
    return len(s)

def mean_gold_relevance(sel, qid, gold_rel):
    vals = [gold_rel.get(qid, {}).get(d, 0) for d in sel]
    return float(np.mean(vals)) if vals else 0.0

def mean_reranker(sel, cands):
    m = {c["doc_id"]: float(c.get("reranker_score", c.get("hybrid_score", 0.0)) or 0.0) for c in cands}
    vals = [m.get(d, 0.0) for d in sel]
    return float(np.mean(vals)) if vals else 0.0

def pairwise_similarity(sel, pool_sim):
    ids, M = pool_sim
    pos = {d: i for i, d in enumerate(ids)}
    sims = [float(M[pos[sel[i]], pos[sel[j]]]) for i in range(len(sel)) for j in range(i + 1, len(sel))]
    return float(np.mean(sims)) if sims else 0.0

def redundancy_demands(sel, ev_dem, qid):
    """demand-set Jaccard（6 类 demand 集合）。"""
    sets = [ev_dem.get(qid, {}).get(d, set()) for d in sel]
    jac = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            a, b = sets[i], sets[j]
            if not a and not b:
                jac.append(0.0)
            else:
                jac.append(len(a & b) / max(len(a | b), 1))
    return float(np.mean(jac)) if jac else 0.0

def jaccard_vs(sel, ref):
    if not sel and not ref:
        return 1.0
    return len(set(sel) & set(ref)) / max(len(set(sel) | set(ref)), 1)

def replacement_count(sel, ref):
    return len(set(sel) - set(ref))

# ============ 预测（复用旧版缓存，不重训 Q1/E2） ============

def train_oof(ann, tq, canon, pool):
    """与 R7 一致的 Q1/E2 训练（仅在无缓存时使用，正常流程不触发）。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    q1_texts = [ann[qs].get("question", "") for qs in tq]
    y_q1 = np.array([[1 if d in map_states_to_demands(set(ann[qs].get("query_states", []))) else 0 for d in L1] for qs in tq], dtype=np.int8)
    qid_to_fold = {qs: i % 5 for i, qs in enumerate(tq)}
    qid_to_oof_pred = {}
    for fold in range(5):
        tid = [i for i, qs in enumerate(tq) if qid_to_fold[qs] != fold]
        vid = [i for i, qs in enumerate(tq) if qid_to_fold[qs] == fold]
        if not vid:
            continue
        vq = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2, max_features=50000, dtype=np.float32, sublinear_tf=True)
        clf = OneVsRestClassifier(LogisticRegression(class_weight="balanced", solver="liblinear", max_iter=500, random_state=42))
        clf.fit(vq.fit_transform([q1_texts[i] for i in tid]), y_q1[tid])
        probs = np.asarray(clf.predict_proba(vq.transform([q1_texts[i] for i in vid])), dtype=np.float32)
        for j, idx in enumerate(vid):
            qs = tq[idx]
            hard = set(L1[j_] for j_ in range(len(L1)) if probs[j, j_] >= 0.5) or {L1[np.argmax(probs[j])]}
            qid_to_oof_pred[qs] = hard
    e2_key = [(str(p["qid"]), p["candidate_doc_id"]) for p in canon]
    e2_texts = [f"[QUERY] {ann.get(str(p['qid']), {}).get('question', '')}\n[DOCUMENT] {p.get('candidate_text', '')}" for p in canon]
    e2_labels = [[1 if d in set(p.get("supported_demands_6", [])) else 0 for d in L1] for p in canon]
    y_e2 = np.array(e2_labels, dtype=np.int8)
    pair_to_oof_pred = {}
    for fold in range(5):
        tid = [i for i, (qs, _) in enumerate(e2_key) if qid_to_fold.get(qs, -1) != fold]
        vid = [i for i, (qs, _) in enumerate(e2_key) if qid_to_fold.get(qs, -1) == fold]
        if not vid:
            continue
        ve = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2, max_features=50000, dtype=np.float32, sublinear_tf=True)
        clf = OneVsRestClassifier(LogisticRegression(class_weight="balanced", solver="liblinear", max_iter=500, random_state=42))
        clf.fit(ve.fit_transform([e2_texts[i] for i in tid]), y_e2[tid])
        probs = np.asarray(clf.predict_proba(ve.transform([e2_texts[i] for i in vid])), dtype=np.float32)
        for j, idx in enumerate(vid):
            qs, did = e2_key[idx]
            hard = set(L1[j_] for j_ in range(len(L1)) if probs[j, j_] >= 0.5) or {L1[np.argmax(probs[j])]}
            pair_to_oof_pred[(qs, did)] = hard
    return qid_to_oof_pred, pair_to_oof_pred


def _pred_to_arr(pred_dict, order):
    m = {d: i for i, d in enumerate(L1)}
    arr = np.zeros((len(order), len(L1)), dtype=np.int8)
    for i, k in enumerate(order):
        for d in pred_dict.get(k, set()):
            if d in m:
                arr[i, m[d]] = 1
    return arr

def _arr_to_pred(arr, order):
    return {k: set(L1[j] for j in range(len(L1)) if arr[i, j]) for i, k in enumerate(order)}

def ensure_predictions(force=False):
    """优先复用 revision_v5_mmr_topk/cache 的 Q1/E2 预测（不重新训练）；
    缺失时才训练并落盘到本目录 cache。"""
    old_cache = OLD_V5 / "cache" / "predictions.npz"
    old_meta = OLD_V5 / "cache" / "predictions_meta.json"
    if old_cache.exists() and old_meta.exists():
        z = np.load(old_cache, allow_pickle=True)
        meta = json.loads(old_meta.read_text(encoding="utf-8"))
        preds = {}
        for sp, info in meta.items():
            pq = _arr_to_pred(z[f"{sp}_qid_pred"], info["qids"])
            pp = _arr_to_pred(z[f"{sp}_pair_pred"], [tuple(p) for p in info["pairs"]])
            preds[sp] = {"pq": pq, "pp": pp}
        return preds

    cache_file = V5 / "cache" / "predictions.npz"
    meta_file = V5 / "cache" / "predictions_meta.json"
    if cache_file.exists() and meta_file.exists() and not force:
        z = np.load(cache_file, allow_pickle=True)
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        preds = {}
        for sp, info in meta.items():
            pq = _arr_to_pred(z[f"{sp}_qid_pred"], info["qids"])
            pp = _arr_to_pred(z[f"{sp}_pair_pred"], [tuple(p) for p in info["pairs"]])
            preds[sp] = {"pq": pq, "pp": pp}
        return preds

    # fallback：训练并落盘（正常流程不会触发，因为旧版缓存存在）
    ann = load_annotations()
    tq = [str(q) for q in load_json(LF / "splits/formal_train_qids.json")]
    canon = load_jsonl(LF / "state_prediction/formal_train_pairs_canonical.jsonl")
    pools = load_pools(["formal_train", "internal_blind", "cmedqa2_external"])
    qg_int, _ = load_phase6b_gold("internal_blind")
    qg_ext, _ = load_phase6b_gold("cmedqa2_external")
    q1_oof, e2_oof = train_oof(ann, tq, canon, pools["formal_train"])
    preds = {}
    meta = {}
    ft_pairs = [(qs, c["doc_id"]) for qs in pools["formal_train"] for c in pools["formal_train"][qs]]
    preds["formal_train"] = {"pq": q1_oof, "pp": {(q, d): e2_oof.get((q, d), set()) for (q, d) in ft_pairs}}
    meta["formal_train"] = {"qids": sorted(q1_oof), "pairs": [list(p) for p in ft_pairs]}
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    q1_texts = [ann[qs].get("question", "") for qs in tq]
    y_q1 = np.array([[1 if d in map_states_to_demands(set(ann[qs].get("query_states", []))) else 0 for d in L1] for qs in tq], dtype=np.int8)
    vq_full = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2, max_features=50000, dtype=np.float32, sublinear_tf=True)
    cq_full = OneVsRestClassifier(LogisticRegression(class_weight="balanced", solver="liblinear", max_iter=500, random_state=42))
    cq_full.fit(vq_full.fit_transform(q1_texts), y_q1)
    e2_texts = [f"[QUERY] {ann.get(str(p['qid']), {}).get('question', '')}\n[DOCUMENT] {p.get('candidate_text', '')}" for p in canon]
    e2_labels = [[1 if d in set(p.get("supported_demands_6", [])) else 0 for d in L1] for p in canon]
    y_e2 = np.array(e2_labels, dtype=np.int8)
    ve_full = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2, max_features=50000, dtype=np.float32, sublinear_tf=True)
    ce_full = OneVsRestClassifier(LogisticRegression(class_weight="balanced", solver="liblinear", max_iter=500, random_state=42))
    ce_full.fit(ve_full.fit_transform(e2_texts), y_e2)
    for sp, qg in [("internal_blind", qg_int), ("cmedqa2_external", qg_ext)]:
        qs_l = sorted(set(pools[sp]) & set(qg))
        texts = [qg[q].get("question", "") for q in qs_l]
        p = np.asarray(cq_full.predict_proba(vq_full.transform(texts)), dtype=np.float32)
        pq = {}
        for i, qs in enumerate(qs_l):
            pq[qs] = set(L1[j] for j in range(len(L1)) if p[i, j] >= 0.5) or {L1[np.argmax(p[i])]}
        ev_texts, order = [], []
        for q in qs_l:
            for c in pools[sp][q]:
                ev_texts.append(f"[QUERY] {qg[q].get('question', '')}\n[DOCUMENT] {c.get('content', '')}")
                order.append((q, c["doc_id"]))
        ep = np.asarray(ce_full.predict_proba(ve_full.transform(ev_texts)), dtype=np.float32)
        pp = {}
        for i, (q, d) in enumerate(order):
            pp[(q, d)] = set(L1[j] for j in range(len(L1)) if ep[i, j] >= 0.5)
        pairs = [list(x) for x in sorted(pp)]
        preds[sp] = {"pq": pq, "pp": pp}
        meta[sp] = {"qids": sorted(pq), "pairs": pairs}
    (V5 / "cache").mkdir(parents=True, exist_ok=True)
    with io.open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    arrays = {}
    for sp, info in meta.items():
        arrays[f"{sp}_qid_pred"] = _pred_to_arr(preds[sp]["pq"], info["qids"])
        arrays[f"{sp}_pair_pred"] = _pred_to_arr(preds[sp]["pp"], [tuple(p) for p in info["pairs"]])
    np.savez(cache_file, **arrays)
    return preds

# ============ 统计（修复：qid 级配对重采样；全精度） ============

def paired_bootstrap_ci(a_vals, b_vals, n_iter=N_BOOT, seed=SEED):
    """qid 级配对 Bootstrap：diff = a - b，对同一组 qid 索引重采样 mean(diff[idx])。

    修复点：不再为 A/B 各自独立采样索引。
    """
    a = np.asarray(a_vals, dtype=np.float64)
    b = np.asarray(b_vals, dtype=np.float64)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    diff = a - b
    mean_diff = float(np.mean(diff))
    rng = np.random.RandomState(seed)
    boots = np.empty(n_iter, dtype=np.float64)
    for t in range(n_iter):
        idx = rng.randint(0, n, n)
        boots[t] = np.mean(diff[idx])
    p_low = (np.sum(boots <= 0) + 1) / (n_iter + 1)
    p_high = (np.sum(boots >= 0) + 1) / (n_iter + 1)
    p = min(1.0, 2 * min(p_low, p_high))
    return {
        "mean_difference": mean_diff,
        "ci_low": float(np.percentile(boots, 2.5)),
        "ci_high": float(np.percentile(boots, 97.5)),
        "p_raw": float(p),
    }

def holm_adjust(ps):
    n = len(ps)
    order = sorted(range(n), key=lambda i: ps[i])
    adj = [0.0] * n
    prev = 0.0
    for rank, i in enumerate(order, start=1):
        v = min(1.0, max(ps[i] * (n - rank + 1), prev))
        adj[i] = v
        prev = v
    return adj

def pos_neg_ties(a_vals, b_vals):
    a = np.asarray(a_vals, dtype=np.float64)
    b = np.asarray(b_vals, dtype=np.float64)
    d = a - b
    return int(np.sum(d > 1e-12)), int(np.sum(d < -1e-12)), int(np.sum(np.abs(d) <= 1e-12))
