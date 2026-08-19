from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingsFeed.ts"
PRESENTATION = ROOT / "src" / "edgeiq-os" / "design-system" / "presentation.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

CSS_MARKER = "/* EDGEIQ MEETINGS WORKSPACE V1 LOCKED SPECIFICATION */"


COMPONENT_SOURCE = r'''import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";
import {
  canonicalRailDisplay,
  canonicalTrackDisplayName,
  canonicalTrackRatingDisplay,
  canonicalWeatherDisplay,
  cleanProductText,
} from "../../design-system/presentation";
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

type MeetingStatusFilter = "Current" | "Completed" | "Abandoned" | "Postponed";

const STATUS_FILTERS: MeetingStatusFilter[] = ["Current", "Completed", "Abandoned", "Postponed"];

function display(value: unknown, fallback = "Not Supplied"): string {
  return cleanProductText(value, fallback);
}

function displayTrack(value: unknown, fallback = "Not Supplied"): string {
  return canonicalTrackDisplayName(value) || fallback;
}

function shortDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", month: "short" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}

function trackRatingClass(value: unknown): string {
  const text = String(value ?? "").toLowerCase();
  if (text.includes("firm")) return "is-firm";
  if (text.includes("good")) return "is-good";
  if (text.includes("soft")) return "is-soft";
  if (text.includes("heavy")) return "is-heavy";
  if (text.includes("synthetic")) return "is-synthetic";
  return "is-awaiting";
}

function meetingStatusFilter(value: unknown): MeetingStatusFilter {
  const text = String(value ?? "").toLowerCase();
  if (text.includes("abandon")) return "Abandoned";
  if (text.includes("postpon")) return "Postponed";
  if (text.includes("result") || text.includes("complete") || text.includes("finalised")) return "Completed";
  return "Current";
}

function parseRaceTime(value: unknown, selectedDate: string): Date | null {
  const text = cleanProductText(value, "");
  if (!text || text === "Not Supplied") return null;
  const direct = new Date(text);
  if (!Number.isNaN(direct.getTime())) return direct;
  const match = text.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
  if (!match) return null;
  let hour = Number(match[1]);
  const minute = Number(match[2] ?? "0");
  const suffix = match[3]?.toLowerCase();
  if (suffix === "pm" && hour < 12) hour += 12;
  if (suffix === "am" && hour === 12) hour = 0;
  const [year, month, day] = selectedDate.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day, hour, minute);
}

function formatHourLabel(date: Date): string {
  return new Intl.DateTimeFormat("en-AU", {
    hour: "numeric",
    hour12: true,
    timeZone: "Australia/Melbourne",
  })
    .format(date)
    .replace(/\s/g, "")
    .toUpperCase();
}

function timelineHours(meetings: MeetingSummaryViewModel[], selectedDate: string): Date[] {
  const times = meetings
    .flatMap((meeting) => meeting.raceSummaries.map((race) => parseRaceTime(race.time, selectedDate)))
    .filter((time): time is Date => Boolean(time));
  if (!times.length) return [];
  const startHour = Math.max(0, Math.min(...times.map((time) => time.getHours())) - 1);
  const endHour = Math.min(23, Math.max(...times.map((time) => time.getHours())) + 1);
  const [year, month, day] = selectedDate.split("-").map(Number);
  const hours: Date[] = [];
  for (let hour = startHour; hour <= endHour; hour += 1) {
    hours.push(new Date(year, month - 1, day, hour, 0));
  }
  return hours;
}

function racePositionPct(time: Date, hours: Date[]): number {
  if (hours.length < 2) return 0;
  const start = hours[0].getTime();
  const end = hours[hours.length - 1].getTime();
  if (end <= start) return 0;
  return Math.min(96, Math.max(2, ((time.getTime() - start) / (end - start)) * 100));
}

function raceChipClass(status: unknown, selected = false): string {
  const filter = meetingStatusFilter(status);
  const classes = ["eiq-meetings-v1-race-chip", `is-${filter.toLowerCase()}`];
  if (selected) classes.push("is-selected");
  return classes.join(" ");
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
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<MeetingStatusFilter>("Current");
  const [selectedRaceKey, setSelectedRaceKey] = useState<string | null>(null);

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

  const availableStatusFilters = useMemo(() => {
    if (!activeDay) return [];
    return STATUS_FILTERS.filter((filter) => activeDay.meetings.some((meeting) => meetingStatusFilter(meeting.status) === filter));
  }, [activeDay]);

  const effectiveStatusFilter = availableStatusFilters.includes(statusFilter) ? statusFilter : availableStatusFilters[0] ?? statusFilter;

  const filteredMeetings = useMemo(() => {
    if (!activeDay) return [];
    const search = searchText.trim().toLowerCase();
    return activeDay.meetings.filter((meeting) => {
      const matchesSearch = !search || displayTrack(meeting.meeting).toLowerCase().includes(search);
      const matchesStatus = meetingStatusFilter(meeting.status) === effectiveStatusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [activeDay, effectiveStatusFilter, searchText]);

  const timelineMeetings = filteredMeetings.slice(0, 5);
  const hours = useMemo(() => timelineHours(timelineMeetings, activeDay?.date ?? ""), [activeDay?.date, timelineMeetings]);

  if (status === "LOADING") {
    return (
      <section className="eiq-meetings-v1">
        <section className="eiq-meetings-v1-empty">Loading the three-day race programme.</section>
      </section>
    );
  }

  if (status === "ERROR" || !viewModel || !activeDay) {
    return (
      <section className="eiq-meetings-v1">
        <section className="eiq-meetings-v1-empty">No meetings published for this date.</section>
      </section>
    );
  }

  const startRow = filteredMeetings.length ? 1 : 0;
  const endRow = filteredMeetings.length;

  return (
    <section className="eiq-meetings-v1" aria-label="Meetings" data-edgeiq-workspace-key="MEETINGS" data-edgeiq-mounted-component="MeetingsWorkspace">
      <header className="eiq-meetings-v1-header">
        <div>
          <h1>MEETINGS</h1>
          <p>Three day racing outlook. Select a meeting to view races and details.</p>
        </div>
        <fieldset className="eiq-meetings-v1-date-range" aria-label="Date range">
          <legend>DATE RANGE</legend>
          <div>
            {viewModel.days.map((day) => (
              <button
                key={day.key}
                type="button"
                className={day.key === activeDay.key ? "is-active" : ""}
                aria-pressed={day.key === activeDay.key}
                onClick={() => onDayChange(day.key)}
              >
                <strong>{day.label}</strong>
                <small>{shortDate(day.date)}</small>
              </button>
            ))}
          </div>
        </fieldset>
      </header>

      <section className="eiq-meetings-v1-card" aria-label={`Meetings for ${activeDay.displayDate}`}>
        <header className="eiq-meetings-v1-card-header">
          <strong>MEETINGS ({activeDay.displayDate.toUpperCase()})</strong>
          <div className="eiq-meetings-v1-actions">
            <label>
              <span>Search meetings</span>
              <input
                aria-label="Search meetings"
                placeholder="Search meetings"
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
              />
            </label>
            <button className="eiq-meetings-v1-button is-secondary" type="button">Filters</button>
            <button
              className="eiq-meetings-v1-button is-primary"
              type="button"
              disabled={!selectedMeeting}
              onClick={() => selectedMeeting && onOpenMeeting(selectedMeeting.rawMeeting)}
            >
              Open Meeting
            </button>
          </div>
        </header>
        {filteredMeetings.length ? (
          <div className="eiq-meetings-v1-table-wrap">
            <table className="eiq-meetings-v1-table">
              <colgroup>
                <col style={{ width: "64px" }} />
                <col style={{ width: "150px" }} />
                <col style={{ width: "64px" }} />
                <col style={{ width: "130px" }} />
                <col style={{ width: "130px" }} />
                <col style={{ width: "150px" }} />
                <col style={{ width: "72px" }} />
                <col style={{ width: "92px" }} />
                <col style={{ width: "104px" }} />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">SELECT</th>
                  <th scope="col" className="is-left">MEETING</th>
                  <th scope="col">STATE</th>
                  <th scope="col">RAIL</th>
                  <th scope="col">TRACK</th>
                  <th scope="col">WEATHER</th>
                  <th scope="col">RACES</th>
                  <th scope="col">DECLARED</th>
                  <th scope="col">SCRATCHINGS</th>
                </tr>
              </thead>
              <tbody>
                {filteredMeetings.map((meeting) => {
                  const isSelected = meeting.meetingKey === selectedMeeting?.meetingKey;
                  const trackRating = canonicalTrackRatingDisplay(meeting.track);
                  return (
                    <tr
                      key={meeting.meetingKey}
                      className={isSelected ? "is-selected" : ""}
                      aria-selected={isSelected}
                      tabIndex={0}
                      onClick={() => onSelectMeeting(meeting.rawMeeting)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelectMeeting(meeting.rawMeeting);
                        }
                      }}
                    >
                      <td>
                        <button
                          className="eiq-meetings-v1-select"
                          type="button"
                          aria-pressed={isSelected}
                          onClick={(event) => {
                            event.stopPropagation();
                            onSelectMeeting(meeting.rawMeeting);
                          }}
                        >
                          {isSelected ? "Selected" : "Select"}
                        </button>
                      </td>
                      <td className="is-left">
                        <button
                          className="eiq-meetings-v1-meeting-name"
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            onSelectMeeting(meeting.rawMeeting);
                          }}
                        >
                          {displayTrack(meeting.meeting)}
                        </button>
                      </td>
                      <td>{display(meeting.state, "VIC")}</td>
                      <td>{canonicalRailDisplay(meeting.rail)}</td>
                      <td><span className={`eiq-meetings-v1-track-badge ${trackRatingClass(trackRating)}`}>{trackRating}</span></td>
                      <td><span className="eiq-meetings-v1-weather-badge">{canonicalWeatherDisplay(meeting.weather)}</span></td>
                      <td>{meeting.races}</td>
                      <td>{meeting.declared}</td>
                      <td>{meeting.scratchings}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="eiq-meetings-v1-empty">No meetings published for this date.</div>
        )}
        <footer className="eiq-meetings-v1-footer">
          <span>Showing {startRow} to {endRow} of {filteredMeetings.length} meetings</span>
          <nav aria-label="Meeting status filters">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter}
                type="button"
                className={filter === effectiveStatusFilter ? "is-active" : ""}
                aria-pressed={filter === effectiveStatusFilter}
                onClick={() => setStatusFilter(filter)}
              >
                {filter}
              </button>
            ))}
          </nav>
        </footer>
      </section>

      <section className="eiq-meetings-v1-card eiq-meetings-v1-timeline" aria-label="Race start times">
        <header className="eiq-meetings-v1-card-header">
          <strong>RACE START TIMES</strong>
          <span>ALL MEETINGS</span>
        </header>
        {timelineMeetings.length && hours.length ? (
          <div className="eiq-meetings-v1-time-grid">
            <div className="eiq-meetings-v1-time-head" style={{ gridTemplateColumns: `120px repeat(${hours.length}, minmax(72px, 1fr))` }}>
              <span />
              {hours.map((hour) => <span key={hour.toISOString()}>{formatHourLabel(hour)}</span>)}
            </div>
            {timelineMeetings.map((meeting) => (
              <div className="eiq-meetings-v1-time-row" key={meeting.meetingKey}>
                <strong>{displayTrack(meeting.meeting)} ({meeting.races})</strong>
                <div>
                  {meeting.raceSummaries.map((race, index) => {
                    const parsed = parseRaceTime(race.time, activeDay.date);
                    if (!parsed) return null;
                    return (
                      <button
                        key={race.raceKey}
                        type="button"
                        className={raceChipClass(race.status, race.raceKey === selectedRaceKey)}
                        style={{ left: `${racePositionPct(parsed, hours)}%` }}
                        aria-label={`Race ${race.raceNumber}`}
                        onClick={() => {
                          setSelectedRaceKey(race.raceKey);
                          onOpenRace(meeting.rawMeeting, race.rawRace, index);
                        }}
                      >
                        R{race.raceNumber}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        ) : timelineMeetings.length ? (
          <div className="eiq-meetings-v1-unscheduled">
            <p>Race start times not published.</p>
            {timelineMeetings.map((meeting) => (
              <article key={meeting.meetingKey}>
                <strong>{displayTrack(meeting.meeting)} ({meeting.races})</strong>
                <div>
                  {meeting.raceSummaries.map((race, index) => (
                    <button
                      key={race.raceKey}
                      type="button"
                      className={raceChipClass(race.status, race.raceKey === selectedRaceKey)}
                      aria-label={`Race ${race.raceNumber}`}
                      onClick={() => {
                        setSelectedRaceKey(race.raceKey);
                        onOpenRace(meeting.rawMeeting, race.rawRace, index);
                      }}
                    >
                      R{race.raceNumber}
                    </button>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="eiq-meetings-v1-empty">No meetings published for this date.</div>
        )}
      </section>
    </section>
  );
}
'''


