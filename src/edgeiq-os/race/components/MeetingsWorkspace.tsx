import { useEffect, useMemo, useState } from "react";
import { loadThreeDayCatalog, type ThreeDayMeeting, type ThreeDayRace } from "../services/threeDayCatalog";
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

type ClubIdentity = { code: string; name: string };

const CLUBS: Array<[RegExp, ClubIdentity]> = [
  [/flemington/i, { code: "VRC", name: "Victoria Racing Club" }],
  [/randwick|rosehill/i, { code: "ATC", name: "Australian Turf Club" }],
  [/eagle farm|doomben/i, { code: "BRC", name: "Brisbane Racing Club" }],
  [/morphettville/i, { code: "SAJC", name: "South Australian Jockey Club" }],
  [/ascot|belmont/i, { code: "PR", name: "Perth Racing" }],
  [/caulfield|sandown/i, { code: "MRC", name: "Melbourne Racing Club" }],
  [/moonee valley/i, { code: "MVRC", name: "Moonee Valley Racing Club" }],
  [/sha tin|happy valley/i, { code: "HKJC", name: "Hong Kong Jockey Club" }],
];

function display(value: unknown, fallback = "-") {
  return cleanProductText(value, fallback);
}

function clubIdentity(meeting: unknown): ClubIdentity {
  const text = display(meeting, "Race Club");
  return CLUBS.find(([pattern]) => pattern.test(text))?.[1] ?? {
    code: text.split(/\s+/).map((part) => part[0]).join("").slice(0, 4).toUpperCase() || "RC",
    name: `${text} Racing Club`,
  };
}

function shortDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", month: "short", timeZone: "Australia/Melbourne" }).format(new Date(Date.UTC(year, month - 1, day)));
}

function tabTitle(index: number, date: string) {
  if (index === 0) return "Today";
  if (index === 1) return "Tomorrow";
  const [year, month, day] = date.split("-").map(Number);
  if (!year || !month || !day) return "Day 3";
  return new Intl.DateTimeFormat("en-AU", { weekday: "long", timeZone: "Australia/Melbourne" }).format(new Date(Date.UTC(year, month - 1, day)));
}

function weatherIcon(value: unknown) {
  const text = display(value, "").toLowerCase();
  if (/rain|shower|storm/.test(text)) return "☂";
  if (/cloud|overcast/.test(text)) return "☁";
  return "☀";
}

function weatherText(meeting: MeetingSummaryViewModel) {
  return canonicalWeatherDisplay(meeting.weather);
}

function temperatureText(meeting: MeetingSummaryViewModel) {
  const value = display(meeting.temp, "");
  return value && value.toLowerCase() !== "not supplied" ? value : "";
}

function meetingStatus(meeting: MeetingSummaryViewModel) {
  const text = display(meeting.status, "").toLowerCase();
  if (/abandon/.test(text)) return "ABANDONED";
  if (/postpon/.test(text)) return "POSTPONED";
  if (/result|complete/.test(text)) return "COMPLETE";
  return "LIVE";
}

function keyRaceRows(meetings: MeetingSummaryViewModel[]) {
  return meetings.flatMap((meeting) => meeting.raceSummaries.map((race) => ({ meeting, race })))
    .filter(({ race }) => /G1|G2|G3|LISTED|LR/i.test(`${race.raceClass} ${race.name}`))
    .slice(0, 5);
}

