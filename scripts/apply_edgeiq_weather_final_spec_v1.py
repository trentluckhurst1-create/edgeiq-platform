from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWeatherWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "weatherFeed.ts"
MEETING_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"


COMPONENT_TEXT = r'''import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import {
  buildMeetingWeatherViewModel,
  loadWeatherTerminalFeeds,
  type MeetingWeatherViewModel,
  type WeatherTerminalFeeds,
  type WeatherValue,
} from "../services/weatherFeed";

type MeetingWeatherWorkspaceProps = {
  meeting: ThreeDayMeeting;
};

function valueOrUnavailable(value: string | null | undefined): string {
  return value && value.trim() ? value : "Unavailable";
}

function statusText(status: MeetingWeatherViewModel["status"]): string {
  if (status === "current") return "Current";
  if (status === "stale") return "Stale";
  if (status === "error") return "Unavailable";
  return "Unavailable";
}

function SummaryGrid({ items }: { items: WeatherValue[] }) {
  return (
    <dl className="eiq-weather-v1-summary-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{valueOrUnavailable(item.value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function WorkspaceHeader({ model }: { model: MeetingWeatherViewModel }) {
  const authority = valueOrUnavailable(model.source.authority);
  const observedAt = valueOrUnavailable(model.source.observedAt);
  return (
    <header className="eiq-weather-v1-header">
      <div>
        <span>WEATHER</span>
        <h2>Meeting weather and race-day conditions</h2>
        <p>{model.meetingName}</p>
      </div>
      <dl className="eiq-weather-v1-status-strip" aria-label="Weather data state">
        <div>
          <dt>STATE</dt>
          <dd>{statusText(model.status)}</dd>
        </div>
        <div>
          <dt>AUTHORITY</dt>
          <dd>{authority}</dd>
        </div>
        <div>
          <dt>OBSERVED</dt>
          <dd>{observedAt}</dd>
        </div>
      </dl>
    </header>
  );
}

function WeatherSummary({ model }: { model: MeetingWeatherViewModel }) {
  return (
    <section className="eiq-weather-v1-panel">
      <header>
        <span>Current Observations</span>
      </header>
      <SummaryGrid items={model.summary} />
    </section>
  );
}

function RaceDayImpact({ model }: { model: MeetingWeatherViewModel }) {
  return (
    <section className="eiq-weather-v1-panel">
      <header>
        <span>Race-Day Weather Context</span>
      </header>
      <dl className="eiq-weather-v1-impact-grid">
        {model.impactRows.map((row) => (
          <div key={row.label}>
            <dt>{row.label}</dt>
            <dd>{valueOrUnavailable(row.value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function WeatherNotes({ model }: { model: MeetingWeatherViewModel }) {
  if (!model.notes.length) return null;
  return (
    <section className="eiq-weather-v1-panel eiq-weather-v1-notes">
      <header>
        <span>Meeting Weather Notes</span>
      </header>
      <ul>
        {model.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}

export function MeetingWeatherWorkspace({ meeting }: MeetingWeatherWorkspaceProps) {
  const [feeds, setFeeds] = useState<WeatherTerminalFeeds | null>(null);
  const [loading, setLoading] = useState(true);
  const [sourceError, setSourceError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadWeatherTerminalFeeds()
      .then((nextFeeds) => {
        if (cancelled) return;
        setFeeds(nextFeeds);
        setSourceError(nextFeeds.sourceError ?? null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : String(error);
        setSourceError(message);
        setFeeds({
          metropolitan: [],
          raceWeather: [],
          onTrack: [],
          generatedAt: null,
          sourceError: message,
        });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const model = useMemo(
    () =>
      feeds
        ? buildMeetingWeatherViewModel(meeting, feeds, {
            sourceError,
          })
        : null,
    [feeds, meeting, sourceError],
  );

  if (loading || !model) {
    return (
      <section className="eiq-weather-v1">
        <div className="eiq-weather-v1-loading">
          <span>WEATHER</span>
          <strong>Loading official weather data...</strong>
        </div>
      </section>
    );
  }

  return (
    <section className="eiq-weather-v1" aria-label="Weather workspace">
      <WorkspaceHeader model={model} />
      {model.status === "unavailable" || model.status === "error" ? (
        <section className="eiq-weather-v1-unavailable">
          <strong>Official weather data is not currently available for this meeting.</strong>
        </section>
      ) : null}
      {model.status === "stale" ? (
        <section className="eiq-weather-v1-unavailable">
          <strong>Latest available weather observations are stale.</strong>
          <p>EDGEiQ displays the governed observation state and does not treat stale observations as current.</p>
        </section>
      ) : null}
      <div className="eiq-weather-v1-layout">
        <main className="eiq-weather-v1-stack">
          <WeatherSummary model={model} />
          <RaceDayImpact model={model} />
          <WeatherNotes model={model} />
        </main>
      </div>
    </section>
  );
}
'''


