import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import FormTab from "./components/FormTab";
import GearTab from "./components/GearTab";
import PerformanceTab from "./components/PerformanceTab";
import RatingsTab from "./components/RatingsTab";
import SpeedMapTab from "./components/SpeedMapTab";
import Worksheet from "./components/Worksheet";


type TabKey = "Worksheet" | "Ratings" | "Form" | "Speed Map" | "Performance" | "Results" | "Bets" | "Gear";
type CsvRow = Record<string, string>;

export type FormHistoryRow = {
  id: string;
  horse: string;
  horseKey: string;
  matchKey: string;
  runDate: string;
  track: string;
  distance: number | null;
  raceClass: string;
  trackCondition: string;
  finishPos: string;
  margin: string;
  jockey: string;
  sp: string;
  runRating: number | null;
  runType: string;
  isOfficialRace: boolean;
};

export type FullCareerFormRow = FormHistoryRow & {
  fieldSize: string;
  trainer: string;
  barrier: string;
  weightCarried: string;
  officialTime: string;
  winner: string;
  second: string;
  pos800: string;
  pos400: string;
  inRunPositions: string;
  ratingDisplay: string;
  sourceUrl: string;
};

export type FormSummary = {
  horseKey: string;
  horse: string;
  ls1: number | null;
  ls2: number | null;
  ls3: number | null;
  ls4: number | null;
  ls5: number | null;
  avg3: number | null;
  avg5: number | null;
  peak: number | null;
  officialRunCount: number | null;
  gap: number | null;
};

export type CareerStats = {
  horseKey: string;
  horse: string;
  raceDate: string;
  track: string;
  raceNo: number;
  hasOfficialForm: boolean;
  careerStarts: number;
  careerWins: number;
  careerSeconds: number;
  careerThirds: number;
  trackStarts: number;
  trackWins: number;
  trackSeconds: number;
  trackThirds: number;
  distanceStarts: number;
  distanceWins: number;
  distanceSeconds: number;
  distanceThirds: number;
  trackDistanceStarts: number;
  trackDistanceWins: number;
  trackDistanceSeconds: number;
  trackDistanceThirds: number;
  firstUpStarts: number;
  firstUpWins: number;
  firstUpSeconds: number;
  firstUpThirds: number;
  secondUpStarts: number;
  secondUpWins: number;
  secondUpSeconds: number;
  secondUpThirds: number;
  fastStarts: number;
  fastWins: number;
  fastSeconds: number;
  fastThirds: number;
  goodStarts: number;
  goodWins: number;
  goodSeconds: number;
  goodThirds: number;
  softStarts: number;
  softWins: number;
  softSeconds: number;
  softThirds: number;
  heavyStarts: number;
  heavyWins: number;
  heavySeconds: number;
  heavyThirds: number;
  distancesWon: string;
  weightsWonWith: string;
};

export type RatingDisplayRow = {
  id: string;
  raceKey: string;
  raceDate: string;
  track: string;
  raceNo: number;
  raceTime: string;
  horse: string;
  horseKey: string;
  matchKey: string;
  horseNo: number | null;
  jockey: string;
  trainer: string;
  barrier: number | null;
  raceClass: string;
  distance: number | null;
  todayTrackCondition: string;
  todayRating: number | null;
  winningFigure: number | null;
  ratedPrice: number | null;
  marketPrice: number | null;
  marketStatus: string;
  marketNote: string;
  highEdgeReview: boolean;
  modelRank: number | null;
  edgePct: number | null;
  isScratched: boolean;
  gearChanges: string;
  flucs: string;
  exp: number | null;
  ls1: number | null;
  ls2: number | null;
  ls3: number | null;
  ls4: number | null;
  ls5: number | null;
  peak: number | null;
  silkUrl: string;
};

type RaceGroup = {
  key: string;
  raceDate: string;
  track: string;
  raceNo: number;
  raceClass: string;
  distance: number | null;
  winningFigure: number | null;
  todayTrackCondition: string;
  rows: RatingDisplayRow[];
};

type MeetingGroup = {
  meetingKey: string;
  raceDate: string;
  track: string;
  races: RaceGroup[];
};

function text(value: unknown): string {
  if (value === null || value === undefined) return "";
  const raw = String(value).trim();
  if (!raw || raw.toLowerCase() === "nan" || raw.toLowerCase() === "null") return "";
  return raw;
}

function num(value: unknown): number | null {
  const raw = text(value).replace("$", "").replace("%", "");
  if (!raw || raw === "-") return null;
  const parsed = Number(raw);
  if (Number.isFinite(parsed)) return parsed;
  const match = raw.match(/(\d+(?:\.\d+)?)/);
  if (!match) return null;
  const parsedFromText = Number(match[1]);
  return Number.isFinite(parsedFromText) ? parsedFromText : null;
}

