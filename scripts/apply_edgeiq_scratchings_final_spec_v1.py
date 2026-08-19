from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT_DIR = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"SCRATCHINGS_FINAL_SPEC_V1_{STAMP}"

COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingScratchingsWorkspace.tsx"
MEETING_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "scratchingsFeed.ts"
CSS_FILE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE_FILE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_SCRATCHINGS_TRACE_V1.md"
AUDIT_SCRIPT = ROOT / "scripts" / "audit_edgeiq_scratchings_final_spec_v1.py"


COMPONENT_SOURCE = r'''import { useMemo, useState } from "react";
import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import {
  buildMeetingScratchingsViewModel,
  type MeetingScratchingsViewModel,
  type ScratchingRecordViewModel,
} from "../services/scratchingsFeed";

type MeetingScratchingsWorkspaceProps = {
  meeting: ThreeDayMeeting;
};

const ALL_RACES = "ALL_RACES";
const ALL_STATUS = "ALL_STATUS";

function valueOrUnavailable(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined || value === "") return "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function formatDateTime(value: string | null): string {
  if (!value) return "Unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-AU", {
    day: "2-digit",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Sydney",
  })
    .format(parsed)
    .replace(/\s/g, " ");
}

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

function rowStatusClass(record: ScratchingRecordViewModel): string {
  if (["SCRATCHED", "LATE_SCRATCHING", "WITHDRAWN", "EMERGENCY_NOT_REQUIRED"].includes(record.status)) {
    return "is-scratched";
  }
  if (record.status === "EMERGENCY_PROMOTED") return "is-promoted";
  return "";
}

function SummaryStrip({ model }: { model: MeetingScratchingsViewModel }) {
  const summary = [
    ["TOTAL SCRATCHINGS", model.summary.totalScratchings],
    ["RACES AFFECTED", model.summary.racesAffected],
    ["EMERGENCIES", model.summary.emergenciesPromoted],
  ];

  return (
    <section className="eiq-scratchings-v1-summary-strip" aria-label="Scratchings summary">
      {summary.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{valueOrUnavailable(value)}</strong>
        </div>
      ))}
    </section>
  );
}

function ScratchingsFilters({
  model,
  raceFilter,
  statusFilter,
  search,
  onRaceFilter,
  onStatusFilter,
  onSearch,
}: {
  model: MeetingScratchingsViewModel;
  raceFilter: string;
  statusFilter: string;
  search: string;
  onRaceFilter: (value: string) => void;
  onStatusFilter: (value: string) => void;
  onSearch: (value: string) => void;
}) {
  const statuses = Array.from(new Set(model.raceGroups.flatMap((group) => group.records.map((record) => record.status))));

  return (
    <section className="eiq-scratchings-v1-filters" aria-label="Scratchings filters">
      <label>
        <span>RACE</span>
        <select value={raceFilter} onChange={(event) => onRaceFilter(event.target.value)}>
          <option value={ALL_RACES}>ALL RACES</option>
          {model.raceGroups.map((group) => (
            <option key={group.raceKey} value={group.raceKey}>
              R{group.raceNumber}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>STATUS</span>
        <select value={statusFilter} onChange={(event) => onStatusFilter(event.target.value)}>
          <option value={ALL_STATUS}>ALL STATUS</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {statusLabel(status)}
            </option>
          ))}
        </select>
      </label>
      <label className="is-search">
        <span>SEARCH HORSE / TRAINER / JOCKEY</span>
        <input
          value={search}
          placeholder="SEARCH HORSE / TRAINER / JOCKEY"
          onChange={(event) => onSearch(event.target.value)}
        />
      </label>
    </section>
  );
}

function rowMatchesSearch(record: ScratchingRecordViewModel, search: string): boolean {
  if (!search.trim()) return true;
  const needle = search.trim().toLowerCase();
  return [record.horse, record.trainer, record.jockey].some((value) => String(value ?? "").toLowerCase().includes(needle));
}

function ScratchingsTable({
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
  const groups = model.raceGroups
    .filter((group) => raceFilter === ALL_RACES || group.raceKey === raceFilter)
    .map((group) => ({
      ...group,
      records: group.records.filter(
        (record) =>
          (statusFilter === ALL_STATUS || record.status === statusFilter) && rowMatchesSearch(record, search),
      ),
    }))
    .filter((group) => group.records.length > 0);

  if (!groups.length) {
    const message = model.sourceUnavailable
      ? "Official scratchings data is currently unavailable."
      : model.raceGroups.length
        ? "No scratchings match the current filters."
        : "No official scratchings have been received for this meeting.";
    return (
      <section className="eiq-scratchings-v1-empty" aria-label="Scratchings unavailable state">
        <span>SCRATCHINGS</span>
        <strong>{message}</strong>
        <p>Race fields remain governed by the current official meeting data.</p>
      </section>
    );
  }

  return (
    <section className="eiq-scratchings-v1-table-card" aria-label="Race grouped scratchings table">
      {groups.map((group) => (
        <div className="eiq-scratchings-v1-race-group" key={group.raceKey}>
          <header>
            <strong>R{group.raceNumber}</strong>
            <span>{group.raceName ?? "Race"}</span>
            <small>
              Field {valueOrUnavailable(group.fieldSizeBefore)} to {valueOrUnavailable(group.fieldSizeAfter)}
            </small>
          </header>
          <div className="eiq-scratchings-v1-table-scroll">
            <table className="eiq-scratchings-v1-table">
              <thead>
                <tr>
                  <th>RACE</th>
                  <th>NO</th>
                  <th>SILK</th>
                  <th className="is-left">HORSE</th>
                  <th className="is-left">TRAINER</th>
                  <th className="is-left">JOCKEY</th>
                  <th>STATUS</th>
                  <th>BAR</th>
                  <th>EFFECTIVE BAR</th>
                  <th>FIELD</th>
                  <th>UPDATED</th>
                </tr>
              </thead>
              <tbody>
                {group.records.map((record) => (
                  <tr key={record.eventKey} className={rowStatusClass(record)}>
                    <td>R{group.raceNumber}</td>
                    <td>{valueOrUnavailable(record.runnerNumber)}</td>
                    <td>
                      {record.silk ? <img src={record.silk} alt={`${record.horse} silk`} /> : <span className="eiq-silk-missing" />}
                    </td>
                    <td className="is-left">
                      <strong>{record.horse}</strong>
                    </td>
                    <td className="is-left">{valueOrUnavailable(record.trainer)}</td>
                    <td className="is-left">{valueOrUnavailable(record.jockey)}</td>
                    <td>{statusLabel(record.status)}</td>
                    <td>{valueOrUnavailable(record.originalBarrier)}</td>
                    <td>{valueOrUnavailable(record.effectiveBarrierAfter)}</td>
                    <td>
                      {valueOrUnavailable(record.fieldSizeBefore)} to {valueOrUnavailable(record.fieldSizeAfter)}
                    </td>
                    <td>{record.scratchedAtDisplay}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </section>
  );
}

export function MeetingScratchingsWorkspace({ meeting }: MeetingScratchingsWorkspaceProps) {
  const model = useMemo(() => buildMeetingScratchingsViewModel(meeting), [meeting]);
  const [raceFilter, setRaceFilter] = useState(ALL_RACES);
  const [statusFilter, setStatusFilter] = useState(ALL_STATUS);
  const [search, setSearch] = useState("");
  return (
    <div className="eiq-scratchings-v1">
      <header className="eiq-scratchings-v1-header">
        <div>
          <span>SCRATCHINGS</span>
          <h2>Official meeting scratchings</h2>
          <p>Scratched runners remain visible where operationally useful.</p>
        </div>
        <div>
          <small>Latest official update</small>
          <strong>{formatDateTime(model.officialUpdatedAt)}</strong>
          <button type="button" onClick={() => window.location.reload()}>
            REFRESH
          </button>
        </div>
      </header>

      <SummaryStrip model={model} />

      <ScratchingsFilters
        model={model}
        raceFilter={raceFilter}
        statusFilter={statusFilter}
        search={search}
        onRaceFilter={setRaceFilter}
        onStatusFilter={setStatusFilter}
        onSearch={setSearch}
      />

      <ScratchingsTable
        model={model}
        raceFilter={raceFilter}
        statusFilter={statusFilter}
        search={search}
      />
    </div>
  );
}
'''


