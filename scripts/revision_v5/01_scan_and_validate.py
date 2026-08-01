#!/usr/bin/env python
"""01_scan_and_validate.py (fixed) — 扫描并验证正式数据版本（审计）。"""
import argparse, io, hashlib, logging, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v5f_common as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("v5f_scan")

CORE = [
    ("data/leakage_free/candidate_pools/formal_train_candidates.jsonl", "candidate_pool", "formal_train"),
    ("data/leakage_free/candidate_pools/formal_dev_candidates.jsonl", "candidate_pool", "formal_dev"),
    ("data/leakage_free/candidate_pools/internal_blind_candidates.jsonl", "candidate_pool", "internal_blind"),
    ("data/leakage_free/candidate_pools/cmedqa2_external_candidates.jsonl", "candidate_pool", "cmedqa2_external"),
    ("data/leakage_free/splits/formal_train_qids.json", "split", "formal_train"),
    ("data/leakage_free/splits/formal_dev_qids.json", "split", "formal_dev"),
    ("data/leakage_free/private_annotations/formal300_annotations.jsonl", "gold_annotation", "formal_train+dev"),
    ("data/leakage_free/phase6b_gold/internal_blind_query_gold.jsonl", "gold_query", "internal_blind"),
    ("data/leakage_free/phase6b_gold/internal_blind_evidence_gold.jsonl", "gold_evidence", "internal_blind"),
    ("data/leakage_free/phase6b_gold/cmedqa2_external_query_gold.jsonl", "gold_query", "cmedqa2_external"),
    ("data/leakage_free/phase6b_gold/cmedqa2_external_evidence_gold.jsonl", "gold_evidence", "cmedqa2_external"),
    ("data/leakage_free/ontology/hierarchical_medical_demands_v1.json", "ontology", "all"),
    ("data/leakage_free/state_prediction/formal_train_pairs_canonical.jsonl", "pairs_canonical", "formal_train"),
    ("outputs/dense_index/embeddings.npy", "embedding_cache", "all"),
    ("outputs/dense_index/documents.jsonl", "embedding_doc_map", "all"),
    ("outputs/phase6b_r7/main_results.csv", "frozen_results", "all"),
    ("experiments/common/frozen_medsage_evaluation.py", "eval_module", "all"),
]


def main():
    ap = argparse.ArgumentParser(description="扫描并验证正式数据版本（审计）")
    ap.add_argument("--out", default=str(C.V5))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for p, role, split in CORE:
        fp = C.ROOT / p
        if not fp.exists():
            rows.append({"file_path": p, "file_size": "", "modified_time": "", "sha256": "",
                         "inferred_role": role, "split": split, "is_frozen": True,
                         "selected_for_analysis": True, "notes": "MISSING"})
            continue
        st = fp.stat()
        h = hashlib.sha256()
        with io.open(fp, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        rows.append({"file_path": p, "file_size": st.st_size,
                     "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                     "sha256": h.hexdigest(), "inferred_role": role, "split": split,
                     "is_frozen": True, "selected_for_analysis": True, "notes": ""})
    C.write_csv(out / "file_inventory.csv", rows)
    log.info("scan done: %d files", len(rows))
    print("DONE scan", len(rows))


if __name__ == "__main__":
    main()
