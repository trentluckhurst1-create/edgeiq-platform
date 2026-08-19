from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOCS = ROOT / "docs" / "architecture" / "step202"

PARSE_ERRORS = DOCS / "STEP202_IMPORT_PARSE_ERRORS.csv"

if not PARSE_ERRORS.exists():
    raise FileNotFoundError(
        f"Missing parse error file: {PARSE_ERRORS}"
    )

def now_iso():
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()

rows = []

with PARSE_ERRORS.open(
    "r",
    newline="",
    encoding="utf-8"
) as f:

    reader = csv.DictReader(f)

    for row in reader:
        rows.append(row)

print("=" * 80)
print("STEP202-002A PARSE ERROR ANALYSIS")
print("=" * 80)
print()
print(f"Parse errors loaded : {len(rows):,}")
print()


# ==============================================================================
# CLASSIFY PARSE ERRORS
# ==============================================================================

categories = defaultdict(list)

def classify(message):

    text = (message or "").lower()

    if "invalid syntax" in text:
        return "SyntaxError"

    if "indent" in text:
        return "IndentationError"

    if "unicode" in text:
        return "UnicodeError"

    if "decode" in text:
        return "DecodeError"

    if "eof" in text:
        return "UnexpectedEOF"

    if "expected" in text:
        return "ExpectedToken"

    if "unterminated" in text:
        return "UnterminatedString"

    return "Other"

for row in rows:

    category = classify(
        row.get("error", "")
    )

    categories[category].append(row)

summary_rows = []

for category in sorted(categories):

    summary_rows.append({

        "category": category,

        "count": len(categories[category])

    })

summary_rows.sort(
    key=lambda r: r["count"],
    reverse=True
)

print("Categories discovered")
print("---------------------")

for row in summary_rows:

    print(
        f"{row['category']:<25} {row['count']:>6}"
    )

print()


# ==============================================================================
# WRITE OUTPUTS
# ==============================================================================

SUMMARY_CSV = DOCS / "STEP202_PARSE_ERROR_SUMMARY.csv"
REPORT_MD = DOCS / "STEP202_PARSE_ERROR_ANALYSIS.md"

with SUMMARY_CSV.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "category",
            "count"
        ]
    )

    writer.writeheader()

    for row in summary_rows:
        writer.writerow(row)

with REPORT_MD.open(
    "w",
    encoding="utf-8"
) as f:

    f.write("# STEP202 Parse Error Analysis\n\n")
    f.write(f"Generated: {now_iso()}\n\n")
    f.write(f"Total Parse Errors: {len(rows):,}\n\n")

    for summary in summary_rows:

        category = summary["category"]

        examples = categories[category][:10]

        f.write(f"## {category}\n\n")
        f.write(f"Occurrences: {summary['count']}\n\n")

        for example in examples:

            f.write(
                f"- {example['module_name']}  "
                f"({example['repository_path']})\n"
            )

        f.write("\n")

print("=" * 80)
print("OUTPUTS")
print("=" * 80)
print(SUMMARY_CSV)
print(REPORT_MD)
print()

errors = []

if len(rows) == 0:
    errors.append("No parse errors were loaded.")

if len(summary_rows) == 0:
    errors.append("No categories were produced.")

if errors:

    print("=" * 80)
    print("STEP202-002A FAILED")
    print("=" * 80)

    for error in errors:
        print("ERROR:", error)

    sys.exit(1)

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Parse errors analysed : {len(rows):,}")
print(f"Categories            : {len(summary_rows):,}")
print()
print("STATUS : PASS")

sys.exit(0)