CSS_APPEND = r'''

/* EDGEIQ SCRATCHINGS FINAL SPEC V1 */
.eiq-scratchings-v1-header,
.eiq-scratchings-v1-summary-strip > div,
.eiq-scratchings-v1-filters,
.eiq-scratchings-v1-table-card,
.eiq-scratchings-v1-empty {
  background: #ffffff !important;
  color: var(--edgeiq-text-primary) !important;
  border-color: var(--edgeiq-border) !important;
  box-shadow: 0 10px 28px rgba(23, 32, 51, 0.08) !important;
}

.eiq-scratchings-v1-summary-strip {
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
}

.eiq-scratchings-v1-table th,
.eiq-scratchings-v1-table td {
  height: 42px;
  padding: 9px 10px;
}

.eiq-scratchings-v1-table tbody tr.is-scratched td {
  color: var(--edgeiq-text-secondary) !important;
  opacity: 0.72;
}

.eiq-scratchings-v1-table tbody tr.is-scratched td.is-left strong {
  text-decoration: line-through;
  text-decoration-thickness: 1px;
}

.eiq-scratchings-v1-table tbody tr.is-promoted td {
  background: #f8fbff;
}

.eiq-scratchings-v1-table td:nth-child(8),
.eiq-scratchings-v1-table td:nth-child(9),
.eiq-scratchings-v1-table td:nth-child(10) {
  font-weight: 800;
}
'''


