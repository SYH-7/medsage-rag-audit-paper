# 生成端与泄漏注入材料说明

- `paper_results/generation/v2_validation/`：60 题 4 条件 240 条答案的盲评统计、独立性与仲裁（A/B/C），Holm 校正后无显著差异；
- `paper_results/generation/v3_frozen/`：生成端唯一正式冻结统计（exact sign / McNemar / 双家族 Holm）；
- `paper_results/revision_v5/tables/leakage_ndcg_*.csv`：泄漏注入 1050 行（3 场景 × 7 率 × 50 seed）补算 NDCG@10（ddof=1），端点与 R7 冻结值闭合；
- `paper_results/revision_v5/figures/leakage_demandcov_and_ndcg_blackwhite.*`：论文图 2（黑白，300dpi）。
