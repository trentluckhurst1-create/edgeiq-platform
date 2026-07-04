import "./edgeiq-vic-stability-pass.css";
import "./edgeiq-speedmap-v2.css";
import React, { useEffect, useMemo, useRef, useState } from "react";
import Papa from "papaparse";
import FormTab from "./components/FormTab";
import SpeedMapTab from "./components/SpeedMapTab";
import EdgeRaceTicker from "./components/EdgeRaceTicker";

import EdgeBookieBoard from "./components/EdgeBookieBoard";
import "./components/edgeiq-bookie-board.css";

import TerminalNav from "./terminal/layout/TerminalNav";
import "./terminal/layout/terminal-shell.css";
import "./styles/terminal-primitives.css";


import ResultsTab from "./terminal/tabs/ResultsTab";
import LearningTab from "./terminal/tabs/LearningTab";
import MarketTab from "./terminal/tabs/MarketTab";
import OverviewTab from "./terminal/tabs/OverviewTab";
import ExecutionTab from "./terminal/tabs/ExecutionTab";

import RaceIntelligenceScreen from "./components/RaceIntelligenceScreen";
import { EDGEIQ_LIVE_FILES, EDGEIQ_REFRESH_MS } from "./config/edgeiqLiveFeeds";
import { formatUserLocalRaceTime, minutesToJump } from "./utils/raceTime";



type TabKey =
  | "OVERVIEW"
  | "INTELLIGENCE"
  | "MARKET"
  | "RESULTS";

type CsvRow = Record<string, string>;

const TAB_KEYS: TabKey[] = [
  "OVERVIEW",
  "INTELLIGENCE",
  "MARKET",
  "RESULTS",
];
function storedValue(key: string): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(key) ?? "";
}

function storedTab(): TabKey {
  if (typeof window === "undefined") return "INTELLIGENCE";
  const saved = window.localStorage.getItem("edgeiq_active_tab") as TabKey | null;
  return saved && TAB_KEYS.includes(saved) ? saved : "INTELLIGENCE";
}

function saveValue(key: string, value: string): void {
  if (typeof window === "undefined") return;
  if (value) window.localStorage.setItem(key, value);
}
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
  formRating?: number | null;
  baseLast5?: number | null;
  contextLast5?: number | null;
  classAdj?: number | null;
  distanceAdj?: number | null;
  speedAdj?: number | null;
  recencyAdj?: number | null;
  momentumAdj?: number | null;
  weightedRecentRating?: number | null;
  recentSimpleAvg?: number | null;
  runsUsed?: number | null;
  lengthsPointScale?: number | null;
  tripAdjPoints?: number | null;
  weightAdjPoints?: number | null;
  jockeyAdjPoints?: number | null;
  jockeyAdjLabel?: string;
  jockeyStatRatingPoints?: number | null;
  jockeyTier?: string;
  jockeyRecentWinSr?: number | null;
  jockeyRecentPlaceSr?: number | null;
  jockeyActualMinusExpected?: number | null;
  jockeyRoiLast100?: number | null;
  jockeyBestTrack?: string;
  jockeyBestDistanceBand?: string;
  jockeyBestTrainerCombo?: string;
  manualJockeyAdjPoints?: number | null;
  trainerAdjPoints?: number | null;
  trainerAdjLabel?: string;
  trainerTier?: string;
  trainerRecentWinSr?: number | null;
  trainerRoiLast100?: number | null;
  trainerActualMinusExpected?: number | null;
  trainerBestTrack?: string;
  trainerBestDistanceBand?: string;
  trainerBestCondition?: string;
  trainerBestClassBand?: string;
  comboAdjPoints?: number | null;
  comboAdjLabel?: string;
  comboRides?: number | null;
  comboWinSr?: number | null;
  comboActualMinusExpected?: number | null;
  comboRoi?: number | null;
  totalConnectionsAdj?: number | null;
  handicapperAdjTotal?: number | null;
  handicapperRating?: number | null;
  eliteTodayRatingBeforeHandicapper?: number | null;
  handicapperContextFlags?: string;
  rawEliteTodayRating?: number | null;
  calibratedTodayRating?: number | null;
  calibrationAdjPoints?: number | null;
  calibrationLabel?: string;
  modelConfidenceScore?: number | null;
  priceConfidenceBand?: string;
  fakeOverlayRisk?: string;
  fakeOverlayReason?: string;

  sectional_profile?: string;
  sectional_edge_tier?: string;
  sectional_strength_score?: number | null;
  sectional_overlay_signal?: string;
  sectional_confidence?: string;
  tempo_role?: string;
  projected_tempo_shape?: string;
  pace_collapse_risk?: string;
  tempo_fit?: string;
  tempo_edge_score?: number | null;
  tempo_edge_grade?: string;
  sectional_weapon_score?: number | null;
  late_power_index?: number | null;
  burst_index?: number | null;
  sustain_index?: number | null;
  fatigue_risk_index?: number | null;
  run_style_cluster?: string;
};

