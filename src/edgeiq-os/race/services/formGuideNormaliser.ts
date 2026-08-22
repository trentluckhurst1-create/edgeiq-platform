import type { ThreeDayRace, ThreeDayRunner } from "./threeDayCatalog";
import type {
  EnrichedFormGuideRace,
  EnrichedFormGuideRunner,
  EnrichedFormRun,
  EnrichedRecordSummary,
  EnrichedSourceValue,
} from "./formGuideEnrichedFeed";

export type FormGuideProfileLine = {
  label: string;
  record: string;
  starts: string;
  wins: string;
  seconds: string;
  thirds: string;
  winPct: string;
  placePct: string;
  matchesToday: boolean;
  source: string;
};

export type FormGuideRecentRun = {
  date: string;
  track: string;
  distance: string;
  condition: string;
  position: string;
  fieldSize: string;
  positionInRunning: string;
  raceClass: string;
  margin: string;
  weight: string;
  jockey: string;
  barrier: string;
  sp: string;
  eri: string;
  epi: string;
  esi800600: string;
  esi600400: string;
  esi400200: string;
  esi200F: string;
  source: string;
};

export type FormGuideLastStart = {
  date: string;
  daysAgo: string;
  track: string;
  distance: string;
  position: string;
  fieldSize: string;
  barrier: string;
  condition: string;
  weight: string;
  jockey: string;
  startingPrice: string;
  margin: string;
};

export type FormGuideRunnerDisplay = {
  id: string;
  sourceIndex: number;
  no: string;
  sortNo: number;
  silkUrl: string;
  lastFive: string[];
  horse: string;
  age: string;
  sex: string;
  breeding: string;
  trainer: string;
  jockey: string;
  weight: string;
  barrier: string;
  effectiveBarrier: string;
  daysSinceLastRun: string;
  rating: string;
  epi: string;
  epiRank: string;
  epiFieldAverage: string;
  epiDifference: string;
  earlySpeed: string;
  earlySpeedLabel: string;
  marketPrice: string;
  edgeiqPrice: string;
  suitabilityScore: string;
  suitabilityLabel: string;
  shapeFit: string;
  late: string;
  formMomentum: string;
  formMomentumDirection: "" | "up" | "down";
  scratched: boolean;
  country: string;
  gear: string;
  careerProfile: FormGuideProfileLine[];
  conditionProfile: FormGuideProfileLine[];
  classProfile: FormGuideProfileLine[];
  jockeyProfile: FormGuideProfileLine[];
  raceDayPattern: FormGuideProfileLine[];
  lastStart: FormGuideLastStart | null;
  insights: FormGuideInsightGroup[];
  governedStatements: string[];
  recentRuns: FormGuideRecentRun[];
};

export type FormGuideInsightItem = {
  text: string;
  tone: "POSITIVE" | "RISK" | "NEUTRAL";
  source: string;
};

export type FormGuideInsightGroup = {
  key: string;
  title: string;
  items: FormGuideInsightItem[];
};

export type FormGuideRaceDisplay = {
  meeting: string;
  date: string;
  raceNumber: string;
  raceName: string;
  primaryLine: string;
  metadata: Array<{ label: string; value: string }>;
  runners: FormGuideRunnerDisplay[];
  activeFieldEpi: {
    validRunnerCount: number;
    fieldAverage: number | null;
  };
  fieldSummary: string;
};

const EMPTY = "";
const NON_START_TOKENS = new Set(["", "-", "X", "NULL", "NONE", "N/A", "NA", "0"]);
const RESULT_CODES = new Set(["DNF", "F", "UR", "PU", "L", "BD"]);
const ENGINE_LABELS: Record<string, string> = {
  MAP_ADVANTAGE: "Map advantage",
  SHORT_BURST_SPRINT: "Expected to sprint from the 400m",
  FORWARD_PRESSURE: "Forward pressure",
  FIRST_START: "First starter",
  FIRST_STARTER: "First starter",
  NO_SECTIONAL_COVERAGE: "No sectional coverage",
  HISTORICAL_ONLY: "Historical evidence only",
  NO_SOURCE_ROW: "Source row unavailable",
  STALE_DATE: "Date requires review",
};

