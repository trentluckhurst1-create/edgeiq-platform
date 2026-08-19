from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT_DIR = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"MEETING_DETAIL_FINAL_SPEC_V1_{STAMP}"

COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingDetailFeed.ts"
CSS_FILE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE_FILE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MEETING_DETAIL_TRACE_V1.md"
AUDIT_SCRIPT = ROOT / "scripts" / "audit_edgeiq_meeting_detail_final_spec_v1.py"


COMPONENT_SOURCE = r'''import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";
import {
  MEETING_DETAIL_TAB_ORDER,
  buildMeetingConditionStripForRace,
  buildMeetingDetailSelectedRace,
  buildMeetingDetailViewModel,
  type MeetingDetailSelectedRace,
  type MeetingDetailTab,
  type MeetingDetailValue,
} from "../services/meetingDetailFeed";
import { MeetingGearChangesWorkspace } from "./MeetingGearChangesWorkspace";
import { MeetingResultsWorkspace } from "./MeetingResultsWorkspace";
import { MeetingScratchingsWorkspace } from "./MeetingScratchingsWorkspace";
import { MeetingTrackWorkspace } from "./MeetingTrackWorkspace";
import { MeetingWeatherWorkspace } from "./MeetingWeatherWorkspace";

type MeetingWorkspaceProps = {
  raceBook: any;
  meeting: ThreeDayMeeting;
  clean: (value: any) => string;
  onBackToMeetings: () => void;
  onOpenRace: (race: ThreeDayRace, index: number) => void;
};

function DetailGrid({ details }: { details: MeetingDetailValue[] }) {
  return (
    <dl className="eiq-meeting-v1-detail-grid">
      {details.map((detail) => (
        <div key={detail.label} className={detail.tone ? `is-${detail.tone}` : ""}>
          <dt>{detail.label}</dt>
          <dd>{detail.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function SummaryStrip({ items }: { items: MeetingDetailValue[] }) {
  return (
    <section className="eiq-meeting-v1-summary-strip" aria-label="Meeting summary">
      {items.map((item) => (
        <div key={item.label} className={item.tone ? `is-${item.tone}` : ""}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </section>
  );
}

function PendingTab({ label, message }: { label: string; message: string }) {
  return (
    <section className="eiq-meeting-v1-pending" aria-label={`${label} pending`}>
      <span>{label}</span>
      <strong>{message}</strong>
    </section>
  );
}

function formatMeetingConditionLabel(label: string): string {
  const displayLabels: Record<string, string> = {
    TEMPERATURE: "TEMP",
    "RAIN 24H": "RAIN",
    "IRRIGATION 24H": "IRRIGATION",
  };

  return displayLabels[label.trim().toUpperCase()] ?? label;
}

function trackConditionClass(value: string): string {
  const text = value.toLowerCase();
  if (/firm\s*[12]|\bfirm\b/.test(text)) return "is-firm";
  if (/good\s*[34]|\bgood\b/.test(text)) return "is-good";
  if (/soft\s*[5-7]|\bsoft\b/.test(text)) return "is-soft";
  if (/heavy\s*(8|9|10)|\bheavy\b/.test(text)) return "is-heavy";
  return "";
}

function MeetingConditionStrip({
  meeting,
  selected,
}: {
  meeting: ThreeDayMeeting;
  selected: MeetingDetailSelectedRace | null;
}) {
  const conditionStrip = buildMeetingConditionStripForRace(meeting, selected?.row.race ?? null);
  return (
    <section className="eiq-meeting-v1-condition-strip" aria-label="Meeting condition strip">
      {conditionStrip
        .filter((item) => item.label.trim().toUpperCase() !== "OFFICIAL UPDATE")
        .map((item) => {
          const isTrack = item.label.trim().toUpperCase() === "TRACK";
          return (
            <div
              key={item.label}
              className={[
                item.tone ? `is-${item.tone}` : "",
                isTrack ? trackConditionClass(item.value) : "",
              ].filter(Boolean).join(" ")}
            >
              <span>{formatMeetingConditionLabel(item.label)}</span>
              <strong>{item.value}</strong>
            </div>
          );
        })}
    </section>
  );
}

function RacesTable({
  model,
  selectedRaceKey,
  onSelectRace,
  onOpenRace,
}: {
  model: ReturnType<typeof buildMeetingDetailViewModel>;
  selectedRaceKey: string;
  onSelectRace: (raceKey: string) => void;
  onOpenRace: (race: ThreeDayRace, index: number) => void;
}) {
  return (
    <section className="eiq-meeting-v1-panel">
      <header>
        <div>
          <span>RACES</span>
          <strong>Meeting race list</strong>
        </div>
      </header>
      <div className="eiq-meeting-v1-table-scroll">
        <table className="eiq-meeting-v1-table">
          <thead>
            <tr>
              <th>RACE</th>
              <th>TIME</th>
              <th className="is-left">RACE NAME</th>
              <th>DIST</th>
              <th>CLASS</th>
              <th>FIELD</th>
              <th>SCR</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {model.races.map((row) => (
              <tr
                key={row.raceKey}
                className={selectedRaceKey === row.raceKey ? "is-selected" : ""}
                role="button"
                tabIndex={0}
                aria-label={`Open ${row.raceLabel} ${row.raceName}`}
                onClick={() => {
                  onSelectRace(row.raceKey);
                  onOpenRace(row.race, row.raceIndex);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectRace(row.raceKey);
                    onOpenRace(row.race, row.raceIndex);
                  }
                }}
              >
                <td>{row.raceLabel.replace(/^R/i, "")}</td>
                <td>{row.time}</td>
                <td className="is-left">
                  <strong>{row.raceName}</strong>
                </td>
                <td>{row.distance}</td>
                <td>{row.raceClass}</td>
                <td>{row.fieldSize}</td>
                <td>{row.scratchings}</td>
                <td className={row.statusTone ? `is-${row.statusTone}` : ""}>{row.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SelectedRacePanel({
  selected,
}: {
  selected: MeetingDetailSelectedRace | null;
}) {
  if (!selected) {
    return (
      <section className="eiq-meeting-v1-panel eiq-meeting-v1-selected-race">
        <header>
          <div>
            <span>SELECTED RACE</span>
            <strong>No race selected</strong>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section className="eiq-meeting-v1-panel eiq-meeting-v1-selected-race">
      <header>
        <div>
          <span>SELECTED RACE</span>
          <strong>{selected.row.raceLabel} - {selected.row.raceName}</strong>
        </div>
        <p>{selected.row.secondary || "Race details not supplied"}</p>
      </header>
      <DetailGrid details={selected.details} />
    </section>
  );
}

function RacesTab({
  model,
  selected,
  selectedRaceKey,
  setSelectedRaceKey,
  onOpenRace,
}: {
  model: ReturnType<typeof buildMeetingDetailViewModel>;
  selected: MeetingDetailSelectedRace | null;
  selectedRaceKey: string;
  setSelectedRaceKey: (raceKey: string) => void;
  onOpenRace: (race: ThreeDayRace, index: number) => void;
}) {
  return (
    <div className="eiq-meeting-v1-main-stack">
      <RacesTable
        model={model}
        selectedRaceKey={selectedRaceKey}
        onSelectRace={setSelectedRaceKey}
        onOpenRace={onOpenRace}
      />
      <SelectedRacePanel selected={selected} />
    </div>
  );
}

export function MeetingWorkspace({
  raceBook,
  meeting,
  clean,
  onBackToMeetings,
  onOpenRace,
}: MeetingWorkspaceProps) {
  void raceBook;
  void clean;

  const model = useMemo(() => buildMeetingDetailViewModel(meeting), [meeting]);
  const [tab, setTab] = useState<MeetingDetailTab>("RACES");
  const [selectedRaceKey, setSelectedRaceKey] = useState(model.races[0]?.raceKey ?? "");

  const selected = useMemo(
    () =>
      buildMeetingDetailSelectedRace(
        model,
        meeting,
        selectedRaceKey,
      ),
    [model, meeting, selectedRaceKey],
  );

  useEffect(() => {
    if (!model.races.some((race) => race.raceKey === selectedRaceKey)) {
      setSelectedRaceKey(model.races[0]?.raceKey ?? "");
    }
  }, [model, selectedRaceKey]);

  const activePending = MEETING_DETAIL_TAB_ORDER.find((item) => item.key === tab && item.key !== "RACES");
  const scratchingsFixtureMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqScratchingsFixture") === "1";
  const gearFixtureMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqGearFixture") === "1";
  const trackFixtureMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqTrackFixture") === "1";
  const trackMissingMapMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqTrackMissingMap") === "1";
  const trackMissingHistoricalMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqTrackMissingHistorical") === "1";
  const weatherFixtureMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqWeatherFixture") === "1";
  const weatherUnavailableMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqWeatherUnavailable") === "1";
  const weatherPartialMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqWeatherPartial") === "1";

  return (
    <section className="eiq-meeting-workspace eiq-meeting-v1">
      <header className="eiq-meeting-v1-hero">
        <div>
          <span>MEETING DETAIL</span>
          <h2>{model.meetingName}</h2>
          <p>{model.venueLine}</p>
        </div>
        <button type="button" onClick={onBackToMeetings}>
          Back to Meetings
        </button>
      </header>

      <SummaryStrip items={model.summary} />
      <MeetingConditionStrip meeting={meeting} selected={selected} />

      <nav className="eiq-context-tabs eiq-meeting-v1-tabs" aria-label="Meeting workspace navigation" role="tablist">
        {MEETING_DETAIL_TAB_ORDER.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={tab === item.key}
            className={tab === item.key ? "is-active" : ""}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="eiq-meeting-v1-layout">
        <main>
          {tab === "RACES" ? (
            <RacesTab
              model={model}
              selected={selected}
              selectedRaceKey={selectedRaceKey}
              setSelectedRaceKey={setSelectedRaceKey}
              onOpenRace={onOpenRace}
            />
          ) : tab === "SCRATCHINGS" ? (
            <MeetingScratchingsWorkspace meeting={meeting} fixtureMode={scratchingsFixtureMode} />
          ) : tab === "GEAR_CHANGES" ? (
            <MeetingGearChangesWorkspace meeting={meeting} fixtureMode={gearFixtureMode} />
          ) : tab === "TRACK" ? (
            <MeetingTrackWorkspace
              meeting={meeting}
              fixtureMode={trackFixtureMode}
              missingMapMode={trackMissingMapMode}
              missingHistoricalMode={trackMissingHistoricalMode}
            />
          ) : tab === "WEATHER" ? (
            <MeetingWeatherWorkspace
              meeting={meeting}
              fixtureMode={weatherFixtureMode}
              unavailableMode={weatherUnavailableMode}
              partialMode={weatherPartialMode}
            />
          ) : tab === "RESULTS" ? (
            <MeetingResultsWorkspace meeting={meeting} />
          ) : activePending ? (
            <PendingTab label={activePending.label} message={activePending.pendingMessage ?? model.pendingTabs[tab]} />
          ) : null}
        </main>
      </div>
    </section>
  );
}
'''


