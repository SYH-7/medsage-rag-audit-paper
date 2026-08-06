# Result Status

## Status legend

- **REPRODUCED** - recalculated / verified inside this package.
- **VERIFIED_FROM_RELEASE** - taken from the previously verified release bundle and re-checked.
- **REQUIRES_LOCAL_ORIGINAL_PROJECT** - requires the local original projects / corpora
  (`medsage_rag_full` / `tcm_sleep_rag_full`) and environment variables
  (`TCM_SLEEP_RAG_ROOT`, `MEDSAGE_RAG_ROOT`).

## Main project (v5.1.1) - `results/01_main_audit/`

| Group | Status |
|---|---|
| detection / localization / runtime / behavior / unseen / quality reports | REPRODUCED |
| gold reports (coverage, hash, source map, normalization) | REPRODUCED |
| author tables TABLE_01..11 | REPRODUCED |
| cross-pipeline status | VERIFIED_FROM_RELEASE (status row) |

## Deployment diagnostics (v2 allowed subset) - `results/02_deployment_diagnostics/`

| Group | Status |
|---|---|
| verified_release_results (B0-D3 / MMR / Top-K / generation) | VERIFIED_FROM_RELEASE |
| provenance | VERIFIED_FROM_RELEASE |
| author tables TABLE_02/03/04/10/11/12/14/15 | VERIFIED_FROM_RELEASE |

> Excluded by policy: TABLE_05/06/07/08/09 (legacy leakage/ablation/runtime/injection) and
> `LEAKAGE_INJECTION_VERIFIED_SUMMARY.csv` (superseded by v5.1.1).

## Second project cross-pipeline (v6) - `results/03_cross_pipeline/`

| Group | Status |
|---|---|
| detection summary / confusion / failure cases / leak effects / runtime | REPRODUCED (from v6 bundle) |
| frozen manifest / second-pipeline baseline | VERIFIED_FROM_RELEASE |
| synthetic fixtures | REPRODUCED (fixture tests) |
| real-candidate end-to-end | REQUIRES_LOCAL_ORIGINAL_PROJECT (6 skipped) |

## Public archives

Public release attachments are generated from the frozen original archives by path redaction and
public directory reorganization; core results/config/statistics unchanged - see
`docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`.