export function humaniseEngineLabel(value: unknown): string {
  const text = safeText(value);
  if (!text) return "";
  const key = text.trim().toUpperCase();
  if (ENGINE_LABELS[key]) return ENGINE_LABELS[key];
  if (!key.includes("_")) return text;
  return key
    .toLowerCase()
    .split("_")
    .filter(Boolean)
    .map((part, index) => (index === 0 ? part.charAt(0).toUpperCase() + part.slice(1) : part))
    .join(" ");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function parseMaybeStructured(value: unknown): unknown {
  if (isRecord(value) || Array.isArray(value)) return value;
  if (typeof value !== "string") return value;
  const text = value.trim();
  if (!text || !"[{".includes(text[0])) return value;

  try {
    return JSON.parse(text);
  } catch {
    return value;
  }
}

function firstValue(source: unknown, keys: string[]): unknown {
  const parsed = parseMaybeStructured(source);
  if (!isRecord(parsed)) return undefined;
  const lowerKeyMap = new Map<string, string>();
  Object.keys(parsed).forEach((key) => lowerKeyMap.set(key.toLowerCase(), key));

  for (const key of keys) {
    const actual = Object.prototype.hasOwnProperty.call(parsed, key)
      ? key
      : lowerKeyMap.get(key.toLowerCase());
    if (!actual) continue;
    const value = parsed[actual];
    if (value === null || value === undefined || value === "") continue;
    return value;
  }

  return undefined;
}

function isSourceValue(value: unknown): value is EnrichedSourceValue {
  return isRecord(value) && Object.prototype.hasOwnProperty.call(value, "value");
}

function unwrapSourceValue(value: unknown): unknown {
  return isSourceValue(value) ? value.value : value;
}

function safeText(value: unknown): string {
  const unwrapped = unwrapSourceValue(value);
  const parsed = parseMaybeStructured(unwrapped);
  if (isRecord(parsed) || Array.isArray(parsed)) return "";
  if (parsed === null || parsed === undefined) return "";
  const text = String(parsed).replace(/\s+/g, " ").trim();
  if (!text || ["-", "none", "null", "n/a", "na"].includes(text.toLowerCase())) return "";
  if (text.includes("[object Object]")) return "";
  if ((text.startsWith("{") && text.endsWith("}")) || (text.startsWith("[") && text.endsWith("]"))) return "";
  return text;
}

function numericValue(value: unknown): number | null {
  const text = safeText(unwrapSourceValue(value)).replace(/[$,]/g, "");
  if (!text) return null;
  const parsed = Number(text);
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 1000) return null;
  return parsed;
}

function metricNumber(value: unknown): number | null {
  const text = safeText(unwrapSourceValue(value)).replace(/[$,]/g, "");
  if (!text) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) && Math.abs(parsed) < 10000 ? parsed : null;
}

function metricText(value: unknown, decimals?: number): string {
  const parsed = metricNumber(value);
  if (parsed !== null) {
    return decimals === undefined ? String(Number(parsed.toFixed(2))) : parsed.toFixed(decimals);
  }
  return safeText(unwrapSourceValue(value));
}

function signedMetricText(value: unknown, decimals = 1): string {
  const parsed = metricNumber(value);
  if (parsed === null) return safeText(unwrapSourceValue(value));
  const fixed = parsed.toFixed(decimals);
  return parsed > 0 ? `+${fixed}` : fixed;
}

export function formatPrice(value: unknown): string {
  const price = numericValue(value);
  if (price === null) return "";
  return `$${price.toFixed(2)}`;
}

function textFrom(source: unknown, keys: string[]): string {
  const direct = safeText(source);
  if (direct) return direct;
  const nested = firstValue(source, keys);
  if (nested === source) return "";
  return safeText(nested);
}

function publicReasonsFrom(source: unknown): string[] {
  const parsed = parseMaybeStructured(source);
  if (!isRecord(parsed)) return [];
  const reasons = parsed.publicReasons;
  if (!Array.isArray(reasons)) return [];
  return reasons.map((reason) => safeText(reason)).filter(Boolean);
}

function normaliseRunnerName(value: unknown): string {
  return safeText(value)
    .toUpperCase()
    .replace(/\s*\([A-Z]{2,3}\)\s*$/, "")
    .replace(/['']/g, "")
    .replace(/&/g, "AND")
    .replace(/[^A-Z0-9]+/g, "");
}

function normaliseRunnerId(value: unknown): string {
  return safeText(value).replace(/[^a-z0-9_-]+/gi, "");
}

