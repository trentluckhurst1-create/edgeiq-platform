import { useEffect, useMemo, useState } from "react";
import { loadMeetingsWorkspaceViewModel, type MeetingsWorkspaceViewModel } from "../race/services/meetingsFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../design-system/presentation";

type HomeWorkspaceSection = "meetings" | "race" | "field" | "formGuide" | "performance" | "epi" | "map" | "market" | "overview" | "insights" | "results" | "lab" | "compare" | "review" | "settings";
type EdgeiqOsHomeProps = { onOpenMeetings?: () => void; onOpenWorkspace?: (section: HomeWorkspaceSection) => void };

const clean = (value: unknown) => cleanProductText(value, "");
const display = (value: unknown, fallback = "-") => cleanProductText(value, fallback);

function trackRating(meeting: any): string {
  const candidates = [meeting.track, meeting.rawMeeting?.trackCondition, meeting.rawMeeting?.races?.[0]?.trackCondition, meeting.rawMeeting?.races?.[0]?.source?.track_rating];
  for (const candidate of candidates) {
    const text = clean(candidate);
    const match = text.match(/\b(Firm|Good|Soft|Heavy)\s*([0-9]{1,2})?\b/i);
    if (match) return `${match[1][0].toUpperCase()}${match[1].slice(1).toLowerCase()}${match[2] ? ` ${match[2]}` : ""}`;
  }
  return "Awaiting";
}

function weatherSummary(value: unknown): string {
  const text = clean(value);
  if (!text) return "Awaiting";
  if (/sun|fine|clear/i.test(text)) return "Fine";
  if (/cloud|overcast/i.test(text)) return "Cloudy";
  if (/rain|shower|storm|wet/i.test(text)) return "Shower";
  if (/wind/i.test(text)) return "Wind";
  return text.length > 18 ? "Awaiting" : text;
}