CSS_SOURCE = r'''/* EDGEIQ MEETINGS WORKSPACE V1 LOCKED SPECIFICATION */
.eiq-meetings-v1 {
  width: 100%;
  color: var(--eiq-product-text, #172033) !important;
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  line-height: 22px !important;
  padding: 16px 24px 24px !important;
  display: grid;
  gap: 12px;
}

.eiq-meetings-v1 *,
.eiq-meetings-v1 *::before,
.eiq-meetings-v1 *::after {
  box-sizing: border-box;
}

.eiq-meetings-v1-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.eiq-meetings-v1-header h1 {
  margin: 0 0 4px;
  color: var(--eiq-product-text, #172033) !important;
  font-size: 24px !important;
  font-weight: 700 !important;
  line-height: 30px !important;
  letter-spacing: 0 !important;
}

.eiq-meetings-v1-header p {
  margin: 0;
  max-width: 520px;
  color: var(--eiq-product-muted, #5c667a) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  line-height: 20px !important;
}

.eiq-meetings-v1-date-range {
  margin: 0;
  padding: 0;
  border: 0;
  display: grid;
  gap: 8px;
}

.eiq-meetings-v1-date-range legend {
  padding: 0;
  color: var(--eiq-product-muted, #5c667a) !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  line-height: 16px !important;
}

.eiq-meetings-v1-date-range > div {
  display: flex;
  gap: 8px;
}

.eiq-meetings-v1-date-range button {
  min-width: 110px;
  height: 44px;
  border: 1px solid var(--eiq-product-border, #dfe5ee);
  border-radius: 6px;
  background: #ffffff;
  color: var(--eiq-product-text, #172033);
  display: grid;
  place-content: center;
  gap: 2px;
  cursor: pointer;
}

.eiq-meetings-v1-date-range button strong,
.eiq-meetings-v1-date-range button small {
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  line-height: 16px !important;
  letter-spacing: 0 !important;
}

.eiq-meetings-v1-date-range button strong {
  font-size: 13px !important;
  font-weight: 700 !important;
}

.eiq-meetings-v1-date-range button small {
  font-size: 12px !important;
  font-weight: 500 !important;
}

.eiq-meetings-v1-date-range button:hover {
  border-color: var(--eiq-product-blue, #315faa);
  background: #f2f6fc;
}

.eiq-meetings-v1-date-range button:focus-visible,
.eiq-meetings-v1-button:focus-visible,
.eiq-meetings-v1-select:focus-visible,
.eiq-meetings-v1-meeting-name:focus-visible,
.eiq-meetings-v1-footer button:focus-visible,
.eiq-meetings-v1-race-chip:focus-visible {
  outline: 2px solid var(--eiq-product-blue, #315faa);
  outline-offset: 2px;
}

.eiq-meetings-v1-date-range button.is-active {
  border-color: var(--eiq-product-blue, #315faa);
  background: var(--eiq-product-blue, #315faa);
  color: #ffffff;
}

.eiq-meetings-v1-card {
  background: #ffffff !important;
  border: 1px solid var(--eiq-product-border, #dfe5ee) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  overflow: hidden;
}

.eiq-meetings-v1-card-header {
  min-height: 44px;
  padding: 12px !important;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--eiq-product-border, #dfe5ee);
}

.eiq-meetings-v1-card-header strong {
  color: var(--eiq-product-text, #172033) !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  line-height: 20px !important;
  letter-spacing: 0 !important;
}

.eiq-meetings-v1-card-header span {
  color: var(--eiq-product-muted, #5c667a) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  line-height: 16px !important;
}

.eiq-meetings-v1-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.eiq-meetings-v1-actions label {
  display: block;
}

.eiq-meetings-v1-actions label span {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

.eiq-meetings-v1-actions input {
  width: 220px;
  height: 36px;
  border: 1px solid var(--eiq-product-border, #dfe5ee);
  border-radius: 6px;
  padding: 0 10px;
  color: var(--eiq-product-text, #172033);
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  line-height: 16px !important;
}

.eiq-meetings-v1-button {
  height: 36px;
  border-radius: 6px;
  padding: 0 16px;
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 16px !important;
  cursor: pointer;
}

.eiq-meetings-v1-button.is-primary {
  border: 1px solid var(--eiq-product-blue, #315faa);
  background: var(--eiq-product-blue, #315faa);
  color: #ffffff;
}

.eiq-meetings-v1-button.is-primary:disabled {
  border-color: #cbd5e1;
  background: #eef2f7;
  color: #7a8597;
  cursor: not-allowed;
}

.eiq-meetings-v1-button.is-secondary {
  border: 1px solid var(--eiq-product-blue, #315faa);
  background: #ffffff;
  color: var(--eiq-product-blue, #315faa);
}

.eiq-meetings-v1-table-wrap {
  width: 100%;
  overflow-x: auto;
}

.eiq-meetings-v1-table {
  width: 100%;
  min-width: 956px;
  table-layout: fixed;
  border-collapse: collapse;
  background: #ffffff;
}

.eiq-meetings-v1-table th,
.eiq-meetings-v1-table td {
  border-bottom: 1px solid var(--eiq-product-border, #dfe5ee);
  padding: 8px 10px !important;
  text-align: center !important;
  vertical-align: middle !important;
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.eiq-meetings-v1-table th {
  height: 42px !important;
  background: #f7f9fc;
  color: var(--eiq-product-text, #172033) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 16px !important;
  letter-spacing: 0.02em !important;
}

.eiq-meetings-v1-table td {
  min-height: 42px !important;
  height: 42px !important;
  color: var(--eiq-product-text, #172033) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  line-height: 18px !important;
}

.eiq-meetings-v1-table .is-left {
  text-align: left !important;
}

.eiq-meetings-v1-table tbody tr {
  cursor: pointer;
}

.eiq-meetings-v1-table tbody tr:hover td {
  background: #f2f6fc;
}

.eiq-meetings-v1-table tbody tr.is-selected td {
  background: #edf4ff;
}

.eiq-meetings-v1-select,
.eiq-meetings-v1-meeting-name {
  border: 0;
  background: transparent;
  color: var(--eiq-product-blue, #315faa);
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 16px !important;
  cursor: pointer;
}

.eiq-meetings-v1-meeting-name {
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
}

.eiq-meetings-v1-track-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 128px;
  width: 136px;
  max-width: none;
  height: 28px;
  border: 1px solid var(--eiq-product-border, #dfe5ee);
  border-radius: 5px;
  padding: 0 10px;
  overflow: visible;
  text-overflow: clip;
  color: var(--eiq-product-text, #172033);
  background: #f8fafc;
  font-size: 12px !important;
  font-weight: 700 !important;
  line-height: 16px !important;
}

.eiq-meetings-v1-track-badge.is-firm {
  border-color: #b42318;
  background: #b42318;
  color: #ffffff;
}

.eiq-meetings-v1-track-badge.is-good {
  border-color: #22863a;
  background: #22863a;
  color: #ffffff;
}

.eiq-meetings-v1-track-badge.is-soft {
  border-color: #315faa;
  background: #315faa;
  color: #ffffff;
}

.eiq-meetings-v1-track-badge.is-heavy {
  border-color: #111827;
  background: #111827;
  color: #ffffff;
}

.eiq-meetings-v1-track-badge.is-synthetic {
  border-color: var(--eiq-product-blue, #315faa);
  background: #f8fafc;
  color: var(--eiq-product-text, #172033);
}

.eiq-meetings-v1-footer {
  min-height: 40px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--eiq-product-muted, #5c667a);
  font-size: 12px !important;
  font-weight: 500 !important;
  line-height: 16px !important;
}

.eiq-meetings-v1-footer nav {
  display: flex;
  align-items: center;
  gap: 20px;
}

.eiq-meetings-v1-footer button {
  min-height: 36px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--eiq-product-muted, #5c667a);
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  line-height: 16px !important;
  cursor: pointer;
}

.eiq-meetings-v1-footer button.is-active {
  border-bottom-color: var(--eiq-product-blue, #315faa);
  color: var(--eiq-product-blue, #315faa);
  font-weight: 700 !important;
}

.eiq-meetings-v1-timeline {
  min-height: 180px;
}

.eiq-meetings-v1-time-grid,
.eiq-meetings-v1-unscheduled {
  padding: 12px;
}

.eiq-meetings-v1-time-head {
  display: grid;
  align-items: center;
  min-height: 32px;
  border-bottom: 1px solid var(--eiq-product-border, #dfe5ee);
}

.eiq-meetings-v1-time-head span {
  text-align: center;
  color: var(--eiq-product-muted, #5c667a);
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 16px !important;
}

.eiq-meetings-v1-time-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  min-height: 46px;
  align-items: center;
  border-bottom: 1px solid var(--eiq-product-border, #dfe5ee);
}

.eiq-meetings-v1-time-row > strong,
.eiq-meetings-v1-unscheduled article > strong {
  color: var(--eiq-product-text, #172033);
  font-size: 14px !important;
  font-weight: 700 !important;
  line-height: 18px !important;
}

.eiq-meetings-v1-time-row > div {
  position: relative;
  min-height: 38px;
  border-left: 1px solid var(--eiq-product-border, #dfe5ee);
}

.eiq-meetings-v1-time-row > div::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  height: 1px;
  background: var(--eiq-product-border, #dfe5ee);
}

.eiq-meetings-v1-race-chip {
  width: 40px;
  height: 28px;
  border-radius: 5px;
  border: 1px solid var(--eiq-product-blue, #315faa);
  background: #ffffff;
  color: var(--eiq-product-blue, #315faa);
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 16px !important;
  cursor: pointer;
}

.eiq-meetings-v1-time-row .eiq-meetings-v1-race-chip {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
}

.eiq-meetings-v1-race-chip:hover {
  background: #f2f6fc;
}

.eiq-meetings-v1-race-chip.is-current {
  background: var(--eiq-product-blue, #315faa);
  color: #ffffff;
}

.eiq-meetings-v1-race-chip.is-completed {
  border-color: #cbd5e1;
  background: #f1f5f9;
  color: #475569;
}

.eiq-meetings-v1-race-chip.is-abandoned {
  border-color: #b42318;
  background: #fff1f0;
  color: #8a1f14;
}

.eiq-meetings-v1-race-chip.is-postponed {
  border-color: #b45309;
  background: #fff7ed;
  color: #92400e;
}

.eiq-meetings-v1-race-chip.is-selected {
  outline: 2px solid var(--eiq-product-blue, #315faa);
  outline-offset: 2px;
}

.eiq-meetings-v1-unscheduled {
  display: grid;
  gap: 12px;
}

.eiq-meetings-v1-unscheduled p {
  margin: 0;
  color: var(--eiq-product-muted, #5c667a);
  font-size: 14px !important;
  font-weight: 500 !important;
  line-height: 20px !important;
}

.eiq-meetings-v1-unscheduled article {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-height: 42px;
}

.eiq-meetings-v1-unscheduled article > div {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.eiq-meetings-v1-empty {
  min-height: 140px;
  display: grid;
  place-items: center;
  color: var(--eiq-product-muted, #5c667a);
  font-size: 14px !important;
  font-weight: 500 !important;
  line-height: 20px !important;
  text-align: center;
}

@media (max-width: 1365px) {
  .eiq-meetings-v1-header,
  .eiq-meetings-v1-card-header,
  .eiq-meetings-v1-footer {
    flex-wrap: wrap;
  }

  .eiq-meetings-v1-date-range,
  .eiq-meetings-v1-actions {
    width: 100%;
  }

  .eiq-meetings-v1-date-range > div,
  .eiq-meetings-v1-actions {
    justify-content: flex-start;
  }
}
'''