function lastFiveFrom(value: unknown): string[] {
  const parsed = parseMaybeStructured(value);
  const rawTokens = Array.isArray(parsed)
    ? parsed
    : typeof parsed === "string"
      ? parsed.split(/[\s,]+/)
      : [];
  const output: string[] = [];

  for (const token of rawTokens) {
    const text = safeText(token).toUpperCase();
    if (!text || NON_START_TOKENS.has(text)) continue;
    if (/^\d{1,2}$/.test(text) || RESULT_CODES.has(text)) output.push(text);
    if (output.length >= 5) break;
  }

  return output;
}

function runnerLastFive(runner: ThreeDayRunner): string[] {
  const official = runner.official ?? {};
  const source = runner.source ?? {};
  const horse = firstValue(source, ["horse"]);
  const candidates = [
    lastFiveFrom(firstValue(official, ["lastFive", "last5", "last_five"])),
    lastFiveFrom(firstValue(source, ["lastFive", "last5", "last_five", "form"])),
    lastFiveFrom(firstValue(horse, ["lastFive", "last5", "last_five", "form"])),
  ];

  return (candidates.find((items) => items.length > 0) ?? []).slice(0, 5);
}

function enrichedRunnerFor(
  enrichedRace: EnrichedFormGuideRace | null | undefined,
  runner: ThreeDayRunner,
  no: string,
  name: string,
): EnrichedFormGuideRunner | undefined {
  if (!enrichedRace) return undefined;
  const official = runner.official ?? {};
  const source = (runner.source ?? {}) as Record<string, unknown>;
  const runnerId = normaliseRunnerId(firstValue(source, ["horseCode", "id", "runnerId", "runner_id"]));
  const runnerNameKey = normaliseRunnerName(name);
  const runnerNo = Number(no);

  if (runnerId) {
    const idMatch = enrichedRace.runners.find((item) => normaliseRunnerId(item.runnerId) === runnerId);
    if (idMatch) return idMatch;
  }

  return enrichedRace.runners.find((item) => {
    const sameNo = Number(item.runnerNumber) === runnerNo || Number(official.no) === Number(item.runnerNumber);
    return sameNo && normaliseRunnerName(item.runnerName) === runnerNameKey;
  });
}

function formatRecordSummary(value: EnrichedRecordSummary | null | undefined): string {
  if (!value) return "";
  if (value.display) return value.display;
  if (!value.starts) return "";
  return `${value.starts}:${value.wins || 0}-${value.seconds || 0}-${value.thirds || 0}`;
}

function pct(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return `${n.toFixed(n % 1 === 0 ? 0 : 1)}%`;
}

function profileLine(
  label: string,
  value: EnrichedRecordSummary | null | undefined,
  matchesToday = false,
  source = "edgeiq_form_guide_enriched_v2",
): FormGuideProfileLine {
  return {
    label,
    record: formatRecordSummary(value),
    starts: value?.starts ? String(value.starts) : "",
    wins: value?.wins !== undefined ? String(value.wins) : "",
    seconds: value?.seconds !== undefined ? String(value.seconds) : "",
    thirds: value?.thirds !== undefined ? String(value.thirds) : "",
    winPct: pct(value?.winPct),
    placePct: pct(value?.placePct),
    matchesToday: Boolean(matchesToday && value && value.starts > 0),
    source,
  };
}

function normaliseToken(value: unknown): string {
  return safeText(value)
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "");
}

function conditionFamily(value: unknown): string {
  const text = safeText(value).toUpperCase();
  if (text.includes("HEAVY")) return "HEAVY";
  if (text.includes("SOFT")) return "SOFT";
  if (text.includes("GOOD")) return "GOOD";
  if (text.includes("FIRM")) return "FIRM";
  if (text.includes("SYNTH")) return "SYNTHETIC";
  return normaliseToken(value);
}

function distanceMetres(value: unknown): number | null {
  const match = safeText(value).replace(/,/g, "").match(/\d{3,4}/);
  if (!match) return null;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
}

function classToken(value: unknown): string {
  return normaliseToken(value).replace(/^BENCHMARK/, "BM");
}

function profileRows(
  rows: Array<(EnrichedRecordSummary & { label: string })> | undefined,
  matchesToday: (label: string) => boolean = () => false,
): FormGuideProfileLine[] {
  return (rows ?? []).map((row) => profileLine(row.label, row, matchesToday(row.label)));
}

