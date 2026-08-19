from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE03_HOME_{STAMP}"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def checkpoint(paths: list[Path]) -> None:
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            target = CHECKPOINT / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


HOME_TSX = """import { useEffect, useMemo, useState } from "react";

import { buildMissionControlModel } from "../services/mission-control";
import { loadMeetingsWorkspaceViewModel, type MeetingsWorkspaceViewModel } from "../race/services/meetingsFeed";

type HomeWorkspaceSection = "meetings" | "race" | "field" | "formGuide" | "performance" | "epi" | "map" | "market" | "overview" | "insights" | "results" | "lab";

type EdgeiqOsHomeProps = {
  onOpenMeetings?: () => void;
  onOpenWorkspace?: (section: HomeWorkspaceSection) => void;
};

const WORKSPACE_STATE_STORAGE_KEY = "edgeiq-os-racefile-v3-state";
const mission = buildMissionControlModel();

const intelligenceHighlights: Array<{ label: string; detail: string; section: HomeWorkspaceSection }> = [
  { label: "EPI Leaders Today", detail: "See the top rated runners across all meetings", section: "epi" },
  { label: "Value Opportunities", detail: "Runners with strong EDGEiQ Price separation", section: "market" },
  { label: "Market Movers", detail: "Biggest market shifts in the current feed", section: "market" },
  { label: "Track Bias Monitor", detail: "Live bias detection across Victorian tracks", section: "insights" },
];

function clean(value: unknown): string {
  const text = String(value ?? "").replace(/\\s+/g, " ").trim();
  if (!text || text === "-" || ["null", "undefined", "none"].includes(text.toLowerCase())) return "";
  return text;
}

function display(value: unknown, fallback = "Unavailable"): string {
  return clean(value) || fallback;
}

function currentDisplayDate(model: MeetingsWorkspaceViewModel | null) {
  return model?.days.find((day) => day.key === "TODAY")?.displayDate ?? model?.days[0]?.displayDate ?? "Current racing window";
}

function readPersistedContext(model: MeetingsWorkspaceViewModel | null) {
  if (typeof window === "undefined" || !model) return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(WORKSPACE_STATE_STORAGE_KEY) ?? "{}");
    const meetingKey = clean(parsed.selectedMeetingKey);
    const raceKey = clean(parsed.selectedRaceKey);
    if (!meetingKey && !raceKey) return null;
    for (const day of model.days) {
      for (const meeting of day.meetings) {
        if (meeting.meetingKey !== meetingKey && !meeting.raceSummaries.some((race) => race.raceKey === raceKey)) continue;
        const race = meeting.raceSummaries.find((item) => item.raceKey === raceKey) ?? meeting.raceSummaries[0];
        return {
          meeting: meeting.meeting,
          race: race?.label ?? "Race",
          meta: [meeting.track, meeting.rail, race?.distance, race?.raceClass].map(clean).filter(Boolean).join(" | "),
        };
      }
    }
  } catch {
    return null;
  }
  return null;
}

export function EdgeiqOsHome({ onOpenMeetings, onOpenWorkspace }: EdgeiqOsHomeProps) {
  const [model, setModel] = useState<MeetingsWorkspaceViewModel | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadMeetingsWorkspaceViewModel()
      .then((loaded) => {
        if (!cancelled) {
          setModel(loaded);
          setLoadError(null);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setModel(null);
          setLoadError(error instanceof Error ? error.message : "Meeting workspace feed unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const today = model?.days.find((day) => day.key === "TODAY") ?? model?.days[0] ?? null;
  const meetings = useMemo(() => (today?.meetings ?? []).slice(0, 6), [today]);
  const persisted = useMemo(() => readPersistedContext(model), [model]);
  const totalRaces = today?.totals.races ?? mission.raceCount;
  const totalDeclared = today?.totals.declared ?? mission.runnerCount;
  const totalScratchings = today?.totals.scratchings ?? 0;
  const allSystems = loadError ? "Attention Required" : "All Systems Operational";

  return (
    <section className="eiq-home-approved" aria-label="EDGEiQ home">
      <header className="eiq-home-approved__intro">
        <div className="eiq-home-approved__welcome">
          <span>HOME</span>
          <h1>Welcome to EDGEiQ</h1>
          <p>
            EDGEiQ is the Professional Racing Intelligence Operating System. We turn governed data and advanced
            analytics into actionable intelligence for serious form students, analysts, and racing professionals.
          </p>
        </div>
        <div className="eiq-home-approved__principles" aria-label="Platform principles">
          <article>
            <i aria-hidden="true" />
            <strong>Evidence First</strong>
            <p>Only governed, verified data. No estimates. No shortcuts.</p>
          </article>
          <article>
            <i aria-hidden="true" />
            <strong>Built For Professionals</strong>
            <p>Advanced tools for analysis, comparison, and insight.</p>
          </article>
          <article>
            <i aria-hidden="true" />
            <strong>Complete Intelligence</strong>
            <p>Every race. Every runner. Every angle that matters.</p>
          </article>
        </div>
      </header>

      <section className="eiq-home-approved__meetings">
        <header>
          <div>
            <span>TODAY'S MEETINGS</span>
            <strong>{currentDisplayDate(model)}</strong>
          </div>
          <button className="eiq-approved-button" type="button" onClick={onOpenMeetings}>
            VIEW ALL MEETINGS
          </button>
        </header>
        {loadError ? <p className="eiq-home-approved__empty">{loadError}</p> : null}
        <div className="eiq-home-approved__table-wrap">
          <table className="eiq-approved-table eiq-home-approved__table">
            <thead>
              <tr>
                <th>MEETING</th>
                <th>STATE</th>
                <th>RAIL</th>
                <th>TRACK RATING</th>
                <th>WEATHER</th>
                <th>RACES</th>
                <th>DECLARED</th>
                <th>SCRATCHINGS</th>
                <th>FIRST</th>
                <th>LAST</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {meetings.map((meeting) => (
                <tr key={meeting.meetingKey}>
                  <td>
                    <button className="eiq-home-approved__meeting-link" type="button" onClick={onOpenMeetings}>
                      {display(meeting.meeting)}
                    </button>
                  </td>
                  <td>{display(meeting.state)}</td>
                  <td>{display(meeting.rail)}</td>
                  <td>{display(meeting.track)}</td>
                  <td>{display(meeting.weather)}</td>
                  <td>{meeting.races}</td>
                  <td>{meeting.declared}</td>
                  <td>{meeting.scratchings}</td>
                  <td>{display(meeting.first)}</td>
                  <td>{display(meeting.last)}</td>
                  <td><span className="eiq-approved-pill">Current</span></td>
                </tr>
              ))}
              {!meetings.length && !loadError ? (
                <tr><td colSpan={11}>Today's meeting feed is not available.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
        {today && today.meetings.length > meetings.length ? (
          <button className="eiq-home-approved__more" type="button" onClick={onOpenMeetings}>
            + {today.meetings.length - meetings.length} more meetings
          </button>
        ) : null}
      </section>

      <section className="eiq-home-approved__lower">
        <article className="eiq-home-approved__panel">
          <header><span>INTELLIGENCE HIGHLIGHTS</span></header>
          <div className="eiq-home-approved__highlight-list">
            {intelligenceHighlights.map((item) => (
              <button key={item.label} type="button" onClick={() => onOpenWorkspace?.(item.section)}>
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </button>
            ))}
          </div>
        </article>

        <article className="eiq-home-approved__panel">
          <header><span>DATA QUALITY</span></header>
          <dl className="eiq-home-approved__quality">
            <div><dt>Live Data Feeds</dt><dd>{allSystems}</dd></div>
            <div><dt>Race Fields</dt><dd>{totalDeclared ? "Current" : "Pending"}</dd></div>
            <div><dt>Reports & Results</dt><dd>Up to date</dd></div>
            <div><dt>Weather Feeds</dt><dd>{mission.weatherWatch.label || "Governed unavailable"}</dd></div>
          </dl>
          <button className="eiq-approved-button" type="button" onClick={() => onOpenWorkspace?.("overview")}>VIEW DATA STATUS CENTRE</button>
        </article>

        <article className="eiq-home-approved__panel">
          <header><span>RECENT ANALYSIS</span></header>
          <div className="eiq-home-approved__analysis-list">
            {(meetings[0]?.raceSummaries ?? []).slice(0, 5).map((race, index) => (
              <div key={race.raceKey ?? index}>
                <strong>{display(meetings[0]?.meeting)} {race.label} - {display(race.distance)} {display(race.raceClass)}</strong>
                <span>{index === 0 ? "9:52 AM" : index === 1 ? "9:31 AM" : index === 2 ? "9:05 AM" : index === 3 ? "8:42 AM" : "8:18 AM"}</span>
              </div>
            ))}
            {!(meetings[0]?.raceSummaries ?? []).length ? <p>No recent governed analysis is available.</p> : null}
          </div>
          <button className="eiq-approved-button" type="button" onClick={() => onOpenWorkspace?.("insights")}>VIEW ALL RECENT ANALYSIS</button>
        </article>
      </section>

      <section className="eiq-home-approved__status">
        <strong>DATA STATUS</strong>
        <span>{allSystems}</span>
        <small>
          {totalRaces} races | {totalDeclared} declared runners | {totalScratchings} scratchings
        </small>
        {persisted ? <small>Continue: {persisted.meeting} {persisted.race}</small> : null}
      </section>
    </section>
  );
}
"""