SERVICE_TEXT = r'''import type { ThreeDayMeeting } from "./threeDayCatalog";

export type WeatherWorkspaceStatus = "loading" | "empty" | "unavailable" | "stale" | "error" | "current";

export type WeatherValue = {
  label: string;
  value: string | null;
  source: string | null;
};

export type WeatherHourlyRow = {
  time: string | null;
  weather: string | null;
  tempC: string | null;
  windKmh: string | null;
  gustsKmh: string | null;
  rainProbability: string | null;
  rainMm: string | null;
  source: string | null;
};

export type WeatherImpactRow = {
  label: "TRACK IMPACT" | "WIND IMPACT" | "RAIN TIMING" | "OVERALL OUTLOOK";
  value: string | null;
  source: string | null;
};

export type WeatherTerminalFeeds = {
  metropolitan: MetropolitanWeatherRecord[];
  raceWeather: RaceWeatherRecord[];
  onTrack: MetropolitanWeatherRecord[];
  generatedAt: string | null;
  sourceError?: string | null;
};

export type MeetingWeatherViewModel = {
  workspaceId: "BETA-007";
  meetingKey: string;
  generatedAt: string | null;
  status: WeatherWorkspaceStatus;
  meetingName: string;
  summary: WeatherValue[];
  hourlyRows: WeatherHourlyRow[];
  impactRows: WeatherImpactRow[];
  notes: string[];
  source: {
    metropolitanRows: number;
    raceWeatherRows: number;
    sourceStatus: string;
    gapReason: string | null;
    authority: string | null;
    observedAt: string | null;
    freshnessStatus: string | null;
  };
};

type MetropolitanWeatherRecord = Record<string, unknown>;
type RaceWeatherRecord = Record<string, unknown>;

const METROPOLITAN_URL = "/data/edgeiq_metropolitan_weather_v1.json";
const RACE_WEATHER_URL = "/data/edgeiq_race_weather_v1.json";
const ON_TRACK_WEATHER_URL = "/data/edgeiq_on_track_weather_governed_v1_2.json";

let cachedFeeds: WeatherTerminalFeeds | null = null;
let pendingFeeds: Promise<WeatherTerminalFeeds> | null = null;

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text === "—") return "";
  if (["null", "undefined", "none", "n/a", "na"].includes(text.toLowerCase())) return "";
  return text;
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = usable(value);
    if (text) return text;
  }
  return "";
}

function normaliseMeeting(value: unknown): string {
  return String(value ?? "")
    .toUpperCase()
    .replace(/\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, "");
}

function num(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(String(value).replace(/[^\d.-]/g, ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function metric(value: unknown, unit: string, precision = 1): string | null {
  const parsed = num(value);
  if (parsed === null) return null;
  return `${parsed.toFixed(precision).replace(/\.0$/, "")}${unit}`;
}

function value(label: string, val: unknown, source: string | null): WeatherValue {
  return { label, value: firstText(val) || null, source };
}

function onTrackToMetropolitan(record: Record<string, unknown>): MetropolitanWeatherRecord {
  const sourceOwner = firstText(record.source_owner, "On-track");
  return {
    meeting_key: record.track_group,
    meeting: record.track_group,
    course: record.track_group,
    provider: sourceOwner,
    source_name: `${sourceOwner} on-track weather`,
    source_url: record.source_page,
    source_endpoint: record.live_request_url,
    fetched_at_utc: record.fetched_at,
    source_observed_datetime: record.observation_local,
    source_observed_time: firstText(record.source_timestamp, record.observation_local),
    station_status: record.station_status,
    source_status: record.governed_source_state,
    governed_source_state: record.governed_source_state,
    freshness_status: record.freshness_status,
    official_track_rating: record.going_report,
    official_rail: null,
    going_stick: null,
    temperature_c: record.temperature_c,
    rainfall_24h_mm: record.rain_24h_mm,
    rainfall_since_9am_mm: null,
    rainfall_today_mm: record.rain_today_mm,
    rainfall_7day_mm: record.rain_7d_mm,
    forecast_rainfall: null,
    humidity_pct: record.humidity_percent,
    moisture_loss_mm: null,
    soil_moisture: null,
    irrigation: null,
    weather_comment: record.weather_comment,
    additional_comment: null,
    wind_direction: record.wind_direction_text,
    wind_speed_kmh: record.wind_speed_kmh,
    wind_average_kmh: record.wind_speed_average_kmh,
    wind_gust_kmh: record.wind_gust_kmh,
    wind_gust_max_kmh: record.wind_gust_max_kmh,
    wind_station: record.station_id,
    wind_station_count: 1,
    turf_http_status: null,
    wind_http_status: null,
    errors: [],
  };
}

async function loadJson(url: string): Promise<unknown> {
  const response = await fetch(`${url}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url} failed with ${response.status}`);
  return response.json();
}

export async function loadWeatherTerminalFeeds(force = false): Promise<WeatherTerminalFeeds> {
  if (!force && cachedFeeds) return cachedFeeds;
  if (pendingFeeds) return pendingFeeds;
  pendingFeeds = Promise.all([
    loadJson(METROPOLITAN_URL),
    loadJson(RACE_WEATHER_URL),
    loadJson(ON_TRACK_WEATHER_URL).catch(() => ({ records: [] })),
  ])
    .then(([metropolitanPayload, racePayload, onTrackPayload]) => {
      const metropolitan = Array.isArray((metropolitanPayload as any)?.records)
        ? (metropolitanPayload as any).records
        : [];
      const raceWeather = Array.isArray((racePayload as any)?.records) ? (racePayload as any).records : [];
      const onTrack = Array.isArray((onTrackPayload as any)?.records)
        ? (onTrackPayload as any).records.map((record: Record<string, unknown>) => onTrackToMetropolitan(record))
        : [];
      if (metropolitan.length > 10000 || raceWeather.length > 10000 || onTrack.length > 10000) {
        console.warn("EDGEiQ rejected oversized weather feed", metropolitan.length, raceWeather.length, onTrack.length);
        return {
          metropolitan: [],
          raceWeather: [],
          onTrack: [],
          generatedAt: null,
          sourceError: "Weather feed exceeded frontend row limit",
        };
      }
      return {
        metropolitan: [...onTrack, ...metropolitan],
        raceWeather,
        onTrack,
        generatedAt: firstText((metropolitanPayload as any)?.generated_at_utc, (onTrackPayload as any)?.generated_at),
        sourceError: null,
      };
    })
    .then((feeds) => {
      cachedFeeds = feeds;
      return feeds;
    })
    .finally(() => {
      pendingFeeds = null;
    });
  return pendingFeeds;
}

function findMetropolitan(meeting: ThreeDayMeeting, feeds: WeatherTerminalFeeds): MetropolitanWeatherRecord | null {
  const key = normaliseMeeting(meeting.meeting);
  return (
    feeds.metropolitan.find((record) => {
      const recordKey = normaliseMeeting(record.meeting_key ?? record.meeting ?? record.course);
      return recordKey === key || key.includes(recordKey) || recordKey.includes(key);
    }) ?? null
  );
}

function findRaceWeather(meeting: ThreeDayMeeting, feeds: WeatherTerminalFeeds): RaceWeatherRecord | null {
  const key = normaliseMeeting(meeting.meeting);
  return (
    feeds.raceWeather.find((record) => {
      const recordKey = normaliseMeeting(record.meeting);
      return firstText(record.raceDate) === meeting.date && (recordKey === key || recordKey.includes(key) || key.includes(recordKey));
    }) ?? null
  );
}

function impactRows(metro: MetropolitanWeatherRecord | null, race: RaceWeatherRecord | null): WeatherImpactRow[] {
  const source = firstText(metro?.source_name, race?.source) || null;
  const gap = firstText(race?.gapReason);
  const condition = firstText(race?.condition, metro?.weather_comment);
  return [
    {
      label: "TRACK IMPACT",
      value: gap ? null : firstText(race?.trackCondition, metro?.official_track_rating) || null,
      source,
    },
    {
      label: "WIND IMPACT",
      value: firstText(race?.windDirection, metro?.wind_direction)
        ? `${firstText(race?.windDirection, metro?.wind_direction)} ${metric(race?.windSpeedKmh ?? metro?.wind_speed_kmh, " km/h") ?? ""}`.trim()
        : null,
      source,
    },
    {
      label: "RAIN TIMING",
      value: condition || null,
      source,
    },
    {
      label: "OVERALL OUTLOOK",
      value: gap ? null : condition || null,
      source,
    },
  ];
}

export function buildMeetingWeatherViewModel(
  meeting: ThreeDayMeeting,
  feeds: WeatherTerminalFeeds,
  options: { sourceError?: string | null } = {},
): MeetingWeatherViewModel {
  const metro = findMetropolitan(meeting, feeds);
  const race = findRaceWeather(meeting, feeds);
  const authority = firstText(metro?.provider, race?.source) || null;
  const observedAt = firstText(race?.observedAt, metro?.source_observed_time, metro?.source_observed_datetime, feeds.generatedAt) || null;
  const source = firstText(metro?.source_name, race?.source) || "Official weather data";
  const gapReason = firstText(race?.gapReason) || null;
  const hasWeather = Boolean(metro || race);
  const sourceState = firstText(metro?.governed_source_state, metro?.source_status, race?.source_status);
  const freshnessStatus = firstText(metro?.freshness_status, race?.freshnessStatus);
  const stale =
    String(race?.stale ?? "").toLowerCase() === "true" ||
    race?.stale === true ||
    /STALE/i.test(sourceState) ||
    /STALE/i.test(freshnessStatus);
  const status: WeatherWorkspaceStatus = options.sourceError
    ? "error"
    : !hasWeather
      ? "unavailable"
      : stale
        ? "stale"
        : "current";

  const summary = [
    value("CURRENT CONDITION", firstText(race?.condition, metro?.weather_comment), source),
    value("TRACK CONDITION", firstText(race?.trackCondition, metro?.official_track_rating), source),
    value("TEMPERATURE", metric(race?.temperatureC ?? metro?.temperature_c, "C"), source),
    value(
      "WIND",
      firstText(race?.windDirection, metro?.wind_direction)
        ? `${firstText(race?.windDirection, metro?.wind_direction)} ${metric(race?.windSpeedKmh ?? metro?.wind_speed_kmh, " km/h") ?? ""}`.trim()
        : null,
      source,
    ),
    value("GUSTS", metric(race?.windGustKmh ?? metro?.wind_gust_kmh, " km/h"), source),
    value("HUMIDITY", metric(race?.humidityPct ?? metro?.humidity_pct, "%"), source),
    value("RAIN TODAY", metric(metro?.rainfall_today_mm, " mm"), source),
    value("RAIN 24H", metric(race?.rainfall24hMm ?? metro?.rainfall_24h_mm, " mm"), source),
    value("RAIN 7D", metric(metro?.rainfall_7day_mm, " mm"), source),
  ];

  return {
    workspaceId: "BETA-007",
    meetingKey: meeting.meetingKey,
    generatedAt: observedAt,
    status,
    meetingName: meeting.meeting,
    summary,
    hourlyRows: [],
    impactRows: impactRows(metro, race),
    notes: [gapReason ? "Weather facts are unavailable for this meeting." : ""].filter(Boolean),
    source: {
      metropolitanRows: feeds.metropolitan.length,
      raceWeatherRows: feeds.raceWeather.length,
      sourceStatus: options.sourceError ?? sourceState ?? (hasWeather ? "Loaded" : "Unavailable"),
      gapReason,
      authority,
      observedAt,
      freshnessStatus: freshnessStatus || null,
    },
  };
}
'''


