import { edgeiqDataPath } from "../../../config/edgeiqDataOrigin";
import type { ThreeDayRace } from "./threeDayCatalog";

export type EnrichedSourceValue<T = number | string> = {
  value: T | null;
  source: string | null;
  version: string | null;
  asAt?: string | null;
  status?: string | null;
  missingReason?: string | null;
  publicReasons?: string[] | null;
};

export type EnrichedRecordSummary = {
  starts: number;
  wins: number;
  seconds: number;
  thirds: number;
  places: number;
  winPct?: number | null;
  placePct?: number | null;
  display: string;
};

export type EnrichedFormRun = {
  date: string | null;
  track: string | null;
  raceNumber: number | null;
  distance: number | null;
  condition: string | null;
  conditionFamily: string | null;
  class: string | null;
  position: string | number | null;
  fieldSize: number | null;
  positionInRunning?: string | null;
  barrier: number | null;
  weight: string | null;
  jockey: string | null;
  margin: string | null;
  startingPrice: string | null;
  performanceRating: number | null;
  raceRating?: EnrichedSourceValue<number>;
  historicalEpi?: EnrichedSourceValue<number>;
  sectionalIndices?: {
    index800To600?: EnrichedSourceValue<number>;
    index600To400?: EnrichedSourceValue<number>;
    index400To200?: EnrichedSourceValue<number>;
    index200ToFinish?: EnrichedSourceValue<number>;
    finishLen?: EnrichedSourceValue<number>;
    benchmarkMode?: string | null;
    signConvention?: string | null;
  } | null;
  benchmarkEvidence?: EnrichedSourceValue<number>;
  historicalEarlySpeed?: EnrichedSourceValue<number>;
  historicalLateSpeed?: EnrichedSourceValue<number>;
  historicalSpeedRating?: EnrichedSourceValue<number>;
  historicalSuitability?: EnrichedSourceValue<number>;
  historicalFormMomentum?: EnrichedSourceValue<number>;
  note: string | null;
};

export type EnrichedFormGuideRunner = {
  raceDate: string;
  meeting: string;
  raceNumber: number | null;
  raceKey: string;
  runnerId: string | null;
  runnerNumber: number | null;
  runnerName: string;
  normalisedRunnerName: string;
  lastRunDate: string | null;
  daysSinceLastRun: number | null;
  rating?: EnrichedSourceValue<number> | number | null;
  ratingSource?: string | null;
  epi: EnrichedSourceValue<number> | number | null;
  epiSource: string | null;
  marketPrice: EnrichedSourceValue<number> | number | null;
  marketSource: string | null;
  marketAsAt: string | null;
  edgeiqPrice: EnrichedSourceValue<number> | number | null;
  edgeiqPriceSource: string | null;
  earlySpeed?: EnrichedSourceValue<number> | number | null;
  earlySpeedSource?: string | null;
  suitability?: EnrichedSourceValue<number> | number | null;
  suitabilitySource?: string | null;
  raceShape?: EnrichedSourceValue<string | number> | string | number | null;
  raceShapeSource?: string | null;
  lateSpeed?: EnrichedSourceValue<number> | number | null;
  lateSpeedSource?: string | null;
  formMomentum?: EnrichedSourceValue<number> | number | null;
  formMomentumSource?: string | null;
  trackRecord: EnrichedRecordSummary | null;
  distanceRecord: EnrichedRecordSummary | null;
  conditionRecord: EnrichedRecordSummary | null;
  careerRecord?: EnrichedRecordSummary | null;
  trackDistanceRecord?: EnrichedRecordSummary | null;
  conditionProfile?: Array<EnrichedRecordSummary & { label: string }>;
  classProfile?: Array<EnrichedRecordSummary & { label: string }>;
  jockeyProfile?: {
    currentJockey: string | null;
    jockeyWithHorse: EnrichedRecordSummary | null;
    otherJockeys: EnrichedRecordSummary | null;
  };
  raceDayPattern?: Array<EnrichedRecordSummary & { label: string }>;
  preparationProfile?: Array<EnrichedRecordSummary & { label: string }>;
  lastStart?: EnrichedFormRun | null;
  fullForm: EnrichedFormRun[];
  lastFive: string[];
  joinMethod: "RUNNER_ID" | "STRICT_COMPOSITE" | "UNMATCHED" | "AMBIGUOUS";
  historySource: string | null;
  recordSource: string | null;
  firstStarter: boolean;
  scratched: boolean;
};

export type EnrichedRaceWeather = {
  raceDate: string;
  meeting: string;
  observedAt: string | null;
  forecastAt: string | null;
  condition: string | null;
  temperatureC: number | null;
  apparentTemperatureC: number | null;
  windSpeedKmh: number | null;
  windGustKmh: number | null;
  windDirection: string | null;
  rainfall24hMm: number | null;
  rainfall7dMm: number | null;
  irrigation24hMm: number | null;
  irrigation7dMm: number | null;
  trackCondition: string | null;
  rail: string | null;
  weatherSource: string;
  weatherVersion: string;
  asAt?: string | null;
};

