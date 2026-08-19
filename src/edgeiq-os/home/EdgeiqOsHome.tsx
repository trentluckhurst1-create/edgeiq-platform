import { useEffect, useMemo, useState } from "react";

import { buildMissionControlModel } from "../services/mission-control";
import { loadEdgeiqDailyPipelineStatus, type EdgeiqDailyPipelineStatus } from "../services/daily-pipeline/DailyPipelineStatusService";
import { loadMeetingsWorkspaceViewModel, type MeetingSummaryViewModel, type MeetingsWorkspaceViewModel } from "../race/services/meetingsFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../design-system/presentation";

type HomeWorkspaceSection = "meetings" | "race" | "field" | "formGuide" | "performance" | "epi" | "map" | "market" | "overview" | "insights" | "results" | "lab" | "compare" | "review" | "settings";

type EdgeiqOsHomeProps = {
  onOpenMeetings?: () => void;
  onOpenWorkspace?: (section: HomeWorkspaceSection) => void;
};

const WORKSPACE_STATE_STORAGE_KEY = "edgeiq-os-racefile-v3-state";
const mission = buildMissionControlModel();

const valuePanels = [
  {
    icon: "EF",
    heading: "Evidence First",
    description: "Governed race, runner and market context in one operating view.",
  },
  {
    icon: "PR",
    heading: "Built For Professionals",
    description: "Fast navigation for analysts working through live race days.",
  },
  {
    icon: "CI",
    heading: "Complete Intelligence",
    description: "Race shape, performance, form, map, market and review workspaces.",
  },
];

const workspaceRows: Array<{ icon: string; title: string; description: string; section: HomeWorkspaceSection }> = [
  { icon: "RI", title: "Race Intelligence", description: "Race overview, field context and operating read.", section: "race" },
  { icon: "PF", title: "Performance", description: "EPI, ERI, historical ratings and benchmark comparison.", section: "performance" },
  { icon: "MK", title: "Market", description: "Market, fair price, edge and movement status.", section: "market" },
  { icon: "TB", title: "Track Bias", description: "Track, weather, map and conditions intelligence.", section: "insights" },
  { icon: "CP", title: "Compare", description: "Runner and race comparison workspace.", section: "compare" },
  { icon: "LB", title: "Lab", description: "Governed research and diagnostics workspace.", section: "lab" },
  { icon: "RV", title: "Review", description: "Post-race review and audit workflow.", section: "review" },
  { icon: "ST", title: "Settings", description: "Product controls and operating configuration.", section: "settings" },
];

function clean(value: unknown): string {
  return cleanProductText(value, "");
}

function display(value: unknown, fallback = "-"): string {
  return cleanProductText(value, fallback);
}

function currentDisplayDate(model: MeetingsWorkspaceViewModel | null) {
  return model?.days.find((day) => day.key === "TODAY")?.displayDate ?? model?.days[0]?.displayDate ?? "Current racing window";
}

function trackRatingOnly(meeting: MeetingSummaryViewModel): string {
  const candidates = [meeting.track, meeting.rawMeeting?.trackCondition, meeting.rawMeeting?.races?.[0]?.trackCondition, meeting.rawMeeting?.races?.[0]?.source?.track_rating];
  for (const candidate of candidates) {
    const text = clean(candidate);
    const match = text.match(/\b(Firm|Good|Soft|Heavy)\s*([0-9]{1,2})?\b/i);
    if (match) return `${match[1][0].toUpperCase()}${match[1].slice(1).toLowerCase()}${match[2] ? ` ${match[2]}` : ""}`;
  }
  return "Awaiting Track Feed";
}

function weatherSummary(value: unknown): string {
  const text = clean(value);
  if (!text) return "Awaiting Weather Feed";
  if (/sun|fine|clear/i.test(text)) return "Sunny";
  if (/cloud|overcast/i.test(text)) return "Cloudy";
  if (/rain|shower|storm|wet/i.test(text)) return "Rain";
  if (/wind/i.test(text)) return "Wind";
  return text.length > 18 ? "Awaiting Weather Feed" : text;
}