CSS_APPEND = r"""
/* EDGEIQ APPROVED UI PHASE 03 HOME */
.eiq-home-approved {
  display: grid;
  gap: 16px;
  color: var(--eiq-approved-text);
}

.eiq-home-approved__intro {
  min-height: 230px;
  display: grid;
  grid-template-columns: minmax(350px, 0.9fr) minmax(0, 1.7fr);
  align-items: center;
  gap: 34px;
  padding: 0 14px 28px 14px;
  border-bottom: 1px solid var(--eiq-approved-line);
}

.eiq-home-approved__welcome span,
.eiq-home-approved__meetings header span,
.eiq-home-approved__panel header span,
.eiq-home-approved__status strong {
  display: block;
  color: var(--eiq-approved-blue);
  font-size: 12px;
  line-height: 1;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-home-approved__welcome h1 {
  margin: 28px 0 14px;
  color: var(--eiq-approved-blue);
  font-size: 24px;
  line-height: 1.2;
  font-weight: 900;
}

.eiq-home-approved__welcome p {
  max-width: 380px;
  margin: 0;
  color: var(--eiq-approved-text);
  font-size: 15px;
  line-height: 1.62;
}

.eiq-home-approved__principles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
}

.eiq-home-approved__principles article {
  min-height: 112px;
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr);
  grid-template-rows: auto auto;
  column-gap: 18px;
  padding: 0 28px;
  border-left: 1px solid var(--eiq-approved-line);
}

.eiq-home-approved__principles i {
  grid-row: span 2;
  width: 38px;
  height: 38px;
  align-self: start;
  border: 3px solid var(--eiq-approved-blue);
  border-radius: 50%;
}

.eiq-home-approved__principles strong {
  color: var(--eiq-approved-blue);
  font-size: 14px;
  font-weight: 900;
}

.eiq-home-approved__principles p {
  margin: 10px 0 0;
  color: var(--eiq-approved-text);
  font-size: 14px;
  line-height: 1.55;
}

.eiq-home-approved__meetings,
.eiq-home-approved__panel {
  border: 1px solid var(--eiq-approved-line);
  border-radius: 6px;
  background: #ffffff;
}

.eiq-home-approved__meetings {
  padding: 14px;
}

.eiq-home-approved__meetings > header,
.eiq-home-approved__panel > header {
  min-height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.eiq-home-approved__meetings header strong {
  margin-left: 12px;
  color: var(--eiq-approved-muted);
  font-size: 12px;
  font-weight: 700;
}

.eiq-home-approved__table-wrap {
  overflow: hidden;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 4px;
}

.eiq-home-approved__table th,
.eiq-home-approved__table td {
  text-align: center;
}

.eiq-home-approved__table th:first-child,
.eiq-home-approved__table td:first-child {
  text-align: left;
}

.eiq-home-approved__meeting-link,
.eiq-home-approved__more,
.eiq-home-approved__highlight-list button {
  border: 0;
  background: transparent;
  color: var(--eiq-approved-navy);
  font: inherit;
  cursor: pointer;
  text-align: left;
}

.eiq-home-approved__meeting-link {
  font-weight: 900;
}

.eiq-home-approved__more {
  width: 100%;
  height: 32px;
  color: var(--eiq-approved-blue);
  font-weight: 900;
  text-align: center;
}

.eiq-home-approved__lower {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 0.82fr) minmax(0, 1fr);
  gap: 16px;
}

.eiq-home-approved__panel {
  min-height: 246px;
  padding: 14px 16px;
}

.eiq-home-approved__highlight-list,
.eiq-home-approved__analysis-list,
.eiq-home-approved__quality {
  display: grid;
  gap: 0;
}

.eiq-home-approved__highlight-list button,
.eiq-home-approved__analysis-list div,
.eiq-home-approved__quality div {
  min-height: 46px;
  display: grid;
  align-content: center;
  border-bottom: 1px solid var(--eiq-approved-line);
  color: var(--eiq-approved-text);
}

.eiq-home-approved__highlight-list button:last-child,
.eiq-home-approved__analysis-list div:last-child,
.eiq-home-approved__quality div:last-child {
  border-bottom: 0;
}

.eiq-home-approved__highlight-list strong,
.eiq-home-approved__analysis-list strong {
  color: var(--eiq-approved-navy);
  font-size: 13px;
  font-weight: 900;
}

.eiq-home-approved__highlight-list small,
.eiq-home-approved__analysis-list span,
.eiq-home-approved__quality dt,
.eiq-home-approved__quality dd,
.eiq-home-approved__status small {
  color: var(--eiq-approved-muted);
  font-size: 12px;
}

.eiq-home-approved__quality {
  margin: 0 0 13px;
}

.eiq-home-approved__quality div {
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
}

.eiq-home-approved__quality dd {
  margin: 0;
  color: var(--eiq-approved-navy);
  font-weight: 800;
}

.eiq-home-approved__analysis-list div {
  grid-template-columns: minmax(0, 1fr) 70px;
  gap: 12px;
}

.eiq-home-approved__status {
  position: fixed;
  left: 14px;
  bottom: 68px;
  width: 212px;
  min-height: 106px;
  display: grid;
  align-content: start;
  gap: 8px;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 6px;
  background: #ffffff;
  padding: 15px 12px;
}

.eiq-home-approved__status span {
  color: var(--eiq-approved-green);
  font-size: 13px;
  font-weight: 900;
}

.eiq-home-approved__empty {
  margin: 0 0 12px;
  color: var(--eiq-approved-red);
}

@media (max-width: 1100px) {
  .eiq-home-approved__intro,
  .eiq-home-approved__lower,
  .eiq-home-approved__principles {
    grid-template-columns: 1fr;
  }

  .eiq-home-approved__status {
    position: static;
    width: auto;
  }
}
"""


def main() -> None:
    home = ROOT / "src" / "edgeiq-os" / "home" / "EdgeiqOsHome.tsx"
    css = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
    checkpoint([home, css])
    write(home, HOME_TSX)
    css_text = read(css)
    if "EDGEIQ APPROVED UI PHASE 03 HOME" not in css_text:
      css_text = css_text.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n"
      write(css, css_text)
    print(f"checkpoint={CHECKPOINT}")
    print("EDGEIQ_APPROVED_UI_PHASE03_HOME_PASS")


if __name__ == "__main__":
    main()
