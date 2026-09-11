# scripts/review_metrics/ — revision-round evidence scripts (E1–E7)

Scripts used for the revision round of the paper. Each one is additive: it writes
new case directories under a `benchmark_work_*` folder (git-ignored) and result
files into an output directory, and never modifies the frozen detector code, the
frozen case directories, or the frozen result packages.

Frozen outputs produced by these scripts are shipped in
[`results/04_revision_metrics/`](../../results/04_revision_metrics/) so that every
number claimed in the manuscript and the response letter can be checked without the
private data. See [`docs/REVISION_EVIDENCE_MAPPING.md`](../../docs/REVISION_EVIDENCE_MAPPING.md)
for the claim-by-claim mapping.

| script | experiment | ships as |
|---|---|---|
| `run_main_four_layer_metrics.py` | E1 four outcome metrics on the main benchmark (36 positives) | `main_four_layer_metrics_*` |
| `run_schema_overlap_hardnegatives.py` | E2 schema-overlap hard negative controls (18 clean) | `main_hard_negative_schema_overlap_*` |
| `run_new_leak_operators.py` | E3 four unseen operators on the main pool (12 positives + 6 clean) | `new_operators_main_*` |
| `run_cross_new_leak_operators.py` | E3 four unseen operators on the second pipeline (12 positives + 4 clean) | `new_operators_cross_*` |
| `run_retrieval_independence.py` | E4 unseen operators on dense-only and BM25-only sub-pools (8 positives + 2 clean each) | `retrieval_independence_*` |
| `run_latent_gate.py` | E5 dormant (configuration-gated) leakage: composite vs runtime | `latent_gate_*` |
| `run_boundary_channels.py` | E6 out-of-band channel probes (env var / side file) | `boundary_channels_*` |
| `sweep_real_code.py` | E7 identifier sweep of both real codebases for gold reads | `real_code_sweep_*` |

## Environment variables

| variable | meaning | used by |
|---|---|---|
| `MEDSAGE_FORMAL_TRAIN_POOL` | path to `formal_train_candidates.jsonl` (public candidate pool, **not distributed**) | E3, E4, E5, E6 |
| `MEDSAGE_V5_CASES` | frozen main-benchmark case dirs (`benchmark_work_v5`) | E1 |
| `MEDSAGE_REVIEW_HN` | case dir for the schema-overlap controls | E2 |
| `MEDSAGE_CROSS_CASES` | frozen second-pipeline case dirs (`benchmark_work_cross`) | E3 cross |
| `MEDSAGE_RAG_ROOT` | root of the main project (for `src/medsage`) | E7 |
| `TCM_SLEEP_RAG_ROOT` | root of the second project (for `rag_service`) | E7 |
| `REVIEW_METRICS_OUT` | output directory (default: `paper_package_dakd_v5_1/17_review_metrics`) | all |

```bash
export MEDSAGE_FORMAL_TRAIN_POOL=/path/to/formal_train_candidates.jsonl
export MEDSAGE_V5_CASES=/path/to/benchmark_work_v5
export MEDSAGE_CROSS_CASES=/path/to/benchmark_work_cross
export MEDSAGE_RAG_ROOT=/path/to/main_project
export TCM_SLEEP_RAG_ROOT=/path/to/second_project
export REVIEW_METRICS_OUT=results/04_revision_metrics

python scripts/review_metrics/run_main_four_layer_metrics.py
```

## Behaviour without the local projects

Raw medical text, complete candidate documents, the private gold labels and the two
original projects are **not** published (see [`docs/DATA_AVAILABILITY.md`](../../docs/DATA_AVAILABILITY.md)).
When a required input is missing, a script prints

```
REQUIRES_LOCAL_ORIGINAL_PROJECT: missing local input(s): ...
```

and exits with status 0 **without writing anything**, so the frozen outputs in
`results/04_revision_metrics/` are never overwritten by an empty run. This mirrors
the `REQUIRES_LOCAL_ORIGINAL_PROJECT` status used by the existing test suite
(`docs/RESULT_STATUS.md`).

`run_schema_overlap_hardnegatives.py` needs no private input: it constructs its own
public-only cases.

## Reproducing the shipped numbers

The shipped files are the frozen outputs of the runs reported in the paper. The
consistency of those files with the claims in the manuscript is enforced by
`tests/revision/test_revision_evidence_consistency.py` (no private data required):

```bash
python -m pytest tests/revision -q
```
