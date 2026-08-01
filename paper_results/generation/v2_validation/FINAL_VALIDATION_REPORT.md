# FINAL VALIDATION REPORT — Paper Revision Final Validation v2

**Final status: COMPLETE**

## 1. 冻结结果差异来自哪里
- 逐qid核对 1626 行（B0/D2/D3 × 3 splits）。DC差异 26 行，选择集差异 399 行。
- formal_train（OOF）DC差异 0 行 —— 完全一致。
- 根因：R7测试集 `pred_e2` 无 empty→argmax fallback（空集编码），新运行统一应用了该 fallback。

## 2. 哪组结果可作为论文主结果
- **推荐使用 R7 冻结端点作为主结果**（B0/D0/D1/D2/D3），新运行 TF-IDF 测试集数值作为一致性附录说明。

## 3. Strong-E2 最终选择
- selection_split=formal_dev, metric=micro_f1
- 候选：{"tfidf": {"split": "formal_dev", "metric": "micro_f1", "micro_f1": 0.5145, "macro_f1": 0.3562, "sample_f1": 0.3784, "jaccard": 0.3192}, "bge": {"split": "formal_dev", "metric": "micro_f1", "micro_f1": 0.5527, "macro_f1": 0.4888, "sample_f1": 0.4076, "jaccard": 0.3429}, "roberta": {"split": "formal_dev", "metric": "micro_f1", "micro_f1": 0.6477, "macro_f1": 0.6287, "sample_f1": 0.4603, "jaccard": 0.4092}}
- **selected_model = roberta**

## 4. RoBERTa-D3 vs B0（qid配对Bootstrap 10000次, Holm校正）

| split | diff | ci_low | ci_high | raw_p | holm_p | cohen_d | n | 显著(α=0.05) |
|-------|------|--------|---------|-------|--------|---------|---|-------------|
| formal_train | 0.00675 | -0.011 | 0.023167 | 0.421958 | 1.0 | 0.0553 | 200 | 否 |
| internal_blind | 0.000167 | -0.011917 | 0.012 | 0.953705 | 1.0 | 0.0019 | 200 | 否 |
| cmedqa2_external | 0.001174 | -0.007042 | 0.010563 | 0.678532 | 1.0 | 0.0232 | 142 | 否 |

## 5. RoBERTa-D3 vs 原冻结D3

| split | diff | ci_low | ci_high | raw_p | holm_p | cohen_d | n | 显著(α=0.05) |
|-------|------|--------|---------|-------|--------|---------|---|-------------|
| formal_train | 0.0085 | -0.006754 | 0.026 | 0.29577 | 1.0 | 0.0723 | 200 | 否 |
| internal_blind | -0.003167 | -0.02025 | 0.014333 | 0.718328 | 1.0 | -0.0254 | 200 | 否 |
| cmedqa2_external | -0.008803 | -0.028756 | 0.007629 | 0.374763 | 1.0 | -0.0785 | 142 | 否 |

## 6. 强模型 EvidenceLoss vs QueryLoss

| split | model | D0 | D2_strong | EvidenceLoss | QueryLoss | EL>QL |
|-------|-------|----|-----------|--------------|-----------|-------|
| formal_train | bge | 0.9398 | 0.8764 | 0.0634 | 0.0179 | True |
| formal_train | roberta | 0.9398 | 0.8822 | 0.0577 | 0.0179 | True |
| internal_blind | bge | 0.9819 | 0.9239 | 0.058 | 0.0283 | True |
| internal_blind | roberta | 0.9819 | 0.9286 | 0.0533 | 0.0283 | True |
| cmedqa2_external | bge | 0.9859 | 0.9689 | 0.017 | 0.0023 | True |
| cmedqa2_external | roberta | 0.9859 | 0.9642 | 0.0217 | 0.0023 | True |

## 7. 生成了多少回答
- 规划 240 条（60 qids × 4 条件），实际生成 240 条。
- generated=True

## 8. 是否发生 API 失败
- 未调用 API（配置缺失）。api_failures: []

## 9. 是否访问测试集调参 → 否
## 10. 是否修改冻结结果 → 否
## 11. 是否执行 git push → 否

## 状态原因

