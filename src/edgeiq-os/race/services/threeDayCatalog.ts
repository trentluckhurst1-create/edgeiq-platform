import { edgeiqDataPath } from "../../../config/edgeiqDataOrigin";
import { normaliseCatalogTrackNames } from "../../design-system/presentation";

export type ThreeDayRunner = {
  official: {
    no?: unknown;
    number?: unknown;
    runner?: string | null;
    barrier?: unknown;
    jockey?: string | null;
    trainer?: string | null;
    weight?: string | null;
    market?: unknown;
  };
  source?: Record<string, unknown>;
  historicalRuns?: unknown[];
  evidenceRuns?: unknown[];
};

export type ThreeDayRace = {
  raceKey: string;
  raceNumber: number;
  raceName: string;
  distance: string | null;
  raceClass: string | null;
  raceTime: string | null;
  trackCondition: string | null;
  rail: string | null;
  runners: ThreeDayRunner[];
  source?: Record<string, unknown>;
};

export type ThreeDayMeeting = {
  meetingKey: string;
  meeting: string;
  providerMeetingKey: string;
  date: string;
  trackCondition: string | null;
  rail: string | null;
  raceCount: number;
  races: ThreeDayRace[];
  source?: Record<string, unknown>;
};

export type ThreeDayCatalog = {
  schemaVersion: string;
  generatedAt: string;
  dates: string[];
  dayLabels: Record<string, string>;
  meetings: ThreeDayMeeting[];
};

type SummaryRace = {
  raceKey: string;
  raceNumber: number;
  time: string;
  distance: string;
  name: string;
  raceClass: string;
  fieldSize: number;
  status: string;
};

type SummaryMeeting = {
  meetingKey: string;
  meeting: string;
  providerMeetingKey?: string;
  date: string;
  state: string;
  track: string;
  rail: string;
  races: number;
  raceSummaries: SummaryRace[];
};

type SummaryFeed = {
  schemaVersion: string;
  generatedAt: string;
  days: Array<{
    key: string;
    date: string;
    meetings: SummaryMeeting[];
  }>;
};

type MeetingDetailFeed = {
  schemaVersion: string;
  generatedAt: string;
  date: string;
  meetingKey: string;
  meeting: ThreeDayMeeting;
};

const SUMMARY_URL = edgeiqDataPath("/data/edgeiq_meetings_summary_feed_v1.json");
const WORKSPACE_STATE_STORAGE_KEY = "edgeiq-os-racefile-v3-state";
const MAX_SUMMARY_BYTES = 1_000_000;
const MAX_MEETING_DETAIL_BYTES = 8_000_000;

let cachedCatalog: ThreeDayCatalog | null = null;
let pendingCatalog: Promise<ThreeDayCatalog> | null = null;

function detailSlug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "meeting";
}

function lightweightRace(race: SummaryRace): ThreeDayRace {
  return {
    raceKey: race.raceKey,
    raceNumber: race.raceNumber,
    raceName: race.name,
    distance: race.distance === "Not supplied" ? null : race.distance,
    raceClass: race.raceClass === "Not supplied" ? null : race.raceClass,
    raceTime: race.time === "Not supplied" ? null : race.time,
    trackCondition: null,
    rail: null,
    runners: [],
    source: {
      lightweightSummary: true,
      field_size: race.fieldSize,
      race_status: race.status,
    },
  };
}

function lightweightMeeting(meeting: SummaryMeeting): ThreeDayMeeting {
  return {
    meetingKey: meeting.meetingKey,
    meeting: meeting.meeting,
    providerMeetingKey: meeting.providerMeetingKey ?? "",
    date: meeting.date,
    trackCondition: meeting.track === "Not supplied" ? null : meeting.track,
    rail: meeting.rail === "Not supplied" ? null : meeting.rail,
    raceCount: meeting.races,
    races: meeting.raceSummaries.map(lightweightRace),
    source: {
      State: meeting.state,
      lightweightSummary: true,
    },
  };
}

function persistedContext(): { meetingKey: string; raceKey: string } {
  if (typeof window === "undefined") return { meetingKey: "", raceKey: "" };
  try {
    const parsed = JSON.parse(window.localStorage.getItem(WORKSPACE_STATE_STORAGE_KEY) ?? "{}");
    return {
      meetingKey: typeof parsed.selectedMeetingKey === "string" ? parsed.selectedMeetingKey : "",
      raceKey: typeof parsed.selectedRaceKey === "string" ? parsed.selectedRaceKey : "",
    };
  } catch {
    return { meetingKey: "", raceKey: "" };
  }
}

async function fetchText(url: string, maxBytes: number, label: string): Promise<string> {
  const response = await fetch(`${url}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${label} failed with ${response.status}`);
  const text = await response.text();
  if (text.length > maxBytes) throw new Error(`${label} exceeds ${maxBytes} bytes`);
  return text;
}

async function fetchMeetingDetail(date: string, meetingKey: string): Promise<ThreeDayMeeting> {
  const url = edgeiqDataPath(`/data/meetings/${date}_${detailSlug(meetingKey)}.json`);
  const text = await fetchText(url, MAX_MEETING_DETAIL_BYTES, "Meeting detail");
  const payload = JSON.parse(text) as MeetingDetailFeed;
  if (!payload.meeting || payload.meeting.meetingKey !== meetingKey) {
    throw new Error("Meeting detail is invalid");
  }
  return payload.meeting;
}

async function buildLazyCatalog(): Promise<ThreeDayCatalog> {
  const text = await fetchText(SUMMARY_URL, MAX_SUMMARY_BYTES, "Meetings summary");
  const summary = JSON.parse(text) as SummaryFeed;
  if (!Array.isArray(summary.days)) throw new Error("Meetings summary is invalid");

  const meetings = summary.days.flatMap((day) => day.meetings.map(lightweightMeeting));
  const context = persistedContext();
  const target = meetings.find((meeting) => meeting.meetingKey === context.meetingKey)
    ?? meetings.find((meeting) => meeting.races.some((race) => race.raceKey === context.raceKey));

  if (target) {
    const fullMeeting = await fetchMeetingDetail(target.date, target.meetingKey);
    const index = meetings.findIndex((meeting) => meeting.meetingKey === target.meetingKey);
    if (index >= 0) meetings[index] = fullMeeting;
  }

  return normaliseCatalogTrackNames({
    schemaVersion: "edgeiq_three_day_catalog_lazy_v1",
    generatedAt: summary.generatedAt,
    dates: summary.days.map((day) => day.date),
    dayLabels: Object.fromEntries(summary.days.map((day) => [day.date, day.key])),
    meetings,
  });
}

export async function loadThreeDayCatalog(force = false): Promise<ThreeDayCatalog> {
  if (!force && cachedCatalog) return cachedCatalog;
  if (pendingCatalog) return pendingCatalog;

  pendingCatalog = buildLazyCatalog()
    .then((catalog) => {
      cachedCatalog = catalog;
      return catalog;
    })
    .finally(() => {
      pendingCatalog = null;
    });

  return pendingCatalog;
}
