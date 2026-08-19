from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT_DIR = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"MEETINGS_FINAL_SPEC_V1_{STAMP}"


MEETINGS_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
MEETINGS_SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingsFeed.ts"
CSS_FILE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE_FILE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MEETINGS_TRACE_V1.md"
AUDIT_SCRIPT = ROOT / "scripts" / "audit_edgeiq_meetings_final_spec_v1.py"


COMPONENT_SOURCE = r'''import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";
import {
  loadMeetingsWorkspaceViewModel,
  type MeetingSummaryViewModel,
  type MeetingsDayKey,
  type MeetingsWorkspaceViewModel,
} from "../services/meetingsFeed";

type MeetingsWorkspaceProps = {
  selectedDayKey: MeetingsDayKey;
  selectedMeetingKey: string | null;
  clean: (value: any) => string;
  onDayChange: (day: MeetingsDayKey) => void;
  onSelectMeeting: (meeting: ThreeDayMeeting | null) => void;
  onOpenMeeting: (meeting: ThreeDayMeeting) => void;
  onOpenRace: (meeting: ThreeDayMeeting, race: ThreeDayRace, index: number) => void;
};

function isUnavailable(value: string): boolean {
  return (
    !value ||
    value === "Not supplied" ||
    value === "Weather unavailable" ||
    value === "Wind unavailable" ||
    value === "Temp unavailable"
  );
}

function trackConditionClass(value: string): string {
  const text = value.toLowerCase();
  if (/firm\s*[12]|\bfirm\b/.test(text)) return "is-firm";
  if (/good\s*[34]|\bgood\b/.test(text)) return "is-good";
  if (/soft\s*[5-7]|\bsoft\b/.test(text)) return "is-soft";
  if (/heavy\s*(8|9|10)|\bheavy\b/.test(text)) return "is-heavy";
  return "is-other";
}

export function MeetingsWorkspace({
  selectedDayKey,
  selectedMeetingKey,
  clean,
  onDayChange,
  onSelectMeeting,
  onOpenMeeting,
  onOpenRace,
}: MeetingsWorkspaceProps) {
  const [viewModel, setViewModel] = useState<MeetingsWorkspaceViewModel | null>(null);
  const [status, setStatus] = useState<"LOADING" | "READY" | "ERROR">("LOADING");

  useEffect(() => {
    let active = true;
    setStatus("LOADING");
    loadMeetingsWorkspaceViewModel()
      .then((nextViewModel) => {
        if (!active) return;
        setViewModel(nextViewModel);
        setStatus("READY");
      })
      .catch(() => {
        if (!active) return;
        setStatus("ERROR");
      });

    return () => {
      active = false;
    };
  }, []);

  const activeDay = useMemo(() => {
    return (
      viewModel?.days.find((day) => day.key === selectedDayKey) ??
      viewModel?.days[0] ??
      null
    );
  }, [selectedDayKey, viewModel]);

  const selectedMeeting = useMemo(() => {
    if (!activeDay) return null;
    return (
      activeDay.meetings.find((meeting) => meeting.meetingKey === selectedMeetingKey) ??
      activeDay.meetings[0] ??
      null
    );
  }, [activeDay, selectedMeetingKey]);

  useEffect(() => {
    if (status !== "READY" || !activeDay) return;
    if (selectedMeeting) {
      if (selectedMeeting.meetingKey !== selectedMeetingKey) {
        onSelectMeeting(selectedMeeting.rawMeeting);
      }
      return;
    }
    if (selectedMeetingKey) onSelectMeeting(null);
  }, [activeDay, onSelectMeeting, selectedMeeting, selectedMeetingKey, status]);

  if (status === "LOADING") {
    return (
      <section className="eiq-meetings-workspace eiq-meetings-engineering">
        <section className="eiq-workspace-panel">
          <span>MEETINGS</span>
          <strong>Loading the three-day race programme.</strong>
        </section>
      </section>
    );
  }

  if (status === "ERROR" || !viewModel || !activeDay) {
    return (
      <section className="eiq-meetings-workspace eiq-meetings-engineering">
        <section className="eiq-workspace-panel">
          <span>MEETINGS</span>
          <strong>The three-day race programme could not be loaded.</strong>
        </section>
      </section>
    );
  }

  return (
    <section className="eiq-meetings-workspace eiq-meetings-engineering">
      <header className="eiq-meetings-engineering__header">
        <div>
          <span>MEETINGS</span>
          <h2>Meeting Centre</h2>
          <p>{activeDay.displayDate}</p>
        </div>
        <dl>
          <div>
            <dt>Meetings</dt>
            <dd>{activeDay.totals.meetings}</dd>
          </div>
          <div>
            <dt>Races</dt>
            <dd>{activeDay.totals.races}</dd>
          </div>
          <div>
            <dt>Runners</dt>
            <dd>{activeDay.totals.declared}</dd>
          </div>
          <div>
            <dt>Scratchings</dt>
            <dd>{activeDay.totals.scratchings}</dd>
          </div>
        </dl>
      </header>

      <nav className="eiq-meetings-engineering__days" aria-label="Meeting day selector">
        {viewModel.days.map((day) => (
          <button
            key={day.key}
            type="button"
            className={day.key === activeDay.key ? "is-active" : ""}
            onClick={() => onDayChange(day.key)}
          >
            <strong>{day.label}</strong>
            <span>{day.displayDate}</span>
          </button>
        ))}
      </nav>

      <section className="eiq-meetings-engineering__grid">
        <div className="eiq-meetings-engineering__table-panel">
          <header>
            <div>
              <span>MEETINGS TABLE</span>
              <strong>{activeDay.displayDate}</strong>
            </div>
            <p>{activeDay.meetings.length} meetings in the current rolling window</p>
          </header>

          {activeDay.meetings.length === 0 ? (
            <div className="eiq-meetings-engineering__empty">
              No meetings are loaded for this day.
            </div>
          ) : (
            <div className="eiq-meetings-engineering__table-scroll">
              <table className="eiq-meetings-engineering__table">
                <thead>
                  <tr>
                    <th>SELECT</th>
                    <th>MEETING</th>
                    <th>STATE</th>
                    <th>TRACK</th>
                    <th>RAIL</th>
                    <th>RACES</th>
                    <th>RUNNERS</th>
                    <th>SCRATCHINGS</th>
                    <th>FIRST</th>
                    <th>LAST</th>
                    <th>UPDATE</th>
                    <th>OPEN</th>
                  </tr>
                </thead>
                <tbody>
                  {activeDay.meetings.map((meeting) => (
                    <MeetingRow
                      key={meeting.meetingKey}
                      meeting={meeting}
                      selected={meeting.meetingKey === selectedMeeting?.meetingKey}
                      clean={clean}
                      onSelect={() => onSelectMeeting(meeting.rawMeeting)}
                      onOpen={() => onOpenMeeting(meeting.rawMeeting)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="eiq-meetings-engineering__rail" aria-label="Selected meeting">
          {selectedMeeting ? (
            <>
              <span>SELECTED MEETING</span>
              <h3>{clean(selectedMeeting.meeting)}</h3>
              <p>{clean(selectedMeeting.venue)}</p>
              <dl>
                <div>
                  <dt>Track</dt>
                  <dd>
                    <span
                      className={`eiq-meetings-engineering__condition ${trackConditionClass(
                        selectedMeeting.track,
                      )}`}
                    >
                      {selectedMeeting.track}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>Rail</dt>
                  <dd className={isUnavailable(selectedMeeting.rail) ? "is-muted" : ""}>
                    {selectedMeeting.rail}
                  </dd>
                </div>
                <div>
                  <dt>Weather</dt>
                  <dd className={isUnavailable(selectedMeeting.weather) ? "is-muted" : ""}>
                    {selectedMeeting.weather}
                  </dd>
                </div>
                <div>
                  <dt>Wind</dt>
                  <dd className={isUnavailable(selectedMeeting.wind) ? "is-muted" : ""}>
                    {selectedMeeting.wind}
                  </dd>
                </div>
                <div>
                  <dt>Temperature</dt>
                  <dd className={isUnavailable(selectedMeeting.temp) ? "is-muted" : ""}>
                    {selectedMeeting.temp}
                  </dd>
                </div>
                <div>
                  <dt>Rain 24h</dt>
                  <dd>{selectedMeeting.rain24h}</dd>
                </div>
                <div>
                  <dt>Irrigation 24h</dt>
                  <dd>{selectedMeeting.irrigation24h}</dd>
                </div>
                <div>
                  <dt>Races</dt>
                  <dd>{selectedMeeting.races}</dd>
                </div>
                <div>
                  <dt>Runners</dt>
                  <dd>{selectedMeeting.declared}</dd>
                </div>
                <div>
                  <dt>Scratchings</dt>
                  <dd>{selectedMeeting.scratchings}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{selectedMeeting.status}</dd>
                </div>
                <div>
                  <dt>Official Update</dt>
                  <dd>{selectedMeeting.officialUpdate}</dd>
                </div>
              </dl>
              <button type="button" onClick={() => onOpenMeeting(selectedMeeting.rawMeeting)}>
                Open Meeting &gt;
              </button>
            </>
          ) : (
            <p>No meeting selected.</p>
          )}
        </aside>
      </section>

      <section className="eiq-meetings-engineering__race-strip">
        <header>
          <div>
            <span>RACES - {selectedMeeting ? clean(selectedMeeting.meeting) : "NO MEETING"}</span>
            <strong>
              {selectedMeeting
                ? `${selectedMeeting.raceSummaries.length} races scheduled`
                : "Select a meeting"}
            </strong>
          </div>
          {selectedMeeting ? (
            <p>
              First {selectedMeeting.first} / Last {selectedMeeting.last}
            </p>
          ) : null}
        </header>

        <div className="eiq-meetings-engineering__race-list">
          {selectedMeeting?.raceSummaries.map((race, index) => (
            <article key={race.raceKey}>
              <button
                type="button"
                onClick={() => onOpenRace(selectedMeeting.rawMeeting, race.rawRace, index)}
              >
                <strong>{race.label}</strong>
                <span>{race.time}</span>
              </button>
              <dl>
                <div>
                  <dt>Distance</dt>
                  <dd>{race.distance}</dd>
                </div>
                <div>
                  <dt>Race</dt>
                  <dd>{race.name}</dd>
                </div>
                <div>
                  <dt>Class</dt>
                  <dd>{race.raceClass}</dd>
                </div>
                <div>
                  <dt>Runners</dt>
                  <dd>{race.fieldSize}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{race.status}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

function MeetingRow({
  meeting,
  selected,
  clean,
  onSelect,
  onOpen,
}: {
  meeting: MeetingSummaryViewModel;
  selected: boolean;
  clean: (value: any) => string;
  onSelect: () => void;
  onOpen: () => void;
}) {
  return (
    <tr className={selected ? "is-selected" : ""}>
      <td>
        <button
          type="button"
          className="eiq-meetings-engineering__select"
          aria-pressed={selected}
          aria-label={`Select ${meeting.meeting}`}
          onClick={onSelect}
        >
          {selected ? "Selected" : "Select"}
        </button>
      </td>
      <td className="is-left">
        <strong>{clean(meeting.meeting)}</strong>
      </td>
      <td>{meeting.state}</td>
      <td>
        <span
          className={`eiq-meetings-engineering__condition ${trackConditionClass(
            meeting.track,
          )}`}
        >
          {meeting.track}
        </span>
      </td>
      <td className={isUnavailable(meeting.rail) ? "is-muted" : ""}>{meeting.rail}</td>
      <td>{meeting.races}</td>
      <td>{meeting.declared}</td>
      <td>{meeting.scratchings}</td>
      <td>{meeting.first}</td>
      <td>{meeting.last}</td>
      <td>{meeting.officialUpdate}</td>
      <td>
        <button
          type="button"
          className="eiq-meetings-engineering__open"
          onClick={onOpen}
        >
          Open
        </button>
      </td>
    </tr>
  );
}
'''


