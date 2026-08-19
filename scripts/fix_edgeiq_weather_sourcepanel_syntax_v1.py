from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
PATH = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingWeatherWorkspace.tsx"
)

text = PATH.read_text(encoding="utf-8")
original = text

broken_block = '''function SourcePanel({ model }: { model: MeetingWeatherViewModel }) {
  return (
      );
}

'''

count = text.count(broken_block)

if count != 1:
    raise RuntimeError(
        f"Expected one broken SourcePanel block, found {count}. "
        "No file was written."
    )

text = text.replace(
    broken_block,
    "",
    1,
)

if "function SourcePanel(" in text:
    raise RuntimeError(
        "SourcePanel still remains after syntax repair."
    )

if text == original:
    raise RuntimeError(
        "No Weather syntax repair was produced."
    )

PATH.write_text(
    text,
    encoding="utf-8",
)

print("EDGEIQ_WEATHER_SOURCEPANEL_SYNTAX_FIX_V1_APPLIED")
print("removed=BROKEN_SOURCE_PANEL_FUNCTION")
print(f"path={PATH}")
