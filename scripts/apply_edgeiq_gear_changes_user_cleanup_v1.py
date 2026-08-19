from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

PATH = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingGearChangesWorkspace.tsx"
)

text = PATH.read_text(encoding="utf-8")
original = text


def remove_function(
    source: str,
    start_marker: str,
    next_marker: str,
    label: str,
) -> str:
    start = source.find(start_marker)

    if start < 0:
        raise RuntimeError(
            f"{label} function start was not found. No file was written."
        )

    end = source.find(next_marker, start)

    if end < 0:
        raise RuntimeError(
            f"{label} function end boundary was not found. No file was written."
        )

    return source[:start] + source[end + 1:]


# ------------------------------------------------------------
# 1. Remove SummaryStrip render.
# ------------------------------------------------------------
summary_render = "      <SummaryStrip model={model} />\n"

count = text.count(summary_render)

if count != 1:
    raise RuntimeError(
        f"Expected one Gear Changes SummaryStrip render, found {count}. "
        "No file was written."
    )

text = text.replace(summary_render, "", 1)


# ------------------------------------------------------------
# 2. Remove DataStatusPanel render.
# ------------------------------------------------------------
data_status_render = "      <DataStatusPanel model={model} />\n"

count = text.count(data_status_render)

if count != 1:
    raise RuntimeError(
        f"Expected one Gear Changes DataStatusPanel render, found {count}. "
        "No file was written."
    )

text = text.replace(data_status_render, "", 1)


# ------------------------------------------------------------
# 3. Remove SummaryStrip function.
# ------------------------------------------------------------
text = remove_function(
    text,
    "function SummaryStrip(",
    "\nfunction GearChangesFilters(",
    "SummaryStrip",
)


# ------------------------------------------------------------
# 4. Remove DataStatusPanel function.
# ------------------------------------------------------------
data_start = text.find("function DataStatusPanel(")

if data_start < 0:
    raise RuntimeError(
        "DataStatusPanel function start was not found. No file was written."
    )

export_marker = "\nexport function MeetingGearChangesWorkspace("
data_end = text.find(export_marker, data_start)

if data_end < 0:
    raise RuntimeError(
        "DataStatusPanel function end boundary was not found. "
        "No file was written."
    )

text = text[:data_start] + text[data_end + 1:]


# ------------------------------------------------------------
# 5. Validate before writing.
# ------------------------------------------------------------
for forbidden in (
    "function SummaryStrip(",
    "<SummaryStrip",
    "function DataStatusPanel(",
    "<DataStatusPanel",
    "eiq-gear-v1-summary-strip",
    "DATA FRESHNESS",
    "Gear source monitored",
    "LOADED ROWS",
    "MATCHED ROWS",
    "WORKSPACE",
):
    if forbidden in text:
        raise RuntimeError(
            f"Gear Changes cleanup validation failed: {forbidden}"
        )

for required in (
    "Official gear changes and equipment updates",
    "GearChangesFilters",
):
    if required not in text:
        raise RuntimeError(
            f"Required Gear Changes content was unexpectedly lost: {required}"
        )

if text == original:
    raise RuntimeError("No Gear Changes source changes were produced.")

PATH.write_text(text, encoding="utf-8")

print("EDGEIQ_GEAR_CHANGES_USER_CLEANUP_V1_APPLIED")
print("removed=SUMMARY_CARDS")
print("removed=DATA_FRESHNESS_PANEL")
print(f"path={PATH}")
