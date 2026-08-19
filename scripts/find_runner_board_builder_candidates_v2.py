from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "runner_board_builder_candidates_v2.txt"

SKIP = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".vite",
    "__pycache__",
    "checkpoints",
}

KEYWORDS = [
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_live_runner_board_governed_v1.csv",
    "race_fields.csv",
    "edgeiq_vic_live_fields_synced.csv",
    "edgeiq_graphql_getRacesForMeet_meeting_warehouse_v1.csv",
    "to_csv(",
    "DictWriter",
    "writerows(",
    "write_csv(",
]

report = []
report.append("=" * 120)
report.append("EDGEIQ RUNNER BOARD BUILDER CANDIDATES")
report.append("=" * 120)

count = 0

for path in sorted((ROOT / "scripts").glob("*.py")):

    name = path.name.lower()

    if not (
        name.startswith("build_")
        or name.startswith("generate_")
        or name.startswith("create_")
    ):
        continue

    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
    except:
        continue

    lower = text.lower()

    if not any(k.lower() in lower for k in KEYWORDS):
        continue

    count += 1

    report.append("")
    report.append("=" * 120)
    report.append(f"FILE={path.name}")

    lines = text.splitlines()

    for kw in KEYWORDS:

        matches = [
            i
            for i,l in enumerate(lines,1)
            if kw.lower() in l.lower()
        ]

        if not matches:
            continue

        for line_no in matches[:5]:

            report.append("")
            report.append(f"KEYWORD={kw} LINE={line_no}")

            start=max(1,line_no-5)
            end=min(len(lines),line_no+10)

            for j in range(start,end+1):
                report.append(f"{j:05d}: {lines[j-1]}")

report.append("")
report.append("=" * 120)
report.append(f"FILES FOUND={count}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("COMPLETE")
print(f"FILES FOUND={count}")
print(f"OUTPUT={OUT}")
