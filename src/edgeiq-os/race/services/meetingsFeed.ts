import { edgeiqDataPath } from "../../../config/edgeiqDataOrigin";
import {
  loadThreeDayCatalog,
  type ThreeDayCatalog,
  type ThreeDayMeeting,
  type ThreeDayRace,
  type ThreeDayRunner,
} from "./threeDayCatalog";
import { canonicalTrackRatingDisplay, canonicalWeatherDisplay } from "../../design-system/presentation";

export type MeetingsDayKey = "TODAY" | "TOMORROW" | "DAY_PLUS_2";

type ThreeDayWindowDate = {
  key: MeetingsDayKey;
  date: string;
  dayOffset: number;
};

type ThreeDayWindow = {
  schemaVersion: string;
  timezone: string;
  generatedAt: string;
  dates: ThreeDayWindowDate[];
};

export type MeetingEvidenceItem = {
  label: string;
  value: string;
  authority: "official" | "governed" | "unavailable";
};

export type MeetingRaceSummaryViewModel = {
  raceKey: string;
  raceNumber: number;
  label: string;
  time: string;
  distance: string;
  name: string;
  raceClass: string;
  restriction: string;
  fieldSize: number;
  status: string;
  rawRace: ThreeDayRace;
};

export type MeetingSummaryViewModel = {
  meetingKey: string;
  meeting: string;
  venue: string;
  state: string;
  rail: string;
  track: string;
  weather: string;
  wind: string;
  temp: string;
  rain24h: string;
  irrigation24h: string;
  officialUpdate: string;
  races: number;
  declared: number;
  scratchings: number;
  first: string;
  last: string;
  status: string;
  notes: MeetingEvidenceItem[];
  raceSummaries: MeetingRaceSummaryViewModel[];
  rawMeeting: ThreeDayMeeting;
};

export type MeetingsDayViewModel = {
  key: MeetingsDayKey;
  label: "TODAY" | "TOMORROW" | "DAY +2";
  date: string;
  displayDate: string;
  generatedAt: string;
  totals: {
    meetings: number;
    races: number;
    declared: number;
    scratchings: number;
    heavyTracks: number;
    softTracks: number;
    goodTracks: number;
    weatherAlerts: number;
  };
  meetings: MeetingSummaryViewModel[];
};

export type MeetingsWorkspaceViewModel = {
  workspaceId: "BETA-002";
  status: "READY";
  generatedAt: string;
  generatedAtDisplay: string;
  days: MeetingsDayViewModel[];
};

const WINDOW_URL = edgeiqDataPath("/data/edgeiq_three_day_window_v1.json");

let cachedWindow: ThreeDayWindow | null = null;
let pendingWindow: Promise<ThreeDayWindow> | null = null;
let cachedViewModel: MeetingsWorkspaceViewModel | null = null;
let pendingViewModel: Promise<MeetingsWorkspaceViewModel> | null = null;

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).replace(/\s+/g, " ").trim();
  if (!text || text === "-" || text === "Pending") return "";
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

function unavailable(value: unknown, fallback = "Not supplied"): string {
  return firstText(value) || fallback;
}

function formatWindowDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("en-AU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

function formatLocalTime(value: unknown): string {
  const text = usable(value);
  if (!text) return "";
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;
  return new Intl.DateTimeFormat("en-AU", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Melbourne",
  })
    .format(parsed)
    .replace(/\s/g, "")
    .toLowerCase();
}

function formatGeneratedAt(value: string): string {
  return formatLocalTime(value) || "Not supplied";
}

function formatOfficialUpdate(value: unknown): string {
  const text = usable(value);
  if (!text) return "Not supplied";

  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;

  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Melbourne",
    timeZoneName: "short",
  }).format(parsed);
}

function dateLabel(key: MeetingsDayKey): "TODAY" | "TOMORROW" | "DAY +2" {
  if (key === "DAY_PLUS_2") return "DAY +2";
  return key;
}

function raceTime(race: ThreeDayRace): string {
  return firstText(race.raceTime, formatLocalTime(race.source?.race_time_utc)) || "Not supplied";
}

function raceStatus(race: ThreeDayRace): string {
  const raw = firstText(
    race.source?.race_status,
    race.source?.result_status,
    race.source?.full_status,
    race.source?.meet_status,
  );
  if (!raw) return "Not supplied";
  const upper = raw.toUpperCase();
  if (upper.includes("FINAL")) return "Final fields";
  if (upper.includes("ACCEPT")) return "Acceptances";
  if (upper.includes("RESULT")) return "Results";
  if (upper.includes("ABANDON")) return "Abandoned";
  return raw;
}

