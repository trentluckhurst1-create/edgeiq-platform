import type { ThreeDayMeeting } from "./threeDayCatalog";

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
  victorianTrack: MetropolitanWeatherRecord[];
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
const VICTORIAN_TRACK_WEATHER_URL = "/data/edgeiq_victorian_track_weather_v1.json";

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

function victorianTrackToMetropolitan(record: Record<string, unknown>): MetropolitanWeatherRecord {
  const provider = firstText(record.weather_provider, "Bureau of Meteorology");
  return {
    meeting_key: record.canonical_venue_name,
    meeting: record.canonical_venue_name,
    course: record.canonical_venue_name,
    provider,
    source_name: provider,
    source_url: null,
    source_endpoint: null,
    fetched_at_utc: record.generated_timestamp,
    source_observed_datetime: record.observation_timestamp,
    source_observed_time: record.observation_timestamp,
    station_status: record.availability_status,
    source_status: record.availability_status,
    governed_source_state: record.availability_status,
    freshness_status: record.freshness_status,
    official_track_rating: null,
    official_rail: null,
    going_stick: null,
    temperature_c: record.temperature_c,
    rainfall_24h_mm: null,
    rainfall_since_9am_mm: record.rain_since_9am_mm,
    rainfall_today_mm: record.rain_since_9am_mm,
    rainfall_7day_mm: null,
    forecast_rainfall: null,
    humidity_pct: record.humidity_pct,
    moisture_loss_mm: null,
    soil_moisture: null,
    irrigation: null,
    weather_comment: record.user_disclosure,
    additional_comment: record.station_relationship,
    wind_direction: record.wind_direction,
    wind_speed_kmh: record.wind_speed_kmh,
    wind_average_kmh: record.wind_speed_kmh,
    wind_gust_kmh: record.wind_gust_kmh,
    wind_gust_max_kmh: record.wind_gust_kmh,
    wind_station: null,
    wind_station_count: 1,
    turf_http_status: null,
    wind_http_status: null,
    errors: [],
  };
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
    loadJson(VICTORIAN_TRACK_WEATHER_URL).catch(() => ({ records: [] })),
  ])
    .then(([metropolitanPayload, racePayload, onTrackPayload, victorianTrackPayload]) => {
      const metropolitan = Array.isArray((metropolitanPayload as any)?.records)
        ? (metropolitanPayload as any).records
        : [];
      const raceWeather = Array.isArray((racePayload as any)?.records) ? (racePayload as any).records : [];
      const onTrack = Array.isArray((onTrackPayload as any)?.records)
        ? (onTrackPayload as any).records.map((record: Record<string, unknown>) => onTrackToMetropolitan(record))
        : [];
      const victorianTrack = Array.isArray((victorianTrackPayload as any)?.records)
        ? (victorianTrackPayload as any).records.map((record: Record<string, unknown>) => victorianTrackToMetropolitan(record))
        : [];
      if (metropolitan.length > 10000 || raceWeather.length > 10000 || onTrack.length > 10000 || victorianTrack.length > 10000) {
        console.warn("EDGEiQ rejected oversized weather feed", metropolitan.length, raceWeather.length, onTrack.length, victorianTrack.length);
        return {
          metropolitan: [],
          raceWeather: [],
          onTrack: [],
          victorianTrack: [],
          generatedAt: null,
          sourceError: "Weather feed exceeded frontend row limit",
        };
      }
      return {
        metropolitan: [...victorianTrack, ...onTrack, ...metropolitan],
        raceWeather,
        onTrack,
        victorianTrack,
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