AUDIT_SOURCE = r'''from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingScratchingsWorkspace.tsx"
MEETING_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "scratchingsFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_scratchings_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_SCRATCHINGS_FINAL_SPEC_AUDIT_V1.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add(rows: list[dict[str, str]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    component = read(COMPONENT)
    meeting_component = read(MEETING_COMPONENT)
    service = read(SERVICE)
    css = read(CSS)
    rows: list[dict[str, str]] = []

    for token in ["SCRATCHINGS", "STATUS", "BAR", "EFFECTIVE BAR", "FIELD", "UPDATED", "SummaryStrip", "rowStatusClass"]:
        add(rows, f"component_contains_{token}", token in component, token)

    for token in ["fixtureMode", "buildFixtureMeeting", "Development fixture", "REASON", "SOURCE", "Builder", "DATA FRESHNESS", "TimelinePanel"]:
        add(rows, f"component_absent_{token}", token not in component, token)

    add(rows, "meeting_workspace_no_scratchings_fixture", "scratchingsFixtureMode" not in meeting_component and "edgeiqScratchingsFixture" not in meeting_component, "No visible/development scratchings fixture path in meeting route")
    add(rows, "service_no_fixture_builder", "buildFixtureMeeting" not in service and "Development fixture" not in service and "fixtureMode" not in service, "Scratchings service uses current meeting data only")
    add(rows, "service_effective_barrier_helper", "calculateEffectiveBarriers" in service, "Barrier compression helper remains in service")
    add(rows, "css_marker", "/* EDGEIQ SCRATCHINGS FINAL SPEC V1 */" in css, "Scratchings CSS marker")
    add(rows, "css_scratch_fade", "is-scratched" in css and "text-decoration" in css, "Scratched rows fade and strike horse name")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    status = "EDGEIQ_SCRATCHINGS_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_SCRATCHINGS_FINAL_SPEC_AUDIT_FAIL"
    OUT_MD.write_text(
        "\n".join([
            "# EDGEiQ Scratchings Final Spec Audit V1",
            "",
            f"Status: {status}",
            "",
            f"Checks: {len(rows)}",
            f"Failures: {len(failed)}",
            "",
            "## Results",
            "",
            *[f"- {row['status']}: {row['check']} - {row['detail']}" for row in rows],
            "",
        ]),
        encoding="utf-8",
    )
    print(status)
    print(f"Audit CSV: {OUT_CSV}")
    print(f"Audit MD: {OUT_MD}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


TRACE_SOURCE = """# EDGEiQ Scratchings Trace V1

## Scope

Workspace: SCRATCHINGS

Purpose: official current scratchings for the selected meeting.

## Source Trace

| Display field | Canonical source | Service path | Component path | Availability |
| --- | --- | --- | --- | --- |
| Scratched runner | Current meeting race runners | `normaliseStatus` / `buildRecordsForRace` | Scratchings table | Available where runner status flags are supplied |
| Runner number | Current catalog official runner number | `runnerNumber` | `NO` | Available where supplied |
| Silk | Current catalog silk URL | `silkUrl` | `SILK` | Available where supplied |
| Trainer / jockey | Current catalog official runner fields | `buildRecordsForRace` | Scratchings table | Available where supplied |
| Status | Current catalog runner status | `normaliseStatus` | `STATUS` | Available where supplied |
| Original barrier | Current catalog runner barrier | `originalBarrier` | `BAR` | Available where supplied |
| Effective barrier | Service barrier-compression helper | `calculateEffectiveBarriers` | `EFFECTIVE BAR` | Available where original barriers are resolvable |
| Field before / after | Current race runner count and scratching status | `buildRaceGroups` / `buildRecordsForRace` | `FIELD` | Available where runner rows are supplied |
| Official update | Scratch timestamp where supplied | `officialUpdatedAt` | Header | Available where official scratch time exists |

## Legitimate Gaps

- Empty state is shown when no official scratching status is present in the current meeting catalog.
- Effective barrier is unavailable when original barrier data is unavailable or internally inconsistent.

## Governance Notes

- React displays service fields only.
- Fixture/development scratchings are removed from the product path.
- No reasons, rumours, source names, builder labels, or debug freshness panels are displayed.
"""


def checkpoint(paths: list[Path]) -> None:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            relative = path.relative_to(ROOT)
            target = CHECKPOINT_DIR / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def patch_service() -> None:
    text = SERVICE.read_text(encoding="utf-8")
    text = text.replace('''type ScratchingsBuildOptions = {
  fixtureMode?: boolean;
};

