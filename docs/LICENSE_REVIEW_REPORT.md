# LICENSE_REVIEW_REPORT

## Final conclusion

**SAFE_TO_USE_MIT_FOR_ORIGINAL_CODE_ONLY**

## Basis

- The author (Shi Yuhan) confirmed that all code intended for publication in this repository
  (`src/`, `scripts/`, `tests/`, and author-created configuration/utility files) is **original
  work by Shi Yuhan**; a license-marker scan of every `.py` under `src/`, `scripts/`, `tests/`
  found **0** third-party license markers.
- **No copied or modified third-party source code** was found.
- Third-party datasets (webMedQA, cMedQA2), pretrained models (BAAI/bge-*), software dependencies
  (`requirements.txt`) and other external materials are **not** re-licensed under MIT; they remain
  subject to their respective licenses and terms (see `THIRD_PARTY_NOTICES.md`).
- Reuse of derived/desensitized result records should still be assessed against the original data
  sources' terms.
- Copyright line: `Copyright (c) 2026 Shi Yuhan` (no fictitious institution, author, DOI or ORCID).

## What changed

- `LICENSE`: copyright line set to `Copyright (c) 2026 Shi Yuhan`; MIT license text unchanged.
- `README.md`: added a License section (English + Chinese) clarifying that MIT covers only the
  original code, not third-party data/models/dependencies/raw medical content.
- `THIRD_PARTY_NOTICES.md`: created with per-item usage and license statements.
- `docs/LICENSE_STATUS.md`: updated to `CONFIRMED` with exact scope and exclusions.
- Release ZIPs: MIT LICENSE copy + THIRD_PARTY_NOTICES.md added; MIT scope clarified inside each
  package.

## Actions still pending

- None. Tagging/Release only after the author's explicit "confirm commit".
