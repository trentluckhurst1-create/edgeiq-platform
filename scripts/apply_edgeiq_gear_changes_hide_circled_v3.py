from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "edgeiq-os" / "race" / "components" / "MeetingGearChangesWorkspace.tsx"

text = path.read_text(encoding="utf-8")
original = text

targets = [
    "      <SummaryStrip model={model} />\n",
    "      <DataStatusPanel model={model} />\n",
]

removed = 0

for target in targets:
    if target in text:
        text = text.replace(target, "", 1)
        removed += 1

if removed == 0:
    print("EDGEIQ_GEAR_CHANGES_CIRCLED_CONTENT_ALREADY_REMOVED")
else:
    if "<SummaryStrip model={model} />" in text:
        raise RuntimeError("SummaryStrip render still remains.")

    if "<DataStatusPanel model={model} />" in text:
        raise RuntimeError("DataStatusPanel render still remains.")

    path.write_text(text, encoding="utf-8")

    print("EDGEIQ_GEAR_CHANGES_HIDE_CIRCLED_V3_APPLIED")
    print(f"render_blocks_removed={removed}")
    print(f"path={path}")
