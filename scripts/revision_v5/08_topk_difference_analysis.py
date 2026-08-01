#!/usr/bin/env python
"""08_topk_difference_analysis.py (fixed) — Top-K 差值（vs K=5）与稳定性描述。

口径：跨 K 比较以 DemandCov@K、NDCG@K 为主；official NDCG@10 仅用于与 K=5 口径兼容，
不将其随 K 的机械上升解释为排序质量改善。
"""
import argparse, io, csv, logging, sys
from pathlib import Path
from collections import defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_topkdiff")
SPLITS = ["formal_train", "internal_blind", "cmedqa2_external"]
METHODS = ["B0", "D0", "D1", "D2", "D3_TFIDF", "MMR"]


def main():
    ap = argparse.ArgumentParser(description="Top-K 差值（vs K=5）与稳定性")
    ap.add_argument("--out", default=str(C.V5))
    ap.add_argument("--ks", default="3,7")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    KS_CMP = [int(x) for x in args.ks.split(",")]
    base_k = 5

    per = defaultdict(dict)
    with io.open(out / "tables/topk_sensitivity_per_qid.csv", "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            per[(r["split"], r["method"], int(r["k"]))][r["qid"]] = r

    def pm(sp, m, k):
        return per.get((sp, m, k), {})

    diff_rows = []
    for sp in SPLITS:
        for m in METHODS:
            base = pm(sp, m, base_k)
            if not base:
                continue
            for kc in KS_CMP:
                cur = pm(sp, m, kc)
                common = sorted(set(base) & set(cur))
                def d(key):
                    return [float(cur[q][key]) - float(base[q][key]) for q in common]
                d_dc, d_nd, d_o10, d_un, d_rd = d("demand_cov_at_k"), d("ndcg_at_k"), d("official_ndcg_10"), d("unique_demand_count"), d("redundancy")
                ci = C.paired_bootstrap_ci(d_dc, [0.0] * len(d_dc)) if d_dc else {"ci_low": 0.0, "ci_high": 0.0}
                diff_rows.append({"split": sp, "method": m, "comparison": f"K{kc}_vs_K{base_k}", "n_qid": len(common),
                                  "delta_demand_cov": float(np.mean(d_dc)),
                                  "delta_demand_cov_ci_low": ci["ci_low"],
                                  "delta_demand_cov_ci_high": ci["ci_high"],
                                  "delta_ndcg_at_k": float(np.mean(d_nd)),
                                  "delta_official_ndcg_10": float(np.mean(d_o10)),
                                  "delta_unique_demand_count": float(np.mean(d_un)),
                                  "delta_redundancy": float(np.mean(d_rd))})
    C.write_csv(out / "tables/topk_sensitivity_differences.csv", diff_rows)

    summ = {}
    with io.open(out / "tables/topk_sensitivity_summary.csv", "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            summ[(r["split"], r["method"], int(r["k"]))] = r

    md = ["# Top-K 敏感性报告（fixed：DemandCov@K / NDCG@K 为主口径）", "",
          "## 方法", "",
          "- 仅改变 K∈{3,5,7}；候选池、Q1/E2 预测、Version B 权重、阈值、reranker、MMR λ 均不变；",
          "- **跨 K 比较以 DemandCov@K、NDCG@K 为主指标**；",
          "- **official NDCG@10 仅用于与原 K=5 口径兼容，不得将其随 K 增加的机械上升解释为排序质量改善**；",
          "- 差值以 K=5 为参照；qid 级配对 Bootstrap（10000 次，seed=42，percentile 95% CI）仅用于描述；",
          "- 稳定性判定为描述性，不设显著性门槛、不筛选结果。",
          "",
          "## 稳定性判定（描述性，基于 DemandCov@K 与 NDCG@K 的方法相对排序）", ""]
    for sp in SPLITS:
        ranks = {}
        for k in [3, 5, 7]:
            sub = [summ[(sp, m, k)] for m in ["B0", "MMR", "D3_TFIDF"] if (sp, m, k) in summ]
            order = sorted(sub, key=lambda r: -float(r["demand_cov_at_k"]))
            ranks[k] = [r["method"] for r in order]
        pos = defaultdict(list)
        for k in [3, 5, 7]:
            for i, m in enumerate(ranks[k]):
                pos[m].append(i)
        max_shift = max(max(v) - min(v) for v in pos.values())
        first_consistent = ranks[3][0] == ranks[5][0] == ranks[7][0]
        flip = (ranks[3][0] != ranks[7][0]) or max_shift >= 2
        dir_ok, max_abs = True, 0.0
        for m in ["B0", "MMR", "D3_TFIDF"]:
            d37 = next((r for r in diff_rows if r["split"] == sp and r["method"] == m and r["comparison"] == "K7_vs_K5"), None)
            d35 = next((r for r in diff_rows if r["split"] == sp and r["method"] == m and r["comparison"] == "K3_vs_K5"), None)
            if d37 and d35:
                max_abs = max(max_abs, abs(d37["delta_demand_cov"]), abs(d35["delta_demand_cov"]))
                if d37["delta_demand_cov"] * d35["delta_demand_cov"] < -1e-9:
                    dir_ok = False
        if flip:
            verdict = "K_SENSITIVE"
        elif ranks[3] == ranks[5] == ranks[7] and dir_ok:
            verdict = "DIRECTIONALLY_STABLE"
        elif ranks[3] == ranks[5] == ranks[7] and max_abs < 5e-3:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "DIRECTIONALLY_STABLE"
        md.append(f"### {sp}")
        md.append(f"- 方法 DemandCov@K 排序（K=3/5/7）：{ranks[3]} / {ranks[5]} / {ranks[7]}")
        md.append(f"- 主导方法跨 K 一致：{first_consistent}；最大排名位移={max_shift}")
        md.append(f"- 判定：**{verdict}**（描述性）")
        md.append("")
    md += ["", "## 说明", "",
           "- DemandCov@K、NDCG@K 随 K 的上升体现预算扩展本身；官方 NDCG@10 的上升仅因可见位置增多，不作为排序质量改善证据；",
           "- 固定 NDCG@10 受返回列表长度影响，跨 K 稳健性主要依据 DemandCov@K、NDCG@K 及方法相对排序。",
           "- 「DIRECTIONALLY_STABLE」不等价于统计显著或方法等效。"]
    C.write_md(out / "topk_sensitivity_report.md", md)
    log.info("difference analysis done: %d rows", len(diff_rows))
    print("DONE topk difference", len(diff_rows))


if __name__ == "__main__":
    main()
