# RoBERTa Downstream Significance (qid-level paired bootstrap, 10000 iters, seed 42, Holm-corrected)

| split | comparison | diff | ci_low | ci_high | raw_p | holm_p | cohen_d | n |
|-------|------------|------|--------|---------|-------|--------|---------|---|
| formal_train | roberta_D2_vs_frozen_D2 | 0.012 | -0.002167 | 0.026583 | 0.09619 | 1.0 | 0.1166 | 200 |
| formal_train | roberta_D3_vs_frozen_D3 | 0.0085 | -0.006754 | 0.026 | 0.29577 | 1.0 | 0.0723 | 200 |
| formal_train | roberta_D3_vs_B0 | 0.00675 | -0.011 | 0.023167 | 0.421958 | 1.0 | 0.0553 | 200 |
| formal_train | roberta_D3_vs_bge_D3 | 0.01575 | -0.002917 | 0.033585 | 0.09859 | 1.0 | 0.1194 | 200 |
| internal_blind | roberta_D2_vs_frozen_D2 | 0.000333 | -0.019085 | 0.02025 | 0.979902 | 1.0 | 0.0023 | 200 |
| internal_blind | roberta_D3_vs_frozen_D3 | -0.003167 | -0.02025 | 0.014333 | 0.718328 | 1.0 | -0.0254 | 200 |
| internal_blind | roberta_D3_vs_B0 | 0.000167 | -0.011917 | 0.012 | 0.953705 | 1.0 | 0.0019 | 200 |
| internal_blind | roberta_D3_vs_bge_D3 | -0.00325 | -0.019833 | 0.01225 | 0.686931 | 1.0 | -0.0277 | 200 |
| cmedqa2_external | roberta_D2_vs_frozen_D2 | -0.012324 | -0.03169 | 0.002347 | 0.128187 | 1.0 | -0.119 | 142 |
| cmedqa2_external | roberta_D3_vs_frozen_D3 | -0.008803 | -0.028756 | 0.007629 | 0.374763 | 1.0 | -0.0785 | 142 |
| cmedqa2_external | roberta_D3_vs_B0 | 0.001174 | -0.007042 | 0.010563 | 0.678532 | 1.0 | 0.0232 | 142 |
| cmedqa2_external | roberta_D3_vs_bge_D3 | 0.010563 | -0.006455 | 0.028169 | 0.219778 | 1.0 | 0.1006 | 142 |
