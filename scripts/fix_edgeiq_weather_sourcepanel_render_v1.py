from pathlib import Path

path = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
) / "src" / "edgeiq-os" / "race" / "components" / "MeetingWeatherWorkspace.tsx"

text = path.read_text(encoding="utf-8")
original = text

target = "        <SourcePanel model={model} />\n"

count = text.count(target)

if count != 1:
    raise RuntimeError(
        f"Expected exactly one SourcePanel render, found {count}. "
        "No file was written."
    )

text = text.replace(target, "", 1)

if "SourcePanel" in text:
    raise RuntimeError(
        "SourcePanel reference still remains. No file was written."
    )

if text == original:
    raise RuntimeError("No Weather source change was produced.")

path.write_text(text, encoding="utf-8")

print("EDGEIQ_WEATHER_SOURCEPANEL_RENDER_FIX_V1_APPLIED")
print("removed=SOURCE_PANEL_RENDER")
print(f"path={path}")
