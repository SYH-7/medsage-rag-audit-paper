# GENERATION EVALUATION FINAL REPORT

**Status: COMPLETE_FINAL_GENERATION_EVALUATION**

## 1. Method summary (per condition, qid-level means)

| condition | n | faithfulness | relevance | completeness | overall_utility | unsupported_claim | risk_omission |
|---|--|---|---|---|---|---|---|
| B0 | 60 | 1.9167 | 2.0 | 1.8167 | 1.7333 | 0.0333 | 0.0167 |
| D0 | 60 | 1.9333 | 2.0 | 1.8 | 1.7667 | 0.0333 | 0.0167 |
| D3_TFIDF | 60 | 1.9667 | 2.0 | 1.8667 | 1.85 | 0.0333 | 0.0 |
| D3_ROBERTA | 60 | 1.9 | 2.0 | 1.85 | 1.7667 | 0.0833 | 0.0333 |

## 2. Pairwise significance (Holm-corrected)
| comparison | dimension | diff | ci95 | bootstrap_p(holm) | wilcoxon_p(holm) |
|---|---|---|---|---|---|
| D3_ROBERTA_vs_B0 | faithfulness | -0.0167 | [-0.1000, 0.0667] | 1.0 | 1.0 |
| D3_ROBERTA_vs_B0 | relevance | +0.0000 | [0.0000, 0.0000] | 1.0 | 1.0 |
| D3_ROBERTA_vs_B0 | completeness | +0.0333 | [-0.0333, 0.1000] | 1.0 | 1.0 |
| D3_ROBERTA_vs_B0 | overall_utility | +0.0333 | [-0.0504, 0.1333] | 1.0 | 1.0 |
| D3_ROBERTA_vs_B0 | unsupported_claim | +0.0500 | [-0.0167, 0.1333] | 1.0 |  |
| D3_ROBERTA_vs_B0 | risk_omission | +0.0167 | [-0.0333, 0.0667] | 1.0 |  |
| D0_vs_B0 | faithfulness | +0.0167 | [-0.0500, 0.0833] | 1.0 | 1.0 |
| D0_vs_B0 | relevance | +0.0000 | [0.0000, 0.0000] | 1.0 | 1.0 |
| D0_vs_B0 | completeness | -0.0167 | [-0.0833, 0.0500] | 1.0 | 1.0 |
| D0_vs_B0 | overall_utility | +0.0333 | [-0.0500, 0.1167] | 1.0 | 1.0 |
| D0_vs_B0 | unsupported_claim | +0.0000 | [-0.0500, 0.0500] | 1.0 |  |
| D0_vs_B0 | risk_omission | +0.0000 | [0.0000, 0.0000] | 1.0 |  |
| D3_TFIDF_vs_B0 | faithfulness | +0.0500 | [-0.0167, 0.1167] | 1.0 | 1.0 |
| D3_TFIDF_vs_B0 | relevance | +0.0000 | [0.0000, 0.0000] | 1.0 | 1.0 |
| D3_TFIDF_vs_B0 | completeness | +0.0500 | [0.0000, 0.1167] | 1.0 | 1.0 |
| D3_TFIDF_vs_B0 | overall_utility | +0.1167 | [0.0333, 0.2167] | 1.0 | 0.545 |
| D3_TFIDF_vs_B0 | unsupported_claim | +0.0000 | [-0.0500, 0.0500] | 1.0 |  |
| D3_TFIDF_vs_B0 | risk_omission | -0.0167 | [-0.0500, 0.0000] | 1.0 |  |
| D3_ROBERTA_vs_D3_TFIDF | faithfulness | -0.0667 | [-0.1333, -0.0167] | 1.0 | 1.0 |
| D3_ROBERTA_vs_D3_TFIDF | relevance | +0.0000 | [0.0000, 0.0000] | 1.0 | 1.0 |
| D3_ROBERTA_vs_D3_TFIDF | completeness | -0.0167 | [-0.0833, 0.0500] | 1.0 | 1.0 |
| D3_ROBERTA_vs_D3_TFIDF | overall_utility | -0.0833 | [-0.1667, -0.0167] | 1.0 | 1.0 |
| D3_ROBERTA_vs_D3_TFIDF | unsupported_claim | +0.0500 | [0.0000, 0.1167] | 1.0 |  |
| D3_ROBERTA_vs_D3_TFIDF | risk_omission | +0.0333 | [0.0000, 0.0833] | 1.0 |  |
| D0_vs_D3_ROBERTA | faithfulness | +0.0333 | [-0.0500, 0.1167] | 1.0 | 1.0 |
| D0_vs_D3_ROBERTA | relevance | +0.0000 | [0.0000, 0.0000] | 1.0 | 1.0 |
| D0_vs_D3_ROBERTA | completeness | -0.0500 | [-0.1333, 0.0167] | 1.0 | 1.0 |
| D0_vs_D3_ROBERTA | overall_utility | +0.0000 | [-0.1000, 0.0833] | 1.0 | 1.0 |
| D0_vs_D3_ROBERTA | unsupported_claim | -0.0500 | [-0.1167, 0.0000] | 1.0 |  |
| D0_vs_D3_ROBERTA | risk_omission | -0.0167 | [-0.0667, 0.0333] | 1.0 |  |

## 3. Notes
- Final label priority: A==B shared score; A!=B adjudicated; no averaging.
- Bootstrap: 10000 iterations, seed=42, paired qid-level.
- Independence confirmed via annotator_independence_declaration_FILLED.md.
