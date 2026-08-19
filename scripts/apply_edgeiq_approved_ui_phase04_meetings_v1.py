from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE04_MEETINGS_{STAMP}"


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


TSX = """import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";
import {
  loadMeetingsWorkspaceViewModel,
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

function display(value: unknown, fallback = "Unavailable"): string {
  const text = String(value ?? "").replace(/\\s+/g, " ").trim();
  if (!text || text === "-" || ["null", "undefined", "none"].includes(text.toLowerCase())) return fallback;
  return text;
}

function shortDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", month: "short" }).format(parsed);
}

export function MeetingsWorkspace({
  selectedDayKey,
  selectedMeetingKey,
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
    return viewModel?.days.find((day) => day.key === selectedDayKey) ?? viewModel?.days[0] ?? null;
  }, [selectedDayKey, viewModel]);

  const selectedMeeting = useMemo(() => {
    if (!activeDay) return null;
    return activeDay.meetings.find((meeting) => meeting.meetingKey === selectedMeetingKey) ?? activeDay.meetings[0] ?? null;
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
      <section className="eiq-meetings-approved">
        <section className="eiq-meetings-approved__empty">Loading the three-day race programme.</section>
      </section>
    );
  }

  if (status === "ERROR" || !viewModel || !activeDay) {
    return (
      <section className="eiq-meetings-approved">
        <section className="eiq-meetings-approved__empty">The three-day race programme could not be loaded.</section>
      </section>
    );
  }

  const timelineMeetings = activeDay.meetings.slice(0, 5);

  return (
    <section className="eiq-meetings-approved" aria-label="Meetings">
      <header className="eiq-meetings-approved__header">
        <div>
          <h1>MEETINGS</h1>
          <p>Three day racing outlook. Select a meeting to view races and details.</p>
        </div>
        <div className="eiq-meetings-approved__days" aria-label="Date range">
          <span>DATE RANGE (BUILDER CONTROLLED)</span>
          <div>
            {viewModel.days.map((day) => (
              <button
                key={day.key}
                type="button"
                className={day.key === activeDay.key ? "is-active" : ""}
                onClick={() => onDayChange(day.key)}
              >
                <strong>{day.label}</strong>
                <small>{shortDate(day.date)}</small>
              </button>
            ))}
          </div>
        </div>
      </header>

      <section className="eiq-meetings-approved__table-panel">
        <header>
          <strong>MEETINGS ({activeDay.displayDate.toUpperCase()})</strong>
          <div>
            <input aria-label="Search meetings" placeholder="Search meetings..." />
            <button className="eiq-approved-button" type="button">FILTERS</button>
            {selectedMeeting ? (
              <button className="eiq-approved-button" type="button" onClick={() => onOpenMeeting(selectedMeeting.rawMeeting)}>
                OPEN MEETING
              </button>
            ) : null}
          </div>
        </header>
        <div className="eiq-meetings-approved__table-wrap">
          <table className="eiq-approved-table eiq-meetings-approved__table">
            <thead>
              <tr>
                <th>SELECT</th>
                <th>MEETING</th>
                <th>STATE</th>
                <th>RAIL</th>
                <th>TRACK</th>
                <th>WEATHER</th>
                <th>RACES</th>
                <th>DECLARED</th>
                <th>SCRATCHINGS</th>
              </tr>
            </thead>
            <tbody>
              {activeDay.meetings.map((meeting) => (
                <tr key={meeting.meetingKey} className={meeting.meetingKey === selectedMeeting?.meetingKey ? "is-selected" : ""}>
                  <td>
                    <button className="eiq-meetings-approved__select" type="button" onClick={() => onSelectMeeting(meeting.rawMeeting)}>
                      {meeting.meetingKey === selectedMeeting?.meetingKey ? "Selected" : "Select"}
                    </button>
                  </td>
                  <td>
                    <button className="eiq-meetings-approved__meeting" type="button" onClick={() => onSelectMeeting(meeting.rawMeeting)}>
                      {display(meeting.meeting)}
                    </button>
                  </td>
                  <td>{display(meeting.state, "Not supplied")}</td>
                  <td>{display(meeting.rail, "Not supplied")}</td>
                  <td>{display(meeting.track, "Not supplied")}</td>
                  <td>{display(meeting.weather, "Weather unavailable")}</td>
                  <td>{meeting.races}</td>
                  <td>{meeting.declared}</td>
                  <td>{meeting.scratchings}</td>
                </tr>
              ))}
              {!activeDay.meetings.length ? <tr><td colSpan={9}>No meetings are loaded for this day.</td></tr> : null}
            </tbody>
          </table>
        </div>
        <footer>
          <span>Showing 1 to {activeDay.meetings.length} of {activeDay.meetings.length} meetings</span>
          <span>Current</span>
          <span>Completed</span>
          <span>Abandoned</span>
          <span>Postponed</span>
        </footer>
      </section>

      <section className="eiq-meetings-approved__timeline">
        <header><strong>RACE START TIMES (ALL MEETINGS)</strong></header>
        <div className="eiq-meetings-approved__time-head">
          <span>11AM</span><span>12PM</span><span>1PM</span><span>2PM</span><span>3PM</span><span>4PM</span><span>5PM</span><span>6PM</span>
        </div>
        {timelineMeetings.map((meeting) => (
          <div className="eiq-meetings-approved__time-row" key={meeting.meetingKey}>
            <strong>{display(meeting.meeting)} ({meeting.races})</strong>
            <div>
              {meeting.raceSummaries.slice(0, 7).map((race, index) => (
                <button
                  key={race.raceKey}
                  type="button"
                  style={{ left: `${Math.min(92, Math.max(3, 10 + index * 13))}%` }}
                  onClick={() => onOpenRace(meeting.rawMeeting, race.rawRace, index)}
                >
                  {race.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </section>
    </section>
  );
}
"""