def replace_once(text: str, old: str, new: str, path: Path) -> str:
  if old not in text:
    raise RuntimeError(f"Expected block not found in {path}")
  return text.replace(old, new, 1)


def patch_meeting_workspace() -> None:
  text = MEETING_WORKSPACE.read_text(encoding="utf-8")
  old_modes = '''  const activePending = MEETING_DETAIL_TAB_ORDER.find((item) => item.key === tab && item.key !== "RACES");
  const weatherFixtureMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqWeatherFixture") === "1";
  const weatherUnavailableMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqWeatherUnavailable") === "1";
  const weatherPartialMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqWeatherPartial") === "1";
'''
  new_modes = '''  const activePending = MEETING_DETAIL_TAB_ORDER.find((item) => item.key === tab && item.key !== "RACES");
'''
  text = replace_once(text, old_modes, new_modes, MEETING_WORKSPACE)
  old_weather = '''          ) : tab === "WEATHER" ? (
            <MeetingWeatherWorkspace
              meeting={meeting}
              fixtureMode={weatherFixtureMode}
              unavailableMode={weatherUnavailableMode}
              partialMode={weatherPartialMode}
            />
'''
  new_weather = '''          ) : tab === "WEATHER" ? (
            <MeetingWeatherWorkspace meeting={meeting} />
'''
  text = replace_once(text, old_weather, new_weather, MEETING_WORKSPACE)
  MEETING_WORKSPACE.write_text(text, encoding="utf-8")


