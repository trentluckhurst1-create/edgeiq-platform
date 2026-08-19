from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()

GITIGNORE = ROOT / ".gitignore"

RULES = [
    "",
    "# EDGEIQ governed generated warehouse assets",
    (
        "docs/performance-intelligence/warehouse-v2/"
        "historical-observation-warehouse-v3/"
        "eiq_historical_observation_v3_*/"
        "historical_observation_warehouse_v3.csv"
    ),
    (
        "docs/performance-intelligence/warehouse-v2/"
        "historical-observation-warehouse-v3/"
        "eiq_historical_observation_v3_*/"
        "historical_observation_warehouse_v3.sqlite"
    ),
]

existing = ""

if GITIGNORE.exists():
    existing = GITIGNORE.read_text(
        encoding="utf-8-sig"
    )

existing_lines = {
    line.rstrip()
    for line in existing.splitlines()
}

missing_rules = [
    rule
    for rule in RULES
    if rule
    and rule not in existing_lines
]

if missing_rules:
    updated = existing.rstrip()

    if updated:
        updated += "\n"

    updated += "\n".join(RULES)
    updated += "\n"

    GITIGNORE.write_text(
        updated,
        encoding="utf-8",
    )

    print("UPDATED: .gitignore")

    for rule in missing_rules:
        print("  ADDED:", rule)
else:
    print(
        "UNCHANGED: .gitignore already contains "
        "the governed V3 warehouse asset rules"
    )

print()
print(
    "POLICY: generated V3 CSV and SQLite assets "
    "remain local and reproducible."
)

print(
    "POLICY: governance artefacts, contracts, "
    "reports, manifest and latest pointer remain trackable."
)
