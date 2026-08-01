# Top-K 敏感性报告（fixed：DemandCov@K / NDCG@K 为主口径）

## 方法

- 仅改变 K∈{3,5,7}；候选池、Q1/E2 预测、Version B 权重、阈值、reranker、MMR λ 均不变；
- **跨 K 比较以 DemandCov@K、NDCG@K 为主指标**；
- **official NDCG@10 仅用于与原 K=5 口径兼容，不得将其随 K 增加的机械上升解释为排序质量改善**；
- 差值以 K=5 为参照；qid 级配对 Bootstrap（10000 次，seed=42，percentile 95% CI）仅用于描述；
- 稳定性判定为描述性，不设显著性门槛、不筛选结果。

## 稳定性判定（描述性，基于 DemandCov@K 与 NDCG@K 的方法相对排序）

### formal_train
- 方法 DemandCov@K 排序（K=3/5/7）：['MMR', 'D3_TFIDF', 'B0'] / ['MMR', 'B0', 'D3_TFIDF'] / ['MMR', 'B0', 'D3_TFIDF']
- 主导方法跨 K 一致：True；最大排名位移=1
- 判定：**DIRECTIONALLY_STABLE**（描述性）

### internal_blind
- 方法 DemandCov@K 排序（K=3/5/7）：['MMR', 'B0', 'D3_TFIDF'] / ['MMR', 'D3_TFIDF', 'B0'] / ['MMR', 'D3_TFIDF', 'B0']
- 主导方法跨 K 一致：True；最大排名位移=1
- 判定：**DIRECTIONALLY_STABLE**（描述性）

### cmedqa2_external
- 方法 DemandCov@K 排序（K=3/5/7）：['D3_TFIDF', 'B0', 'MMR'] / ['D3_TFIDF', 'B0', 'MMR'] / ['D3_TFIDF', 'MMR', 'B0']
- 主导方法跨 K 一致：True；最大排名位移=1
- 判定：**DIRECTIONALLY_STABLE**（描述性）


## 说明

- DemandCov@K、NDCG@K 随 K 的上升体现预算扩展本身；官方 NDCG@10 的上升仅因可见位置增多，不作为排序质量改善证据；
- 固定 NDCG@10 受返回列表长度影响，跨 K 稳健性主要依据 DemandCov@K、NDCG@K 及方法相对排序。
- 「DIRECTIONALLY_STABLE」不等价于统计显著或方法等效。
