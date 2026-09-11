# E4-E7: retrieval independence, latent composite value, boundary probes, real-code sweep

Companion evidence for the revision. All runs are additive; frozen detectors,
frozen case dirs and frozen result packages are untouched. New case dirs live in
`benchmark_work_v5_review_method`, `benchmark_work_v5_review_latent`,
`benchmark_work_v5_review_boundary`.

Files: `retrieval_independence_{per_case,summary}.csv/.json`,
`latent_gate_{per_case,summary}.csv/.json`, `boundary_channels_{per_case,summary}.csv/.json`,
`real_code_sweep_{hits,summary}.csv` + `real_code_sweep.json`.

## E4 - detection does not depend on the retrieval method (addresses BM25-only scope)

The four unseen N-operators (N1 embedding-derived, N2 serialization round-trip,
N3 hot config-swap fallback, N4 3-hop proxy) were rebuilt on DENSE-ONLY and
BM25-ONLY candidate sub-pools of the real `formal_train` pool (rows restricted by
that method's real rank), 2 seeds x 4 operators = 8 positives per method + 2 clean.

| method | runtime_taint | ast_static_dataflow | schema_guard | invariance | full_audit |
|---|---|---|---|---|---|
| dense | 8 TP / 0 FP | 8 TP / 0 FP | 0 | 0 | 8 TP / 0 FP |
| bm25  | 8 TP / 0 FP | 8 TP / 0 FP | 0 | 0 | 8 TP / 0 FP |

Same detectors, same operators, same clean specificity (1.0) regardless of
whether the candidates were retrieved densely or with BM25. keyword keeps its
spec-0 baseline.

## E5 - composite audit adds value for dormant (config-gated) leaks

runtime_taint only sees EXECUTED paths. Identical adapter code whose private read
sits behind `config['latent_gold']`:

| group (n=3) | runtime_taint | ast_static_dataflow | schema_guard | invariance | full_audit |
|---|---|---|---|---|---|
| dormant (gate off) | 0/3 | 3/3 | 0/3 | 0/3 | 3/3 |
| active (gate on) | 3/3 | 3/3 | 0/3 | 0/3 | 3/3 |
| clean controls | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |

Composite = full_audit detects dormant leaks through its static component while
runtime alone misses them: composite is not redundant; it extends coverage to
not-yet-executed (e.g., flag-gated) code paths. All dormant/active are
ACCESS-class under masking.

## E6 - measured boundary: out-of-band smuggling is out of scope

Private doc lists are smuggled to the scoring sink through channels that bypass
the instrumented read surface (env var, raw side-cache file I/O). Every
surface-bound component is blind (0/3); keyword may fire only on name tokens in
paths (spec 0 by design). Conclusion is honest and by construction: the audit
covers flows through the instrumented surface; raw file/env smuggling must be
handled by deployment hygiene (whitelists, module isolation, dummy replacement),
which the paper recommends.

## E7 - real-code sweep (negative result, external validity)

Identifier-level sweep of both audited real codebases (`src/medsage` and the TCM
`rag_service`) for gold/private-truth reads: **41 read sites, all OFFLINE**
(annotation importers, dataset constructors, post-selection metrics); **0 read
sites in DEPLOY_PATH code** (retrieval/selection/scoring/state/api). No naturally
occurring leak exists in these contract-designed projects - exactly why controlled
injection is the feasible ground-truth method and why real-world prevalence needs
industry collaboration. This is written up as an external-validity threat in the
Discussion, not hidden in the Limitations list.
