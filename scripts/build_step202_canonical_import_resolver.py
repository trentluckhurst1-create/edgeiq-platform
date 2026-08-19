from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "architecture" / "step202"

IDENTITIES = DOCS / "STEP202_CANONICAL_MODULE_IDENTITIES.csv"
IMPORTS = DOCS / "STEP202_IMPORT_GRAPH.csv"

OUTPUT = DOCS / "STEP202_CANONICAL_IMPORT_RESOLUTION.csv"

# ---------------------------------------------------------------------

modules = {}

with IDENTITIES.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        modules[row["canonical_module"]] = row

rows = []

resolved = 0
unresolved = 0

with IMPORTS.open("r", encoding="utf-8-sig", newline="") as f:

    reader = csv.DictReader(f)

    for row in reader:

        imported = row.get("imported_module", "").strip()

        target = modules.get(imported)

        if target:

            resolved += 1

            row["resolved"] = "YES"
            row["resolved_repository_path"] = target["repository_path"]
            row["resolved_canonical_module"] = target["canonical_module"]

        else:

            unresolved += 1

            row["resolved"] = "NO"
            row["resolved_repository_path"] = ""
            row["resolved_canonical_module"] = ""

        rows.append(row)

fieldnames = list(rows[0].keys())

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:

    writer = csv.DictWriter(f, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(rows)

print("=" * 80)
print("STEP202-003C CANONICAL IMPORT RESOLUTION")
print("=" * 80)
print()
print(f"Imports analysed : {len(rows):,}")
print(f"Resolved         : {resolved:,}")
print(f"Unresolved       : {unresolved:,}")
print()
print(f"Output           : {OUTPUT}")
print()
print("STATUS : PASS")
