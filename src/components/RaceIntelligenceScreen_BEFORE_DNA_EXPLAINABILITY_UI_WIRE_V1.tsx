import React, { useEffect, useMemo, useState } from "react";

type Row = Record<string, string>;

const FILES = {
  runnerBoard: "/data/edgeiq_live_runner_board_v1.csv",
  runnerIntel: "/data/edgeiq_runner_intelligence_v1.csv",
  v8: "/data/edgeiq_live_v8_candidate_display_feed_v1.csv",
  betQuality: "/data/edgeiq_live_bet_quality_v1_1.csv",
  reliability: "/data/edgeiq_live_race_reliability_v1_feed.csv",
  intelligenceCards: "/data/edgeiq_race_intelligence_cards_v1.csv",
  briefing: "/data/edgeiq_race_briefing_v1.csv",
  marketIntel: "/data/edgeiq_market_intelligence_v1.csv",
  verdict: "/data/edgeiq_race_verdict_v1.csv",
  trackIntel: "/data/edgeiq_track_intelligence_card_v1.csv",
  horseDrawer: "/data/edgeiq_horse_intelligence_drawer_current.csv",
  runnerDnaDrawer: "/data/edgeiq_runner_dna_drawer_feed_v2.csv",
  factorScorecard: "/data/edgeiq_live_runner_factor_scorecard_v2.csv",
  limitedData: "/data/edgeiq_limited_data_market_adjusted_v1.csv",
  intelligenceScore: "/data/edgeiq_live_intelligence_score_v1.csv",
};

type Props = {
  selectedTrack?: string;
  selectedRaceNo?: number | string;
  currentRace?: any;
  [key: string]: any;
};

type EnrichedRunner = {
  row: Row;
  runnerIntel?: Row;
  v8?: Row;
  bet?: Row;
  rel?: Row;
  drawer?: Row;
  limited?: Row;
  intel?: Row;
  factorRows?: Row[];
};

function text(v: unknown): string {
  if (v === null || v === undefined) return "";
  return String(v).trim();
}

function num(v: unknown): number | null {
  const s = text(v).replace(/[$,%]/g, "");
  if (!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function cleanTrack(v: unknown): string {
  return text(v).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function cleanHorse(v: unknown): string {
  return text(v)
    .toUpperCase()
    .replace(/\([^)]*\)/g, "")
    .replace(/[^A-Z0-9]/g, "");
}

function cleanHorseLoose(v: unknown): string {
  return cleanHorse(v).replace(/(NZ|GB|IRE|FR|USA|JPN|AUS)$/g, "");
}

function raceDate(row: Row): string {
  return text(row.race_date || row.meeting_date || row.date || row.raceDate);
}

function track(row: Row): string {
  return text(row.track || row.meeting || row.meeting_name);
}

function raceNo(row: Row): string {
  return text(row.race_no || row.raceNo || row.race_number || row.race);
}

function horse(row: Row): string {
  return text(row.horse || row.horseName || row.runner || row.runner_name);
}

function distance(row: Row): string {
  const d = text(row.distance || row.race_distance || row.dist);
  return d ? `${d}m`.replace("mm", "m") : "—";
}

function raceClass(row: Row): string {
  return text(row.race_class_clean || row.race_class || row.class || row.raceClass || row.grade || row.race_grade) || "—";
}

function trackCondition(row: Row): string {
  return text(row.track_condition || row.condition || row.going || row.trackCondition) || "—";
}


function money(v: number | null): string {
  if (v === null || !Number.isFinite(v) || v <= 0) return "—";
  return `$${v.toFixed(2)}`;
}

function pct(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "—";
  return `${v.toFixed(1)}%`;
}

function integer(v: string): number | null {
  const match = text(v).match(/-?\d+/);
  return match ? Number(match[0]) : null;
}

function signed(v: number | null, digits = 1): string {
  if (v === null || !Number.isFinite(v)) return "—";
  const prefix = v > 0 ? "+" : "";
  return `${prefix}${v.toFixed(digits)}`;
}

function csvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let quoted = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    const next = line[i + 1];

    if (ch === '"' && quoted && next === '"') {
      cur += '"';
      i += 1;
    } else if (ch === '"') {
      quoted = !quoted;
    } else if (ch === "," && !quoted) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }

  out.push(cur);
  return out;
}

function parseCsv(raw: string): Row[] {
  const lines = raw.replace(/^\uFEFF/, "").split(/\r?\n/).filter((x) => x.trim());
  if (!lines.length) return [];
  if (lines[0].trim().startsWith("<!doctype html>")) return [];

  const headers = csvLine(lines[0]).map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const cells = csvLine(line);
    const row: Row = {};
    headers.forEach((h, i) => {
      row[h] = cells[i] ?? "";
    });
    return row;
  });
}

