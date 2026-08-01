#!/usr/bin/env python
"""10_generate_figures.py (fixed) — 生成全部图表（λ 曲线 + Top-K 四指标 × 三划分，黑白 300dpi）。"""
import argparse, io, csv, logging, sys, traceback
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_figs")
SPLITS = ["formal_train", "internal_blind", "cmedqa2_external"]
METHODS = ["B0", "D0", "D3_TFIDF", "MMR"]
METRICS = [("demand_cov_at_k", "DemandCov@K", "topk_demandcov"),
           ("ndcg_at_k", "NDCG@K", "topk_ndcg_at_k"),
           ("official_ndcg_10", "Official NDCG@10 (compat)", "topk_official_ndcg10"),
           ("redundancy", "Redundancy", "topk_redundancy")]
STYLES = {"B0": ("-", "o"), "D0": ("--", "s"), "D3_TFIDF": ("-.", "^"), "MMR": (":", "x")}
KS = C.K_LIST


def load_summ(out):
    summ = {}
    with io.open(out / "tables/topk_sensitivity_summary.csv", "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            summ[(r["split"], r["method"], int(r["k"]))] = r
    return summ


def draw(out, sp, metric, ylab, base, want_main):
    fig, ax = plt.subplots(figsize=(4.8, 3.6), dpi=300)
    for m in METHODS:
        ys = [float(summ.get((sp, m, k), {}).get(metric, "nan")) for k in KS]
        ls, mk = STYLES[m]
        ax.plot(KS, ys, color="k", ls=ls, marker=mk, mfc="white", mec="k", ms=6, lw=1.4, label=m)
    ax.set_xlabel("K (selection budget)"); ax.set_ylabel(ylab)
    ax.set_xticks(KS); ax.set_xticklabels([f"K={k}" for k in KS])
    ax.set_title(f"{ylab} by K — {sp}", fontsize=10)
    ax.grid(True, ls=":", color="0.6", lw=0.6); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out / f"figures/{base}_{sp}.{ext}", dpi=300)
        if want_main:
            fig.savefig(out / f"figures/{base}.{ext}", dpi=300)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="生成全部图表")
    ap.add_argument("--out", default=str(C.V5))
    args = ap.parse_args()
    out = Path(args.out)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    global summ
    summ = load_summ(out)
    ok, fail = 0, []
    for metric, ylab, base in METRICS:
        for sp in SPLITS:
            try:
                draw(out, sp, metric, ylab, base, want_main=(sp == "formal_train"))
                ok += 1
            except Exception:
                fail.append((base, sp)); log.error(traceback.format_exc())
    log.info("figures ok=%d fail=%d", ok, len(fail))
    print("DONE figures", ok, "fail", len(fail))


if __name__ == "__main__":
    summ = None
    main()
