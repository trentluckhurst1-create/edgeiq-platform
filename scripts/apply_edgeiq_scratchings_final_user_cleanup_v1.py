from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

meeting_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingWorkspace.tsx"
)

scratchings_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingScratchingsWorkspace.tsx"
)

css_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "styles"
    / "edgeiqOsV2.css"
)

meeting = meeting_path.read_text(encoding="utf-8")
scratchings = scratchings_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")

original_meeting = meeting
original_scratchings = scratchings


# ============================================================
# 1. REMOVE OFFICIAL UPDATE FROM MEETING CONDITION STRIP
# ============================================================

old_condition_map = '''      {conditionStrip.map((item) => (
        <div key={item.label} className={item.tone ? `is-${item.tone}` : ""}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
'''

new_condition_map = '''      {conditionStrip
        .filter((item) => item.label.trim().toUpperCase() !== "OFFICIAL UPDATE")
        .map((item) => (
          <div key={item.label} className={item.tone ? `is-${item.tone}` : ""}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
'''

count = meeting.count(old_condition_map)

if count != 1:
    raise RuntimeError(
        f"Expected one Meeting condition-strip map, found {count}. "
        "No files were written."
    )

meeting = meeting.replace(
    old_condition_map,
    new_condition_map,
    1,
)


# ============================================================
# 2. SIMPLIFY SCRATCHINGS TABLE PROPS
# ============================================================

old_table_signature = '''function ScratchingsTable({
  model,
  raceFilter,
  statusFilter,
  search,
  selectedKey,
  onSelect,
}: {
  model: MeetingScratchingsViewModel;
  raceFilter: string;
  statusFilter: string;
  search: string;
  selectedKey: string | null;
  onSelect: (record: ScratchingRecordViewModel) => void;
}) {
'''

new_table_signature = '''function ScratchingsTable({
  model,
  raceFilter,
  statusFilter,
  search,
}: {
  model: MeetingScratchingsViewModel;
  raceFilter: string;
  statusFilter: string;
  search: string;
}) {
'''

count = scratchings.count(old_table_signature)

if count != 1:
    raise RuntimeError(
        f"Expected one ScratchingsTable signature, found {count}. "
        "No files were written."
    )

scratchings = scratchings.replace(
    old_table_signature,
    new_table_signature,
    1,
)


# ============================================================
# 3. REMOVE RACE-HEADER FIELD/SCRATCHINGS TEXT
# ============================================================

old_group_header = '''          <header>
            <strong>R{group.raceNumber}</strong>
            <span>{group.raceName ?? "Race"}</span>
            <small>
              {valueOrUnavailable(group.scheduledTime)} / field {valueOrUnavailable(group.fieldSizeBefore)} to{" "}
              {valueOrUnavailable(group.fieldSizeAfter)} / {group.scratchingsCount} scratchings
            </small>
          </header>
'''

new_group_header = '''          <header>
            <strong>R{group.raceNumber}</strong>
            <span>{group.raceName ?? "Race"}</span>
          </header>
'''

count = scratchings.count(old_group_header)

if count != 1:
    raise RuntimeError(
        f"Expected one grouped-race header template, found {count}. "
        "No files were written."
    )

scratchings = scratchings.replace(
    old_group_header,
    new_group_header,
    1,
)


# ============================================================
# 4. REMOVE ROW SELECTION BEHAVIOUR
# ============================================================

old_row_open = '''                  <tr
                    key={record.eventKey}
                    className={record.eventKey === selectedKey ? "is-selected" : ""}
                    onClick={() => onSelect(record)}
                  >
'''

new_row_open = '''                  <tr key={record.eventKey}>
'''

count = scratchings.count(old_row_open)

if count != 1:
    raise RuntimeError(
        f"Expected one Scratchings row-selection block, found {count}. "
        "No files were written."
    )

scratchings = scratchings.replace(
    old_row_open,
    new_row_open,
    1,
)


# ============================================================
# 5. REMOVE ENTIRE IMPACT PANEL FUNCTION
# ============================================================

impact_start = scratchings.find(
    "function ImpactPanel({ record }: "
    "{ record: ScratchingRecordViewModel | null }) {"
)

if impact_start < 0:
    raise RuntimeError(
        "ImpactPanel function start was not found. No files were written."
    )

impact_end_marker = "\nfunction TimelinePanel("
impact_end = scratchings.find(
    impact_end_marker,
    impact_start,
)