export type EnrichedFormGuideRace = {
  raceDate: string;
  meeting: string;
  raceNumber: number | null;
  raceKey: string;
  weather?: EnrichedRaceWeather | null;
  tempo?: string | null;
  pressure?: string | null;
  benchmarkContext?: Record<string, unknown> | null;
  runners: EnrichedFormGuideRunner[];
};

export type EnrichedFormGuideFeed = {
  schemaVersion: string;
  generatedAt: string;
  sourceContract: Record<string, string | string[]>;
  races: EnrichedFormGuideRace[];
};

const URL = edgeiqDataPath("/data/edgeiq_form_guide_enriched_v2.json");

let cachedFeed: EnrichedFormGuideFeed | null = null;
let pendingFeed: Promise<EnrichedFormGuideFeed> | null = null;

function normaliseTrack(value: unknown): string {
  return String(value ?? "")
    .toUpperCase()
    .replace(/\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b/g, " ")
    .replace(/\b(RACECOURSE|RACING|TRACK)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, "");
}

function normaliseRaceNumber(value: unknown): string {
  const match = String(value ?? "").match(/\d+/);
  return match?.[0] ?? "";
}

function raceKeyFromParts(date: unknown, meeting: unknown, raceNumber: unknown): string {
  return [
    String(date ?? "").trim(),
    normaliseTrack(meeting),
    normaliseRaceNumber(raceNumber),
  ].join("|");
}

function raceKeyCandidatesFromParts(date: unknown, meeting: unknown, raceNumber: unknown): string[] {
  const normalizedDate = String(date ?? "").trim();
  const normalizedMeeting = normaliseTrack(meeting);
  const normalizedRaceNumber = normaliseRaceNumber(raceNumber);
  if (!normalizedDate || !normalizedMeeting || !normalizedRaceNumber) return [];

  const candidates = new Set<string>([
    `${normalizedDate}|${normalizedMeeting}|${normalizedRaceNumber}`,
    `${normalizedDate}|${normalizedMeeting}|R${normalizedRaceNumber}`,
  ]);

  const venueAliases = [
    normalizedMeeting.replace(/(HILLSIDE|LAKESIDE)$/g, ""),
  ].filter(Boolean);
  venueAliases.forEach((venue) => {
    candidates.add(`${normalizedDate}|${venue}|${normalizedRaceNumber}`);
    candidates.add(`${normalizedDate}|${venue}|R${normalizedRaceNumber}`);
  });

  return [...candidates];
}

function raceKeyCandidatesFromKey(value: unknown): string[] {
  const text = String(value ?? "").trim().toUpperCase();
  if (!text) return [];
  const parts = text.replace(/_/g, "|").split("|");
  if (parts.length < 3) return [text];
  return raceKeyCandidatesFromParts(parts[0], parts[1], parts[2]);
}

export async function loadFormGuideEnrichedFeed(force = false): Promise<EnrichedFormGuideFeed> {
  if (!force && cachedFeed) return cachedFeed;
  if (pendingFeed) return pendingFeed;

  pendingFeed = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, {
    cache: "no-store",
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Form Guide enrichment failed with ${response.status}`);
      }

      return (await response.json()) as EnrichedFormGuideFeed;
    })
    .then((feed) => {
      cachedFeed = feed;
      return feed;
    })
    .finally(() => {
      pendingFeed = null;
    });

  return pendingFeed;
}

export function findEnrichedFormGuideRace(
  feed: EnrichedFormGuideFeed | null,
  raceBook: any,
  meetingRaces: ThreeDayRace[] = [],
  selectedRaceKey?: string | null,
): EnrichedFormGuideRace | null {
  if (!feed) return null;

  const official = raceBook?.official ?? {};
  const explicitRaceKeys = [
    selectedRaceKey,
    official.raceKey,
  ].flatMap(raceKeyCandidatesFromKey);
  const activeRaceByKey = meetingRaces.find((race) => {
    const candidates = raceKeyCandidatesFromKey(race.raceKey);
    return candidates.some((candidate) => explicitRaceKeys.includes(candidate));
  });
  const activeRace =
    activeRaceByKey ??
    meetingRaces.find((race) => normaliseRaceNumber(race.raceNumber) === normaliseRaceNumber(official.raceNumber));
  const meeting = official.meeting ?? activeRace?.source?.meeting ?? activeRace?.source?.venue ?? activeRace?.source?.track;
  const date = official.date ?? official.meetingDate ?? activeRace?.source?.date;
  const raceNumber = official.raceNumber ?? activeRace?.raceNumber;
  const lookupKeys = [
    ...explicitRaceKeys,
    ...raceKeyCandidatesFromKey(activeRace?.raceKey),
    ...raceKeyCandidatesFromParts(date, meeting, raceNumber),
    raceKeyFromParts(date, meeting, raceNumber),
  ].filter(Boolean);

  return (
    feed.races.find((race) => lookupKeys.includes(String(race.raceKey).toUpperCase())) ??
    feed.races.find((race) => raceKeyCandidatesFromParts(race.raceDate, race.meeting, race.raceNumber).some((key) => lookupKeys.includes(key))) ??
    null
  );
}