CSS_APPEND = r'''

/* EDGEIQ MEETINGS FINAL SPEC V1 */
.eiq-meetings-engineering__header dl {
  display: grid;
  grid-template-columns: repeat(4, minmax(86px, 1fr));
  gap: 10px;
  margin: 0;
}

.eiq-meetings-engineering__header dl div,
.eiq-meetings-engineering__rail dl div,
.eiq-meetings-engineering__race-list dl div {
  background: #ffffff;
  border: 1px solid var(--edgeiq-border);
  border-radius: 12px;
}

.eiq-meetings-engineering__days button strong {
  display: block;
  color: var(--edgeiq-primary);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-meetings-engineering__days button span {
  color: var(--edgeiq-text-secondary);
  font-size: 12px;
  letter-spacing: 0;
  text-transform: none;
}

.eiq-meetings-engineering__table th,
.eiq-meetings-engineering__table td {
  height: 44px;
  padding: 9px 10px;
  white-space: nowrap;
}

.eiq-meetings-engineering__table th:nth-child(2),
.eiq-meetings-engineering__table td:nth-child(2) {
  min-width: 160px;
}

.eiq-meetings-engineering__table th:nth-child(4),
.eiq-meetings-engineering__table td:nth-child(4) {
  min-width: 102px;
}

.eiq-meetings-engineering__table th:nth-child(11),
.eiq-meetings-engineering__table td:nth-child(11) {
  min-width: 150px;
}

.eiq-meetings-engineering__condition {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 70px;
  border-radius: 999px;
  padding: 4px 9px;
  border: 1px solid #d7dde8;
  background: #f8fafc;
  color: var(--edgeiq-text-primary);
  font-weight: 800;
  line-height: 1;
}

.eiq-meetings-engineering__condition.is-firm {
  border-color: #fecaca;
  background: #fff1f2;
  color: #b91c1c;
}

.eiq-meetings-engineering__condition.is-good {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
}

.eiq-meetings-engineering__condition.is-soft {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}

.eiq-meetings-engineering__condition.is-heavy {
  border-color: #111827;
  background: #111827;
  color: #ffffff;
}

.eiq-meetings-engineering__rail dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.eiq-meetings-engineering__rail dl div {
  padding: 10px;
}

.eiq-meetings-engineering__rail dl div:last-child {
  grid-column: 1 / -1;
}

.eiq-meetings-engineering__race-list {
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
}

.eiq-meetings-engineering__race-list article {
  min-height: 0;
}

.eiq-meetings-engineering__race-list dl {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 1040px) {
  .eiq-meetings-engineering__header dl,
  .eiq-meetings-engineering__rail dl {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
'''


