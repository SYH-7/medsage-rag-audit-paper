# MMR 显著性检验报告（fixed：qid 级配对重采样）

## 方法

- diff = a − b；对同一组 qid 索引 idx 重采样 mean(diff[idx])，10000 次，seed=42，percentile 95% CI；
- 每个 family 内 Holm 校正；
- p>0.05 表述为「当前样本中未检测到经多重校正后的稳定差异」，不作等效结论。

## 结果

| family | split | metric | A vs B | n | diff | 95% CI | p_raw | p_Holm | sig(Holm) |
|---|---|---|---|---|---|---|---|---|---|
| PRIMARY_DC | formal_train | demand_cov | MMR vs B0 | 200 | 0.000500 | [-0.022752, 0.022417] | 0.948705 | 1.000000 | NO |
| PRIMARY_DC | internal_blind | demand_cov | MMR vs B0 | 200 | 0.012750 | [-0.003083, 0.029833] | 0.121788 | 0.365363 | NO |
| PRIMARY_DC | cmedqa2_external | demand_cov | MMR vs B0 | 142 | -0.004108 | [-0.018192, 0.008803] | 0.587941 | 1.000000 | NO |
| PRIMARY_NDCG | formal_train | ndcg_10 | MMR vs B0 | 200 | -0.011915 | [-0.023778, -0.000050] | 0.048995 | 0.079592 | NO |
| PRIMARY_NDCG | internal_blind | ndcg_10 | MMR vs B0 | 200 | -0.015829 | [-0.031492, -0.000776] | 0.039796 | 0.079592 | NO |
| PRIMARY_NDCG | cmedqa2_external | ndcg_10 | MMR vs B0 | 142 | -0.015457 | [-0.025778, -0.005465] | 0.002200 | 0.006599 | YES |
| DIAGNOSTIC_DC | formal_train | demand_cov | MMR vs D3_TFIDF | 200 | 0.002250 | [-0.020750, 0.025750] | 0.848715 | 0.848715 | NO |
| DIAGNOSTIC_DC | internal_blind | demand_cov | MMR vs D3_TFIDF | 200 | 0.009417 | [-0.008917, 0.029167] | 0.327967 | 0.655934 | NO |
| DIAGNOSTIC_DC | cmedqa2_external | demand_cov | MMR vs D3_TFIDF | 142 | -0.014085 | [-0.036385, 0.004695] | 0.169183 | 0.507549 | NO |
| DIAGNOSTIC_NDCG | formal_train | ndcg_10 | MMR vs D3_TFIDF | 200 | 0.000079 | [-0.012875, 0.013603] | 0.986301 | 1.000000 | NO |
| DIAGNOSTIC_NDCG | internal_blind | ndcg_10 | MMR vs D3_TFIDF | 200 | 0.010545 | [-0.007617, 0.028817] | 0.259374 | 0.778122 | NO |
| DIAGNOSTIC_NDCG | cmedqa2_external | ndcg_10 | MMR vs D3_TFIDF | 142 | 0.005686 | [-0.014018, 0.024892] | 0.544946 | 1.000000 | NO |
| SUPPLEMENTARY | formal_train | demand_cov | D3_TFIDF vs B0 | 200 | -0.001750 | [-0.020417, 0.014500] | 0.879912 | 1.000000 | NO |
| SUPPLEMENTARY | formal_train | ndcg_10 | D3_TFIDF vs B0 | 200 | -0.011994 | [-0.021109, -0.003715] | 0.004400 | 0.021998 | YES |
| SUPPLEMENTARY | internal_blind | demand_cov | D3_TFIDF vs B0 | 200 | 0.003333 | [-0.012669, 0.019500] | 0.659934 | 1.000000 | NO |
| SUPPLEMENTARY | internal_blind | ndcg_10 | D3_TFIDF vs B0 | 200 | -0.026374 | [-0.043824, -0.009397] | 0.003400 | 0.020398 | YES |
| SUPPLEMENTARY | cmedqa2_external | demand_cov | D3_TFIDF vs B0 | 142 | 0.009977 | [-0.007042, 0.031103] | 0.309169 | 0.927507 | NO |
| SUPPLEMENTARY | cmedqa2_external | ndcg_10 | D3_TFIDF vs B0 | 142 | -0.021143 | [-0.040527, -0.001352] | 0.036196 | 0.144786 | NO |
