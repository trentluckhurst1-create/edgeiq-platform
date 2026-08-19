import type {
  HistoricalPerformanceIntelligenceRow,
  HorseIntelligenceIndexRow,
  PerformanceIntelligenceFeed,
  RaceIntelligenceIndexRow,
} from "../services/performance-intelligence";

export type CompareEntityMode = "HORSE" | "RACE";

export type CompareEntityOption = {
  id: string;
  label: string;
  meta: string;
};

export type CompareUnavailableMode = {
  label: string;
  reason: string;
};

export type CompareMetricRow = {
  label: string;
  left: string;
  right: string;
  scope: string;
};

export type ComparePanel = {
  title: string;
  subtitle: string;
  rows: CompareMetricRow[];
};

export type CompareHistoricalPairRow = {
  id: string;
  side: "Left" | "Right";
  date: string;
  race: string;
  distance: string;
  className: string;
  condition: string;
  finish: string;
  margin: string;
  sp: string;
  benchmark: string;
};

export type CompareViewModel = {
  mode: CompareEntityMode;
  options: CompareEntityOption[];
  leftPanel: ComparePanel | null;
  rightPanel: ComparePanel | null;
  metricRows: CompareMetricRow[];
  historicalRows: CompareHistoricalPairRow[];
  unavailableModes: CompareUnavailableMode[];
  feedGenerated: string;
  limitationText: string;
};

const UNAVAILABLE = "Unavailable";

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function value(value: unknown): string {
  return clean(value) || UNAVAILABLE;
}

