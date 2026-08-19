from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BUILDER = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"
FEED = ROOT / "public" / "data" / "edgeiq_epi_workspace_terminal_feed_v1.csv"
FORM = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json"
OUT = (
    ROOT
    / "docs"
    / "full-product-implementation"
    / "HISTORICAL_EPI_WRITE_PATH_DIAGNOSTIC.txt"
)

if not BUILDER.exists():
    raise SystemExit(f"BUILDER_NOT_FOUND={BUILDER}")

lines = BUILDER.read_text(
    encoding="utf-8-sig",
    errors="replace",
).splitlines()

report = [
    "EDGEIQ HISTORICAL EPI WRITE-PATH DIAGNOSTIC",
    "=" * 110,
    "",
    f"BUILDER={BUILDER}",
    f"BUILDER_LINES={len(lines)}",
    "",
    "BUILDER WRITE PATH — LINES 240 TO END",
    "-" * 110,
]

for line_number in range(240, len(lines) + 1):
    report.append(f"{line_number:05d}: {lines[line_number - 1]}")

report.extend(
    [
        "",
        "OUTPUT FEED INSPECTION",
        "-" * 110,
    ]
)

if not FEED.exists():
    report.append(f"FEED_NOT_FOUND={FEED}")
else:
    with FEED.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        headers = reader.fieldnames or []

    report.append(f"FEED={FEED}")
    report.append(f"FEED_ROWS={len(rows)}")
    report.append(f"FEED_HEADERS={headers}")
    report.append("")

    start_fields = [
        field
        for field in headers
        if field.startswith("start_") and not field.endswith("_class")
        and not field.endswith("_context")
    ]

    report.append(f"DETECTED_START_FIELDS={start_fields}")
    report.append("")

    for index, row in enumerate(rows[:10], start=1):
        report.append(f"ROW_{index}")
        report.append(f"HORSE={row.get('horse', '')}")
        report.append(f"CURRENT_EPI={row.get('current_epi', '')}")

        for field in start_fields:
            report.append(f"{field}={row.get(field, '')!r}")
            report.append(
                f"{field}_context={row.get(field + '_context', '')!r}"
            )

        report.append("-" * 110)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print(f"WROTE={OUT}")
print("EDGEIQ_HISTORICAL_EPI_WRITE_PATH_DIAGNOSTIC_PASS")