function formatPosition(position: unknown, fieldSize: unknown): string {
  const pos = safeText(position);
  if (!pos) return "";
  const field = Number(fieldSize);
  if (!Number.isFinite(field) || field <= 0) return pos;
  const n = Number(pos);
  const suffix =
    n % 10 === 1 && n % 100 !== 11
      ? "st"
      : n % 10 === 2 && n % 100 !== 12
        ? "nd"
        : n % 10 === 3 && n % 100 !== 13
          ? "rd"
          : "th";
  return Number.isFinite(n) ? `${n}/${field}` : `${pos}/${field}`;
}

function recentRunsFromEnriched(enriched: EnrichedFormGuideRunner | undefined): FormGuideRecentRun[] {
  if (!enriched?.fullForm?.length) return [];

  return enriched.fullForm.slice(0, 8).map((run) => {
    const runRecord = run as EnrichedFormRun & Record<string, unknown>;
    return {
    date: safeText(run.date),
    track: safeText(run.track),
    distance: run.distance ? `${run.distance}m` : "",
    condition: safeText(run.condition),
    position: formatPosition(run.position, run.fieldSize),
    fieldSize: safeText(run.fieldSize),
    positionInRunning: safeText(firstValue(runRecord, ["positionInRunning", "position_in_running", "inRunning", "in_running", "settlingPosition", "settling_position"])),
    raceClass: safeText(run.class),
    margin: safeText(run.margin),
    weight: safeText(run.weight),
    jockey: safeText(run.jockey),
    barrier: safeText(run.barrier),
    sp: safeText(run.startingPrice),
    eri: metricText(run.raceRating, 1),
    epi: metricText(run.historicalEpi ?? run.performanceRating, 1),
    esi800600: signedMetricText(run.sectionalIndices?.index800To600, 1),
    esi600400: signedMetricText(run.sectionalIndices?.index600To400, 1),
    esi400200: signedMetricText(run.sectionalIndices?.index400To200, 1),
    esi200F: signedMetricText(run.sectionalIndices?.index200ToFinish, 1),
    source: run.sectionalIndices ? "edgeiq_standardised_sectionals" : "edgeiq_form_guide_enriched_v2",
  };
  });
}

function lastStartFromRun(run: EnrichedFormRun | null | undefined, daysSinceLastRun: string): FormGuideLastStart | null {
  if (!run) return null;
  return {
    date: safeText(run.date),
    daysAgo: daysSinceLastRun,
    track: safeText(run.track),
    distance: run.distance ? `${run.distance}m` : "",
    position: formatPosition(run.position, run.fieldSize),
    fieldSize: safeText(run.fieldSize),
    barrier: safeText(run.barrier),
    condition: safeText(run.condition),
    weight: safeText(run.weight),
    jockey: safeText(run.jockey),
    startingPrice: safeText(run.startingPrice),
    margin: safeText(run.margin),
  };
}

function formatJockey(source: Record<string, unknown>, official: ThreeDayRunner["official"]): string {
  const jockey = safeText(official?.jockey) || safeText(firstValue(source, ["jockeyName", "jockey"]));
  const claim = safeText(firstValue(official, ["apprenticeClaim"])) || safeText(firstValue(source, ["apprenticeAllowedClaim", "claim", "claimKg"]));
  if (!jockey) return "";
  if (!claim || Number(claim) <= 0) return jockey;
  return `${jockey} (${claim}kg)`;
}

function runnerName(runner: ThreeDayRunner): string {
  const official = runner.official ?? {};
  const source = runner.source ?? {};

  return (
    safeText(official.runner) ||
    safeText(firstValue(source, ["horseName", "runnerName", "runner", "name"])) ||
    textFrom(firstValue(source, ["horse"]), ["horseName", "runnerName", "name", "fullName"]) ||
    "Unnamed runner"
  );
}

function runnerNo(runner: ThreeDayRunner, index: number): string {
  const official = runner.official ?? {};
  const source = runner.source ?? {};

  return (
    safeText(official.no) ||
    safeText(official.number) ||
    safeText(firstValue(source, ["raceEntryNumber", "runnerNumber", "saddlecloth", "number"])) ||
    String(index + 1)
  );
}

function metadataItem(label: string, value: unknown): { label: string; value: string } | null {
  const text = safeText(value);
  return text ? { label, value: text } : null;
}

