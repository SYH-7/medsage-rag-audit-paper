#!/usr/bin/env python
"""07_run_topk_sensitivity.py (fixed) — Top-K 逐 qid + 汇总（全精度，K=3/5/7）。"""
import argparse, io, json, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_topk")
SPLITS = ["formal_train", "internal_blind", "cmedqa2_external"]
METHODS = ["B0", "D0", "D1", "D2", "D3_TFIDF", "MMR"]
RISK_STATES = {"risk_emergency", "risk_medication", "risk_special_population", "risk_mental_health"}


def main():
    ap = argparse.ArgumentParser(description="Top-K 敏感性（全精度）")
    ap.add_argument("--out", default=str(C.V5))
    ap.add_argument("--ks", default="3,5,7")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    KS = [int(x) for x in args.ks.split(",")]
    lam = json.loads((out / "frozen_lambda.json").read_text(encoding="utf-8"))["lambda"]

    ann = C.load_annotations()
    pools = C.load_pools(SPLITS)
    qg_int, eg_int = C.load_phase6b_gold("internal_blind")
    qg_ext, eg_ext = C.load_phase6b_gold("cmedqa2_external")
    GOLD = {"formal_train": C.build_gold("formal_train", ann=ann),
            "internal_blind": C.build_gold("internal_blind", qg=qg_int, eg=eg_int),
            "cmedqa2_external": C.build_gold("cmedqa2_external", qg=qg_ext, eg=eg_ext)}
    preds = C.ensure_predictions()

    def risk_demands(sp, qs):
        if sp == "formal_train":
            qs_15 = set(ann[qs].get("query_states", []))
        else:
            qg = qg_int if sp == "internal_blind" else qg_ext
            qs_15 = set(qg.get(qs, {}).get("query_states_15", []))
        return C.map_states_to_demands(qs_15 & RISK_STATES)

    rows = []
    for sp in SPLITS:
        gqd, gev, grel = GOLD[sp]
        pq, pp = preds[sp]["pq"], preds[sp]["pp"]
        ev_dem = C.gold_ev_demands(sp, gev)
        for qs in sorted(set(pools[sp]) & set(gqd)):
            cands = pools[sp][qs]
            ps = C.build_sim_matrix(cands)
            gd = gqd[qs]; pd = pq.get(qs, set())
            def eg(d, qi=qs): return C.map_states_to_demands(gev[qi].get(d, set()))
            def ep(d, qi=qs): return pp.get((qi, d), set())
            risk = risk_demands(sp, qs)
            for k in KS:
                sels = {"B0": C.select_b0_k(cands, k),
                        "D0": C.select_version_b_k(gd, cands, eg, k),
                        "D1": C.select_version_b_k(pd if pd else gd, cands, eg, k),
                        "D2": C.select_version_b_k(gd, cands, ep, k),
                        "D3_TFIDF": C.select_version_b_k(pd, cands, ep, k),
                        "MMR": C.mmr_select_tfidf(cands, lam, k, ps)}
                for m, sel in sels.items():
                    cov_dem = set()
                    for d in sel:
                        for st in gev.get(qs, {}).get(d, set()):
                            if st in C.ONT and C.ONT[st] in gd:
                                cov_dem.add(C.ONT[st])
                    rows.append({"split": sp, "qid": qs, "method": m, "k": k, "lambda": lam if m == "MMR" else "",
                                 "selected_doc_ids": "|".join(sel),
                                 "demand_cov_at_k": C.dc_at_k(sel, qs, gev, gqd, k),
                                 "ndcg_at_k": C.ndcg_at_k(sel, qs, grel, k),
                                 "official_ndcg_10": C.ndcg10(sel, qs, grel),
                                 "unique_demand_count": C.unique_demand_count(sel, ev_dem, qs),
                                 "mean_gold_relevance": C.mean_gold_relevance(sel, qs, grel),
                                 "mean_reranker_score": C.mean_reranker(sel, cands),
                                 "mean_pairwise_similarity": C.pairwise_similarity(sel, ps),
                                 "redundancy": C.redundancy_demands(sel, ev_dem, qs),
                                 "full_query_coverage": int(bool(gd and cov_dem >= gd)),
                                 "risk_demand_coverage": int(bool(risk and (cov_dem & risk))),
                                 "has_risk_demand": int(bool(risk))})
    C.write_csv(out / "tables/topk_sensitivity_per_qid.csv", rows)
    log.info("per-qid rows: %d", len(rows))

    sum_rows = []
    for sp in SPLITS:
        for m in METHODS:
            for k in KS:
                sub = [r for r in rows if r["split"] == sp and r["method"] == m and r["k"] == k]
                if not sub:
                    continue
                n = len(sub)
                risk_q = [r for r in sub if r["has_risk_demand"]]
                sum_rows.append({"split": sp, "method": m, "k": k, "n_qid": n,
                                 "demand_cov_at_k": float(sum(r["demand_cov_at_k"] for r in sub) / n),
                                 "ndcg_at_k": float(sum(r["ndcg_at_k"] for r in sub) / n),
                                 "official_ndcg_10": float(sum(r["official_ndcg_10"] for r in sub) / n),
                                 "unique_demand_count": float(sum(r["unique_demand_count"] for r in sub) / n),
                                 "mean_gold_relevance": float(sum(r["mean_gold_relevance"] for r in sub) / n),
                                 "mean_reranker_score": float(sum(r["mean_reranker_score"] for r in sub) / n),
                                 "mean_pairwise_similarity": float(sum(r["mean_pairwise_similarity"] for r in sub) / n),
                                 "redundancy": float(sum(r["redundancy"] for r in sub) / n),
                                 "full_query_coverage_rate": float(sum(r["full_query_coverage"] for r in sub) / n),
                                 "risk_demand_coverage_rate": float(sum(r["risk_demand_coverage"] for r in risk_q) / len(risk_q)) if risk_q else "",
                                 "risk_qid_count": len(risk_q)})
    C.write_csv(out / "tables/topk_sensitivity_summary.csv", sum_rows)
    log.info("summary rows: %d", len(sum_rows))
    print("DONE topk", len(rows))


if __name__ == "__main__":
    main()
