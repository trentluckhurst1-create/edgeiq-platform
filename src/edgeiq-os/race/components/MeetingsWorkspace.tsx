import { useEffect, useMemo, useState } from "react";
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
