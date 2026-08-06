# PUBLIC_ARCHIVE_DIFF_REPORT

Per-file differences between the **public (redacted) release archives** and the **original frozen
archives**. Scientific results (detection statistics, ACCESS_LEAK / BEHAVIORAL_LEAK counts, table
values, case ids, runtime results, B0-D3 results, configuration parameters, test expectations, and
paper-conclusion evidence) are **unchanged**.

Public archives are generated from the repository's public directories, which mirror the frozen
original archives (v5.1.1: 80/81 files byte-identical; v6: 34 files byte-identical), plus the
redactions and reorganizations listed below.

---

## 1. `medleakaudit_01_main_audit.zip` vs `medsage_dakd_authoring_bundle_v5_1_1.zip`

| File | Change | Reason | Impacts results? |
|---|---|---|---|
| `tests/dakd_v5/test_v5_core.py` | Path resolution remapped (`BUNDLE_MODE` detection; results read from `results/01_main_audit/` instead of a sibling `medsage_dakd_authoring_bundle_v5_1_1/` dir) | Repo layout adaptation | No (test only) |
| `README_PUBLIC.md` (new) | Added | Public-archive usage + env-var instructions | No |
| `docs/DATA_AVAILABILITY.md`, `docs/REPRODUCIBILITY.md`, `docs/RESULT_STATUS.md`, `docs/PACKAGE_MAPPING.md`, `docs/PUBLIC_ARCHIVE_DIFF_REPORT.md` (new) | Added | Public support documentation | No |
| all other files (80) | Byte-identical to the original archive | — | No |
| line endings | CRLF (repo) vs LF (archive) | Normalized by git (`.gitattributes`) | No |

## 2. `medleakaudit_03_cross_pipeline_bm25_topk.zip` vs `medsage_dakd_cross_pipeline_v6.zip`

| File | Change | Reason | Impacts results? |
|---|---|---|---|
| `scripts/dakd_v6/run_tcm_sleep_cross_pipeline.py` | `SECOND_ROOT` now read from env `TCM_SLEEP_RAG_ROOT` (raises `REQUIRES_LOCAL_ORIGINAL_PROJECT` if unset); `import os` added; absolute-path substitution regex generalized (`E:` -> `[A-Za-z]:`) | Redact local absolute path; env-var first | No (runtime path only; results deterministic) |
| `configs/dakd_v6/tcm_sleep_cross_pipeline.yaml` | Local absolute paths replaced by `<TCM_SLEEP_RAG_ROOT>` placeholder | Redact local paths | No (values identical) |
| `tests/dakd_v6/test_tcm_sleep_cross_pipeline.py` | `SECOND_ROOT` env-var based; results root remapped to `results/03_cross_pipeline/`; `REQUIRES_LOCAL_ORIGINAL_PROJECT` skip guard | Repo layout + env-var | No (test only) |
| `fixture_dakd_v6/` -> `fixtures/cross_pipeline/` | Directory rename | Public dir reorganization | No |
| `paper_package_dakd_v6/16_cross_pipeline/` -> `results/03_cross_pipeline/{cases,detection,leak_effects,runtime,manifests,quality_reports}/` | Directory reorganization | Public dir reorganization | No (file contents identical) |
| `manifests/EXPORT_ZIP_RESULT.json`, `manifests/VERIFY_ZIP_RESULT.json`, `manifests/synthetic_private_truth_registry.json` (extra) | Added (not in original archive) | Build/verify metadata + synthetic-truth registry (test-only values, never presented as human EvidenceGold) | No |
| `README_PUBLIC.md` + `docs/` (new) | Added | Public support documentation | No |
| all other files (34) | Byte-identical | — | No |
| line endings | CRLF (repo) vs LF (archive) | Normalized by git | No |

## 3. Path-replacement inventory (applies to both public archives)

| Original (local, redacted) | Replacement |
|---|---|
| `<original-second-project-root>` (the frozen archive's local path) | `<TCM_SLEEP_RAG_ROOT>` / env `TCM_SLEEP_RAG_ROOT` |
| `<original-repo-root>` (the frozen archive's local repo root) | resolved at runtime: `Path(__file__).resolve().parents[3]` |
| `[A-Za-z]:\python_project\...` (redaction regex, generalized) | `[A-Za-z]:[\/]python_project[\/]...` |
| `<REPO_ROOT>` (provenance, deployment package) | placeholder, see `release_assets/RELEASE_ASSETS_STATUS.md` |

No Windows drive-letter paths, `/home/`, `/Users/`, usernames, local data/model-cache directories
appear in either public archive (verified by automated scan: `real_absolute_path = 0`).

## 4. Conclusion

- All redactions are limited to: local paths, environment-variable entry points, path-related
  comments, cache/temp files, line endings and encoding.
- **No** scientific value, statistic, table value, case id, runtime result, B0-D3 result,
  configuration parameter, test expectation, or conclusion evidence was modified.
- Public archives replace the original archives as **GitHub Release attachments**; the original
  archives remain frozen and local-only (`dist/`, `_incoming/`).
