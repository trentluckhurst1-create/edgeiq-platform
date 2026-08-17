import { useEffect, useMemo, useState } from "react";

import { loadMeetingsWorkspaceViewModel, type MeetingSummaryViewModel, type MeetingsWorkspaceViewModel } from "../race/services/meetingsFeed";
import { canonicalTrackDisplayName, cleanProductText } from "../design-system/presentation";
import {
  EiqButton,
  EiqDataTable,
  EiqPanel,
  EiqSectionHeader,
  PageFrame,
  PageHeader,
} from "../design-system/v1";

type HomeWorkspaceSection = "meetings" | "race" | "field" | "formGuide" | "performance" | "epi" | "map" | "market" | "overview" | "insights" | "results" | "lab" | "compare" | "review" | "settings";

type EdgeiqOsHomeProps = {
  onOpenMeetings?: () => void;
  onOpenWorkspace?: (section: HomeWorkspaceSection) => void;
};

const workspaceRows: Array<{ icon: string; title: string; description: string; section: HomeWorkspaceSection }> = [
  { icon: "RI", title: "Race Intelligence", description: "Race overview, key determinants and runner board.", section: "race" },
  { icon: "PF", title: "Performance", description: "Ratings, benchmarks and performance evidence.", section: "performance" },
  { icon: "MK", title: "Market", description: "Market position, prices and movement context.", section: "market" },
  { icon: "EP", title: "EPI", description: "Ranking, benchmarks and intelligence signals.", section: "epi" },
  { icon: "MP", title: "Map", description: "Barrier map, settling positions and race shape.", section: "map" },
  { icon: "LB", title: "Lab", description: "Research queries and governed diagnostics.", section: "lab" },
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

export function EdgeiqOsHome({ onOpenMeetings, onOpenWorkspace }: EdgeiqOsHomeProps) {
  const [model, setModel] = useState<MeetingsWorkspaceViewModel | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadMeetingsWorkspaceViewModel()
      .then((loaded) => {
        if (!cancelled) {
          setModel(loaded);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn("EDGEiQ home governed feed awaiting", error);
          setModel(null);
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

  return (
    <PageFrame className="eiq-home-v2 eiq-home-v1" aria-label="EDGEiQ home" data-edgeiq-workspace-key="HOME" data-edgeiq-mounted-component="EdgeiqOsHome">
      <div className="eiq-home-v2__inner eiq-home-v1__inner">
        <PageHeader
          eyebrow="HOME"
          title="EDGEiQ Operating Home"
          actions={<EiqButton onClick={onOpenMeetings}>View Meetings</EiqButton>}
        />

        <EiqPanel className="eiq-home-v2__meetings eiq-home-v1-card eiq-home-v1__meetings" aria-label="Today's Meetings">
          <EiqSectionHeader
            title="Today's Meetings"
            meta={<EiqButton size="compact" onClick={onOpenMeetings}>View Meetings</EiqButton>}
          />
          <p className="eiq-home-v3-section-date">{currentDisplayDate(model)}</p>
          <EiqDataTable
            density="compact"
            className="eiq-home-v2-table"
            wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}
          >
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
          </EiqDataTable>
        </EiqPanel>

        <section className="eiq-home-v1__lower-grid" aria-label="Home operating modules">
          <EiqPanel className="eiq-home-v2__activity eiq-home-v1-card eiq-home-v1__activity" aria-label="Recent Analysis">
            <EiqSectionHeader title="Recent Analysis" />
            <div>
              {activityRows.map((row) => (
                <article key={`${row.meeting}-${row.race}-${row.title}`}>
                  <span className="eiq-home-v3-race-id" aria-hidden="true">{row.race.replace(/^RACE\s+/i, "R")}</span>
                  <div>
                    <strong>{row.meeting} {row.race}</strong>
                    <p>{row.title}</p>
                  </div>
                  <time>{row.timestamp}</time>
                </article>
              ))}
              {!activityRows.length ? <p className="eiq-home-v1-empty">Awaiting Analysis Feed</p> : null}
            </div>
            <button className="eiq-home-v3-section-action" type="button" onClick={() => onOpenWorkspace?.("review")}>View all recent analysis</button>
          </EiqPanel>

          <EiqPanel className="eiq-home-v2__launcher eiq-home-v1-card eiq-home-v1__launcher" aria-label="Workspaces">
            <EiqSectionHeader title="Workspaces" />
            <div>
              {workspaceRows.map((item) => (
                <button className="eiq-home-v2-workspace-button" key={item.title} type="button" onClick={() => onOpenWorkspace?.(item.section)}>
                  <span aria-hidden="true">{item.icon}</span>
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </button>
              ))}
            </div>
            <button className="eiq-home-v3-section-action" type="button" onClick={() => onOpenWorkspace?.("race")}>Open all workspaces</button>
          </EiqPanel>
        </section>
      </div>
    </PageFrame>
  );
}
