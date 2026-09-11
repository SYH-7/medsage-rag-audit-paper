# Main-benchmark four-layer metrics (reviewer comment 3) — E1 results

Computed additively on TEMP copies of `benchmark_work_v5` case dirs with the frozen
adapters and frozen detector semantics (`run_selection` equivalence). 36/36 leak
positives reproduced the frozen ACCESS_LEAK/BEHAVIORAL_LEAK labels at K=5.
Frozen code and frozen case dirs were not modified.

Files: `main_four_layer_metrics_per_case.csv`, `main_four_layer_metrics_summary.csv`,
`main_four_layer_metrics.json`.

## Summary

| metric | ACCESS_LEAK (n=28) | BEHAVIORAL_LEAK (n=8) |
|---|---|---|
| frozen-label reproduction at K=5 | 28/28 | 8/8 |
| candidate scores changed when masking private value (mean fraction of evaluated docs) | 0.058 | 0.011 |
| mean absolute score delta (masked vs unmasked) | 0.079 | 0.032 |
| max absolute score delta | 5.0 | 5.0 |
| mean Kendall tau (full ranking, masked vs unmasked) | 1.000 | 0.994 |
| cases with Top-K set change at K=3 / 5 / 7 | 0 / 0 / 0 | 8 / 4 / 4 |
| cases with Top-K order change at K=3 / 5 / 7 | 0 / 0 / 0 | 8 / 8 / 8 |
| docs dropped from Top-K (masked) at K=3 / 5 / 7 | 0 / 0 / 0 | 20 / 16 / 12 |

## How this answers the reviewer

- Boundary violation (layer 1): runtime source–sink path exists for all 36 positives
  (frozen); Top-K comparison alone sees only 8.
- Retrieval perturbation (layer 2): for the 28 ACCESS cases, masking the private value
  changed candidate scores for 5.8% of evaluated documents (mean) with mean |Δscore|
  0.079, yet the full ranking (Kendall τ = 1.0) and Top-K at K in {3,5,7} were unchanged.
  The private value therefore reaches the scoring function and changes its numeric
  output without (in these samples) reordering the final list — i.e., the deployed
  decision does depend on non-deployable data even when the visible Top-K is stable.
- Evidence-selection change (layer 3): 8/8 BEHAVIORAL cases change order at every K;
  4/8 change the Top-K set at K=5 and 8/8 at K=3 (masked drops: 20 docs at K=3, 16 at K=5).
- Downstream answer change (layer 4): defined in the paper as generation-side score
  changes; not recomputed here (needs the frozen generation stack) — reported as a
  measurement protocol in the manuscript.

Suggested sentence for the response letter:
"In the main benchmark, masking the private value perturbed candidate scores in
5.8% of evaluated documents on average across the 28 ACCESS_LEAK cases while leaving
the full ranking (Kendall tau = 1.0) and Top-K at K = 3/5/7 unchanged, showing that
these cases do affect the deployed scoring function even though no Top-K change is
observed; the 8 BEHAVIORAL_LEAK cases reorder or replace documents at every tested K."