function meetingStatus(meeting: ThreeDayMeeting): string {
  const raw = firstText(
    meeting.source?.FullStatus,
    meeting.source?.MeetStatus,
    meeting.source?.Status,
    meeting.races[0]?.source?.full_status,
    meeting.races[0]?.source?.meet_status,
  );
  if (!raw) return "Not supplied";
  const upper = raw.toUpperCase();
  if (upper.includes("ACCEPT")) return "Acceptances";
  if (upper.includes("FINAL")) return "Final fields";
  if (upper.includes("RESULT")) return "Results";
  if (upper.includes("ABANDON")) return "Abandoned";
  return raw;
}

function trackRating(race: ThreeDayRace | undefined, meeting: ThreeDayMeeting): string {
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
}

function trackConditionKind(value: string): "heavy" | "soft" | "good" | "other" {
  const text = value.toLowerCase();
  if (text.includes("heavy")) return "heavy";
  if (text.includes("soft")) return "soft";
  if (text.includes("good")) return "good";
  return "other";
}

function railPosition(race: ThreeDayRace | undefined, meeting: ThreeDayMeeting): string {
  return unavailable(
    firstText(race?.rail, race?.source?.rail_position, meeting.rail),
  );
}

function weatherLabel(race: ThreeDayRace | undefined): string {
  return canonicalWeatherDisplay(firstText(race?.source?.weather));
}

function windLabel(race: ThreeDayRace | undefined): string {
  const direction = firstText(race?.source?.weather_wind_direction);
  const speed = firstText(race?.source?.weather_wind_speed);
  if (direction && speed) return `${direction} ${speed}`;
  return firstText(direction, speed) || "Not supplied";
}

function tempLabel(race: ThreeDayRace | undefined): string {
  const min = firstText(race?.source?.weather_min);
  const max = firstText(race?.source?.weather_max);
  if (min && max) return `${min}-${max}`;
  return firstText(max, min) || "Not supplied";
}

function rainLabel(race: ThreeDayRace | undefined): string {
  return firstText(race?.source?.rainfall, race?.source?.weather_rain) || "Not supplied";
}

function officialUpdate(race: ThreeDayRace | undefined, catalog: ThreeDayCatalog): string {
  const sourceTimestamp = firstText(
    race?.source?.built_at,
    catalog.generatedAt,
  );

  return formatOfficialUpdate(sourceTimestamp);
}

function runnerIsScratched(runner: ThreeDayRunner): boolean {
  const official = (runner.official ?? {}) as Record<string, unknown>;
  const source = runner.source ?? {};
  return (
    official.scratched === true ||
    source.scratched === true ||
    firstText(official.status, source.status).toLowerCase().includes("scratch")
  );
}

function raceRestriction(race: ThreeDayRace): string {
  const name = firstText(race.raceName);
  if (/3yo|3yo\+|2yo|fillies|mares|colts|geldings/i.test(name)) {
    const match = name.match(/(2YO|3YO\+?|Fillies|Mares|Colts|Geldings)/i);
    return match?.[0] ?? "";
  }
  return "";
}

function buildNotes(summary: {
  track: string;
  rail: string;
  weather: string;
  wind: string;
  officialUpdate: string;
}): MeetingEvidenceItem[] {
  return [
    { label: "Today's Track", value: summary.track, authority: summary.track === "Not supplied" ? "unavailable" : "official" },
    { label: "Rail", value: summary.rail, authority: summary.rail === "Not supplied" ? "unavailable" : "official" },
    { label: "Weather", value: summary.weather, authority: summary.weather === "Awaiting Weather Feed" ? "unavailable" : "governed" },
    { label: "Wind", value: summary.wind, authority: summary.wind === "Not supplied" ? "unavailable" : "governed" },
    { label: "Official Update", value: summary.officialUpdate, authority: summary.officialUpdate === "Not supplied" ? "unavailable" : "official" },
  ];
}

function buildRaceSummary(race: ThreeDayRace): MeetingRaceSummaryViewModel {
  return {
    raceKey: race.raceKey,
    raceNumber: race.raceNumber,
    label: `R${race.raceNumber}`,
    time: raceTime(race),
    distance: unavailable(race.distance),
    name: unavailable(race.raceName, "Unnamed race"),
    raceClass: unavailable(race.raceClass),
    restriction: raceRestriction(race) || "Not supplied",
    fieldSize: race.runners.length,
    status: raceStatus(race),
    rawRace: race,
  };
}

