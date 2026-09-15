import { useEffect, useMemo, useState } from "react";
import { loadMeetingsWorkspaceViewModel, type MeetingsWorkspaceViewModel } from "../race/services/meetingsFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../design-system/presentation";

type EdgeiqOsHomeProps = { onOpenMeetings?: () => void };
const display = (value: unknown, fallback = "—") => cleanProductText(value, fallback);

function dayLabel(index: number, value: string | Date) {
  const parsed = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(parsed.getTime())) return { title: index === 0 ? "Today" : index === 1 ? "Tomorrow" : "Day +2", date: String(value) };
  const date = new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", month: "short", timeZone: "Australia/Melbourne" }).format(parsed);
  return { title: index === 0 ? "Today" : index === 1 ? "Tomorrow" : "Day +2", date };
}

function fallbackDays() {
  const now = new Date();
  return [0, 1, 2].map((offset) => { const date = new Date(now); date.setDate(now.getDate() + offset); return { key: `FALLBACK_${offset}`, displayDate: date }; });
}

export function EdgeiqOsHome({ onOpenMeetings }: EdgeiqOsHomeProps) {
  const [model, setModel] = useState<MeetingsWorkspaceViewModel | null>(null);
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    loadMeetingsWorkspaceViewModel().then((loaded) => { if (!cancelled) setModel(loaded); }).catch(() => { if (!cancelled) setModel(null); });
    return () => { cancelled = true; };
  }, []);

  const days = model?.days.slice(0, 3) ?? [];
  const visibleDays = days.length ? days.map((day) => ({ key: day.key, displayDate: day.displayDate })) : fallbackDays();
  const selectedDay = days[selectedDayIndex] ?? days[0] ?? null;
  const meetings = useMemo(() => (selectedDay?.meetings ?? []).slice(0, 8), [selectedDay]);
  const activityRows = useMemo(() => {
    const rows: Array<{ meeting: string; race: string; time: string; status: string }> = [];
    for (const meeting of selectedDay?.meetings ?? []) for (const race of meeting.raceSummaries) {
      rows.push({ meeting: canonicalTrackDisplayName(meeting.meeting), race: race.label, time: display(race.time), status: display(race.status, "Scheduled") });
      if (rows.length >= 8) return rows;
    }
    return rows;
  }, [selectedDay]);

  return (
    <section className="eiq-dashboard-locked" aria-label="EDGEiQ Home" data-edgeiq-workspace-key="HOME">
      <header className="eiq-dashboard-locked__header">
        <div><h1>Home</h1><p>Race-day intelligence overview.</p></div>
        <div className="eiq-dashboard-locked__days" aria-label="Racing days">
          {visibleDays.map((day, index) => { const label = dayLabel(index, day.displayDate); return <button key={day.key} type="button" className={selectedDayIndex === index ? "is-active" : ""} onClick={() => setSelectedDayIndex(index)}><strong>{label.title}</strong><span>{label.date}</span></button>; })}
        </div>
      </header>

      <div className="eiq-dashboard-locked__grid eiq-dashboard-locked__grid--top">
        <section className="eiq-dashboard-panel eiq-dashboard-panel--meetings">
          <header><strong>Meetings</strong><button type="button" onClick={onOpenMeetings}>View All</button></header>
          <div className="eiq-dashboard-table-wrap"><table className="eiq-dashboard-table"><thead><tr><th>Meeting</th><th>State</th><th>Rail</th><th>Races</th><th>First</th><th>Scratchings</th></tr></thead><tbody>
            {meetings.map((meeting) => <tr key={meeting.meetingKey}><td><button className="eiq-dashboard-link" type="button" onClick={onOpenMeetings}>{display(canonicalTrackDisplayName(meeting.meeting))}</button></td><td>{display(meeting.state)}</td><td>{display(meeting.rail)}</td><td>{meeting.races}</td><td>{display(meeting.raceSummaries?.[0]?.time)}</td><td>{meeting.scratchings ?? 0}</td></tr>)}
            {!meetings.length ? <tr><td colSpan={6} className="eiq-dashboard-empty">Meetings feed unavailable</td></tr> : null}
          </tbody></table></div>
        </section>

        <section className="eiq-dashboard-panel"><header><strong>Race Activity</strong><span>Current programme</span></header><div className="eiq-dashboard-activity">{activityRows.slice(0, 5).map((row, index) => <div key={`${row.meeting}-${row.race}-${index}`}><b>{row.race}</b><span>{row.meeting}</span><strong>{row.time}</strong></div>)}{!activityRows.length ? <p className="eiq-dashboard-empty">No current race activity</p> : null}</div></section>

        <section className="eiq-dashboard-panel"><header><strong>Race-Day Alerts</strong><span>Governed data only</span></header><div className="eiq-dashboard-alerts">{(selectedDay?.totals.scratchings ?? 0) > 0 ? <div className="is-alert"><i /><span>{selectedDay?.totals.scratchings} scratchings in selected window</span></div> : <div><i /><span>No reported scratchings in selected window</span></div>}<div><i /><span>{meetings.length ? `${meetings.length} meetings available` : "Meetings feed unavailable"}</span></div></div></section>
      </div>

      <div className="eiq-dashboard-locked__grid eiq-dashboard-locked__grid--bottom">
        <section className="eiq-dashboard-panel"><header><strong>Programme Summary</strong><span>Selected day</span></header><div className="eiq-dashboard-mini-table">{meetings.slice(0, 5).map((meeting) => <div key={meeting.meetingKey}><strong>{canonicalTrackDisplayName(meeting.meeting)}</strong><span>{display(meeting.state)}</span><span>{meeting.races} races</span><span>{meeting.scratchings ?? 0} scratchings</span></div>)}</div></section>
        <section className="eiq-dashboard-panel"><header><strong>Timeline</strong><span>Selected day</span></header><div className="eiq-dashboard-timeline">{activityRows.slice(0, 6).map((row, index) => <div key={`${row.meeting}-${row.race}-timeline-${index}`}><i /><time>{row.time}</time><span>{row.meeting} {row.race}</span><em>{row.status}</em></div>)}</div></section>
        <section className="eiq-dashboard-panel"><header><strong>EDGEiQ</strong><span>Racing Intelligence</span></header><p className="eiq-dashboard-note">Open Meetings to select a meeting and move into Race, Form, Performance, EPI Ratings, Speed Map, Market and the specialist workspaces.</p></section>
      </div>
    </section>
  );
}
