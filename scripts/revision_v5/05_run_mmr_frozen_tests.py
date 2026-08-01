#!/usr/bin/env python
"""05_run_mmr_frozen_tests.py (fixed) — 三划分 MMR 冻结测试（全精度，逐 qid 8 位小数）。"""
import argparse, io, json, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_frozen")
SPLITS = ["formal_train", "internal_blind", "cmedqa2_external"]
K = 5


def main():
    ap = argparse.ArgumentParser(description="MMR 冻结测试（全精度）")
    ap.add_argument("--out", default=str(C.V5))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lam = json.loads((out / "frozen_lambda.json").read_text(encoding="utf-8"))["lambda"]

    ann = C.load_annotations()
    pools = C.load_pools(SPLITS)
    qg_int, eg_int = C.load_phase6b_gold("internal_blind")
    qg_ext, eg_ext = C.load_phase6b_gold("cmedqa2_external")
    GOLD = {"formal_train": C.build_gold("formal_train", ann=ann),
            "internal_blind": C.build_gold("internal_blind", qg=qg_int, eg=eg_int),
            "cmedqa2_external": C.build_gold("cmedqa2_external", qg=qg_ext, eg=eg_ext)}
    preds = C.ensure_predictions()
    ev_dem = {sp: C.gold_ev_demands(sp, GOLD[sp][1]) for sp in SPLITS}

    rows = []
    for sp in SPLITS:
        gqd, gev, grel = GOLD[sp]
        pq, pp = preds[sp]["pq"], preds[sp]["pp"]
        for qs in sorted(set(pools[sp]) & set(gqd)):
            cands = pools[sp][qs]
            ps = C.build_sim_matrix(cands)
            gd = gqd[qs]; pd = pq.get(qs, set())
            def ep(d, qi=qs): return pp.get((qi, d), set())
            sels = {"B0": C.select_b0_k(cands, K),
                    "MMR": C.mmr_select_tfidf(cands, lam, K, ps),
                    "D3_TFIDF": C.select_version_b_k(pd, cands, ep, K)}
            b0 = sels["B0"]
            for m, sel in sels.items():
                rr = [float(c.get("reranker_score", c.get("hybrid_score", 0.0)) or 0.0) for c in cands if c["doc_id"] in set(sel)]
                rows.append({"split": sp, "qid": qs, "method": m, "k": K, "lambda": lam if m == "MMR" else "",
                             "selected_doc_ids": "|".join(sel),
                             "selected_scores": ";".join(f"{v:.8f}" for v in rr),
                             "demand_cov": C.dc_at_k(sel, qs, gev, gqd, K),
                             "ndcg_10": C.ndcg10(sel, qs, grel),
                             "unique_demand_count": C.unique_demand_count(sel, ev_dem[sp], qs),
                             "mean_gold_relevance": C.mean_gold_relevance(sel, qs, grel),
                             "mean_reranker_score": C.mean_reranker(sel, cands),
                             "mean_pairwise_similarity": C.pairwise_similarity(sel, ps),
                             "redundancy": C.redundancy_demands(sel, ev_dem[sp], qs),
                             "jaccard_vs_b0": C.jaccard_vs(sel, b0),
                             "replacement_count_vs_b0": C.replacement_count(sel, b0)})
    C.write_csv(out / "tables/mmr_results_per_qid.csv", rows)
    log.info("per-qid rows: %d", len(rows))

    sum_rows = []
    for sp in SPLITS:
        for m in ["B0", "MMR", "D3_TFIDF"]:
            sub = [r for r in rows if r["split"] == sp and r["method"] == m]
            n = len(sub)
            sum_rows.append({"split": sp, "method": m, "n_qid": n,
                             "demand_cov_5": float(sum(r["demand_cov"] for r in sub) / n),
                             "ndcg_10": float(sum(r["ndcg_10"] for r in sub) / n),
                             "unique_demand_count": float(sum(r["unique_demand_count"] for r in sub) / n),
                             "mean_gold_relevance": float(sum(r["mean_gold_relevance"] for r in sub) / n),
                             "mean_reranker_score": float(sum(r["mean_reranker_score"] for r in sub) / n),
                             "mean_pairwise_similarity": float(sum(r["mean_pairwise_similarity"] for r in sub) / n),
                             "redundancy": float(sum(r["redundancy"] for r in sub) / n),
                             "jaccard_vs_b0": float(sum(r["jaccard_vs_b0"] for r in sub) / n),
                             "replacement_count_vs_b0": float(sum(r["replacement_count_vs_b0"] for r in sub) / n)})
    C.write_csv(out / "tables/mmr_summary.csv", sum_rows)

    md = ["# MMR 主结果（K=5，λ=%s，MMR-TFIDF 代理基线，全精度 fixed）" % lam, "",
          "> Sim=char 2-4gram TF-IDF 余弦（float64）；Rel=reranker_score（qid 内 min-max）；显式 tie-break。",
          "", "| split | method | n_qid | DemandCov@5 | NDCG@10 | unique | gold_rel | 内部sim | 冗余度 | Jaccard vs B0 | 替换数 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sum_rows:
        md.append("| %s | %s | %d | %.6f | %.6f | %.4f | %.6f | %.6f | %.6f | %.6f | %.4f |" % (
            r["split"], r["method"], r["n_qid"], r["demand_cov_5"], r["ndcg_10"], r["unique_demand_count"],
            r["mean_gold_relevance"], r["mean_pairwise_similarity"], r["redundancy"],
            r["jaccard_vs_b0"], r["replacement_count_vs_b0"]))
    C.write_md(out / "mmr_main_results.md", md)
    log.info("frozen tests done")
    print("DONE frozen tests", lam)


if __name__ == "__main__":
    main()
