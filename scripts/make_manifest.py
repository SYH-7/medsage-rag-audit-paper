#!/usr/bin/env python
"""Generate release_manifest_sha256.csv from the GIT INDEX (blob = LF-normalized archive bytes).

Why: Windows worktrees may contain CRLF; GitHub source archives / clean checkouts are LF.
Hashing the index blobs makes the manifest identical to what a fresh Linux checkout or
GitHub source archive produces. The manifest itself and any other *sha256*.csv files are
EXCLUDED (a manifest cannot contain itself).
"""
import csv, hashlib, io, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "paper_results" / "manifests" / "release_manifest_sha256.csv"


def blob_of(rel):
    r = subprocess.run(["git", "-C", str(REPO), "show", ":" + rel],
                       capture_output=True)
    if r.returncode != 0:
        sys.exit(f"git show :{rel} failed: {r.stderr.decode(errors='replace')}")
    return r.stdout


files = [f for f in (subprocess.run(
    ["git", "-C", str(REPO), "ls-files"],
    capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.splitlines()) if f.strip()]

rows, excluded = [], []
for rel in sorted(files):
    rel = rel.replace("\\", "/")
    if "sha256" in rel.lower() and rel.endswith(".csv"):
        excluded.append(rel)
        continue
    b = blob_of(rel)
    rows.append({"path": rel, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)})

with io.open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["path", "sha256", "size"])
    w.writeheader()
    w.writerows(rows)

print(f"manifest written: {len(rows)} files -> {OUT.relative_to(REPO)}")
print(f"excluded sha256 lists: {excluded}")
