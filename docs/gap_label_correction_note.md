# Gap Label Correction Note

## Original gap_decomposition.csv column names
| Old Column | Paper Definition | Correct Meaning |
|-----------|-----------------|-----------------|
| query_loss | D0 - D1 | QueryLoss (D1 = Predicted Query + Gold Evidence) |
| evidence_loss | D0 - D2 | EvidenceLoss (D2 = Gold Query + Predicted Evidence) |
| interaction_loss | D1 + D2 - D0 - D3 | Correct |
| oracle_gain | D0 - B0 | OracleGain |

The mislabeling was a column name swap in the original data. Values are unchanged.
