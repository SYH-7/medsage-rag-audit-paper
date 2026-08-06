# Reproducibility

## Environment

- Python 3.10+ (tests run under 3.13 locally). Dependencies: see `requirements.txt`
  (pytest, PyYAML; standard permissive licenses, referenced not bundled).
- Set environment variables before running second-project / deployment scripts:

  - `TCM_SLEEP_RAG_ROOT` : local root of the second project (`tcm_sleep_rag_full`).
  - `MEDSAGE_RAG_ROOT` : local root of the main project when needed.

## What can be reproduced without the local original projects

- Main-project audit recalculation and tests (`tests/dakd_v5`, `tests/dakd_v5_1`) against
  `results/01_main_audit/`.
- Second-project synthetic fixture tests (`tests/dakd_v6_fixture`) against `fixtures/cross_pipeline/`.
- Deployment-diagnostics verified results checks (`results/02_deployment_diagnostics/`).
- Repository-level integrity tests (`tests/test_comprehensive.py`).
- SHA-256 verification of all Release attachments (`SHA256SUMS.txt`).

## What requires the local original projects (`REQUIRES_LOCAL_ORIGINAL_PROJECT`)

- End-to-end re-execution of `scripts/dakd_v5/run_pipeline.py` and
  `scripts/dakd_v6/run_tcm_sleep_cross_pipeline.py` against the raw corpora.
- `tests/dakd_v6/test_tcm_sleep_cross_pipeline.py` real-candidate cases (6 skipped, not faked).

These tests are skipped (not failed and not faked) when the local projects are unavailable.

## Result status

- `REPRODUCED` / `VERIFIED_FROM_RELEASE` / `REQUIRES_LOCAL_ORIGINAL_PROJECT` - see
  `docs/RESULT_STATUS.md` and `docs/TEST_REPORT.md`.

## Public archives

Public archives are generated from the frozen original archives by path redaction and public
directory reorganization; core results/config/statistics are unchanged - see
`docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`.
