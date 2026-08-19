import type {
  BenchmarkExplanationIndexRow,
  HistoricalPerformanceIntelligenceRow,
  HorseIntelligenceIndexRow,
  PerformanceIntelligenceFeed,
  PerformanceIntelligenceRaceContext,
  RaceIntelligenceIndexRow,
} from "./types";

function clean(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function key(value: unknown): string {
  return clean(value).toUpperCase();
}

function normaliseHorse(value: unknown): string {
  return key(value).replace(/[^A-Z0-9]/g, "");
}

function raceKeyFromParts(date: unknown, track: unknown, raceNumber: unknown): string {
  const dateText = clean(date);
  const trackText = key(track);
  const raceText = clean(raceNumber).replace(/^R/i, "");
  if (!dateText || !trackText || !raceText) return "";
  return `${dateText}|${trackText}|R${raceText}`;
}

export function formatBenchmarkLevel(level: string): string {
  const text = clean(level);
  return text ? `Level ${text}` : "Unavailable";
}

export function formatBenchmarkConfidence(confidence: string): string {
  return clean(confidence).replace(/_/g, " ") || "Unavailable";
}

export function profileSummary(profile: string, limit = 3): string {
  return clean(profile)
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, limit)
    .join(" | ");
}

export class PerformanceIntelligenceService {
  private raceByKey = new Map<string, RaceIntelligenceIndexRow>();
  private horsesByRace = new Map<string, HorseIntelligenceIndexRow[]>();
  private historicalByRace = new Map<string, HistoricalPerformanceIntelligenceRow[]>();
  private historicalByRunner = new Map<string, HistoricalPerformanceIntelligenceRow[]>();
  private benchmarkById = new Map<string, BenchmarkExplanationIndexRow>();

  constructor(public readonly feed: PerformanceIntelligenceFeed) {
    feed.race_intelligence_index.forEach((row) => {
      if (clean(row.race_context_key)) this.raceByKey.set(key(row.race_context_key), row);
      const derivedKey = raceKeyFromParts(row.race_date, row.track, row.race_number);
      if (derivedKey) this.raceByKey.set(derivedKey, row);
    });

    feed.horse_intelligence_index.forEach((row) => {
      const raceKey = key(row.race_context_key);
      if (!raceKey) return;
      const rows = this.horsesByRace.get(raceKey) ?? [];
      rows.push(row);
      this.horsesByRace.set(raceKey, rows);
    });

    feed.historical_performance_intelligence_index.forEach((row) => {
      const raceKey = key(row.current_race_context_key);
      if (!raceKey) return;
      const raceRows = this.historicalByRace.get(raceKey) ?? [];
      raceRows.push(row);
      this.historicalByRace.set(raceKey, raceRows);

      const runnerKey = `${raceKey}|${clean(row.runner_number)}|${normaliseHorse(row.horse)}`;
      const runnerRows = this.historicalByRunner.get(runnerKey) ?? [];
      runnerRows.push(row);
      this.historicalByRunner.set(runnerKey, runnerRows);
    });

    feed.benchmark_explanation_index.forEach((row) => {
      if (clean(row.benchmark_id)) this.benchmarkById.set(clean(row.benchmark_id), row);
    });
  }

  getRace(raceKey: string | null | undefined): RaceIntelligenceIndexRow | null {
    return this.raceByKey.get(key(raceKey)) ?? null;
  }

  getRaceContext(raceKey: string | null | undefined): PerformanceIntelligenceRaceContext {
    const raceKeyText = key(raceKey);
    const historical = this.historicalByRace.get(raceKeyText) ?? [];
    const benchmarkIds = new Set(historical.map((row) => clean(row.selected_benchmark_id)).filter(Boolean));
    const race = this.getRace(raceKeyText);
    if (race?.selected_benchmark_id) benchmarkIds.add(clean(race.selected_benchmark_id));

    return {
      race,
      horses: this.horsesByRace.get(raceKeyText) ?? [],
      historical,
      benchmarks: [...benchmarkIds].map((id) => this.getBenchmark(id)).filter((row): row is BenchmarkExplanationIndexRow => Boolean(row)),
    };
  }

  getHorse(raceKey: string | null | undefined, runnerNumber?: string | number | null, horseName?: string | null): HorseIntelligenceIndexRow | null {
    const rows = this.horsesByRace.get(key(raceKey)) ?? [];
    const runner = clean(runnerNumber);
    const horse = normaliseHorse(horseName);
    return (
      rows.find((row) => runner && clean(row.runner_number) === runner) ??
      rows.find((row) => horse && normaliseHorse(row.horse_name) === horse) ??
      null
    );
  }

  getHistoricalForRunner(
    raceKey: string | null | undefined,
    runnerNumber?: string | number | null,
    horseName?: string | null,
  ): HistoricalPerformanceIntelligenceRow[] {
    const raceKeyText = key(raceKey);
    const runner = clean(runnerNumber);
    const horse = normaliseHorse(horseName);
    const exact = this.historicalByRunner.get(`${raceKeyText}|${runner}|${horse}`);
    if (exact) return exact;
    return (this.historicalByRace.get(raceKeyText) ?? []).filter((row) => {
      if (runner && clean(row.runner_number) === runner) return true;
      return Boolean(horse && normaliseHorse(row.horse) === horse);
    });
  }

  getBenchmark(benchmarkId: string | null | undefined): BenchmarkExplanationIndexRow | null {
    return this.benchmarkById.get(clean(benchmarkId)) ?? null;
  }
}

export function buildPerformanceIntelligenceService(feed: PerformanceIntelligenceFeed): PerformanceIntelligenceService {
  return new PerformanceIntelligenceService(feed);
}
