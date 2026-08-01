#!/usr/bin/env python
"""04_run_mmr_dev.py (fixed) — formal_dev λ 选择（全精度，候选 {0.5..0.9}）。"""
import argparse, io, json, logging, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_dev")
SPLIT = "formal_dev"


def main():
    ap = argparse.ArgumentParser(description="formal_dev λ 选择（全精度）")
    ap.add_argument("--out", default=str(C.V5))
    ap.add_argument("--lambdas", default="0.5,0.6,0.7,0.8,0.9")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lams = [float(x) for x in args.lambdas.split(",")]

    ann = C.load_annotations()
    pools = C.load_pools([SPLIT])
    gqd, gev, grel = C.build_gold(SPLIT, ann=ann)
    ev_dem = C.gold_ev_demands(SPLIT, gev)
    pool = pools[SPLIT]
    qs_list = sorted(set(pool) & set(gqd))
    for qs in qs_list:
        C.build_sim_matrix(pool[qs])

    rows = []
    for lam in lams:
        dcs, nds, uniqs, rels, sims, reds, jacs, reps = ([] for _ in range(8))
        for qs in qs_list:
            cands = pool[qs]
            ps = C.build_sim_matrix(cands)
            b0 = C.select_b0_k(cands, 5)
            mmr = C.mmr_select_tfidf(cands, lam, 5, ps)
            dcs.append(C.dc_at_k(mmr, qs, gev, gqd, 5))
            nds.append(C.ndcg10(mmr, qs, grel))
            uniqs.append(C.unique_demand_count(mmr, ev_dem, qs))
            rels.append(C.mean_gold_relevance(mmr, qs, grel))
            sims.append(C.pairwise_similarity(mmr, ps))
            reds.append(C.redundancy_demands(mmr, ev_dem, qs))
            jacs.append(C.jaccard_vs(mmr, b0))
            reps.append(C.replacement_count(mmr, b0))
        rows.append({"lambda": lam, "n_qid": len(qs_list),
                     "mean_demand_cov_5": float(sum(dcs) / len(dcs)),
                     "mean_ndcg_10": float(sum(nds) / len(nds)),
                     "mean_unique_demand_count": float(sum(uniqs) / len(uniqs)),
                     "mean_gold_relevance": float(sum(rels) / len(rels)),
                     "mean_pairwise_similarity": float(sum(sims) / len(sims)),
                     "mean_redundancy": float(sum(reds) / len(reds)),
                     "mean_jaccard_vs_b0": float(sum(jacs) / len(jacs)),
                     "mean_replacement_count_vs_b0": float(sum(reps) / len(reps))})
        log.info("lambda=%s DC=%.6f NDCG=%.6f red=%.6f", lam, rows[-1]["mean_demand_cov_5"],
                 rows[-1]["mean_ndcg_10"], rows[-1]["mean_redundancy"])

    best = rows[0]
    for r in rows[1:]:
        if r["mean_demand_cov_5"] > best["mean_demand_cov_5"] + 1e-9:
            best = r
        elif abs(r["mean_demand_cov_5"] - best["mean_demand_cov_5"]) < 1e-6:
            if r["mean_ndcg_10"] > best["mean_ndcg_10"] + 1e-9:
                best = r
            elif abs(r["mean_ndcg_10"] - best["mean_ndcg_10"]) < 1e-9:
                if r["mean_redundancy"] < best["mean_redundancy"] - 1e-9:
                    best = r
                elif abs(r["mean_redundancy"] - best["mean_redundancy"]) < 1e-9 and r["lambda"] > best["lambda"]:
                    best = r
    best_lambda = best["lambda"]
    for r in rows:
        r["selected"] = (r["lambda"] == best_lambda)
    C.write_csv(out / "tables/mmr_dev_lambda_selection.csv", rows)
    C.write_md(out / "mmr_dev_lambda_selection.md", [
        "# MMR lambda 选择（仅 formal_dev，全精度，fixed）", "",
        "## 选择结果：**lambda = %s**" % best_lambda, "",
        "规则（预先固定）：DemandCov@5 最高 → 差值<1e-6 时 NDCG@10 更高 → 冗余更低 → λ 更大。",
        "", "| lambda | DemandCov@5 | NDCG@10 | 唯一需求数 | gold rel | 内部相似度 | 冗余度 | Jaccard vs B0 | 替换数 | 选中 |",
        "|---|---|---|---|---|---|---|---|---|---|"] + [
        "| %s | %.6f | %.6f | %.6f | %.6f | %.6f | %.6f | %.6f | %.6f | %s |" % (
            r["lambda"], r["mean_demand_cov_5"], r["mean_ndcg_10"], r["mean_unique_demand_count"],
            r["mean_gold_relevance"], r["mean_pairwise_similarity"], r["mean_redundancy"],
            r["mean_jaccard_vs_b0"], r["mean_replacement_count_vs_b0"], "✓" if r["selected"] else "")
        for r in rows])
    with io.open(out / "frozen_lambda.json", "w", encoding="utf-8") as f:
        json.dump({"lambda": best_lambda, "selection_split": "formal_dev", "k_frozen": 5,
                   "rule": "DemandCov@5 -> NDCG@10 -> redundancy -> larger lambda",
                   "sim": "char2-4gram TF-IDF cosine (float64)", "rel": "reranker_score min-max per qid",
                   "tie_break": "MMR score desc -> reranker desc -> doc_id asc"},
                  f, ensure_ascii=False, indent=2)
    xs = [r["lambda"] for r in rows]
    for metric, name, ylab in [("mean_demand_cov_5", "demandcov", "DemandCov@5"), ("mean_ndcg_10", "ndcg", "NDCG@10")]:
        fig, ax = plt.subplots(figsize=(4.6, 3.4), dpi=300)
        ax.plot(xs, [r[metric] for r in rows], "ko-", mfc="white", mec="k", ms=6, lw=1.4)
        ax.axvline(best_lambda, ls=":", color="k", lw=1.0)
        ax.set_xlabel("lambda"); ax.set_ylabel(ylab); ax.set_xticks(xs)
        ax.grid(True, ls=":", color="0.6", lw=0.6)
        fig.tight_layout()
        fig.savefig(out / f"figures/mmr_lambda_dev_curve_{name}.png", dpi=300)
        fig.savefig(out / f"figures/mmr_lambda_dev_curve_{name}.pdf")
        if name == "demandcov":
            fig.savefig(out / "figures/mmr_lambda_dev_curve.png", dpi=300)
            fig.savefig(out / "figures/mmr_lambda_dev_curve.pdf")
        plt.close(fig)
    log.info("selected lambda = %s", best_lambda)
    print("DONE lambda select", best_lambda)


if __name__ == "__main__":
    main()
