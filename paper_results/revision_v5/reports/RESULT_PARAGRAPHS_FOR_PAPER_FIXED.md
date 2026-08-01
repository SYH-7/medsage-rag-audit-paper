# 论文可直接使用的段落草稿（fixed：配对 Bootstrap / 6 类映射 / 全精度）

> 所有数值引自 `tables/*.csv`（真实计算，未修改）；段落不假设 D3 优于 MMR；MMR 统一命名 MMR-TFIDF。

## 1. MMR 实验设置

MMR 基线与 B0、D3_TFIDF 使用完全相同的候选池（每查询 15 篇候选，external 1 个查询为 9 篇）。相关性项 Rel(d) 取冻结 reranker_score 的查询内 min-max 归一化（全部相同时统一为 0.5）；多样性项 Sim(d,s) 采用字符 2–4gram TF-IDF 余弦（float64，按查询拟合，仅限候选池文档），故命名为 MMR-TFIDF——基于 TF-IDF 文档相似度的 MMR 代理基线（dense embedding 对候选 doc_id 覆盖不足：formal_train≈46%、internal_blind≈40%、external≈15%）。选择为贪心：首文档取候选池最高 reranker_score（与 B0 首位一致）；候选比较严格按 MMR score 降序、reranker_score 降序、doc_id 升序的确定性 tie-break。评价使用官方 DemandCov@5 与 NDCG@10（gain=2^rel−1，rel∈{0,1,2}）。

## 2. MMR 参数冻结

λ 候选固定为 [0.5, 0.6, 0.7, 0.8, 0.9]，仅在 formal_dev（100 查询）上选择，规则预先固定：DemandCov@5 最高→NDCG@10→内部冗余更低→λ 更大。选中 λ=0.6（formal_dev DemandCov@5=0.904667，NDCG@10=0.609231）。选中后 λ 冻结，三个正式划分不再调整；未使用 internal_blind / external 进行任何选参。

## 3. MMR 主结果

| 方法 | formal_train DC/NDCG | internal_blind DC/NDCG | cmedqa2_external DC/NDCG | 冗余度(ft) |
|---|---|---|---|---|
| B0 | 0.8762/0.6413 | 0.9183/0.5338 | 0.9630/0.5166 | 0.5827 |
| MMR | 0.8768/0.6294 | 0.9310/0.5180 | 0.9589/0.5011 | 0.5278 |
| D3_TFIDF | 0.8745/0.6293 | 0.9216/0.5075 | 0.9730/0.4954 | 0.5478 |

## 4. MMR 与 D3 定位

覆盖维度：MMR 与 D3_TFIDF 的 DemandCov@5 差异（formal_train +0.0022、internal_blind +0.0094、external -0.0141）经配对 Bootstrap（10000 次、seed=42）与 Holm 校正后均无显著差异。排序质量维度：修复后的 qid 级配对 Bootstrap 显示 PRIMARY_NDCG 结果为 formal_train demand_cov p_Holm=1.0000；internal_blind demand_cov p_Holm=0.3654；cmedqa2_external demand_cov p_Holm=1.0000；formal_train ndcg_10 p_Holm=0.0796；internal_blind ndcg_10 p_Holm=0.0796；cmedqa2_external ndcg_10 p_Holm=0.0066（显著）。本素材不主张 D3 或 MMR 任一方法整体领先；覆盖维度两者表现接近，需求标签与一般多样化的可区分覆盖收益未被检出。

## 5. Top-K 敏感性设置

仅改变最终选择预算 K∈{3,5,7}；候选池、Q1/E2 预测、Version B 权重（0.1/0.2/0.2/0.05）、阈值 0.5、reranker 分数、MMR λ 均不变。跨 K 比较以 DemandCov@K、NDCG@K 为主指标；official NDCG@10 仅用于与原 K=5 口径兼容。

## 6. Top-K 结果

三个划分上所有方法的 DemandCov@K 随 K 单调上升（formal_train：B0 0.8114→0.8763→0.9113，MMR 0.8303→0.8768→0.9216，D3_TFIDF 0.8274→0.8745→0.9016）。方法相对排序跨 K 方向一致（主导方法不变、最大排名位移≤1），判定 DIRECTIONALLY_STABLE（描述性）。注意：official NDCG@10 随 K 上升仅因可见位置增多（固定 NDCG@10 受返回列表长度影响），不解释为排序质量改善。

## 7. D01-D06 类别变化

D01–D06 为本任务操作性信息需求分类，不是 ICD 或 SNOMED CT 临床术语本体。formal_train 上 B0 随 K 增加（K3→K7）覆盖率增幅最大的类别为 D05_care_emergency（Δ=+0.237）；K=3 时最易遗漏类别与 MMR-TFIDF 相对 B0 的提升类别明细见 tables/topk_demand_category_coverage.csv。

## 8. 讨论：多样性与需求覆盖的区别

MMR-TFIDF 通过显式降低候选内部相似度改变了证据组合（冗余度与平均相似度下降，unique demand 与 redundancy 均基于 6 类需求集合计算），但其 DemandCov@5 与 B0、D3_TFIDF 无显著差异，说明当前强 reranker 候选池中信息冗余空间有限：多样化重排序的收益主要表现为证据集合构成变化（平均替换 1.0–1.4 篇），而非可观测的覆盖增益。需求覆盖与一般多样性是相关但不等价的优化目标。

## 9. 讨论：K 值对结论外推的影响

三个 K 下方法相对排序与主要差值方向一致（描述性），支持「现象非 K=5 单点假象」；但证据预算 K 直接影响 DemandCov@K/NDCG@K 的量级与 official NDCG@10 的可见性，部署结论必须明确 K；K 不应被视为无关超参数。

## 10. 局限性新增内容

- MMR-TFIDF 为代理基线（dense embedding 未覆盖全部候选语料）；
- 低资源预测器（TF-IDF+LR）为诊断基线；D3-E2-RoBERTa 仅升级 E2，未构成强 Q1+E2 配置；
- λ 仅在 formal_dev（100 查询）选择；
- 覆盖与生成关系仅经 60 查询盲评初步验证。

## 11. 结语建议内容

强调无泄漏评测方案（Public/Private 隔离、B0–D3 诊断、泄漏注入验证）可用于任何证据选择系统的组件诊断；在医疗 RAG 案例中，需求感知选择与一般多样化选择在当前强 reranker 候选池上的覆盖表现接近；候选多样性、证据预算 K 与需求覆盖之间的权衡构成部署时需要显式管理的维度。

