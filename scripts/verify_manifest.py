#!/usr/bin/env python
"""Verify release_manifest_sha256.csv against the GIT INDEX (blob bytes).

READ-ONLY: this script never writes or regenerates the manifest.
It checks that every listed file matches (sha256 + size) the exact bytes stored in
the git index, i.e. the bytes of a fresh Linux checkout / GitHub source archive.
"""
import csv, hashlib, io, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MF = REPO / "paper_results" / "manifests" / "release_manifest_sha256.csv"


def blob_of(rel):
    r = subprocess.run(["git", "-C", str(REPO), "show", ":" + rel],
                       capture_output=True)
    return r.stdout


if not MF.exists():
    sys.exit(f"manifest missing: {MF}. Run scripts/make_manifest.py first.")

rows = list(csv.DictReader(io.open(MF, encoding="utf-8")))
ok = fail = 0
for r in rows:
    p = r["path"]
    b = blob_of(p)
    if hashlib.sha256(b).hexdigest() != r["sha256"] or len(b) != int(r["size"]):
        print(f"  MISMATCH: {p}")
        fail += 1
    else:
        ok += 1

print(f"manifest verified against git index: {ok} OK, {fail} FAILED")
if ok == 0:
    print("  ERROR: verified count must be > 0")
    fail += 1
print(f"Status: {'PASS' if fail == 0 else 'FAIL'}")
sys.exit(0 if fail == 0 else 1)