function buildMeetingSummary(
  meeting: ThreeDayMeeting,
  catalog: ThreeDayCatalog,
): MeetingSummaryViewModel {
  const races = [...meeting.races].sort((a, b) => a.raceNumber - b.raceNumber);
  const firstRace = races[0];
  const lastRace = races[races.length - 1];
  const declared = races.reduce((total, race) => total + race.runners.length, 0);
  const scratchings = races.reduce(
    (total, race) => total + race.runners.filter(runnerIsScratched).length,
    0,
  );
  const representativeRace = firstRace;
  const track = trackRating(representativeRace, meeting);
  const rail = railPosition(representativeRace, meeting);
  const weather = weatherLabel(representativeRace);
  const wind = windLabel(representativeRace);
  const temp = tempLabel(representativeRace);
  const rain24h = rainLabel(representativeRace);
  const irrigation24h = firstText(representativeRace?.source?.irrigation) || "Not supplied";
  const update = officialUpdate(representativeRace, catalog);
  const venue = firstText(
    meeting.source?.Venue,
    meeting.source?.Track,
    meeting.providerMeetingKey,
    meeting.meeting,
  );
  const raceSummaries = races.map(buildRaceSummary);

  return {
    meetingKey: meeting.meetingKey,
    meeting: unavailable(meeting.meeting, "Unnamed meeting"),
    venue: venue || unavailable(meeting.meeting),
    state: unavailable(meeting.source?.State),
    rail,
    track,
    weather,
    wind,
    temp,
    rain24h,
    irrigation24h,
    officialUpdate: update,
    races: meeting.raceCount || races.length,
    declared,
    scratchings,
    first: firstRace ? raceTime(firstRace) : "Not supplied",
    last: lastRace ? raceTime(lastRace) : "Not supplied",
    status: meetingStatus(meeting),
    notes: buildNotes({ track, rail, weather, wind, officialUpdate: update }),
    raceSummaries,
    rawMeeting: meeting,
  };
}

function buildDay(
  windowDay: ThreeDayWindowDate,
  catalog: ThreeDayCatalog,
): MeetingsDayViewModel {
  const meetings = catalog.meetings
    .filter((meeting) => meeting.date === windowDay.date)
    .map((meeting) => buildMeetingSummary(meeting, catalog));
  const totals = meetings.reduce(
    (next, meeting) => {
      const condition = trackConditionKind(meeting.track);
      next.meetings += 1;
      next.races += meeting.races;
      next.declared += meeting.declared;
      next.scratchings += meeting.scratchings;
      if (condition === "heavy") next.heavyTracks += 1;
      if (condition === "soft") next.softTracks += 1;
      if (condition === "good") next.goodTracks += 1;
      if (
        meeting.weather !== "Awaiting Weather Feed" ||
        meeting.wind !== "Not supplied" ||
        meeting.rain24h !== "Not supplied"
      ) {
        next.weatherAlerts += 1;
      }
      return next;
    },
    {
      meetings: 0,
      races: 0,
      declared: 0,
      scratchings: 0,
      heavyTracks: 0,
      softTracks: 0,
      goodTracks: 0,
      weatherAlerts: 0,
    },
  );

  return {
    key: windowDay.key,
    label: dateLabel(windowDay.key),
    date: windowDay.date,
    displayDate: formatWindowDate(windowDay.date),
    generatedAt: catalog.generatedAt,
    totals,
    meetings,
  };
}

async function loadThreeDayWindow(force = false): Promise<ThreeDayWindow> {
  if (!force && cachedWindow) return cachedWindow;
  if (pendingWindow) return pendingWindow;

  pendingWindow = fetch(
    `${WINDOW_URL}?updated=${encodeURIComponent(String(Date.now()))}`,
    { cache: "no-store" },
  )
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Three-day window failed with ${response.status}`);
      }
      return (await response.json()) as ThreeDayWindow;
    })
    .then((windowModel) => {
      cachedWindow = windowModel;
      return windowModel;
    })
    .finally(() => {
      pendingWindow = null;
    });

  return pendingWindow;
}

export async function loadMeetingsWorkspaceViewModel(
  force = false,
): Promise<MeetingsWorkspaceViewModel> {
  if (!force && cachedViewModel) return cachedViewModel;
  if (pendingViewModel) return pendingViewModel;

  pendingViewModel = Promise.all([
    loadThreeDayWindow(force),
    loadThreeDayCatalog(force),
  ])
    .then(([windowModel, catalog]) => {
      const viewModel: MeetingsWorkspaceViewModel = {
        workspaceId: "BETA-002",
        status: "READY",
        generatedAt: firstText(catalog.generatedAt, windowModel.generatedAt),
        generatedAtDisplay: formatGeneratedAt(firstText(catalog.generatedAt, windowModel.generatedAt)),
        days: windowModel.dates.map((day) => buildDay(day, catalog)),
      };
      cachedViewModel = viewModel;
      return viewModel;
    })
    .finally(() => {
      pendingViewModel = null;
    });

  return pendingViewModel;
}
