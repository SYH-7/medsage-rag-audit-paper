# Result Provenance

All paper results are sourced from:
- `outputs/paper_r7_freeze/`: Final frozen paper results with SHA256 verification
- `outputs/phase6b_r7/`: R7 phase paper results
- `outputs/paper_r8_northcore/`: Additional analysis (BGE robustness, equivalence tests)
- `outputs/leakage_injection_r4/`: Leakage injection results

## Verification
- release_manifest_sha256.csv contains full 64-char SHA256 hashes for all release files
- Historical bundle_manifest.csv uses truncated hashes (source record only)
- endpoint_final_validation.json verifies 6 endpoints at Top-5 query level
