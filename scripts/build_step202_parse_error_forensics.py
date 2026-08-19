from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOCS = ROOT / "docs" / "architecture" / "step202"

INPUT = DOCS / "STEP202_IMPORT_PARSE_ERRORS.csv"

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

rows = []

with INPUT.open(
    "r",
    newline="",
    encoding="utf-8"
) as f:

    reader = csv.DictReader(f)

    for row in reader:
        rows.append(row)

print("=" * 80)
print("STEP202 PARSE ERROR FORENSICS")
print("=" * 80)
print()

print(f"Rows loaded : {len(rows):,}")
print()


# ==============================================================================
# FORENSIC ANALYSIS
# ==============================================================================

message_counter = Counter()

for row in rows:

    message = (row.get("error") or "").strip()

    if not message:
        message = "<EMPTY ERROR MESSAGE>"

    message_counter[message] += 1

print("=" * 80)
print("UNIQUE ERROR MESSAGES")
print("=" * 80)
print()

for message, count in message_counter.most_common():

    print(f"{count:>5}  {message}")

print()

OUTPUT = DOCS / "STEP202_PARSE_ERROR_FORENSICS.md"

with OUTPUT.open(
    "w",
    encoding="utf-8"
) as f:

    f.write("# STEP202 Parse Error Forensics\n\n")

    f.write(f"Total parse errors: {len(rows):,}\n\n")

    f.write("## Unique Error Messages\n\n")

    for message, count in message_counter.most_common():

        f.write(f"### {count} occurrence(s)\n\n")
        f.write("```\n")
        f.write(message)
        f.write("\n```\n\n")

print("=" * 80)
print("OUTPUT")
print("=" * 80)
print(OUTPUT)
print()

print("STATUS : PASS")

sys.exit(0)