export function MeetingsWorkspace({
  selectedDayKey,
  selectedMeetingKey,
  onDayChange,
  onSelectMeeting,
  onOpenMeeting,
  onOpenRace,
}: MeetingsWorkspaceProps) {
  const [model, setModel] = useState<MeetingsWorkspaceViewModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("All");

  useEffect(() => {
    let active = true;
    loadMeetingsWorkspaceViewModel()
      .then((next) => { if (active) { setModel(next); setLoading(false); setLoadError(""); } })
      .catch((error) => { if (active) { setModel(null); setLoading(false); setLoadError(error instanceof Error ? error.message : "Meetings feed unavailable"); } });
    return () => { active = false; };
  }, []);

  const activeDay = model?.days.find((day) => day.key === selectedDayKey) ?? model?.days[0] ?? null;
  const states = useMemo(() => Array.from(new Set((activeDay?.meetings ?? []).map((meeting) => display(meeting.state, "")).filter(Boolean))).sort(), [activeDay]);
  const meetings = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (activeDay?.meetings ?? []).filter((meeting) => {
      const name = canonicalTrackDisplayName(meeting.meeting).toLowerCase();
      return (!q || name.includes(q)) && (stateFilter === "All" || display(meeting.state) === stateFilter);
    });
  }, [activeDay, search, stateFilter]);
  const selectedMeeting = meetings.find((meeting) => meeting.meetingKey === selectedMeetingKey) ?? meetings[0] ?? null;

  useEffect(() => {
    if (selectedMeeting && selectedMeeting.meetingKey !== selectedMeetingKey) onSelectMeeting(selectedMeeting.rawMeeting);
  }, [onSelectMeeting, selectedMeeting, selectedMeetingKey]);

  async function resolveFullMeeting(meeting: MeetingSummaryViewModel): Promise<ThreeDayMeeting> {
    setDetailLoading(true);
    setLoadError("");
    try {
      const catalog = await loadThreeDayCatalog();
      const fullMeeting = catalog.meetings.find((candidate) => candidate.meetingKey === meeting.meetingKey && candidate.date === meeting.rawMeeting.date)
        ?? catalog.meetings.find((candidate) => candidate.meetingKey === meeting.meetingKey);
      if (!fullMeeting) throw new Error(`Full meeting data unavailable for ${meeting.meeting}`);
      return fullMeeting;
    } finally {
      setDetailLoading(false);
    }
  }

  async function openMeeting(meeting: MeetingSummaryViewModel) {
    try {
      const fullMeeting = await resolveFullMeeting(meeting);
      onSelectMeeting(fullMeeting);
      onOpenMeeting(fullMeeting);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Meeting detail unavailable");
    }
  }

  async function openRace(meeting: MeetingSummaryViewModel, raceKey: string, index: number) {
    try {
      const fullMeeting = await resolveFullMeeting(meeting);
      const fullRace = fullMeeting.races.find((race) => race.raceKey === raceKey) ?? fullMeeting.races[index];
      if (!fullRace) throw new Error(`Full race data unavailable for ${meeting.meeting}`);
      onSelectMeeting(fullMeeting);
      onOpenRace(fullMeeting, fullRace, Math.max(0, fullMeeting.races.indexOf(fullRace)));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Race detail unavailable");
    }
  }

  const club = clubIdentity(selectedMeeting?.meeting);
  const keyRaces = keyRaceRows(meetings);
  const changes = meetings.flatMap((meeting) => meeting.scratchings > 0 ? [{ meeting, count: meeting.scratchings }] : []).slice(0, 5);

  if (loading) return <section className="eiq-meetings-locked"><div className="eiq-meetings-locked__empty">Loading meetings…</div></section>;

  return (
    <section className="eiq-meetings-locked" aria-label="Meetings" data-edgeiq-workspace-key="MEETINGS">
      <header className="eiq-meetings-locked__header">
        <div>
          <h1>Meetings</h1>
          <p>Select a meeting to view races, club details and key information.</p>
          {loadError ? <p role="alert">{loadError}</p> : null}
        </div>
        <button className="eiq-meetings-locked__refresh" type="button" onClick={() => window.location.reload()}>↻ Refresh Meetings</button>
      </header>

      <div className="eiq-meetings-locked__days" aria-label="Meeting days">
        {(model?.days ?? []).slice(0, 3).map((day, index) => (
          <button key={day.key} type="button" className={day.key === activeDay?.key ? "is-active" : ""} onClick={() => onDayChange(day.key)}>
            <strong>{tabTitle(index, day.date)}</strong><span>{shortDate(day.date)}</span>
          </button>
        ))}
      </div>

      <section className="eiq-meetings-locked__filters">
        <label>State<select value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}><option>All</option>{states.map((state) => <option key={state}>{state}</option>)}</select></label>
        <label>Country<select><option>All</option><option>Australia</option><option>Hong Kong</option></select></label>
        <label>Track Type<select><option>All</option><option>Turf</option></select></label>
        <label>Track<select><option>All</option></select></label>
        <label>Rail Position<select><option>All</option></select></label>
        <label>Weather<select><option>All</option></select></label>
        <label className="is-search">Search meetings<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search meetings…" /></label>
        <button type="button" onClick={() => { setSearch(""); setStateFilter("All"); }}>Clear Filters</button>
      </section>

      <div className="eiq-meetings-locked__main-grid">
        <section className="eiq-meetings-panel eiq-meetings-panel--list">
          <header><strong>{tabTitle(activeDay ? model?.days.findIndex((day) => day.key === activeDay.key) ?? 0 : 0, activeDay?.date ?? "")} Meetings ({meetings.length})</strong></header>
          <div className="eiq-meetings-locked__table-wrap">
            <table className="eiq-meetings-locked__table">
              <thead><tr><th>Meeting</th><th>State</th><th>Track</th><th>Rail</th><th>Weather</th><th>Races</th><th>First</th><th>Last</th><th>Status</th><th /></tr></thead>
              <tbody>
                {meetings.map((meeting) => {
                  const identity = clubIdentity(meeting.meeting);
                  const selected = meeting.meetingKey === selectedMeeting?.meetingKey;
                  return <tr key={meeting.meetingKey} className={selected ? "is-selected" : ""} onClick={() => onSelectMeeting(meeting.rawMeeting)}>
                    <td><span className="eiq-club-mark"><b>{identity.code}</b><small>{identity.name}</small></span><strong>{canonicalTrackDisplayName(meeting.meeting)}</strong></td>
                    <td>{display(meeting.state)}</td><td>{canonicalTrackRatingDisplay(meeting.track)}</td><td>{canonicalRailDisplay(meeting.rail)}</td>
                    <td><span className="eiq-weather-cell">{weatherIcon(meeting.weather)} {weatherText(meeting)}</span></td>
                    <td>{meeting.races}</td><td>{display(meeting.first)}</td><td>{display(meeting.last)}</td><td><span className="eiq-meeting-status">{meetingStatus(meeting)}</span></td>
                    <td><button type="button" disabled={detailLoading} onClick={(event) => { event.stopPropagation(); void openMeeting(meeting); }}>{detailLoading ? "…" : "›"}</button></td>
                  </tr>;
                })}
                {!meetings.length ? <tr><td colSpan={10} className="eiq-meetings-locked__empty">No meetings published for this date.</td></tr> : null}
              </tbody>
            </table>
          </div>
        </section>

        <div className="eiq-meetings-locked__side-stack">
          <section className="eiq-meetings-panel eiq-meetings-panel--overview">
            <header><strong>Meeting Overview</strong>{selectedMeeting ? <button type="button" disabled={detailLoading} onClick={() => void openMeeting(selectedMeeting)}>View Meeting</button> : null}</header>
            {selectedMeeting ? <>
              <div className="eiq-meeting-overview__hero">
                <div className="eiq-club-logo-large"><b>{club.code}</b><span>{club.name}</span></div>
                <div><h2>{canonicalTrackDisplayName(selectedMeeting.meeting)}</h2><p>{display(selectedMeeting.state)} &nbsp; | &nbsp; {canonicalTrackRatingDisplay(selectedMeeting.track)} &nbsp; | &nbsp; {canonicalRailDisplay(selectedMeeting.rail)}</p></div>
              </div>
              <div className="eiq-meeting-overview__weather"><span>{weatherIcon(selectedMeeting.weather)}</span><strong>{weatherText(selectedMeeting)}</strong><small>{temperatureText(selectedMeeting) ? `Temperature ${temperatureText(selectedMeeting)}` : "Forecast — Racing Australia"}</small><b>Wind</b><em>{display(selectedMeeting.wind)}</em></div>
              <dl><div><dt>Races</dt><dd>{selectedMeeting.races}</dd></div><div><dt>First Race</dt><dd>{display(selectedMeeting.first)}</dd></div><div><dt>Last Race</dt><dd>{display(selectedMeeting.last)}</dd></div></dl>
            </> : <div className="eiq-meetings-locked__empty">Select a meeting.</div>}
          </section>

          <section className="eiq-meetings-panel eiq-meetings-panel--times">
            <header><strong>Race Times{selectedMeeting ? ` — ${canonicalTrackDisplayName(selectedMeeting.meeting)}` : ""}</strong></header>
            <div>{selectedMeeting?.raceSummaries.map((race, index) => <button key={race.raceKey} type="button" disabled={detailLoading} onClick={() => void openRace(selectedMeeting, race.raceKey, index)}><b>R{race.raceNumber}</b><span>{display(race.time)}</span></button>)}</div>
          </section>
        </div>
      </div>

      <div className="eiq-meetings-locked__bottom-grid">
        <section className="eiq-meetings-panel"><header><strong>Scratchings & Changes</strong></header><div className="eiq-meetings-list">{changes.length ? changes.map(({ meeting, count }) => <div key={meeting.meetingKey}><i className="is-red" /><span>{canonicalTrackDisplayName(meeting.meeting)}</span><b>{count} scratching{count === 1 ? "" : "s"}</b></div>) : <p>No reported scratchings in this window.</p>}</div></section>
        <section className="eiq-meetings-panel"><header><strong>Key Races</strong></header><div className="eiq-meetings-list">{keyRaces.length ? keyRaces.map(({ meeting, race }) => <button key={race.raceKey} type="button" disabled={detailLoading} onClick={() => void openRace(meeting, race.raceKey, Math.max(0, race.raceNumber - 1))}><span>{display(race.time)}</span><strong>{canonicalTrackDisplayName(meeting.meeting)} R{race.raceNumber}</strong><b>{display(race.name, race.raceClass)}</b></button>) : <p>No black-type races identified in this window.</p>}</div></section>
        <section className="eiq-meetings-panel"><header><strong>Quick Actions</strong></header><div className="eiq-meetings-actions"><button type="button" onClick={() => model?.days[1] && onDayChange(model.days[1].key)}>View Tomorrow's Meetings</button><button type="button">Today's Races (All)</button><button type="button">Market Movers</button><button type="button">Scratchings (All)</button><button type="button">Weather</button><button type="button">Track Information</button></div></section>
      </div>
    </section>
  );
}