def ensure_presentation_helpers() -> None:
    text = PRESENTATION.read_text(encoding="utf-8")
    if "export function canonicalTrackRatingDisplay" not in text:
        text += r'''

export function canonicalTrackRatingDisplay(value: unknown, fallback = "Awaiting Track Rating"): string {
  const text = cleanProductText(value, "");
  if (!text) return fallback;
  if (/synthetic/i.test(text)) return "Synthetic";
  const match = text.match(/\b(Firm|Good|Soft|Heavy)\s*([0-9]{1,2})?\b/i);
  if (!match) return fallback;
  const label = `${match[1][0].toUpperCase()}${match[1].slice(1).toLowerCase()}${match[2] ? ` ${match[2]}` : ""}`;
  return label.length > 24 ? fallback : label;
}

export function canonicalWeatherDisplay(value: unknown, fallback = "Awaiting Weather Feed"): string {
  const text = cleanProductText(value, "");
  if (!text) return fallback;
  if (/not\s+published/i.test(text)) return "Weather Not Published";
  if (/sun|fine|clear/i.test(text)) return /fine/i.test(text) ? "Fine" : "Sunny";
  if (/cloud/i.test(text)) return "Cloudy";
  if (/overcast/i.test(text)) return "Overcast";
  if (/shower/i.test(text)) return "Showers";
  if (/rain|storm|wet/i.test(text)) return "Rain";
  if (/wind/i.test(text)) return "Windy";
  return text.length > 24 ? fallback : text;
}

export function canonicalRailDisplay(value: unknown, fallback = "Not Supplied"): string {
  const text = cleanProductText(value, "");
  if (!text) return fallback;
  return text.length > 32 ? fallback : text;
}
'''
    if "SOUTHSIDE\\s+PAKENHAM" not in text:
        text = text.replace('[/^SPORTSBET\\s+PAKENHAM$/i, "Pakenham"],', '[/^SPORTSBET\\s+PAKENHAM$/i, "Pakenham"],\n  [/^SOUTHSIDE\\s+PAKENHAM\\s+SYNTHETIC$/i, "Pak Syn"],\n  [/^SOUTHSIDE\\s+PAKENHAM$/i, "Pakenham"],\n  [/^SOUTHSIDE\\s+CRANBOURNE$/i, "Cranbourne"],')
    PRESENTATION.write_text(text, encoding="utf-8")


