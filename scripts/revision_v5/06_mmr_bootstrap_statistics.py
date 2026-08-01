#!/usr/bin/env python
"""06_mmr_bootstrap_statistics.py (fixed) — MMR 显著性（修复：qid 级配对重采样 + Holm，全精度）。

修复说明：diff = a - b，对同一组 qid 索引 idx 重采样 mean(diff[idx])；
不再为 A/B 各自独立采样索引。
"""
import argparse, io, csv, logging, sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_sig")
SPLITS = ["formal_train", "internal_blind", "cmedqa2_external"]
METRICS = ["demand_cov", "ndcg_10"]


def main():
    ap = argparse.ArgumentParser(description="MMR 显著性（配对 Bootstrap 修复版 + Holm）")
    ap.add_argument("--out", default=str(C.V5))
    ap.add_argument("--input", default="tables/mmr_results_per_qid.csv")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    per = defaultdict(dict)
    with io.open(out / args.input, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            per[(r["split"], r["method"])][r["qid"]] = {"demand_cov": float(r["demand_cov"]),
                                                        "ndcg_10": float(r["ndcg_10"])}
    FAMILIES = {
        "PRIMARY_DC": [("MMR", "B0", "demand_cov", sp) for sp in SPLITS],
        "PRIMARY_NDCG": [("MMR", "B0", "ndcg_10", sp) for sp in SPLITS],
        "DIAGNOSTIC_DC": [("MMR", "D3_TFIDF", "demand_cov", sp) for sp in SPLITS],
        "DIAGNOSTIC_NDCG": [("MMR", "D3_TFIDF", "ndcg_10", sp) for sp in SPLITS],
        "SUPPLEMENTARY": [("D3_TFIDF", "B0", m, sp) for sp in SPLITS for m in METRICS],
    }
    all_rows = []
    for fam, comps in FAMILIES.items():
        comp_rows = []
        for ma, mb, metric, sp in comps:
            da, db = per[(sp, ma)], per[(sp, mb)]
            common = sorted(set(da) & set(db))
            av, bv = [da[q][metric] for q in common], [db[q][metric] for q in common]
            b = C.paired_bootstrap_ci(av, bv)  # 修复版：配对重采样
            pos, neg, tie = C.pos_neg_ties(av, bv)
            comp_rows.append({"family_id": fam, "split": sp, "metric": metric,
                              "method_a": ma, "method_b": mb, "n_qid": len(common),
                              "mean_a": float(sum(av) / len(av)), "mean_b": float(sum(bv) / len(bv)),
                              "mean_difference": b["mean_difference"], "ci_low": b["ci_low"],
                              "ci_high": b["ci_high"], "p_raw": b["p_raw"],
                              "positive_qid": pos, "negative_qid": neg, "tied_qid": tie})
            log.info("%s %s %s: %s-%s diff=%.6f CI=[%.6f, %.6f] p_raw=%.6f",
                     fam, sp, metric, ma, mb, b["mean_difference"], b["ci_low"], b["ci_high"], b["p_raw"])
        adj = C.holm_adjust([r["p_raw"] for r in comp_rows])
        for r, p_h in zip(comp_rows, adj):
            r["p_holm"] = p_h
            r["significant_raw"] = "YES" if r["p_raw"] < 0.05 else "NO"
            r["significant_holm"] = "YES" if p_h < 0.05 else "NO"
        all_rows.extend(comp_rows)
    C.write_csv(out / "tables/mmr_paired_bootstrap.csv", all_rows)

    md = ["# MMR 显著性检验报告（fixed：qid 级配对重采样）", "",
          "## 方法", "",
          "- diff = a − b；对同一组 qid 索引 idx 重采样 mean(diff[idx])，10000 次，seed=42，percentile 95% CI；",
          "- 每个 family 内 Holm 校正；",
          "- p>0.05 表述为「当前样本中未检测到经多重校正后的稳定差异」，不作等效结论。",
          "", "## 结果", "",
          "| family | split | metric | A vs B | n | diff | 95% CI | p_raw | p_Holm | sig(Holm) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in all_rows:
        md.append("| %s | %s | %s | %s vs %s | %d | %.6f | [%.6f, %.6f] | %.6f | %.6f | %s |" % (
            r["family_id"], r["split"], r["metric"], r["method_a"], r["method_b"], r["n_qid"],
            r["mean_difference"], r["ci_low"], r["ci_high"], r["p_raw"], r["p_holm"], r["significant_holm"]))
    C.write_md(out / "mmr_significance_report.md", md)
    log.info("significance done: %d rows", len(all_rows))
    print("DONE significance", len(all_rows))


if __name__ == "__main__":
    main()