function normKey(v: unknown): string {
  return String(v ?? "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .trim();
}

function normTrack(v: unknown): string {
  return String(v ?? "")
    .toUpperCase()
    .replace(/BET365/g, "")
    .replace(/LADBROKES/g, "")
    .replace(/TAB/g, "")
    .replace(/RACINGCOM/g, "")
    .replace(/[^A-Z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function conditionClassName(v: unknown): string {
  const x = text(v).toUpperCase();
  if (x.includes("FAST 1") || x.includes("FAST 2")) return "cond-fast";
  if (x.includes("GOOD 3") || x.includes("GOOD 4")) return "cond-good";
  if (x.includes("SOFT 5") || x.includes("SOFT 6") || x.includes("SOFT 7")) return "cond-soft";
  if (x.includes("HEAVY 8") || x.includes("HEAVY 9") || x.includes("HEAVY 10")) return "cond-heavy";
  return "cond-unknown";
}

function boolish(value: unknown): boolean {
  const raw = text(value).toLowerCase();
  return raw === "1" || raw === "true" || raw === "yes" || raw === "y";
}

function normalizeHorse(value: unknown): string {
  return text(value)
    .toUpperCase()
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/\b(NZ|IRE|GB|USA|FR|JPN|SAF|GER|CAN)\b/g, " ")
    .replace(/\([^)]*\)/g, " ")
    .replace(/['’`]/g, "")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compactKey(value: unknown): string {
  return normalizeHorse(value).replace(/[^A-Z0-9]/g, "");
}

function cleanTrack(value: unknown): string {
  return text(value)
    .toUpperCase()
    .replace(/BET365|SPORTSBET|LADBROKES|TAB|RACING|MRC|ATC|VRC|BRC/g, " ")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function raceKeyOf(raceDate: string, track: string, raceNo: number): string {
  return `${raceDate}|${cleanTrack(track)}|${raceNo}`;
}

function runnerKeyOf(raceDate: string, track: string, raceNo: number, horse: string, horseKey: string): string {
  return `${raceKeyOf(raceDate, track, raceNo)}|${compactKey(horseKey) || compactKey(horse)}`;
}

function meetingKeyOf(raceDate: string, track: string): string {
  return `${raceDate}|${cleanTrack(track)}`;
}

function runTypeOf(runType: string, raceClass: string, official: boolean): string {
  const rt = text(runType).toUpperCase();
  const rc = text(raceClass).toUpperCase();
  if (rt.includes("JUMP") || rt === "J/OUT" || rc.includes("JUMP")) return "JUMPOUT";
  if (rt.includes("TRIAL") || rc.includes("TRIAL") || rc.includes("-BT") || rc.includes("TRL")) return "TRIAL";
  return official ? "RACE" : rt || "TRIAL";
}

function displayDate(dateValue: string): string {
  if (!dateValue) return "-";
  const parsed = new Date(dateValue);
  if (Number.isNaN(parsed.getTime())) return dateValue;
  return parsed.toLocaleDateString("en-AU", { day: "2-digit", month: "short" });
}

async function loadCsv(url: string): Promise<CsvRow[]> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to load ${url}`);
  const csv = await response.text();
  return Papa.parse<CsvRow>(csv, { header: true, skipEmptyLines: true }).data;
}

function lastFiveFromRuns(runs: FormHistoryRow[]) {
  const official = runs
    .filter((run) => run.isOfficialRace && run.runRating !== null)
    .sort((a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime())
    .slice(0, 5);

  const ratings = official.map((run) => run.runRating as number);
  return {
    ls1: official[0]?.runRating ?? null,
    ls2: official[1]?.runRating ?? null,
    ls3: official[2]?.runRating ?? null,
    ls4: official[3]?.runRating ?? null,
    ls5: official[4]?.runRating ?? null,
    peak: ratings.length ? Math.max(...ratings) : null,
  };
}

function usablePrice(row: CsvRow | undefined, field: string): number | null {
  if (!row) return null;
  return num(row[field]);
}

function firstPrice(...values: Array<number | null>): number | null {
  for (const value of values) {
    if (value !== null && Number.isFinite(value) && value > 0) return value;
  }
  return null;
}

function rankRows(rows: RatingDisplayRow[]): RatingDisplayRow[] {
  const ranked = [...rows].sort((a, b) => {
    if (a.isScratched !== b.isScratched) return a.isScratched ? 1 : -1;
    if (a.modelRank !== null && b.modelRank !== null) return a.modelRank - b.modelRank;
    if (a.modelRank !== null) return -1;
    if (b.modelRank !== null) return 1;
    if (a.ratedPrice !== null && b.ratedPrice !== null && a.ratedPrice !== b.ratedPrice) return a.ratedPrice - b.ratedPrice;
    if (a.horseNo !== null && b.horseNo !== null) return a.horseNo - b.horseNo;
    return a.horse.localeCompare(b.horse);
  });

  let autoRank = 1;
  return ranked.map((row) => ({
    ...row,
    modelRank: row.modelRank ?? (row.isScratched ? null : autoRank++),
  }));
}

function defaultSilkUrl(): string {
  return "/silks/default.svg";
}

function formatSummary(race: RaceGroup | null): string {
  if (!race) return "-";
  return [`R${race.raceNo}`, race.distance ? `${race.distance}m` : "", race.raceClass, race.todayTrackCondition].filter(Boolean).join(" | ");
}

export default function App(): React.ReactElement {
  const [tab, setTab] = useState<TabKey>("Worksheet");
  const [raceCardRows, setRaceCardRows] = useState<CsvRow[]>([]);
  const [ratedRows, setRatedRows] = useState<CsvRow[]>([]);
  const [historyRows, setHistoryRows] = useState<CsvRow[]>([]);
  const [summaryRows, setSummaryRows] = useState<CsvRow[]>([]);
  const [speedRows, setSpeedRows] = useState<CsvRow[]>([]);
  const [silkRows, setSilkRows] = useState<CsvRow[]>([]);
  const [scratchRows, setScratchRows] = useState<any[]>([]);
  const [careerStatsRows, setCareerStatsRows] = useState<CsvRow[]>([]);
  const [fullCareerRows, setFullCareerRows] = useState<CsvRow[]>([]);
  const [selectedMeetingKey, setSelectedMeetingKey] = useState("");
  const getNextRace = (rows) => {
  const now = new Date();
  const upcoming = rows.filter(r => new Date(r.race_datetime) >= now);
  return upcoming.sort((a,b)=> new Date(a.race_datetime).getTime() - new Date(b.race_datetime).getTime())[0];
};

const [selectedRaceKey, setSelectedRaceKey] = useState("");
  const [selectedHorseKey, setSelectedHorseKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function run(): Promise<void> {
      try {
        setLoading(true);
        setError("");
        const [raceCard, rated, history, summary, speed, silks, careerStats, fullCareer, scratchings] = await Promise.all([    loadCsv("/data/race_card_report.csv"),
          loadCsv("/data/rated_market_v2.csv"),
          loadCsv("/data/form_card_runs.csv"),
          loadCsv("/data/form_card_summary.csv"),
          loadCsv("/data/speed_map_report.csv"),
          loadCsv("/data/horse_silks.csv"),
          loadCsv("/data/horse_career_stats.csv"),
          loadCsv("/data/full_career_form.csv"),
          loadCsv("/data/scratchings_gear.csv"),
        ]);

        if (!active) return;
        setRaceCardRows(raceCard);
        setRatedRows(rated);
        setHistoryRows(history);
        setSummaryRows(summary);
        setSpeedRows(speed);
        setSilkRows(silks);
        setCareerStatsRows(careerStats);
        setFullCareerRows(fullCareer);
        setScratchRows((scratchings || []).filter(r => String(r.is_scratched).toLowerCase() === 'true'));
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load local data files");
      } finally {
        if (active) setLoading(false);
      }
    }

    void run();
    return () => {
      active = false;
    };
  }, []);

  
  const scratchMap = useMemo(() => {
    const map = new Map<string, boolean>();

    for (const r of scratchRows) {
      const horse = normKey(r.horse_key || r.horse);
      if (!horse || horse === "WEATHER" || horse === "THEREARENOLATESCRATCHINGS") continue;

      const key = `${normKey(r.race_date)}|${normTrack(r.track)}|${normKey(r.race_no)}|${horse}`;
      if (boolish(r.is_scratched)) {
        map.set(key, true);
      }
    }

    return map;
  }, [scratchRows]);

const silkByHorse = useMemo(() => {
    const map = new Map<string, string>();
    for (const row of silkRows) {
      const keys = [compactKey(row.horse_key), compactKey(row.horse)].filter(Boolean);
      const url = text(row.local_silk_path) || text(row.silk_url);
      if (!url) continue;
      for (const key of keys) {
        if (!map.has(key)) map.set(key, url);
      }
    }
    return map;
  }, [silkRows]);

  const historyByHorse = useMemo(() => {
    const map = new Map<string, FormHistoryRow[]>();

    function add(key: string, run: FormHistoryRow): void {
      if (!key) return;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(run);
    }

    for (const row of historyRows) {
      const horse = text(row.horse);
      const horseKey = compactKey(row.horse_key) || compactKey(horse);
      if (!horseKey) continue;

      const official = boolish(row.is_official_race);
      const raceClass = text(row.race_class);
      const runType = runTypeOf(row.run_type, raceClass, official);
      const run: FormHistoryRow = {
        id: `${horseKey}|${text(row.run_date)}|${text(row.track)}|${text(row.distance)}|${text(row.finish_pos)}|${runType}`,
        horse,
        horseKey,
        matchKey: compactKey(horse),
        runDate: text(row.run_date || row.race_date),
        track: text(row.track),
        distance: num(row.distance),
        raceClass,
        trackCondition: text(row.track_condition),
        finishPos: text(row.finish_pos),
        margin: text(row.margin),
        jockey: text(row.jockey),
        sp: text(row.sp),
        runRating: runType === "RACE" ? num(row.run_rating) : null,
        runType,
        isOfficialRace: runType === "RACE" && official,
      };

      add(horseKey, run);
      add(compactKey(horse), run);
      add(normalizeHorse(horse), run);
    }

    for (const [key, runs] of map.entries()) {
      const deduped = Array.from(new Map(runs.map((run) => [run.id, run])).values()).sort(
        (a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime()
      );
      map.set(key, deduped);
    }

    return map;
  }, [historyRows]);

  const summaryByHorse = useMemo(() => {
    const map = new Map<string, FormSummary>();
    for (const row of summaryRows) {
      const horse = text(row.horse);
      const horseKey = compactKey(row.horse_key) || compactKey(horse);
      if (!horseKey) continue;
      const summary: FormSummary = {
        horseKey,
        horse,
        ls1: num(row["1LS"]),
        ls2: num(row["2LS"]),
        ls3: num(row["3LS"]),
        ls4: num(row["4LS"]),
        ls5: num(row["5LS"]),
        avg3: num(row["3LSA"]),
        avg5: num(row["5LSA"]),
        peak: num(row.PEAK),
        officialRunCount: num(row.official_run_count),
        gap: num(row.gap),
      };
      for (const key of [horseKey, compactKey(horse), normalizeHorse(horse)].filter(Boolean)) {
        if (!map.has(key)) map.set(key, summary);
      }
    }
    return map;
  }, [summaryRows]);

  const fullCareerByHorse = useMemo(() => {
    const map = new Map<string, FullCareerFormRow[]>();

    function add(key: string, run: FullCareerFormRow): void {
      if (!key) return;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(run);
    }

    for (const row of fullCareerRows) {
      const horse = text(row.horse);
      const horseKey = compactKey(row.horse_key) || compactKey(horse);
      if (!horseKey) continue;

      const raceClass = text(row.race_class);
      const runType = runTypeOf(row.run_type, raceClass, text(row.run_type).toUpperCase() === "RACE");
      const runRating = runType === "RACE" ? num(row.run_rating) : null;
      const run: FullCareerFormRow = {
        id: `${horseKey}|${text(row.run_date)}|${text(row.track)}|${text(row.distance)}|${text(row.finish_pos)}|${runType}|${text(row.source_url)}`,
        horse,
        horseKey,
        matchKey: compactKey(horse),
        runDate: text(row.run_date || row.date),
        track: text(row.track),
        distance: num(row.distance),
        raceClass,
        trackCondition: text(row.track_condition),
        finishPos: text(row.finish_pos),
        margin: text(row.margin),
        jockey: text(row.jockey),
        sp: text(row.sp_text) || text(row.starting_price),
        runRating,
        runType,
        isOfficialRace: runType === "RACE",
        fieldSize: text(row.field_size),
        trainer: text(row.trainer),
        barrier: text(row.barrier),
        weightCarried: text(row.weight_carried),
        officialTime: text(row.official_time),
        winner: text(row.winner),
        second: text(row.second),
        pos800: text(row.pos_800),
        pos400: text(row.pos_400),
        inRunPositions: text(row.in_run_positions),
        ratingDisplay: text(row.rating_display) || (runRating !== null ? runRating.toFixed(1) : runType === "RACE" ? "-" : "Not rated"),
        sourceUrl: text(row.source_url),
      };

      add(horseKey, run);
      add(compactKey(horse), run);
      add(normalizeHorse(horse), run);
    }

    for (const [key, runs] of map.entries()) {
      const deduped = Array.from(new Map(runs.map((run) => [run.id, run])).values()).sort(
        (a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime()
      );
      map.set(key, deduped);
    }

    return map;
  }, [fullCareerRows]);

  const careerStatsByRunner = useMemo(() => {
    const map = new Map<string, CareerStats>();
    for (const row of careerStatsRows) {
      const raceDate = text(row.race_date);
      const track = text(row.track);
      const raceNo = num(row.race_no) ?? 0;
      const horse = text(row.horse);
      const horseKey = compactKey(row.horse_key) || compactKey(horse);
      if (!horseKey) continue;
      const stats: CareerStats = {
        horseKey,
        horse,
        raceDate,
        track,
        raceNo,
        hasOfficialForm: boolish(row.has_official_form),
        careerStarts: num(row.career_starts) ?? 0,
        careerWins: num(row.career_wins) ?? 0,
        careerSeconds: num(row.career_seconds) ?? 0,
        careerThirds: num(row.career_thirds) ?? 0,
        trackStarts: num(row.track_starts) ?? 0,
        trackWins: num(row.track_wins) ?? 0,
        trackSeconds: num(row.track_seconds) ?? 0,
        trackThirds: num(row.track_thirds) ?? 0,
        distanceStarts: num(row.distance_starts) ?? 0,
        distanceWins: num(row.distance_wins) ?? 0,
        distanceSeconds: num(row.distance_seconds) ?? 0,
        distanceThirds: num(row.distance_thirds) ?? 0,
        trackDistanceStarts: num(row.track_distance_starts) ?? 0,
        trackDistanceWins: num(row.track_distance_wins) ?? 0,
        trackDistanceSeconds: num(row.track_distance_seconds) ?? 0,
        trackDistanceThirds: num(row.track_distance_thirds) ?? 0,
        firstUpStarts: num(row.first_up_starts) ?? 0,
        firstUpWins: num(row.first_up_wins) ?? 0,
        firstUpSeconds: num(row.first_up_seconds) ?? 0,
        firstUpThirds: num(row.first_up_thirds) ?? 0,
        secondUpStarts: num(row.second_up_starts) ?? 0,
        secondUpWins: num(row.second_up_wins) ?? 0,
        secondUpSeconds: num(row.second_up_seconds) ?? 0,
        secondUpThirds: num(row.second_up_thirds) ?? 0,
        fastStarts: num(row.fast_starts) ?? 0,
        fastWins: num(row.fast_wins) ?? 0,
        fastSeconds: num(row.fast_seconds) ?? 0,
        fastThirds: num(row.fast_thirds) ?? 0,
        goodStarts: num(row.good_starts) ?? 0,
        goodWins: num(row.good_wins) ?? 0,
        goodSeconds: num(row.good_seconds) ?? 0,
        goodThirds: num(row.good_thirds) ?? 0,
        softStarts: num(row.soft_starts) ?? 0,
        softWins: num(row.soft_wins) ?? 0,
        softSeconds: num(row.soft_seconds) ?? 0,
        softThirds: num(row.soft_thirds) ?? 0,
        heavyStarts: num(row.heavy_starts) ?? 0,
        heavyWins: num(row.heavy_wins) ?? 0,
        heavySeconds: num(row.heavy_seconds) ?? 0,
        heavyThirds: num(row.heavy_thirds) ?? 0,
        distancesWon: text(row.distances_won),
        weightsWonWith: text(row.weights_won_with),
      };
      map.set(runnerKeyOf(raceDate, track, raceNo, horse, horseKey), stats);
    }
    return map;
  }, [careerStatsRows]);

  const ratedByRunner = useMemo(() => {
    const map = new Map<string, CsvRow>();
    for (const row of ratedRows) {
      const raceDate = text(row.race_date);
      const track = text(row.track);
      const raceNo = num(row.race_no) ?? 0;
      const horse = text(row.horse);
      const horseKey = text(row.horse_key);
      map.set(runnerKeyOf(raceDate, track, raceNo, horse, horseKey), row);
    }
    return map;
  }, [ratedRows]);

  const ratingRows = useMemo<RatingDisplayRow[]>(() => {
    const rows = raceCardRows
      .filter((row) => text(row.horse))
      .map((row, index) => {
        const raceDate = text(row.race_date);
        const track = text(row.track);
        const raceNo = num(row.race_no) ?? 0;
        const horse = text(row.horse);
        const horseKey = compactKey(row.horse_key) || compactKey(horse);
        const matchKey = compactKey(horse);
        const rated = ratedByRunner.get(runnerKeyOf(raceDate, track, raceNo, horse, horseKey));
        const history = historyByHorse.get(horseKey) ?? historyByHorse.get(matchKey) ?? [];
        const runLast5 = lastFiveFromRuns(history);
        const summary = summaryByHorse.get(horseKey) ?? summaryByHorse.get(matchKey);

        const ratedPrice = firstPrice(usablePrice(rated, "rated_price"), num(row.rated_price));
        const marketPrice = firstPrice(
          num(row.market_price),
          num(row.fixed_odds),
          num(row.win_odds),
          usablePrice(rated, "market_price"),
          usablePrice(rated, "fixed_odds"),
          usablePrice(rated, "win_odds")
        );
        const marketStatus = (text(rated?.market_status) || text(row.market_status) || "MISSING").toUpperCase();
        const marketNote = text(rated?.market_note) || text(row.market_note);
        const highEdgeReview = boolish(rated?.high_edge_review) || boolish(row.high_edge_review);
        const edgePct = marketStatus === "OK" ? num(rated?.edge_pct) ?? num(row.edge_pct) : null;

        return {
          id: `${raceDate}|${track}|${raceNo}|${horseKey}|${index}`,
          raceKey: raceKeyOf(raceDate, track, raceNo),
          raceDate,
          track,
          raceNo,
          raceTime: text(row.race_time),
          horse,
          horseKey,
          matchKey,
          horseNo: num(row.horse_no),
          jockey: text(row.jockey),
          trainer: text(row.trainer),
          barrier: num(row.barrier),
          raceClass: text(row.race_class),
          distance: num(row.distance),
          todayTrackCondition: text(row.track_condition),
          todayRating:
            num(row.today_rating) ??
            usablePrice(rated, "today_rating") ??
            summary?.ls1 ??
            summary?.ls3 ??
            summary?.ls5 ??
            summary?.peak,
          winningFigure: num(row.winning_figure),
          ratedPrice,
          marketPrice,
          marketStatus,
          marketNote,
          highEdgeReview,
          modelRank: num(row.model_rank) ?? usablePrice(rated, "model_rank"),
          edgePct,
          isScratched:
            scratchMap.get(`${normKey(raceDate)}|${normTrack(track)}|${normKey(raceNo)}|${normKey(horseKey)}`) === true ||
            boolish(row.is_scratched),
          gearChanges:
            text(row.gear_changes) ||
            text(row.gear_change) ||
            text(row.gear) ||
            text(row.gear_changes_short) ||
            "-",
          flucs:
            text(row.flucs) ||
            text(row.market_fluctuations) ||
            text(row.price_fluctuations) ||
            text(row.fixed_odds_flucs) ||
            text(row.odds_flucs) ||
            "-",
          exp: summary?.peak ?? runLast5.peak,
          ls1: summary?.ls1 ?? runLast5.ls1,
          ls2: summary?.ls2 ?? runLast5.ls2,
          ls3: summary?.ls3 ?? runLast5.ls3,
          ls4: summary?.ls4 ?? runLast5.ls4,
          ls5: summary?.ls5 ?? runLast5.ls5,
          peak: summary?.peak ?? runLast5.peak,
          silkUrl: silkByHorse.get(horseKey) ?? silkByHorse.get(matchKey) ?? defaultSilkUrl(),
        };
      });

    const grouped = new Map<string, RatingDisplayRow[]>();
    for (const row of rows) {
      if (!grouped.has(row.raceKey)) grouped.set(row.raceKey, []);
      grouped.get(row.raceKey)!.push(row);
    }

    return [...grouped.values()].flatMap(rankRows);
  }, [raceCardRows, ratedByRunner, historyByHorse, summaryByHorse, silkByHorse]);

  const raceGroups = useMemo<RaceGroup[]>(() => {
    const grouped = new Map<string, RatingDisplayRow[]>();
    for (const row of ratingRows) {
      if (!grouped.has(row.raceKey)) grouped.set(row.raceKey, []);
      grouped.get(row.raceKey)!.push(row);
    }

    return [...grouped.entries()]
      .map(([key, rows]) => {
        const first = rows[0];
        return {
          key,
          raceDate: first.raceDate,
          track: first.track,
          raceNo: first.raceNo,
          raceClass: first.raceClass,
          distance: first.distance,
          winningFigure: first.winningFigure,
          todayTrackCondition: first.todayTrackCondition,
          rows,
        };
      })
      .sort((a, b) => a.raceDate.localeCompare(b.raceDate) || a.track.localeCompare(b.track) || a.raceNo - b.raceNo);
  }, [ratingRows]);

  const meetings = useMemo<MeetingGroup[]>(() => {
    const grouped = new Map<string, MeetingGroup>();
    for (const race of raceGroups) {
      const meetingKey = meetingKeyOf(race.raceDate, race.track);
      if (!grouped.has(meetingKey)) grouped.set(meetingKey, { meetingKey, raceDate: race.raceDate, track: race.track, races: [] });
      grouped.get(meetingKey)!.races.push(race);
    }
    return [...grouped.values()]
      .map((meeting) => ({ ...meeting, races: [...meeting.races].sort((a, b) => a.raceNo - b.raceNo) }))
      .sort((a, b) => a.raceDate.localeCompare(b.raceDate) || a.track.localeCompare(b.track));
  }, [raceGroups]);

  useEffect(() => {
    if (!selectedMeetingKey && meetings.length) {
      setSelectedMeetingKey(meetings[0].meetingKey);
      setSelectedRaceKey(meetings[0].races[0]?.key ?? "");
    }
  }, [meetings, selectedMeetingKey]);

  const currentMeeting = useMemo(
    () => meetings.find((meeting) => meeting.meetingKey === selectedMeetingKey) ?? meetings[0] ?? null,
    [meetings, selectedMeetingKey]
  );

  useEffect(() => {
    if (!currentMeeting) return;
    if (!currentMeeting.races.some((race) => race.key === selectedRaceKey)) {
      setSelectedRaceKey(currentMeeting.races[0]?.key ?? "");
    }
  }, [currentMeeting, selectedRaceKey]);

  useEffect(() => {
    function handleTickerRaceSelect(event: Event): void {
      const custom = event as CustomEvent<{ raceDate?: string; track?: string; raceNo?: string }>;
      const raceDate = text(custom.detail?.raceDate);
      const track = cleanTrack(custom.detail?.track);
      const raceNo = num(custom.detail?.raceNo) ?? 0;

      const meeting = meetings.find((item) => item.raceDate === raceDate && cleanTrack(item.track) === track);
      const race = meeting?.races.find((item) => item.raceNo === raceNo);

      if (!meeting || !race) return;

      setSelectedMeetingKey(meeting.meetingKey);
      setSelectedRaceKey(race.key);
      setSelectedHorseKey("");
    }

    window.addEventListener("edgeiq-select-race", handleTickerRaceSelect);
    return () => window.removeEventListener("edgeiq-select-race", handleTickerRaceSelect);
  }, [meetings]);

  const currentRace = useMemo(
    () => currentMeeting?.races.find((race) => race.key === selectedRaceKey) ?? currentMeeting?.races[0] ?? null,
    [currentMeeting, selectedRaceKey]
  );

  useEffect(() => {
    if (!currentRace) return;
  }, [currentRace, selectedHorseKey]);

  const selectedRunner = useMemo(
    () => currentRace?.rows.find((row) => row.horseKey === selectedHorseKey) ?? null,
    [currentRace, selectedHorseKey]
  );

  const selectedHistory = useMemo(() => {
    if (!selectedRunner) return [];
    return historyByHorse.get(selectedRunner.horseKey) ?? historyByHorse.get(selectedRunner.matchKey) ?? [];
  }, [historyByHorse, selectedRunner]);

  const selectedFullCareer = useMemo(() => {
    if (!selectedRunner) return [];
    return fullCareerByHorse.get(selectedRunner.horseKey) ?? fullCareerByHorse.get(selectedRunner.matchKey) ?? [];
  }, [fullCareerByHorse, selectedRunner]);

  const selectedSummary = useMemo(() => {
    if (!selectedRunner) return null;
    return summaryByHorse.get(selectedRunner.horseKey) ?? summaryByHorse.get(selectedRunner.matchKey) ?? null;
  }, [summaryByHorse, selectedRunner]);

  const selectedCareerStats = useMemo(() => {
    if (!selectedRunner) return null;
    return careerStatsByRunner.get(runnerKeyOf(selectedRunner.raceDate, selectedRunner.track, selectedRunner.raceNo, selectedRunner.horse, selectedRunner.horseKey)) ?? null;
  }, [careerStatsByRunner, selectedRunner]);

  const currentSpeedRows = useMemo(() => {
    if (!currentRace) return [];
    return speedRows
      .filter((row) => {
        return text(row.race_date) === currentRace.raceDate && cleanTrack(row.track) === cleanTrack(currentRace.track) && (num(row.race_no) ?? 0) === currentRace.raceNo;
      })
      .map((row) => {
        const key = compactKey(row.horse_key) || compactKey(row.horse);
        return { ...row, silkUrl: silkByHorse.get(key) ?? defaultSilkUrl() };
      });
  }, [speedRows, currentRace, silkByHorse]);

  const allHistoryRows = useMemo(() => {
    const seen = new Set<string>();
    const rows: FormHistoryRow[] = [];
    for (const list of historyByHorse.values()) {
      for (const run of list) {
        if (seen.has(run.id)) continue;
        seen.add(run.id);
        rows.push(run);
      }
    }
    
return rows;

  }, [historyByHorse]);

  const topRated = currentRace?.rows.filter((row) => !row.isScratched).sort((a, b) => (a.modelRank ?? 999) - (b.modelRank ?? 999))[0] ?? null;
  const tabs: TabKey[] = ["Worksheet", "Ratings", "Form", "Gear", "Speed Map", "Performance", "Results", "Bets"];

  return (
    <>
      
      <div className="ert-shell min-h-screen bg-[#07101b] text-[#dbe7f3]">
      <div className="mx-auto max-w-[1760px] px-3 pb-3 pt-14 sm:px-4 sm:pt-3">
        <header className="rounded-2xl border border-slate-700/60 bg-gradient-to-r from-[#0b1220] to-[#070d18] text-white shadow-xl">
          <div className="grid gap-2 border-b border-[#263a53] px-3 py-2 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-end">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#f05252]">EDGEiQ RACING</div>
              <div className="mt-0.5 text-[18px] font-semibold tracking-tight">Race worksheet</div>
            </div>
            <div className="grid gap-2 md:grid-cols-[280px_minmax(0,1fr)]">
              <label>
                <span className="mb-1 block text-[10px] uppercase tracking-[0.14em] text-[#aebdd0]">Meeting</span>
                <select
                  value={currentMeeting?.meetingKey ?? ""}
                  onChange={(event) => {
                    const meeting = meetings.find((item) => item.meetingKey === event.target.value);
                    setSelectedMeetingKey(event.target.value);
                    setSelectedRaceKey(meeting?.races[0]?.key ?? "");
                    setSelectedHorseKey("");
                  }}
                  className="h-8 w-full border border-[#3a516d] bg-[#0f1a29] px-2 text-[13px] text-white outline-none"
                >
                  {meetings.map((meeting) => (
                    <option key={meeting.meetingKey} value={meeting.meetingKey}>
                      {meeting.raceDate} | {meeting.track}
                    </option>
                  ))}
                </select>
              </label>
              <div>
                <div className="mb-1 text-[10px] uppercase tracking-[0.14em] text-[#aebdd0]">Race</div>
                <div className="flex gap-1 overflow-x-auto pb-1">
                  {(currentMeeting?.races ?? []).map((race) => (
                    <button
                      key={race.key}
                      type="button"
                      onClick={() => {
                        setSelectedRaceKey(race.key);
                        setSelectedHorseKey("");
                      }}
                      className={[
                        "h-9 min-w-[52px] rounded-full border px-3 text-[11px] font-bold tracking-wide",
                        race.key === currentRace?.key
                          ? "border-[#f05252] bg-emerald-500/10 text-white border border-emerald-400/40"
                          : "border-slate-700 bg-[#0b1220] text-slate-300 hover:border-emerald-400/50 hover:text-white",
                      ].join(" ")}
                    >
                      R{race.raceNo}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {currentRace ? (
              <div className="edgeiq-current-race-detail">
                <span>{currentRace.raceDate}</span>
                <span>{currentRace.rows[0]?.raceTime || "TIME TBC"}</span>
                <span>{currentRace.track}</span>
                <span>R{currentRace.raceNo}</span>
                <span>{currentRace.rows[0]?.distance ? `${currentRace.rows[0].distance}m` : "-"}</span>
                <span>{currentRace.rows[0]?.raceClass || "-"}</span>
                <span className={`condition-pill ${conditionClassName(currentRace.rows[0]?.todayTrackCondition)}`}>
                  {(currentRace.rows[0]?.todayTrackCondition || "-").toUpperCase()}
                </span>
              </div>
            ) : null}
          </div>

          </header>

        <nav className="mt-3 flex gap-2 overflow-x-auto rounded-full border border-slate-700/60 bg-[#070d18] p-2">
          {tabs.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setTab(item)}
              className={[
                "h-9 px-4 text-[12px] font-bold tracking-wide rounded-full transition-all",
                tab === item ? "bg-emerald-500/10 text-white border border-emerald-400/40" : "text-slate-400 hover:text-white hover:bg-[#0f172a]",
              ].join(" ")}
            >
              {item}
            </button>
          ))}
        </nav>

        
      <main className="mt-3">
        

          {loading ? (
            <div className="border border-[#ccd3da] bg-[#07101d] px-4 py-12 text-[14px] text-[#5b6570]">Loading local race files...</div>
          ) : error ? (
            <div className="border border-[#a64b4b] bg-[#07101d] px-4 py-12 text-[14px] text-[#8f3030]">{error}</div>
          ) : tab === "Worksheet" ? (
            <Worksheet runners={currentRace?.rows ?? []} selectedHorseKey={selectedRunner?.horseKey ?? ""} onSelectHorse={setSelectedHorseKey} selectedHorseHistory={selectedHistory} />
          ) : tab === "Ratings" ? (
            <RatingsTab runners={currentRace?.rows ?? []} selectedHorseKey={selectedRunner?.horseKey ?? ""} onSelectHorse={setSelectedHorseKey} historyByHorse={historyByHorse} careerStats={selectedCareerStats} />
          ) : tab === "Form" ? (
            <FormTab
              runners={currentRace?.rows ?? []}
              selectedHorseKey={selectedRunner?.horseKey ?? ""}
              onSelectHorse={setSelectedHorseKey}
              selectedHorseHistory={selectedHistory}
              selectedFullCareer={selectedFullCareer}
              selectedSummary={selectedSummary}
              selectedCareerStats={selectedCareerStats}
            />
          ) : tab === "Gear" ? (
            <GearTab raceDate={currentRace?.raceDate} track={currentRace?.track} raceNo={currentRace?.raceNo} />
          ) : tab === "Speed Map" ? (
            <SpeedMapTab data={currentSpeedRows} />
          ) : tab === "Performance" ? (
            <PerformanceTab runners={currentRace?.rows ?? []} allHistoryRows={allHistoryRows} selectedHorseKey={selectedRunner?.horseKey ?? ""} onSelectHorse={setSelectedHorseKey} careerStatsByRunner={careerStatsByRunner} />
          ) : (
            <div className="border border-[#ccd3da] bg-[#07101d] px-4 py-12 text-[14px] text-[#5b6570]">{tab} tab unchanged.</div>
          )}
        </main>

        <div className="mt-2 text-[10px] text-[#6d7680]">Data: {displayDate(currentRace?.raceDate ?? "")} | local CSV files</div>
      </div>
    </div>
    </>
  );
}





