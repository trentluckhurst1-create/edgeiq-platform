from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TARGET = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"
OUT = ROOT / "docs" / "full-product-implementation" / "FORM_GUIDE_HISTORICAL_EPI_BUILDER_LIVE_INSPECTION.txt"

if not TARGET.exists():
    raise SystemExit(f"TARGET_NOT_FOUND={TARGET}")

text = TARGET.read_text(encoding="utf-8-sig", errors="replace")
lines = text.splitlines()

patterns = [
    r"historical_epi_for_run",
    r"historicalEpi",
    r"edgeiq_historical_performance_rating_v6_1_research",
    r"performance_rating_v6_1_research",
    r"historical.*lookup",
    r"research.*lookup",
    r"csv\.DictReader",
    r"TRACK",
    r"track",
]

hit_lines = set()

for index, line in enumerate(lines, start=1):
    if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in patterns):
        start = max(1, index - 20)
        end = min(len(lines), index + 45)

        for line_number in range(start, end + 1):
            hit_lines.add(line_number)

sections = []
current = []

for line_number in sorted(hit_lines):
    if current and line_number != current[-1] + 1:
        sections.append(current)
        current = []

    current.append(line_number)

if current:
    sections.append(current)

report = [
    "EDGEIQ FORM GUIDE HISTORICAL EPI BUILDER LIVE INSPECTION",
    "=" * 110,
    "",
    f"TARGET={TARGET}",
    f"TOTAL_LINES={len(lines)}",
    f"SECTIONS={len(sections)}",
    "",
]

for section_number, section in enumerate(sections, start=1):
    report.append(f"SECTION {section_number}: LINES {section[0]}-{section[-1]}")
    report.append("-" * 110)

    for line_number in section:
        report.append(f"{line_number:05d}: {lines[line_number - 1]}")

    report.append("")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print(f"WROTE={OUT}")
print("EDGEIQ_FORM_GUIDE_HISTORICAL_EPI_BUILDER_LIVE_INSPECTION_PASS")
