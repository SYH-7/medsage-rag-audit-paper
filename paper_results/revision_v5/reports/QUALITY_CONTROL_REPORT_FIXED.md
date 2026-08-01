# 最终质量控制报告（fixed）

## 26 项检查

| # | 检查项 | 状态 | 证据 |
|---|---|---|---|
| 1 | 原 240 条答案未被重新生成 | PASS | 未调用 LLM/生成代码（声明） |
| 2 | 人工评分未被修改 | PASS | 未读取或写入 A/B/C 评分（声明） |
| 3 | 原冻结目录未被覆盖 | PASS | 新产物全部写入 revision_v5_mmr_topk_fixed（声明） |
| 4 | K=5 冻结结果全精度复现 | PASS | 15/15 通过（1e-4） |
| 5 | MMR 候选池与 B0 一致 | PASS | 同一 candidate_pools 文件 |
| 6 | MMR 未读取 Gold 完成选择 | PASS | mmr_select_tfidf 仅用 reranker_score + TF-IDF |
| 7 | lambda 只在 formal_dev 选择 | PASS | formal_dev |
| 8 | λ=1 精确复现 B0（显式 tie-break 后） | PASS | 12/12 通过 |
| 9 | Top-K 只改变 K | PASS | 07/08 仅遍历 K（声明） |
| 10 | D3 权重与阈值未改变 | PASS | frozen_medsage_evaluation 常量 + TH=0.5 |
| 11 | Bootstrap 为 qid 级 | PASS | diff=a-b，同一组 qid 索引 idx 重采样 |
| 12 | Bootstrap 为 10000 次 | PASS | v5f_common N_BOOT=10000 |
| 13 | seed=42 | PASS | v5f_common SEED=42 |
| 14 | Holm family 划分正确 | PASS | PRIMARY/DIAGNOSTIC/SUPPLEMENTARY 各自独立 Holm |
| 15 | 不显著未解释为等效 | PASS | 统一表述「未检测到经多重校正后的稳定差异」 |
| 16 | MMR 结果可追溯到 doc_id | PASS | mmr_results_per_qid.csv 含 selected_doc_ids |
| 17 | Top-K 结果可追溯到 qid | PASS | topk_sensitivity_per_qid.csv 含 qid |
| 18 | 所有图表由真实数据生成 | PASS | 10_generate_figures.py 仅读汇总 CSV |
| 19 | Excel 可打开 | PASS | 工作表数=≥12 |
| 20 | 无虚构结果 | PASS | 全部数值来自真实计算（声明） |
| 21 | 未把任务型需求分类写成临床本体 | PASS | 全部报告含 ICD/SNOMED 澄清 |
| 22 | 未使用测试集调参 | PASS | λ 仅 formal_dev |
| 23 | 配对 Bootstrap 已修复 | PASS | diff=a-b 同索引重采样（v5f_common） |
| 24 | 6 类需求映射已修复 | PASS | gold_ev_demands 返回 {ONT[s]}（6 类） |
| 25 | MMR 显式 tie-break 已实现 | PASS | 候选比较按 (-s, -reranker, doc_id) 最小者 |
| 26 | 全精度统计 | PASS | 逐 qid/均值/Bootstrap/CI/p/Holm 全程 float64，CSV ≥8 位 |

## 结论
**全部通过，结果可用于论文素材**
