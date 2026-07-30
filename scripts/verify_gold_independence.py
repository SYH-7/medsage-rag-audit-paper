#!/usr/bin/env python
"""Gold independence check for D3 deployable conditions only.
Scans only the D3 deployment chain. Private evaluation modules
legitimately use Oracle gold data - those are NOT deployment leaks."""
import sys, os, ast, json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
exit_code = 0
findings = []

# Define D3 deployment chain files ONLY
deploy_chain = [
    REPO / "src/public_runtime/types.py",
    REPO / "src/private_evaluation/core.py",
]

# Check D3 gold fallback in core.py (pqd if pqd else gqd -> pqd if pqd else set())
cd_path = REPO / "src/private_evaluation/core.py"
gold_fallback_count = 0
if cd_path.exists():
    src = cd_path.read_text(encoding='utf-8')
    gold_fallback_count = src.count("pqd if pqd else gqd")
    if gold_fallback_count > 0:
        findings.append(f"GOLD_FALLBACK_IN_D3: 'pqd if pqd else gqd' found in {cd_path.relative_to(REPO)} ({gold_fallback_count} occurrences)")

# Check public_runtime types.py for actual gold FIELD leakage in class definitions
# DENY_COLUMNS list is not a leak - it's a safety mechanism
types_path = REPO / "src/public_runtime/types.py"
public_gold_fields = 0
if types_path.exists():
    src = types_path.read_text(encoding='utf-8')
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in ast.walk(node):
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    gold_fields = ["query_states", "supported_states", "relevance", "risk_types",
                                   "oracle", "gold"]
                    for gf in gold_fields:
                        if gf in field_name.lower():
                            findings.append(f"GOLD_FIELD_IN_PUBLIC_CLASS: '{field_name}' in class {node.name}")
                            public_gold_fields += 1

# Report
print(f"Scanned D3 deployment chain: {[str(f.relative_to(REPO)) for f in deploy_chain]}")
print(f"Gold fallback (pqd if pqd else gqd) count: {gold_fallback_count}")
print(f"static_gold_violation_count: {len([f for f in findings if 'GOLD_FALLBACK' in f])}")

for f in findings:
    exit_code = 1
    print(f"  FINDING: {f}")

report = {
    "gold_independent": exit_code == 0,
    "findings": findings,
    "total_findings": len(findings),
    "scanned_files": [str(f.relative_to(REPO)) for f in deploy_chain],
    "gold_fallback_count": gold_fallback_count,
    "static_gold_violation_count": len([f for f in findings if 'GOLD_FALLBACK' in f]),
}
with open(str(REPO / "GOLD_INDEPENDENCE_REPORT.json"), 'w') as f:
    json.dump(report, f, indent=2)
print(f"\nGold independence: {'PASS' if exit_code == 0 else 'FAIL'}")
sys.exit(exit_code)