def patch_css() -> None:
  css = CSS.read_text(encoding="utf-8")
  block = r'''

/* EDGEIQ WEATHER FINAL SPEC V1 */
.eiq-weather-v1-status-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(92px, 1fr));
  gap: 8px;
  margin: 0;
  min-width: min(460px, 100%);
}

.eiq-weather-v1-status-strip div {
  border: 1px solid #e5e8ee;
  border-radius: 10px;
  background: #ffffff;
  padding: 9px 10px;
}

.eiq-weather-v1-status-strip dt {
  color: #7c8798;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.eiq-weather-v1-status-strip dd {
  margin: 4px 0 0;
  color: #172033;
  font-size: 12px;
  font-weight: 760;
}

.eiq-weather-v1-notes ul {
  margin: 0;
  padding: 12px 16px 14px 28px;
  color: #3c4656;
  font-size: 13px;
  line-height: 1.45;
}

.eiq-weather-v1 .eiq-weather-v1-unavailable {
  border: 1px solid #e5e8ee;
  border-radius: 12px;
  background: #fff;
  margin-bottom: 12px;
}

@media (max-width: 900px) {
  .eiq-weather-v1-status-strip {
    grid-template-columns: 1fr;
    min-width: 0;
  }
}
'''
  marker = "/* EDGEIQ WEATHER FINAL SPEC V1 */"
  if marker in css:
    start = css.index(marker)
    css = css[:start].rstrip() + "\n" + block
  else:
    css = css.rstrip() + "\n" + block
  CSS.write_text(css, encoding="utf-8")


def main() -> int:
  COMPONENT.write_text(COMPONENT_TEXT, encoding="utf-8")
  SERVICE.write_text(SERVICE_TEXT, encoding="utf-8")
  patch_meeting_workspace()
  patch_css()
  print("EDGEIQ_WEATHER_FINAL_SPEC_V1_APPLIED")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
