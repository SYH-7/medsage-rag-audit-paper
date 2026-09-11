# Privacy Scan Report (final)

Generated: 2026-08-06 16:21:09
Scope: repository tracked text files + extracted contents of the three Release ZIPs
(`medleakaudit_01_main_audit.zip`, `medleakaudit_02_deployment_diagnostics.zip`,
`medleakaudit_03_cross_pipeline_bm25_topk.zip`).

## Five-zero verdict

| category | count |
|---|---|
| real_secret | 0 |
| real_absolute_path | 0 |
| real_private_gold | 0 |
| raw_medical_text | 0 |
| unresolved_manual_review | 0 |

## Classified items (all resolved)

| classification | count | examples |
|---|---|---|
| false_positive (rule text) | 5 | `docs/PRIVACY_AND_LICENSE.md:7`, `docs/PRIVACY_SCAN_REPORT.md:11`, `docs/PUBLIC_ARCHIVE_DIFF_REPORT.md:47` (and 2 copies inside the public ZIPs) - statements that merely list forbidden path kinds (`/home/`, `/Users/`) as policy text, not real paths |
| variable_name_only | 0 | - |

No items require manual review: every hit was classified as rule-text/false_positive; no secrets,
no absolute local paths, no plaintext Gold, no raw medical text, no model/vector/DB artifacts.

## Revision-round re-scan (round 2 additions)

Scope added: `scripts/review_metrics/*.py`, `results/04_revision_metrics/**`,
`docs/REVISION_EVIDENCE_MAPPING.md`, `tests/revision/**`.

| category | count |
|---|---|
| real_secret | 0 |
| real_absolute_path | 0 |
| real_private_gold | 0 |
| raw_medical_text | 0 |
| unresolved_manual_review | 0 |

Notes: one internal absolute source-case path recorded in the frozen
`new_operators_cross.json` was redacted to `benchmark_work_cross/<frozen-cross-case>` before
publication; the hardcoded second-project root in `sweep_real_code.py` was replaced by the
`TCM_SLEEP_RAG_ROOT` / `MEDSAGE_RAG_ROOT` environment variables. The zero-absolute-path policy is
enforced by `tests/revision/test_revision_evidence_consistency.py`.

## Scan rules applied

- Windows drive-letter absolute paths (excluding URLs and `<placeholder>` values)
- `/home/`, `/Users/` (excluding rule-text statements)
- API_KEY / SECRET / TOKEN / PASSWORD / Bearer / sk- assignments (real-value check)
- `.env` secrets; sensitive binary extensions (sqlite/chroma/faiss/pkl/pt/bin/safetensors)
- EvidenceGold / QueryGold markers; long CJK medical-text blocks

## Notes

- The report itself contains no real local absolute paths (placeholders only).
- Dataset-derived tables carry attribution to webMedQA / cMedQA2 (see LICENSE_REVIEW_REPORT.md).
