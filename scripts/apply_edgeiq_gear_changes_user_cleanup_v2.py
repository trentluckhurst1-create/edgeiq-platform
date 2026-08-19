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

# Remove the two live render calls first.
for render, label in (
    ("      <SummaryStrip model={model} />\n", "SummaryStrip render"),
    ("      <DataStatusPanel model={model} />\n", "DataStatusPanel render"),
):
    count = text.count(render)

    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label}, found {count}. "
            "No file was written."
        )

    text = text.replace(render, "", 1)

# Remove SummaryStrip from its confirmed start to DataStatusPanel.
summary_start = text.find("function SummaryStrip(")
data_status_start = text.find("function DataStatusPanel(")

if summary_start < 0:
    raise RuntimeError("SummaryStrip start not found. No file was written.")

if data_status_start < 0:
    raise RuntimeError("DataStatusPanel start not found. No file was written.")

if data_status_start <= summary_start:
    raise RuntimeError(
        "Confirmed Gear Changes function order is invalid. "
        "No file was written."
    )

text = text[:summary_start] + text[data_status_start:]

# Remove DataStatusPanel from its confirmed start to the exported workspace.
data_status_start = text.find("function DataStatusPanel(")
workspace_start = text.find("export function MeetingGearChangesWorkspace(")

if data_status_start < 0:
    raise RuntimeError(
        "DataStatusPanel start was lost before removal. "
        "No file was written."
    )

if workspace_start < 0:
    raise RuntimeError(
        "MeetingGearChangesWorkspace export not found. "
        "No file was written."
    )

if workspace_start <= data_status_start:
    raise RuntimeError(
        "Confirmed DataStatusPanel/workspace order is invalid. "
        "No file was written."
    )

text = text[:data_status_start] + text[workspace_start:]

# Validate only the requested removals.
for forbidden in (
    "function SummaryStrip(",
    "<SummaryStrip",
    "function DataStatusPanel(",
    "<DataStatusPanel",
    "eiq-gear-v1-summary-strip",
    "DATA FRESHNESS",
    "Gear source monitored",
    "Official gear records matched",
    '["Loaded Rows", model.source.loadedRows]',
    '["Matched Rows", model.source.matchedRows]',
    '["Workspace", model.workspaceId]',
):
    if forbidden in text:
        raise RuntimeError(
            f"Gear Changes cleanup validation failed: {forbidden}"
        )

# Preserve the actual user-facing workspace.
for required in (
    "Official gear changes and equipment updates",
    "export function MeetingGearChangesWorkspace(",
    "ALL RACES",
    "SEARCH HORSE / CHANGE",
):
    if required not in text:
        raise RuntimeError(
            f"Required Gear Changes content was unexpectedly lost: {required}"
        )

if text == original:
    raise RuntimeError("No Gear Changes source changes were produced.")

PATH.write_text(text, encoding="utf-8")

print("EDGEIQ_GEAR_CHANGES_USER_CLEANUP_V2_APPLIED")
print("removed=SUMMARY_STRIP")
print("removed=DATA_STATUS_PANEL")
print(f"path={PATH}")