def patch_meetings_feed() -> None:
    text = SERVICE.read_text(encoding="utf-8")
    text = text.replace(
        'import {\n  loadThreeDayCatalog,\n  type ThreeDayCatalog,\n  type ThreeDayMeeting,\n  type ThreeDayRace,\n  type ThreeDayRunner,\n} from "./threeDayCatalog";',
        'import {\n  loadThreeDayCatalog,\n  type ThreeDayCatalog,\n  type ThreeDayMeeting,\n  type ThreeDayRace,\n  type ThreeDayRunner,\n} from "./threeDayCatalog";\nimport { canonicalTrackRatingDisplay, canonicalWeatherDisplay } from "../../design-system/presentation";',
    )
    old_track = '''function trackRating(race: ThreeDayRace | undefined, meeting: ThreeDayMeeting): string {
  const condition = firstText(
    race?.trackCondition,
    race?.source?.track_condition,
    meeting.trackCondition,
  );
  const rating = firstText(race?.source?.track_rating);
  if (condition && rating && !condition.includes(rating)) return `${condition} ${rating}`;
  return unavailable(condition);
}'''
    new_track = '''function trackRating(race: ThreeDayRace | undefined, meeting: ThreeDayMeeting): string {
  return canonicalTrackRatingDisplay(
    firstText(
      race?.source?.official_track_rating,
      race?.source?.track_rating_short,
      race?.source?.going,
      race?.source?.track_rating,
      race?.source?.track_condition,
      race?.trackCondition,
      meeting.trackCondition,
    ),
  );
}'''
    text = text.replace(old_track, new_track)
    text = text.replace(
        '''function weatherLabel(race: ThreeDayRace | undefined): string {
  return unavailable(firstText(race?.source?.weather), "Weather unavailable");
}''',
        '''function weatherLabel(race: ThreeDayRace | undefined): string {
  return canonicalWeatherDisplay(firstText(race?.source?.weather));
}''',
    )
    text = text.replace('"Wind unavailable"', '"Not supplied"')
    text = text.replace('"Temp unavailable"', '"Not supplied"')
    text = text.replace('summary.weather === "Weather unavailable"', 'summary.weather === "Awaiting Weather Feed"')
    text = text.replace('meeting.weather !== "Weather unavailable"', 'meeting.weather !== "Awaiting Weather Feed"')
    text = text.replace('meeting.wind !== "Wind unavailable"', 'meeting.wind !== "Not supplied"')
    SERVICE.write_text(text, encoding="utf-8")


def write_component() -> None:
    COMPONENT.write_text(COMPONENT_SOURCE, encoding="utf-8")


def append_css() -> None:
    text = CSS.read_text(encoding="utf-8")
    if CSS_MARKER in text:
      text = text.split(CSS_MARKER, 1)[0].rstrip() + "\n\n" + CSS_SOURCE + "\n"
    else:
      text = text.rstrip() + "\n\n" + CSS_SOURCE + "\n"
    CSS.write_text(text, encoding="utf-8")


def main() -> int:
    ensure_presentation_helpers()
    patch_meetings_feed()
    write_component()
    append_css()
    print("EDGEIQ_MEETINGS_WORKSPACE_V1_SPEC_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