function titleCase(value: unknown): string {
  const text = clean(value);
  if (!text) return UNAVAILABLE;
  return text
    .toLowerCase()
    .split(/[\s_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function numberKey(value: unknown): number {
  const parsed = Number(clean(value).replace(/[^\d.]/g, ""));
  return Number.isFinite(parsed) ? parsed : 9999;
}

function normaliseKey(value: unknown): string {
  return clean(value).toUpperCase();
}

function horseId(row: HorseIntelligenceIndexRow): string {
  return ["HORSE", row.race_context_key, row.runner_number, row.horse_code || row.horse_name].map(clean).join("|");
}

function raceId(row: RaceIntelligenceIndexRow): string {
  return ["RACE", row.race_context_key].map(clean).join("|");
}

function raceLabel(row: RaceIntelligenceIndexRow): string {
  const track = value(row.track);
  const raceNo = clean(row.race_number).replace(/^R/i, "");
  return `${track} R${raceNo || "?"}`;
}

function raceMeta(row: RaceIntelligenceIndexRow): string {
  return [row.race_date, row.distance_metres ? `${row.distance_metres}m` : "", row.race_class, row.track_condition]
    .map(clean)
    .filter(Boolean)
    .join(" | ");
}

function horseMeta(row: HorseIntelligenceIndexRow): string {
  const runner = clean(row.runner_number) ? `No ${clean(row.runner_number)}` : "";
  return [runner, row.date_range, `${value(row.performance_count)} starts`].filter(Boolean).join(" | ");
}

function scopedHorses(feed: PerformanceIntelligenceFeed, raceKey?: string | null): HorseIntelligenceIndexRow[] {
  const key = normaliseKey(raceKey);
  const rows = key
    ? feed.horse_intelligence_index.filter((row) => normaliseKey(row.race_context_key) === key)
    : feed.horse_intelligence_index;

  return [...rows]
    .filter((row) => clean(row.horse_name))
    .sort((a, b) => {
      const raceOrder = normaliseKey(a.race_context_key).localeCompare(normaliseKey(b.race_context_key));
      if (raceOrder !== 0) return raceOrder;
      return numberKey(a.runner_number) - numberKey(b.runner_number);
    });
}

function raceRows(feed: PerformanceIntelligenceFeed): RaceIntelligenceIndexRow[] {
  return [...feed.race_intelligence_index]
    .filter((row) => clean(row.race_context_key))
    .sort((a, b) => {
      const dateOrder = clean(a.race_date).localeCompare(clean(b.race_date));
      if (dateOrder !== 0) return dateOrder;
      const trackOrder = clean(a.track).localeCompare(clean(b.track));
      if (trackOrder !== 0) return trackOrder;
      return numberKey(a.race_number) - numberKey(b.race_number);
    });
}

export function getCompareOptions(
  feed: PerformanceIntelligenceFeed | null,
  mode: CompareEntityMode,
  raceKey?: string | null,
): CompareEntityOption[] {
  if (!feed) return [];
  if (mode === "RACE") {
    return raceRows(feed).map((row) => ({ id: raceId(row), label: raceLabel(row), meta: raceMeta(row) }));
  }

  return scopedHorses(feed, raceKey).map((row) => ({
    id: horseId(row),
    label: value(row.horse_name),
    meta: horseMeta(row),
  }));
}

function findHorse(feed: PerformanceIntelligenceFeed, id: string): HorseIntelligenceIndexRow | null {
  return scopedHorses(feed).find((row) => horseId(row) === id) ?? null;
}

function findRace(feed: PerformanceIntelligenceFeed, id: string): RaceIntelligenceIndexRow | null {
  return raceRows(feed).find((row) => raceId(row) === id) ?? null;
}

function horseMetricRows(left: HorseIntelligenceIndexRow | null, right: HorseIntelligenceIndexRow | null): CompareMetricRow[] {
  const pairs: Array<[string, keyof HorseIntelligenceIndexRow, string]> = [
    ["Profile State", "profile_quality_state", "Horse profile"],
    ["Identity State", "identity_quality_state", "Horse profile"],
    ["Performance Count", "performance_count", "Eligible historical runs"],
    ["Eligible Performances", "eligible_performance_count", "Eligible historical runs"],
    ["Date Range", "date_range", "Historical coverage"],
    ["Track Profile", "track_profile", "Comparable profile"],
    ["Distance Profile", "distance_profile", "Comparable profile"],
    ["Condition Profile", "going_profile", "Comparable profile"],
    ["Class Profile", "class_profile", "Comparable profile"],
    ["Pressure Profile", "pressure_profile", "Race shape"],
    ["Late Speed Profile", "late_speed_profile", "Race shape"],
    ["Consistency Profile", "consistency_profile", "Performance pattern"],
  ];

  return pairs.map(([label, key, scope]) => ({
    label,
    left: value(left?.[key]),
    right: value(right?.[key]),
    scope,
  }));
}

function raceMetricRows(left: RaceIntelligenceIndexRow | null, right: RaceIntelligenceIndexRow | null): CompareMetricRow[] {
  const pairs: Array<[string, keyof RaceIntelligenceIndexRow, string]> = [
    ["Meeting", "meeting", "Race identity"],
    ["Race Date", "race_date", "Race identity"],
    ["Race Name", "race_name", "Race identity"],
    ["Distance", "distance_metres", "Race conditions"],
    ["Class", "race_class", "Race conditions"],
    ["Track Condition", "track_condition", "Race conditions"],
    ["Rail", "rail_position", "Race conditions"],
    ["Runner Count", "runner_count", "Field composition"],
    ["Race Quality", "race_quality_state", "Governed assessment"],
    ["Benchmark Level", "selected_benchmark_level", "Benchmark selection"],
    ["Benchmark Sample", "selected_benchmark_sample_size", "Benchmark selection"],
    ["Fingerprint", "fingerprint_pattern", "Race pattern"],
    ["Fingerprint State", "fingerprint_quality_state", "Race pattern"],
  ];

  return pairs.map(([label, key, scope]) => ({
    label,
    left: value(left?.[key]),
    right: value(right?.[key]),
    scope,
  }));
}

function horsePanel(row: HorseIntelligenceIndexRow | null, side: string): ComparePanel | null {
  if (!row) return null;
  return {
    title: value(row.horse_name),
    subtitle: horseMeta(row),
    rows: [
      { label: "Profile State", left: titleCase(row.profile_quality_state), right: "", scope: side },
      { label: "Runs", left: value(row.performance_count), right: "", scope: side },
      { label: "Eligible Runs", left: value(row.eligible_performance_count), right: "", scope: side },
      { label: "Date Range", left: value(row.date_range), right: "", scope: side },
    ],
  };
}

function racePanel(row: RaceIntelligenceIndexRow | null, side: string): ComparePanel | null {
  if (!row) return null;
  return {
    title: raceLabel(row),
    subtitle: raceMeta(row),
    rows: [
      { label: "Race Quality", left: titleCase(row.race_quality_state), right: "", scope: side },
      { label: "Runners", left: value(row.runner_count), right: "", scope: side },
      { label: "Benchmark", left: value(row.selected_benchmark_level), right: "", scope: side },
      { label: "Pattern", left: value(row.fingerprint_pattern), right: "", scope: side },
    ],
  };
}

function historicalForHorse(feed: PerformanceIntelligenceFeed, horse: HorseIntelligenceIndexRow | null): HistoricalPerformanceIntelligenceRow[] {
  if (!horse) return [];
  const raceKey = normaliseKey(horse.race_context_key);
  const runner = clean(horse.runner_number);
  const horseCode = normaliseKey(horse.horse_code);
  const horseName = normaliseKey(horse.horse_name);
  return feed.historical_performance_intelligence_index
    .filter((row) => {
      if (normaliseKey(row.current_race_context_key) !== raceKey) return false;
      if (runner && clean(row.runner_number) === runner) return true;
      if (horseCode && normaliseKey(row.horse_code) === horseCode) return true;
      return Boolean(horseName && normaliseKey(row.horse) === horseName);
    })
    .sort((a, b) => clean(b.race_date).localeCompare(clean(a.race_date)))
    .slice(0, 5);
}

function toHistoricalPairRows(side: "Left" | "Right", rows: HistoricalPerformanceIntelligenceRow[]): CompareHistoricalPairRow[] {
  return rows.map((row) => ({
    id: `${side}-${row.performance_fact_id || row.legacy_performance_fact_id || row.race_date}-${row.race_number}`,
    side,
    date: value(row.race_date),
    race: [row.track, row.race_number].map(clean).filter(Boolean).join(" R") || UNAVAILABLE,
    distance: clean(row.distance_metres) ? `${clean(row.distance_metres)}m` : UNAVAILABLE,
    className: value(row.race_class),
    condition: value(row.track_condition),
    finish: value(row.finish_position),
    margin: value(row.margin_raw || row.margin_lengths_raw),
    sp: value(row.starting_price),
    benchmark: value(row.benchmark_level),
  }));
}

export function defaultCompareSelection(options: CompareEntityOption[]): { leftId: string; rightId: string } {
  return {
    leftId: options[0]?.id ?? "",
    rightId: options[1]?.id ?? options[0]?.id ?? "",
  };
}

export function buildCompareViewModel(
  feed: PerformanceIntelligenceFeed | null,
  mode: CompareEntityMode,
  leftId: string,
  rightId: string,
  raceKey?: string | null,
): CompareViewModel {
  const options = getCompareOptions(feed, mode, raceKey);
  const unavailableModes = [
    { label: "Jockey", reason: "Governed side-by-side jockey comparison is not available in the current product feed." },
    { label: "Trainer", reason: "Governed side-by-side trainer comparison is not available in the current product feed." },
    { label: "Track", reason: "Governed side-by-side track comparison is not available in the current product feed." },
  ];

  if (!feed || options.length === 0) {
    return {
      mode,
      options,
      leftPanel: null,
      rightPanel: null,
      metricRows: [],
      historicalRows: [],
      unavailableModes,
      feedGenerated: "",
      limitationText: "Governed comparison data is not available for this context.",
    };
  }

  const selection = defaultCompareSelection(options);
  const safeLeftId = options.some((option) => option.id === leftId) ? leftId : selection.leftId;
  const safeRightId = options.some((option) => option.id === rightId) ? rightId : selection.rightId;

  if (mode === "RACE") {
    const leftRace = findRace(feed, safeLeftId);
    const rightRace = findRace(feed, safeRightId);
    return {
      mode,
      options,
      leftPanel: racePanel(leftRace, "Left"),
      rightPanel: racePanel(rightRace, "Right"),
      metricRows: raceMetricRows(leftRace, rightRace),
      historicalRows: [],
      unavailableModes,
      feedGenerated: clean(feed.manifest.generated_timestamp),
      limitationText: "Race comparison is limited to fields governed by the certified performance intelligence feed.",
    };
  }

  const leftHorse = findHorse(feed, safeLeftId);
  const rightHorse = findHorse(feed, safeRightId);
  return {
    mode,
    options,
    leftPanel: horsePanel(leftHorse, "Left"),
    rightPanel: horsePanel(rightHorse, "Right"),
    metricRows: horseMetricRows(leftHorse, rightHorse),
    historicalRows: [
      ...toHistoricalPairRows("Left", historicalForHorse(feed, leftHorse)),
      ...toHistoricalPairRows("Right", historicalForHorse(feed, rightHorse)),
    ],
    unavailableModes,
    feedGenerated: clean(feed.manifest.generated_timestamp),
    limitationText: "Only common governed fields are compared. Different sample sizes and date ranges remain visible.",
  };
}
