from pathlib import Path

path = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\race\components\MeetingWorkspace.tsx"
)

text = path.read_text(encoding="utf-8")
original = text

# ------------------------------------------------------------------
# Install label formatter once.
# ------------------------------------------------------------------

helper = '''
function formatMeetingConditionLabel(label: string): string {
  switch (label.trim().toUpperCase()) {
    case "TEMPERATURE":
      return "TEMP";

    case "RAIN 24H":
      return "RAIN";

    case "IRRIGATION 24H":
      return "IRRIGATION";

    default:
      return label;
  }
}

'''

marker = "function MeetingConditionStrip("

if "function formatMeetingConditionLabel(" not in text:

    pos = text.find(marker)

    if pos < 0:
        raise RuntimeError("MeetingConditionStrip not found.")

    text = text[:pos] + helper + text[pos:]

old = "<span>{item.label}</span>"
new = "<span>{formatMeetingConditionLabel(item.label)}</span>"

count = text.count(old)

if count != 1:
    raise RuntimeError(
        f"Expected one MeetingConditionStrip label render, found {count}."
    )

text = text.replace(
    old,
    new,
    1,
)

if text == original:
    raise RuntimeError("No Meeting changes were made.")

path.write_text(
    text,
    encoding="utf-8",
)

print("EDGEIQ_MEETING_LABEL_RENDER_PATCH_APPLIED")
print(path)