AUDIT_SOURCE = r'''from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingsFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
WINDOW = ROOT / "public" / "data" / "edgeiq_three_day_window_v1.json"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_meetings_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MEETINGS_FINAL_SPEC_AUDIT_V1.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add(rows: list[dict[str, str]], check: str, passed: bool, detail: str) -> None:
    rows.append({
        "check": check,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    })


def main() -> int:
    component = read(COMPONENT)
    service = read(SERVICE)
    css = read(CSS)
    rows: list[dict[str, str]] = []

    required_component_tokens = [
        "selectedDayKey",
        "onDayChange",
        "onOpenMeeting",
        "onOpenRace",
        "meeting.declared",
        "meeting.scratchings",
        "meeting.officialUpdate",
        "selectedMeeting.declared",
        "selectedMeeting.scratchings",
        "trackConditionClass",
        "RUNNERS",
        "SCRATCHINGS",
        "UPDATE",
    ]
    for token in required_component_tokens:
      add(rows, f"component_contains_{token}", token in component, token)

    rejected_visible_tokens = [
        "EDGEiQ Notes",
        "Weather Stations",
        "Forecast Source",
        "station ID",
        "builder status",
    ]
    for token in rejected_visible_tokens:
        add(rows, f"component_absent_{token}", token not in component, token)

    add(rows, "component_absent_confidence_label", "Confidence" not in component, "No product-facing Confidence copy in Meetings component")
    add(rows, "service_renamed_meeting_evidence_authority", "confidence:" not in service and "authority:" in service, "Meeting evidence uses authority, not Confidence wording")
    add(rows, "service_no_edgeiq_read_copy", "edgeiqRead" not in service and "buildEdgeiqRead" not in service, "Generic meeting notes removed from service model")

    for token in ["/* EDGEIQ MEETINGS FINAL SPEC V1 */", "is-firm", "is-good", "is-soft", "is-heavy"]:
        add(rows, f"css_contains_{token}", token in css, token)

    if WINDOW.exists():
        try:
            data = json.loads(WINDOW.read_text(encoding="utf-8"))
            dates = data.get("dates", [])
            keys = [item.get("key") for item in dates]
            add(rows, "three_day_window_has_three_dates", len(dates) == 3, str(keys))
            add(rows, "three_day_window_keys", {"TODAY", "TOMORROW", "DAY_PLUS_2"}.issubset(set(keys)), str(keys))
        except Exception as exc:
            add(rows, "three_day_window_parse", False, repr(exc))
    else:
        add(rows, "three_day_window_exists", False, str(WINDOW))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    status = "EDGEIQ_MEETINGS_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_MEETINGS_FINAL_SPEC_AUDIT_FAIL"
    OUT_MD.write_text(
        "\n".join([
            "# EDGEiQ Meetings Final Spec Audit V1",
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


TRACE_SOURCE = """# EDGEiQ Meetings Trace V1

## Scope

Workspace: MEETINGS

Purpose: primary operational meeting selector across the rolling three-day window.

## Source Trace

| Display field | Canonical source | Service path | Component path | Availability |
| --- | --- | --- | --- | --- |
| Day window | `public/data/edgeiq_three_day_window_v1.json` | `loadMeetingsWorkspaceViewModel` | `MeetingsWorkspace` day buttons | TODAY / TOMORROW / DAY +2 where supplied |
| Meetings | `loadThreeDayCatalog` current product catalog | `buildDay` / `buildMeetingSummary` | Meetings table | Available from catalog |
| Race count | Meeting races in catalog | `meeting.races` | `meeting.races` | Available |
| Declared runners | Current catalog runners | `declared` | `meeting.declared` | Available |
| Scratchings | Current catalog runner status | `scratchings` | `meeting.scratchings` | Available when catalog status supplies scratched runner state |
| Track condition | Meeting/race track condition fields | `trackRating` | `meeting.track` | Available where official/current source supplies condition |
| Rail | Meeting/race rail fields | `railPosition` | `meeting.rail` | Available where supplied |
| Weather / wind / temperature | Current meeting race weather fields | `weatherLabel`, `windLabel`, `tempLabel` | selected meeting rail | Available where supplied |
| Official update | Race build timestamp or catalog generated timestamp | `officialUpdate` | `meeting.officialUpdate` | Available where timestamp exists |
| Race list | Meeting races in catalog | `buildRaceSummary` | Race strip | Available |

## Legitimate Gaps

- Scratchings are zero when no runner in the current catalog is marked scratched.
- Weather values remain unavailable where the catalog does not supply current weather fields.
- Official update falls back to the catalog generated timestamp when a race timestamp is not supplied.

## Governance Notes

- React displays service fields only.
- React does not calculate racing metrics, rankings, market fields, speed, suitability, form momentum, or freshness.
- Track-condition colours are scoped to the condition value only.
- Generic meeting notes were removed from the visible workspace.
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
    text = MEETINGS_SERVICE.read_text(encoding="utf-8")
    text = text.replace('  confidence: "official" | "governed" | "unavailable";', '  authority: "official" | "governed" | "unavailable";')
    text = text.replace("  edgeiqRead: string[];\n", "")
    text = text.replace(
        r'''function buildEdgeiqRead(
  track: string,
  rail: string,
  weather: string,
  wind: string,
): string[] {
  const notes: string[] = [];
  if (track !== "Not supplied") notes.push(`${track} track`);
  if (rail !== "Not supplied") notes.push(`Rail ${rail}`);
  if (weather !== "Weather unavailable") notes.push(weather);
  if (wind !== "Wind unavailable") notes.push(`Wind ${wind}`);
  if (notes.length === 0) return ["Limited current evidence"];
  return notes.slice(0, 3);
}

