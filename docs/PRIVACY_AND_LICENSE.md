# Privacy & License

## Privacy policy for this release

The following are **excluded** from the repository:

- Windows drive-letter absolute paths (e.g. `C:` / `D:` / `E:`), Linux/macOS user-home paths (`/home/`, `/Users/`), and any other local absolute paths.
- API keys, secrets, tokens, passwords, bearer tokens, `sk-*` credentials.
- Identity numbers, phone numbers, and email addresses.
- Raw medical questions and long medical text passages.
- Plaintext EvidenceGold / QueryGold values and non-synthetic `private_truth` labels.
- `.env` files, SQLite/Chroma/FAISS stores, pickle files, and model weights.

A content scan was run over all staged files; results are recorded in `docs/PRIVACY_SCAN_REPORT.md`. Variable names such as `API_KEY` or `token` in source code are **not** treated as secrets by themselves; each hit is classified as `real_secret` / `variable_name_only` / `false_positive` / `requires_manual_review`.

## Data licenses of derived datasets

- webMedQA (`hejunqing/webMedQA`): Apache-2.0.
- cMedQA2 (`zhangsheng93/cMedQA2`): dataset for non-commercial research only.

This repository does not redistribute the complete source texts; users must obtain the datasets from the official sources and comply with their licenses.

## License of this repository

The existing `LICENSE` (MIT, Copyright (c) 2026 MedSAGE Team) is retained as-is because it is the previously author-confirmed license file in this repository. See `docs/LICENSE_STATUS.md`.
