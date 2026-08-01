# GENERATION FINAL STATISTICS AUDIT

**Frozen status: see JSON**

## 1. 焦点核查：D3_TFIDF vs B0（overall_utility）

- n_qids = 60
- positive_count = 8（D3_TFIDF 更优）
- negative_count = 1（B0 更优）
- zero_count = 51
- mean_difference = 0.1167
- median_difference = 0.0
- standard_deviation = 0.3724

## 2. 统计方法说明

- Bootstrap：qid 级配对重采样，10000 次，seed=42；bootstrap CI **未做多重比较校正**。
- Wilcoxon signed-rank：**zero_method = 'wilcox'**（零差值被排除）；p 值由正态近似给出。
- BCa CI：偏差校正 z0 + 加速度 a（jackknife 估计）。
- sign test：精确二项双侧。
- Cohen's dz = mean(diff)/sd(diff)；rank-biserial = (W+ − W−)/(W+ + W−)（Kerby, 2014）。
- answer_relevance 所有条件均为 2（**CEILING_EFFECT**），不进入显著性检验。

## 3. Holm 校正

- Bootstrap p 家族：5 比较 × 5 指标 = **25** 个检验。
- Wilcoxon p 家族：5 比较 × 3（0/1/2 指标）= **15** 个检验。
- sign test p 家族：5 比较 × 3 = **15** 个检验。
- 三个家族分别独立 Holm 校正（不跨家族合并）。

## 4. 逐比较结果

| comparison | metric | n | mean_diff | pct CI | BCa CI | boot_p(holm) | wilcox_p(holm) | sign_p(holm) | dz | rb |
|---|---|---|---|---|---|---|---|---|---|---|
| D3_ROBERTA_vs_B0 | faithfulness | 60 | -0.0167 | [-0.1, 0.0667] | [-0.2, 0.1333] | 1.0 | 1.0 | 1.0 | -0.0484 | -0.1429 |
| D3_ROBERTA_vs_B0 | demand_completeness | 60 | +0.0333 | [-0.0333, 0.1] | [-0.1, 0.1833] | 1.0 | 1.0 | 1.0 | 0.1291 | 0.5 |
| D3_ROBERTA_vs_B0 | overall_utility | 60 | +0.0333 | [-0.0504, 0.1333] | [-0.15, 0.25] | 1.0 | 1.0 | 1.0 | 0.0909 | 0.25 |
| D3_ROBERTA_vs_B0 | unsupported_claim | 60 | +0.0500 | [-0.0167, 0.1333] | [-0.1, 0.2667] | 1.0 |  |  | 0.1744 | 0.6 |
| D3_ROBERTA_vs_B0 | critical_risk_omission | 60 | +0.0167 | [-0.0333, 0.0667] | [-0.1, 0.1667] | 1.0 |  |  | 0.0741 | 0.3333 |
| D0_vs_B0 | faithfulness | 60 | +0.0167 | [-0.05, 0.0833] | [-0.1167, 0.15] | 1.0 | 1.0 | 1.0 | 0.0573 | 0.2 |
| D0_vs_B0 | demand_completeness | 60 | -0.0167 | [-0.0833, 0.05] | [-0.1667, 0.1167] | 1.0 | 1.0 | 1.0 | -0.0573 | -0.2 |
| D0_vs_B0 | overall_utility | 60 | +0.0333 | [-0.05, 0.1167] | [-0.1167, 0.2] | 1.0 | 1.0 | 1.0 | 0.1051 | 0.3333 |
| D0_vs_B0 | unsupported_claim | 60 | +0.0000 | [-0.05, 0.05] | [-0.1167, 0.1167] | 1.0 |  |  | 0.0 | 0.0 |
| D0_vs_B0 | critical_risk_omission | 60 | +0.0000 | [0.0, 0.0] | [0.0, 0.0] | 1.0 |  |  |  |  |
| D3_TFIDF_vs_B0 | faithfulness | 60 | +0.0500 | [-0.0167, 0.1167] | [-0.0667, 0.2] | 1.0 | 1.0 | 1.0 | 0.1744 | 0.6 |
| D3_TFIDF_vs_B0 | demand_completeness | 60 | +0.0500 | [0.0, 0.1167] | [0.0, 0.1667] | 1.0 | 1.0 | 1.0 | 0.2275 | 1.0 |
| D3_TFIDF_vs_B0 | overall_utility | 60 | +0.1167 | [0.0333, 0.2167] | [-0.0667, 0.3] | 0.3216 | 0.57228 | 0.58593 | 0.3133 | 0.7778 |
| D3_TFIDF_vs_B0 | unsupported_claim | 60 | +0.0000 | [-0.05, 0.05] | [-0.1167, 0.1333] | 1.0 |  |  | 0.0 | 0.0 |
| D3_TFIDF_vs_B0 | critical_risk_omission | 60 | -0.0167 | [-0.05, 0.0] | [-0.1167, -0.0167] | 1.0 |  |  | -0.1291 | -1.0 |
| D3_ROBERTA_vs_D3_TFIDF | faithfulness | 60 | -0.0667 | [-0.1333, -0.0167] | [-0.2333, 0.0] | 0.7728 | 0.882557 | 1.0 | -0.265 | -1.0 |
| D3_ROBERTA_vs_D3_TFIDF | demand_completeness | 60 | -0.0167 | [-0.0833, 0.05] | [-0.1833, 0.1167] | 1.0 | 1.0 | 1.0 | -0.0573 | -0.2 |
| D3_ROBERTA_vs_D3_TFIDF | overall_utility | 60 | -0.0833 | [-0.1667, -0.0167] | [-0.2667, 0.0] | 0.225 | 0.603596 | 0.875 | -0.299 | -1.0 |
| D3_ROBERTA_vs_D3_TFIDF | unsupported_claim | 60 | +0.0500 | [0.0, 0.1167] | [0.0, 0.1833] | 1.0 |  |  | 0.2275 | 1.0 |
| D3_ROBERTA_vs_D3_TFIDF | critical_risk_omission | 60 | +0.0333 | [0.0, 0.0833] | [0.0, 0.1667] | 1.0 |  |  | 0.1841 | 1.0 |
| D0_vs_D3_ROBERTA | faithfulness | 60 | +0.0333 | [-0.05, 0.1167] | [-0.1167, 0.2333] | 1.0 | 1.0 | 1.0 | 0.1051 | 0.3333 |
| D0_vs_D3_ROBERTA | demand_completeness | 60 | -0.0500 | [-0.1333, 0.0167] | [-0.2167, 0.1] | 1.0 | 1.0 | 1.0 | -0.1744 | -0.6 |
| D0_vs_D3_ROBERTA | overall_utility | 60 | +0.0000 | [-0.1, 0.0833] | [-0.1833, 0.1833] | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| D0_vs_D3_ROBERTA | unsupported_claim | 60 | -0.0500 | [-0.1167, 0.0] | [-0.2167, 0.0] | 1.0 |  |  | -0.2275 | -1.0 |
| D0_vs_D3_ROBERTA | critical_risk_omission | 60 | -0.0167 | [-0.0667, 0.0333] | [-0.1667, 0.1] | 1.0 |  |  | -0.0741 | -0.3333 |

## 5. D3_TFIDF vs B0 utility 逐 qid（见 CSV）

## 6. 标签来源与合规
- 最终标签：A==B 共享；A≠B 使用 adjudicated 值；**未使用 A/B 平均值**。
- 未修改人工标签；未重新生成回答；未执行 git push。
- 严格配对：全部 60 qid 均含 4 条件。
