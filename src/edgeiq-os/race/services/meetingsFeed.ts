import { edgeiqDataPath } from "../../../config/edgeiqDataOrigin";
import type { ThreeDayMeeting, ThreeDayRace } from "./threeDayCatalog";

export type MeetingsDayKey = "TODAY" | "TOMORROW" | "DAY_PLUS_2";

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

type SummaryRace = Omit<MeetingRaceSummaryViewModel, "label" | "rawRace">;
type SummaryMeeting = Omit<MeetingSummaryViewModel, "notes" | "raceSummaries" | "rawMeeting"> & {
  providerMeetingKey?: string;
  date: string;
  raceSummaries: SummaryRace[];
};
type SummaryDay = {
  key: MeetingsDayKey;
  date: string;
  generatedAt: string;
  totals: MeetingsDayViewModel["totals"];
  meetings: SummaryMeeting[];
};
type SummaryFeed = {
  schemaVersion: string;
  timezone: string;
  generatedAt: string;
  days: SummaryDay[];
};
type MeetingDetailFeed = {
  schemaVersion: string;
  generatedAt: string;
  date: string;
  meetingKey: string;
  meeting: ThreeDayMeeting;
};

const SUMMARY_URL = edgeiqDataPath("/data/edgeiq_meetings_summary_feed_v1.json");
const MAX_SUMMARY_BYTES = 1_000_000;
const MAX_MEETING_DETAIL_BYTES = 8_000_000;
let cachedViewModel: MeetingsWorkspaceViewModel | null = null;
let pendingViewModel: Promise<MeetingsWorkspaceViewModel> | null = null;
const meetingDetailCache = new Map<string, ThreeDayMeeting>();
const meetingDetailPending = new Map<string, Promise<ThreeDayMeeting>>();

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

function formatGeneratedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value || "Not supplied";
  return new Intl.DateTimeFormat("en-AU", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Melbourne",
  }).format(parsed).replace(/\s/g, "").toLowerCase();
}

function dateLabel(key: MeetingsDayKey): "TODAY" | "TOMORROW" | "DAY +2" {
  return key === "DAY_PLUS_2" ? "DAY +2" : key;
}

function notes(meeting: SummaryMeeting): MeetingEvidenceItem[] {
  return [
    { label: "Today's Track", value: meeting.track, authority: meeting.track === "Not supplied" ? "unavailable" : "official" },
    { label: "Rail", value: meeting.rail, authority: meeting.rail === "Not supplied" ? "unavailable" : "official" },
    { label: "Weather", value: meeting.weather, authority: meeting.weather === "Awaiting Weather Feed" ? "unavailable" : "governed" },
    { label: "Wind", value: meeting.wind, authority: meeting.wind === "Not supplied" ? "unavailable" : "governed" },
    { label: "Official Update", value: meeting.officialUpdate, authority: meeting.officialUpdate === "Not supplied" ? "unavailable" : "official" },
  ];
}

function rawRaceFromSummary(race: SummaryRace): ThreeDayRace {
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
    source: { lightweightSummary: true },
  };
}

function meetingFromSummary(meeting: SummaryMeeting): MeetingSummaryViewModel {
  const raceSummaries = meeting.raceSummaries.map((race) => ({
    ...race,
    label: `R${race.raceNumber}`,
    rawRace: rawRaceFromSummary(race),
  }));
  const rawMeeting: ThreeDayMeeting = {
    meetingKey: meeting.meetingKey,
    meeting: meeting.meeting,
    providerMeetingKey: meeting.providerMeetingKey ?? "",
    date: meeting.date,
    trackCondition: meeting.track === "Not supplied" ? null : meeting.track,
    rail: meeting.rail === "Not supplied" ? null : meeting.rail,
    raceCount: meeting.races,
    races: raceSummaries.map((race) => race.rawRace),
    source: { State: meeting.state, lightweightSummary: true },
  };
  return { ...meeting, notes: notes(meeting), raceSummaries, rawMeeting };
}

function buildViewModel(feed: SummaryFeed): MeetingsWorkspaceViewModel {
  return {
    workspaceId: "BETA-002",
    status: "READY",
    generatedAt: feed.generatedAt,
    generatedAtDisplay: formatGeneratedAt(feed.generatedAt),
    days: feed.days.map((day) => ({
      key: day.key,
      label: dateLabel(day.key),
      date: day.date,
      displayDate: formatWindowDate(day.date),
      generatedAt: day.generatedAt || feed.generatedAt,
      totals: day.totals,
      meetings: day.meetings.map(meetingFromSummary),
    })),
  };
}

async function fetchSummary(force: boolean): Promise<SummaryFeed> {
  const response = await fetch(`${SUMMARY_URL}?updated=${encodeURIComponent(String(Date.now()))}`, {
    cache: force ? "reload" : "no-store",
  });
  if (!response.ok) throw new Error(`Meetings summary failed with ${response.status}`);
  const text = await response.text();
  if (text.length > MAX_SUMMARY_BYTES) throw new Error(`Meetings summary exceeds ${MAX_SUMMARY_BYTES} bytes`);
  const payload = JSON.parse(text) as SummaryFeed;
  if (!Array.isArray(payload.days)) throw new Error("Meetings summary is invalid");
  return payload;
}

function detailSlug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "meeting";
}

export async function loadMeetingDetail(date: string, meetingKey: string, force = false): Promise<ThreeDayMeeting> {
  const cacheKey = `${date}|${meetingKey}`;
  if (!force && meetingDetailCache.has(cacheKey)) return meetingDetailCache.get(cacheKey)!;
  if (meetingDetailPending.has(cacheKey)) return meetingDetailPending.get(cacheKey)!;

  const url = edgeiqDataPath(`/data/meetings/${date}_${detailSlug(meetingKey)}.json`);
  const pending = fetch(`${url}?updated=${encodeURIComponent(String(Date.now()))}`, {
    cache: force ? "reload" : "no-store",
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Meeting detail failed with ${response.status}`);
      const text = await response.text();
      if (text.length > MAX_MEETING_DETAIL_BYTES) throw new Error(`Meeting detail exceeds ${MAX_MEETING_DETAIL_BYTES} bytes`);
      const payload = JSON.parse(text) as MeetingDetailFeed;
      if (!payload.meeting || payload.meeting.meetingKey !== meetingKey) throw new Error("Meeting detail is invalid");
      meetingDetailCache.set(cacheKey, payload.meeting);
      return payload.meeting;
    })
    .finally(() => {
      meetingDetailPending.delete(cacheKey);
    });

  meetingDetailPending.set(cacheKey, pending);
  return pending;
}

export async function loadMeetingsWorkspaceViewModel(force = false): Promise<MeetingsWorkspaceViewModel> {
  if (!force && cachedViewModel) return cachedViewModel;
  if (pendingViewModel) return pendingViewModel;
  pendingViewModel = fetchSummary(force)
    .then(buildViewModel)
    .then((model) => {
      cachedViewModel = model;
      return model;
    })
    .finally(() => {
      pendingViewModel = null;
    });
  return pendingViewModel;
}
