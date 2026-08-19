from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"

text = path.read_text(encoding="utf-8")
original = text

replacements = [
    (
        "        <DetailGrid details={model.summary} />\n",
        "",
        "header summary grid",
    ),
    (
        "      <SummaryStrip items={model.summary} />\n",
        "",
        "duplicate summary strip",
    ),
    (
        "              <th>STATUS</th>\n",
        "",
        "status heading",
    ),
    (
        "                <td className={`is-${row.statusTone}`}>{row.status}</td>\n",
        "",
        "status cell",
    ),
    (
        "        <OperationalRail model={model} />\n",
        "",
        "operational rail render",
    ),
]

for old, new, label in replacements:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label}, found {count}. No file was written."
        )
    text = text.replace(old, new, 1)

function_start_marker = (
    "function OperationalRail({ model }: "
    "{ model: ReturnType<typeof buildMeetingDetailViewModel> }) {\n"
)

start = text.find(function_start_marker)

if start == -1:
    raise RuntimeError(
        "OperationalRail function start not found. No file was written."
    )

end_marker = "\nexport function MeetingWorkspace("
end = text.find(end_marker, start)

if end == -1:
    raise RuntimeError(
        "OperationalRail function end boundary not found. No file was written."
    )

text = text[:start] + text[end + 1:]

for forbidden in (
    "<DetailGrid details={model.summary} />",
    "<SummaryStrip items={model.summary} />",
    "<th>STATUS</th>",
    "{row.status}",
    "function OperationalRail",
    "<OperationalRail model={model} />",
    "Meeting Highlights",
    "Data Freshness",
    "EDGEiQ Notes",
):
    if forbidden in text:
        raise RuntimeError(
            f"Validation failed; source still contains: {forbidden}"
        )

if text == original:
    raise RuntimeError("No source changes were produced.")

path.write_text(text, encoding="utf-8")

print("EDGEIQ_MEETING_WORKSPACE_USER_CLEANUP_V3_APPLIED")
print("removed=header_summary_grid")
print("removed=duplicate_summary_strip")
print("removed=operational_rail")
print("removed=status_column")
print(f"path={path}")
