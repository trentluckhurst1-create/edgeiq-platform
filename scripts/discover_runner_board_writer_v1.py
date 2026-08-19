from pathlib import Path
import re
import sys

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "runner_board_writer_discovery_v1.txt"

SKIP = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".vite",
    "__pycache__",
    "checkpoints",
}

WRITE_PATTERNS = [
    r"edgeiq_live_runner_board_v1\.csv",
    r"edgeiq_live_runner_board_governed_v1\.csv",
    r"\.to_csv\(",
    r"DictWriter",
    r"writerows\(",
    r"write_csv\(",
    r'open\s*\(.*["' + "'" + r']w["' + "'" + r']',
]

def skip(path):
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        return True
    return any(part in SKIP for part in rel.parts)

report = []
report.append("="*120)
report.append("EDGEIQ RUNNER BOARD WRITER DISCOVERY")
report.append("="*120)

matches = 0

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    if skip(path):
        continue

    if path.suffix.lower() not in (".py", ".ps1"):
        continue

    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        continue

    lower = text.lower()

    if (
        "edgeiq_live_runner_board_v1.csv" not in lower and
        "edgeiq_live_runner_board_governed_v1.csv" not in lower
    ):
        continue

    report.append("")
    report.append("="*120)
    report.append(f"FILE: {path.relative_to(ROOT)}")

    lines = text.splitlines()

    interesting = []

    for i,line in enumerate(lines,1):
        l=line.lower()

        if (
            "edgeiq_live_runner_board_v1.csv" in l or
            "edgeiq_live_runner_board_governed_v1.csv" in l or
            "to_csv(" in l or
            "dictwriter" in l or
            "writerows(" in l or
            "write_csv(" in l or
            ".open(" in l
        ):
            interesting.append(i)

    interesting = sorted(set(interesting))

    for line_no in interesting[:40]:
        matches += 1

        report.append("")
        report.append(f"LINE {line_no}")

        start=max(1,line_no-5)
        end=min(len(lines),line_no+10)

        for j in range(start,end+1):
            report.append(f"{j:05d}: {lines[j-1]}")

report.append("")
report.append("="*120)
report.append(f"MATCHES={matches}")

OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text("\n".join(report),encoding="utf-8")

sys.stdout.reconfigure(encoding="utf-8",errors="replace")

print("DISCOVERY COMPLETE")
print(f"MATCHES={matches}")
print(f"OUTPUT={OUT}")
