from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
HOME = ROOT / "src/edgeiq-os/home/EdgeiqOsHome.tsx"
CSS = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"

home_source = r'''import { useEffect, useMemo, useState } from "react";

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
          console.warn("EDGEiQ home governed feed unavailable", error);
          setModel(null);
          setPipelineStatus(null);
          setLoadError("Meeting feed unavailable");
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
'''

HOME.write_text(home_source, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
home_css = r'''

/* EDGEIQ HOME WORKSPACE V1 LOCKED SPECIFICATION */
.eiq-home-v1 {
  width: 100%;
  min-height: 100%;
  background: var(--eiq-product-bg, #ffffff) !important;
  color: var(--eiq-product-text, #172033) !important;
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  line-height: 22px !important;
  padding: 24px !important;
  position: relative;
}

.eiq-home-v1__inner {
  width: min(100%, 1600px);
  margin: 0 auto;
  display: grid;
  gap: 20px;
}

.eiq-home-v1-card {
  background: var(--eiq-product-panel, #ffffff) !important;
  border: 1px solid var(--eiq-product-border, #dfe5ee) !important;
  border-radius: 8px !important;
  padding: 20px !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
}

.eiq-home-v1__top-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 16px;
  align-items: stretch;
}

.eiq-home-v1__welcome {
  min-height: 164px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: #ffffff !important;
  border: 1px solid var(--eiq-product-border, #dfe5ee) !important;
  border-radius: 8px !important;
  padding: 20px !important;
}

.eiq-home-v1__welcome h1 {
  margin: 0 0 10px !important;
  font-size: 18px !important;
  line-height: 24px !important;
  font-weight: 700 !important;
  color: var(--eiq-product-text, #172033) !important;
}

.eiq-home-v1__welcome p {
  max-width: 520px;
  margin: 0 !important;
  font-size: 14px !important;
  line-height: 22px !important;
  font-weight: 500 !important;
  color: var(--eiq-product-muted, #5f6b7a) !important;
}

.eiq-home-v1__value-panels {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.eiq-home-v1-value {
  height: 120px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.eiq-home-v1-value > span,
.eiq-home-v1__launcher button > span,
.eiq-home-v1-status-dot {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  display: inline-grid;
  place-items: center;
  border: 1px solid var(--eiq-product-border, #dfe5ee);
  border-radius: 6px;
  color: var(--eiq-product-blue, #2456b8);
  background: #ffffff;
  font-size: 12px !important;
  font-weight: 700 !important;
}

.eiq-home-v1-value strong,
.eiq-home-v1-card > header strong {
  display: block;
  font-size: 16px !important;
  line-height: 22px !important;
  font-weight: 700 !important;
  color: var(--eiq-product-text, #172033) !important;
}

.eiq-home-v1-value p,
.eiq-home-v1-card > header span,
.eiq-home-v1__activity p,
.eiq-home-v1__launcher small {
  margin: 2px 0 0 !important;
  font-size: 13px !important;
  line-height: 18px !important;
  font-weight: 500 !important;
  color: var(--eiq-product-muted, #5f6b7a) !important;
}

.eiq-home-v1-card > header,
.eiq-home-v1__meetings > header {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 16px;
}

.eiq-home-v1-table-wrap {
  width: 100%;
  overflow: hidden;
}

.eiq-home-v1-table {
  width: 100%;
  border-collapse: collapse !important;
  table-layout: fixed;
  border: 1px solid var(--eiq-product-border, #dfe5ee) !important;
  border-radius: 8px !important;
  overflow: hidden;
}

.eiq-home-v1-table th,
.eiq-home-v1-table td {
  border-bottom: 1px solid var(--eiq-product-border-soft, #edf1f6) !important;
  vertical-align: middle !important;
  padding: 0 10px !important;
  letter-spacing: 0 !important;
}

.eiq-home-v1-table th {
  height: 40px !important;
  text-align: center !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  text-transform: none !important;
  color: var(--eiq-product-text, #172033) !important;
  background: var(--eiq-product-panel-soft, #f8fafc) !important;
}

.eiq-home-v1-table td {
  height: 40px !important;
  text-align: center !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  color: var(--eiq-product-text, #172033) !important;
}

.eiq-home-v1-table td.is-left,
.eiq-home-v1-table td:first-child {
  text-align: left !important;
}

.eiq-home-v1-table tbody tr:hover td {
  background: rgba(36, 86, 184, 0.035) !important;
}

.eiq-home-v1-link,
.eiq-home-v1-button,
.eiq-home-v1__launcher button {
  font-family: var(--eiq-product-font, Inter, "Segoe UI", Helvetica, Arial, sans-serif) !important;
  letter-spacing: 0 !important;
}

.eiq-home-v1-link {
  border: 0 !important;
  background: transparent !important;
  color: var(--eiq-product-text, #172033) !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  padding: 0 !important;
  text-align: left !important;
  cursor: pointer;
}

.eiq-home-v1-button {
  height: 36px !important;
  padding: 0 16px !important;
  border-radius: 6px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  cursor: pointer;
}

.eiq-home-v1-button--primary {
  color: #ffffff !important;
  background: var(--eiq-product-blue, #2456b8) !important;
  border: 1px solid var(--eiq-product-blue, #2456b8) !important;
}

.eiq-home-v1__lower-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  gap: 16px;
}

.eiq-home-v1__activity > div,
.eiq-home-v1__launcher > div,
.eiq-home-v1__quality dl {
  display: grid;
  gap: 0;
}

.eiq-home-v1__activity article {
  height: 44px;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) 120px;
  align-items: center;
  gap: 12px;
  border-top: 1px solid var(--eiq-product-border-soft, #edf1f6);
}

.eiq-home-v1__activity article:first-child,
.eiq-home-v1__launcher button:first-child,
.eiq-home-v1__quality dl div:first-child {
  border-top: 0;
}

.eiq-home-v1__activity strong,
.eiq-home-v1__activity time,
.eiq-home-v1__launcher strong,
.eiq-home-v1__quality dt,
.eiq-home-v1__quality dd {
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--eiq-product-text, #172033) !important;
}

.eiq-home-v1__activity time {
  text-align: right;
  color: var(--eiq-product-muted, #5f6b7a) !important;
}

.eiq-home-v1__launcher button {
  height: 40px !important;
  width: 100%;
  display: grid;
  grid-template-columns: 28px minmax(130px, 0.42fr) minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  border: 0 !important;
  border-top: 1px solid var(--eiq-product-border-soft, #edf1f6) !important;
  border-radius: 0 !important;
  background: #ffffff !important;
  text-align: left !important;
  cursor: pointer;
}

.eiq-home-v1__launcher button:hover {
  background: rgba(36, 86, 184, 0.035) !important;
}

.eiq-home-v1__quality dl {
  margin: 0;
}

.eiq-home-v1__quality dl div {
  min-height: 30px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-top: 1px solid var(--eiq-product-border-soft, #edf1f6);
}

.eiq-home-v1__quality dt,
.eiq-home-v1__quality dd {
  margin: 0;
}

.eiq-home-v1__quality dt {
  color: var(--eiq-product-muted, #5f6b7a) !important;
  font-weight: 500 !important;
  text-align: left;
}

.eiq-home-v1__quality dd {
  text-align: right;
  font-weight: 700 !important;
}

.eiq-home-v1 .is-ready {
  color: var(--eiq-product-green, #1f8f5f) !important;
}

.eiq-home-v1 .is-awaiting {
  color: #b88000 !important;
}

.eiq-home-v1 .is-failed {
  color: var(--eiq-product-red, #b42318) !important;
}

.eiq-home-v1-empty {
  margin: 0 !important;
  font-size: 13px !important;
  color: var(--eiq-product-muted, #5f6b7a) !important;
}

.eiq-home-v1__floating-status {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 300px;
  display: grid;
  gap: 4px;
  background: #ffffff !important;
  border: 1px solid var(--eiq-product-border, #dfe5ee) !important;
  border-radius: 8px !important;
  padding: 14px 16px !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08) !important;
}

.eiq-home-v1__floating-status strong,
.eiq-home-v1__floating-status span {
  font-size: 13px !important;
  font-weight: 600 !important;
}

.eiq-home-v1__floating-status small {
  font-size: 12px !important;
  font-weight: 500 !important;
  color: var(--eiq-product-muted, #5f6b7a) !important;
}

@media (max-width: 1366px) {
  .eiq-home-v1__top-row {
    grid-template-columns: minmax(0, 1fr) 380px;
  }

  .eiq-home-v1__lower-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .eiq-home-v1__floating-status {
    position: static;
    width: min(100%, 1600px);
    margin: 20px auto 0;
  }
}

@media (max-width: 900px) {
  .eiq-home-v1__top-row,
  .eiq-home-v1__value-panels {
    grid-template-columns: 1fr;
  }
}
'''
marker = "/* EDGEIQ HOME WORKSPACE V1 LOCKED SPECIFICATION */"
if marker not in css:
    css += home_css
else:
    start = css.index(marker)
    css = css[:start] + home_css
CSS.write_text(css, encoding="utf-8")
print("EDGEIQ_HOME_WORKSPACE_V1_LOCKED_SPEC_APPLIED")