''',
        "",
    )
    text = text.replace(
        '{ label: "Today\'s Track", value: summary.track, confidence: summary.track === "Not supplied" ? "unavailable" : "official" }',
        '{ label: "Today\'s Track", value: summary.track, authority: summary.track === "Not supplied" ? "unavailable" : "official" }',
    )
    text = text.replace(
        '{ label: "Rail", value: summary.rail, confidence: summary.rail === "Not supplied" ? "unavailable" : "official" }',
        '{ label: "Rail", value: summary.rail, authority: summary.rail === "Not supplied" ? "unavailable" : "official" }',
    )
    text = text.replace(
        '{ label: "Weather", value: summary.weather, confidence: summary.weather === "Weather unavailable" ? "unavailable" : "governed" }',
        '{ label: "Weather", value: summary.weather, authority: summary.weather === "Weather unavailable" ? "unavailable" : "governed" }',
    )
    text = text.replace(
        '{ label: "Wind", value: summary.wind, confidence: summary.wind === "Wind unavailable" ? "unavailable" : "governed" }',
        '{ label: "Wind", value: summary.wind, authority: summary.wind === "Wind unavailable" ? "unavailable" : "governed" }',
    )
    text = text.replace(
        '{ label: "Official Update", value: summary.officialUpdate, confidence: summary.officialUpdate === "Not supplied" ? "unavailable" : "official" }',
        '{ label: "Official Update", value: summary.officialUpdate, authority: summary.officialUpdate === "Not supplied" ? "unavailable" : "official" }',
    )
    text = text.replace("    edgeiqRead: buildEdgeiqRead(track, rail, weather, wind),\n", "")
    MEETINGS_SERVICE.write_text(text, encoding="utf-8")


def append_css() -> None:
    text = CSS_FILE.read_text(encoding="utf-8")
    marker = "/* EDGEIQ MEETINGS FINAL SPEC V1 */"
    if marker in text:
        before = text.split(marker)[0].rstrip()
        text = before + "\n" + CSS_APPEND.lstrip()
    else:
        text = text.rstrip() + "\n" + CSS_APPEND.lstrip()
    CSS_FILE.write_text(text, encoding="utf-8")


def main() -> None:
    checkpoint([MEETINGS_COMPONENT, MEETINGS_SERVICE, CSS_FILE])
    MEETINGS_COMPONENT.write_text(COMPONENT_SOURCE, encoding="utf-8")
    patch_service()
    append_css()
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACE_FILE.write_text(TRACE_SOURCE, encoding="utf-8")
    AUDIT_SCRIPT.write_text(AUDIT_SOURCE, encoding="utf-8")
    print(f"Checkpoint: {CHECKPOINT_DIR}")
    print("EDGEIQ_MEETINGS_FINAL_SPEC_PATCH_APPLIED")


if __name__ == "__main__":
    main()