function parseDisplayDate(value: string): Date | null {
  const text = clean(value);
  if (!text) return null;
  const parsed = new Date(text);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function dayTabLabel(index: number, value: string | Date): { title: string; date: string } {
  const parsed = value instanceof Date ? value : parseDisplayDate(value);
  if (!parsed) return { title: index === 0 ? "Today" : index === 1 ? "Tomorrow" : "Day", date: String(value) };
  const weekday = new Intl.DateTimeFormat("en-AU", { weekday: "long", timeZone: "Australia/Melbourne" }).format(parsed);
  const date = new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", month: "short", timeZone: "Australia/Melbourne" }).format(parsed);
  return { title: index === 0 ? "Today" : index === 1 ? "Tomorrow" : weekday, date };
}

function fallbackDays() {
  const now = new Date();
  return [0, 1, 2].map((offset) => {
    const date = new Date(now);
    date.setDate(now.getDate() + offset);
    return { key: `FALLBACK_${offset}`, displayDate: date };
  });
}

export function EdgeiqOsHome({ onOpenMeetings, onOpenWorkspace }: EdgeiqOsHomeProps) {
  const [model, setModel] = useState<MeetingsWorkspaceViewModel | null>(null);
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    loadMeetingsWorkspaceViewModel().then((loaded) => { if (!cancelled) setModel(loaded); }).catch((error) => {
      console.warn("EDGEiQ dashboard feed awaiting", error);
      if (!cancelled) setModel(null);
    });
    return () => { cancelled = true; };
  }, []);

  const days = model?.days.slice(0, 3) ?? [];
  const visibleDays = days.length ? days.map((day) => ({ key: day.key, displayDate: day.displayDate })) : fallbackDays();
  const selectedDay = days[selectedDayIndex] ?? days[0] ?? null;
  const meetings = useMemo(() => (selectedDay?.meetings ?? []).slice(0, 8), [selectedDay]);
  const featuredMeeting = meetings[0] ?? null;
  const featuredRace = featuredMeeting?.raceSummaries?.[0] ?? null;
  const activityRows = useMemo(() => {
    const rows: Array<{ meeting: string; race: string; time: string; status: string }> = [];
    for (const meeting of selectedDay?.meetings ?? []) {
      for (const race of meeting.raceSummaries) {
        rows.push({ meeting: canonicalTrackDisplayName(meeting.meeting), race: race.label, time: display(race.time), status: display(race.status, "Scheduled") });
        if (rows.length >= 8) return rows;
      }
    }
    return rows;
  }, [selectedDay]);
  const activeLabel = dayTabLabel(selectedDayIndex, visibleDays[selectedDayIndex]?.displayDate ?? new Date());

  return (
    <section className="eiq-dashboard-locked" aria-label="EDGEiQ Dashboard" data-edgeiq-workspace-key="HOME">
      <header className="eiq-dashboard-locked__header">
        <div><h1>Dashboard</h1><p>Race day command centre. Live meetings, key races, market context and alerts.</p></div>
        <div className="eiq-dashboard-locked__days" aria-label="Racing days">
          {visibleDays.map((day, index) => {
            const label = dayTabLabel(index, day.displayDate);
            return <button key={day.key} type="button" className={selectedDayIndex === index ? "is-active" : ""} onClick={() => setSelectedDayIndex(index)}><strong>{label.title}</strong><span>{label.date}</span></button>;
          })}
        </div>
      </header>

      <div className="eiq-dashboard-locked__grid eiq-dashboard-locked__grid--top">
        <section className="eiq-dashboard-panel eiq-dashboard-panel--meetings">
          <header><strong>{selectedDayIndex === 0 ? "Today's" : activeLabel.title} Meetings</strong><button type="button" onClick={onOpenMeetings}>View All</button></header>
          <div className="eiq-dashboard-table-wrap"><table className="eiq-dashboard-table"><thead><tr><th>Meeting</th><th>State</th><th>Rail</th><th>Track</th><th>Weather</th><th>Races</th><th>First</th><th>Status</th></tr></thead><tbody>
            {meetings.map((meeting) => <tr key={meeting.meetingKey}><td><button className="eiq-dashboard-link" type="button" onClick={onOpenMeetings}>{display(canonicalTrackDisplayName(meeting.meeting))}</button></td><td>{display(meeting.state)}</td><td>{display(meeting.rail)}</td><td>{trackRating(meeting)}</td><td>{weatherSummary(meeting.weather)}</td><td>{meeting.races}</td><td>{display(meeting.raceSummaries?.[0]?.time)}</td><td><span className="eiq-dashboard-status">{meeting.races ? "READY" : "AWAITING"}</span></td></tr>)}
            {!meetings.length ? <tr><td colSpan={8} className="eiq-dashboard-empty">Awaiting Meetings Feed</td></tr> : null}
          </tbody></table></div>
        </section>

        <section className="eiq-dashboard-panel"><header><strong>Race Activity</strong><span>Current programme</span></header><div className="eiq-dashboard-activity">{activityRows.slice(0, 5).map((row, index) => <div key={`${row.meeting}-${row.race}-${index}`}><b>{row.race}</b><span>{row.meeting}</span><strong>{row.time}</strong></div>)}{!activityRows.length ? <p className="eiq-dashboard-empty">Awaiting race activity</p> : null}</div></section>

        <section className="eiq-dashboard-panel"><header><strong>Alerts</strong><span>Governed feed</span></header><div className="eiq-dashboard-alerts">{(selectedDay?.totals.scratchings ?? 0) > 0 ? <div className="is-alert"><i /><span>{selectedDay?.totals.scratchings} scratchings in selected window</span></div> : <div><i /><span>No scratching alerts in selected window</span></div>}<div><i /><span>Track and weather status monitored</span></div><div><i /><span>Meeting feed {meetings.length ? "available" : "awaiting"}</span></div></div></section>
      </div>

      <div className="eiq-dashboard-locked__grid eiq-dashboard-locked__grid--middle">
        <section className="eiq-dashboard-panel eiq-dashboard-panel--featured"><header><strong>Featured Race</strong><span>{featuredMeeting ? canonicalTrackDisplayName(featuredMeeting.meeting) : "Awaiting race"}</span></header>{featuredMeeting && featuredRace ? <><div className="eiq-dashboard-featured-head"><div><h2>{canonicalTrackDisplayName(featuredMeeting.meeting)} {featuredRace.label}</h2><p>{[featuredRace.raceClass, featuredRace.distance, trackRating(featuredMeeting), display(featuredMeeting.rail)].filter(Boolean).join("  ·  ")}</p></div><button type="button" onClick={() => onOpenWorkspace?.("race")}>Open Race Analysis →</button></div><div className="eiq-dashboard-featured-tabs"><span className="is-active">Top Contenders</span><span>Market</span><span>Speed Map</span><span>Key Factors</span></div><div className="eiq-dashboard-featured-empty">Open Race Analysis for governed runner ratings, prices and tactical intelligence.</div></> : <div className="eiq-dashboard-empty">Awaiting featured race</div>}</section>
        <section className="eiq-dashboard-panel"><header><strong>Track & Weather</strong><span>Selected day</span></header><div className="eiq-dashboard-mini-table">{meetings.slice(0, 5).map((meeting) => <div key={meeting.meetingKey}><strong>{canonicalTrackDisplayName(meeting.meeting)}</strong><span>{display(meeting.rail)}</span><span>{trackRating(meeting)}</span><span>{weatherSummary(meeting.weather)}</span></div>)}</div></section>
      </div>

      <div className="eiq-dashboard-locked__grid eiq-dashboard-locked__grid--bottom">
        <section className="eiq-dashboard-panel"><header><strong>Market Summary</strong><span>Race-day pricing</span></header><button className="eiq-dashboard-action" type="button" onClick={() => onOpenWorkspace?.("market")}>Open Market Workspace</button><p className="eiq-dashboard-note">Fair price, market price, edge and movement remain governed inside the Market workspace.</p></section>
        <section className="eiq-dashboard-panel"><header><strong>Intelligence</strong><span>Analysis tools</span></header><div className="eiq-dashboard-actions"><button type="button" onClick={() => onOpenWorkspace?.("performance")}>Performance</button><button type="button" onClick={() => onOpenWorkspace?.("epi")}>EPI Ratings</button><button type="button" onClick={() => onOpenWorkspace?.("map")}>Speed Map</button></div></section>
        <section className="eiq-dashboard-panel"><header><strong>{selectedDayIndex === 0 ? "Today's" : activeLabel.title} Timeline</strong><span>{activeLabel.date}</span></header><div className="eiq-dashboard-timeline">{activityRows.slice(0, 6).map((row, index) => <div key={`${row.meeting}-${row.race}-timeline-${index}`}><i /><time>{row.time}</time><span>{row.meeting} {row.race}</span><em>{row.status}</em></div>)}</div></section>
      </div>
    </section>
  );
}
