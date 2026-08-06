# Data Availability

## Public data (this repository)

- `results/01_main_audit/` - main-project (v5.1.1) leak-audit desensitized results and recalculation materials (supported data item [1]).
- `results/02_deployment_diagnostics/` - B0-D3 / MMR / Top-K / generation verified-release desensitized results (item [2]).
- `results/03_cross_pipeline/` - second-project BM25 + Top-K cross-pipeline controlled verification (item [3]).
- `fixtures/cross_pipeline/` - synthetic fixtures (`TEST_ONLY_PRIVATE_SOURCE`; test-only values, never presented as human EvidenceGold).

## Release attachments

- `medleakaudit_01_main_audit.zip`
- `medleakaudit_02_deployment_diagnostics.zip`
- `medleakaudit_03_cross_pipeline_bm25_topk.zip`
- `SHA256SUMS.txt`

Public attachments are generated from the frozen original archives' scientific material via path
redaction and public-directory reorganization. Core results, configurations and statistics are
unchanged (see `docs/PUBLIC_ARCHIVE_DIFF_REPORT.md`).

## Not published (private)

- Raw medical texts, patient questions, complete candidate documents, plaintext EvidenceGold /
  QueryGold, annotator sheets, vector stores, model weights, credentials, and the two original
  projects (main + second). The original archives remain local-only (`dist/`, `_incoming/`).

## Original datasets

Derived files originate from webMedQA (`hejunqing/webMedQA`) and cMedQA2 (`zhangsheng93/cMedQA2`).
Users must obtain the original datasets from their official sources and comply with their licenses.
This repository does not redistribute full source texts.
