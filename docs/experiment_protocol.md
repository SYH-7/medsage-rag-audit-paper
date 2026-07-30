# Experiment Protocol

## Conditions
- B0: Reranker baseline using only public reranker scores
- D0: Oracle query + Oracle evidence states (reference, NOT deployable)
- D1: Predicted query + Gold evidence states (QueryLoss = D0-D1)
- D2: Gold query + Predicted evidence states (EvidenceLoss = D0-D2)
- D3: Predicted query + Predicted evidence states (deployable)
- ExactMaxCoverage: Brute-force combinatorial upper bound

## Data Splits
- formal_train: Out-of-fold on training set
- internal_blind: Held-out internal validation
- cmedqa2_external: External cross-domain validation

## Metrics
- DemandCov@5: Fraction of query demands covered by selected documents
- NDCG@10: Normalized discounted cumulative gain at rank 10

## Leakage Injection
- query-only: Leak query state labels into selection
- evidence-only: Leak evidence state labels into selection
- joint: Leak both query and evidence labels
- Rates: 0, 0.05, 0.10, 0.25, 0.50, 0.75, 1.00 (50 seeds per intermediate rate)

## Significance
- Paired bootstrap (10000 iterations)
- Wilcoxon signed-rank test
- Holm-Bonferroni correction for multiple comparisons