if impact_end < 0:
    raise RuntimeError(
        "ImpactPanel function end boundary was not found. "
        "No files were written."
    )

scratchings = (
    scratchings[:impact_start]
    + scratchings[impact_end + 1:]
)


# ============================================================
# 6. REMOVE SELECTED SCRATCHING STATE
# ============================================================

selected_state = '''  const [selectedKey, setSelectedKey] = useState<string | null>(model.raceGroups[0]?.records[0]?.eventKey ?? null);

  const selectedRecord =
    model.raceGroups.flatMap((group) => group.records).find((record) => record.eventKey === selectedKey) ??
    model.raceGroups[0]?.records[0] ??
    null;

'''

count = scratchings.count(selected_state)

if count != 1:
    raise RuntimeError(
        f"Expected one selected scratching state block, found {count}. "
        "No files were written."
    )

scratchings = scratchings.replace(
    selected_state,
    "",
    1,
)


# ============================================================
# 7. REPLACE TWO-COLUMN GRID WITH FULL-WIDTH TABLE
# ============================================================

old_grid = '''      <div className="eiq-scratchings-v1-grid">
        <ScratchingsTable
          model={model}
          raceFilter={raceFilter}
          statusFilter={statusFilter}
          search={search}
          selectedKey={selectedRecord?.eventKey ?? null}
          onSelect={(record) => setSelectedKey(record.eventKey)}
        />
        <ImpactPanel record={selectedRecord} />
      </div>
'''

new_grid = '''      <ScratchingsTable
        model={model}
        raceFilter={raceFilter}
        statusFilter={statusFilter}
        search={search}
      />
'''

count = scratchings.count(old_grid)

if count != 1:
    raise RuntimeError(
        f"Expected one Scratchings table/impact grid, found {count}. "
        "No files were written."
    )

scratchings = scratchings.replace(
    old_grid,
    new_grid,
    1,
)


# ============================================================
# 8. VALIDATE BEFORE WRITING
# ============================================================

meeting_forbidden = (
    '.map((item) => (\n'
    '        <div key={item.label}'
)

if (
    '.filter((item) => item.label.trim().toUpperCase() !== "OFFICIAL UPDATE")'
    not in meeting
):
    raise RuntimeError(
        "Official Update condition filter was not installed."
    )

for forbidden in (
    "function ImpactPanel",
    "<ImpactPanel",
    "SELECTED SCRATCHING IMPACT",
    "selectedKey",
    "selectedRecord",
    "setSelectedKey",
    "onSelect(record)",
    "field {valueOrUnavailable(group.fieldSizeBefore)}",
    "{group.scratchingsCount} scratchings",
):
    if forbidden in scratchings:
        raise RuntimeError(
            f"Scratchings cleanup validation failed: {forbidden}"
        )

if meeting == original_meeting:
    raise RuntimeError(
        "No MeetingWorkspace change was produced."
    )

if scratchings == original_scratchings:
    raise RuntimeError(
        "No MeetingScratchingsWorkspace change was produced."
    )


# ============================================================
# 9. CSS: FORCE FULL-WIDTH SCRATCHINGS TABLE
# ============================================================

css_marker = "/* EDGEIQ SCRATCHINGS FINAL USER CLEANUP V1 */"

css_block = r'''

/* EDGEIQ SCRATCHINGS FINAL USER CLEANUP V1 */
.eiq-scratchings-v1-grid {
  display: block;
}

.eiq-scratchings-v1-table-card {
  width: 100%;
  min-width: 0;
}

.eiq-scratchings-v1-table {
  width: 100%;
  table-layout: fixed;
}

.eiq-scratchings-v1-race-group > header {
  grid-template-columns: auto minmax(0, 1fr);
}

.eiq-scratchings-v1-race-group > header small {
  display: none;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"


# Write only after every validation passes.
meeting_path.write_text(meeting, encoding="utf-8")
scratchings_path.write_text(scratchings, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("EDGEIQ_SCRATCHINGS_FINAL_USER_CLEANUP_V1_APPLIED")
print("removed=OFFICIAL_UPDATE_CONDITION_CARD")
print("removed=RACE_HEADER_FIELD_CHANGE_TEXT")
print("removed=SELECTED_SCRATCHING_IMPACT")
print("removed=ROW_SELECTION_BEHAVIOUR")
print("scratchings_table=FULL_WIDTH")
print(f"meeting={meeting_path}")
print(f"scratchings={scratchings_path}")
print(f"css={css_path}")
