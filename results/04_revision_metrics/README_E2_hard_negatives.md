# Schema-overlap hard negative controls (reviewer comment 4) — E2 results

18 fresh Clean cases built with the frozen-case layout, whose public metadata /
features are NAMED like private evaluation artifacts
(`state_cache`, `label_encoder`, `backup_ranker`, `gold_flag`, `gold_feature`,
`relevance_score`, `proxy_score`, `adjudicated_enc`, `cached_evidence`,
`human_label_enc`, `evidence_label_enc`) but whose values are entirely public.
Metadata keys mirror the frozen hard-clean skeleton so `schema_guard` semantics are
unchanged; artifact-like names are carried in `public_features`. One adapter variant
actually *uses* those public fields in scoring; the other variant ignores them.

Frozen detectors, additive run; no frozen code or frozen case dir modified.
Case dirs: `benchmark_work_v5_review_hn/`.

Summary (`main_hard_negative_schema_overlap_summary.csv`), n = 18:

| detector | FP | specificity |
|---|---|---|
| keyword_static_baseline | 18 | 0.0 |
| ast_static_dataflow | 0 | 1.0 |
| schema_guard | 0 | 1.0 |
| runtime_taint | 0 | 1.0 |
| invariance | 0 | 1.0 |
| full_audit (composite) | 0 | 1.0 |

Interpretation: under realistic name-level schema overlap, word/keyword-based
screening loses all specificity, while the taint-based detector and the composite
audit keep specificity 1.0 — field NAMES alone do not produce false alarms when
values come from the public side.

Suggested response-letter sentence:
"We added hard-negative controls whose metadata/feature names deliberately mimic
private evaluation artifacts (state_cache, label_encoder, gold_flag,
relevance_score, proxy_score, adjudicated_enc, cached_evidence) with values
entirely derived from public inputs. The keyword baseline false-alarms on all 18
(specificity 0), whereas runtime taint, invariance, schema, and the composite audit
keep zero false positives (specificity 1.0), showing that name-level similarity does
not break specificity of the taint-based boundary."
