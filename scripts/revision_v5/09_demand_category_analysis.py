#!/usr/bin/env python
"""09_demand_category_analysis.py (fixed) — D01-D06 需求类别覆盖（条件覆盖率，ONT[s] 映射）。"""
import argparse, io, csv, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_cat")
SPLITS = ["formal_train", "internal_blind", "cmedqa2_external"]
CATS = list(C.L1)


def main():
    ap = argparse.ArgumentParser(description="D01-D06 需求类别覆盖分析")
    ap.add_argument("--out", default=str(C.V5))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    per = {}
    with io.open(out / "tables/topk_sensitivity_per_qid.csv", "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            sel = r["selected_doc_ids"].split("|") if r["selected_doc_ids"] else []
            per[(r["split"], r["method"], int(r["k"]), r["qid"])] = set(sel)

    ann = C.load_annotations()
    qg_int, _ = C.load_phase6b_gold("internal_blind")
    qg_ext, _ = C.load_phase6b_gold("cmedqa2_external")
    gold_dem = {}
    for sp in SPLITS:
        if sp == "formal_train":
            for qs, g in ann.items():
                gd = C.map_states_to_demands(set(g.get("query_states", [])))
                if gd:
                    gold_dem[(sp, qs)] = gd
        else:
            qg = qg_int if sp == "internal_blind" else qg_ext
            for qs, r in qg.items():
                gd = set(r.get("query_demands_6", []))
                if gd:
                    gold_dem[(sp, qs)] = gd
    qg_int, eg_int = C.load_phase6b_gold("internal_blind")
    qg_ext, eg_ext = C.load_phase6b_gold("cmedqa2_external")
    GOLDMAP = {"formal_train": C.build_gold("formal_train", ann=ann),
               "internal_blind": C.build_gold("internal_blind", qg=qg_int, eg=eg_int),
               "cmedqa2_external": C.build_gold("cmedqa2_external", qg=qg_ext, eg=eg_ext)}

    def doc_demands(sp, qs, doc):
        gev = GOLDMAP[sp][1]
        return {C.ONT[s] for s in gev.get(qs, {}).get(doc, set()) if s in C.ONT}

    rows = []
    for sp in SPLITS:
        for m in ["B0", "D0", "D1", "D2", "D3_TFIDF", "MMR"]:
            for k in C.K_LIST:
                for cat in CATS:
                    denom = covered = 0
                    for (sp2, qs), gd in gold_dem.items():
                        if sp2 != sp or cat not in gd:
                            continue
                        sel = per.get((sp, m, k, qs))
                        if sel is None:
                            continue
                        denom += 1
                        doc_cov = set()
                        for d in sel:
                            doc_cov |= doc_demands(sp, qs, d)
                        covered += int(cat in doc_cov)
                    rows.append({"split": sp, "method": m, "k": k, "category": cat,
                                 "denominator_qid": denom,
                                 "coverage_rate": (covered / denom) if denom else ""})
    C.write_csv(out / "tables/topk_demand_category_coverage.csv", rows)
    log.info("category rows: %d", len(rows))

    def rates(sp, m, k):
        return {r["category"]: (float(r["coverage_rate"]) if r["coverage_rate"] != "" else float("nan"))
                for r in rows if r["split"] == sp and r["method"] == m and r["k"] == k}

    md = ["# D01-D06 需求类别覆盖分析（fixed）", "",
          "> **D01-D06 是本任务的操作性信息需求分类，不是 ICD 或 SNOMED CT 临床术语本体。**", "",
          "定义：覆盖率 = 在 gold 查询含该类别的 qid 中，选择结果覆盖该类别的比例（条件覆盖率）。",
          "", "## 关键观察", ""]
    for sp in SPLITS:
        gains = {c: rates(sp, "B0", 7)[c] - rates(sp, "B0", 3)[c] for c in CATS
                 if c in rates(sp, "B0", 3) and c in rates(sp, "B0", 7)
                 and rates(sp, "B0", 3)[c] == rates(sp, "B0", 3)[c] and rates(sp, "B0", 7)[c] == rates(sp, "B0", 7)[c]}
        if gains:
            hi = max(gains, key=gains.get)
            md.append(f"- {sp}：B0 随 K 增加（K3→K7）增幅最大的类别：**{hi}**（Δ={gains[hi]:+.3f}）。")
        miss = {c: rates(sp, "B0", 3)[c] for c in CATS if c in rates(sp, "B0", 3) and rates(sp, "B0", 3)[c] == rates(sp, "B0", 3)[c]}
        if miss:
            lo = min(miss, key=miss.get)
            md.append(f"- {sp}：K=3 时 B0 覆盖率最低（最易遗漏）：**{lo}**（{miss[lo]:.3f}）。")
        delta = {c: rates(sp, "MMR", 5)[c] - rates(sp, "B0", 5)[c] for c in CATS
                 if c in rates(sp, "MMR", 5) and c in rates(sp, "B0", 5)
                 and rates(sp, "MMR", 5)[c] == rates(sp, "MMR", 5)[c] and rates(sp, "B0", 5)[c] == rates(sp, "B0", 5)[c]}
        if delta:
            hi = max(delta, key=delta.get)
            md.append(f"- {sp}：MMR-TFIDF 相对 B0 提升最明显的类别：**{hi}**（Δ={delta[hi]:+.3f}）。")
    md += ["", "## 明细", "",
           "逐 split × method × K × category 覆盖率与分母见 `tables/topk_demand_category_coverage.csv`。"]
    C.write_md(out / "topk_demand_category_analysis.md", md)
    print("DONE demand category")


if __name__ == "__main__":
    main()