''', "")
    start = text.find("function buildFixtureMeeting(")
    end = text.find("export function buildMeetingScratchingsViewModel", start)
    if start != -1 and end != -1:
        text = text[:start] + text[end:]
    text = text.replace(
        '''export function buildMeetingScratchingsViewModel(
  sourceMeeting: ThreeDayMeeting,
  options: ScratchingsBuildOptions = {},
): MeetingScratchingsViewModel {
  const meeting = options.fixtureMode ? buildFixtureMeeting(sourceMeeting) : sourceMeeting;''',
        '''export function buildMeetingScratchingsViewModel(
  meeting: ThreeDayMeeting,
): MeetingScratchingsViewModel {''',
    )
    SERVICE.write_text(text, encoding="utf-8")


def patch_meeting_workspace() -> None:
    text = MEETING_COMPONENT.read_text(encoding="utf-8")
    text = text.replace('''  const scratchingsFixtureMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqScratchingsFixture") === "1";
''', "")
    text = text.replace(
        '<MeetingScratchingsWorkspace meeting={meeting} fixtureMode={scratchingsFixtureMode} />',
        '<MeetingScratchingsWorkspace meeting={meeting} />',
    )
    MEETING_COMPONENT.write_text(text, encoding="utf-8")


def append_css() -> None:
    text = CSS_FILE.read_text(encoding="utf-8")
    marker = "/* EDGEIQ SCRATCHINGS FINAL SPEC V1 */"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n" + CSS_APPEND.lstrip()
    else:
        text = text.rstrip() + "\n" + CSS_APPEND.lstrip()
    CSS_FILE.write_text(text, encoding="utf-8")


def main() -> None:
    checkpoint([COMPONENT, MEETING_COMPONENT, SERVICE, CSS_FILE])
    COMPONENT.write_text(COMPONENT_SOURCE, encoding="utf-8")
    patch_service()
    patch_meeting_workspace()
    append_css()
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACE_FILE.write_text(TRACE_SOURCE, encoding="utf-8")
    AUDIT_SCRIPT.write_text(AUDIT_SOURCE, encoding="utf-8")
    print(f"Checkpoint: {CHECKPOINT_DIR}")
    print("EDGEIQ_SCRATCHINGS_FINAL_SPEC_PATCH_APPLIED")


if __name__ == "__main__":
    main()