type RaceGroup = {
  key: string;
  raceDate: string;
  track: string;
  raceNo: number;
  raceTime: string;
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
    .replace(/['â€™`]/g, "")
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
  return `${raceDate}_${cleanTrack(track)}_R${raceNo}`;
}

function runnerKeyOf(raceDate: string, track: string, raceNo: number, horse: string, horseKey: string): string {
  return `${raceKeyOf(raceDate, track, raceNo)}_${compactKey(horseKey) || compactKey(horse)}`;
}

function meetingKeyOf(raceDate: string, track: string): string {
  return `${raceDate}_${cleanTrack(track)}`;
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
  const response = await fetch(`${url}?t=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Failed to load ${url}`);
  const csv = await response.text();
  return Papa.parse<CsvRow>(csv, { header: true, skipEmptyLines: true }).data;
}

async function loadCsvOptional(url: string): Promise<CsvRow[]> {
  try {
    return await loadCsv(url);
  } catch {
    return [];
  }
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


const VIC_TRACKS = new Set([
  "FLEMINGTON",
  "CAULFIELD",
  "SANDOWN",
  "SANDOWN LAKESIDE",
  "SANDOWN HILLSIDE",
  "MOONEE VALLEY",
  "MORNINGTON",
  "PAKENHAM",
  "PAKENHAM SYNTHETIC",
  "BENDIGO",
  "BALLARAT",
  "BALLARAT SYNTHETIC",
  "GEELONG",
  "WARRNAMBOOL",
  "CRANBOURNE",
  "SALE",
  "TERANG",
  "KILMORE",
  "SEYMOUR",
  "ECHUCA",
  "HAMILTON",
  "COLAC",
  "ARARAT",
  "WANGARATTA",
  "BENALLA",
  "SWAN HILL",
  "MILDURA",
  "KYNETON",
  "CAMPERDOWN",
  "CASTERTON",
  "WODONGA",
  "HORSHAM",
  "STAWELL",
  "WERRIBEE",
  "YARRA VALLEY",
  "YARRA GLEN",
  "BAIRNSDALE",
  "AVOCA",
  "BET365 PARK KILMORE",
  "BET365 PARK WODONGA",
  "SPORTSBET BALLARAT",
  "SPORTSBET PAKENHAM",
  "LADBROKES GEELONG",
]);

function isVicTrack(track: unknown): boolean {
  const cleaned = cleanTrack(track).toUpperCase();
  return VIC_TRACKS.has(cleaned) || cleaned.includes("FLEMINGTON") || cleaned.includes("CAULFIELD") || cleaned.includes("SANDOWN") || cleaned.includes("PAKENHAM") || cleaned.includes("BALLARAT") || cleaned.includes("GEELONG") || cleaned.includes("HORSHAM") || cleaned.includes("STAWELL");
}

function formatSummary(race: RaceGroup | null): string {
  if (!race) return "-";
  return [`R${race.raceNo}`, race.distance ? `${race.distance}m` : "", race.raceClass, race.todayTrackCondition].filter(Boolean).join(" | ");
}

function tabTitle(tab: TabKey): string {
  const titles: Record<TabKey, string> = {
    OVERVIEW: "OVERVIEW",
    INTELLIGENCE: "RACE INTELLIGENCE",
    MARKET: "MARKET",
    RESULTS: "RESULTS",
  };
  return titles[tab];
}



function displayUserLocalRaceTime(row?: any, race?: any): string {
  return formatUserLocalRaceTime(row, race, "TIME TBC");
}

function saneOverlay(value: unknown): number | null {
  const parsed = num(value);
  if (parsed === null || !Number.isFinite(parsed)) return null;
  if (Math.abs(parsed) > 150) return null;
  return parsed;
}

function runnerDecision(row: RatingDisplayRow): string {
  if (row.isScratched) return "SCR";
  if (row.fakeOverlayRisk || row.highEdgeReview || !row.marketPrice || !row.ratedPrice) return "WAIT";
  const edge = saneOverlay(row.edgePct);
  if (edge === null) return "SUPPRESSED";
  if ((row.modelConfidenceScore ?? 0) < 35 && edge > 20) return "SUPPRESSED";
  if (edge >= 15) return "EXECUTE";
  if (edge >= 7) return "WATCH";
  return "PASS";
}

function raceStatusLabel(race: RaceGroup | null): string {
  if (!race) return "NO RACE";
  const mins = minutesToJump(race.rows[0], race);
  if (mins === null) return "TIME UNKNOWN";
  if (mins < -5) return "CLOSED";
  if (mins <= 0) return "LIVE";
  if (mins <= 10) return "JUMP SOON";
  return "UPCOMING";
}

export default function App(): React.ReactElement {
  const [tab, setTab] = useState<TabKey>(storedTab);
  const [raceCardRows, setRaceCardRows] = useState<CsvRow[]>([]);
  const [raceFieldRows, setRaceFieldRows] = useState<CsvRow[]>([]);
  const [executionEngineRows, setExecutionEngineRows] = useState<CsvRow[]>([]);
  const [ratedRows, setRatedRows] = useState<CsvRow[]>([]); // LIVE TERMINAL FEED
  const [finalRatingRows, setFinalRatingRows] = useState<CsvRow[]>([]);
  const [historyRows, setHistoryRows] = useState<CsvRow[]>([]);
  const [summaryRows, setSummaryRows] = useState<CsvRow[]>([]);
  const [speedRows, setSpeedRows] = useState<CsvRow[]>([]);
  const [silkRows, setSilkRows] = useState<CsvRow[]>([]);
  const [scratchRows, setScratchRows] = useState<any[]>([]);
  const [careerStatsRows, setCareerStatsRows] = useState<CsvRow[]>([]);
  const [fullCareerRows, setFullCareerRows] = useState<CsvRow[]>([]);
  const [resultRows, setResultRows] = useState<CsvRow[]>([]);
  const [raceStandardRows, setRaceStandardRows] = useState<CsvRow[]>([]);
  const [raceRatingTargetRows, setRaceRatingTargetRows] = useState<CsvRow[]>([]);
  const [trackBiasRows, setTrackBiasRows] = useState<CsvRow[]>([]);

  const [pacePressureRows, setPacePressureRows] = useState<CsvRow[]>([]);
  const [raceShapeRows, setRaceShapeRows] = useState<CsvRow[]>([]);
  const [sectionalTempoRows, setSectionalTempoRows] = useState<CsvRow[]>([]);
  const [activeSelectorRows, setActiveSelectorRows] = useState<CsvRow[]>([]);
  const [selectedMeetingKey, setSelectedMeetingKey] = useState(() => storedValue("edgeiq_selected_meeting"));

const [selectedRaceKey, setSelectedRaceKey] = useState(() => storedValue("edgeiq_selected_race"));
  const [selectedHorseKey, setSelectedHorseKey] = useState(() => storedValue("edgeiq_selected_runner"));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const initialSelectionDone = useRef(false);

  useEffect(() => {
    let active = true;

    async function run(): Promise<void> {
      try {
        setLoading(true);
        setError("");
        const [raceCard, raceFields, executionEngine, rated, finalRatings, history, summary, speed, silks, careerStats, fullCareer, scratchings, results, standards, raceRatingTargets, bias, pacePressure, raceShape, sectionalTempo, activeSelector] = await Promise.all([
          loadCsvOptional("/data/edgeiq_vic_three_day_meeting_universe.csv"),
          loadCsvOptional("/data/edgeiq_vic_three_day_race_fields.csv"),
          loadCsvOptional("/data/edgeiq_execution_engine_v4.csv"),
          loadCsvOptional("/data/edgeiq_vic_live_terminal_feed_v1.csv"),
          loadCsvOptional("/data/ratings_final_v2.csv"),
          loadCsvOptional("/data/form_card_runs.csv"),
          loadCsvOptional("/data/form_card_summary.csv"),
          loadCsvOptional("/data/edgeiq_real_speed_map_positions.csv"),
          loadCsvOptional("/data/horse_silks.csv"),
          loadCsvOptional("/data/horse_career_stats.csv"),
          loadCsvOptional("/data/full_career_form.csv"),
          loadCsvOptional("/data/scratchings_gear.csv"),
          loadCsvOptional("/data/results_audit.csv"),
          loadCsvOptional("/data/race_standards.csv"),
          loadCsvOptional("/data/edgeiq_race_rating_targets_v1.csv"),
          loadCsvOptional("/data/track_bias_profile.csv"),
          loadCsvOptional("/data/pace_pressure.csv"),
          loadCsvOptional(EDGEIQ_LIVE_FILES.raceShape),
          loadCsvOptional("/data/edgeiq_sectional_tempo_engine_v1.csv"),
          loadCsvOptional("/data/edgeiq_active_race_selector.csv"),
        ]);

        console.log("EDGEIQ_RUNTIME_DEBUG", {
          raceCardRows: raceCard.length,
          raceFieldsRows: raceFields.length,
          executionRows: executionEngine.length,
          ratedRows: rated.length,
          activeSelectorRows: activeSelector.length,
          firstRatedRow: rated[0] ?? null,
        });

        if (!active) return;
        console.log("selector rows", activeSelector.length);
        console.log("universe rows", raceCard.length);
        console.log("execution rows", executionEngine.length);
        setRaceCardRows(rated.length ? rated : raceCard.length ? raceCard : raceFields.length ? raceFields : executionEngine);
        setRaceFieldRows(raceFields);
        setExecutionEngineRows(executionEngine);
        setRatedRows(rated);
        setFinalRatingRows(finalRatings);
        setHistoryRows(history);
        setSummaryRows(summary);
        setSpeedRows(speed);
        setSilkRows(silks);
        setCareerStatsRows(careerStats);
        setFullCareerRows(fullCareer);
        setScratchRows((scratchings || []).filter(r => boolish(r.is_scratched)));
        setResultRows(results);
        setRaceStandardRows(standards);
        setRaceRatingTargetRows(raceRatingTargets);
        setTrackBiasRows(bias);
        setPacePressureRows(pacePressure);
        setRaceShapeRows(raceShape);
        setSectionalTempoRows(sectionalTempo);
        setActiveSelectorRows(activeSelector);
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
  
  useEffect(() => {
    saveValue("edgeiq_active_tab", tab);
  }, [tab]);

  useEffect(() => {
    saveValue("edgeiq_selected_meeting", selectedMeetingKey);
  }, [selectedMeetingKey]);

  useEffect(() => {
    saveValue("edgeiq_selected_race", selectedRaceKey);
  }, [selectedRaceKey]);

  useEffect(() => {
    saveValue("edgeiq_selected_runner", selectedHorseKey);
  }, [selectedHorseKey]);

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

  const fieldScratchMap = useMemo(() => {
    const map = new Map<string, boolean>();
    for (const r of raceFieldRows) {
      const raceDate = text(r.race_date || r.date);
      const track = text(r.track);
      const raceNo = num(r.race_no) ?? num(r.race_number) ?? 0;
      const horse = text(r.horse);
      const horseKey = compactKey(r.horse_key) || compactKey(horse);
      if (!raceDate || !track || !raceNo || !horseKey) continue;
      if (boolish(r.is_scratched)) {
        map.set(runnerKeyOf(raceDate, track, raceNo, horse, horseKey), true);
      }
    }
    return map;
  }, [raceFieldRows]);

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
        jockey: text(row.jockey) || text(row.rider) || "-",
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
        jockey: text(row.jockey) || text(row.rider) || "-",
        sp: text(row.sp_text) || text(row.starting_price),
        runRating,
        runType,
        isOfficialRace: runType === "RACE",
        fieldSize: text(row.field_size),
        trainer: text(row.trainer) || "-",
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

  const finalRatingsByRunner = useMemo(() => {
    const map = new Map<string, CsvRow>();
    for (const row of finalRatingRows) {
      const raceDate = text(row.race_date);
      const track = text(row.track);
      const raceNo = num(row.race_no) ?? 0;
      const horse = text(row.horse);
      const horseKey = text(row.horse_key);
      map.set(runnerKeyOf(raceDate, track, raceNo, horse, horseKey), row);
    }
    return map;
  }, [finalRatingRows]);

  const executionByRunner = useMemo(() => {
    const map = new Map<string, CsvRow>();
    for (const row of executionEngineRows) {
      const raceDate = text(row.race_date);
      const track = text(row.track);
      const raceNo = num(row.race_no) ?? 0;
      const horse = text(row.horse);
      const horseKey = compactKey(row.horse_key) || compactKey(horse);
      if (!raceDate || !track || !raceNo || !horseKey) continue;
      map.set(runnerKeyOf(raceDate, track, raceNo, horse, horseKey), row);
    }
    return map;
  }, [executionEngineRows]);

  const sectionalTempoByRunner = useMemo(() => {
    const map = new Map<string, CsvRow>();

    for (const row of sectionalTempoRows) {
      const raceDate = text(row.race_date || row.date);
      const track = text(row.track);
      const raceNo = num(row.race_no) ?? num(row.race_number) ?? 0;
      const horse = text(row.horse || row.horse_sectional);
      const horseKey = compactKey(row.horse_key) || compactKey(horse);

      if (!horseKey) continue;

      map.set(runnerKeyOf(raceDate, track, raceNo, horse, horseKey), row);
      map.set(`${raceKeyOf(raceDate, track, raceNo)}|${compactKey(horse)}`, row);
      map.set(`${raceKeyOf(raceDate, track, raceNo)}|${horseKey}`, row);
    }

    return map;
  }, [sectionalTempoRows]);

  const activeRaceMetaByRace = useMemo(() => {
    const map = new Map<string, CsvRow>();
    for (const row of activeSelectorRows) {
      const track = cleanTrack(row.track);
      const raceNo = num(row.race_no) ?? 0;
      if (!track || !raceNo) continue;
      const raceDate = text(row.race_date);
      if (raceDate) map.set(raceKeyOf(raceDate, track, raceNo), row);
      if (!map.has(`${track}|${raceNo}`)) map.set(`${track}|${raceNo}`, row);
    }
    return map;
  }, [activeSelectorRows]);

  function activeRaceMeta(track: unknown, raceNo: unknown, raceDate?: unknown): CsvRow | undefined {
    const date = text(raceDate);
    const trackKey = cleanTrack(track);
    const rn = num(raceNo) ?? 0;
    return (date ? activeRaceMetaByRace.get(raceKeyOf(date, trackKey, rn)) : undefined) ?? activeRaceMetaByRace.get(`${trackKey}|${rn}`);
  }

  function selectorRaceDate(meta: CsvRow | undefined): string {
    const raceTime = text(meta?.race_time);
    if (!raceTime) return "";
    const parsed = new Date(raceTime);
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString().slice(0, 10);
    return raceTime.slice(0, 10);
  }

  function isFakeSelectorTime(meta: CsvRow | undefined): boolean {
    const raceTime = text(meta?.race_time);
    return !raceTime || raceTime.includes("T23:59") || raceTime.includes(" 23:59");
  }

  function selectorSortValue(race: RaceGroup): number {
    const meta = activeRaceMeta(race.track, race.raceNo, race.raceDate);
    const priority = num(meta?.priority_rank);
    const minutes = num(meta?.minutes_to_jump);
    const fakePenalty = isFakeSelectorTime(meta) ? 100000 : 0;
    const liveBoost = text(meta?.is_live).toUpperCase() === "YES" ? -10000 : 0;
    if (priority !== null) return fakePenalty + liveBoost + priority;
    if (minutes !== null) return fakePenalty + liveBoost + Math.max(minutes, -5);
    return fakePenalty + 999999;
  }

  const ratingRows = useMemo<RatingDisplayRow[]>(() => {
    const rows = raceCardRows
      .filter((row) => text(row.horse))
      .map((row, index) => {
        const track = text(row.track);
        const raceNo = num(row.race_no) ?? 0;
        const rowRaceDate = text(row.race_date) || text(row.date);
        const meta = activeRaceMeta(track, raceNo, rowRaceDate);
        if (!isVicTrack(track)) return null;
        const raceDate = rowRaceDate || selectorRaceDate(meta) || new Date().toISOString().slice(0, 10);
        if (!raceDate) return null;
        const horse = text(row.horse);
        const horseKey = compactKey(row.horse_key) || compactKey(horse);
        const matchKey = compactKey(horse);
        const rated = ratedByRunner.get(runnerKeyOf(raceDate, track, raceNo, horse, horseKey));
        const finalRating = finalRatingsByRunner.get(runnerKeyOf(raceDate, track, raceNo, horse, horseKey));
        const execution = executionByRunner.get(runnerKeyOf(raceDate, track, raceNo, horse, horseKey));

        const mergedRow = {
          ...row,
          ...(rated || {}),
          ...(finalRating || {}),
          ...(execution || {}),
        };
        const sectionalTempo = sectionalTempoByRunner.get(runnerKeyOf(raceDate, track, raceNo, horse, horseKey)) ?? sectionalTempoByRunner.get(`${raceKeyOf(raceDate, track, raceNo)}|${matchKey}`);
        const history = historyByHorse.get(horseKey) ?? historyByHorse.get(matchKey) ?? [];
        const runLast5 = lastFiveFromRuns(history);
        const summary = summaryByHorse.get(horseKey) ?? summaryByHorse.get(matchKey);

        const ratedPrice = firstPrice(usablePrice(execution, "fair_price"), usablePrice(rated, "rated_price"), num(row.rated_price));
        const marketPrice = firstPrice(
          num(execution?.live_price),
          num(mergedRow.ui_price),
          num(mergedRow.sportsbet_price),
          num(mergedRow.fixed_win),
          num(finalRating?.fixed_win),
          usablePrice(rated, "fixed_win"),
          num(mergedRow.current_price),
          num(mergedRow.market_price),
          num(mergedRow.live_price)
        );
        const marketStatus = marketPrice ? "OK" : (text(execution?.execution_decision) === "NO_PRICE" ? "NO_PRICE" : text(rated?.market_status) || text(row.market_status) || "MISSING").toUpperCase();
        const marketNote = text(rated?.market_note) || text(row.market_note);
        const highEdgeReview = boolish(rated?.high_edge_review) || boolish(row.high_edge_review);
        const edgePct = marketStatus === "OK" ? num(execution?.edge_pct) ?? num(mergedRow.ui_edge_pct) ?? num(rated?.edge_pct) ?? num(row.edge_pct) : null;

        return {
          id: `${raceDate}|${track}|${raceNo}|${horseKey}|${index}`,
          raceKey: raceKeyOf(raceDate, track, raceNo),
          raceDate,
          track,
          raceNo,
          raceTime: text(mergedRow.race_time) || text(meta?.race_time),
          horse,
          horseKey,
          matchKey,
          horseNo: num(mergedRow.horse_no) ?? num(mergedRow.runner_number) ?? num(mergedRow.saddlecloth),
          jockey: text(mergedRow.jockey) || text(mergedRow.rider) || "-",
          trainer: text(mergedRow.trainer) || "-",
          barrier: num(mergedRow.barrier),
          raceClass: text(mergedRow.race_class_clean) || text(mergedRow.race_class) || text(mergedRow.raceClass) || text(mergedRow["class"]) || "Class unknown",
          distance: num(mergedRow.distance),
          todayTrackCondition: text(mergedRow.track_condition),
          todayRating:
            num(finalRating?.elite_today_rating) ??
            num(row.today_rating) ??
            usablePrice(rated, "today_rating") ??
            summary?.ls1 ??
            summary?.ls3 ??
            summary?.ls5 ??
            summary?.peak,
          winningFigure: num(row.winning_figure),
          ratedPrice: firstPrice(num(execution?.fair_price), num(mergedRow.ui_fair_price), num(finalRating?.elite_rated_price), ratedPrice),
          marketPrice,
          marketStatus,
          marketNote,
          highEdgeReview,
          modelRank: num(row.model_rank) ?? usablePrice(rated, "model_rank"),
          edgePct,
          isScratched:
            fieldScratchMap.get(runnerKeyOf(raceDate, track, raceNo, horse, horseKey)) === true ||
            scratchMap.get(`${normKey(raceDate)}|${normTrack(track)}|${normKey(raceNo)}|${normKey(horseKey)}`) === true ||
            boolish(row.is_scratched) || boolish(finalRating?.is_scratched) || boolish(rated?.is_scratched),
          gearChanges:
            text(row.gear_changes) ||
            text(row.gear_change) ||
            text(row.gear) ||
            text(row.gear_changes_short) ||
            "-",
          flucs:
            text(mergedRow.flucs) ||
            text(mergedRow.market_fluctuations) ||
            text(mergedRow.price_fluctuations) ||
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
          formRating: num(finalRating?.form_rating),
          baseLast5: num(finalRating?.base_last5),
          contextLast5: num(finalRating?.context_last5),
          classAdj: num(finalRating?.class_adj),
          distanceAdj: num(finalRating?.distance_adj),
          speedAdj: num(finalRating?.speed_adj),
          recencyAdj: num(finalRating?.recency_adj),
          momentumAdj: num(finalRating?.momentum_adj),
          weightedRecentRating: num(finalRating?.weighted_recent_rating),
          recentSimpleAvg: num(finalRating?.recent_simple_avg),
          runsUsed: num(finalRating?.runs_used),
          lengthsPointScale: num(finalRating?.lengths_point_scale),
          tripAdjPoints: num(finalRating?.trip_adj_points),
          weightAdjPoints: num(finalRating?.weight_adj_points),
          jockeyAdjPoints: num(finalRating?.jockey_adj_points),
          jockeyAdjLabel: text(finalRating?.jockey_adj_label),
          jockeyStatRatingPoints: num(finalRating?.jockey_stat_rating_points),
          jockeyTier: text(finalRating?.jockey_tier),
          jockeyRecentWinSr: num(finalRating?.jockey_recent_win_sr),
          jockeyRecentPlaceSr: num(finalRating?.jockey_recent_place_sr),
          jockeyActualMinusExpected: num(finalRating?.jockey_actual_minus_expected),
          jockeyRoiLast100: num(finalRating?.jockey_roi_last_100),
          jockeyBestTrack: text(finalRating?.jockey_best_track),
          jockeyBestDistanceBand: text(finalRating?.jockey_best_distance_band),
          jockeyBestTrainerCombo: text(finalRating?.jockey_best_trainer_combo),
          manualJockeyAdjPoints: num(finalRating?.manual_jockey_adj_points),
          trainerAdjPoints: num(finalRating?.trainer_adj_points),
          trainerAdjLabel: text(finalRating?.trainer_adj_label),
          trainerTier: text(finalRating?.trainer_tier),
          trainerRecentWinSr: num(finalRating?.trainer_recent_win_sr),
          trainerRoiLast100: num(finalRating?.trainer_roi_last_100),
          trainerActualMinusExpected: num(finalRating?.trainer_actual_minus_expected),
          trainerBestTrack: text(finalRating?.trainer_best_track),
          trainerBestDistanceBand: text(finalRating?.trainer_best_distance_band),
          trainerBestCondition: text(finalRating?.trainer_best_condition),
          trainerBestClassBand: text(finalRating?.trainer_best_class_band),
          comboAdjPoints: num(finalRating?.combo_adj_points),
          comboAdjLabel: text(finalRating?.combo_adj_label),
          comboRides: num(finalRating?.combo_rides),
          comboWinSr: num(finalRating?.combo_win_sr),
          comboActualMinusExpected: num(finalRating?.combo_actual_minus_expected),
          comboRoi: num(finalRating?.combo_roi),
          totalConnectionsAdj: num(finalRating?.total_connections_adj),
          handicapperAdjTotal: num(finalRating?.handicapper_adj_total),
          handicapperRating: num(finalRating?.handicapper_rating),
          eliteTodayRatingBeforeHandicapper: num(finalRating?.elite_today_rating_before_handicapper),
          handicapperContextFlags: text(finalRating?.handicapper_context_flags),
          rawEliteTodayRating: num(finalRating?.raw_elite_today_rating),
          calibratedTodayRating: num(finalRating?.calibrated_today_rating),
          calibrationAdjPoints: num(finalRating?.calibration_adj_points),
          calibrationLabel: text(finalRating?.calibration_label),
          modelConfidenceScore: num(finalRating?.model_confidence_score),
          priceConfidenceBand: text(finalRating?.price_confidence_band),
          fakeOverlayRisk: text(finalRating?.fake_overlay_risk),
          fakeOverlayReason: text(finalRating?.fake_overlay_reason),

          sectional_profile: text(sectionalTempo?.sectional_profile),
          sectional_edge_tier: text(sectionalTempo?.sectional_edge_tier),
          sectional_strength_score: num(sectionalTempo?.sectional_strength_score),
          sectional_overlay_signal: text(sectionalTempo?.sectional_overlay_signal),
          sectional_confidence: text(sectionalTempo?.sectional_confidence),
          tempo_role: text(sectionalTempo?.tempo_role),
          projected_tempo_shape: text(sectionalTempo?.projected_tempo_shape),
          pace_collapse_risk: text(sectionalTempo?.pace_collapse_risk),
          tempo_fit: text(sectionalTempo?.tempo_fit),
          tempo_edge_score: num(sectionalTempo?.tempo_edge_score),
          tempo_edge_grade: text(sectionalTempo?.tempo_edge_grade),
          sectional_weapon_score: num(sectionalTempo?.sectional_weapon_score),
          late_power_index: num(sectionalTempo?.late_power_index),
          burst_index: num(sectionalTempo?.burst_index),
          sustain_index: num(sectionalTempo?.sustain_index),
          fatigue_risk_index: num(sectionalTempo?.fatigue_risk_index),
          run_style_cluster: text(sectionalTempo?.run_style_cluster),

          silkUrl: text(mergedRow.silkUrl) || text(mergedRow.silk_url) || text(mergedRow.mobile_silk_image) || silkByHorse.get(horseKey) || silkByHorse.get(matchKey) || defaultSilkUrl(),
        };
      });

    const grouped = new Map<string, RatingDisplayRow[]>();
    for (const row of rows) {
      if (!row) continue;
      if (!grouped.has(row.raceKey)) grouped.set(row.raceKey, []);
      grouped.get(row.raceKey)!.push(row);
    }

    return [...grouped.values()]
      .flatMap(rankRows)
      .filter((row) => isVicTrack(row.track));
  }, [raceCardRows, activeSelectorRows, activeRaceMetaByRace, ratedByRunner, finalRatingsByRunner, executionByRunner, sectionalTempoByRunner, historyByHorse, summaryByHorse, silkByHorse, scratchMap, fieldScratchMap]);

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
          raceTime: first.raceTime,
          raceClass: first.raceClass || "Class unknown",
          distance: first.distance,
          winningFigure: first.winningFigure,
          todayTrackCondition: first.todayTrackCondition,
          rows,
        };
      })
      .sort((a, b) => selectorSortValue(a) - selectorSortValue(b) || a.raceDate.localeCompare(b.raceDate) || a.track.localeCompare(b.track) || a.raceNo - b.raceNo);
  }, [ratingRows, activeSelectorRows]);

  const meetings = useMemo<MeetingGroup[]>(() => {
    const grouped = new Map<string, MeetingGroup>();

    const sourceRows =
      raceCardRows.length
        ? raceCardRows
        : executionEngineRows.length
          ? executionEngineRows
          : ratedRows;

    for (const row of sourceRows) {
      const raceDate = text(row.race_date) || text(row.raceDate) || text(row.date);
      const track = text(row.track) || text(row.meeting) || text(row.meeting_name);
      const raceNo = num(row.race_no) ?? num(row.raceNo) ?? num(row.race_number) ?? 0;

      if (!raceDate || !track || !raceNo) continue;

      const meetingKey = text(row.meeting_key) || meetingKeyOf(raceDate, track);
      const raceKey = text(row.race_key) || `${meetingKey}_R${raceNo}`;

      if (!grouped.has(meetingKey)) {
        grouped.set(meetingKey, {
          meetingKey,
          raceDate,
          track,
          races: [],
        });
      }

      const meeting = grouped.get(meetingKey)!;

      if (!meeting.races.some((race) => race.key === raceKey)) {
        meeting.races.push({
          key: raceKey,
          raceDate,
          track,
          raceNo,
          raceTime: text(row.race_time) || text(row.raceTime),
          raceClass: text(row.race_class) || text(row.raceClass) || "Class unknown",
          distance: num(row.distance) ?? 0,
          winningFigure: num(row.winningFigure),
          todayTrackCondition: text(row.track_condition) || text(row.todayTrackCondition),
          rows: [],
        });
      }
    }

    return [...grouped.values()]
      .map((meeting) => ({
        ...meeting,
        races: [...meeting.races].sort(
          (a, b) =>
            selectorSortValue(a) - selectorSortValue(b) ||
            a.raceNo - b.raceNo
        ),
      }))
      .sort(
        (a, b) =>
          selectorSortValue(a.races[0]) - selectorSortValue(b.races[0]) ||
          a.raceDate.localeCompare(b.raceDate) ||
          a.track.localeCompare(b.track)
      );
  }, [raceCardRows, executionEngineRows, ratedRows]);

  useEffect(() => {
    console.log("EDGEIQ DATA COUNTS", {
      universeRows: raceCardRows.length,
      selectorRows: activeSelectorRows.length,
      executionRows: executionEngineRows.length,
      meetingCount: meetings.length,
      raceCount: raceGroups.length,
      selectedMeetingKey,
      selectedRaceKey,
    });
  }, [raceCardRows.length, activeSelectorRows.length, executionEngineRows.length, meetings.length, raceGroups.length, selectedMeetingKey, selectedRaceKey]);

  useEffect(() => {
    if (!meetings.length) return;

    const selectedMeetingExists = meetings.some((meeting) => meeting.meetingKey === selectedMeetingKey);
    const selectedRaceExists = meetings.some((meeting) =>
      meeting.races.some((race) => race.key === selectedRaceKey)
    );

    if (selectedMeetingExists && selectedRaceExists) {
      initialSelectionDone.current = true;
      return;
    }

    const focus =
      activeSelectorRows.find((row) => text(row.default_ui_focus).toUpperCase() === "YES") ??
      activeSelectorRows.find((row) => text(row.day_bucket).toUpperCase() === "TODAY") ??
      activeSelectorRows[0];

    const focusTrack = cleanTrack(focus?.track);
    const focusDate = text(focus?.race_date);
    const focusRaceNo = num(focus?.race_no) ?? 0;

    const fallbackMeeting =
      meetings.find((meeting) => meeting.raceDate === focusDate && cleanTrack(meeting.track) === focusTrack) ??
      meetings.find((meeting) => cleanTrack(meeting.track) === focusTrack) ??
      meetings[0];

    const fallbackRace =
      fallbackMeeting.races.find((race) => race.raceNo === focusRaceNo) ??
      fallbackMeeting.races[0];

    if (!selectedMeetingExists) {
      setSelectedMeetingKey(fallbackMeeting.meetingKey);
    }

    if (!selectedRaceExists) {
      setSelectedRaceKey(fallbackRace?.key ?? "");
    }

    initialSelectionDone.current = true;
  }, [meetings, activeSelectorRows, selectedMeetingKey, selectedRaceKey]);

  const currentMeeting = useMemo(
    () => meetings.find((meeting) => meeting.meetingKey === selectedMeetingKey) ?? meetings[0] ?? null,
    [meetings, selectedMeetingKey]
  );

  const activeSelectorFocus = useMemo(() => {
    const focus = activeSelectorRows.find((row) => text(row.default_ui_focus).toUpperCase() === "YES") ?? activeSelectorRows[0] ?? null;
    if (!focus) return null;
    return {
      raceDate: text(focus.race_date),
      track: text(focus.track),
      normalizedTrack: cleanTrack(focus.track),
      raceNo: num(focus.race_no) ?? 0,
      raceState: text(focus.race_state),
    };
  }, [activeSelectorRows]);

  const activeSelectorMismatch = useMemo(() => {
    if (!activeSelectorFocus || !meetings.length) return false;
    return !meetings.some(
      (meeting) =>
        meeting.raceDate === activeSelectorFocus.raceDate
        && cleanTrack(meeting.track) === activeSelectorFocus.normalizedTrack
        && meeting.races.some((race) => race.raceNo === activeSelectorFocus.raceNo),
    );
  }, [activeSelectorFocus, meetings]);

  useEffect(() => {
    if (!currentMeeting || !initialSelectionDone.current) return;
    const raceStillExists = currentMeeting.races.some((race) => race.key === selectedRaceKey);
    if (!selectedRaceKey || !raceStillExists) {
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

  const currentRace = useMemo(() => {
    const selected = currentMeeting?.races.find((race) => race.key === selectedRaceKey);
    if (selected?.rows.length) return selected;
    const meetingFallback = currentMeeting?.races.find((race) => race.rows.length);
    if (meetingFallback) return meetingFallback;
    return raceGroups.find((race) => race.rows.length) ?? null;
  }, [currentMeeting, selectedRaceKey, raceGroups]);


  const executionFeedRows = useMemo(() => {
    return (currentRace?.rows ?? []).map((row) => ({
      horse: row.horse,
      track: row.track,
      race_no: String(row.raceNo ?? ""),
      race_time: row.raceTime ?? "",

      sportsbet_price:
        row.marketPrice !== null && row.marketPrice !== undefined
          ? String(row.marketPrice)
          : "",

      rated_price:
        row.ratedPrice !== null && row.ratedPrice !== undefined
          ? String(row.ratedPrice)
          : "",

      overlay_pct:
        row.edgePct !== null && row.edgePct !== undefined
          ? String(row.edgePct)
          : "",

      execution_action: runnerDecision(row),

      jockey: row.jockey ?? "",
      trainer: row.trainer ?? "",
      mobile_silk_image: row.silkUrl ?? "",

      sectional_profile: row.sectional_profile ?? "",
      sectional_edge_tier: row.sectional_edge_tier ?? "",

      sectional_strength_score:
        row.sectional_strength_score !== null &&
        row.sectional_strength_score !== undefined
          ? String(row.sectional_strength_score)
          : "",

      sectional_overlay_signal: row.sectional_overlay_signal ?? "",
      sectional_confidence: row.sectional_confidence ?? "",

      tempo_role: row.tempo_role ?? "",
      projected_tempo_shape: row.projected_tempo_shape ?? "",
      pace_collapse_risk: row.pace_collapse_risk ?? "",
      tempo_fit: row.tempo_fit ?? "",

      tempo_edge_score:
        row.tempo_edge_score !== null &&
        row.tempo_edge_score !== undefined
          ? String(row.tempo_edge_score)
          : "",

      tempo_edge_grade: row.tempo_edge_grade ?? "",

      sectional_weapon_score:
        row.sectional_weapon_score !== null &&
        row.sectional_weapon_score !== undefined
          ? String(row.sectional_weapon_score)
          : "",

      late_power_index:
        row.late_power_index !== null &&
        row.late_power_index !== undefined
          ? String(row.late_power_index)
          : "",

      burst_index:
        row.burst_index !== null &&
        row.burst_index !== undefined
          ? String(row.burst_index)
          : "",

      sustain_index:
        row.sustain_index !== null &&
        row.sustain_index !== undefined
          ? String(row.sustain_index)
          : "",

      fatigue_risk_index:
        row.fatigue_risk_index !== null &&
        row.fatigue_risk_index !== undefined
          ? String(row.fatigue_risk_index)
          : "",

      run_style_cluster: row.run_style_cluster ?? "",
    }));
  }, [currentRace]);


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

    const activeTrack = cleanTrack(currentRace.track);
    const activeRaceNo = currentRace.raceNo;

    const fieldByHorse = new Map<string, any>();

    currentRace.rows.forEach((row) => {
      const key = compactKey(row.horse);
      if (key) fieldByHorse.set(key, row);
    });

    return speedRows
      .filter((row) => {
        const rowTrack = cleanTrack(row.track ?? row.meeting ?? "");
        const rowRaceNo = num(row.race_no ?? row.raceNumber ?? row.race_no_text ?? row.race ?? "");

        const rowDate = text(row.race_date ?? row.date ?? "");
        const dateOk = !rowDate || rowDate === currentRace.raceDate;

        return (
          dateOk &&
          rowTrack === activeTrack &&
          (rowRaceNo ?? 0) === activeRaceNo
        );
      })
      .map((row) => {
        const fieldRunner =
          fieldByHorse.get(compactKey(row.horse)) ??
          fieldByHorse.get(compactKey(row.horse_name)) ??
          null;

        const displayHorse = text(fieldRunner?.horse ?? row.horse ?? row.horse_name);

        return {
          ...row,
          horse: displayHorse,
          saddlecloth: text(
            fieldRunner?.saddlecloth ??
            fieldRunner?.number ??
            fieldRunner?.tab_no ??
            row.saddlecloth ??
            row.number ??
            row.tab_no
          ),
          jockey: text(fieldRunner?.jockey ?? row.jockey),
          barrier: text(row.barrier ?? fieldRunner?.barrier ?? fieldRunner?.barrier_num),
          silk_url: silkByHorse.get(compactKey(displayHorse)) ?? row.silk_url ?? row.silkUrl ?? "",
          is_scratched: text(fieldRunner?.is_scratched ?? fieldRunner?.scratched ?? row.is_scratched ?? row.scratched ?? ""),
        };
      });
  }, [speedRows, currentRace, silkByHorse]);

  const currentPacePressureRows = useMemo(() => {
    if (!currentRace) return [];
    return pacePressureRows.filter((row) =>
      text(row.race_date) === currentRace.raceDate &&
      cleanTrack(row.track) === cleanTrack(currentRace.track) &&
      (num(row.race_no) ?? 0) === currentRace.raceNo
    );
  }, [pacePressureRows, currentRace]);


  const currentRaceShapeRow = useMemo(() => {
    if (!currentRace) return null;

    return (
      raceShapeRows.find(
        (row) =>
          text(row.race_date) === currentRace.raceDate &&
          cleanTrack(row.track) === cleanTrack(currentRace.track) &&
          (num(row.race_no) ?? 0) === currentRace.raceNo
      ) ?? null
    );
  }, [raceShapeRows, currentRace]);


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

  const currentRaceStandard = useMemo(() => {
    if (!currentRace) return null;
    return raceStandardRows.find((row) =>
      text(row.race_date) === currentRace.raceDate &&
      cleanTrack(row.track) === cleanTrack(currentRace.track) &&
      (num(row.race_no) ?? 0) === currentRace.raceNo
    ) ?? null;
  }, [currentRace, raceStandardRows]);
  const currentRaceRatingTarget = useMemo(() => {
    if (!currentRace) return null;
    return raceRatingTargetRows.find((row) =>
      text(row.race_date) === currentRace.raceDate &&
      cleanTrack(row.track) === cleanTrack(currentRace.track) &&
      (num(row.race_no) ?? 0) === currentRace.raceNo
    ) ?? null;
  }, [currentRace, raceRatingTargetRows]);
  const topRated = currentRace?.rows.filter((row) => !row.isScratched).sort((a, b) => (a.modelRank ?? 999) - (b.modelRank ?? 999))[0] ?? null;
  const upcomingRaces = useMemo(() => {
    return raceGroups
      .map((race) => ({ race, mins: minutesToJump(race.rows[0], race) }))
      .filter((item) => item.mins === null || item.mins >= -5)
      .sort((a, b) => (a.mins ?? 99999) - (b.mins ?? 99999))
      .slice(0, 8);
  }, [raceGroups]);

  const strongestRaceOverlays = useMemo(() => {
    return (currentRace?.rows ?? [])
      .filter((row) => !row.isScratched)
      .map((row) => ({ row, edge: saneOverlay(row.edgePct), action: runnerDecision(row) }))
      .filter((item) => item.edge !== null && item.action !== "SUPPRESSED")
      .sort((a, b) => (b.edge ?? -999) - (a.edge ?? -999))
      .slice(0, 10);
  }, [currentRace]);

  const snapshotAgeDays = useMemo(() => {
    if (!currentRace?.raceDate) return null;
    const snapshotDate = new Date(`${currentRace.raceDate}T00:00:00`);
    if (Number.isNaN(snapshotDate.getTime())) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    snapshotDate.setHours(0, 0, 0, 0);
    return Math.floor((today.getTime() - snapshotDate.getTime()) / 86400000);
  }, [currentRace?.raceDate]);

  const staleSnapshot = snapshotAgeDays !== null && snapshotAgeDays > 0;
  const marketStateLabel = !currentRace ? "NO FEED" : staleSnapshot ? "STALE" : raceStatusLabel(currentRace);
  const marketStateContext = !currentRace
    ? "no selected race"
    : staleSnapshot
      ? `latest race date ${displayDate(currentRace.raceDate)}`
      : "live polling active";
  const settlementAuditSummary = resultRows.length ? `${resultRows.length} audit rows` : "No audit rows";
  const selectorFeedSummary = activeSelectorRows.length ? `${activeSelectorRows.length} selector rows` : "Selector unavailable";
  const scratchFeedSummary = scratchRows.length ? `${scratchRows.length} scratch / gear rows` : "No scratchings loaded";
  const surfaceLabel = staleSnapshot ? "EDGEIQ RACING - HISTORICAL SNAPSHOT" : "EDGEIQ RACING - LIVE INTELLIGENCE";

  return (
    <>      <EdgeRaceTicker meetings={meetings} currentRaceKey={currentRace?.key ?? ""} />      <div className="edgeiq-racing-app ert-shell min-h-screen bg-[#07101b] text-[#dbe7f3]">
      <div className="mx-auto max-w-[1760px] px-3 pb-3 pt-14 sm:px-4 sm:pt-3">
        <header className="rounded-2xl border border-slate-700/60 bg-gradient-to-r from-[#0b1220] to-[#070d18] text-white shadow-xl">
          <div className="grid gap-2 border-b border-[#263a53] px-3 py-2 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-end">
            <div>
              <div className="edgeiq-racing-brand-kicker text-[10px] font-semibold uppercase tracking-[0.2em] text-[#f05252]">EDGEiQ RACING</div>
              <div className="mt-0.5 text-[18px] font-semibold tracking-tight">Racing Intelligence Terminal</div>
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
                          ? "border-emerald-400/40 bg-emerald-500/10 text-white"
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
                <span>{displayUserLocalRaceTime(currentRace.rows[0], currentRace)}</span>
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

        {activeSelectorMismatch && activeSelectorFocus ? (
          <div className="edgeiq-terminal-banner bad">
            <strong>Feed mismatch</strong>
            <span>
              Active selector points to {activeSelectorFocus.track} R{activeSelectorFocus.raceNo} on {displayDate(activeSelectorFocus.raceDate)},
              but the loaded meeting universe is still showing archived card data. Treat this screen as display-only until feeds realign.
            </span>
          </div>
        ) : null}

        <div className="mt-3">
          <TerminalNav
            activeTab={tab as any}
            onChange={(next) => setTab(next as TabKey)}
          />
        </div>

      <main className="mt-3">
        

          {loading ? (
            <div className="border border-[#ccd3da] bg-[#07101d] px-4 py-12 text-[14px] text-[#5b6570]">Loading local race files...</div>
          ) : error ? (
            <div className="border border-[#a64b4b] bg-[#07101d] px-4 py-12 text-[14px] text-[#8f3030]">{error}</div>
          ) : tab === "OVERVIEW" ? (            <OverviewTab
              staleSnapshot={staleSnapshot}
              upcomingRaces={upcomingRaces}
              meetings={meetings}
              strongestRaceOverlays={strongestRaceOverlays}
              marketStateLabel={marketStateLabel}
              settlementAuditSummary={settlementAuditSummary}
              scratchFeedSummary={scratchFeedSummary}
              selectorFeedSummary={selectorFeedSummary}
              displayDate={displayDate}
              setSelectedMeetingKey={setSelectedMeetingKey}
              setSelectedRaceKey={setSelectedRaceKey}
              setSelectedHorseKey={setSelectedHorseKey}
              setTab={setTab}
            />
          ) : tab === "INTELLIGENCE" ? (
            <RaceIntelligenceScreen
              currentRace={currentRace}
              currentMeeting={currentMeeting}
              currentSpeedRows={currentSpeedRows}
              currentPacePressureRows={currentPacePressureRows}
              currentRaceShapeRow={currentRaceShapeRow}
              trackBiasRows={trackBiasRows}
              selectedRunner={selectedRunner}
              selectedHistory={selectedHistory}
              selectedFullCareer={selectedFullCareer}
              selectedSummary={selectedSummary}
              selectedCareerStats={selectedCareerStats}
              allHistoryRows={allHistoryRows}
              currentRaceStandard={currentRaceStandard}
              currentRaceRatingTarget={currentRaceRatingTarget}
              executionFeedRows={executionFeedRows}
              setSelectedHorseKey={setSelectedHorseKey}
              compactKey={compactKey}
            />          ) : tab === "MARKET" ? (
            <MarketTab selectedMeetingKey={selectedMeetingKey} selectedRaceKey={selectedRaceKey} />
          ) : tab === "RESULTS" ? (
            <ResultsTab />
          ) : (
            <div className="edgeiq-no-live">NO LIVE MARKET DATA</div>
          )}
        </main>

        <div className="mt-2 text-[10px] text-[#6d7680]">Data: {displayDate(currentRace?.raceDate ?? "")} | local CSV files</div>
      </div>
    </div>
    </>
  );
}







