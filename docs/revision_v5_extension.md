# Revision V5 补充实验说明（MMR-TFIDF 与 Top-K 敏感性）

对应论文《医疗RAG证据选择的无泄漏评测、部署差距与生成验证》第 5 节与表 11-14。

## 统计口径（修正版）
- 配对 Bootstrap：diff = a − b，对同一组 qid 索引重采样 mean(diff[idx])，10000 次，seed=42，percentile 95% CI；
- 多重比较：PRIMARY_DC / PRIMARY_NDCG / DIAGNOSTIC_DC / DIAGNOSTIC_NDCG / SUPPLEMENTARY 各 family 内 Holm 校正；
- 6 类需求映射：gold_ev_demands 返回 {ONT[s]}（unique demand 与 redundancy 均按 6 类 demand 集合）；
- MMR-TFIDF 显式 tie-break：MMR score 降序 → reranker_score 降序 → doc_id 升序；
- 全精度：逐 qid/均值/Bootstrap/CI/p/Holm 全程 float64，逐 qid CSV ≥8 位小数，论文表最后保留 4 位。

## 关键结果
- λ 由 formal_dev 冻结为 0.6；
- 覆盖维度：MMR-TFIDF 与 B0、D3-TFIDF 的 DemandCov@5 差异经 Holm 校正后均不显著；
- 排序维度：external 上 MMR-TFIDF vs B0 的 NDCG@10 差异 Δ=−0.0155（95%CI [−0.0258, −0.0055]，p_Holm=0.0066）显著；
- K=3/5/7 下主要方法 DemandCov@K 排序方向一致（描述性）。
