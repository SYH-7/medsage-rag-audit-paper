# MMR lambda=1 端点验证（fixed：显式 tie-break）

## 状态：**ALL_PASS**

| split | K | total | identical | different | pass |
|---|---|---|---|---|---|
| formal_dev | 3 | 100 | 100 | 0 | ✅ |
| formal_dev | 5 | 100 | 100 | 0 | ✅ |
| formal_dev | 7 | 100 | 100 | 0 | ✅ |
| formal_train | 3 | 200 | 200 | 0 | ✅ |
| formal_train | 5 | 200 | 200 | 0 | ✅ |
| formal_train | 7 | 200 | 200 | 0 | ✅ |
| internal_blind | 3 | 200 | 200 | 0 | ✅ |
| internal_blind | 5 | 200 | 200 | 0 | ✅ |
| internal_blind | 7 | 200 | 200 | 0 | ✅ |
| cmedqa2_external | 3 | 142 | 142 | 0 | ✅ |
| cmedqa2_external | 5 | 142 | 142 | 0 | ✅ |
| cmedqa2_external | 7 | 142 | 142 | 0 | ✅ |

## 结论
- λ=1 全部通过 → 显式 tie-break 正确，允许继续 MMR 主实验；若失败停止主结果输出。
