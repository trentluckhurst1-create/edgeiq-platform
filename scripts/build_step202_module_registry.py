from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ==============================================================================
# STEP202 - MODULE REGISTRY BUILDER
# ==============================================================================

ROOT = Path(__file__).resolve().parent.parent

DOCS = ROOT / "docs" / "architecture" / "step202"
DOCS.mkdir(parents=True, exist_ok=True)

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def find_census():
    matches = list(ROOT.rglob("STEP201_REPOSITORY_CENSUS*.csv"))
    if not matches:
        raise FileNotFoundError(
            "Unable to locate STEP201 repository census."
        )
    matches.sort()
    return matches[-1]

print("=" * 80)
print("STEP202-001 CANONICAL MODULE REGISTRY")
print("=" * 80)

census_path = find_census()

print()
print("Repository :", ROOT)
print("Census     :", census_path)
print()

rows = []

with census_path.open(
    "r",
    newline="",
    encoding="utf-8-sig"
) as f:

    reader = csv.DictReader(f)

    for row in reader:
        rows.append(row)

print(f"Assets loaded : {len(rows):,}")

python_assets = []

for row in rows:

    ext = (row.get("extension") or "").lower()

    if ext != ".py":
        continue

    python_assets.append(row)

print(f"Python assets : {len(python_assets):,}")
print()

# ==============================================================================
# BUILD MODULE REGISTRY
# ==============================================================================

module_rows = []
module_lookup = {}
duplicate_lookup = defaultdict(list)

for row in python_assets:

    repository_path = (
        row.get("repository_path")
        or ""
    ).replace("\\", "/")

    module_name = Path(repository_path).stem

    asset_id = row.get("asset_id", "").strip()

    record = {
        "module_name": module_name,
        "asset_id": asset_id,
        "repository_path": repository_path,
        "domain": row.get("domain", ""),
        "asset_type": row.get("asset_type", ""),
        "extension": row.get("extension", ""),
        "status": row.get("status", "")
    }

    module_rows.append(record)

    module_lookup[module_name] = record
    duplicate_lookup[module_name].append(asset_id)

module_rows.sort(
    key=lambda r: (
        r["module_name"].lower(),
        r["repository_path"].lower()
    )
)

duplicate_rows = []

for module_name in sorted(duplicate_lookup):

    assets = duplicate_lookup[module_name]

    if len(assets) > 1:

        duplicate_rows.append({
            "module_name": module_name,
            "occurrences": len(assets),
            "asset_ids": ";".join(sorted(assets))
        })

print(f"Modules discovered : {len(module_rows):,}")
print(f"Duplicate modules  : {len(duplicate_rows):,}")
print()


# ==============================================================================
# WRITE OUTPUTS
# ==============================================================================

registry_csv = DOCS / "STEP202_MODULE_REGISTRY.csv"
registry_json = DOCS / "STEP202_MODULE_REGISTRY.json"
audit_md = DOCS / "STEP202_MODULE_REGISTRY_AUDIT.md"

write_csv(
    registry_csv,
    module_rows,
    [
        "module_name",
        "asset_id",
        "repository_path",
        "domain",
        "asset_type",
        "extension",
        "status"
    ]
)

write_json(
    registry_json,
    {
        "generated_utc": now_iso(),
        "repository_root": str(ROOT),
        "census_file": str(census_path),
        "module_count": len(module_rows),
        "duplicate_count": len(duplicate_rows),
        "modules": module_rows
    }
)

with audit_md.open("w", encoding="utf-8") as f:

    f.write("# STEP202 MODULE REGISTRY AUDIT\n\n")
    f.write(f"Generated: {now_iso()}\n\n")
    f.write(f"Repository: {ROOT}\n")
    f.write(f"Census: {census_path}\n\n")
    f.write(f"Python assets: {len(python_assets):,}\n")
    f.write(f"Modules: {len(module_rows):,}\n")
    f.write(f"Duplicate module names: {len(duplicate_rows):,}\n\n")

    if duplicate_rows:

        f.write("## Duplicate Modules\n\n")

        for dup in duplicate_rows:

            f.write(
                f"- {dup['module_name']} "
                f"({dup['occurrences']} occurrences)\n"
            )

    else:

        f.write("No duplicate module names detected.\n")

print("=" * 80)
print("OUTPUTS")
print("=" * 80)
print(registry_csv)
print(registry_json)
print(audit_md)
print()
print("STEP202-001 COMPLETE")


# ==============================================================================
# FINAL VALIDATION
# ==============================================================================

errors = []

if len(rows) == 0:
    errors.append("Repository census contained zero assets.")

if len(python_assets) == 0:
    errors.append("Repository contains zero Python assets.")

if len(module_rows) == 0:
    errors.append("Module registry is empty.")

if len(module_lookup) != len(module_rows):

    print()
    print("NOTICE")
    print("Duplicate module names detected.")
    print("Unique modules :", len(module_lookup))
    print("Registry rows  :", len(module_rows))
    print()

if errors:

    print("=" * 80)
    print("STEP202-001 FAILED")
    print("=" * 80)

    for error in errors:
        print("ERROR:", error)

    sys.exit(1)

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Canonical assets     : {len(rows):,}")
print(f"Python assets        : {len(python_assets):,}")
print(f"Registered modules   : {len(module_rows):,}")
print(f"Duplicate modules    : {len(duplicate_rows):,}")
print()

print("STATUS : PASS")
print()

sys.exit(0)