function pipelineDisplay(status: EdgeiqDailyPipelineStatus | null, loadError: string | null): { label: string; tone: "ready" | "awaiting" | "failed" } {
  if (loadError) return { label: "Failed", tone: "failed" };
  if (status?.status === "READY") return { label: "Ready", tone: "ready" };
  if (status?.status === "WARN") return { label: "Awaiting", tone: "awaiting" };
  if (status?.status === "FAIL") return { label: "Failed", tone: "failed" };
  return { label: "Awaiting", tone: "awaiting" };
}

function formatBuildTime(value: unknown): string {
  const text = clean(value);
  if (!text) return "Awaiting Build";
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;
  return new Intl.DateTimeFormat("en-AU", {
    day: "2-digit",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Melbourne",
  }).format(parsed);
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
          meeting: canonicalTrackDisplayName(meeting.meeting),
          race: race?.label ?? "Race",
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
  const [pipelineStatus, setPipelineStatus] = useState<EdgeiqDailyPipelineStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([loadMeetingsWorkspaceViewModel(), loadEdgeiqDailyPipelineStatus()])
      .then(([loaded, status]) => {
        if (!cancelled) {
          setModel(loaded);
          setPipelineStatus(status);
          setLoadError(null);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn("EDGEiQ home governed feed awaiting", error);
          setModel(null);
          setPipelineStatus(null);
          setLoadError("Awaiting Meeting Feed");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const today = model?.days.find((day) => day.key === "TODAY") ?? model?.days[0] ?? null;
  const meetings = useMemo(() => (today?.meetings ?? []).slice(0, 6), [today]);
  const activityRows = useMemo(() => {
    const rows: Array<{ meeting: string; race: string; title: string; timestamp: string; status: string }> = [];
    for (const meeting of today?.meetings ?? []) {
      for (const race of meeting.raceSummaries) {
        rows.push({
          meeting: canonicalTrackDisplayName(meeting.meeting),
          race: race.label,
          title: [race.distance, race.raceClass].map(clean).filter(Boolean).join(" ") || display(race.name),
          timestamp: display(race.time, formatBuildTime(model?.generatedAt)),
          status: display(race.status, "Ready"),
        });
        if (rows.length >= 10) return rows;
      }
    }
    return rows;
  }, [model?.generatedAt, today?.meetings]);
  const persisted = useMemo(() => readPersistedContext(model), [model]);
  const pipeline = pipelineDisplay(pipelineStatus, loadError);
  const totalMeetings = today?.totals.meetings ?? model?.days.reduce((sum, day) => sum + day.totals.meetings, 0) ?? 0;
  const totalRaces = today?.totals.races ?? mission.raceCount;
  const totalDeclared = today?.totals.declared ?? mission.runnerCount;
  const totalScratchings = today?.totals.scratchings ?? 0;
  const lastBuild = formatBuildTime(pipelineStatus?.generated_at ?? model?.generatedAt);

  return (
    <section className="eiq-home-v1" aria-label="EDGEiQ home" data-edgeiq-workspace-key="HOME" data-edgeiq-mounted-component="EdgeiqOsHome">
      <div className="eiq-home-v1__inner">
        <section className="eiq-home-v1__top-row" aria-label="Current operational status">
          <div className="eiq-home-v1__welcome">
            <h1>Welcome to EDGEIQ</h1>
            <p>
              Professional racing intelligence for daily operators. Governed meetings, race shape, performance,
              market context and review tools in one operating system.
            </p>
          </div>
          <section className="eiq-home-v1__quality eiq-home-v1-card" aria-label="Data Quality">
            <header><strong>Data Quality</strong></header>
            <dl>
              <div><dt>Pipeline</dt><dd className={`is-${pipeline.tone}`}>{pipeline.label}</dd></div>
              <div><dt>Status</dt><dd className={`is-${pipeline.tone}`}>{pipeline.label}</dd></div>
              <div><dt>Window</dt><dd>{display(pipelineStatus?.melbourne_date, currentDisplayDate(model))}</dd></div>
              <div><dt>Meetings</dt><dd>{totalMeetings}</dd></div>
              <div><dt>Races</dt><dd>{totalRaces}</dd></div>
              <div><dt>Declared</dt><dd>{totalDeclared}</dd></div>
              <div><dt>Scratchings</dt><dd>{totalScratchings}</dd></div>
              <div><dt>Last Build</dt><dd>{lastBuild}</dd></div>
            </dl>
          </section>
        </section>

        <section className="eiq-home-v1__value-panels" aria-label="EDGEiQ value proposition">
          {valuePanels.map((panel) => (
            <article className="eiq-home-v1-card eiq-home-v1-value" key={panel.heading}>
              <span aria-hidden="true">{panel.icon}</span>
              <div>
                <strong>{panel.heading}</strong>
                <p>{panel.description}</p>
              </div>
            </article>
          ))}
        </section>

        <section className="eiq-home-v1-card eiq-home-v1__meetings" aria-label="Today's Meetings">
          <header>
            <div>
              <strong>Today's Meetings</strong>
              <span>{currentDisplayDate(model)}</span>
            </div>
            <button className="eiq-home-v1-button eiq-home-v1-button--primary" type="button" onClick={onOpenMeetings}>View Meetings</button>
          </header>
          <div className="eiq-home-v1-table-wrap">
            <table className="eiq-home-v1-table">
              <thead>
                <tr>
                  <th>Meeting</th>
                  <th>State</th>
                  <th>Rail</th>
                  <th>Track</th>
                  <th>Weather</th>
                  <th>Races</th>
                  <th>Declared</th>
                  <th>Scratchings</th>
                </tr>
              </thead>
              <tbody>
                {meetings.map((meeting) => (
                  <tr key={meeting.meetingKey}>
                    <td className="is-left">
                      <button className="eiq-home-v1-link" type="button" onClick={onOpenMeetings}>
                        {display(canonicalTrackDisplayName(meeting.meeting))}
                      </button>
                    </td>
                    <td>{display(meeting.state)}</td>
                    <td>{display(meeting.rail)}</td>
                    <td>{trackRatingOnly(meeting)}</td>
                    <td>{weatherSummary(meeting.weather)}</td>
                    <td>{meeting.races}</td>
                    <td>{meeting.declared}</td>
                    <td>{meeting.scratchings}</td>
                  </tr>
                ))}
                {!meetings.length ? <tr><td colSpan={8}>Awaiting Meetings Feed</td></tr> : null}
              </tbody>
            </table>
          </div>
        </section>

        <section className="eiq-home-v1__lower-grid" aria-label="Home operating modules">
          <section className="eiq-home-v1-card eiq-home-v1__activity" aria-label="Recent Analysis">
            <header><strong>Recent Analysis</strong></header>
            <div>
              {activityRows.map((row) => (
                <article key={`${row.meeting}-${row.race}-${row.title}`}>
                  <span className="eiq-home-v1-status-dot" aria-hidden="true" />
                  <div>
                    <strong>{row.meeting} {row.race}</strong>
                    <p>{row.title}</p>
                  </div>
                  <time>{row.timestamp}</time>
                </article>
              ))}
              {!activityRows.length ? <p className="eiq-home-v1-empty">Awaiting Analysis Feed</p> : null}
            </div>
          </section>

          <section className="eiq-home-v1-card eiq-home-v1__launcher" aria-label="Workspaces">
            <header><strong>Workspaces</strong></header>
            <div>
              {workspaceRows.map((item) => (
                <button key={item.title} type="button" onClick={() => onOpenWorkspace?.(item.section)}>
                  <span aria-hidden="true">{item.icon}</span>
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </button>
              ))}
            </div>
          </section>
        </section>
      </div>

      <aside className="eiq-home-v1__floating-status" aria-label="Floating data status">
        <strong>Data Status</strong>
        <span className={`is-${pipeline.tone}`}>{pipeline.label}</span>
        <small>{totalRaces} races | {totalDeclared} declared | {totalScratchings} scratchings</small>
        {persisted ? <small>Continue: {persisted.meeting} {persisted.race}</small> : null}
      </aside>
    </section>
  );
}
