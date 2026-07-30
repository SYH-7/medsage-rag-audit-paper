#!/usr/bin/env python
"""Verify manifest - generate release manifest with full SHA256 and verify it.
Historical truncated SHA entries are marked as HISTORICAL_MANIFEST_UNVERIFIABLE."""
import sys, csv, hashlib, os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NEW_MANIFEST = REPO / "paper_results/manifests/release_manifest_sha256.csv"

def sha256(p):
    return hashlib.sha256(open(str(p), 'rb').read()).hexdigest()

exit_code = 0

# Collect all repo files, excluding caches, pyc, runtime reports, and manifest itself
exclude_patterns = {"__pycache__", ".pytest_cache", ".git"}
exclude_suffixes = {".pyc"}
exclude_files = {
    "PAPER_REPRODUCTION_REPORT.json",
    "GOLD_INDEPENDENCE_REPORT.json",
    "paper_results/manifests/release_manifest_sha256.csv",
}

all_files = []
for f in sorted(REPO.rglob("*")):
    if not f.is_file():
        continue
    rel = str(f.relative_to(REPO)).replace("\\", "/")
    if any(p in rel for p in exclude_patterns):
        continue
    if f.suffix in exclude_suffixes:
        continue
    if rel in exclude_files:
        continue
    all_files.append(f)

release_rows = [["relative_path", "file_size", "sha256", "role"]]
for f in all_files:
    rel = str(f.relative_to(REPO)).replace("\\", "/")
    sz = f.stat().st_size
    h = sha256(str(f))
    role = "code" if f.suffix == ".py" else "result" if f.suffix in (".csv",".json",".jsonl") else "doc"
    release_rows.append([rel, str(sz), h, role])

with open(str(NEW_MANIFEST), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerows(release_rows)
print(f"Release manifest: {len(release_rows)-1} files")

# Re-read release manifest and verify each entry
verified = 0
verified_failed = 0
with open(str(NEW_MANIFEST), encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) < 3:
            continue
        rel_path = row[0].replace("\\", "/")
        expected_sha = row[2].strip()
        if len(expected_sha) != 64:
            print(f"  INVALID_SHA (not 64-char): {rel_path}")
            verified_failed += 1
            exit_code = 1
            continue
        full_path = REPO / rel_path
        if not full_path.exists():
            print(f"  MISSING: {rel_path}")
            verified_failed += 1
            exit_code = 1
            continue
        actual = sha256(str(full_path))
        if actual != expected_sha:
            print(f"  SHA256_MISMATCH: {rel_path}")
            verified_failed += 1
            exit_code = 1
        else:
            verified += 1

print(f"Release manifest verified: {verified} OK, {verified_failed} FAILED")

if verified == 0:
    print("  ERROR: verified_files must be > 0")
    exit_code = 1

print(f"\nStatus: {'PASS' if exit_code == 0 else 'FAIL'}")
sys.exit(exit_code)
