# Generation-Side Method Comparison (A/B merged ratings)

Mean of annotator A and B per condition. Note: higher is better for all dims except unsupported_claim and critical_risk_omission (where 0 = better).

| condition | n | faithfulness | relevance | completeness | unsupported_claim | risk_omission | overall_utility |
|-----------|---|--------------|------------|--------------|-------------------|---------------|-----------------|
| B0 | 60 | 1.93 | 2.00 | 1.88 | 0.05 | 0.02 | 1.81 |
| D0 | 60 | 1.95 | 2.00 | 1.86 | 0.03 | 0.02 | 1.82 |
| D3_TFIDF | 60 | 1.96 | 2.00 | 1.90 | 0.04 | 0.00 | 1.88 |
| D3_ROBERTA | 60 | 1.92 | 2.00 | 1.89 | 0.07 | 0.03 | 1.82 |
| **overall** | 240 | 1.94 | 2.00 | 1.88 | 0.05 | 0.02 | 1.83 |
