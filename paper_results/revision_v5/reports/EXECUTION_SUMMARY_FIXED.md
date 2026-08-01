# 最终执行摘要（fixed）

## 修复说明（10 项）

**1. 配对 Bootstrap 错误是否修复？**
是。diff=a−b 后对同一组 qid 索引 idx 重采样 mean(diff[idx])；不再为 A/B 各自独立采样。

**2. 6 类需求映射是否修复？**
是。gold_ev_demands 返回 {ONT[s] for s in states if s in ONT}（6 类 demand），影响 unique_demand_count 与 redundancy。

**3. tie-break 是否显式实现？**
是。候选比较严格按 MMR score 降序 → reranker_score 降序 → doc_id 升序（确定性 key 比较，不依赖文件顺序）。

**4. λ 是否仍为 0.6？**
是（0.6）。formal_dev DemandCov@5 最高规则，规则与冻结不变。

**5. MMR 核心数值是否变化？**
DemandCov@5 基本不变（覆盖维度）；NDCG@10 与冗余度/unique demand 因 6 类映射与 float64 微变；显著性因配对 Bootstrap 修复发生变化（见 6）。

**6. 哪些 Holm 校正结果显著？**
3 项显著（共 18 项检验）：PRIMARY_NDCG cmedqa2_external ndcg_10 MMR vs B0 p_Holm=0.0066；SUPPLEMENTARY formal_train ndcg_10 D3_TFIDF vs B0 p_Holm=0.0220；SUPPLEMENTARY internal_blind ndcg_10 D3_TFIDF vs B0 p_Holm=0.0204

**7. Top-K 结论是否仍方向稳定？**
是（描述性）。三划分均 DIRECTIONALLY_STABLE（以 DemandCov@K 排序判定；official NDCG@10 仅兼容 K=5）。

**8. unique demand 和 redundancy 修正前后变化？**
修正后基于 6 类 demand 集合（此前错误地以 15 类 state 计数）；具体数值见 mmr_summary.csv（fixed）。

**9. 全精度 K=5 是否复现冻结结果？**
是。15/15 在 1e-4 容差内复现（freeze_reproduction_result.csv，全精度计算后舍入对比）。

**10. 是否通过全部质量门控？**
是。冻结复现、λ=1 端点、输入/公平性验证、26 项 QC 全部通过；详见 QUALITY_CONTROL_REPORT_FIXED.md。

## 核心结果

λ=0.6；DemandCov@5：formal_train MMR=0.8768 vs B0=0.8762，internal MMR=0.9310 vs B0=0.9183，external MMR=0.9589 vs B0=0.9630。

Top-K：三划分方法 DemandCov@K 随 K 单调上升；formal_train MMR DemandCov@7=0.9216（B0 0.9113 / D3 0.9016）。
