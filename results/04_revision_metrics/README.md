# results/04_revision_metrics/ — revision-round evidence (E1–E7)

Frozen outputs of the revision-round experiments that back the claims added to the
manuscript and to the response letter. Every file here has status **REPRODUCED**
(recomputed from the frozen case directories with the frozen detectors; see
`docs/RESULT_STATUS.md`).

Scripts: [`scripts/review_metrics/`](../../scripts/review_metrics/).
Claim-by-claim mapping: [`docs/REVISION_EVIDENCE_MAPPING.md`](../../docs/REVISION_EVIDENCE_MAPPING.md).

| file | content |
|---|---|
| `main_four_layer_metrics_{per_case,summary}.csv`, `.json` | E1 — four separated outcome metrics on the main benchmark (36 positives, labels reproduced 36/36 at K = 5) |
| `main_hard_negative_schema_overlap_{per_case,summary}.csv`, `.json` | E2 — 18 fresh public-only clean cases whose field names mimic private artifacts (name-level overlap) |
| `new_operators_main_{per_case,summary}.csv`, `.json` | E3 — four operators absent from the frozen twelve, on the main pool (12 positives + 6 clean) |
| `new_operators_cross_{per_case,summary}.csv`, `.json` | E3 — the same four operators on the second pipeline over its real BM25 candidates (12 positives + 4 clean) |
| `retrieval_independence_{per_case,summary}.csv`, `.json` | E4 — the same operators on dense-only and BM25-only sub-pools of the same pool (8 positives + 2 clean per method) |
| `latent_gate_{per_case,summary}.csv`, `.json` | E5 — dormant (configuration-gated) private read: executed-path runtime taint vs composite audit |
| `boundary_channels_{per_case,summary}.csv`, `.json` | E6 — out-of-band smuggling probes (environment variable, raw side-file I/O) that bypass the instrumented read surface |
| `real_code_sweep_{hits,summary}.csv`, `.json` | E7 — identifier-level sweep of both real codebases for gold/private-truth reads, classified by module role |
| `README_E1_four_layer.md`, `README_E2_hard_negatives.md`, `README_E3_new_operators.md`, `README_E4_E7.md` | per-experiment notes written during the runs |

## Headline numbers (as claimed in the paper)

- **E1** — 36/36 positives reproduced the frozen ACCESS_LEAK/BEHAVIORAL_LEAK labels at K = 5;
  28 ACCESS_LEAK cases changed scores for 5.8% of evaluated documents on average (mean |Δ| = 0.079,
  max = 5.0) with the full ranking unchanged (Kendall τ = 1.0) and identical Top-K at K = 3/5/7;
  the 8 BEHAVIORAL_LEAK cases reordered documents at every K and changed the Top-K set in 8/8 cases
  at K = 3 and 4/8 at K = 5.
- **E2** — 18 clean cases: runtime taint, invariance, schema and the composite audit 0 FP
  (specificity 1.0); keyword baseline 18 FP (specificity 0).
- **E3** — runtime taint and composite audit 12 TP / 0 FP in **both** pipelines; `ast_static_dataflow`
  also 12 TP; `schema_guard` and `invariance` do not fire (the handles never enter the public
  candidate schema and all cases are ACCESS-class under masking).
- **E4** — dense-only and BM25-only sub-pools: runtime taint and composite audit 8 TP / 0 FP per
  method with clean specificity 1.0 (detection does not depend on the retrieval method).
- **E5** — dormant gate off: runtime taint 0/3 while the static component and therefore the
  composite audit detect 3/3 (the composite adds coverage of not-yet-executed code); gate on: both
  3/3; clean controls 0 FP.
- **E6** — out-of-band smuggling (env var, side file) fires none of the data-flow components (0/3);
  only the name-based keyword baseline alarms on path tokens. These channels bypass the instrumented
  read surface and are outside the declared coverage by construction (deployment-hygiene item).
- **E7** — 41 gold/private-truth identifier read sites in the main project, all in offline
  annotation/dataset/post-selection metric code (11 files); 0 sites on deployable
  retrieval/selection/scoring paths in either project.

## Scope notes

- Case seeds/ids, per-case detector verdicts and summary statistics are included; raw medical text,
  complete candidate documents and plaintext gold labels are not (`docs/DATA_AVAILABILITY.md`).
- Local execution logs (`RUN_LOG_*.txt`) are **not** shipped; the scripts print the same information
  and are listed in `scripts/review_metrics/README.md`.
- The internal package paths quoted in the response letter
  (`paper_package_dakd_v5_1/17_review_metrics/`, `paper_package_dakd_v6/16_cross_pipeline/`)
  correspond to `results/04_revision_metrics/` and `results/03_cross_pipeline/` respectively; see the
  mapping table in `docs/REVISION_EVIDENCE_MAPPING.md`.