CSS_APPEND = r'''

/* EDGEIQ MEETING DETAIL FINAL SPEC V1 */
.eiq-meeting-v1-hero,
.eiq-meeting-v1-panel,
.eiq-meeting-v1-pending,
.eiq-meeting-v1-summary-strip > div,
.eiq-meeting-v1-condition-strip > div {
  background: #ffffff !important;
  color: var(--edgeiq-text-primary) !important;
  border: 1px solid var(--edgeiq-border) !important;
  border-radius: 16px;
  box-shadow: 0 10px 28px rgba(23, 32, 51, 0.08) !important;
}

.eiq-meeting-v1-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 22px;
}

.eiq-meeting-v1-hero span,
.eiq-meeting-v1-panel header span,
.eiq-meeting-v1-pending span {
  color: var(--edgeiq-primary) !important;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.eiq-meeting-v1-hero h2 {
  margin: 5px 0 5px;
  color: var(--edgeiq-text-primary) !important;
  font-size: clamp(25px, 2.2vw, 34px);
  line-height: 1.1;
}

.eiq-meeting-v1-hero p,
.eiq-meeting-v1-panel header p {
  color: var(--edgeiq-text-secondary) !important;
  margin: 0;
}

.eiq-meeting-v1-hero button {
  border: 1px solid var(--edgeiq-border);
  border-radius: 12px;
  background: #ffffff;
  color: var(--edgeiq-primary);
  font-weight: 800;
  padding: 10px 14px;
}

.eiq-meeting-v1-summary-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  gap: 10px;
}

.eiq-meeting-v1-summary-strip > div,
.eiq-meeting-v1-condition-strip > div {
  padding: 12px;
}

.eiq-meeting-v1-summary-strip span,
.eiq-meeting-v1-condition-strip span,
.eiq-meeting-v1-detail-grid dt {
  display: block;
  color: var(--edgeiq-text-secondary) !important;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.eiq-meeting-v1-summary-strip strong,
.eiq-meeting-v1-condition-strip strong,
.eiq-meeting-v1-detail-grid dd {
  color: var(--edgeiq-text-primary) !important;
  font-size: 15px;
  font-weight: 800;
}

.eiq-meeting-v1-condition-strip > div.is-firm strong {
  color: #b91c1c !important;
}

.eiq-meeting-v1-condition-strip > div.is-good strong {
  color: #15803d !important;
}

.eiq-meeting-v1-condition-strip > div.is-soft strong {
  color: #1d4ed8 !important;
}

.eiq-meeting-v1-condition-strip > div.is-heavy {
  background: #111827 !important;
}

.eiq-meeting-v1-condition-strip > div.is-heavy span,
.eiq-meeting-v1-condition-strip > div.is-heavy strong {
  color: #ffffff !important;
}

.eiq-meeting-v1-panel {
  padding: 16px;
}

.eiq-meeting-v1-panel header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--edgeiq-border);
}

.eiq-meeting-v1-panel header strong {
  color: var(--edgeiq-text-primary) !important;
  font-size: 18px;
}

.eiq-meeting-v1-main-stack {
  display: grid;
  gap: 14px;
}

.eiq-meeting-v1-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin: 14px 0 0;
}

.eiq-meeting-v1-detail-grid div {
  border: 1px solid var(--edgeiq-border);
  border-radius: 12px;
  background: #ffffff;
  padding: 10px;
}

.eiq-meeting-v1-table th,
.eiq-meeting-v1-table td {
  height: 42px;
  padding: 9px 10px;
  color: var(--edgeiq-text-primary) !important;
}

.eiq-meeting-v1-table th {
  color: var(--edgeiq-text-secondary) !important;
}

.eiq-meeting-v1-table td.is-positive {
  color: #15803d !important;
}

.eiq-meeting-v1-table td.is-caution {
  color: #a16207 !important;
}

.eiq-meeting-v1-table td.is-negative {
  color: #b91c1c !important;
}
'''


