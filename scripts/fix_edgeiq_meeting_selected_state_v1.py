from pathlib import Path
import re

path = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\race\components\MeetingWorkspace.tsx")

text = path.read_text(encoding="utf-8")
original = text

# ----------------------------------------------------------
# Ensure buildMeetingDetailSelectedRace is imported
# ----------------------------------------------------------

if "buildMeetingDetailSelectedRace" not in text:

    m = re.search(
        r'import\s*\{(.*?)\}\s*from\s*"../services/meetingDetailFeed";',
        text,
        flags=re.S,
    )

    if not m:
        raise RuntimeError("meetingDetailFeed import block not found.")

    imports = m.group(1)

    imports = imports.rstrip()

    imports += ",\n  buildMeetingDetailSelectedRace"

    replacement = (
        "import {\n"
        + imports.strip()
        + "\n} from \"../services/meetingDetailFeed\";"
    )

    text = text[:m.start()] + replacement + text[m.end():]

# ----------------------------------------------------------
# Remove broken selected declaration
# ----------------------------------------------------------

text = re.sub(
    r'''
    \n\s*const\s+selected\s*=
    \s*model\.races\.find\(.*?
    \?\?\s*null;
    ''',
    "",
    text,
    flags=re.S | re.X,
)

# ----------------------------------------------------------
# Insert correct selected useMemo
# ----------------------------------------------------------

marker = re.search(
    r'''
    const\s+\[selectedRaceKey,\s*setSelectedRaceKey\]
    .*?;
    ''',
    text,
    flags=re.S | re.X,
)

if not marker:
    raise RuntimeError("selectedRaceKey declaration not found.")

selected_block = '''

  const selected = useMemo(
    () =>
      buildMeetingDetailSelectedRace(
        model,
        meeting,
        selectedRaceKey,
      ),
    [model, meeting, selectedRaceKey],
  );

'''

insert_at = marker.end()

text = text[:insert_at] + selected_block + text[insert_at:]

# ----------------------------------------------------------
# Validation
# ----------------------------------------------------------

if "model.races.find((row)" in text:
    raise RuntimeError("Broken selected lookup still exists.")

if "buildMeetingDetailSelectedRace(" not in text:
    raise RuntimeError("Selected builder was not installed.")

if "const selected = useMemo(" not in text:
    raise RuntimeError("Selected useMemo missing.")

if text == original:
    raise RuntimeError("No changes were made.")

path.write_text(text, encoding="utf-8")

print("EDGEIQ_MEETING_SELECTED_REPAIR_APPLIED")
print(path)
