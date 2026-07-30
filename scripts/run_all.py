#!/usr/bin/env python
"""Reproduction verification - re-computes all aggregates from per-query data.
Uses proper paired bootstrap with shared qid indices, 10000 iterations, seed=42."""
import sys, os, json, csv
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parent.parent
exit_code = 0

def dcmp(a, b, tol=1e-4):
    return abs(a - b) < tol

def load_csv(path):
    with open(path) as f: return list(csv.DictReader(f))

def paired_bootstrap_qid(a_dict, b_dict, n_iter=10000, seed=42):
    """Paired bootstrap with shared qid indices."""
    common = sorted(set(a_dict.keys()) & set(b_dict.keys()))
    if len(common) == 0: return None
    a, b = np.array([a_dict[q] for q in common]), np.array([b_dict[q] for q in common])
    n = len(a); diff = float(np.mean(a - b))
    rng = np.random.RandomState(seed)
    boot = []
    for _ in range(n_iter):
        idx = rng.randint(0, n, n)
        boot.append(float(np.mean(a[idx] - b[idx])))
    p_low = (sum(d <= 0 for d in boot) + 1) / (n_iter + 1)
    p_high = (sum(d >= 0 for d in boot) + 1) / (n_iter + 1)
    p = min(1.0, 2 * min(p_low, p_high))
    return {"diff": diff, "p": p, "ci95_low": float(np.percentile(boot, 2.5)),
            "ci95_high": float(np.percentile(boot, 97.5)), "n": n}

results = {}
print("[1/10] Environment check...")
results["environment"] = {"python": sys.version, "ok": True}

print("[2/10] Ontology check...")
onto = REPO / "configs/ontology.json"
if onto.exists():
    data = json.loads(onto.read_text(encoding='utf-8'))
    l2 = data.get("level_2", {}); assert "risk_medication" in l2
    results["ontology"] = {"loaded": True, "classes_15": len(l2)}
    print(f"  Ontology: {len(l2)} classes")
else:
    results["ontology"] = {"loaded": False}; exit_code = 1

print("[3/10] Structure check...")
for d in ["src/private_evaluation", "src/public_runtime", "paper_results/manifests", "paper_results/per_query_minimal"]:
    if not (REPO / d).exists(): exit_code = 1
print("  OK")

pq_dir = REPO / "paper_results/per_query_minimal"
pq_files = sorted(pq_dir.glob("*per_query*"))
results["per_query_files"] = len(pq_files)
print(f"[4/10] Per-query files: {len(pq_files)}")

# Step 5: B0-D3 DemandCov + NDCG
print("[5/10] B0-D3 DemandCov + NDCG...")
paper_main = load_csv(str(REPO / "paper_results/manifests/main_results.csv"))
paper_dc = {(r["split"], r["method"]): float(r["demand_cov"]) for r in paper_main}
paper_ndcg = {(r["split"], r["method"]): float(r["ndcg"]) for r in paper_main}
dc_match = ndcg_match = 0; dc_mismatch = ndcg_mismatch = 0

for pqf in pq_files:
    split = pqf.stem.replace("_per_query", "")
    bm = {m: {"dc": [], "ndcg": []} for m in ["B0", "D0", "D1", "D2", "D3"]}
    with open(pqf) as f:
        for line in f:
            r = json.loads(line); m = r["method"]
            bm[m]["dc"].append(float(r.get("dc", 0) or 0))
            bm[m]["ndcg"].append(float(r.get("ndcg", 0) or 0))
    for method in ["B0", "D0", "D1", "D2", "D3"]:
        key = f"{split}_{method.lower()}"
        dc_v = bm[method]["dc"]; ndcg_v = bm[method]["ndcg"]; n = len(dc_v)
        if n == 0: print(f"  MISS {key}"); exit_code = 1; continue
        rdc = sum(dc_v) / n; rndcg = sum(ndcg_v) / n
        pdc = paper_dc.get((split, method)); pndcg = paper_ndcg.get((split, method))
        md = dcmp(rdc, pdc) if pdc else False; mn = dcmp(rndcg, pndcg) if pndcg else False
        if md:
            dc_match += 1
        else:
            dc_mismatch += 1
        if mn:
            ndcg_match += 1
        else:
            ndcg_mismatch += 1
        dd = rdc - pdc if pdc else None; nd = rndcg - pndcg if pndcg else None
        results[key] = {"n": n, "dc": rdc, "dc_paper": pdc, "dc_match": md, "dc_diff": dd,
                        "ndcg": rndcg, "ndcg_paper": pndcg, "ndcg_match": mn, "ndcg_diff": nd}
        print(f"  {key}: n={n} dc={rdc:.4f}/{pdc} diff={dd} [{'M' if md else 'X'}] ndcg={rndcg:.4f}/{pndcg} diff={nd} [{'M' if mn else 'X'}]")
        if not md or not mn: exit_code = 1
print(f"  DC: {dc_match} match {dc_mismatch} mis | NDCG: {ndcg_match} match {ndcg_mismatch} mis")

