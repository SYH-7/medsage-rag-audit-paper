# Bootstrap Correction Note

## 修正内容

旧版本使用 `np.random.RandomState(seed).randint(0, n, n)` 分别对A和B两个方法独立抽取索引，
导致配对Bootstrap退化为独立双样本Bootstrap，p值系统性偏高。

新版本按 `qid_hash` 对每个查询关联各方法的结果，
一次Bootstrap中A和B使用完全相同的qid索引（共享索引），
严格遵循配对检验的统计原理。

## 影响

- **DemandCov和NDCG均值未改变**：均值计算不涉及Bootstrap。
- **Bootstrap p值普遍下降**：共享索引减少了抽样方差。

### D3相对B0（三个划分）

| 划分 | 旧p值（独立） | 新p值（配对） | 差异 |
|------|-------------|-------------|------|
| formal_train | 0.9279 | 0.8879 | 仍不显著 |
| internal_blind | 0.8527 | 0.6715 | 仍不显著 |
| cmedqa2_external | 0.5363 | 0.3264 | 仍不显著 |

**D3相对B0仍均不显著。**

### external的D0相对B0

| 旧p值（独立） | 新p值（配对） | 变化 |
|-------------|-------------|------|
| 0.1102 | 0.0016 | **从不显著变为显著** |

这是因为配对Bootstrap正确利用了cmedqa2_external中查询内D0和B0之间的相关性，
不再误将两组视为独立样本。

## 技术细节

- 每次Bootstrap从n个qid中有放回抽取n个索引
- A和B使用完全相同的索引集
- iterations=10000，seed=42
- 旧方法：`a[rng.randint(0, n, n)]` vs `b[rng.randint(0, n, n)]`（两个不同索引集）
- 新方法：共享 `idx = rng.randint(0, n, n)`，然后 `a[idx]` vs `b[idx]`
