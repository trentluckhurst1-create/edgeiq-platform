from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingScratchingsWorkspace.tsx"
)

text = path.read_text(encoding="utf-8")
original = text

replacements = [
    (
        '    ["RACES AFFECTED", model.summary.racesAffected],\n',
        "",
        "Races Affected summary card",
    ),
    (
        '    [`NEW SINCE ${model.summary.newSinceLabel ?? "UNAVAILABLE"}`, model.summary.newSinceCount],\n',
        "",
        "New Since summary card",
    ),
    (
        '    ["FIELDS MATERIALLY CHANGED", model.summary.materiallyChangedFields],\n',
        "",
        "Fields Materially Changed summary card",
    ),
    (
        '    ["EMERGENCIES PROMOTED", model.summary.emergenciesPromoted],\n',
        "",
        "Emergencies Promoted summary card",
    ),
    (
        '    ["LATEST UPDATE", formatDateTime(model.officialUpdatedAt)],\n',
        "",
        "Latest Update summary card",
    ),
    (
        '                  <th>SCRATCHED AT</th>\n',
        "",
        "Scratched At heading",
    ),
    (
        '                  <th className="is-left">REASON</th>\n',
        "",
        "Reason heading",
    ),
    (
        '                  <th className="is-left">SOURCE</th>\n',
        "",
        "Source heading",
    ),
    (
        '                  <th>STATUS</th>\n',
        "",
        "Status heading",
    ),
    (
        '                    <td>{record.scratchedAtDisplay}</td>\n',
        "",
        "Scratched At cell",
    ),
    (
        '                    <td className="is-left">{valueOrUnavailable(record.reason)}</td>\n',
        "",
        "Reason cell",
    ),
    (
        '                    <td className="is-left">{valueOrUnavailable(record.source)}</td>\n',
        "",
        "Source cell",
    ),
    (
        '''                    <td>
                      <span className={`eiq-scratchings-v1-status is-${record.status.toLowerCase()}`}>
                        {statusLabel(record.status)}
                      </span>
                    </td>
''',
        "",
        "Status cell",
    ),
]

for old, new, label in replacements:
    count = text.count(old)

    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label}, found {count}. "
            "No file was written."
        )

    text = text.replace(old, new, 1)

for forbidden in (
    '["RACES AFFECTED", model.summary.racesAffected]',
    'NEW SINCE ${model.summary.newSinceLabel',
    '["FIELDS MATERIALLY CHANGED", model.summary.materiallyChangedFields]',
    '["EMERGENCIES PROMOTED", model.summary.emergenciesPromoted]',
    '["LATEST UPDATE", formatDateTime(model.officialUpdatedAt)]',
    "<th>SCRATCHED AT</th>",
    '<th className="is-left">REASON</th>',
    '<th className="is-left">SOURCE</th>',
    "<th>STATUS</th>",
    "{record.scratchedAtDisplay}",
    "valueOrUnavailable(record.reason)",
    "valueOrUnavailable(record.source)",
    "eiq-scratchings-v1-status is-${record.status.toLowerCase()}",
):
    if forbidden in text:
        raise RuntimeError(
            f"Validation failed; source still contains: {forbidden}"
        )

required = (
    '["TOTAL SCRATCHINGS", model.summary.totalScratchings]',
    "<th>RACE</th>",
    "<th>NO</th>",
    "<th>SILK</th>",
    '<th className="is-left">HORSE</th>',
    '<th className="is-left">TRAINER</th>',
    '<th className="is-left">JOCKEY</th>',
)

for item in required:
    if item not in text:
        raise RuntimeError(
            f"Required Scratchings content was unexpectedly lost: {item}"
        )

if text == original:
    raise RuntimeError("No source changes were produced.")

path.write_text(text, encoding="utf-8")

print("EDGEIQ_SCRATCHINGS_USER_CLEANUP_V1_APPLIED")
print("summary_remaining=TOTAL_SCRATCHINGS")
print("columns_remaining=RACE,NO,SILK,HORSE,TRAINER,JOCKEY")
print(f"path={path}")
