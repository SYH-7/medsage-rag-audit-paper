# Unseen-mechanism mutation operators on both pipelines (reviewer comment 1) — E3 results

Four NEW leakage operators are added that are NOT among the frozen 12 (M1..M4, F1..F4,
R1..R4) and that do not violate the public input schema by construction (handles travel
through public features / runtime fallback config rather than extra candidate metadata
fields). Each operator x3 seeds = 12 positives per pipeline, plus 6 (main) / 4 (cross)
ordinary clean controls built from the same real candidate rows.

| operator | mechanism (all read the private handle and feed a deployment sink) |
|---|---|
| N1 | embedding-derived evidence: private evidence list projected into an embedding-style feature slot |
| N2 | cross-module serialization round-trip: handle leaves and re-enters via JSON encode/decode before the source read |
| N3 | hot config-swap fallback: configured public field is absent, runtime falls back to a feature route holding the handle |
| N4 | >=3-hop derived proxy: handle resolved through nested dict/list indirection before the source read |

Frozen detector code/policies, frozen case dirs and frozen results are untouched. New case
dirs are generated additively from the real `formal_train` candidate pool (main) and from
REAL TCM BM25 candidate rows of an existing frozen cross case dir (read-only source, new
dirs) under `benchmark_work_v5_review_newops` / `benchmark_work_cross_review_newops`.

Files: `new_operators_main_{per_case,summary}.csv/.json`, `new_operators_cross_{per_case,summary}.csv/.json`.

## Main pipeline (Path A) — 12 positives + 6 clean

| detector | TP | FP | recall | specificity |
|---|---|---|---|---|
| keyword_static_baseline | 12 | 6 | 1.0 | 0.0 |
| ast_static_dataflow | 12 | 0 | 1.0 | 1.0 |
| schema_guard | 0 | 0 | 0.0 | 1.0 |
| runtime_taint | 12 | 0 | 1.0 | 1.0 |
| invariance | 0 | 0 | 0.0 | 1.0 |
| full_audit (composite) | 12 | 0 | 1.0 | 1.0 |

## TCM cross pipeline (Path B, real BM25 candidates) — 12 positives + 4 clean

| detector | TP | FP | recall | specificity |
|---|---|---|---|---|
| keyword_static_baseline | 12 | 4 | 1.0 | 0.0 |
| ast_static_dataflow | 12 | 0 | 1.0 | 1.0 |
| schema_guard | 0 | 0 | 0.0 | 1.0 |
| runtime_taint | 12 | 0 | 1.0 | 1.0 |
| invariance | 0 | 0 | 0.0 | 1.0 |
| full_audit (composite) | 12 | 0 | 1.0 | 1.0 |

## Reading the table

- runtime_taint + full_audit catch ALL 12 unseen mechanisms in BOTH pipelines with
  zero false positives (specificity 1.0) — the runtime source–sink auditor generalises
  to mechanisms it was never trained/pattern-matched on.
- All 12 leaks are ACCESS-class under invariance (masking changes internal scores but
  not the Top-K in these samples), matching the E1 ACCESS/28 behaviour; runtime_taint
  still fires because the taint trace shows the private value reaching the sink.
- schema_guard TP=0 is expected and honest: the operators deliberately avoid extra
  public-schema fields, so a pure schema check cannot see them — exactly why the
  composite/runtime audit is needed.
- keyword_static_baseline keeps its known spec=0 (flags any adapter text such as the
  shared header), identical to its frozen-suite behaviour.
