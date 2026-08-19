export type CurrentRaceIntelligenceRunner = {
  runnerId?: string | number | null;
  runnerNumber?: string | number | null;
  runnerName?: string | null;
  scratched?: boolean | null;
  barrier?: string | number | null;
  market?: { value?: string | number | null; asAt?: string | null } | null;
  edgeiqPrice?: { value?: string | number | null; asAt?: string | null } | null;
  epi?: {
    value?: string | number | null;
    display?: string | null;
    status?: string | null;
    rankInRace?: string | number | null;
    activeFieldSize?: string | number | null;
    fieldAverage?: string | number | null;
    differenceFromFieldAverage?: string | number | null;
  } | null;
  earlySpeed?: { value?: string | number | null } | null;
  lateSpeed?: { value?: string | number | null } | null;
  suitability?: { value?: string | number | null; band?: string | null; publicReasons?: string[] | null } | null;
  formMomentum?: { value?: string | number | null; band?: string | null; publicReasons?: string[] | null } | null;
  raceShape?: { value?: string | number | null } | null;
  projectedMapZone?: string | null;
  publicReasons?: Record<string, string[] | null | undefined> | null;
};

export type CurrentRaceIntelligenceRace = {
  raceDate?: string | null;
  meeting?: string | null;
  raceNumber?: string | number | null;
  raceKey?: string | null;
  raceName?: string | null;
  distance?: string | number | null;
  class?: string | null;
  trackCondition?: string | null;
  rail?: string | null;
  weather?: string | null;
  tempo?: string | null;
  pressure?: string | null;
  mapCoverage?: { count?: number | null; average?: number | null; top?: number | null } | null;
  fieldSummary?: {
    epi?: { count?: number | null; average?: number | null; top?: number | null } | null;
    earlySpeed?: { count?: number | null; average?: number | null; top?: number | null } | null;
    lateSpeed?: { count?: number | null; average?: number | null; top?: number | null } | null;
    topEpi?: Array<{ runnerNumber?: string | number | null; runnerName?: string | null; value?: string | number | null }> | null;
  } | null;
  overview?: {
    statements?: Array<{ statement?: string | null; source?: string | null }> | null;
  } | null;
  runners?: CurrentRaceIntelligenceRunner[] | null;
};

type CurrentRaceIntelligencePayload = {
  schemaVersion?: string;
  generatedAt?: string;
  races?: CurrentRaceIntelligenceRace[];
};

const URL = "/data/edgeiq_current_race_intelligence_v1.json";
const MAX_RACES = 1000;
let cachedPayload: CurrentRaceIntelligencePayload | null = null;
let pendingPayload: Promise<CurrentRaceIntelligencePayload> | null = null;

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function raceKeyCandidates(raceKey: string | null | undefined): string[] {
  const text = usable(raceKey);
  if (!text) return [];
  const upper = text.toUpperCase();
  const candidates = [upper];
  const pipeMatch = upper.match(/^(\d{4}-\d{2}-\d{2})\|(.+)\|R?(\d+)$/);
  if (pipeMatch) candidates.push(`${pipeMatch[1]}|${pipeMatch[2]}|${pipeMatch[3]}`);
  const underscoreMatch = upper.match(/^(\d{4}-\d{2}-\d{2})_(.+)_R?(\d+)$/);
  if (underscoreMatch) {
    candidates.push(`${underscoreMatch[1]}|${underscoreMatch[2]}|${underscoreMatch[3]}`);
    candidates.push(`${underscoreMatch[1]}|${underscoreMatch[2]}|R${underscoreMatch[3]}`);
  }
  return [...new Set(candidates)];
}

function normaliseRaceKey(value: unknown): string {
  return usable(value).toUpperCase().replace(/_R(\d+)$/, "|R$1").replace(/_/g, "|");
}

export async function loadCurrentRaceIntelligenceFeed(force = false): Promise<CurrentRaceIntelligencePayload> {
  if (!force && cachedPayload) return cachedPayload;
  if (pendingPayload) return pendingPayload;
  pendingPayload = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Current race intelligence feed failed with ${response.status}`);
      const payload = (await response.json()) as CurrentRaceIntelligencePayload;
      if ((payload.races?.length ?? 0) > MAX_RACES) {
        console.warn("EDGEiQ rejected oversized current race intelligence feed", payload.races?.length);
        return { ...payload, races: [] };
      }
      return payload;
    })
    .then((payload) => {
      cachedPayload = payload;
      return payload;
    })
    .finally(() => {
      pendingPayload = null;
    });
  return pendingPayload;
}

export function findCurrentRaceIntelligenceRace(
  payload: CurrentRaceIntelligencePayload | null | undefined,
  raceKey: string | null | undefined,
): CurrentRaceIntelligenceRace | null {
  const candidates = raceKeyCandidates(raceKey);
  if (!payload?.races?.length || !candidates.length) return null;
  return payload.races.find((race) => candidates.includes(normaliseRaceKey(race.raceKey))) ?? null;
}
