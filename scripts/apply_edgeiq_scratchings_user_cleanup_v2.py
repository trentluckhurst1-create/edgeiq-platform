from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
PATH = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingScratchingsWorkspace.tsx"

text = PATH.read_text(encoding="utf-8")
original = text


def function_block(source: str, start_marker: str, end_marker: str) -> tuple[int, int, str]:
    start = source.find(start_marker)

    if start < 0:
        raise RuntimeError(f"Function start not found: {start_marker}")

    end = source.find(end_marker, start)

    if end < 0:
        raise RuntimeError(f"Function end boundary not found: {end_marker}")

    return start, end, source[start:end]


# ------------------------------------------------------------
# 1. Edit SummaryStrip only.
# ------------------------------------------------------------
summary_start, summary_end, summary = function_block(
    text,
    "function SummaryStrip(",
    "\nfunction ScratchingsFilters(",
)

summary_removals = [
    '    ["RACES AFFECTED", model.summary.racesAffected],\n',
    '    [`NEW SINCE ${model.summary.newSinceLabel ?? "UNAVAILABLE"}`, model.summary.newSinceCount],\n',
    '    ["FIELDS MATERIALLY CHANGED", model.summary.materiallyChangedFields],\n',
    '    ["EMERGENCIES PROMOTED", model.summary.emergenciesPromoted],\n',
    '    ["LATEST UPDATE", formatDateTime(model.officialUpdatedAt)],\n',
]

for line in summary_removals:
    count = summary.count(line)

    if count != 1:
        raise RuntimeError(
            f"Expected one summary line, found {count}: {line.strip()}"
        )

    summary = summary.replace(line, "", 1)

if '["TOTAL SCRATCHINGS", model.summary.totalScratchings]' not in summary:
    raise RuntimeError("TOTAL SCRATCHINGS was unexpectedly removed.")

text = text[:summary_start] + summary + text[summary_end:]


# ------------------------------------------------------------
# 2. Edit ScratchingsTable only.
# ------------------------------------------------------------
table_start, table_end, table = function_block(
    text,
    "function ScratchingsTable(",
    "\nfunction ImpactPanel(",
)

table_removals = [
    '                  <th>SCRATCHED AT</th>\n',
    '                  <th className="is-left">REASON</th>\n',
    '                  <th className="is-left">SOURCE</th>\n',
    '                  <th>STATUS</th>\n',
    '                    <td>{record.scratchedAtDisplay}</td>\n',
    '                    <td className="is-left">{valueOrUnavailable(record.reason)}</td>\n',
    '                    <td className="is-left">{valueOrUnavailable(record.source)}</td>\n',
    '''                    <td>
                      <span className={`eiq-scratchings-v1-status is-${record.status.toLowerCase()}`}>
                        {statusLabel(record.status)}
                      </span>
                    </td>
''',
]

for block in table_removals:
    count = table.count(block)

    if count != 1:
        raise RuntimeError(
            f"Expected one ScratchingsTable block, found {count}: "
            f"{block.strip()[:100]}"
        )

    table = table.replace(block, "", 1)

required_headings = [
    "<th>RACE</th>",
    "<th>NO</th>",
    "<th>SILK</th>",
    '<th className="is-left">HORSE</th>',
    '<th className="is-left">TRAINER</th>',
    '<th className="is-left">JOCKEY</th>',
]

for heading in required_headings:
    if heading not in table:
        raise RuntimeError(f"Required heading was lost: {heading}")

for forbidden in [
    "<th>SCRATCHED AT</th>",
    '<th className="is-left">REASON</th>',
    '<th className="is-left">SOURCE</th>',
    "<th>STATUS</th>",
    "{record.scratchedAtDisplay}",
    "valueOrUnavailable(record.reason)",
    "valueOrUnavailable(record.source)",
    "eiq-scratchings-v1-status",
]:
    if forbidden in table:
        raise RuntimeError(
            f"ScratchingsTable validation failed; still contains: {forbidden}"
        )

text = text[:table_start] + table + text[table_end:]


# ------------------------------------------------------------
# 3. Validate only the intended areas.
# ------------------------------------------------------------
_, _, final_summary = function_block(
    text,
    "function SummaryStrip(",
    "\nfunction ScratchingsFilters(",
)

for forbidden in [
    "RACES AFFECTED",
    "NEW SINCE",
    "FIELDS MATERIALLY CHANGED",
    "EMERGENCIES PROMOTED",
    "LATEST UPDATE",
]:
    if forbidden in final_summary:
        raise RuntimeError(
            f"Summary validation failed; still contains: {forbidden}"
        )

if text == original:
    raise RuntimeError("No source changes were produced.")

PATH.write_text(text, encoding="utf-8")

print("EDGEIQ_SCRATCHINGS_USER_CLEANUP_V2_APPLIED")
print("summary_remaining=TOTAL_SCRATCHINGS")
print("columns_remaining=RACE,NO,SILK,HORSE,TRAINER,JOCKEY")
print(f"path={PATH}")