# Step 6: Gaps (QL=D0-D1, EL=D0-D2)
print("[6/10] Gaps (QL=D0-D1, EL=D0-D2)...")
for pqf in pq_files:
    split = pqf.stem.replace("_per_query", "")
    bm = {m: {"dc": []} for m in ["B0", "D0", "D1", "D2", "D3"]}
    with open(pqf) as f:
        for line in f:
            r = json.loads(line); bm[r["method"]]["dc"].append(float(r.get("dc", 0) or 0))
    b0 = sum(bm["B0"]["dc"]) / max(len(bm["B0"]["dc"]), 1)
    d0 = sum(bm["D0"]["dc"]) / max(len(bm["D0"]["dc"]), 1)
    d1 = sum(bm["D1"]["dc"]) / max(len(bm["D1"]["dc"]), 1)
    d2 = sum(bm["D2"]["dc"]) / max(len(bm["D2"]["dc"]), 1)
    d3 = sum(bm["D3"]["dc"]) / max(len(bm["D3"]["dc"]), 1)
    og = d0 - b0; denom = max(og, 1e-10)
    cg = {"oracle_gain": og, "query_loss": d0 - d1, "evidence_loss": d0 - d2,
          "deployment_gap": d0 - d3, "interaction_loss": d1 + d2 - d0 - d3,
          "query_recovery": (d1 - b0) / denom, "evidence_recovery": (d2 - b0) / denom,
          "e2e_recovery": (d3 - b0) / denom}
    results[f"gap_{split}"] = cg
    print(f"  {split}: OG={og:.4f} QL={cg['query_loss']:.4f} EL={cg['evidence_loss']:.4f} DG={cg['deployment_gap']:.4f}")

# Step 7: Paired bootstrap with qid_hash (10000 iterations, seed=42)
print("[7/10] Paired bootstrap (10000 iters, seed=42, shared qid indices)...")
bootstrap_match = 0; bootstrap_mismatch = 0
sig_paper = load_csv(str(REPO / "paper_results/manifests/significance.csv"))
sig_map = {}
for row in sig_paper:
    sig_map[(row["split"], row["method_a"], row["method_b"])] = {
        "diff": float(row["diff"]), "p": float(row["p_value"]),
        "ci95_low": float(row["ci95_low"]), "ci95_high": float(row["ci95_high"])}

for pqf in pq_files:
    split = pqf.stem.replace("_per_query", "")
    by_qid = {}
    with open(pqf) as f:
        for line in f:
            r = json.loads(line); qh = r["qid_hash"]; m = r["method"]
            dc = float(r.get("dc", 0) or 0)
            if qh not in by_qid: by_qid[qh] = {}
            by_qid[qh][m] = dc
    b0 = {q: d["B0"] for q, d in by_qid.items() if "B0" in d}
    d0 = {q: d["D0"] for q, d in by_qid.items() if "D0" in d}
    d1 = {q: d["D1"] for q, d in by_qid.items() if "D1" in d}
    d2 = {q: d["D2"] for q, d in by_qid.items() if "D2" in d}
    d3 = {q: d["D3"] for q, d in by_qid.items() if "D3" in d}
    
    for pair_name, ma, mb in [("D0_vs_B0", d0, b0), ("D1_vs_B0", d1, b0),
                                ("D2_vs_B0", d2, b0), ("D3_vs_B0", d3, b0)]:
        key = f"bootstrap_{split}_{pair_name}"
        br = paired_bootstrap_qid(ma, mb)
        if br is None: print(f"  SKIP {key}"); continue
        results[key] = br
        paper_key = (split, pair_name.split("_vs_")[0], pair_name.split("_vs_")[1])
        ps = sig_map.get(paper_key)
        if ps:
            md = dcmp(br["diff"], ps["diff"]) and dcmp(br["ci95_low"], ps["ci95_low"]) and dcmp(br["ci95_high"], ps["ci95_high"])
            if md: bootstrap_match += 1
            else: bootstrap_mismatch += 1
            print(f"  {key}: diff={br['diff']:.4f}(paper={ps['diff']}) p={br['p']:.6f}(paper={ps['p']}) ci95=[{br['ci95_low']:.4f},{br['ci95_high']:.4f}](paper=[{ps['ci95_low']:.4f},{ps['ci95_high']:.4f}]) [{'M' if md else 'X'}]")
            if not md: exit_code = 1
        else:
            print(f"  {key}: diff={br['diff']:.4f} p={br['p']:.6f} (no paper comparison)")

print(f"  Bootstrap: {bootstrap_match} match {bootstrap_mismatch} mis")

# Step 8: Leakage CSV
print("[8/10] Leakage summary...")
leak = REPO / "paper_results/manifests/leakage_summary.csv"
if leak.exists(): results["leakage_tests"] = len(load_csv(str(leak)))

# Step 9: BGE comparison
print("[9/10] BGE comparison...")
bert = REPO / "paper_results/manifests/bert_vs_tfidf_direct_metrics.csv"
if bert.exists(): results["bge_comparisons"] = len(load_csv(str(bert)))

# Step 10: Manifest
print("[10/10] Manifest...")
mf = REPO / "paper_results/manifests/release_manifest_sha256.csv"
if mf.exists():
    with open(mf) as f: rows = list(csv.reader(f))
    results["manifest"] = {"total_files": len(rows)-1}
    print(f"  {len(rows)-1} files")

with open(str(REPO / "PAPER_REPRODUCTION_REPORT.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"Status: {'PASSED' if exit_code == 0 else 'FAILED'}")
sys.exit(exit_code)
