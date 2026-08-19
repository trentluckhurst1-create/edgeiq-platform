from pathlib import Path
import sys

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "runner_board_builder_trace_v1.txt"

TARGETS = [
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_live_runner_board_governed_v1.csv",
]

KEYWORDS = [
    "edgeiq_graphql_getRacesForMeet_meeting_warehouse_v1.csv",
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_live_runner_board_governed_v1.csv",
    "trainer",
    "jockey",
    "barrier",
    "weight",
    "silk",
    "write_csv",
    "DictWriter",
]

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".vite",
    "__pycache__",
    "checkpoints",
}

def should_skip(path: Path) -> bool:
    rel_parts = path.relative_to(ROOT).parts
    return any(part in SKIP_DIRS for part in rel_parts)

def show_context(lines, line_no, before=8, after=12):
    start = max(1, line_no - before)
    end = min(len(lines), line_no + after)
    return [f"{i:05d}: {lines[i - 1]}" for i in range(start, end + 1)]

hits = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    if should_skip(path):
        continue

    if path.suffix.lower() not in {".py", ".ps1"}:
        continue

    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        continue

    lower = text.lower()

    if not any(target.lower() in lower for target in TARGETS):
        continue

    hits.append((path, text.splitlines()))

report = []
report.append("RUNNER BOARD BUILDER TRACE")
report.append("=" * 120)
report.append(f"FILES MATCHED={len(hits)}")

for path, lines in sorted(hits, key=lambda item: str(item[0]).lower()):
    report.append("")
    report.append("=" * 120)
    report.append(f"FILE={path.relative_to(ROOT)}")

    for keyword in KEYWORDS:
        matches = [
            idx
            for idx, line in enumerate(lines, start=1)
            if keyword.lower() in line.lower()
        ]

        if not matches:
            report.append(f"KEYWORD={keyword} NOT FOUND")
            continue

        for idx in matches[:3]:
            report.append("")
            report.append(f"KEYWORD={keyword} LINE={idx}")
            report.extend(show_context(lines, idx))

        if len(matches) > 3:
            report.append(
                f"KEYWORD={keyword} ADDITIONAL_MATCHES_SKIPPED={len(matches) - 3}"
            )

report.append("")
report.append("=" * 120)
report.append("TRACE COMPLETE")

OUT.parent.mkdir(parents=True, exist_ok=True)

text = "\n".join(report)
OUT.write_text(text, encoding="utf-8")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("RUNNER BOARD BUILDER TRACE COMPLETE")
print(f"FILES MATCHED={len(hits)}")
print(f"OUTPUT={OUT}")