function formatDateLong(value: unknown): string {
  const text = safeText(value);
  if (!text) return "";
  const date = new Date(`${text}T00:00:00`);
  if (Number.isNaN(date.getTime())) return text;
  return new Intl.DateTimeFormat("en-AU", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(date);
}

function buildInsights(runner: FormGuideRunnerDisplay): FormGuideInsightGroup[] {
  const groups: FormGuideInsightGroup[] = [];
  const career = runner.careerProfile.find((item) => item.label === "Career");
  const track = runner.careerProfile.find((item) => item.label === "Track");
  const distance = runner.careerProfile.find((item) => item.label === "Distance");
  const condition = runner.conditionProfile.find((item) => item.matchesToday);
  const classMatch = runner.classProfile.find((item) => item.matchesToday);
  const positiveItems: FormGuideInsightItem[] = [];
  const patternItems: FormGuideInsightItem[] = [];
  const valueItems: FormGuideInsightItem[] = [];

  if (track?.record) positiveItems.push({ text: `Track record: ${track.record}.`, tone: "NEUTRAL", source: track.source });
  if (distance?.record) positiveItems.push({ text: `Distance record: ${distance.record}.`, tone: "NEUTRAL", source: distance.source });
  if (condition?.record) positiveItems.push({ text: `${condition.label} going record: ${condition.record}.`, tone: "NEUTRAL", source: condition.source });
  if (classMatch?.record) positiveItems.push({ text: `Class profile: ${classMatch.record}.`, tone: "NEUTRAL", source: classMatch.source });
  if (runner.daysSinceLastRun) patternItems.push({ text: `${runner.daysSinceLastRun} days since latest official run.`, tone: "NEUTRAL", source: "edgeiq_form_guide_enriched_v2" });
  if (career?.record) patternItems.push({ text: `Career profile: ${career.record}.`, tone: "NEUTRAL", source: career.source });
  if (runner.marketPrice) valueItems.push({ text: `Current market visible at ${runner.marketPrice}.`, tone: "NEUTRAL", source: "edgeiq_form_guide_enriched_v2" });
  if (runner.edgeiqPrice) valueItems.push({ text: `EDGEiQ assessed price: ${runner.edgeiqPrice}.`, tone: "NEUTRAL", source: "edgeiq_form_guide_enriched_v2" });

  if (positiveItems.length) groups.push({ key: "positive-evidence", title: "Positive Evidence", items: positiveItems.slice(0, 4) });
  if (patternItems.length) groups.push({ key: "pattern-notes", title: "Pattern Notes", items: patternItems.slice(0, 3) });
  if (valueItems.length) groups.push({ key: "value-assessment", title: "Value Assessment", items: valueItems.slice(0, 3) });

  return groups;
}

export function normaliseFormGuideRace(
  raceBook: any,
  field: ThreeDayRunner[],
  meetingRaces: ThreeDayRace[] = [],
  enrichedRace?: EnrichedFormGuideRace | null,
): FormGuideRaceDisplay {
  const official = raceBook?.official ?? {};
  const activeRace = meetingRaces.find((race) => String(race.raceKey) === String(official.raceKey));
  const raceSource = activeRace?.source ?? {};
  const meeting = safeText(official.meeting) || safeText(raceSource.meeting) || "Meeting";
  const date = safeText(official.date) || safeText(official.meetingDate) || safeText(raceSource.date);
  const raceNumber = safeText(official.raceNumber) || safeText(activeRace?.raceNumber);
  const raceName = safeText(official.raceName) || safeText(activeRace?.raceName) || `Race ${raceNumber}`;
  const longDate = formatDateLong(date);
  const todayDistance = distanceMetres(official.distance ?? activeRace?.distance);
  const todayCondition = conditionFamily(official.trackCondition ?? activeRace?.trackCondition ?? firstValue(raceSource, ["condition", "conditions"]));
  const todayClass = classToken(official.raceClass ?? activeRace?.raceClass);

  const metadata = [
    metadataItem("Local Time", official.raceTime ?? official.officialRaceTime ?? activeRace?.raceTime ?? "Pending result"),
    metadataItem("Distance", official.distance ?? activeRace?.distance),
    metadataItem("Class", official.raceClass ?? activeRace?.raceClass),
    metadataItem("Age", firstValue(raceSource, ["age", "ageRestriction", "raceAge"])),
    metadataItem("Conditions", firstValue(raceSource, ["condition", "conditions"])),
    metadataItem("Runners", safeText(official.fieldSize) || (field.length ? `${field.length}` : "")),
    metadataItem("Track", official.trackCondition ?? activeRace?.trackCondition),
    metadataItem("Rail", official.rail ?? activeRace?.rail),
    metadataItem("Weather", enrichedRace?.weather?.trackCondition ?? enrichedRace?.weather?.condition),
    metadataItem("Temp", enrichedRace?.weather?.temperatureC === null || enrichedRace?.weather?.temperatureC === undefined ? "" : `${enrichedRace.weather.temperatureC.toFixed(1)}C`),
    metadataItem("Wind", [enrichedRace?.weather?.windDirection, enrichedRace?.weather?.windSpeedKmh === null || enrichedRace?.weather?.windSpeedKmh === undefined ? "" : `${enrichedRace.weather.windSpeedKmh.toFixed(1)} km/h`].filter(Boolean).join(" ")),
    metadataItem("Rain 24h", enrichedRace?.weather?.rainfall24hMm === null || enrichedRace?.weather?.rainfall24hMm === undefined ? "" : `${enrichedRace.weather.rainfall24hMm.toFixed(1)}mm`),
    metadataItem("Updated", enrichedRace?.weather?.observedAt ?? enrichedRace?.weather?.asAt),
    metadataItem("Prize Money", firstValue(raceSource, ["prizeMoney", "prizemoney", "totalPrizeMoney"])),
  ].filter((item): item is { label: string; value: string } => Boolean(item));

  const runners = field
    .map((runner, index) => {
      const officialRunner = runner.official ?? {};
      const source = (runner.source ?? {}) as Record<string, unknown>;
      const no = runnerNo(runner, index);
      const name = runnerName(runner);
      const enriched = enrichedRunnerFor(enrichedRace, runner, no, name);
      const country = safeText(firstValue(officialRunner, ["horseCountry"])) || safeText(firstValue(source, ["horseCountry", "country"]));
      const scratched =
        ["TRUE", "Y", "YES", "1"].includes(safeText(firstValue(officialRunner, ["scratched"])).toUpperCase()) ||
        ["TRUE", "Y", "YES", "1"].includes(safeText(firstValue(source, ["scratched"])).toUpperCase()) ||
        Boolean(enriched?.scratched);
      const marketPrice = scratched ? "" : formatPrice(enriched?.marketPrice);
      const daysSinceLastRun =
        enriched?.daysSinceLastRun === null || enriched?.daysSinceLastRun === undefined
          ? ""
          : String(enriched.daysSinceLastRun);
      const careerProfile = [
        profileLine("Career", enriched?.careerRecord ?? null),
        profileLine("Track", enriched?.trackRecord ?? null, Boolean(enriched?.trackRecord?.starts)),
        profileLine("Distance", enriched?.distanceRecord ?? null, Boolean(enriched?.distanceRecord?.starts && todayDistance)),
        profileLine("Track/Dist", enriched?.trackDistanceRecord ?? null, Boolean(enriched?.trackDistanceRecord?.starts && todayDistance)),
      ];
      const jockeyProfile = [
        profileLine(enriched?.jockeyProfile?.currentJockey ? "Current Jockey" : "Jockey", enriched?.jockeyProfile?.jockeyWithHorse ?? null),
        profileLine("Other Jockeys", enriched?.jockeyProfile?.otherJockeys ?? null),
      ];
      const recentRuns = recentRunsFromEnriched(enriched);
      const governedStatements = [
        ...publicReasonsFrom(enriched?.raceShape),
        ...publicReasonsFrom(enriched?.suitability),
        ...publicReasonsFrom(enriched?.formMomentum),
      ];

      const display: FormGuideRunnerDisplay = {
        id: safeText(enriched?.runnerId) || `race-${raceNumber || "race"}-runner-${no || index + 1}`,
        sourceIndex: index,
        no,
        sortNo: Number(no) || index + 1,
        silkUrl: safeText(firstValue(officialRunner, ["silkUrl"])) || safeText(firstValue(source, ["silkUrl"])) || textFrom(firstValue(source, ["horse"]), ["silkUrl"]),
        lastFive: enriched?.lastFive?.length ? enriched.lastFive.slice(0, 5) : runnerLastFive(runner),
        horse: country ? `${name} (${country})` : name,
        age: safeText(firstValue(officialRunner, ["age", "horseAge"])) || safeText(firstValue(source, ["age", "horseAge"])),
        sex: safeText(firstValue(officialRunner, ["sex", "horseSex"])) || safeText(firstValue(source, ["sex", "horseSex"])),
        breeding: safeText(firstValue(officialRunner, ["breeding"])) || safeText(firstValue(source, ["breeding", "sireDam"])),
        trainer: safeText(officialRunner.trainer) || safeText(firstValue(source, ["trainerName", "trainer"])),
        jockey: formatJockey(source, officialRunner),
        weight: safeText(officialRunner.weight) || safeText(firstValue(source, ["weight"])),
        barrier: safeText(officialRunner.barrier) || safeText(firstValue(source, ["barrierNumber", "liveBarrierNumber", "barrier"])),
        effectiveBarrier: safeText(firstValue(officialRunner, ["effectiveBarrier", "adjustedBarrier"])) || safeText(firstValue(source, ["effectiveBarrier", "adjustedBarrier"])),
        daysSinceLastRun,
        rating: metricText(enriched?.rating, 1),
        epi: metricText(enriched?.epi, 1),
        epiRank: "",
        epiFieldAverage: "",
        epiDifference: "",
        earlySpeed: metricText(enriched?.earlySpeed, 0),
        earlySpeedLabel: "Early Speed",
        marketPrice,
        edgeiqPrice: scratched ? "" : formatPrice(enriched?.edgeiqPrice),
        suitabilityScore: metricText(enriched?.suitability, 0),
        suitabilityLabel: "",
        shapeFit: humaniseEngineLabel(enriched?.raceShape) || metricText(enriched?.raceShape),
        late: metricText(enriched?.lateSpeed, 1),
        formMomentum: metricText(enriched?.formMomentum, 1),
        formMomentumDirection: metricNumber(enriched?.formMomentum) === null ? "" : Number(unwrapSourceValue(enriched?.formMomentum)) >= 0 ? "up" : "down",
        scratched,
        country,
        gear: safeText(firstValue(officialRunner, ["currentGear"])) || textFrom(firstValue(source, ["horse"]), ["currentGear"]) || safeText(firstValue(source, ["gearChanges"])),
        careerProfile,
        conditionProfile: profileRows(enriched?.conditionProfile, (label) => conditionFamily(label) === todayCondition),
        classProfile: profileRows(enriched?.classProfile, (label) => {
          const labelToken = classToken(label);
          return Boolean(todayClass && labelToken && (labelToken === todayClass || labelToken.includes(todayClass) || todayClass.includes(labelToken)));
        }),
        jockeyProfile,
        raceDayPattern: profileRows(enriched?.preparationProfile?.length ? enriched.preparationProfile : enriched?.raceDayPattern),
        lastStart: lastStartFromRun(enriched?.lastStart, daysSinceLastRun),
        insights: [],
        governedStatements,
        recentRuns,
      };
      display.insights = buildInsights(display);
      return display;
    })
    .sort((a, b) => a.sortNo - b.sortNo);

  const activeEpiValues = runners
    .filter((runner) => !runner.scratched)
    .map((runner) => ({ id: runner.id, value: metricNumber(runner.epi) }))
    .filter((item): item is { id: string; value: number } => item.value !== null);
  const fieldAverage = activeEpiValues.length
    ? activeEpiValues.reduce((total, item) => total + item.value, 0) / activeEpiValues.length
    : null;
  const ranks = new Map<string, number>();
  [...activeEpiValues]
    .sort((a, b) => b.value - a.value)
    .forEach((item, index) => ranks.set(item.id, index + 1));

  runners.forEach((runner) => {
    const epi = metricNumber(runner.epi);
    const rank = ranks.get(runner.id);
    runner.epiRank = rank ? `${rank} of ${activeEpiValues.length}` : "";
    runner.epiFieldAverage = fieldAverage === null ? "" : fieldAverage.toFixed(1);
    runner.epiDifference = epi === null || fieldAverage === null ? "" : signedMetricText(epi - fieldAverage, 1);
  });

  return {
    meeting,
    date,
    raceNumber,
    raceName,
    primaryLine: [meeting, longDate, raceNumber ? `Race ${raceNumber}` : ""].filter(Boolean).join(" - "),
    metadata,
    runners,
    activeFieldEpi: {
      validRunnerCount: activeEpiValues.length,
      fieldAverage,
    },
    fieldSummary: `${runners.length} runners | ${runners.filter((runner) => runner.scratched).length} scratched`,
  };
}

export function displayOrDash(value: string): string {
  return value || EMPTY;
}
