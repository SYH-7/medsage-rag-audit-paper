# 生成端统计唯一正式冻结报告 (v3)

**Status: COMPLETE_FINAL_FREEZE**

## 1. 方法说明

- 0/1/2 指标主检验：**exact sign test**（排除零差）；Wilcoxon 仅作 sensitivity（zero_method='wilcox'，零差排除，正态近似）。
- 0/1 指标主检验：**McNemar exact test**（二项双侧）。
- Bootstrap：qid 级配对，10000 次，seed=42，**percentile 95% CI**（无 BCa）。
- 效应量：0/1/2 指标 = Cohen's dz；0/1 指标 = 配对比例差。
- **raw p 每家族只校正一次**：PRIMARY（D3_ROBERTA_vs_B0×5 指标）= 5 项；DIAGNOSTIC（4 比较×5 指标）= 20 项；各自 Holm 校正。
- answer_relevance 全部为 2 → CEILING_EFFECT，不进入检验。

## 2. 焦点结果验证（D3_TFIDF vs B0 · overall_utility）

- n_total=60, n_positive=8, n_negative=1, n_zero=51
- mean_difference=0.1166667, percentile_ci=[0.0333333, 0.2166667]
- exact_sign_raw_p=0.0390625 → 焦点复现通过。

## 3. 方法汇总

| condition | n | faithfulness | demand_completeness | overall_utility | unsupported_claim | critical_risk_omission |
|---|---|---|---|---|---|---|
| B0 | 60 | 1.916667 | 1.816667 | 1.733333 | 0.033333 | 0.016667 |
| D0 | 60 | 1.933333 | 1.8 | 1.766667 | 0.033333 | 0.016667 |
| D3_TFIDF | 60 | 1.966667 | 1.866667 | 1.85 | 0.033333 | 0.0 |
| D3_ROBERTA | 60 | 1.9 | 1.85 | 1.766667 | 0.083333 | 0.033333 |

## 4. 配对统计（Holm 后显著项）

| comparison | metric | mean_diff | pct_ci | primary | raw_p | holm_p | es | conclusion |
|---|---|---|---|---|---|---|---|---|
| D3_ROBERTA_vs_B0 | faithfulness | -0.0167 | [-0.1, 0.066667] | exact_sign_test | 1.0000 | 1.0000 | -0.048444 | not_significant |
| D3_ROBERTA_vs_B0 | demand_completeness | +0.0333 | [-0.033333, 0.1] | exact_sign_test | 0.6250 | 1.0000 | 0.129099 | not_significant |
| D3_ROBERTA_vs_B0 | overall_utility | +0.0333 | [-0.050417, 0.133333] | exact_sign_test | 0.7266 | 1.0000 | 0.090903 | not_significant |
| D3_ROBERTA_vs_B0 | unsupported_claim | +0.0500 | [-0.016667, 0.133333] | mcnemar_exact | 0.3750 | 1.0000 | 0.05 | not_significant |
| D3_ROBERTA_vs_B0 | critical_risk_omission | +0.0167 | [-0.033333, 0.066667] | mcnemar_exact | 1.0000 | 1.0000 | 0.016667 | not_significant |
| D0_vs_B0 | faithfulness | +0.0167 | [-0.05, 0.083333] | exact_sign_test | 1.0000 | 1.0000 | 0.057348 | not_significant |
| D0_vs_B0 | demand_completeness | -0.0167 | [-0.083333, 0.05] | exact_sign_test | 1.0000 | 1.0000 | -0.057348 | not_significant |
| D0_vs_B0 | overall_utility | +0.0333 | [-0.05, 0.116667] | exact_sign_test | 0.6875 | 1.0000 | 0.105113 | not_significant |
| D0_vs_B0 | unsupported_claim | +0.0000 | [-0.05, 0.05] | mcnemar_exact | 1.0000 | 1.0000 | 0.0 | not_significant |
| D0_vs_B0 | critical_risk_omission | +0.0000 | [0.0, 0.0] | mcnemar_exact | 1.0000 | 1.0000 | 0.0 | not_significant |
| D3_TFIDF_vs_B0 | faithfulness | +0.0500 | [-0.016667, 0.116667] | exact_sign_test | 0.3750 | 1.0000 | 0.174391 | not_significant |
| D3_TFIDF_vs_B0 | demand_completeness | +0.0500 | [0.0, 0.116667] | exact_sign_test | 0.2500 | 1.0000 | 0.227496 | not_significant |
| D3_TFIDF_vs_B0 | overall_utility | +0.1167 | [0.033333, 0.216667] | exact_sign_test | 0.0391 | 0.7812 | 0.313262 | not_significant |
| D3_TFIDF_vs_B0 | unsupported_claim | +0.0000 | [-0.05, 0.05] | mcnemar_exact | 1.0000 | 1.0000 | 0.0 | not_significant |
| D3_TFIDF_vs_B0 | critical_risk_omission | -0.0167 | [-0.05, 0.0] | mcnemar_exact | 1.0000 | 1.0000 | -0.016667 | not_significant |
| D3_ROBERTA_vs_D3_TFIDF | faithfulness | -0.0667 | [-0.133333, -0.016667] | exact_sign_test | 0.1250 | 1.0000 | -0.265025 | not_significant |
| D3_ROBERTA_vs_D3_TFIDF | demand_completeness | -0.0167 | [-0.083333, 0.05] | exact_sign_test | 1.0000 | 1.0000 | -0.057348 | not_significant |
| D3_ROBERTA_vs_D3_TFIDF | overall_utility | -0.0833 | [-0.166667, -0.016667] | exact_sign_test | 0.0625 | 1.0000 | -0.298988 | not_significant |
| D3_ROBERTA_vs_D3_TFIDF | unsupported_claim | +0.0500 | [0.0, 0.116667] | mcnemar_exact | 0.2500 | 1.0000 | 0.05 | not_significant |
| D3_ROBERTA_vs_D3_TFIDF | critical_risk_omission | +0.0333 | [0.0, 0.083333] | mcnemar_exact | 0.5000 | 1.0000 | 0.033333 | not_significant |
| D0_vs_D3_ROBERTA | faithfulness | +0.0333 | [-0.05, 0.116667] | exact_sign_test | 0.6875 | 1.0000 | 0.105113 | not_significant |
| D0_vs_D3_ROBERTA | demand_completeness | -0.0500 | [-0.133333, 0.016667] | exact_sign_test | 0.3750 | 1.0000 | -0.174391 | not_significant |
| D0_vs_D3_ROBERTA | overall_utility | +0.0000 | [-0.1, 0.083333] | exact_sign_test | 1.0000 | 1.0000 | 0.0 | not_significant |
| D0_vs_D3_ROBERTA | unsupported_claim | -0.0500 | [-0.116667, 0.0] | mcnemar_exact | 0.2500 | 1.0000 | -0.05 | not_significant |
| D0_vs_D3_ROBERTA | critical_risk_omission | -0.0167 | [-0.066667, 0.033333] | mcnemar_exact | 1.0000 | 1.0000 | -0.016667 | not_significant |

## 5. 合规

- 未修改人工标签；未重新生成回答；未使用 A/B 均值；严格 qid 配对（60/60）。
- 主结果不含 BCa；Wilcoxon 仅 sensitivity。
- 未执行 git push；未覆盖任何旧文件（本包输出到新目录 v3）。