async function loadCsv(path: string): Promise<Row[]> {
  try {
    const res = await fetch(`${path}?v=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) return [];
    return parseCsv(await res.text());
  } catch {
    return [];
  }
}

function firstNum(row: Row | undefined, keys: string[]): number | null {
  if (!row) return null;
  for (const key of keys) {
    const value = num(row[key]);
    if (value !== null) return value;
  }
  return null;
}

function firstText(row: Row | undefined, keys: string[], fallback = "—"): string {
  if (!row) return fallback;
  for (const key of keys) {
    const value = text(row[key]);
    if (value) return value;
  }
  return fallback;
}

function sameRace(a: Row, b: Row): boolean {
  const aDate = raceDate(a);
  const bDate = raceDate(b);
  if (aDate && bDate && aDate !== bDate) return false;
  return cleanTrack(track(a)) === cleanTrack(track(b)) && raceNo(a) === raceNo(b);
}

function findRaceSidecar(rows: Row[], base: Row): Row | undefined {
  return rows.find((row) => sameRace(row, base));
}

function band(row: Row | undefined, keys: string[], fallback = "—"): string {
  return firstText(row, keys, fallback).replace(/_/g, " ").toUpperCase();
}

function customerLimitedDecisionLabel(value: string): string {
  return value.toUpperCase() === "MODEL" ? "MODEL EDGE" : value;
}

function humanTrackStyle(style: string): string {
  const value = style.toUpperCase().replace(/_/g, " ").trim();
  if (!value || value === "—" || value === "NO PROFILE") return "runners without a clear historical pattern";
  if (value.includes("MIDFIELD")) return "runners settling midfield";
  if (value.includes("ON PACE")) return "on-pace runners";
  if (value.includes("LEADER")) return "leaders";
  if (value.includes("BACKMARKER")) return "backmarkers";
  return value.toLowerCase();
}

function humanBarrierPhrase(barrier: string): string {
  const value = barrier.toUpperCase().replace(/_/g, " ").trim();
  if (!value || value === "—") return "";
  if (value.includes("MIDDLE")) return "middle barriers";
  if (value.includes("INSIDE") || value.includes("LOW")) return "inside barriers";
  if (value.includes("WIDE") || value.includes("OUTSIDE") || value.includes("HIGH")) return "wide barriers";
  return value.toLowerCase();
}

function humanMovementPhrase(movement: string): string {
  const value = movement.toUpperCase().replace(/_/g, " ").trim();
  if (!value || value === "—") return "";
  if (value === "HOLDS POSITION") return "holding their position in the run";
  if (value.includes("IMPROVE")) return "improving through the run";
  if (value.includes("DROP")) return "drifting back through the run";
  return value.toLowerCase();
}

function trackDnaHeadline(style: string): string {
  const value = style.toUpperCase().replace(/_/g, " ").trim();
  if (!value || value === "—" || value === "NO PROFILE") return "No clear historical profile";
  return `Favours ${humanTrackStyle(style)}`;
}

function raceClarityNarrative(value: string): string {
  const upper = value.toUpperCase();
  if (upper.includes("WIDE OPEN")) return "highly competitive";
  if (upper.includes("CLEAR")) return "more straightforward";
  if (upper.includes("BALANCED")) return "balanced";
  if (upper.includes("OPEN")) return "competitive";
  return "live and competitive";
}

function buildBriefingNarrative(
  clarity: string,
  tempo: string,
  confidence: string,
  topWinChance: string,
  topWinFair: number | null,
  bestValue: string,
  bestValueEdge: number | null,
): string {
  const parts: string[] = [];
  parts.push(`This race looks ${raceClarityNarrative(clarity)}.`);
  if (tempo !== "—") parts.push(`Tempo projects as ${tempo}.`);
  if (confidence !== "—") parts.push(`Overall confidence sits at ${confidence}.`);

  if (topWinChance && bestValue && topWinChance === bestValue) {
    const fairText = topWinFair !== null ? ` at an EDGEiQ fair of ${money(topWinFair)}` : "";
    const edgeText = bestValueEdge !== null ? ` with ${signed(bestValueEdge)}% edge` : "";
    parts.push(`${topWinChance} profiles as both the top win chance${fairText}, with current value also sitting there${edgeText}.`);
  } else {
    if (topWinChance) {
      const fairText = topWinFair !== null ? ` at an EDGEiQ fair of ${money(topWinFair)}` : "";
      parts.push(`${topWinChance} profiles as the top win chance${fairText}.`);
    }
    if (bestValue) {
      const edgeText = bestValueEdge !== null ? ` at ${signed(bestValueEdge)}% edge` : "";
      parts.push(`Best current value sits with ${bestValue}${edgeText}.`);
    }
  }

  return parts.join(" ");
}

function bandColor(value: string): string {
  const v = value.toUpperCase();
  if (v.includes("VERY CLEAR") || v === "CLEAR" || v.includes("VERY HIGH") || v === "HIGH") return "#3ee68f";
  if (v.includes("BALANCED") || v.includes("MEDIUM") || v.includes("MODERATE") || v.includes("EVEN")) return "#f5c451";
  if (v.includes("OPEN") || v === "LOW" || v.includes("SLOW")) return "#fb923c";
  if (v.includes("WIDE") || v.includes("VERY LOW") || v.includes("FAST") || v.includes("EXTREME")) return "#f87171";
  return "#cbd5e1";
}

function sameRunner(a: Row, b: Row): boolean {
  const aDate = raceDate(a);
  const bDate = raceDate(b);
  if (aDate && bDate && aDate !== bDate) return false;
  if (cleanTrack(track(a)) !== cleanTrack(track(b))) return false;
  if (raceNo(a) !== raceNo(b)) return false;

  const ah = [
    cleanHorse(a.horse_key),
    cleanHorse(a.horse_canon),
    cleanHorse(horse(a)),
    cleanHorseLoose(a.horse_key),
    cleanHorseLoose(a.horse_canon),
    cleanHorseLoose(horse(a)),
  ].filter(Boolean);

  const bh = [
    cleanHorse(b.horse_key),
    cleanHorse(b.horse_canon),
    cleanHorse(horse(b)),
    cleanHorseLoose(b.horse_key),
    cleanHorseLoose(b.horse_canon),
    cleanHorseLoose(horse(b)),
  ].filter(Boolean);

  return ah.some((x) => bh.includes(x));
}

function findSidecar(rows: Row[], base: Row): Row | undefined {
  return rows.find((row) => sameRunner(row, base));
}

function saddle(row: Row): number {
  return firstNum(row, ["horse_no", "runner_no", "saddlecloth", "number", "no"]) ?? 999;
}

function barrier(row: Row): string {
  const b = firstNum(row, ["barrier", "bar"]);
  return b === null ? "—" : String(Math.trunc(b));
}

function fairPrice(row: Row, bet?: Row): number | null {
  return firstNum(row, ["display_fair_price", "fair_price", "rated_price", "ui_fair_price", "edgeiq_price"]) ??
    firstNum(bet, ["bet_quality_fair_price_used_v1_1", "fair_price"]);
}

function livePrice(row: Row, bet?: Row): number | null {
  return firstNum(row, ["display_live_price", "live_price", "tab_fixed_win", "sportsbet_price", "fixed_win", "market_price"]) ??
    firstNum(bet, ["bet_quality_live_price_used_v1_1", "live_price"]);
}

function edgePct(row: Row, bet?: Row): number | null {
  const direct =
    firstNum(row, ["display_edge_pct", "edge_pct", "ui_edge_pct"]) ??
    firstNum(bet, ["bet_quality_overlay_pct_v1_1", "edge_pct"]);

  if (direct !== null) return direct;

  const live = livePrice(row, bet);
  const fair = fairPrice(row, bet);
  if (live && fair) return ((live / fair) - 1) * 100;
  return null;
}

function winPct(row: Row, bet?: Row): number | null {
  const p = firstNum(row, ["v3_probability", "edgeiq_probability", "rated_probability", "win_probability"]) ??
    firstNum(bet, ["v3_probability"]);

  if (p !== null && p > 0) return p > 1 ? p : p * 100;

  const fair = fairPrice(row, bet);
  return fair && fair > 0 ? 100 / fair : null;
}

function v8Fair(v8?: Row, bet?: Row): number | null {
  return firstNum(v8, ["v8_candidate_price_display", "v8_interaction_candidate_price"]) ??
    firstNum(bet, ["v8_candidate_price_display"]);
}

function v8Conf(v8?: Row, bet?: Row): string {
  return firstText(v8, ["brc_match_level_v8", "v8_confidence"], firstText(bet, ["brc_match_level_v8"], "—"))
    .replace("TRACK_DISTANCE_RAIL_CONDITION_WIDE", "LOW")
    .replace("TRACK_DISTANCE_RAIL_CONDITION", "MEDIUM")
    .replace("EXACT", "HIGH")
    .replace(/_/g, " ");
}

function betScore(bet?: Row): string {
  const n = firstNum(bet, ["bet_quality_score_v1_1", "bet_quality_score"]);
  return n === null ? "—" : n.toFixed(0);
}

function betGrade(bet?: Row): string {
  return firstText(bet, ["bet_quality_grade_v1_1", "bet_quality_grade"], "—").toUpperCase();
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function isScratchedRunner(row: Row): boolean {
  const blob = [
    row.display_decision,
    row.runner_status,
    row.tab_fixed_betting_status,
    row.scratch_status,
    row.is_scratched,
    row.execution_action,
    row.decision,
  ]
    .map((value) => text(value).toUpperCase())
    .join(" ");

  if (blob.includes("SCRATCH")) return true;

  const explicitFlag = text(row.is_scratched).toUpperCase();
  return ["YES", "Y", "TRUE", "1"].includes(explicitFlag);
}

function isScratched(item: EnrichedRunner): boolean {
  return isScratchedRunner(item.row);
}

function isFallbackRow(item: EnrichedRunner): boolean {
  const priceStatus = firstText(item.row, ["V6_1_RESEARCH_price_status"], "").toUpperCase();
  return priceStatus.includes("FALLBACK");
}

function confidenceScoreValue(item: EnrichedRunner): number | null {
  return firstNum(item.runnerIntel, ["confidence_score"]) ??
    firstNum(item.drawer, ["confidence_score"]) ??
    firstNum(item.intel, ["confidence_score", "intelligence_reliability_component_v1"]) ??
    firstNum(item.row, ["confidence_score"]);
}

function intelligenceScoreValue(item: EnrichedRunner): number | null {
  return firstNum(item.intel, ["intelligence_score_v1"]);
}

function normalizeGradeLabel(value: string): string {
  const v = value.toUpperCase();
  if (!v || v === "—") return "";
  if (v.includes("SCRATCH")) return "SCRATCHED";
  if (v.includes("LOW DATA")) return "LOW DATA";
  if (v.includes("HIGH") || v.includes("ELITE") || v.includes("STRONG")) return "HIGH";
  if (v.includes("MEDIUM") || v.includes("PASS") || v.includes("WATCH") || v.includes("NEUTRAL")) return "MEDIUM";
  if (v.includes("LOW") || v.includes("POOR") || v.includes("NEGATIVE") || v.includes("WEAK")) return "LOW";
  return v;
}

function limitedAdjustedPrice(item: EnrichedRunner): number | null {
  return firstNum(item.limited, ["limited_data_adjusted_price_v1"]) ??
    firstNum(item.row, ["limited_data_adjusted_price_v1"]);
}

function betQualityNumeric(item: EnrichedRunner): number | null {
  return firstNum(item.bet, ["bet_quality_score_v1_1", "bet_quality_score"]) ??
    firstNum(item.drawer, ["bet_quality_score"]) ??
    firstNum(item.intel, ["intelligence_bet_quality_component_v1", "bet_quality_score"]) ??
    firstNum(item.row, ["bet_quality_score_v1_1", "bet_quality_score"]);
}

function sourceBetQualityGrade(item: EnrichedRunner): string {
  return normalizeGradeLabel(firstText(item.bet, ["bet_quality_grade_v1_1", "bet_quality_grade"], ""));
}

function computedLimitedScore(item: EnrichedRunner): number {
  if (isScratched(item)) return 0;

  const existing =
    firstNum(item.limited, ["limited_data_factor_score_v1", "limited_data_score_v1", "limited_score"]) ??
    firstNum(item.row, ["limited_data_factor_score_v1", "limited_data_score_v1", "limited_score"]);
  if (existing !== null) return clamp(Math.round(existing), 1, 100);

  const betQualityScore = betQualityNumeric(item);
  if (betQualityScore !== null) return clamp(Math.round(betQualityScore), 1, 100);

  const intelligenceScore = intelligenceScoreValue(item);
  if (intelligenceScore !== null) return clamp(Math.round(intelligenceScore), 1, 100);

  const win = winPct(item.row, item.bet) ?? 0;
  const edge = edgePct(item.row, item.bet) ?? 0;
  const base = 35;
  const winComponent = clamp(win * 1.8, 0, 25);
  const edgeComponent = clamp(Math.max(edge, 0) * 0.18, 0, 25);
  const negativeEdgePenalty = edge < 0 ? clamp(Math.abs(edge) * 0.12, 0, 20) : 0;
  const fallbackPenalty = isFallbackRow(item) ? 12 : 0;
  return clamp(Math.round(base + winComponent + edgeComponent - negativeEdgePenalty - fallbackPenalty), 1, 100);
}

function limitedScoreValue(item: EnrichedRunner): string {
  if (isScratched(item)) return "";
  return Math.round(computedLimitedScore(item)).toString();
}

function limitedDecisionValue(item: EnrichedRunner): string {
  const value = firstText(
    item.limited,
    ["limited_data_decision_v1"],
    firstText(item.row, ["limited_data_decision_v1"], ""),
  );

  if (value) return customerLimitedDecisionLabel(value.replace(/_/g, " ").toUpperCase());

  if (isScratched(item)) return "SCRATCHED";

  const score = computedLimitedScore(item);
  const edge = edgePct(item.row, item.bet) ?? 0;

  if (edge < 0) return "PASS";
  if (score >= 65 && edge >= 18) return "MODEL EDGE";
  if (score >= 50 && edge >= 10) return "WATCH";
  if (isFallbackRow(item) && score < 60) return "LOW DATA";
  if (score >= 40 && edge > 0) return "PASS";
  return "PASS";
}

function displayBetValue(item: EnrichedRunner): string {
  if (isScratched(item)) return "SCRATCHED";

  const base = decision(item.row, item.bet).toUpperCase();
  const edge = edgePct(item.row, item.bet) ?? 0;

  if (base === "NO MARKET" || base === "NO_MODEL" || base === "NO MODEL") return "WAIT";
  if (base === "WATCH" && edge >= 18) return "BET";
  if (base === "WATCH") return "WATCH";
  if (base === "LEAN") return "LEAN";
  if (base === "PASS" || base === "UNDERLAY") return "PASS";
  return base || "WAIT";
}

function displayGradeValue(item: EnrichedRunner): string {
  if (isScratched(item)) return "SCRATCHED";

  const qualityScore = betQualityNumeric(item);
  if (qualityScore !== null) {
    if (qualityScore >= 75) return "VERY HIGH";
    if (qualityScore >= 60) return "HIGH";
    if (qualityScore >= 45) return "MEDIUM";
    if (qualityScore >= 30) return "LOW";
    return "VERY LOW";
  }

  const qualityGrade = sourceBetQualityGrade(item);
  if (qualityGrade) return qualityGrade;

  const score = computedLimitedScore(item);
  const edge = edgePct(item.row, item.bet) ?? 0;
  const win = winPct(item.row, item.bet) ?? 0;

  if (isFallbackRow(item) && !(edge >= 50 && win >= 8)) {
    if (score >= 45) return "MEDIUM";
    if (score >= 30) return "LOW";
    return "VERY LOW";
  }

  if (score >= 75) return "VERY HIGH";
  if (score >= 60) return "HIGH";
  if (score >= 45) return "MEDIUM";
  if (score >= 30) return "LOW";
  return "VERY LOW";
}

function displayBetQualityValue(item: EnrichedRunner): string {
  if (isScratched(item)) return "SCRATCHED";

  const score = betQualityNumeric(item);
  const grade = sourceBetQualityGrade(item);
  if (score !== null) {
    if (score >= 75) return "VERY HIGH";
    if (score >= 60) return "HIGH";
    if (score >= 45) return "MEDIUM";
    if (score >= 30) return "LOW";
    return "VERY LOW";
  }
  if (grade) return grade;

  const scoreFromLimited = computedLimitedScore(item);
  if (scoreFromLimited >= 75) return "VERY HIGH";
  if (scoreFromLimited >= 60) return "HIGH";
  if (scoreFromLimited >= 45) return "MEDIUM";
  if (scoreFromLimited >= 30) return "LOW";
  return "VERY LOW";
}

function cellTone(label: string): string {
  const value = label.toUpperCase();
  if (value === "BET") return "#3ee68f";
  if (value === "VERY HIGH" || value === "HIGH") return "#3ee68f";
  if (value === "WATCH" || value === "LEAN" || value === "MEDIUM") return "#f5c451";
  if (value === "MODEL" || value === "MODEL EDGE") return "#7dd3fc";
  if (value === "LOW DATA") return "#94a3b8";
  if (value === "SCRATCHED") return "#9ca3af";
  if (value === "WAIT") return "#94a3b8";
  if (value === "PASS" || value === "UNDERLAY" || value === "LOW" || value === "VERY LOW") return "#f87171";
  return "#eaf2ff";
}

function valueAccent(label: string): React.CSSProperties {
  return { color: cellTone(label), fontWeight: 900 };
}

function sourceLabel(row: Row, bet?: Row): string {
  const display = firstText(row, ["display_source"], "");
  if (display && display !== "—") {
    return display
      .replace("LIMITED_DATA_MARKET_ADJUSTED_V1", "MARKET ADJ")
      .replace(/^MODEL$/i, "EDGEIQ")
      .toUpperCase();
  }

  const live = livePrice(row, bet);
  const explicit = firstText(row, ["live_price_source", "tab_live_price_source", "edgeiq_price_source_v1", "bookmaker"], "");
  if (explicit && explicit !== "—") {
    return explicit
      .replace("LIMITED_DATA_MARKET_ADJUSTED_V1", "MARKET ADJ")
      .replace(/^MODEL$/i, "EDGEIQ")
      .toUpperCase();
  }

  return live && live > 0 ? "TAB" : "EDGEIQ";
}

function decision(row: Row, bet?: Row): string {
  const display = firstText(row, ["display_decision"], "");
  if (display && display !== "—") return display.toUpperCase();

  const explicit = firstText(row, ["execution_action", "decision"], "");
  if (explicit && explicit !== "—" && !["NO MARKET", "NO_MARKET"].includes(explicit.toUpperCase())) {
    return explicit.toUpperCase();
  }

  const live = livePrice(row, bet);
  const fair = fairPrice(row, bet);
  const edge = edgePct(row, bet);

  if (!live || live <= 0) return "NO MARKET";
  if (!fair || fair <= 0) return "PASS";
  if (edge !== null && edge >= 18) return "WATCH";
  if (edge !== null && edge >= 10) return "LEAN";
  if (edge !== null && edge > 0) return "PASS";
  if (edge !== null) return "UNDERLAY";
  return "PASS";
}

export default function RaceIntelligenceScreen(props: Props): React.ReactElement {
  const [loading, setLoading] = useState(true);
  const [runnerRows, setRunnerRows] = useState<Row[]>([]);
  const [runnerIntelRows, setRunnerIntelRows] = useState<Row[]>([]);
  const [v8Rows, setV8Rows] = useState<Row[]>([]);
  const [betRows, setBetRows] = useState<Row[]>([]);
  const [reliabilityRows, setReliabilityRows] = useState<Row[]>([]);
  const [intelligenceCardRows, setIntelligenceCardRows] = useState<Row[]>([]);
  const [briefingRows, setBriefingRows] = useState<Row[]>([]);
  const [marketIntelRows, setMarketIntelRows] = useState<Row[]>([]);
  const [verdictRows, setVerdictRows] = useState<Row[]>([]);
  const [trackIntelRows, setTrackIntelRows] = useState<Row[]>([]);
  const [horseDrawerRows, setHorseDrawerRows] = useState<Row[]>([]);
  const [runnerDnaDrawerRows, setRunnerDnaDrawerRows] = useState<Row[]>([]);
  const [limitedDataRows, setLimitedDataRows] = useState<Row[]>([]);
  const [intelligenceScoreRows, setIntelligenceScoreRows] = useState<Row[]>([]);
  const [factorScorecardRows, setFactorScorecardRows] = useState<Row[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    let active = true;

    async function run(): Promise<void> {
      setLoading(true);

      const [runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel, horseDrawer, runnerDnaDrawer, factorScorecard, limitedData, intelligenceScore] = await Promise.all([
        loadCsv(FILES.runnerBoard),
        loadCsv(FILES.runnerIntel),
        loadCsv(FILES.v8),
        loadCsv(FILES.betQuality),
        loadCsv(FILES.reliability),
        loadCsv(FILES.intelligenceCards),
        loadCsv(FILES.briefing),
        loadCsv(FILES.marketIntel),
        loadCsv(FILES.verdict),
        loadCsv(FILES.trackIntel),
        loadCsv(FILES.horseDrawer),
        loadCsv(FILES.runnerDnaDrawer),
        loadCsv(FILES.factorScorecard),
        loadCsv(FILES.limitedData),
        loadCsv(FILES.intelligenceScore),
      ]);

      if (!active) return;

      setRunnerRows(runner);
      setRunnerIntelRows(runnerIntel);
      setV8Rows(v8);
      setBetRows(bet);
      setReliabilityRows(rel);
      setIntelligenceCardRows(cards);
      setBriefingRows(briefing);
      setMarketIntelRows(marketIntel);
      setVerdictRows(verdict);
      setTrackIntelRows(trackIntel);
      setHorseDrawerRows(horseDrawer);
      setRunnerDnaDrawerRows(runnerDnaDrawer);
      setFactorScorecardRows(factorScorecard);
      setLimitedDataRows(limitedData);
      setIntelligenceScoreRows(intelligenceScore);
      setLoading(false);
    }

    run();

    return () => {
      active = false;
    };
  }, []);

  const selectedTrack = cleanTrack(props.selectedTrack || props.currentRace?.track);
  const selectedRaceNo = text(props.selectedRaceNo || props.currentRace?.raceNo || props.currentRace?.race_no);
  const futureMeeting = text(props.currentMeeting?.dashboardReady).toUpperCase() === "NO";
  const futureMeetingTrack = text(props.currentMeeting?.track);
  const futureMeetingDate = text(props.currentMeeting?.raceDate);
  const futureMeetingStatus = text(props.currentMeeting?.meetingStatus).replace(/_/g, " ") || "FIELDS PENDING";
  const futureMeetingDayBucket = text(props.currentMeeting?.dayBucket).replace("DAY+2", "DAY +2") || "UPCOMING";

  const raceRows = useMemo(() => {
    let rows = runnerRows;

    if (selectedTrack) rows = rows.filter((row) => cleanTrack(track(row)) === selectedTrack);
    if (selectedRaceNo) rows = rows.filter((row) => raceNo(row) === selectedRaceNo);

    if (!rows.length && props.currentRace?.track && props.currentRace?.raceNo) {
      rows = runnerRows.filter(
        (row) =>
          cleanTrack(track(row)) === cleanTrack(props.currentRace.track) &&
          raceNo(row) === text(props.currentRace.raceNo)
      );
    }

    return [...rows].sort((a, b) => saddle(a) - saddle(b));
  }, [runnerRows, selectedTrack, selectedRaceNo, props.currentRace]);

  const enriched = useMemo(() => {
    return raceRows.map((row) => {
      const runnerIntel = findSidecar(runnerIntelRows, row);
      const v8 = findSidecar(v8Rows, row);
      const bet = findSidecar(betRows, row);
      const rel = findSidecar(reliabilityRows, row);
      const drawer = findSidecar(horseDrawerRows, row);
      const dna = findSidecar(runnerDnaDrawerRows, row);
      const limited = findSidecar(limitedDataRows, row);
      const intel = findSidecar(intelligenceScoreRows, row);
      const rowJoinKey = firstText(dna, ["join_key"], "") || firstText(row, ["join_key"], "");
      const factorRows = factorScorecardRows
        .filter((factorRow) => {
          const factorJoinKey = firstText(factorRow, ["join_key"], "");
          if (rowJoinKey && factorJoinKey) return factorJoinKey === rowJoinKey;
          return cleanTrack(track(factorRow)) === cleanTrack(track(row)) && raceNo(factorRow) === raceNo(row) && cleanHorse(horse(factorRow)) === cleanHorse(horse(row));
        })
        .sort((a, b) => (num(a.factor_order) ?? 999) - (num(b.factor_order) ?? 999));

      return { row, runnerIntel, v8, bet, rel, drawer, dna, limited, intel, factorRows };
    });
  }, [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, factorScorecardRows, limitedDataRows, intelligenceScoreRows]);

  const decisionBoardGridCols =
    "55px 245px 80px 150px 100px 96px 96px 96px 110px 120px";

  const decisionBoardLegend =
    "WIN CHANCE | FAIR PRICE | TAB PRICE | VALUE EDGE | EDGEiQ CONFIDENCE | FINAL CALL";

  const selected =
    enriched.find((item) => `${track(item.row)}|${raceNo(item.row)}|${cleanHorse(horse(item.row))}` === selectedKey) ||
    enriched.find((item) => (edgePct(item.row, item.bet) ?? -999) > 0) ||
    enriched[0];

  const header = raceRows[0];

  const intelligenceCard = useMemo(() => {
    if (!header) return undefined;
    return findRaceSidecar(intelligenceCardRows, header);
  }, [intelligenceCardRows, header]);

  const briefing = useMemo(() => {
    if (!header) return undefined;
    return findRaceSidecar(briefingRows, header);
  }, [briefingRows, header]);

  const marketIntel = useMemo(() => {
    if (!header) return undefined;
    return findRaceSidecar(marketIntelRows, header);
  }, [marketIntelRows, header]);

  const verdict = useMemo(() => {
    if (!header) return undefined;
    return findRaceSidecar(verdictRows, header);
  }, [verdictRows, header]);

  const trackIntel = useMemo(() => {
    if (!header) return undefined;
    return findRaceSidecar(trackIntelRows, header);
  }, [trackIntelRows, header]);

  const raceClarity = band(intelligenceCard, ["race_clarity_band_v1", "race_clarity"], "—");
  const expectedTempo = band(intelligenceCard, ["expected_tempo_band_v1", "expected_tempo"], "—");
  const bettingConfidence = band(intelligenceCard, ["betting_confidence_band_v1", "betting_confidence"], "—");
  const raceStory = firstText(intelligenceCard, ["race_story_v1", "race_story"], "");

  const mostLikelyWinner =
    firstText(verdict, ["most_likely_winner", "likely_winner", "top_pick"], "") ||
    firstText(briefing, ["most_likely_winner", "likely_winner", "top_pick"], "");

  const bestValue =
    firstText(verdict, ["best_value", "best_current_value", "best_value_runner"], "") ||
    firstText(briefing, ["best_value", "best_current_value", "best_value_runner"], "");

  const mostLikelyFair =
    firstNum(briefing, ["most_likely_fair", "top_pick_fair"]) ??
    firstNum(verdict, ["most_likely_fair", "top_pick_fair"]);
  const bestValueEdge =
    firstNum(briefing, ["top_value_edge", "best_value_edge", "best_current_value_edge"]) ??
    firstNum(verdict, ["top_value_edge", "best_value_edge", "best_current_value_edge"]);
  const bestBet = firstText(verdict, ["best_bet", "bet_recommendation", "verdict_bet"], "WATCH").toUpperCase();
  const verdictNarrative = firstText(verdict, ["verdict_narrative", "race_verdict", "verdict_comment", "narrative"], "");
  const briefingNarrative = firstText(briefing, ["race_briefing", "briefing", "race_briefing_text", "briefing_text"], "");
  const marketComment = firstText(marketIntel, ["market_comment", "market_intelligence", "market_narrative"], "");
  const trackProfile = firstText(trackIntel, ["track_dna_style"], "NO PROFILE");
  const trackBarrier = firstText(trackIntel, ["track_dna_barrier"], "");
  const trackMovement = firstText(trackIntel, ["track_dna_movement"], "");
  const trackDnaConfidence = band(trackIntel, ["track_dna_confidence"], "—");
  const trackDnaSampleWinners = firstText(trackIntel, ["track_dna_sample_winners"], "");

  const bestTrackFitRunner = firstText(trackIntel, ["best_track_fit_runner"], "—");
  const bestTrackFitScore = firstText(trackIntel, ["best_track_fit_score"], "—");
  const eliteFitCount = firstText(trackIntel, ["elite_fit_count"], "0");
  const strongFitCount = firstText(trackIntel, ["strong_fit_count"], "0");
  const positiveFitCount = firstText(trackIntel, ["positive_fit_count"], "0");
  const negativeFitCount = firstText(trackIntel, ["negative_fit_count"], "0");
  const poorFitCount = firstText(trackIntel, ["poor_fit_count"], "0");
  const trackAdvantageSummary = firstText(trackIntel, ["track_advantage_summary"], "");
  const trackRiskSummary = firstText(trackIntel, ["track_risk_summary"], "");
  const trackIntelligenceComment = firstText(trackIntel, ["track_intelligence_comment"], "");
  const conditionLabel = header ? `${trackCondition(header).toUpperCase()} / ${distance(header)} / ${raceClass(header)}` : "—";
  const trackRiskCount =
    integer(trackRiskSummary) ??
    ((integer(negativeFitCount) ?? 0) + (integer(poorFitCount) ?? 0) || null);
  const trackDnaHeaderCopy = trackDnaHeadline(trackProfile);
  const trackDnaFitContext =
    trackProfile.toUpperCase() === "NO PROFILE"
      ? conditionLabel
      : `${trackDnaHeaderCopy}${humanBarrierPhrase(trackBarrier) ? ` • ${humanBarrierPhrase(trackBarrier)}` : ""}`;
  const customerTrackAdvantage =
    trackProfile.toUpperCase() === "NO PROFILE"
      ? "No clear historical track pattern is available for this setup."
      : `This setup historically favours ${humanTrackStyle(trackProfile)}${humanBarrierPhrase(trackBarrier) ? ` from ${humanBarrierPhrase(trackBarrier)}` : ""}.${bestTrackFitRunner && bestTrackFitRunner !== "—" ? ` Best profile match: ${bestTrackFitRunner}.` : ""}`;
  const customerTrackRisk =
    trackRiskCount && trackRiskCount > 0
      ? `${trackRiskCount} runners clash with today's historical profile.`
      : trackRiskSummary || "No major profile risks stand out for this race.";
  const customerTrackInsight =
    trackIntelligenceComment
      ? `Track influence: ${trackDnaConfidence}.${trackDnaSampleWinners ? ` Historical sample: ${trackDnaSampleWinners} winners.` : ""}${integer(positiveFitCount) !== null && trackRiskCount !== null ? ` Clear fits: ${positiveFitCount}. Profile risks: ${trackRiskCount}.` : ""}`
      : `Track influence: ${trackDnaConfidence}.${trackDnaSampleWinners ? ` Historical sample: ${trackDnaSampleWinners} winners.` : ""}`;
  const customerBriefingNarrative = buildBriefingNarrative(
    raceClarity,
    expectedTempo,
    bettingConfidence,
    mostLikelyWinner,
    mostLikelyFair,
    bestValue,
    bestValueEdge,
  );
  const selectedIsScratched = selected ? isScratched(selected) : false;
  const selectedDisplayBet = selected ? displayBetValue(selected) : "—";
  const selectedDisplayGrade = selected ? displayGradeValue(selected) : "—";
  const selectedLimitedScore = selected ? limitedScoreValue(selected) : "";
  const selectedLimitedScoreNumeric = selected ? computedLimitedScore(selected) : null;
  const selectedLimitedDecision = selected ? limitedDecisionValue(selected) : "—";
  const selectedBetQuality = selected ? displayBetQualityValue(selected) : "—";
  const selectedProjectionBand = selected
    ? firstText(selected.row, ["projection_band_V6_1_RESEARCH", "projection_band_v5_2"], "—").replace(/_/g, " ").toUpperCase()
    : "—";
  const selectedProjectionGap = selected
    ? firstNum(selected.row, ["projection_gap_V6_1_RESEARCH", "projection_gap_v5_2"])
    : null;
  const selectedProjectionStatus = selected
    ? firstText(selected.row, ["V6_1_RESEARCH_price_status"], "—").replace(/_/g, " ").toUpperCase()
    : "—";
  const selectedProjectedSpd = selected
    ? firstNum(selected.runnerIntel, ["projected_spd"]) ?? firstNum(selected.row, ["projected_spd"])
    : null;
  const selectedSectional = selected
    ? firstNum(selected.runnerIntel, ["sectional_weapon_score"]) ??
      firstNum(selected.drawer, ["sectional_weapon_score"]) ??
      firstNum(selected.intel, ["intelligence_sectional_component_v1"])
    : null;
  const selectedLatePower = selected
    ? firstNum(selected.runnerIntel, ["late_power_index"]) ?? firstNum(selected.drawer, ["late_power_index"])
    : null;
  const selectedCareerStarts = selected ? firstText(selected.drawer, ["career_starts_profile"], "—") : "—";
  const selectedCareerWins = selected ? firstText(selected.drawer, ["career_wins_profile"], "—") : "—";
  const selectedCareerPlaces = selected ? firstText(selected.drawer, ["career_places_profile"], "—") : "—";
  const selectedLast5Form = selected ? firstText(selected.drawer, ["last_5_form_profile"], "—") : "—";
  const selectedProfileQuality = selected ? firstText(selected.drawer, ["profile_quality"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedDominantRunStyle = selected ? firstText(selected.drawer, ["dominant_run_style", "run_style"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedSectionalStrengthRating = selected ? firstText(selected.drawer, ["sectional_strength_rating"], "—") : "—";
  const selectedSectionalStrengthBand = selected ? firstText(selected.drawer, ["sectional_strength_band"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedDnaScore = selected ? firstText(selected.dna, ["dna_v6_2_score", "runner_dna_v6_1_score"], "—") : "—";
  const selectedDnaBand = selected ? firstText(selected.dna, ["dna_v6_2_band", "runner_dna_v6_1_band"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedDnaRank = selected ? firstText(selected.dna, ["runner_dna_v6_2_rank_in_race", "runner_dna_v6_1_rank_in_race"], "—") : "—";
  const selectedStrongestFactor = selected ? firstText(selected.dna, ["strongest_factor_v6_2", "strongest_factor_v6_1"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedStrongestFactorScore = selected ? firstText(selected.dna, ["strongest_factor_score_v6_2", "strongest_factor_score_v6_1"], "—") : "—";
  const selectedWeakestFactor = selected ? firstText(selected.dna, ["weakest_factor_v6_2", "weakest_factor_v6_1"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedWeakestFactorScore = selected ? firstText(selected.dna, ["weakest_factor_score_v6_2", "weakest_factor_score_v6_1"], "—") : "—";
  const selectedDistanceScore = selected ? firstText(selected.dna, ["distance_fit_score"], "—") : "—";
  const selectedDistanceBand = selected ? firstText(selected.dna, ["distance_fit_band"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedConditionScore = selected ? firstText(selected.dna, ["condition_fit_score"], "—") : "—";
  const selectedConditionBand = selected ? firstText(selected.dna, ["condition_fit_band"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedClassScore = selected ? firstText(selected.dna, ["class_fit_score"], "—") : "—";
  const selectedClassBand = selected ? firstText(selected.dna, ["class_fit_band"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedDnaNarrative = selected ? firstText(selected.dna, ["runner_dna_v6_2_narrative", "runner_dna_v6_1_narrative"], "") : "";
  const selectedFactorRows = selected?.factorRows || [];
  const selectedCurrentDecision = selected ? decision(selected.row, selected.bet) : "—";
  const selectedLivePrice = selected && !selectedIsScratched ? money(livePrice(selected.row, selected.bet)) : "—";
  const selectedFairPrice = selected && !selectedIsScratched ? money(limitedAdjustedPrice(selected) ?? fairPrice(selected.row, selected.bet)) : "—";
  const selectedEdge = selected && !selectedIsScratched ? pct(edgePct(selected.row, selected.bet)) : "—";
  const selectedHasCurrentBetQuality = !!selected?.bet;
  const selectedHasCurrentIntelligenceScore = !!selected?.intel;
  const selectedHasCurrentLimitedData = !!selected?.limited;
  const selectedConfidenceSource = !selected
    ? ""
    : selectedIsScratched
      ? "Confidence source unavailable while this runner is scratched."
      : selectedHasCurrentLimitedData
        ? "Confidence source: Live EDGEiQ confidence profile"
        : selectedHasCurrentBetQuality || selectedHasCurrentIntelligenceScore
          ? "Confidence source: Matched EDGEiQ confidence profile"
          : "Confidence source: Composite EDGEiQ confidence profile";
  const selectedDataCoverage = !selected
    ? ""
    : selectedIsScratched
      ? "SCRATCHED"
      : selectedHasCurrentLimitedData
        ? "GOOD"
        : selectedHasCurrentBetQuality || selectedHasCurrentIntelligenceScore
          ? ((selectedLimitedScoreNumeric ?? 0) >= 60 ? "GOOD" : "MEDIUM")
          : ((selectedLimitedScoreNumeric ?? 0) >= 60 ? "MEDIUM" : "LOW");
  const selectedEdgeNumeric = selected ? edgePct(selected.row, selected.bet) : null;
  const selectedPriceEdgeNarrative = !selected
    ? ""
    : selectedIsScratched
      ? "This runner is scratched and is not considered a live betting option."
      : selectedDisplayBet === "BET" && selectedCurrentDecision !== "BET"
        ? `Market edge qualifies as BET. Overall intelligence call remains ${selectedCurrentDecision}.`
        : selectedDisplayBet === "BET"
          ? "Market edge qualifies as BET and the overall EDGEiQ call agrees."
          : selectedEdgeNumeric !== null && selectedEdgeNumeric > 0
            ? `Positive price edge detected. Overall call remains ${selectedCurrentDecision}.`
            : `Current market is at or below EDGEiQ fair. Overall call remains ${selectedCurrentDecision}.`;
  const selectedFinalCallNarrative = !selected
    ? ""
    : selectedIsScratched
      ? "This runner is scratched and is not considered a live betting option."
      : selectedEdgeNumeric !== null && selectedEdgeNumeric >= 18 && selectedCurrentDecision === "WATCH"
        ? `Strong market edge (${selectedEdge}), but overall model confidence remains moderate.`
        : selectedEdgeNumeric !== null && selectedEdgeNumeric > 0
          ? `Current market still sits above EDGEiQ fair, while the overall call remains ${selectedCurrentDecision}.`
          : `The market is already at or below EDGEiQ fair, so the overall call remains ${selectedCurrentDecision}.`;
  const selectedReason = !selected
    ? ""
    : selectedIsScratched
      ? "This runner is scratched and is not considered a live betting option."
      : (() => {
          const overlayLead =
            selectedEdgeNumeric !== null && selectedEdgeNumeric >= 18
              ? "shows a strong market overlay"
              : selectedEdgeNumeric !== null && selectedEdgeNumeric > 0
                ? "shows a positive market edge"
                : "is currently priced tighter than EDGEiQ fair";
          const priceLine =
            selectedLivePrice !== "—" && selectedFairPrice !== "—"
              ? `, with the market at ${selectedLivePrice} versus EDGEiQ fair ${selectedFairPrice}`
              : "";
          const reasonTail =
            selectedDisplayBet === "BET" && selectedCurrentDecision === "WATCH"
              ? "Overall call remains WATCH because the broader model profile is not strong enough for a full upgrade."
              : selectedCurrentDecision === "WATCH"
                ? `Overall call remains WATCH because EDGEiQ confidence still grades ${selectedDisplayGrade.toLowerCase()}${selectedProjectionBand !== "—" ? ` with a ${selectedProjectionBand.toLowerCase()} runner profile` : ""}.`
                : selectedCurrentDecision === "BET"
                  ? "Overall call is BET because price edge and overall confidence are aligned."
                  : selectedCurrentDecision === "LEAN"
                    ? "Overall call stays LEAN while EDGEiQ waits for stronger confirmation."
                    : `Overall call remains ${selectedCurrentDecision} because the broader EDGEiQ profile does not justify an upgrade.`;
          return `${horse(selected.row)} ${overlayLead}${priceLine}. ${reasonTail}`;
        })();
  const selectedStats = selected
    ? selectedIsScratched
      ? [
        { label: "Status", value: "SCRATCHED", tone: "#9ca3af" },
        { label: "Win Chance", value: "—", tone: "#64748b" },
        { label: "Fair Price", value: "—", tone: "#64748b" },
        { label: "TAB Price", value: "—", tone: "#64748b" },
        { label: "Value Edge", value: "—", tone: "#64748b" },
        { label: "Price Signal", value: "SCRATCHED", tone: "#9ca3af" },
        { label: "EDGEiQ Confidence", value: "SCRATCHED", tone: "#9ca3af" },
        { label: "Confidence Score", value: "—", tone: "#64748b" },
        { label: "Model View", value: "SCRATCHED", tone: "#9ca3af" },
        { label: "Bet Quality", value: "SCRATCHED", tone: "#9ca3af" },
      ]
      : [
        { label: "Win Chance", value: pct(winPct(selected.row, selected.bet)) },
        { label: "Fair Price", value: money(limitedAdjustedPrice(selected) ?? fairPrice(selected.row, selected.bet)) },
        { label: "TAB Price", value: money(livePrice(selected.row, selected.bet)) },
        { label: "Value Edge", value: pct(edgePct(selected.row, selected.bet)) },
        { label: "Price Signal", value: displayBetValue(selected), tone: cellTone(displayBetValue(selected)) },
        { label: "EDGEiQ Confidence", value: displayGradeValue(selected), tone: cellTone(displayGradeValue(selected)) },
        { label: "Confidence Score", value: limitedScoreValue(selected) },
        { label: "Model View", value: limitedDecisionValue(selected), tone: cellTone(limitedDecisionValue(selected)) },
        { label: "Bet Quality", value: displayBetQualityValue(selected), tone: cellTone(displayBetQualityValue(selected)) },
      ]
    : [];

  const pageStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: 12,
    padding: 12,
    color: "#eaf2ff",
  };

  const panelStyle: React.CSSProperties = {
    padding: 12,
    border: "1px solid rgba(80,120,180,.35)",
    borderRadius: 12,
    background: "rgba(7,16,29,.92)",
  };

  const headerStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "minmax(0,1.3fr) minmax(300px,.85fr)",
    gap: 10,
    padding: 12,
    border: "1px solid rgba(91,229,169,.22)",
    borderRadius: 12,
    background: "linear-gradient(90deg,rgba(20,82,67,.35),rgba(7,16,29,.95))",
  };

  const titleStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
    fontWeight: 900,
    textTransform: "uppercase",
    letterSpacing: ".08em",
    color: "#c9d7ee",
  };

  const statStyle: React.CSSProperties = {
    border: "1px solid rgba(80,120,180,.35)",
    borderRadius: 12,
    padding: 8,
    background: "rgba(5,12,22,.75)",
  };
  const breakdownCardStyle: React.CSSProperties = {
    ...statStyle,
    display: "grid",
    gap: 5,
    alignContent: "start",
    minHeight: 122,
  };
  const breakdownPill = (label: string): React.CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "4px 9px",
    borderRadius: 999,
    border: "1px solid rgba(80,120,180,.35)",
    background: "rgba(10,18,30,.9)",
    color: cellTone(label),
    fontSize: 10,
    fontWeight: 900,
    letterSpacing: ".08em",
    textTransform: "uppercase",
    width: "fit-content",
  });
  const metricRowStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 6,
    fontSize: 10.5,
    color: "#cbd5e1",
  };
  const barTrackStyle: React.CSSProperties = {
    height: 3,
    borderRadius: 999,
    background: "rgba(51,65,85,.55)",
    overflow: "hidden",
  };
  const barFill = (percent: number, color: string): React.CSSProperties => ({
    width: `${clamp(percent, 0, 100)}%`,
    height: "100%",
    borderRadius: 999,
    background: color,
  });
  const performanceBarPct = (value: number | null, maxValue: number): number =>
    value === null ? 0 : clamp((value / maxValue) * 100, 0, 100);
  const infoGridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))",
    gap: 8,
    alignItems: "stretch",
  };
  const narrativeCardStyle: React.CSSProperties = {
    border: "1px solid rgba(51,65,85,.7)",
    borderRadius: 12,
    background: "linear-gradient(180deg, rgba(10,18,30,.95), rgba(4,10,18,.92))",
    padding: 10,
    display: "grid",
    gap: 8,
    minHeight: 0,
  };
  const narrativeTitleStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
  };
  const narrativeHeaderTextStyle: React.CSSProperties = {
    color: "#e5edf8",
    fontSize: 12,
    fontWeight: 900,
    letterSpacing: ".08em",
    textTransform: "uppercase",
  };
  const narrativeSubStyle: React.CSSProperties = {
    color: "#7f8ea3",
    fontSize: 10,
    fontStyle: "normal",
    fontWeight: 800,
    letterSpacing: ".06em",
    textTransform: "uppercase",
  };
  const miniGridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit,minmax(118px,1fr))",
    gap: 6,
  };
  const miniTileStyle: React.CSSProperties = {
    border: "1px solid rgba(51,65,85,.65)",
    borderRadius: 10,
    background: "rgba(3,11,20,.76)",
    padding: "7px 9px",
    display: "grid",
    gap: 3,
    minHeight: 48,
  };
  const miniLabelStyle: React.CSSProperties = {
    color: "#7f8ea3",
    fontSize: 10,
    fontWeight: 850,
    letterSpacing: ".06em",
    textTransform: "uppercase",
  };
  const miniValueStyle: React.CSSProperties = {
    color: "#f8fafc",
    fontSize: 13,
    fontWeight: 900,
    lineHeight: 1.2,
  };
  const narrativeInsetStyle: React.CSSProperties = {
    border: "1px solid rgba(30,41,59,.9)",
    borderRadius: 10,
    background: "rgba(2,8,16,.72)",
    padding: "8px 10px",
    color: "#cbd5e1",
    fontSize: 11.5,
    lineHeight: 1.35,
  };
  const trackPanelStyle: React.CSSProperties = {
    ...narrativeCardStyle,
    gridColumn: "span 2",
  };
  const trackTopTilesStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit,minmax(120px,1fr))",
    gap: 6,
  };
  const fitBadgeRowStyle: React.CSSProperties = {
    display: "flex",
    flexWrap: "wrap",
    gap: 5,
    alignItems: "center",
  };
  const fitBadge = (label: string, color: string, background: string, border: string): React.CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "2px 7px",
    borderRadius: 999,
    color,
    background,
    border,
    fontSize: 9.5,
    fontWeight: 900,
    letterSpacing: ".05em",
    textTransform: "uppercase",
  });
  const selectedHeaderStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    marginBottom: 8,
  };
  const selectedGridStyle = (count: number): React.CSSProperties => ({
    display: "grid",
    gridTemplateColumns: `repeat(${count}, minmax(96px,1fr))`,
    gap: 6,
    minWidth: `${count * 96}px`,
  });
  const selectedStatCardStyle: React.CSSProperties = {
    ...statStyle,
    minHeight: 60,
    display: "grid",
    gap: 4,
    alignContent: "start",
    padding: 7,
  };
  const selectedStatLabelStyle: React.CSSProperties = {
    color: "#7f8ea3",
    fontSize: 9.5,
    fontWeight: 850,
    letterSpacing: ".06em",
    textTransform: "uppercase",
    lineHeight: 1.1,
  };
  const selectedStatValueStyle = (tone?: string): React.CSSProperties => ({
    color: tone || "#f8fafc",
    fontSize: 14,
    fontWeight: 950,
    lineHeight: 1.15,
  });
  const selectedPanelStyle: React.CSSProperties = {
    display: "grid",
    gap: 8,
  };
  const selectedMetricsWrapStyle: React.CSSProperties = {
    overflowX: "auto",
    paddingBottom: 2,
  };
  const subsectionTitleStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
    marginBottom: 6,
    color: "#c9d7ee",
    fontWeight: 900,
    textTransform: "uppercase",
    letterSpacing: ".08em",
  };
  const breakdownGridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
    gap: 6,
  };

  if (loading) {
    return <div style={pageStyle}><section style={panelStyle}>Loading Race Intelligence...</section></div>;
  }

  if (futureMeeting) {
    return (
      <div style={pageStyle}>
        <section style={panelStyle}>
          <div style={titleStyle}>
            <span>Meeting Preview</span>
            <em>{futureMeetingDayBucket}</em>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Selected Meeting</div>
              <div className="edgeiq-mini-note-value">{futureMeetingTrack || "Upcoming meeting"}</div>
              <div className="edgeiq-mini-note-sub">
                {futureMeetingDate || "Date TBC"} | {futureMeetingStatus}
              </div>
            </div>

            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Expected Availability</div>
              <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
                Fields not yet available. EDGEiQ is monitoring this meeting and will populate intelligence automatically once fields are released.
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (!raceRows.length || !header) {
    return (
      <div style={pageStyle}>
        <section style={panelStyle}>
          <div style={titleStyle}>
            <span>Race Intelligence</span>
            <em>No runner rows available.</em>
          </div>
          <div style={{ color: "#94a3b8" }}>
            runnerRows {runnerRows.length} | selected {selectedTrack || "NO_TRACK"} R{selectedRaceNo || "NO_RACE"}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <header style={headerStyle}>
        <div style={{ display: "grid", gap: 6 }}>
          <div style={{ color: "#7dd3fc", fontWeight: 900, letterSpacing: ".16em", fontSize: 11 }}>
            EDGEiQ INTELLIGENCE LIVE
          </div>
          <h2 style={{ margin: "4px 0 2px", fontSize: 22, lineHeight: 1.1 }}>
            {track(header)} R{raceNo(header)}
          </h2>

          <div className="edgeiq-intel-race-meta">
            <span>{distance(header)}</span>
            {raceClass(header) !== "—" && <span>{raceClass(header)}</span>}
            <span>
              TRACK <em className={`edgeiq-condition-text ${trackCondition(header).toUpperCase().startsWith("FAST") ? "cond-fast" : trackCondition(header).toUpperCase().startsWith("GOOD") ? "cond-good" : trackCondition(header).toUpperCase().startsWith("SOFT") ? "cond-soft" : trackCondition(header).toUpperCase().startsWith("HEAVY") ? "cond-heavy" : "cond-unknown"}`}>{trackCondition(header).toUpperCase()}</em>
            </span>
          </div>

          <p style={{ margin: 0, color: "#bfd0ea", lineHeight: 1.35, maxWidth: 720, fontSize: 12 }}>
            {raceStory || "EDGEiQ combines live market context, model prices and race profile signals to frame the current betting picture."}
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 6 }}>
          <div style={miniTileStyle}><span style={miniLabelStyle}>Race Clarity</span><strong style={{ ...miniValueStyle, color: bandColor(raceClarity) }}>{raceClarity}</strong></div>
          <div style={miniTileStyle}><span style={miniLabelStyle}>Expected Tempo</span><strong style={{ ...miniValueStyle, color: bandColor(expectedTempo) }}>{expectedTempo}</strong></div>
          <div style={miniTileStyle}><span style={miniLabelStyle}>Track DNA</span><strong style={miniValueStyle}>{trackProfile}</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>{trackDnaFitContext}</em></div>
          <div style={miniTileStyle}><span style={miniLabelStyle}>Betting Confidence</span><strong style={{ ...miniValueStyle, color: bandColor(bettingConfidence) }}>{bettingConfidence}</strong></div>
        </div>
      </header>

      <div style={infoGridStyle}>
        <section style={narrativeCardStyle}>
          <div style={narrativeTitleStyle}><span style={narrativeHeaderTextStyle}>Race Briefing</span><em style={narrativeSubStyle}>Race Shape</em></div>
          <p style={{ ...narrativeInsetStyle, margin: 0 }}>{customerBriefingNarrative || briefingNarrative || `${expectedTempo} tempo expected. Race clarity is ${raceClarity}. Betting confidence is ${bettingConfidence}.`}</p>
          <div style={miniGridStyle}>
            <div style={miniTileStyle}>
              <span style={miniLabelStyle}>Top Win Chance</span>
              <strong style={miniValueStyle}>{mostLikelyWinner || "—"}</strong>
              {mostLikelyFair !== null ? <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>EDGEiQ fair {money(mostLikelyFair)}</em> : null}
            </div>
            <div style={miniTileStyle}>
              <span style={miniLabelStyle}>Best Value</span>
              <strong style={miniValueStyle}>{bestValue || "—"}</strong>
              {bestValueEdge !== null ? <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>{signed(bestValueEdge)}% edge</em> : null}
            </div>
          </div>
        </section>

        <section style={narrativeCardStyle}>
          <div style={narrativeTitleStyle}><span style={narrativeHeaderTextStyle}>Market Intelligence</span><em style={narrativeSubStyle}>Market Read</em></div>
          <div style={miniGridStyle}>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Strongest Firmer</span><strong style={miniValueStyle}>{firstText(marketIntel, ["strongest_firmer"], "—")}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Largest Drifter</span><strong style={miniValueStyle}>{firstText(marketIntel, ["largest_drifter"], "—")}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Market Efficiency</span><strong style={{ ...miniValueStyle, color: bandColor(band(marketIntel, ["market_efficiency"], "—")) }}>{band(marketIntel, ["market_efficiency"], "—")}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Overlay Count</span><strong style={miniValueStyle}>{firstText(marketIntel, ["overlay_count"], "—")}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Strong Overlay Count</span><strong style={miniValueStyle}>{firstText(marketIntel, ["strong_overlay_count"], "—")}</strong></div>
          </div>
          {marketComment && <p style={{ ...narrativeInsetStyle, margin: 0 }}>{marketComment}</p>}
        </section>

        <section style={narrativeCardStyle}>
          <div style={narrativeTitleStyle}><span style={narrativeHeaderTextStyle}>Race Verdict</span><em style={narrativeSubStyle}>EDGEiQ Call</em></div>
          <div style={miniGridStyle}>
            <div style={miniTileStyle}>
              <span style={miniLabelStyle}>Top Win Chance</span>
              <strong style={miniValueStyle}>{mostLikelyWinner || "—"}</strong>
              {mostLikelyFair !== null ? <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>EDGEiQ fair {money(mostLikelyFair)}</em> : null}
            </div>
            <div style={miniTileStyle}>
              <span style={miniLabelStyle}>Best Value</span>
              <strong style={miniValueStyle}>{bestValue || "—"}</strong>
              {bestValueEdge !== null ? <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>{signed(bestValueEdge)}% edge</em> : null}
            </div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Best Bet</span><strong style={{ ...miniValueStyle, color: bandColor(bestBet) }}>{bestBet}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Confidence</span><strong style={{ ...miniValueStyle, color: bandColor(bettingConfidence) }}>{bettingConfidence}</strong></div>
          </div>
          <p style={{ ...narrativeInsetStyle, margin: 0 }}>{verdictNarrative || `${raceClarity} race. ${expectedTempo} tempo. ${bettingConfidence} betting confidence.`}</p>
        </section>

        <section style={trackPanelStyle}>
          <div style={narrativeTitleStyle}><span style={narrativeHeaderTextStyle}>Track Intelligence</span><em style={narrativeSubStyle}>Historical DNA</em></div>

          <div style={trackTopTilesStyle}>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Track DNA</span><strong style={{ ...miniValueStyle, color: "#7dd3fc" }}>{trackProfile}</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>{trackDnaHeadline(trackProfile)}</em></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Barrier Bias</span><strong style={{ ...miniValueStyle, color: "#f5c451" }}>{trackBarrier || "—"}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Best Fit</span><strong style={miniValueStyle}>{bestTrackFitRunner}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Fit Score</span><strong style={{ ...miniValueStyle, color: "#34d399" }}>{bestTrackFitScore}</strong></div>
          </div>

          <div style={fitBadgeRowStyle}>
            <span style={fitBadge(`Elite ${eliteFitCount}`, "#bbf7d0", "rgba(6,95,70,.32)", "1px solid rgba(52,211,153,.34)")}>{`Elite ${eliteFitCount}`}</span>
            <span style={fitBadge(`Strong ${strongFitCount}`, "#bfdbfe", "rgba(30,64,175,.28)", "1px solid rgba(96,165,250,.34)")}>{`Strong ${strongFitCount}`}</span>
            <span style={fitBadge(`Poor ${poorFitCount}`, "#fecaca", "rgba(127,29,29,.28)", "1px solid rgba(248,113,113,.32)")}>{`Poor ${poorFitCount}`}</span>
          </div>

          <div style={{ ...narrativeInsetStyle, display: "grid", gap: 8 }}>
            {(customerTrackAdvantage || trackAdvantageSummary) ? <div><strong style={{ color: "#7dd3fc", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>What The Track Favours</strong><div style={{ marginTop: 4 }}>{customerTrackAdvantage || trackAdvantageSummary}</div></div> : null}
            {(customerTrackRisk || trackRiskSummary) ? <div><strong style={{ color: "#f5c451", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>Profile Risks</strong><div style={{ marginTop: 4 }}>{customerTrackRisk || trackRiskSummary}</div></div> : null}
            {(customerTrackInsight || trackIntelligenceComment) ? <div><strong style={{ color: "#34d399", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>EDGEiQ Insight</strong><div style={{ marginTop: 4 }}>{customerTrackInsight || trackIntelligenceComment}</div></div> : null}
          </div>
        </section>
      </div>

      {selected ? (
        <section
          style={
            selectedIsScratched
              ? {
                ...panelStyle,
                opacity: 0.82,
                border: "1px solid rgba(100,116,139,.35)",
                background: "rgba(15,23,42,.92)",
                ...selectedPanelStyle,
              }
              : { ...panelStyle, ...selectedPanelStyle }
          }
        >
          <div style={selectedHeaderStyle}>
            <div style={{ display: "grid", gap: 3 }}>
              <span style={{ color: "#c9d7ee", fontWeight: 900, textTransform: "uppercase", letterSpacing: ".08em" }}>Selected Runner</span>
              <em style={{ color: "#94a3b8", fontStyle: "normal", fontSize: 11 }}>
                {selectedIsScratched ? "Scratched / inactive" : "Live runner summary and EDGEiQ view"}
              </em>
            </div>
            <em style={selectedIsScratched ? { color: "#94a3b8", fontStyle: "normal", textAlign: "right", lineHeight: 1.25 } : { fontStyle: "normal", textAlign: "right", lineHeight: 1.25 }}>
              {horse(selected.row)}
              {selectedIsScratched ? " • SCRATCHED" : ""}
            </em>
          </div>

          <div style={selectedMetricsWrapStyle}>
            <div style={selectedGridStyle(selectedStats.length)}>
              {selectedStats.map((stat) => (
                <div key={stat.label} style={selectedStatCardStyle}>
                  <span style={selectedStatLabelStyle}>{stat.label}</span>
                  <strong style={selectedStatValueStyle(stat.tone)}>{stat.value || "—"}</strong>
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...narrativeInsetStyle, marginTop: 2, color: selectedIsScratched ? "#94a3b8" : "#d8e3f3" }}>
            <strong style={{ display: "block", marginBottom: 4, color: "#7dd3fc", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>EDGEiQ Reason</strong>
            <span>{selectedReason}</span>
          </div>

          <div style={{ borderTop: "1px solid rgba(51,65,85,.55)", marginTop: 2, paddingTop: 8 }}>
            <div style={subsectionTitleStyle}>
              <span>EDGEiQ Decision Breakdown</span>
              <em style={{ color: "#94a3b8", fontStyle: "normal", fontSize: 11, textTransform: "none", letterSpacing: "normal" }}>
                {selectedIsScratched ? "Scratched / inactive" : "Why EDGEiQ rates this runner this way"}
              </em>
            </div>
          </div>

          <div style={breakdownGridStyle}>
            <div style={breakdownCardStyle}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>Price Edge</span>
                <span style={breakdownPill(selectedIsScratched ? "SCRATCHED" : selectedDisplayBet)}>{selectedIsScratched ? "SCRATCHED" : selectedDisplayBet}</span>
              </div>
              <div style={metricRowStyle}><span>TAB Price</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedLivePrice}</strong></div>
              <div style={metricRowStyle}><span>Fair Price</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedFairPrice}</strong></div>
              <div style={metricRowStyle}><span>Value Edge</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedDisplayBet) }}>{selectedEdge}</strong></div>
              <div style={{ color: "#94a3b8", fontSize: 11, lineHeight: 1.4 }}>
                {selectedPriceEdgeNarrative}
              </div>
            </div>

            <div style={breakdownCardStyle}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>Runner Profile</span>
                <span style={breakdownPill(selectedProjectionStatus)}>{selectedProjectionStatus}</span>
              </div>
              <div style={metricRowStyle}><span>Runner Profile</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedProjectionBand) }}>{selectedProjectionBand}</strong></div>
              <div style={metricRowStyle}><span>Projection Gap</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedIsScratched ? "—" : signed(selectedProjectionGap, 2)}</strong></div>
              <div style={metricRowStyle}><span>Rating Status</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedProjectionStatus}</strong></div>
              <div style={{ color: "#94a3b8", fontSize: 11, lineHeight: 1.4 }}>
                {selectedIsScratched ? "This runner is scratched and not part of the live model read." : "Rating generated from the current EDGEiQ projection model."}
              </div>
            </div>
            <div style={{ ...breakdownCardStyle, gap: 7 }}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>RUNNER DNA</span>
                <span style={breakdownPill(selectedIsScratched ? "SCRATCHED" : selectedDnaBand)}>
                  {selectedIsScratched ? "SCRATCHED" : selectedDnaBand}
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>DNA Score</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : cellTone(selectedDnaBand), fontSize: 20 }}>
                    {selectedIsScratched ? "—" : selectedDnaScore}
                  </strong>
                </div>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>Race Rank</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : "#7dd3fc", fontSize: 20 }}>
                    {selectedIsScratched ? "—" : `#${selectedDnaRank}`}
                  </strong>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>Strongest</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : "#7dd3fc" }}>
                    {selectedIsScratched ? "—" : selectedStrongestFactor}
                  </strong>
                  <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal" }}>{selectedIsScratched ? "" : selectedStrongestFactorScore}</em>
                </div>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>Weakest</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : "#f5c451" }}>
                    {selectedIsScratched ? "—" : selectedWeakestFactor}
                  </strong>
                  <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal" }}>{selectedIsScratched ? "" : selectedWeakestFactorScore}</em>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 6 }}>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>Distance</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : cellTone(selectedDistanceBand) }}>{selectedIsScratched ? "—" : selectedDistanceBand}</strong>
                  <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal" }}>{selectedIsScratched ? "" : selectedDistanceScore}</em>
                </div>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>Condition</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : cellTone(selectedConditionBand) }}>{selectedIsScratched ? "—" : selectedConditionBand}</strong>
                  <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal" }}>{selectedIsScratched ? "" : selectedConditionScore}</em>
                </div>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>Class</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : cellTone(selectedClassBand) }}>{selectedIsScratched ? "—" : selectedClassBand}</strong>
                  <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal" }}>{selectedIsScratched ? "" : selectedClassScore}</em>
                </div>
              </div>

              <div style={{ ...narrativeInsetStyle, margin: 0, fontSize: 11, lineHeight: 1.4 }}>
                <strong style={{ color: "#7dd3fc", fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".06em" }}>
                  EDGEiQ DNA Read
                </strong>
                <div style={{ marginTop: 4 }}>
                  {selectedIsScratched ? "Runner scratched." : selectedDnaNarrative || "No DNA narrative available."}
                </div>
              </div>

              <div style={{ ...narrativeInsetStyle, margin: 0, display: "grid", gap: 6 }}>
                <strong style={{ color: "#7dd3fc", fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".06em" }}>
                  DNA Factor Breakdown
                </strong>
                {selectedIsScratched ? (
                  <div style={{ color: "#94a3b8", fontSize: 11 }}>Runner scratched.</div>
                ) : selectedFactorRows.length ? (
                  <div style={{ display: "grid", gap: 6 }}>
                    {selectedFactorRows.map((factorRow) => {
                      const factorName = firstText(factorRow, ["factor"], "—");
                      const factorScore = firstNum(factorRow, ["factor_score"]);
                      const factorBand = firstText(factorRow, ["factor_band"], "—").replace(/_/g, " ").toUpperCase();
                      const isStrong = firstText(factorRow, ["is_strongest_factor"], "") === "YES";
                      const isWeak = firstText(factorRow, ["is_weakest_factor"], "") === "YES";
                      const tone = isWeak ? "#f5c451" : isStrong ? "#7dd3fc" : cellTone(factorBand);
                      return (
                        <div key={`${horse(selected.row)}-${factorName}`} style={{ display: "grid", gap: 3 }}>
                          <div style={{ display: "grid", gridTemplateColumns: "92px 42px 1fr", gap: 6, alignItems: "center" }}>
                            <span style={{ color: tone, fontSize: 10.5, fontWeight: 900, letterSpacing: ".04em" }}>{factorName}</span>
                            <strong style={{ color: "#f8fafc", fontSize: 11, textAlign: "right" }}>{factorScore === null ? "—" : factorScore.toFixed(0)}</strong>
                            <span style={{ color: "#94a3b8", fontSize: 9.5, fontWeight: 800, textTransform: "uppercase" }}>{factorBand}</span>
                          </div>
                          <div style={barTrackStyle}>
                            <div style={barFill(factorScore ?? 0, tone)} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ color: "#94a3b8", fontSize: 11 }}>No factor breakdown available.</div>
                )}
              </div>
            </div>

            <div style={breakdownCardStyle}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>Performance Factors</span>
                <span style={breakdownPill(selectedIsScratched ? "SCRATCHED" : "LIVE")}>{selectedIsScratched ? "SCRATCHED" : "LIVE"}</span>
              </div>
              <div>
                <div style={metricRowStyle}><span>Projected SPD</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedIsScratched ? "—" : selectedProjectedSpd?.toFixed(1) ?? "—"}</strong></div>
                <div style={barTrackStyle}><div style={barFill(selectedIsScratched ? 0 : performanceBarPct(selectedProjectedSpd, 10), "#7dd3fc")} /></div>
              </div>
              <div>
                <div style={metricRowStyle}><span>Sectional Weapon</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedIsScratched ? "—" : selectedSectional?.toFixed(0) ?? "—"}</strong></div>
                <div style={barTrackStyle}><div style={barFill(selectedIsScratched ? 0 : performanceBarPct(selectedSectional, 100), "#a78bfa")} /></div>
              </div>
              <div>
                <div style={metricRowStyle}><span>Late Power</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedIsScratched ? "—" : selectedLatePower?.toFixed(0) ?? "—"}</strong></div>
                <div style={barTrackStyle}><div style={barFill(selectedIsScratched ? 0 : performanceBarPct(selectedLatePower, 100), "#f5c451")} /></div>
              </div>
            </div>

            <div style={breakdownCardStyle}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>Data Quality</span>
                <span style={breakdownPill(selectedIsScratched ? "SCRATCHED" : selectedDisplayGrade)}>{selectedIsScratched ? "SCRATCHED" : selectedDisplayGrade}</span>
              </div>
              <div style={metricRowStyle}><span>Confidence Score</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedIsScratched ? "—" : selectedLimitedScore || "—"}</strong></div>
              <div style={metricRowStyle}><span>EDGEiQ Confidence</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedDisplayGrade) }}>{selectedDisplayGrade}</strong></div>
              <div style={metricRowStyle}><span>Bet Quality</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedBetQuality) }}>{selectedBetQuality}</strong></div>
              <div style={{ color: "#94a3b8", fontSize: 11, lineHeight: 1.4 }}>
                {selectedConfidenceSource}. Data coverage: {selectedDataCoverage}.
              </div>
            </div>

            <div style={breakdownCardStyle}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>Final Call</span>
                <span style={breakdownPill(selectedIsScratched ? "SCRATCHED" : selectedCurrentDecision)}>{selectedIsScratched ? "SCRATCHED" : selectedCurrentDecision}</span>
              </div>
              <div style={metricRowStyle}><span>Final Call</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedCurrentDecision) }}>{selectedIsScratched ? "SCRATCHED" : selectedCurrentDecision}</strong></div>
              <div style={metricRowStyle}><span>Price Signal</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedDisplayBet) }}>{selectedIsScratched ? "SCRATCHED" : selectedDisplayBet}</strong></div>
              <div style={metricRowStyle}><span>Model View</span><strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedLimitedDecision) }}>{selectedIsScratched ? "SCRATCHED" : selectedLimitedDecision}</strong></div>
              <div style={{ color: "#bfd0ea", fontSize: 11, lineHeight: 1.45 }}>
                <div style={{ fontWeight: 900, color: selectedIsScratched ? "#94a3b8" : cellTone(selectedCurrentDecision), marginBottom: 4 }}>{selectedIsScratched ? "SCRATCHED" : selectedCurrentDecision}</div>
                <div>{selectedFinalCallNarrative}</div>
                {!selectedIsScratched ? (
                  <div style={{ marginTop: 6 }}>
                    Fair Price: {selectedFairPrice}
                    <br />
                    TAB Price: {selectedLivePrice}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <section style={{ ...panelStyle, overflowX: "auto" }}>
        <div style={titleStyle}>
          <span>Decision Board</span>
          <em>{decisionBoardLegend}</em>
        </div>

        <div style={{ display: "grid", gap: 6, minWidth: 1040 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: decisionBoardGridCols,
              gap: 8,
              padding: "10px 12px",
              color: "#94a3b8",
              fontSize: 11,
              fontWeight: 900,
              textTransform: "uppercase",
              letterSpacing: ".08em",
              borderBottom: "1px solid rgba(80,120,180,.35)",
            }}
          >
            <span style={{ textAlign: "center" }}>#</span>
            <span style={{ textAlign: "center" }}>Runner</span>
            <span style={{ textAlign: "center" }}>Barrier</span>
            <span style={{ textAlign: "center" }}>Jockey</span>
            <span style={{ textAlign: "center" }}>Win Chance</span>
            <span style={{ textAlign: "center" }}>Fair Price</span>
            <span style={{ textAlign: "center" }}>TAB Price</span>
            <span style={{ textAlign: "center" }}>Value Edge</span>
            <span style={{ textAlign: "center" }}>EDGEiQ Confidence</span>
            <span style={{ textAlign: "center" }}>Final Call</span>
          </div>

          {enriched.map((item) => {
            const key = `${track(item.row)}|${raceNo(item.row)}|${cleanHorse(horse(item.row))}`;
            const scratched = isScratched(item);
            const rowStyle: React.CSSProperties = {
              display: "grid",
              gridTemplateColumns: decisionBoardGridCols,
              gap: 8,
              alignItems: "center",
              padding: "11px 12px",
              border: scratched
                ? "1px solid rgba(100,116,139,.28)"
                : "1px solid rgba(80,120,180,.22)",
              borderRadius: 10,
              background: scratched
                ? "rgba(30,41,59,.18)"
                : selected && key === `${track(selected.row)}|${raceNo(selected.row)}|${cleanHorse(horse(selected.row))}`
                  ? "rgba(18,80,62,.38)"
                  : "rgba(5,12,22,.82)",
              opacity: scratched ? 0.42 : 1,
              filter: scratched ? "grayscale(0.9)" : undefined,
              cursor: "pointer",
            };
            const mutedCellStyle: React.CSSProperties | undefined = scratched ? { color: "#94a3b8" } : undefined;

            return (
              <button
                type="button"
                key={key}
                style={rowStyle}
                onClick={() => {
                  setSelectedKey(key);
                  setDrawerOpen(true);
                }}
              >
                {(() => {
                  const gradeLabel = displayGradeValue(item);
                  const runnerNameStyle: React.CSSProperties = scratched
                    ? {
                      display: "flex",
                      flexDirection: "column",
                      gap: 2,
                      fontWeight: 900,
                      color: "#cbd5e1",
                      textAlign: "center",
                      textDecoration: "line-through",
                    }
                    : {
                      display: "flex",
                      flexDirection: "column",
                      gap: 2,
                      fontWeight: 900,
                      color: "#f4f7fb",
                      textAlign: "center",
                    };

                  return (
                    <>
                <span style={mutedCellStyle}>{saddle(item.row) === 999 ? "—" : saddle(item.row)}</span>
                <strong style={runnerNameStyle}>
                  <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 6, flexWrap: "wrap" }}>
                    <span>{horse(item.row)}</span>
                    {scratched ? (
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: "2px 6px",
                          borderRadius: 999,
                          border: "1px solid rgba(148,163,184,.35)",
                          background: "rgba(51,65,85,.45)",
                          color: "#cbd5e1",
                          fontSize: 10,
                          letterSpacing: ".08em",
                          textTransform: "uppercase",
                        }}
                      >
                        SCR
                      </span>
                    ) : null}
                  </span>
                  <em style={{ color: scratched ? "#94a3b8" : "#94a3b8", fontSize: 11, textDecoration: "none" }}>{firstText(item.row, ["trainer"], "")}</em>
                </strong>
                <span style={mutedCellStyle}>{barrier(item.row)}</span>
                <span style={mutedCellStyle}>{firstText(item.row, ["jockey", "rider"], "—")}</span>
                <span style={mutedCellStyle}>{scratched ? "—" : pct(winPct(item.row, item.bet))}</span>
                <span style={mutedCellStyle}>{scratched ? "—" : money(limitedAdjustedPrice(item) ?? fairPrice(item.row, item.bet))}</span>
                <span style={mutedCellStyle}>{scratched ? "—" : money(livePrice(item.row, item.bet))}</span>
                <span style={mutedCellStyle}>{scratched ? "—" : pct(edgePct(item.row, item.bet))}</span>
                <span style={scratched ? { color: "#94a3b8", fontWeight: 900 } : valueAccent(gradeLabel)}>{gradeLabel}</span>
                <span style={scratched ? { color: "#94a3b8", fontWeight: 900 } : valueAccent(decision(item.row, item.bet))}>{decision(item.row, item.bet)}</span>
                    </>
                  );
                })()}
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}




























