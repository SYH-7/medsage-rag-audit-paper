# Revision Evidence Mapping (paper claims -> repository artifacts)

This document maps every claim added in the **revision round** of the manuscript
(*Auditing Private-Label Leakage and Deployment Gaps in Medical RAG Evaluation*,
DSInS 2026, submission YANIMYKJEA) and in the response letter to the artifact that
backs it in this public repository.

Status legend (see `docs/RESULT_STATUS.md`): **REPRODUCED** = recomputed from the frozen
case directories with the frozen detectors; **VERIFIED_FROM_RELEASE** = taken from the
previously verified release bundle and re-checked; **REQUIRES_LOCAL_ORIGINAL_PROJECT** =
re-execution additionally needs the local original projects / corpora, which are not
published.

## 1. Path aliases (internal package paths quoted in the response letter)

The response letter quotes the *internal* package paths used while producing the
revision. In this repository the same material is published under the public layout:

| quoted in the response letter | public repository path |
|---|---|
| `scripts/review_metrics/<script>.py` | `scripts/review_metrics/<script>.py` (identical path) |
| `paper_package_dakd_v5_1/17_review_metrics/` | `results/04_revision_metrics/` |
| `paper_package_dakd_v6/16_cross_pipeline/` | `results/03_cross_pipeline/` |
| `paper_package_dakd_v5_1/` (main benchmark package) | `results/01_main_audit/` |
| `paper_package_dakd_v2/` (deployment diagnostics) | `results/02_deployment_diagnostics/` |

Internal frozen source versions (v5.1.1, v6, v2) appear only inside package READMEs and
provenance files; they are not part of the public file names
(`docs/PACKAGE_MAPPING.md`, `docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`).

## 2. Response-letter items (1)-(8)

| item | script | shipped artifact | key frozen numbers |
|---|---|---|---|
| (1) four-level metric quantification on the main benchmark | `scripts/review_metrics/run_main_four_layer_metrics.py` | `results/04_revision_metrics/main_four_layer_metrics_{per_case,summary}.csv`, `.json` | 36/36 positives reproduce the frozen ACCESS_LEAK/BEHAVIORAL_LEAK labels at K = 5 |
| (2) schema-overlap hard negative control | `scripts/review_metrics/run_schema_overlap_hardnegatives.py` | `results/04_revision_metrics/main_hard_negative_schema_overlap_{per_case,summary}.csv`, `.json` | 18 clean cases; runtime/invariance/schema/composite specificity 1.0; keyword specificity 0 |
| (3) cross-pipeline validation | `scripts/dakd_v6/run_tcm_sleep_cross_pipeline.py` | `results/03_cross_pipeline/` (confusion matrix, detection summary, failure cases, leak effects, runtime, `FROZEN_DETECTOR_MANIFEST.json`, fixtures) | 96 executed cases (36 positives + 60 clean): 36 TP / 60 TN / 0 FP / 0 FN; 25 ACCESS_LEAK / 11 BEHAVIORAL_LEAK |
| (4) unseen-mechanism operators on both pipelines | `scripts/review_metrics/run_new_leak_operators.py`, `run_cross_new_leak_operators.py` | `results/04_revision_metrics/new_operators_main_*`, `new_operators_cross_*` | 12 positives + 6 clean (main) and 12 positives + 4 clean (second pipeline): runtime taint and composite 12 TP / 0 FP each; `ast_static_dataflow` 12 TP; `schema_guard`/`invariance` do not fire |
| (5) retrieval-method independence | `scripts/review_metrics/run_retrieval_independence.py` | `results/04_revision_metrics/retrieval_independence_*` | dense-only and BM25-only sub-pools: runtime taint and composite 8 TP / 0 FP per method, clean specificity 1.0 |
| (6) dormant (configuration-gated) leakage | `scripts/review_metrics/run_latent_gate.py` | `results/04_revision_metrics/latent_gate_*` | dormant (gate off): runtime taint 0/3 vs composite 3/3; active (gate on): 3/3 both; clean 0 FP |
| (7) out-of-band boundary probes | `scripts/review_metrics/run_boundary_channels.py` | `results/04_revision_metrics/boundary_channels_*` | env-var and side-file smuggling: 0/3 for all data-flow components (keyword alarms on path tokens only) |
| (8) real-code sweep | `scripts/review_metrics/sweep_real_code.py` | `results/04_revision_metrics/real_code_sweep_{hits,summary}.csv`, `.json` | 41 gold/private-truth identifier sites, all OFFLINE (annotation/dataset/post-selection metric code, 11 files); 0 on deployable retrieval/selection/scoring paths |

## 3. Manuscript claims -> artifacts

