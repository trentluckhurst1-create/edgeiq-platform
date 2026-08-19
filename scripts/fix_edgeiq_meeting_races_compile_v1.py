from pathlib import Path
import re

path = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
) / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"

text = path.read_text(encoding="utf-8")
original = text

# Fix race-number display using the field that actually exists.
old_race_number = "<td>{row.raceNumber}</td>"
new_race_number = '<td>{row.raceLabel.replace(/^R/i, "")}</td>'

count = text.count(old_race_number)

if count != 1:
    raise RuntimeError(
        f"Expected one invalid raceNumber render, found {count}. "
        "No file was written."
    )

text = text.replace(
    old_race_number,
    new_race_number,
    1,
)

# Restore selected race lookup only if it is currently missing.
if re.search(r"\bconst\s+selected\s*=", text) is None:
    model_marker = re.search(
        r'''
        (?P<block>
        ^[ \t]*const\s+model\s*=\s*useMemo\(
        .*?
        ^[ \t]*\);\s*$
        )
        ''',
        text,
        flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
    )

    if model_marker is None:
        raise RuntimeError(
            "Could not locate the Meeting Detail model useMemo block. "
            "No file was written."
        )

    selected_block = '''

  const selected =
    model.races.find((row) => row.raceKey === selectedRaceKey) ??
    model.races[0] ??
    null;
'''

    insert_at = model_marker.end()
    text = text[:insert_at] + selected_block + text[insert_at:]

# Validate.
if "<td>{row.raceNumber}</td>" in text:
    raise RuntimeError("Invalid raceNumber render still remains.")

if '<td>{row.raceLabel.replace(/^R/i, "")}</td>' not in text:
    raise RuntimeError("Numeric race-label render was not installed.")

if re.search(r"\bconst\s+selected\s*=", text) is None:
    raise RuntimeError("Selected race lookup was not restored.")

if text == original:
    raise RuntimeError("No compile repair was produced.")

path.write_text(text, encoding="utf-8")

print("EDGEIQ_MEETING_RACES_COMPILE_FIX_V1_APPLIED")
print("fixed=RACE_NUMBER_FROM_RACE_LABEL")
print("restored=SELECTED_RACE_LOOKUP")
print(f"path={path}")
