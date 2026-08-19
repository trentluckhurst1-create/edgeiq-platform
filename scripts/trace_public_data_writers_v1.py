from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SCRIPTS = ROOT / "scripts"
OUT = ROOT / "docs" / "public_data_writer_trace_v1.txt"

KEYWORDS = [
    "public/data",
    "public\\data",
    "to_csv(",
    "Path(",
    "write_csv(",
    "DictWriter",
    "writerows(",
    "OUTPUT",
    "OUT =",
    "OUT=",
]

report = []
report.append("="*120)
report.append("PUBLIC DATA WRITER TRACE")
report.append("="*120)

hits = 0

for path in sorted(SCRIPTS.glob("*.py")):

    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        continue

    lower = text.lower()

    if (
        "public/data" not in lower
        and "public\\data" not in lower
        and "to_csv(" not in lower
    ):
        continue

    report.append("")
    report.append("="*120)
    report.append(f"FILE={path.name}")

    lines = text.splitlines()

    interesting = []

    for i, line in enumerate(lines, 1):

        l = line.lower()

        if (
            "public/data" in l or
            "public\\data" in l or
            "to_csv(" in l or
            "dictwriter" in l or
            "writerows(" in l or
            "write_csv(" in l or
            "out =" in l or
            "out=" in l
        ):
            interesting.append(i)

    interesting = sorted(set(interesting))

    for line_no in interesting[:50]:

        hits += 1

        report.append("")
        report.append(f"LINE {line_no}")

        start = max(1, line_no - 8)
        end = min(len(lines), line_no + 15)

        for j in range(start, end + 1):
            report.append(f"{j:05d}: {lines[j-1]}")

report.append("")
report.append("="*120)
report.append(f"TOTAL MATCHES={hits}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print(f"Report written to {OUT}")
print(f"Total matches: {hits}")