| manuscript statement | artifact |
|---|---|
| Twelve controlled mutation operators (Table 1) and 30 ordinary + 30 hard clean controls | `results/01_main_audit/author_tables/TABLE_02_PATTERN_DESIGN.csv`, `TABLE_03_CLEAN_CONTROLS.csv` |
| Table 2 detection results (keyword 36/60, AST 0/36, schema 12/36, runtime 36/36, invariance 8/36, composite 36/36) | `results/01_main_audit/detection_results/DETECTION_SUMMARY.csv` (per-run: `DETECTION_PER_RUN.csv`, `FALSE_POSITIVES.csv`, `FALSE_NEGATIVES.csv`) |
| Localization ability (source/field/path exact 1.000; weaker sink/module/line) | `results/01_main_audit/author_tables/TABLE_07_LOCALIZATION.csv` |
| Table 3 runtime overhead (baseline 491.17 ms; +17.14 / +22.88 / +447.41 ms; composite 993.10 ms, 202.19%) | `results/01_main_audit/author_tables/TABLE_08A_OFFLINE_RUNTIME.csv`, `TABLE_08B_ONLINE_RUNTIME.csv` |
| 28 ACCESS_LEAK / 8 BEHAVIORAL_LEAK split and its quantification (5.8% of documents, mean |Δ| 0.079, max 5.0, Kendall τ = 1.0, Top-K set changes 8/8 at K = 3 and 4/8 at K = 5) | `results/04_revision_metrics/main_four_layer_metrics_*` and `results/01_main_audit/behavior/BEHAVIORAL_EFFECT_*.csv` |
| 18 schema-overlap clean cases (Section 3.3) | `results/04_revision_metrics/main_hard_negative_schema_overlap_*` |
| Cross-pipeline validation on the second project (Section 4.6) | `results/03_cross_pipeline/` |
| Four unseen operators added in the revision + retrieval-method independence (Section 4.6) | `results/04_revision_metrics/new_operators_main_*`, `new_operators_cross_*`, `retrieval_independence_*` |
| B0-D3 oracle-to-deployment diagnosis (Table 4), MMR baseline, Top-K sensitivity, generation blind review | `results/02_deployment_diagnostics/` |
| Discussion: composite audit covers dormant (not-yet-executed) leaks; out-of-band smuggling is outside the instrumented surface by construction | `results/04_revision_metrics/latent_gate_*`, `boundary_channels_*` |
| Limitations: no naturally occurring leak was found; controlled injection is the feasible ground-truth method | `results/04_revision_metrics/real_code_sweep_*` |
| Source-transform-sink policy, contracts and detector semantics (Sections 3.1-3.2) | `src/benchmark_v3/contracts.py`, `taint.py`, `isolated_runner.py`, `static_dataflow_detector.py`, `source_sink_policy.py`; `configs/dakd_v5/source_sink_policy.yaml`, `configs/dakd_v5/full_audit_frozen.yaml` |
| Reproducibility labels: controlled leakage detection, runtime overhead, software tests and the second-pipeline BM25 validation are REPRODUCED; B0-D3 / MMR / Top-K / generation are VERIFIED_FROM_RELEASE | `docs/RESULT_STATUS.md`, `results/02_deployment_diagnostics/verified_release_results/RELEASE_VERIFICATION_REPORT.md` |
| Artifact availability statement: an anonymized review package with public schemas, detector inputs, mutation descriptions, scripts, environment notes and hashes | `release_assets/medleakaudit_01_main_audit.zip`, `release_assets/medleakaudit_02_deployment_diagnostics.zip` (+ `03` cross-pipeline), `SHA256SUMS.txt`, `docs/REPRODUCIBILITY.md`, `docs/PACKAGE_MAPPING.md` |

## 4. How to check the numbers without private data

```bash
python -m pytest tests/revision -q     # claim-consistency tests over results/04_revision_metrics/
python -m pytest tests -q              # full public suite
```

The consistency tests read only `results/04_revision_metrics/` and assert the exact
figures quoted above (TP/FP/specificity per detector, ACCESS/BEHAVIORAL split, latent
gate behaviour, boundary probes, sweep classification). Re-executing the experiments
themselves needs the local original projects and is reported as
`REQUIRES_LOCAL_ORIGINAL_PROJECT`.

## 5. Publication boundary

Published here: frozen sanitized results, detector source, configs, scripts, synthetic
fixtures, hashes and this mapping. Not published: raw medical questions/answers,
complete candidate documents, plaintext QueryGold/EvidenceGold, annotator sheets, model
weights, credentials, and the two original projects. The release attachments
(`v2.0.5-paper-support`) are unchanged and their SHA-256 values still match
`SHA256SUMS.txt`; the revision-round evidence is distributed repository-side under
`results/04_revision_metrics/`.
