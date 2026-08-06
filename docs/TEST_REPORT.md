# Test Report (final)

Version `2.0.4-paper-support` · Default branch `main`

## 1. pytest

```
python -m pytest tests/ -q
```
**45 passed / 6 skipped / 0 failed** (2026-08-06).

Skipped (6) - all `REQUIRES_LOCAL_ORIGINAL_PROJECT` (need `medsage_rag_full` /
`tcm_sleep_rag_full` local projects; set `TCM_SLEEP_RAG_ROOT`). Not faked.

## 2. Release-ZIP verification (3 public ZIPs)

| check | result |
|---|---|
| SHA256SUMS root == release_assets | PASS |
| SHA-256 of all 3 ZIPs in SHA256SUMS.txt | PASS |
| `testzip` integrity for all 3 | PASS |
| no `.pyc`/`__pycache__` inside | PASS |
| public ZIP vs repo public dirs mapping (0 missing) | PASS |
| blacklist filenames = 0 / data content = 0 (deployment pkg) | PASS |
| absolute-path scan (real_absolute_path) | 0 |
| JSON/JSONL parse | 0 errors |
| YAML parse | 0 errors |
| CSV readable | 0 errors |
| Python `py_compile` (src+scripts+tests) | 0 errors |

## 3. Privacy

Five-zero: real_secret=0, real_absolute_path=0, real_private_gold=0, raw_medical_text=0,
unresolved_manual_review=0. See `docs/PRIVACY_SCAN_REPORT.md`.

## 4. Consistency vs frozen original archives

Public archives are generated from the frozen originals via path redaction and public-dir
reorganization. Scientific values unchanged. Per-file diff:
`docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`.

## 5. Release SHA-256 (archives unchanged from v2.0.1; v2.0.4 repackage of main-audit zip)

```
fd73a02d817a22bee3609af4fdceb7ecf2c792154cc50e1d64114a6b544b705b  medleakaudit_01_main_audit.zip
ad7e479fdf1fd6381e6243700af9a3d3937b7d13e31362d356284ea38e72c8a9  medleakaudit_02_deployment_diagnostics.zip
24b752f10527e305162b0d6e818f93aef6bef54a68cfb61ae5221045ea699360  medleakaudit_03_cross_pipeline_bm25_topk.zip
```