AUDIT_SOURCE = r'''from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingDetailFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_meeting_detail_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MEETING_DETAIL_FINAL_SPEC_AUDIT_V1.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add(rows: list[dict[str, str]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    component = read(COMPONENT)
    service = read(SERVICE)
    css = read(CSS)
    rows: list[dict[str, str]] = []

    for token in [
        "MEETING DETAIL",
        "SummaryStrip",
        "MeetingConditionStrip",
        "SelectedRacePanel",
        "Back to Meetings",
        "RACES",
        "SCRATCHINGS",
        "TRACK",
        "WEATHER",
        "RESULTS",
    ]:
        add(rows, f"component_contains_{token}", token in component, token)

    for token in ["STATE", "RACES", "RUNNERS", "SCRATCHINGS", "OFFICIAL UPDATE"]:
        add(rows, f"service_summary_contains_{token}", token in service, token)

    add(rows, "service_tab_order_contains_gear_changes", "GEAR CHANGES" in service, "GEAR CHANGES tab label is supplied by meeting-detail tab order")

    for token in ["Weather Stations", "Forecast Source", "station ID", "builder status", "Confidence"]:
        add(rows, f"component_absent_{token}", token not in component, token)

    add(rows, "component_no_generic_intelligence_copy", "Governed operational evidence" not in component, "No generic Race Intelligence copy rendered")
    add(rows, "css_marker", "/* EDGEIQ MEETING DETAIL FINAL SPEC V1 */" in css, "Meeting detail CSS marker")
    add(rows, "css_track_condition_colours", all(token in css for token in ["is-firm", "is-good", "is-soft", "is-heavy"]), "Track condition classes")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    status = "EDGEIQ_MEETING_DETAIL_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_MEETING_DETAIL_FINAL_SPEC_AUDIT_FAIL"
    OUT_MD.write_text(
        "\n".join([
            "# EDGEiQ Meeting Detail Final Spec Audit V1",
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


TRACE_SOURCE = """# EDGEiQ Meeting Detail Trace V1

## Scope

Workspace: MEETING DETAIL

Purpose: operational bridge between selected meeting and race-level workspaces.

## Source Trace

| Display field | Canonical source | Service path | Component path | Availability |
| --- | --- | --- | --- | --- |
| Meeting identity | Three-day product catalog meeting | `buildMeetingDetailViewModel` | `MeetingWorkspace` hero | Available |
| Date | Three-day product catalog meeting date | `formatDateLong` | Hero and summary | Available |
| State | Meeting catalog source state | `buildMeetingSummary` | Summary strip | Available where supplied |
| Track condition | Race/meeting condition fields | `buildConditionStrip` | Condition strip | Available where supplied |
| Rail | Race/meeting rail fields | `railPosition` | Condition strip and selected-race details | Available where supplied |
| Weather | Race/meeting current weather fields | `buildConditionStrip` | Condition strip | Available where supplied |
| Race list | Meeting races in catalog | `buildRaceRows` | Race table | Available |
| Declared runners | Current catalog race runners | `buildMeetingSummary` | Summary strip and race table | Available |
| Scratchings | Current catalog runner status | `scratchedCount` | Summary strip and race table | Available when status is supplied |
| Official update | Current race/meeting timestamp fields | `buildMeetingSummary` / `buildConditionStrip` | Summary strip | Available where supplied |

## Legitimate Gaps

- Race prize money, age/sex and weight conditions remain `Not supplied` where not present in the selected race row.
- Weather remains unavailable where current meeting/race weather fields are not supplied.
- Scratchings remain zero when no runner is marked scratched in the current catalog.

## Governance Notes

- React displays the meeting-detail service view model only.
- No pricing, EPI, ERI, EPF, weather freshness or governed model logic is changed.
- Weather sub-workspace and live-weather v1.2 integration are preserved.
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
    text = text.replace(
        r'''function buildMeetingSummary(meeting: ThreeDayMeeting, races: MeetingDetailRaceRow[]): MeetingDetailValue[] {
  const first = races[0]?.time || "Unavailable";
  const last = races[races.length - 1]?.time || "Unavailable";
  const completed = races.filter((race) => ["OFFICIAL", "UNOFFICIAL", "RESULTS"].includes(race.status)).length;
  const totalRunners = meeting.races.reduce((sum, race) => sum + race.runners.length, 0);
  const status = races.length && completed === races.length ? "COMPLETED" : races.length ? "READY" : "FIELDS PENDING";

  return [
    { label: "RACE COUNT", value: String(meeting.raceCount || races.length) },
    { label: "FIRST RACE", value: first },
    { label: "LAST RACE", value: last },
    { label: "RUNNERS", value: totalRunners ? String(totalRunners) : "Not supplied" },
    { label: "STATUS", value: status, tone: statusTone(status) },
    { label: "LAST UPDATED", value: firstText(meeting.source?.built_at, "Unavailable") },
  ];
}
''',
        r'''function buildMeetingSummary(meeting: ThreeDayMeeting, races: MeetingDetailRaceRow[]): MeetingDetailValue[] {
  const first = races[0]?.time || "Unavailable";
  const last = races[races.length - 1]?.time || "Unavailable";
  const completed = races.filter((race) => ["OFFICIAL", "UNOFFICIAL", "RESULTS"].includes(race.status)).length;
  const totalRunners = meeting.races.reduce((sum, race) => sum + race.runners.length, 0);
  const totalScratchings = meeting.races.reduce((sum, race) => sum + scratchedCount(race), 0);
  const status = races.length && completed === races.length ? "COMPLETED" : races.length ? "READY" : "FIELDS PENDING";
  const condition = buildConditionStrip(meeting, meeting.races[0] ?? null);
  const officialUpdate = condition.find((item) => item.label === "OFFICIAL UPDATE")?.value ?? "Unavailable";

  return [
    { label: "STATE", value: firstText(meeting.source?.State, "Not supplied") },
    { label: "RACES", value: String(meeting.raceCount || races.length) },
    { label: "RUNNERS", value: totalRunners ? String(totalRunners) : "Not supplied" },
    { label: "SCRATCHINGS", value: String(totalScratchings) },
    { label: "FIRST", value: first },
    { label: "LAST", value: last },
    { label: "STATUS", value: status, tone: statusTone(status) },
    { label: "OFFICIAL UPDATE", value: officialUpdate },
  ];
}
''',
    )
    SERVICE.write_text(text, encoding="utf-8")


def append_css() -> None:
    text = CSS_FILE.read_text(encoding="utf-8")
    marker = "/* EDGEIQ MEETING DETAIL FINAL SPEC V1 */"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n" + CSS_APPEND.lstrip()
    else:
        text = text.rstrip() + "\n" + CSS_APPEND.lstrip()
    CSS_FILE.write_text(text, encoding="utf-8")


def main() -> None:
    checkpoint([COMPONENT, SERVICE, CSS_FILE])
    COMPONENT.write_text(COMPONENT_SOURCE, encoding="utf-8")
    patch_service()
    append_css()
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACE_FILE.write_text(TRACE_SOURCE, encoding="utf-8")
    AUDIT_SCRIPT.write_text(AUDIT_SOURCE, encoding="utf-8")
    print(f"Checkpoint: {CHECKPOINT_DIR}")
    print("EDGEIQ_MEETING_DETAIL_FINAL_SPEC_PATCH_APPLIED")


if __name__ == "__main__":
    main()
