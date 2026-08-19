from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TARGET = ROOT / "scripts" / "build_edgeiq_three_day_product_catalog_v1.py"
OUTPUT = ROOT / "docs" / "three_day_product_catalog_builder_focus_v1.txt"

if not TARGET.exists():
    raise SystemExit(f"MISSING={TARGET}")

lines = TARGET.read_text(encoding="utf-8-sig").splitlines()

ranges = [
    (1, 230, "IMPORTS, INPUTS, OUTPUTS, FIELD ALIASES"),
    (230, 430, "ROW HELPERS, NESTED FIELD EXTRACTION, SILKS"),
    (430, 610, "SOURCE DISCOVERY AND RUNNER INPUT ASSEMBLY"),
    (610, 710, "OFFICIAL RUNNER OBJECT CONSTRUCTION"),
    (710, 850, "RACE AND MEETING ASSEMBLY"),
    (1080, 1210, "FINAL PAYLOAD, AUDIT AND WRITE"),
]

out = []

for start, end, title in ranges:
    out.append("")
    out.append("=" * 120)
    out.append(title)
    out.append(f"LINES {start}-{end}")
    out.append("=" * 120)

    for number in range(start, min(end, len(lines)) + 1):
        out.append(f"{number:04d}: {lines[number - 1]}")

keywords = [
    "read_csv",
    "read_json",
    "json.load",
    "glob(",
    "rglob(",
    "race_fields",
    "official",
    "runner_rows",
    "field_rows",
    "entries",
    "runners",
    "source",
    "TRAINER_KEYS",
    "JOCKEY_KEYS",
    "BARRIER_KEYS",
    "WEIGHT_KEYS",
]

out.append("")
out.append("=" * 120)
out.append("KEYWORD INDEX")
out.append("=" * 120)

for number, line in enumerate(lines, start=1):
    if any(keyword.lower() in line.lower() for keyword in keywords):
        out.append(f"{number:04d}: {line}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(out) + "\n", encoding="utf-8")

print("\n".join(out))
print("")
print(f"OUTPUT={OUTPUT}")
print("THREE_DAY_PRODUCT_CATALOG_BUILDER_FOCUS_V1_COMPLETE")
