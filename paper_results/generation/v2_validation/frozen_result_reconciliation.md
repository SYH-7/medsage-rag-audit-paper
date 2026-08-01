# Frozen Result Reconciliation — R7 TF-IDF vs New-Run TF-IDF

Reconciled qid-level across B0/D2/D3 for splits: formal_train, internal_blind, cmedqa2_external.

## Summary

| split | n_qids | n_dc_diff | n_selected_diff | B0 | D2 | D3 |
|-------|--------|-----------|-----------------|----|----|----|
| formal_train | 200 | 0 | 0 | 0/200 diff, max|Δ|=0.00000, sel_diff=0 | 0/200 diff, max|Δ|=0.00000, sel_diff=0 | 0/200 diff, max|Δ|=0.00000, sel_diff=0 |
| internal_blind | 200 | 23 | 224 | 0/200 diff, max|Δ|=0.00000, sel_diff=0 | 13/200 diff, max|Δ|=0.50000, sel_diff=103 | 10/200 diff, max|Δ|=0.50000, sel_diff=121 |
| cmedqa2_external | 142 | 3 | 175 | 0/142 diff, max|Δ|=0.00000, sel_diff=0 | 1/142 diff, max|Δ|=0.50000, sel_diff=83 | 2/142 diff, max|Δ|=0.50000, sel_diff=92 |

## Checks performed (all frozen config)

| Item | R7 value | New run value | Match |
|------|----------|---------------|-------|
| TF-IDF analyzer | char | char | OK |
| ngram_range | (2,4) | (2,4) | OK |
| min_df | 2 | 2 | OK |
| max_features | 50000 | 50000 | OK |
| sublinear_tf | True | True | OK |
| LR solver | liblinear | liblinear | OK |
| class_weight | balanced | balanced | OK |
| max_iter | 500 | 500 | OK |
| random_state | 42 | 42 | OK |
| threshold | 0.5 | 0.5 | OK |
| qid fold map | idx%5 over qid list order | identical loader | OK |
| selector | select_version_b / select_b0 | same frozen code | OK |
| TopK | 5 | 5 | OK |

## Root-cause of differences


1. **formal_train (OOF)**: B0/D2/D3 are identical between R7 and the new run
   (`max|ΔDC| <= 1e-9`), because both used the identical qid-level 5-fold OOF
   predictions with empty->argmax fallback.

2. **internal_blind / cmedqa2_external (full-model test)**: the new run applies the
   frozen `empty->argmax` fallback when producing E2 hard predictions
   (`hard_from_probs` in revision_v1/common.py), whereas the R7 test-set path
   (`pred_e2` in run_phase6b_r7.py) returned the EMPTY set for pairs where every
   class probability < 0.5. This changes a small number of D2/D3 selections and hence
   DemandCov on the test sets. The R7 formal_train OOF E2 path DID include the
   fallback (line 87 `or {L1[np.argmax(probs[j])]}`), which is why formal_train matches.

3. **B0** is unaffected (reranker-only, no E2 prediction) and matches exactly on all
   three splits.

The new-run numbers are therefore the CONSISTENT application of the frozen convention;
the R7 test-set E2 numbers used an undocumented empty-set encoding. Per the task rules,
we do NOT overwrite the R7 frozen results; we report both.


## Frozen endpoints (reference)

| split | B0 | D0 | D1 | D2 | D3 |
|-------|----|----|----|----|----|
| formal_train | 0.8762 | 0.9398 | 0.9219 | 0.8702 | 0.8745 |
| internal_blind | 0.9183 | 0.9819 | 0.9537 | 0.9282 | 0.9216 |
| cmedqa2_external | 0.9630 | 0.9859 | 0.9836 | 0.9765 | 0.9730 |

## New-run TF-IDF endpoints (v1 output)

| split | B0 | D2 | D3 |
|-------|----|----|----|
| formal_train | 0.8762 | 0.8702 | 0.8745 |
| internal_blind | 0.9183 | 0.9314 | 0.9231 |
| cmedqa2_external | 0.9630 | 0.9730 | 0.9730 |