CSS_APPEND = r"""
/* EDGEIQ APPROVED UI PHASE 04 MEETINGS */
.eiq-meetings-approved {
  display: grid;
  gap: 14px;
  color: var(--eiq-approved-text);
}

.eiq-meetings-approved__header {
  min-height: 86px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 440px;
  align-items: start;
  gap: 24px;
}

.eiq-meetings-approved__header h1 {
  margin: 0 0 8px;
  color: var(--eiq-approved-navy);
  font-size: 28px;
  line-height: 1.1;
  font-weight: 900;
}

.eiq-meetings-approved__header p {
  margin: 0;
  color: var(--eiq-approved-text);
  font-size: 14px;
}

.eiq-meetings-approved__days > span {
  display: block;
  margin: 0 0 10px;
  color: var(--eiq-approved-navy);
  font-size: 11px;
  font-weight: 900;
  text-align: center;
}

.eiq-meetings-approved__days > div {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.eiq-meetings-approved__days button {
  height: 42px;
  border: 1px solid var(--eiq-approved-line-strong);
  border-radius: 5px;
  background: #ffffff;
  color: var(--eiq-approved-navy);
  font: inherit;
  cursor: pointer;
}

.eiq-meetings-approved__days button.is-active {
  background: var(--eiq-approved-blue);
  border-color: var(--eiq-approved-blue);
  color: #ffffff;
}

.eiq-meetings-approved__days strong,
.eiq-meetings-approved__days small {
  display: block;
}

.eiq-meetings-approved__table-panel,
.eiq-meetings-approved__timeline {
  border: 1px solid var(--eiq-approved-line);
  border-radius: 6px;
  background: #ffffff;
}

.eiq-meetings-approved__table-panel > header {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 14px;
  border-bottom: 1px solid var(--eiq-approved-line);
}

.eiq-meetings-approved__table-panel > header strong,
.eiq-meetings-approved__timeline > header strong {
  color: var(--eiq-approved-navy);
  font-size: 15px;
  font-weight: 900;
}

.eiq-meetings-approved__table-panel > header div {
  display: flex;
  align-items: center;
  gap: 12px;
}

.eiq-meetings-approved__table-panel input {
  width: 220px;
  height: 34px;
  border: 1px solid var(--eiq-approved-line-strong);
  border-radius: 4px;
  background: #ffffff;
  color: var(--eiq-approved-text);
  padding: 0 12px;
  font: inherit;
  font-size: 13px;
}

.eiq-meetings-approved__table-wrap {
  overflow: auto;
}

.eiq-meetings-approved__table th,
.eiq-meetings-approved__table td {
  text-align: center;
}

.eiq-meetings-approved__table th:nth-child(2),
.eiq-meetings-approved__table td:nth-child(2) {
  text-align: left;
}

.eiq-meetings-approved__table tr.is-selected td {
  background: #f5f9ff;
}

.eiq-meetings-approved__select,
.eiq-meetings-approved__meeting {
  border: 0;
  background: transparent;
  color: var(--eiq-approved-blue);
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.eiq-meetings-approved__select {
  color: var(--eiq-approved-muted);
  font-size: 12px;
}

.eiq-meetings-approved__table-panel > footer {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 0 14px;
  color: var(--eiq-approved-muted);
  font-size: 13px;
}

.eiq-meetings-approved__timeline {
  min-height: 274px;
  padding: 14px;
}

.eiq-meetings-approved__timeline > header {
  height: 34px;
}

.eiq-meetings-approved__time-head {
  height: 32px;
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  align-items: center;
  border-bottom: 1px solid var(--eiq-approved-line);
  color: var(--eiq-approved-navy);
  font-size: 13px;
  font-weight: 900;
  text-align: center;
}

.eiq-meetings-approved__time-row {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr);
  height: 36px;
  align-items: center;
  border-bottom: 1px solid var(--eiq-approved-line);
}

.eiq-meetings-approved__time-row:last-child {
  border-bottom: 0;
}

.eiq-meetings-approved__time-row > strong {
  color: var(--eiq-approved-navy);
  font-size: 13px;
}

.eiq-meetings-approved__time-row > div {
  position: relative;
  height: 100%;
}

.eiq-meetings-approved__time-row button {
  position: absolute;
  top: 6px;
  width: 42px;
  height: 24px;
  margin-left: -21px;
  border: 1px solid #7ba6ff;
  border-radius: 4px;
  background: #ffffff;
  color: var(--eiq-approved-blue);
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.eiq-meetings-approved__empty {
  border: 1px solid var(--eiq-approved-line);
  border-radius: 6px;
  background: #ffffff;
  padding: 18px;
  color: var(--eiq-approved-muted);
}

@media (max-width: 1100px) {
  .eiq-meetings-approved__header {
    grid-template-columns: 1fr;
  }
}
"""


def main() -> None:
    tsx = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
    css = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
    checkpoint([tsx, css])
    write(tsx, TSX)
    css_text = read(css)
    if "EDGEIQ APPROVED UI PHASE 04 MEETINGS" not in css_text:
        write(css, css_text.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n")
    print(f"checkpoint={CHECKPOINT}")
    print("EDGEIQ_APPROVED_UI_PHASE04_MEETINGS_PASS")


if __name__ == "__main__":
    main()
