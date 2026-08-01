#!/usr/bin/env python
"""02_reproduce_frozen_k5.py (fixed) — 全精度复现 K=5 冻结结果（门控）。

预测复用旧版缓存（不重训 Q1/E2）；逐 qid 全精度，均值全精度，输出 8 位小数。
"""
import argparse, logging, sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_gate")

EXPECT = {
    "formal_train": {"B0": (0.8762, 0.6413), "D0": (0.9398, 0.6012), "D1": (0.9219, 0.6065), "D2": (0.8702, 0.6319), "D3": (0.8745, 0.6293)},
    "internal_blind": {"B0": (0.9183, 0.5338), "D0": (0.9819, 0.4988), "D1": (0.9537, 0.5094), "D2": (0.9282, 0.5109), "D3": (0.9216, 0.5075)},
    "cmedqa2_external": {"B0": (0.9630, 0.5166), "D0": (0.9859, 0.4849), "D1": (0.9836, 0.4961), "D2": (0.9765, 0.5074), "D3": (0.9730, 0.4954)},
}


def main():
    ap = argparse.ArgumentParser(description="全精度复现 K=5 冻结结果（门控）")
    ap.add_argument("--out", default=str(C.V5))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    ann = C.load_annotations()
    pools = C.load_pools(["formal_train", "internal_blind", "cmedqa2_external"])
    qg_int, eg_int = C.load_phase6b_gold("internal_blind")
    qg_ext, eg_ext = C.load_phase6b_gold("cmedqa2_external")
    GOLD = {"formal_train": C.build_gold("formal_train", ann=ann),
            "internal_blind": C.build_gold("internal_blind", qg=qg_int, eg=eg_int),
            "cmedqa2_external": C.build_gold("cmedqa2_external", qg=qg_ext, eg=eg_ext)}
    preds = C.ensure_predictions()  # 复用旧缓存，不重训
    log.info("predictions loaded (cached)")

    rows, fails = [], []
    for sp, exp in EXPECT.items():
        gqd, gev, grel = GOLD[sp]
        pq, pp = preds[sp]["pq"], preds[sp]["pp"]
        res = defaultdict(lambda: {"dc": [], "ndcg": []})
        for qs in sorted(set(pools[sp]) & set(gqd)):
            ca = pools[sp][qs]
            gd = gqd[qs]; pd = pq.get(qs, set())
            def eg(d, qi=qs): return C.map_states_to_demands(gev[qi].get(d, set()))
            def ep(d, qi=qs): return pp.get((qi, d), set())
            sels = {"B0": C.select_b0_k(ca, 5), "D0": C.select_version_b_k(gd, ca, eg, 5),
                    "D1": C.select_version_b_k(pd if pd else gd, ca, eg, 5),
                    "D2": C.select_version_b_k(gd, ca, ep, 5), "D3": C.select_version_b_k(pd, ca, ep, 5)}
            for m, sel in sels.items():
                res[m]["dc"].append(C.compute_demand_cov(sel, qs, gev, gd))
                res[m]["ndcg"].append(C.compute_ndcg(sel, qs, grel))
        for m in ["B0", "D0", "D1", "D2", "D3"]:
            dc = float(np.mean(res[m]["dc"]))
            ng = float(np.mean(res[m]["ndcg"]))
            e_dc, e_ng = exp[m]
            ok = abs(dc - e_dc) <= 1e-4 and abs(ng - e_ng) <= 1e-4
            rows.append({"split": sp, "method": m, "n_qid": len(res[m]["dc"]),
                         "demand_cov_expected": e_dc, "demand_cov_actual": dc,
                         "ndcg_expected": e_ng, "ndcg_actual": ng,
                         "dc_diff": dc - e_dc, "ndcg_diff": ng - e_ng, "pass": ok})
            if not ok:
                fails.append((sp, m, dc, ng, e_dc, e_ng))
            log.info("%s %s: DC=%.6f (exp %.4f) NDCG=%.6f (exp %.4f) ok=%s",
                     sp, m, dc, e_dc, ng, e_ng, ok)
    C.write_csv(out / "freeze_reproduction_result.csv", rows)

    if fails:
        md = ["# FREEZE_REPRODUCTION_FAILED (fixed)", "",
              "| split | method | 实际 DC | 期望 DC | 实际 NDCG | 期望 NDCG | 差异 DC | 差异 NDCG |", "|---|---|---|---|---|---|---|---|"]
        for sp, m, dc, ng, e_dc, e_ng in fails:
            md.append(f"| {sp} | {m} | {dc:.8f} | {e_dc:.4f} | {ng:.8f} | {e_ng:.4f} | {dc-e_dc:+.8f} | {ng-e_ng:+.8f} |")
        C.write_md(out / "FREEZE_REPRODUCTION_FAILED.md", md)
        log.error("GATE FAILED")
        sys.exit(1)
    md = ["# 冻结结果复现门控（K=5，全精度，fixed）", "",
          "## 状态：**COMPLETE_REPRODUCTION_PASS**", "",
          "| split | method | DemandCov | NDCG |", "|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['split']} | {r['method']} | {r['demand_cov_actual']:.6f} | {r['ndcg_actual']:.6f} |")
    C.write_md(out / "freeze_reproduction.md", md)
    log.info("GATE PASS")
    print("DONE gate PASS")


if __name__ == "__main__":
    import numpy as np
    main()
