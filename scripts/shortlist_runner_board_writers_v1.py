from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
REPORT = ROOT / "docs" / "public_data_writer_trace_v1.txt"
OUT = ROOT / "docs" / "runner_board_writer_shortlist_v1.txt"

text = REPORT.read_text(encoding="utf-8-sig", errors="ignore")
blocks = re.split(r"\n={20,}\n", text)

wanted = []

for block in blocks:
    lower = block.lower()

    if not block.strip().startswith("FILE="):
        continue

    score = 0
    reasons = []

    if "edgeiq_live_runner_board" in lower:
        score += 10
        reasons.append("runner-board reference")

    if "race_fields.csv" in lower:
        score += 6
        reasons.append("race-fields source")

    if "edgeiq_vic_live_fields_synced.csv" in lower:
        score += 6
        reasons.append("live-fields source")

    if "edgeiq_graphql_getracesformeet_meeting_warehouse_v1.csv" in lower:
        score += 12
        reasons.append("GraphQL warehouse source")

    if "to_csv(" in lower:
        score += 2
        reasons.append("pandas write")

    if "dictwriter" in lower or "writerows(" in lower:
        score += 2
        reasons.append("csv write")

    if "copyfile" in lower or "shutil.copy" in lower or "replace(" in lower:
        score += 3
        reasons.append("copy/replace write")

    first_line = block.splitlines()[0].strip().lower()

    if any(
        first_line.startswith(prefix)
        for prefix in (
            "file=build_",
            "file=generate_",
            "file=create_",
            "file=run_",
            "file=refresh_",
            "file=sync_",
            "file=ingest_",
            "file=orchestrate_",
        )
    ):
        score += 4
        reasons.append("builder/orchestrator name")

    if first_line.startswith("file=audit_"):
        score -= 8

    if first_line.startswith("file=apply_"):
        score -= 3

    if score >= 8:
        wanted.append((score, reasons, block))

wanted.sort(key=lambda x: (-x[0], x[2].splitlines()[0]))

lines = []
lines.append("=" * 120)
lines.append("EDGEIQ RUNNER BOARD WRITER SHORTLIST")
lines.append("=" * 120)
lines.append(f"CANDIDATES={len(wanted)}")
lines.append("")

for score, reasons, block in wanted:
    lines.append("=" * 120)
    lines.append(f"SCORE={score}")
    lines.append("REASONS=" + ", ".join(reasons))
    lines.append(block.strip())
    lines.append("")

OUT.write_text("\n".join(lines), encoding="utf-8")

print("SHORTLIST COMPLETE")
print(f"CANDIDATES={len(wanted)}")
print(f"OUTPUT={OUT}")
