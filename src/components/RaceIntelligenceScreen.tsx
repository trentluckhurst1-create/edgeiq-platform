import { buildSelectedRunnerProfile } from "../services/selectedRunnerProfileService";
import { HomeScreen } from "../screens/HomeScreen";
import { MeetingsScreen } from "../screens/MeetingsScreen";
import { cleanHorse, cleanHorseLoose, cleanTrack, marketMoney, money, num, pct, signed, text } from "../utils/edgeiqFormat";
import { parseCsv, type CsvRow } from "../utils/edgeiqCsv";
import { loadEdgeIQData } from "../services/edgeiqDataLoader";
import { distance, firstNum, firstText, horse, integer, raceClass, raceDate, raceNo, railPosition, track, trackCondition } from "../utils/raceRowHelpers";
import { buildRaceRows, runnerRowKey } from "../services/raceSelectionService";
import { buildEnrichedRunners } from "../services/runnerEnrichmentService";
import { buildRankedEnriched } from "../services/rankingService";
import { buildProductShellRaces } from "../services/productShellRaceService";
import { buildProductShellMeetings } from "../services/productShellMeetingService";
import { buildRaceIntelligenceSummary } from "../services/raceIntelligenceSummaryService";
import { betGrade, betScore, edgePct, fairPrice, getV72PriceSource, getV72wareDisplayFairPrice, getV72wareFairPrice, getV72wareProbability, isV72FeatureOn, livePrice, v8Conf, v8Fair, winPct } from "../services/marketPricingService";
import { compactKey, findCampaignSidecar, findCommandEnrichmentSidecar, findConnectionSidecar, findDnaSidecar, findFormEnrichmentSidecar, findHiddenGemForRunner, findNexusContextualSidecar, findSidecar, findSidecarByRaceHorse, sameRunner } from "../services/sidecarLookupService";
import { buildHistoryIndexes } from "../services/historyIndexService";
import { compactHistoryLine, findHistoryMasterRowsForRunner, formatHistoryDate, hasHistoricalRating, historyBarrierText, historyClassText, historyDateText, historyDateValue, historyDetailMergeKey, historyDetailMergeKeyLoose, historyDistanceText, historyFieldSizeText, historyFinishText, historyGoingText, historyJockeyText, historyRaceNoText, historyRaceStrengthText, historyRatingValue, historyRunnerLookupKey, historyRunKey, historySpText, historyTrackText, historyWeightText, mergeRunnerHistoryRows, ratedHistoryRows, ratingVariance, renderStaticMetricValue } from "../services/historyService";
import { betQualityNumeric, comboScoreValue, confidenceScoreValue, connectionScoreValue, dnaScoreValue, factorBandValue, factorRowValue, factorScoreValue, intelligenceScoreValue, jockeyScoreValue, latePowerMetricValue, limitedAdjustedPrice, normalizeGradeLabel, paceMapRole, paceMapXPercent, paceRoleSpeedValue, paceRoleTone, projectedSpdValue, projectionGapValue, projectionRatingValue, scoreTone, sectionalWeaponValue, shortHorseName, sourceBetQualityGrade, trackFitScoreValue, trainerScoreValue } from "../services/runnerMetricsService";
import { campaignEvidenceTone, cellTone, connectionTone, coverageStatus, coverageStatusTone, customerPerformanceNarrative, decision, drawerValue, evidenceQualityTone, fitReadLabel, formatCampaignStage, formatCampaignWindow, hiddenGemTone, historyReadLabel, opportunityTone, ordinal, performanceIntelligenceLabel, riskTone, runnerTrendSummary, runnerTrendTone, sourceLabel, trajectoryTone, valueccent } from "../services/displayFormattingService";
import { buildRaceDashboardSummary } from "../services/raceDashboardSummaryService";
import { buildSelectedRunnerCore } from "../services/selectedRunnerCoreService";
import React, { useEffect, useMemo, useState } from "react";
import { getMeetingDisplayState } from "../utils/meetingDisplayState";

type Row = CsvRow;


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
 dna?: Row;
 explainability?: Row;
 connection?: Row;
 limited?: Row;
 customerIntel?: Row;
 intelligenceSummary?: Row;
 raceDayIntelligence?: Row;
 intel?: Row;
 factorRows?: Row[];
 runnerProfile?: Row;
 formIntelligence?: Row;
 runnerForm?: Row;
 runnerHistory?: Row[];
 runnerCareer?: Row;
 runnerrchetype?: Row;
 runnerTrajectory?: Row;
 runnerProjection?: Row;
 campaign?: Row;
 hiddenGem?: Row;
 commandEnrichment?: Row;
 mapEnrichment?: Row;
 formEnrichment?: Row;
 ratingsHeatmap?: Row;
 nexusContextual?: Row;
};
type IntelMode = "COMMND" | "RUNNERS" | "PERFORMANCE" | "FORM" | "MP" | "NEXUS" | "STATS" | "DVNCED" | "RESULTS" | "TRACK" | "WEATHER";
type ProductView = "HOME" | "MEETINGS" | "RCE";
type RunnerSubMode = "DN" | "PROFILE" | "FORM" | "CONNECTIONS" | "EXPLINBILITY";
type BenchmarkMode = "CLASS_BENCHMARK" | "ALL_CLASSES_BENCHMARK";
type StatsMode = "JOCKEYS" | "TRAINERS";
type RatingHoverMetric = {
 label: string;
 value: string;
 tone?: string;
};
type RatingHoverSection = {
 title?: string;
 lines: string[];
};
type RatingHoverCard = {
 title: string;
 subtitle?: string;
 metrics: RatingHoverMetric[];
 sections?: RatingHoverSection[];
 footer?: string;
 x: number;
 y: number;
};



function evidenceFlag(row: Row | undefined, keys: string[]): boolean {
 if (!row) return false;
 return keys.some((key) => {
 const value = text(row[key]).trim().toUpperCase();
 return value === "YES" || value === "TRUE" || value === "1" || value === "Y";
 });
}

function hasMergedEvidencePayload(row: Row | undefined): boolean {
 return evidenceFlag(row, [
 "edgeiq_connection_evidence_available",
 "edgeiq_market_evidence_available",
 "edgeiq_hidden_gem_evidence_available",
 ]);
}

function usefulEvidenceText(value: string): boolean {
 const normalized = value.trim().toUpperCase();
 return !!normalized && !["-", "NO", "NONE", "N/", "N", "NO_SOURCE_MTCH", "NO_CONNECTION", "NO_EVIDENCE", "FLSE", "0", "NO CONNECTION NGLE TRIGGERED.", "MRKET SOURCE UNVILBLE LODED.", "NO HIDDEN GEM FLGGED."].includes(normalized);
}

function commandEvidenceSource(item: EnrichedRunner): Row | undefined {
 return {
 ...(item.row || {}),
 ...(item.runnerProfile || {}),
 ...(item.runnerForm || {}),
 ...(item.runnerTrajectory || {}),
 ...(item.runnerProjection || {}),
 ...(item.campaign || {}),
 ...(item.dna || {}),
 ...(item.explainability || {}),
 ...(item.connection || {}),
 ...(item.hiddenGem || {}),
 ...(item.mapEnrichment || {}),
 ...(item.commandEnrichment || {}),
 };
}

function commandEvidencevailable(item: EnrichedRunner, flagKeys: string[], summaryKeys: string[]): boolean {
 const source = commandEvidenceSource(item);
 if (evidenceFlag(source, flagKeys)) return true;
 return usefulEvidenceText(firstText(source, summaryKeys, ""));
}

function scoreToneValue(value: number | null): string {
 if (value === null || !Number.isFinite(value)) return "#64748b";
 if (value >= 80) return "#34d399";
 if (value >= 60) return "#ffffff";
 if (value >= 40) return "#ffffff";
 return "#f87171";
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

function findRaceShapeFallbackForRace(rows: Row[], base: Row): Row | undefined {
 const baseDate = raceDate(base);
 const baseTrack = cleanTrack(track(base));
 const baseRaceNo = raceNo(base);

 if (!baseTrack || !baseRaceNo) return undefined;

 return rows.find((row) => {
 const rowDate = raceDate(row);
 const rowTrack = cleanTrack(track(row));
 const rowRaceNo = raceNo(row);
 if (!rowTrack || !rowRaceNo) return false;
 if (baseDate && rowDate && baseDate !== rowDate) return false;
 return rowTrack === baseTrack && rowRaceNo === baseRaceNo;
 });
}

function band(row: Row | undefined, keys: string[], fallback = "-"): string {
 return firstText(row, keys, fallback).replace(/_/g, " ").toUpperCase();
}

function customerLimitedDecisionLabel(value: string): string {
 return value.toUpperCase() === "MODEL" ? "MODEL EDGE" : value;
}

function humanTrackStyle(style: string): string {
 const value = style.toUpperCase().replace(/_/g, " ").trim();
 if (!value || value === "-" || value === "NO PROFILE") return "runners without a clear historical pattern";
 if (value.includes("MIDFIELD")) return "runners settling midfield";
 if (value.includes("ON PACE")) return "on-pace runners";
 if (value.includes("LEADER")) return "leaders";
 if (value.includes("BCKMRKER")) return "backmarkers";
 return value.toLowerCase();
}

function humanBarrierPhrase(barrier: string): string {
 const value = barrier.toUpperCase().replace(/_/g, " ").trim();
 if (!value || value === "-") return "";
 if (value.includes("MIDDLE")) return "middle barriers";
 if (value.includes("INSIDE") || value.includes("LOW")) return "inside barriers";
 if (value.includes("WIDE") || value.includes("OUTSIDE") || value.includes("HIGH")) return "wide barriers";
 return value.toLowerCase();
}

function humanMovementPhrase(movement: string): string {
 const value = movement.toUpperCase().replace(/_/g, " ").trim();
 if (!value || value === "-") return "";
 if (value === "HOLDS POSITION") return "holding their position in the run";
 if (value.includes("IMPROVE")) return "improving through the run";
 if (value.includes("DROP")) return "drifting back through the run";
 return value.toLowerCase();
}

function trackDnaHeadline(style: string): string {
 const value = style.toUpperCase().replace(/_/g, " ").trim();
 if (!value || value === "-" || value === "NO PROFILE") return "No clear historical profile";
 return `Favours ${humanTrackStyle(style)}`;
}

function raceClarityNarrative(value: string): string {
 const upper = value.toUpperCase();
 if (upper.includes("WIDE OPEN")) return "highly competitive";
 if (upper.includes("CLER")) return "more straightforward";
 if (upper.includes("BLNCED")) return "balanced";
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
 if (tempo !== "-") parts.push(`Tempo projects as ${tempo}.`);
 if (confidence !== "-") parts.push(`Overall confidence sits at ${confidence}.`);

 if (topWinChance && bestValue && topWinChance === bestValue) {
 const fairText = topWinFair !== null ? ` at an EDGEiQ price of ${money(topWinFair)}` : "";
 const edgeText = bestValueEdge !== null ? ` with ${signed(bestValueEdge)}% edge` : "";
 parts.push(`${topWinChance} profiles as both the top win chance${fairText}, with the widest gap to the EDGEiQ price also sitting there${edgeText}.`);
 } else {
 if (topWinChance) {
 const fairText = topWinFair !== null ? ` at an EDGEiQ price of ${money(topWinFair)}` : "";
 parts.push(`${topWinChance} profiles as the top win chance${fairText}.`);
 }
 if (bestValue) {
 const edgeText = bestValueEdge !== null ? ` at ${signed(bestValueEdge)}% edge` : "";
 parts.push(`The widest gap to the EDGEiQ price sits with ${bestValue}${edgeText}.`);
 }
 }

 return parts.join(" ");
}

function bandColor(value: string): string {
 const v = value.toUpperCase();
 if (v.includes("VERY CLER") || v === "CLER" || v.includes("VERY HIGH") || v === "HIGH") return "#3ee68f";
 if (v.includes("BLNCED") || v.includes("MEDIUM") || v.includes("MODERATE") || v.includes("EVEN")) return "#ffffff";
 if (v.includes("OPEN") || v === "LOW" || v.includes("SLOW")) return "#fb923c";
 if (v.includes("WIDE") || v.includes("VERY LOW") || v.includes("FST") || v.includes("EXTREME")) return "#f87171";
 return "#cbd5e1";
}


function hasConnectionPayload(row: Row | undefined): boolean {
 if (!row) return false;
 if (evidenceFlag(row, ["edgeiq_connection_evidence_available"])) return true;
 const band = firstText(row, ["connection_band"], "").toUpperCase();
 if (band === "NO_EVIDENCE") return false;
 return [
 "connection_score",
 "connection_band",
 "connection_angle_1",
 "connection_angle_2",
 "connection_angle_3",
 "connection_evidence_status",
 "evidence_quality",
 "connection_positive_1",
 "connection_risk_1",
 "connection_narrative",
 "trainer_track_sr",
 "jockey_track_sr",
 "combo_sr",
 "combo_track_sr",
 "market_expectation_label",
 "sp_expectation_delta",
 ].some((key) => text(row[key]));
}

function hasDnaPayload(item: EnrichedRunner): boolean {
 if (firstNum(item.dna, ["dna_v6_2_score", "dna_score", "runner_dna_v6_1_score"]) !== null) return true;

 const hasFitBand = ["distance_fit_band", "condition_fit_band", "class_fit_band", "dna_v6_2_band", "dna_band"].some((key) => {
 const value = firstText(item.dna, [key], "").trim().toUpperCase();
 return value !== "" && value !== "-" && value !== "N/";
 });

 if (hasFitBand) return true;

 return Array.isArray(item.factorRows) && item.factorRows.length > 0;
}


function connectionSourceRow(item: EnrichedRunner): Row | undefined {
 if (hasMergedEvidencePayload(item.row)) return item.row;
 if (hasConnectionPayload(item.connection)) return item.connection;
 if (hasConnectionPayload(item.explainability)) return item.explainability;
 return item.explainability || item.connection || item.row;
}

function formSourceRow(item: EnrichedRunner): Row | undefined {
 return item.formIntelligence || item.runnerForm;
}

function saddle(row: Row): number {
 return firstNum(row, ["horse_no", "runner_no", "saddlecloth", "number", "no"]) ?? 999;
}

function barrier(row: Row): string {
 const b = firstNum(row, ["barrier", "bar"]);
 return b === null ? "-" : String(Math.trunc(b));
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

 if (blob.includes("SCRTCH")) return true;

 const explicitFlag = text(row.is_scratched).toUpperCase();
 return ["YES", "Y", "TRUE", "1"].includes(explicitFlag);
}

function isScratched(item: EnrichedRunner): boolean {
 return isScratchedRunner(item.row);
}

function isFallbackRow(item: EnrichedRunner): boolean {
 const priceStatus = firstText(item.row, ["V6_1_RESERCH_price_status"], "").toUpperCase();
 return priceStatus.includes("FLLBCK");
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

 if (edge < 0) return "PSS";
 if (score >= 65 && edge >= 18) return "MODEL EDGE";
 if (score >= 50 && edge >= 10) return "WATCH";
 if (isFallbackRow(item) && score < 60) return "LOW DT";
 if (score >= 40 && edge > 0) return "PSS";
 return "PSS";
}

function displayBetValue(item: EnrichedRunner): string {
 if (isScratched(item)) return "SCRATCHED";

 const base = decision(item.row, item.bet).toUpperCase();
 const edge = edgePct(item.row, item.bet) ?? 0;

 if (base === "WITING FEED" || base === "NO_MODEL" || base === "NO MODEL") return "WIT";
 if (base === "WATCH" && edge >= 18) return "BET";
 if (base === "WATCH") return "WATCH";
 if (base === "LEN") return "LEN";
 if (base === "PSS" || base === "MRKET COMPRESSION") return "PSS";
 return base || "WIT";
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
 const [explainabilityRows, setExplainabilityRows] = useState<Row[]>([]);
 const [connectionRows, setConnectionRows] = useState<Row[]>([]);
 const [limitedRows, setLimitedRows] = useState<Row[]>([]);
 const [customerIntelligenceRows, setCustomerIntelligenceRows] = useState<Row[]>([]);
 const [intelligenceSummaryRows, setIntelligenceSummaryRows] = useState<Row[]>([]);
 const [intelligenceScoreRows, setIntelligenceScoreRows] = useState<Row[]>([]);
 const [raceDayIntelligenceRows, setRaceDayIntelligenceRows] = useState<Row[]>([]);
 const [factorScorecardRows, setFactorScorecardRows] = useState<Row[]>([]);
 const [runnerProfileRows, setRunnerProfileRows] = useState<Row[]>([]);
 const [formIntelligenceRows, setFormIntelligenceRows] = useState<Row[]>([]);
 const [runnerFormRows, setRunnerFormRows] = useState<Row[]>([]);
 const [runnerFormHistoryRows, setRunnerFormHistoryRows] = useState<Row[]>([]);
 const [historyMasterRows, setHistoryMasterRows] = useState<Row[]>([]);
 const [historyDetailRows, setHistoryDetailRows] = useState<Row[]>([]);
 const [horseCareerRows, setHorseCareerRows] = useState<Row[]>([]);
 const [horserchetypeRows, setHorserchetypeRows] = useState<Row[]>([]);
 const [horseTrajectoryRows, setHorseTrajectoryRows] = useState<Row[]>([]);
 const [horseProjectionRows, setHorseProjectionRows] = useState<Row[]>([]);
 const [campaignIntelligenceRows, setCampaignIntelligenceRows] = useState<Row[]>([]);
 const [hiddenGemRows, setHiddenGemRows] = useState<Row[]>([]);
 const [raceShapeFallbackRows, setRaceShapeFallbackRows] = useState<Row[]>([]);
 const [mapEnrichmentRows, setMapEnrichmentRows] = useState<Row[]>([]);
 const [chaosIndexRows, setChaosIndexRows] = useState<Row[]>([]);
 const [opportunityScoreRows, setOpportunityScoreRows] = useState<Row[]>([]);
 const [commandEnrichmentRows, setCommandEnrichmentRows] = useState<Row[]>([]);
 const [formEnrichmentRows, setFormEnrichmentRows] = useState<Row[]>([]);
 const [ratingsHeatmapRows, setRatingsHeatmapRows] = useState<Row[]>([]);
  const [productMeetingRows, setProductMeetingRows] = useState<Row[]>([]);
 const [raceListRows, setRaceListRows] = useState<Row[]>([]);
  const [meetingCalendarRows, setMeetingCalendarRows] = useState<Row[]>([]);
  const [liveTrackIntelligenceRows, setLiveTrackIntelligenceRows] = useState<Row[]>([]);
  const [trackMapManifestRows, setTrackMapManifestRows] = useState<Row[]>([]);
  const [nexusContextualRows, setNexusContextualRows] = useState<Row[]>([]);
  const [formSectionalProfileRows, setFormSectionalProfileRows] = useState<Row[]>([]);
  const [gearProfileRows, setGearProfileRows] = useState<Row[]>([]);
  const [labPriceEngineRows, setLabPriceEngineRows] = useState<Row[]>([]);
  const [expandedMeetingDays, setExpandedMeetingDays] = useState<Record<string, boolean>>({ TODAY: true, TOMORROW: false, "DAY+2": false });
 const [selectedKey, setSelectedKey] = useState("");
 const [productView, setProductView] = useState<ProductView>("HOME");
 const updateProductView = (next: ProductView) => {
 setProductView(next);
 if (typeof props.onProductViewChange === "function") props.onProductViewChange(next);
 };
 const [shellMeetingKey, setShellMeetingKey] = useState("");
  const [shellTrack, setShellTrack] = useState("");
  const [shellRaceNo, setShellRaceNo] = useState("");
  const [shellRaceDate, setShellRaceDate] = useState("");
  const [shellRaceKey, setShellRaceKey] = useState("");
 const [raceRailCollapsed, setRaceRailCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
 const [intelMode, setIntelMode] = useState<IntelMode>("COMMND");
 const [runnerSubMode, setRunnerSubMode] = useState<RunnerSubMode>("DN");
 const [labModule, setLabModule] = useState("TRAINERS");
 const [statsMode, setStatsMode] = useState<StatsMode>("JOCKEYS");
 const [formBenchmarkMode, setFormBenchmarkMode] = useState<BenchmarkMode>("CLASS_BENCHMARK");
 const [priceEngineAdjustments, setPriceEngineAdjustments] = useState<Record<string, number>>({});
 const [ratingHover, setRatingHover] = useState<RatingHoverCard | null>(null);
 const [historicalDrawerOpen, setHistoricalDrawerOpen] = useState(false);
 const [selectedHistoricalRun, setSelectedHistoricalRun] = useState<Row | null>(null);
 const [historicalDrawerRuns, setHistoricalDrawerRuns] = useState<Row[]>([]);
 const [fullHistoryRunner, setFullHistoryRunner] = useState<EnrichedRunner | null>(null);
 const [historicalDrawerSourceLabel, setHistoricalDrawerSourceLabel] = useState("LST STRT");
 const [historicalDrawerRunnerKey, setHistoricalDrawerRunnerKey] = useState("");
 const [historicalDrawerRunnerName, setHistoricalDrawerRunnerName] = useState("");

 useEffect(() => {
 let active = true;

 async function run(): Promise<void> {
 setLoading(true);

 const data = await loadEdgeIQData();

 if (!active) return;

 setRunnerRows(data.runner);
 setRunnerIntelRows(data.runnerIntel);
 setV8Rows(data.v8);
 setBetRows(data.bet);
 setReliabilityRows(data.rel);
 setIntelligenceCardRows(data.cards);
 setBriefingRows(data.briefing);
 setMarketIntelRows(data.marketIntel);
 setVerdictRows(data.verdict);
 setTrackIntelRows(data.trackIntel);
 setHorseDrawerRows(data.horseDrawer);
 setRunnerDnaDrawerRows(data.runnerDnaDrawer);
 setExplainabilityRows(data.explainability);
 setConnectionRows(data.connection);
 setFactorScorecardRows(data.factorScorecard);
 setLimitedRows(data.limited);
 setCustomerIntelligenceRows(data.customerIntelligence);
 setIntelligenceSummaryRows(data.intelligenceSummary);
 setRaceDayIntelligenceRows(data.raceDayIntelligence);
 setRunnerProfileRows(data.runnerProfile);
 setFormIntelligenceRows(data.formIntelligence);
 setRunnerFormRows(data.runnerForm);
 setRunnerFormHistoryRows(data.runnerFormHistory);
 setHistoryMasterRows(data.historyMaster);
 setHistoryDetailRows(data.historyDetail);
 setHorseCareerRows(data.horseCareer);
 setHorserchetypeRows(data.horserchetype);
 setHorseTrajectoryRows(data.horseTrajectory);
 setHorseProjectionRows(data.horseProjection);
 setCampaignIntelligenceRows(data.campaignIntelligence);
 setHiddenGemRows(data.hiddenGem);
 setRaceShapeFallbackRows(data.raceShapeFallback);
 setMapEnrichmentRows(data.mapEnrichment);
 setChaosIndexRows(data.chaosIndex);
 setOpportunityScoreRows(data.opportunityScore);
 setCommandEnrichmentRows(data.commandEnrichment);
 setFormEnrichmentRows(data.formEnrichment);
 setRatingsHeatmapRows(data.ratingsHeatmap);
 setProductMeetingRows(data.productMeetings);
 setRaceListRows(data.raceList);
 setMeetingCalendarRows(data.meetingCalendar);
 setLiveTrackIntelligenceRows(data.liveTrackIntelligence);
 setTrackMapManifestRows(data.trackMapManifest);
 setNexusContextualRows(data.nexusContextual.length ? data.nexusContextual : data.nexusContextualFallback);
 setFormSectionalProfileRows(data.formSectionalProfile);
 setGearProfileRows(data.gearProfile);
 setLabPriceEngineRows(data.labPriceEngine);
 setIntelligenceScoreRows(data.intelligenceScore);
 setLoading(false);
 }

 run();

 return () => {
 active = false;
 };
 }, []);

 const selectedTrack = cleanTrack(shellTrack || props.selectedTrack || props.currentRace?.track);
 const selectedRaceNo = text(shellRaceNo || props.selectedRaceNo || props.currentRace?.raceNo || props.currentRace?.race_no);
 const selectedRaceDate = text(shellRaceDate || props.currentRace?.raceDate || props.currentRace?.race_date || props.currentRace?.race_date_raw);
 const meetingDisplayState = getMeetingDisplayState(props.currentMeeting);
 const futureMeetingWithFields = meetingDisplayState === "FUTURE_MEETING_WITH_FIELDS";
 const futureMeetingWithoutFields = meetingDisplayState === "FUTURE_MEETING_WITHOUT_FIELDS";
 const futureMeetingTrack = text(props.currentMeeting?.track);
 const futureMeetingDate = text(props.currentMeeting?.raceDate);
 const futureMeetingStatus = text(props.currentMeeting?.meetingStatus).replace(/_/g, " ") || "FIELDS PENDING";
 const futureMeetingDayBucket = text(props.currentMeeting?.dayBucket).replace("DY+2", "DY +2") || "UPCOMING";
 const futureMeetingSelectedRace =
 futureMeetingTrack && selectedRaceNo
 ? `${futureMeetingTrack} R${selectedRaceNo}`
 : futureMeetingTrack || "Upcoming race";

 const raceRows = useMemo(() => buildRaceRows({
  runnerRows,
  selectedTrack,
  selectedRaceNo,
  selectedRaceDate,
  currentRace: props.currentRace,
  saddle,
 }), [runnerRows, selectedTrack, selectedRaceNo, selectedRaceDate, props.currentRace]);

 const productShellRaces = useMemo(() => buildProductShellRaces({
  runnerRows,
  raceListRows,
 }), [runnerRows, raceListRows]);

 const productShellMeetings = useMemo(() => buildProductShellMeetings({
  productShellRaces,
  productMeetingRows,
  meetingCalendarRows,
  liveTrackIntelligenceRows,
  trackMapManifestRows,
 }), [productShellRaces, productMeetingRows, meetingCalendarRows, liveTrackIntelligenceRows, trackMapManifestRows]);

 const selectedShellMeeting = productShellMeetings.find((meeting) => meeting.meetingKey === shellMeetingKey) || null;
 const selectedShellMeetingRaces = selectedShellMeeting
  ? productShellRaces.filter((race) => race.meetingKey === selectedShellMeeting.meetingKey)
  : [];
 const selectedShellRace =
 shellRaceKey
 ? productShellRaces.find((race) => race.raceKey === shellRaceKey) || null
 : selectedRaceNo && selectedShellMeeting
 ? productShellRaces.find((race) => race.meetingKey === selectedShellMeeting.meetingKey && race.raceNoValue === selectedRaceNo) || null
 : null;
 const openShellMeeting = (meetingKey: string) => {
  setShellMeetingKey(meetingKey);
  setShellTrack("");
  setShellRaceNo("");
  setShellRaceDate("");
  setShellRaceKey("");
  setSelectedKey("");
  setIntelMode("COMMND");
  updateProductView("MEETINGS");
 };
 const openShellRace = (race: typeof productShellRaces[number]) => {
  if (race.fieldSize <= 0) {
  setShellMeetingKey(race.meetingKey);
  setShellTrack("");
  setShellRaceNo("");
  setShellRaceDate("");
  setShellRaceKey("");
  setSelectedKey("");
  updateProductView("MEETINGS");
  return;
  }
  setShellMeetingKey(race.meetingKey);
  setShellTrack(race.trackName);
  setShellRaceNo(race.raceNoValue);
  setShellRaceDate(race.meetingDate);
  setShellRaceKey(race.raceKey);
  updateProductView("RCE");
  setSelectedKey("");
  setIntelMode("COMMND");
 };

 const {
  historyMasterByHorse,
  historyMasterByTrackRaceHorse,
  historyDetailByHorse,
  historyDetailByMergeKey,
  historyDetailByLooseMergeKey,
  runnerFormHistoryByHorse,
  horseCareerByHorse,
  horserchetypeByHorse,
  horseTrajectoryByHorse,
  horseProjectionByHorse,
 } = useMemo(() => buildHistoryIndexes({
  historyMasterRows,
  historyDetailRows,
  runnerFormHistoryRows,
  horseCareerRows,
  horserchetypeRows,
  horseTrajectoryRows,
  horseProjectionRows,
  historyRunnerLookupKey,
  historyDateValue,
  historyDetailMergeKey,
  historyDetailMergeKeyLoose,
 }), [historyMasterRows, historyDetailRows, runnerFormHistoryRows, horseCareerRows, horserchetypeRows, horseTrajectoryRows, horseProjectionRows]);
 const formEnrichmentByRunnerKey = useMemo(() => {
 const map = new Map<string, Row>();
 formEnrichmentRows.forEach((formRow) => {
 const key =
 firstText(formRow, ["runner_key"], "") ||
 [
 firstText(formRow, ["race_date"], ""),
 cleanTrack(firstText(formRow, ["track"], "")),
 `R${firstText(formRow, ["race_no"], "").replace(/^R/i, "")}`,
 cleanHorseLoose(firstText(formRow, ["horse_key"], "")) || cleanHorseLoose(firstText(formRow, ["horse"], "")),
 ].join("_");
 if (key) map.set(key, formRow);
 });
 return map;
 }, [formEnrichmentRows]);

 const enriched = useMemo(() => buildEnrichedRunners({
  raceRows,
  formEnrichmentRows,
  runnerIntelRows,
  v8Rows,
  betRows,
  reliabilityRows,
  horseDrawerRows,
  runnerDnaDrawerRows,
  explainabilityRows,
  connectionRows,
  limitedRows,
  customerIntelligenceRows,
  intelligenceSummaryRows,
  raceDayIntelligenceRows,
  runnerProfileRows,
  formIntelligenceRows,
  runnerFormRows,
  horseCareerByHorse,
  horserchetypeByHorse,
  horseTrajectoryByHorse,
  horseProjectionByHorse,
  campaignIntelligenceRows,
  hiddenGemRows,
  commandEnrichmentRows,
  mapEnrichmentRows,
  ratingsHeatmapRows,
  nexusContextualRows,
  historyMasterByHorse,
  historyMasterByTrackRaceHorse,
  historyDetailByHorse,
  runnerFormHistoryByHorse,
  historyDetailByMergeKey,
  historyDetailByLooseMergeKey,
  intelligenceScoreRows,
  factorScorecardRows,
  findSidecar,
  findDnaSidecar,
  findConnectionSidecar,
  findSidecarByRaceHorse,
  findCampaignSidecar,
  findHiddenGemForRunner,
  findCommandEnrichmentSidecar,
  findNexusContextualSidecar,
  findFormEnrichmentSidecar,
  findHistoryMasterRowsForRunner,
  mergeRunnerHistoryRows,
 }), [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, explainabilityRows, connectionRows, factorScorecardRows, limitedRows, intelligenceScoreRows, customerIntelligenceRows, intelligenceSummaryRows, runnerProfileRows, formIntelligenceRows, runnerFormRows, historyMasterByHorse, historyMasterByTrackRaceHorse, historyDetailByHorse, historyDetailByMergeKey, historyDetailByLooseMergeKey, runnerFormHistoryByHorse, horseCareerByHorse, horserchetypeByHorse, horseTrajectoryByHorse, horseProjectionByHorse, campaignIntelligenceRows, hiddenGemRows, commandEnrichmentRows, mapEnrichmentRows, formEnrichmentRows, ratingsHeatmapRows, nexusContextualRows]);

 const rankedEnriched = useMemo(() => buildRankedEnriched({
  enriched,
  runnerRowKey,
  winPct,
 }), [enriched]);

 const decisionBoardGridCols =
 "55px 245px 80px 150px 100px 96px 96px 96px 110px 120px";

 const decisionBoardLegend =
 "MODEL RANK | WIN CHANCE | FAIR PRICE | MARKET | SETUP GAP | EDGEiQ CONFIDENCE | MARKET READ";

 const selected =
 rankedEnriched.find((item) => runnerRowKey(item.row) === selectedKey) ||
 rankedEnriched.find((item) => (edgePct(item.row, item.bet) ?? -999) > 0) ||
 rankedEnriched[0];

 const header = raceRows[0];
 const futureMeetingSelectedMeta = [
 header ? distance(header) : num(props.currentRace?.distance) !== null ? `${num(props.currentRace?.distance)}m` : "",
 header && raceClass(header) !== "-" ? raceClass(header) : text(props.currentRace?.raceClass),
 text(props.currentRace?.raceTime),
 ]
 .filter(Boolean)
 .join(" | ");
 const futureMeetingFieldCount = raceRows.length || (Array.isArray(props.currentRace?.rows) ? props.currentRace.rows.length : 0);

 const {
  intelligenceCard,
  briefing,
  marketIntel,
  verdict,
  trackIntel,
  raceShapeFallback,
  chaosIndex,
  opportunityScore,
  raceClarity,
  expectedTempo,
  fallbackRaceShapeLabel,
  fallbackTempoLabel,
  fallbackPressureLabel,
  fallbackPacedvantageLabel,
  fallbackRaceShapeNarrative,
  displayExpectedTempo,
  bettingConfidence,
  raceStory,
  mostLikelyWinner,
  bestValue,
  mostLikelyFair,
  bestValueEdge,
  bestBet,
  verdictNarrative,
  briefingNarrative,
  marketComment,
  trackProfile,
  trackBarrier,
  trackMovement,
  trackDnaConfidence,
  trackDnaSampleWinners,
  bestTrackFitRunner,
  bestTrackFitScore,
  eliteFitCount,
  strongFitCount,
  positiveFitCount,
  negativeFitCount,
  poorFitCount,
  trackdvantageSummary,
  trackRiskSummary,
  trackIntelligenceComment,
  conditionLabel,
  railDisplay,
  trackRiskCount,
  trackDnaHeaderCopy,
  trackDnaFitContext,
  customerTrackdvantage,
  customerTrackRisk,
  customerTrackInsight,
  customerBriefingNarrative,
  activeRaceRows,
 } = useMemo(() => buildRaceIntelligenceSummary({
  header,
  currentRace: props.currentRace,
  rankedEnriched,
  intelligenceCardRows,
  briefingRows,
  marketIntelRows,
  verdictRows,
  trackIntelRows,
  raceShapeFallbackRows,
  chaosIndexRows,
  opportunityScoreRows,
  findRaceSidecar,
  findRaceShapeFallbackForRace,
  band,
  trackDnaHeadline,
  humanBarrierPhrase,
  humanTrackStyle,
  buildBriefingNarrative,
  isScratched,
 }), [header, props.currentRace, rankedEnriched, intelligenceCardRows, briefingRows, marketIntelRows, verdictRows, trackIntelRows, raceShapeFallbackRows, chaosIndexRows, opportunityScoreRows]);
 useEffect(() => {
 console.log("[EDGEiQ runner row audit]", JSON.stringify({
 selectedMeeting: selectedShellMeeting
 ? {
 meetingKey: selectedShellMeeting.meetingKey,
 track: selectedShellMeeting.trackName,
 date: selectedShellMeeting.meetingDate,
 }
 : null,
 selectedRace: selectedShellRace
 ? {
 raceKey: selectedShellRace.raceKey,
 track: selectedShellRace.trackName,
 date: selectedShellRace.meetingDate,
 raceNo: selectedShellRace.raceNoValue,
 fieldSize: selectedShellRace.fieldSize,
 }
 : {
 track: shellTrack || props.selectedTrack || props.currentRace?.track || "",
 date: selectedRaceDate,
 raceNo: selectedRaceNo,
 },
 raceKey: selectedShellRace?.raceKey || shellRaceKey || "",
 meetingKey: selectedShellMeeting?.meetingKey || shellMeetingKey || "",
 runnerRowsLength: runnerRows.length,
 "runnerRows.length": runnerRows.length,
 runnerRows: { length: runnerRows.length },
 intelligenceRowsLength: runnerIntelRows.length,
 "intelligenceRows.length": runnerIntelRows.length,
 intelligenceRows: { length: runnerIntelRows.length },
 raceIntelligenceRowsLength: intelligenceCardRows.length,
 filteredRowsLength: raceRows.length,
 "filteredRows.length": raceRows.length,
 filteredRows: { length: raceRows.length },
 activeRaceRowsLength: activeRaceRows.length,
 }));
 }, [selectedShellMeeting, selectedShellRace, shellTrack, shellRaceKey, shellMeetingKey, selectedRaceDate, selectedRaceNo, runnerRows.length, runnerIntelRows.length, intelligenceCardRows.length, raceRows.length, activeRaceRows.length, props.selectedTrack, props.currentRace]);
 const {
  livePriceRowCount,
  overlayCountComputed,
  strongOverlayCountComputed,
  topModelRow,
  bestValueItem,
  topWinChanceRunner,
  topWinChanceFair,
  bestValueRunner,
  bestValueEdgeDisplay,
  marketEfficiency,
  overlayCountDisplay,
  strongOverlayCountDisplay,
  marketStatus,
  marketStatusTone,
  marketEfficiencyTone,
  raceAssessmentNarrative,
 } = useMemo(() => buildRaceDashboardSummary({
  activeRaceRows,
  rankedEnriched,
  marketIntel,
  mostLikelyWinner,
  mostLikelyFair,
  bestValue,
  bestValueEdge,
  raceClarity,
  displayExpectedTempo,
  bettingConfidence,
  band,
  bandColor,
 }), [activeRaceRows, rankedEnriched, marketIntel, mostLikelyWinner, mostLikelyFair, bestValue, bestValueEdge, raceClarity, displayExpectedTempo, bettingConfidence]);
 const {
  selectedIsScratched,
  selectedModelRank,
  selectedDisplayBet,
  selectedDisplayGrade,
  selectedLimitedScore,
  selectedLimitedScoreNumeric,
  selectedExplainability,
  selectedCustomerIntel,
  selectedIntelligenceSummary,
  selectedRaceDayIntelligence,
  selectedEdgeiqScore,
  selectedEdgeiqBandRaw,
  selectedEdgeiqBand,
  selectedEdgeiqVerdict,
  selectedEdgeiqReasonsRaw,
  selectedEdgeiqRisksRaw,
  selectedEdgeiqReasons,
  selectedEdgeiqRisks,
  selectedStableIntentBandRaw,
  selectedStableIntentBand,
  selectedContextSignalCount,
  selectedCustomerDnaBandRaw,
  selectedCustomerDnaBand,
  selectedIntelligenceSummaryTitle,
  selectedIntelligenceSummaryText,
  selectedIntelligencectionText,
  selectedRaceDayCondition,
  selectedRaceDayRail,
  selectedRaceDayTempo,
  selectedRaceDayPressure,
  selectedRaceDayTrackProfile,
  selectedRaceDayTrackConfidence,
  selectedRaceDayRead,
  selectedConnectionSource,
  selectedConnectionLoaded,
  selectedRaceExplainability,
  selectedExplainabilityModelRankRaw,
  selectedExplainabilityModelRank,
  selectedExplainabilityConfidenceBand,
  selectedExplainabilityConfidenceScore,
  selectedExplainabilityTrendLabel,
  selectedExplainabilityTrendDelta,
  selectedExplainabilityTrendDisplay,
  selectedExplainabilityRaceTempo,
  selectedExplainabilityRaceShape,
  selectedExplainabilityWhy,
  selectedExplainabilityConfidenceExplanation,
  selectedExplainabilityTrendSummary,
  selectedConnectionBand,
  selectedConnectionEvidenceQuality,
  selectedConnectionEvidenceStatus,
  selectedExplainabilityConnectionScore,
  selectedConnectionngles,
  selectedConnectionReadPatterns,
  selectedConnectionEvidencePatterns,
  selectedConnectionRisk,
  selectedConnectionRiskMeaningful,
  selectedConnectionPositiveItems,
  selectedConnectionRiskItems,
  selectedConnectionNarrative,
  selectedMergedMarketvailable,
  selectedMergedMarketSummary,
  selectedMergedHiddenGemvailable,
  selectedMergedHiddenGemSummary,
  selectedConnectionMarketLabel,
  selectedConnectionSpDelta,
  selectedConnectionTrainerTrackSr,
  selectedConnectionJockeyTrackSr,
  selectedConnectionComboSr,
  selectedConnectionComboTrackSr,
  selectedConnectionSpSampleStarts,
  selectedExplainabilitySupports,
  selectedExplainabilityRisks,
  selectedRaceShapeLabel,
  selectedRaceTempoLabel,
  selectedRacePacedvantageRunner,
  selectedRaceLatePowerBeneficiary,
  selectedRacePressureRiskRunner,
  selectedRaceShapeStory,
  selectedRacePacedvantageDisplay,
  selectedRacePressureDisplay,
  selectedRaceShapeStoryDisplay,
  selectedLimitedDecision,
  selectedBetQuality,
  raceShapeFallbackLoaded,
 } = useMemo(() => buildSelectedRunnerCore({
  selected,
  topModelRow,
  activeRaceRows,
  displayExpectedTempo,
  fallbackRaceShapeLabel,
  fallbackTempoLabel,
  fallbackPressureLabel,
  fallbackPacedvantageLabel,
  fallbackRaceShapeNarrative,
  raceAssessmentNarrative,
  raceClarity,
  isScratched,
  displayBetValue,
  displayGradeValue,
  limitedScoreValue,
  computedLimitedScore,
  connectionSourceRow,
  hasConnectionPayload,
  evidenceFlag,
  limitedDecisionValue,
  displayBetQualityValue,
  firstText,
  firstNum,
  renderMetricValue,
  text,
 }), [selected, topModelRow, activeRaceRows, displayExpectedTempo, fallbackRaceShapeLabel, fallbackTempoLabel, fallbackPressureLabel, fallbackPacedvantageLabel, fallbackRaceShapeNarrative, raceAssessmentNarrative, raceClarity]);

 const selectedProjectionBand = selected
 ? firstText(selected.row, ["projection_band_V6_1_RESERCH", "projection_band_v5_2"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedProjectionGap = selected
 ? firstNum(selected.row, ["projection_gap_V6_1_RESERCH", "projection_gap_v5_2"])
 : null;
 const selectedProjectionStatus = selected
 ? firstText(selected.row, ["V6_1_RESERCH_price_status"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedProjectedSpd = selected ? projectedSpdValue(selected) : null;
 const selectedSectional = selected
 ? firstNum(selected.runnerIntel, ["sectional_weapon_score"]) ??
 firstNum(selected.drawer, ["sectional_weapon_score"]) ??
 firstNum(selected.intel, ["intelligence_sectional_component_v1"])
 : null;
 const selectedLatePower = selected
 ? firstNum(selected.runnerIntel, ["late_power_index"]) ?? firstNum(selected.drawer, ["late_power_index"])
 : null;
 const selectedProfile = selected?.runnerProfile;
 const selectedHorserchetype = selected ? firstText(selectedProfile, ["horse_archetype"], "-") : "-";
 const selectedProfileStrength = selected ? firstText(selectedProfile, ["profile_strength"], "-").replace(/_/g, " ").toUpperCase() : "-";
 const selectedProfileCareerStarts = selected ? firstText(selectedProfile, ["career_starts"], "-") : "-";
 const selectedProfileCareerWins = selected ? firstText(selectedProfile, ["career_wins"], "-") : "-";
 const selectedProfileCareerPlaces = selected ? firstText(selectedProfile, ["career_places"], "-") : "-";
 const selectedProfileCareerWinPct = selected ? firstText(selectedProfile, ["career_win_pct"], "-") : "-";
 const selectedProfileCareerPlacePct = selected ? firstText(selectedProfile, ["career_place_pct"], "-") : "-";
 const selectedDistanceProfile = selected ? firstText(selectedProfile, ["distance_profile"], "-") : "-";
 const selectedConditionProfile = selected ? firstText(selectedProfile, ["condition_profile"], "-") : "-";
 const selectedTrackProfile = selected ? firstText(selectedProfile, ["track_profile"], "-") : "-";
 const selectedClassProfile = selected ? firstText(selectedProfile, ["class_profile"], "-") : "-";
 const selectedProfileSummary = selected ? firstText(selectedProfile, ["profile_summary"], "") : "";
 const {
  selectedCareerIntel,
  selectedrchetypeIntel,
  selectedTrajectoryIntel,
  selectedProjectionIntel,
  selectedCampaignIntel,
  selectedHiddenGemIntel,
  selectedCareerStartsDisplay,
  selectedCareerWinsDisplay,
  selectedCareerPlacesDisplay,
  selectedCareerPeakRating,
  selectedCareerverageRating,
  selectedCareerMedianRating,
  selectedCareerLatestRating,
  selectedCareerLast5verage,
  selectedCareerLast10verage,
  selectedCareerConsistency,
  selectedCareerVolatility,
  selectedCareerBand,
  selectedCareerTrend,
  selectedCareerBestTrack,
  selectedCareerBestDistance,
  selectedCareerBestCondition,
  selectedCareerBestClass,
  selectedCareerWorstTrack,
  selectedCareerWorstDistance,
  selectedCareerWorstCondition,
  selectedCareerPeakDate,
  selectedCareerPeakTrack,
  selectedCareerPeakDistance,
  selectedCareerPeakClass,
  selectedCampaignProfile,
  selectedCampaignProfileBand,
  selectedCampaignCurrentPrepStage,
  selectedCampaignPrepStageLabel,
  selectedCampaignPeakWindowStart,
  selectedCampaignPeakWindowEnd,
  selectedCampaignRiskScore,
  selectedCampaignRiskBand,
  selectedCampaignEvidenceStatus,
  selectedCampaignNarrative,
  selectedCampaignHistoryRuns,
  selectedCampaignStageSampleCount,
  selectedCampaignPrepDisplay,
  selectedCampaignPeakWindowDisplay,
  selectedHiddenGemDisplayBand,
  selectedHiddenGemctionable,
  selectedHiddenGemHistorical,
  selectedHiddenGemRecencyBand,
  selectedHiddenGemDaysSince,
  selectedHiddenGemScore,
  selectedHiddenGemTrigger,
  selectedHiddenGemNarrative,
  selectedHiddenGemDate,
  selectedHiddenGemTrack,
  selectedHiddenGemRaceNo,
  selectedHiddenGemLoaded,
  selectedHiddenGemStatusDisplay,
  selectedPerformanceIntelligenceBand,
  selectedHiddenGemgeDisplay,
  selectedCareerrchetype,
  selectedDevelopmentStage,
  selectedImprovementProfile,
  selectedConsistencyProfile,
  selectedFreshnessProfile,
  selectedrchetypeDistanceProfile,
  selectedSeasonalityProfile,
  selectedCareerPeakgeStage,
  selectedRunsSincePeak,
  selectedPeakTrend,
  selectedCareerLast3verage,
  selectedCareerPercentileScore,
  selectedBoomOrBustFlag,
  selectedLateMaturerFlag,
  selectedEarlyMaturerFlag,
  selectedImproverFlag,
  selectedRegressorFlag,
  selectedTrajectoryDirection,
  selectedTrajectoryStrength,
  selectedTrajectoryScore,
  selectedPointsOffPeak,
  selectedPercentOfPeak,
  selectedRunsSincePeakDisplay,
  selectedDaysSincePeakDisplay,
  selectedImprovementLast3,
  selectedImprovementLast5,
  selectedImprovementLast10,
  selectedBounceRisk,
  selectedRegressionRisk,
  selectedBreakoutPotential,
  selectedCareerPhase,
  selectedProjectionOutlookBand,
  selectedProjectionOutlookConfidence,
  selectedNextRunProjection,
  selectedCeilingProjection,
  selectedFloorProjection,
  selectedExpectedImprovement,
  selectedExpectedRegression,
  selectedImprovementProbability,
  selectedRegressionProbability,
  selectedPeakRevisitProbability,
  selectedBreakoutProbability,
  selectedBounceProbability,
  selectedRunsToPeakEstimate,
  selectedDaysToPeakEstimate,
  selectedRunnerForm,
  selectedRunnerHistory,
  selectedRatedHistory,
  selectedRatedHistoryChronological,
  selectedRecentRatedHistory,
  selectedRecentRatedHistoryChronological,
  selectedHistoryLastRun,
  selectedHistoryPeakRun,
  selectedFormSignal,
  selectedFormCycle,
  selectedRatingTrend,
  selectedRatingTrendDelta,
  selectedLastStartRatingValue,
  selectedAVGRatingLast5Value,
  selectedBestRatingLast5Value,
  selectedLastStartRating,
  selectedAVGRatingLast5,
  selectedBestRatingLast5,
  selectedRating1,
  selectedRating2,
  selectedRating3,
  selectedRating4,
  selectedRating5,
  selectedRecentRatingsFromForm,
  selectedRecentRatingsFromHistory,
  selectedRecentRatings,
  selectedFormNarrative,
  selectedFormPerformanceLabel,
  selectedFormRunCards,
  selectedTodayProjectionFigure,
  selectedHistoricalRunDate,
  selectedHistoricalRunTrack,
  selectedHistoricalRunRaceNo,
  selectedHistoricalRunDistance,
  selectedHistoricalRunClass,
  selectedHistoricalRunCondition,
  selectedHistoricalRunPosition,
  selectedHistoricalRunFieldSize,
  selectedHistoricalRunBarrier,
  selectedHistoricalRunJockey,
  selectedHistoricalRunWeight,
  selectedHistoricalRunSp,
  selectedHistoricalRunFigure,
  selectedHistoricalRunRaceStrength,
  selectedHistoricalRunRaceStrengthValue,
  selectedHistoricalRunMargin,
  selectedHistoricalRunPos800,
  selectedHistoricalRunPos400,
  selectedHistoricalTodayDifference,
  selectedHistoricalComparisonMax,
  selectedHistoricalRunSummaryLine,
  selectedHistoricalCareerRank,
  selectedHistoricalCareerRankDisplay,
  selectedHistoricalRunSequence,
  selectedCareerPeakRunSequence,
  selectedHistoricalRunsBeforePeak,
  selectedTodayVsCareerPeakDifference,
  selectedTodayVsCareerPeakNarrative,
  selectedHistoricalCareerNarrative,
  selectedHistoricalPeakTimingNarrative,
  selectedHistoricalPeakPercent,
  selectedHistoricalPeakPercentNarrative,
  selectedHistoricalFreshnessNarrative,
  selectedHistoricalrchetypeNarrative,
  selectedPointsOffPeakNarrative,
  selectedTrajectoryNarrative,
  selectedBreakoutNarrative,
  selectedCareerPhaseNarrative,
  selectedProjectionImprovementNarrative,
  selectedProjectionCeilingNarrative,
  selectedProjectionNextRunNarrative,
  selectedProjectionRiskNarrative,
 } = useMemo(() => buildSelectedRunnerProfile({
  selected,
  selectedIsScratched,
  selectedProfileCareerStarts,
  selectedProfileCareerWins,
  selectedProfileCareerPlaces,
  selectedHorserchetype,
  selectedDistanceProfile,
  selectedHistoricalRun,
  firstText,
  firstNum,
  renderMetricValue,
  customerPerformanceNarrative,
  performanceIntelligenceLabel,
  formatCampaignStage,
  formatCampaignWindow,
  ratedHistoryRows,
  historyDateValue,
  historyRatingValue,
  historyRunKey,
  formatHistoryDate,
  historyDateText,
  drawerValue,
  historyTrackText,
  historyDistanceText,
  historyClassText,
  historyGoingText,
  historyJockeyText,
  historyFinishText,
  historySpText,
  historyRaceNoText,
  historyFieldSizeText,
  historyBarrierText,
  historyWeightText,
  historyRaceStrengthText,
  ordinal,
  projectionRatingValue,
  num,
 }), [selected, selectedIsScratched, selectedProfileCareerStarts, selectedProfileCareerWins, selectedProfileCareerPlaces, selectedHorserchetype, selectedDistanceProfile, selectedHistoricalRun]);

 const selectedLast5Form = selected ? firstText(selected.drawer, ["last_5_form_profile"], "-") : "-";
 const selectedProfileQuality = selected ? firstText(selected.drawer, ["profile_quality"], "-").replace(/_/g, " ").toUpperCase() : "-";
 const selectedDominantRunStyle = selected ? firstText(selected.drawer, ["dominant_run_style", "run_style"], "-").replace(/_/g, " ").toUpperCase() : "-";
 const selectedSectionalStrengthRating = selected ? firstText(selected.drawer, ["sectional_strength_rating"], "-") : "-";
 const selectedSectionalStrengthBand = selected ? firstText(selected.drawer, ["sectional_strength_band"], "-").replace(/_/g, " ").toUpperCase() : "-";
 const selectedDnaScore = selected ? firstText(selected.dna, ["dna_v6_2_score", "runner_dna_v6_1_score"], firstText(selectedProfile, ["dna_v6_2_score", "dna_score"], "-")) : "-";
 const selectedDnaBand = selected ? firstText(selected.dna, ["dna_v6_2_band", "runner_dna_v6_1_band"], firstText(selectedProfile, ["dna_v6_2_band", "dna_band"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedRunnerProfileDnaDisplay = selectedIsScratched
 ? "-"
 : selectedDnaBand !== "-"
 ? selectedDnaBand
 : selectedDnaScore;
 const selectedDnaRank = selected ? firstText(selected.dna, ["runner_dna_v6_2_rank_in_race", "runner_dna_v6_1_rank_in_race"], "-") : "-";
 const selectedStrongestFactor = selected ? firstText(selected.dna, ["strongest_factor_v6_2", "strongest_factor_v6_1"], firstText(selectedProfile, ["positive_1_factor"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedStrongestFactorScore = selected ? firstText(selected.dna, ["strongest_factor_score_v6_2", "strongest_factor_score_v6_1"], "-") : "-";
 const selectedWeakestFactor = selected ? firstText(selected.dna, ["weakest_factor_v6_2", "weakest_factor_v6_1"], firstText(selectedProfile, ["negative_1_factor"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedWeakestFactorScore = selected ? firstText(selected.dna, ["weakest_factor_score_v6_2", "weakest_factor_score_v6_1"], "-") : "-";
 const selectedDistanceScore = selected ? firstText(selected.dna, ["distance_fit_score"], "-") : "-";
 const selectedDistanceBand = selected ? firstText(selected.dna, ["distance_fit_band"], "-").replace(/_/g, " ").toUpperCase() : "-";
 const selectedConditionScore = selected ? firstText(selected.dna, ["condition_fit_score"], "-") : "-";
 const selectedConditionBand = selected ? firstText(selected.dna, ["condition_fit_band"], "-").replace(/_/g, " ").toUpperCase() : "-";
 const selectedClassScore = selected ? firstText(selected.dna, ["class_fit_score"], "-") : "-";
 const selectedClassBand = selected ? firstText(selected.dna, ["class_fit_band"], "-").replace(/_/g, " ").toUpperCase() : "-";
 const selectedDnaNarrative = selected ? firstText(selected.dna, ["impact_explanation", "runner_dna_v6_2_narrative", "runner_dna_v6_1_narrative"], "") : "";
 const selectedPositive1Factor = selected ? firstText(selected.dna, ["positive_1_factor"], firstText(selectedProfile, ["positive_1_factor"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedPositive1Impact = selected ? firstText(selected.dna, ["positive_1_impact"], firstText(selectedProfile, ["positive_1_impact"], "-")) : "-";
 const selectedPositive2Factor = selected ? firstText(selected.dna, ["positive_2_factor"], firstText(selectedProfile, ["positive_2_factor"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedPositive2Impact = selected ? firstText(selected.dna, ["positive_2_impact"], firstText(selectedProfile, ["positive_2_impact"], "-")) : "-";
 const selectedPositive3Factor = selected ? firstText(selected.dna, ["positive_3_factor"], firstText(selectedProfile, ["positive_3_factor"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedPositive3Impact = selected ? firstText(selected.dna, ["positive_3_impact"], firstText(selectedProfile, ["positive_3_impact"], "-")) : "-";
 const selectedNegative1Factor = selected ? firstText(selected.dna, ["negative_1_factor"], firstText(selectedProfile, ["negative_1_factor"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedNegative1Impact = selected ? firstText(selected.dna, ["negative_1_impact"], firstText(selectedProfile, ["negative_1_impact"], "-")) : "-";
 const selectedNegative2Factor = selected ? firstText(selected.dna, ["negative_2_factor"], firstText(selectedProfile, ["negative_2_factor"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedNegative2Impact = selected ? firstText(selected.dna, ["negative_2_impact"], firstText(selectedProfile, ["negative_2_impact"], "-")) : "-";
 const selectedNegative3Factor = selected ? firstText(selected.dna, ["negative_3_factor"], firstText(selectedProfile, ["negative_3_factor"], "-")).replace(/_/g, " ").toUpperCase() : "-";
 const selectedNegative3Impact = selected ? firstText(selected.dna, ["negative_3_impact"], firstText(selectedProfile, ["negative_3_impact"], "-")) : "-";
 const selectedFactorRows = selected?.factorRows || [];
 const selectedCurrentDecision = selected ? decision(selected.row, selected.bet) : "-";
 const selectedLivePrice = selected && !selectedIsScratched ? money(livePrice(selected.row, selected.bet)) : "-";
 const selectedFairPrice = selected && !selectedIsScratched ? money(limitedAdjustedPrice(selected) ?? fairPrice(selected.row, selected.bet)) : "-";
 const selectedEdge = selected && !selectedIsScratched ? pct(edgePct(selected.row, selected.bet)) : "-";
 const selectedHasCurrentBetQuality = !!selected?.bet;
 const selectedHasCurrentIntelligenceScore = !!selected?.intel;
 const selectedHasCurrentLimited = !!selected?.limited;
 const selectedConfidenceSource = !selected
 ? ""
 : selectedIsScratched
 ? "Confidence source unavailable while this runner is scratched."
 : selectedHasCurrentLimited
 ? "Confidence source: Live EDGEiQ confidence profile"
 : selectedHasCurrentBetQuality || selectedHasCurrentIntelligenceScore
 ? "Confidence source: Matched EDGEiQ confidence profile"
 : "Confidence source: Composite EDGEiQ confidence profile";
 const selectedCoverage = !selected
 ? ""
 : selectedIsScratched
 ? "SCRATCHED"
 : selectedHasCurrentLimited
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
 const priceLead =
 selectedEdgeNumeric !== null && selectedEdgeNumeric >= 18
 ? "shows a wide market-to-EDGEiQ price gap"
 : selectedEdgeNumeric !== null && selectedEdgeNumeric > 0
 ? "shows a positive price gap versus the EDGEiQ price"
 : "is currently priced tighter than EDGEiQ fair";
 const priceLine =
 selectedLivePrice !== "-" && selectedFairPrice !== "-"
 ? `, with the market at ${selectedLivePrice} versus EDGEiQ fair ${selectedFairPrice}`
 : "";
 const reasonTail =
 selectedDisplayBet === "BET" && selectedCurrentDecision === "WATCH"
 ? "Overall call remains WATCH because the broader model profile is not strong enough for a full upgrade."
 : selectedCurrentDecision === "WATCH"
 ? `Overall call remains WATCH because EDGEiQ confidence still grades ${selectedDisplayGrade.toLowerCase()}${selectedProjectionBand !== "-" ? ` with a ${selectedProjectionBand.toLowerCase()} runner profile` : ""}.`
 : selectedCurrentDecision === "BET"
 ? "Overall call is BET because price edge and overall confidence are aligned."
 : selectedCurrentDecision === "LEN"
 ? "Overall call stays LEN while EDGEiQ waits for stronger confirmation."
 : `Overall call remains ${selectedCurrentDecision} because the broader EDGEiQ profile does not justify an upgrade.`;
 return `${horse(selected.row)} ${priceLead}${priceLine}. ${reasonTail}`;
 })();
 const selectedSupportPoints = selectedIsScratched
 ? []
 : [
 { factor: selectedPositive1Factor, impact: selectedPositive1Impact },
 { factor: selectedPositive2Factor, impact: selectedPositive2Impact },
 { factor: selectedPositive3Factor, impact: selectedPositive3Impact },
 ].filter((item) => item.factor && item.factor !== "-");
 const selectedRiskPoints = selectedIsScratched
 ? []
 : [
 { factor: selectedNegative1Factor, impact: selectedNegative1Impact },
 { factor: selectedNegative2Factor, impact: selectedNegative2Impact },
 { factor: selectedNegative3Factor, impact: selectedNegative3Impact },
 ].filter((item) => item.factor && item.factor !== "-");
 const selectedRawConfidence = selected ? confidenceScoreValue(selected) : null;
 const selectedTrackFitScore = selected ? trackFitScoreValue(selected) : null;
 const selectedJockeyScore = selected ? jockeyScoreValue(selected) : null;
 const selectedTrainerScore = selected ? trainerScoreValue(selected) : null;
 const selectedConnectionScore = selected ? connectionScoreValue(selected) : null;
 const selectedRunnerFactors = selected
 ? [
 { label: "Runner DN", value: dnaScoreValue(selected), max: 100, digits: 0, tone: dnaScoreValue(selected) !== null ? cellTone(selectedDnaBand) : "#94a3b8" },
 { label: "Projection Gap", value: selectedProjectionGap, max: 20, digits: 2, signedValue: true, tone: selectedProjectionGap === null ? "#94a3b8" : selectedProjectionGap >= 0 ? "#3ee68f" : "#f87171" },
 { label: "Projected SPD", value: projectedSpdValue(selected), max: 10, digits: 1, tone: "#ffffff" },
 { label: "Sectionals", value: sectionalWeaponValue(selected), max: 100, digits: 0, tone: "#a78bfa" },
 { label: "Late Power", value: latePowerMetricValue(selected), max: 100, digits: 0, tone: "#ffffff" },
 { label: "Confidence", value: selectedRawConfidence, max: 100, digits: 0, tone: selectedDisplayGrade === "-" ? "#94a3b8" : cellTone(selectedDisplayGrade) },
 { label: "Track Fit", value: selectedTrackFitScore, max: 100, digits: 0, tone: selectedTrackFitScore === null ? "#94a3b8" : selectedTrackFitScore >= 60 ? "#3ee68f" : selectedTrackFitScore >= 45 ? "#ffffff" : "#f87171" },
 { label: "Jockey", value: selectedJockeyScore, max: 100, digits: 0, tone: selectedJockeyScore === null ? "#94a3b8" : selectedJockeyScore >= 60 ? "#3ee68f" : selectedJockeyScore >= 45 ? "#ffffff" : "#f87171" },
 { label: "Trainer", value: selectedTrainerScore, max: 100, digits: 0, tone: selectedTrainerScore === null ? "#94a3b8" : selectedTrainerScore >= 60 ? "#3ee68f" : selectedTrainerScore >= 45 ? "#ffffff" : "#f87171" },
 { label: "Connection", value: selectedConnectionScore, max: 100, digits: 0, tone: selectedConnectionScore === null ? "#94a3b8" : selectedConnectionScore >= 60 ? "#3ee68f" : selectedConnectionScore >= 45 ? "#ffffff" : "#f87171" },
 ]
 : [];
 const topBarMetrics = header
 ? [
 { label: "Race", value: `${track(header)} R${raceNo(header)}` },
 { label: "Distance", value: distance(header) },
 { label: "Class", value: raceClass(header) },
 { label: "Track Condition", value: trackCondition(header).toUpperCase() },
 { label: "Rail", value: railDisplay },
 { label: "Race Clarity", value: raceClarity, tone: bandColor(raceClarity) },
 { label: "Expected Tempo", value: displayExpectedTempo, tone: bandColor(displayExpectedTempo) },
 { label: "Confidence", value: bettingConfidence, tone: bandColor(bettingConfidence) },
 { label: "Market Status", value: marketStatus, tone: marketStatusTone },
 { label: "Rating Reference", value: topWinChanceRunner || "-" },
 { label: "Price Reference", value: bestValueRunner || "-", tone: "#f8fafc" },
 { label: "Market State", value: marketStatus, tone: marketStatusTone },
 ]
 : [];
 const speedMapLanes = ["LEADERS", "ON PACE", "MIDFIELD", "BACKMARKERS"].map((lane) => ({
 lane,
 tone: paceRoleTone(lane),
 runners: activeRaceRows
 .filter((item) => paceMapRole(item) === lane)
 .sort((a, b) => {
 const spdDelta = (projectedSpdValue(b) ?? -1) - (projectedSpdValue(a) ?? -1);
 if (spdDelta !== 0) return spdDelta;
 return (a.modelRank ?? 999) - (b.modelRank ?? 999);
 }),
 }));
 const leadersLane = speedMapLanes.find((lane) => lane.lane === "LEADERS");
 const onPaceLane = speedMapLanes.find((lane) => lane.lane === "ON PACE");
 const speedMapSummaryBits = [
 `${activeRaceRows.length} active runners`,
 `${leadersLane?.runners.length ?? 0} leaders`,
 `${onPaceLane?.runners.length ?? 0} on pace`,
 displayExpectedTempo !== "-" ? `tempo ${displayExpectedTempo}` : "",
 ].filter(Boolean);
 const activeMapRows = [...activeRaceRows].sort((a, b) => {
 const xDelta = paceMapXPercent(a) - paceMapXPercent(b);
 if (xDelta !== 0) return xDelta;
 const barrierA = num(barrier(a.row)) ?? 999;
 const barrierB = num(barrier(b.row)) ?? 999;
 if (barrierA !== barrierB) return barrierA - barrierB;
 return (a.modelRank ?? 999) - (b.modelRank ?? 999);
 });
 const explicitMapYValues = activeMapRows
 .map((item) => firstNum(item.mapEnrichment, ["map_y_px"]) ?? firstNum(item.row, ["map_y_px"]))
 .filter((value): value is number => value !== null && Number.isFinite(value));
 const explicitMapYMin = explicitMapYValues.length ? Math.min(...explicitMapYValues) : null;
 const explicitMapYMax = explicitMapYValues.length ? Math.max(...explicitMapYValues) : null;
 const speedMapPlotPoints = activeMapRows.map((item, index) => {
 const lane = paceMapRole(item);
 const explicitY = firstNum(item.mapEnrichment, ["map_y_px"]) ?? firstNum(item.row, ["map_y_px"]);
 const laneIndex = ["LEADERS", "ON PACE", "MIDFIELD", "BACKMARKERS"].indexOf(lane);
 const barrierValue = num(barrier(item.row));
 const laneBase = laneIndex >= 0 ? 12 + laneIndex * 22 : 45;
 const fallbackY =
 laneBase +
 (((barrierValue ?? index + 1) % 6) * 2.8);
 const derivedY =
 explicitY !== null && explicitMapYMin !== null && explicitMapYMax !== null && explicitMapYMax > explicitMapYMin
 ? 10 + ((explicitY - explicitMapYMin) / (explicitMapYMax - explicitMapYMin)) * 76
 : fallbackY;
 const edgeValue = edgePct(item.row, item.bet);
 const selectedRow = !!selected && runnerRowKey(item.row) === runnerRowKey(selected.row);
 const tone = selectedRow
 ? "#ffffff"
 : edgeValue !== null && edgeValue > 0
 ? "#34d399"
 : edgeValue !== null && edgeValue < 0
 ? "#f87171"
 : "#94a3b8";
 return {
 item,
 lane,
 x: paceMapXPercent(item),
 y: Math.max(8, Math.min(88, derivedY)),
 tone,
 selectedRow,
 tooltip: `${horse(item.row)} | Barrier ${barrier(item.row)} | ${lane} | SPD ${renderMetricValue(projectedSpdValue(item), 1)} | LP ${renderMetricValue(latePowerMetricValue(item), 0)} | Edge ${pct(edgeValue)}`,
 chipLabel: `${saddle(item.row) === 999 ? "?" : saddle(item.row)} ${shortHorseName(horse(item.row), 14)}`,
 };
 });
 const speedMapScaleMarks = Array.from({ length: 10 }, (_, index) => index * 10);
 const speedMetricValues = activeRaceRows
 .map((item) => projectedSpdValue(item))
 .filter((value): value is number => value !== null && Number.isFinite(value));
 const speedMetricMin = speedMetricValues.length ? Math.min(...speedMetricValues) : null;
 const speedMetricMax = speedMetricValues.length ? Math.max(...speedMetricValues) : null;
 const speedMapBarRows = [...activeRaceRows]
 .map((item) => {
 const explicitMap = firstNum(item.mapEnrichment, ["map_x_pct"]) ?? firstNum(item.row, ["map_x_pct"]);
 const projectedSpeed = projectedSpdValue(item);
 let mapValue =
 explicitMap !== null && Number.isFinite(explicitMap)
 ? clamp(90 - explicitMap, 0, 90)
 : null;

 if (mapValue === null && projectedSpeed !== null && speedMetricMin !== null && speedMetricMax !== null) {
 mapValue =
 speedMetricMax > speedMetricMin
 ? 28 + ((projectedSpeed - speedMetricMin) / (speedMetricMax - speedMetricMin)) * 54
 : 45;
 }

 if (mapValue === null) {
 mapValue = paceRoleSpeedValue(paceMapRole(item));
 }

 mapValue = clamp(mapValue, 0, 90);
 const barWidthPercent = clamp((mapValue / 90) * 100, 0, 100);
 const markerLeftPercent = clamp(100 - barWidthPercent, 0, 100);
 const selectedRow = !!selected && runnerRowKey(item.row) === runnerRowKey(selected.row);
 const tone = paceRoleTone(paceMapRole(item));
 const labelInside = barWidthPercent >= 28;
 const labelLeftPercent = labelInside
 ? clamp(markerLeftPercent + 1.5, 4, 92)
 : clamp(markerLeftPercent - 1.5, 6, 90);
 const labelTransform = labelInside ? "translate(0, -50%)" : "translate(-100%, -50%)";
 const styleLabel = paceMapRole(item).replace(/_/g, " ");
 const runnerLabel = shortHorseName(horse(item.row), 14);

 return {
 item,
 mapValue,
 barWidthPercent,
 markerLeftPercent,
 tone,
 selectedRow,
 projectedSpeed,
 styleLabel,
 runnerLabel,
 labelLeftPercent,
 labelTransform,
 barrierValue: num(barrier(item.row)),
 };
 })
 .sort((a, b) => {
 const aBarrier = a.barrierValue;
 const bBarrier = b.barrierValue;
 if (aBarrier !== null && bBarrier !== null && aBarrier !== bBarrier) return bBarrier - aBarrier;
 if (aBarrier === null && bBarrier !== null) return 1;
 if (aBarrier !== null && bBarrier === null) return -1;
 const mapDelta = b.mapValue - a.mapValue;
 if (mapDelta !== 0) return mapDelta;
 return (a.item.modelRank ?? 999) - (b.item.modelRank ?? 999);
 });
 const speedMapPressureRisk = firstText(
 intelligenceCard,
 ["pressure_risk_v1", "pressure_risk", "pace_pressure", "tempo_pressure"],
 fallbackPressureLabel !== "-" ? fallbackPressureLabel : "",
 );
 const raceShapeBiasNote =
 firstText(trackIntel, ["track_advantage_summary"], "") ||
 firstText(intelligenceCard, ["race_shape_advantage", "tempo_edge_summary"], "") ||
 fallbackPacedvantageLabel;
 const topWinChanceRows = [...activeRaceRows]
 .sort((a, b) => (winPct(b.row, b.bet) ?? -1) - (winPct(a.row, a.bet) ?? -1))
 .slice(0, 5);
 const bestValueRows = [...activeRaceRows]
 .filter((item) => (edgePct(item.row, item.bet) ?? -999) > 0)
 .sort((a, b) => (edgePct(b.row, b.bet) ?? -999) - (edgePct(a.row, a.bet) ?? -999))
 .slice(0, 5);
 const underlayRows = [...activeRaceRows]
 .filter((item) => (edgePct(item.row, item.bet) ?? 999) < 0)
 .sort((a, b) => (edgePct(a.row, a.bet) ?? 999) - (edgePct(b.row, b.bet) ?? 999))
 .slice(0, 5);
 const factorMatrixRows = rankedEnriched.map((item) => {
 const rating = projectionRatingValue(item);
 const projectionGap = projectionGapValue(item);
 const dna = dnaScoreValue(item);
 const sectionals = sectionalWeaponValue(item);
 const latePower = latePowerMetricValue(item);
 const pace = factorScoreValue(item, "PCE") ?? projectedSpdValue(item);
 const paceBand = factorBandValue(item, "PCE");
 const paceRole = paceMapRole(item);
 const trackFit = trackFitScoreValue(item) ?? firstNum(item.dna, ["profile_score"]);
 const jockey = factorScoreValue(item, "JOCKEY") ?? jockeyScoreValue(item);
 const trainer = factorScoreValue(item, "TRINER") ?? trainerScoreValue(item);
 const connection = factorScoreValue(item, "CONNECTION") ?? comboScoreValue(item) ?? connectionScoreValue(item);
 const ratedHistory = ratedHistoryRows(item.runnerHistory || []);
 const recentRatedHistory = ratedHistory.slice(0, 5);
 const lastStart = recentRatedHistory[0];
 const avg5 = recentRatedHistory.length
 ? recentRatedHistory.reduce((sum, historyRow) => sum + (historyRatingValue(historyRow) ?? 0), 0) / recentRatedHistory.length
 : null;
 const peak = ratedHistory.length
 ? Math.max(...ratedHistory.map((historyRow) => historyRatingValue(historyRow) ?? Number.NEGATIVE_INFINITY).filter((value) => Number.isFinite(value)))
 : null;
 const dnaBand = firstText(item.dna, ["dna_v6_2_band", "runner_dna_v6_1_band", "dna_band"], "-").replace(/_/g, " ").toUpperCase();
 const distanceBand = firstText(item.dna, ["distance_fit_band"], "-").replace(/_/g, " ").toUpperCase();
 const conditionBand = firstText(item.dna, ["condition_fit_band"], "-").replace(/_/g, " ").toUpperCase();
 const classBand = firstText(item.dna, ["class_fit_band"], "-").replace(/_/g, " ").toUpperCase();
 const campaignProfile = firstText(item.campaign, ["campaign_profile"], "-").replace(/_/g, " ").toUpperCase();
 const campaignRisk = firstText(item.campaign, ["campaign_risk_band"], "-").replace(/_/g, " ").toUpperCase();
 const campaignEvidence = firstText(item.campaign, ["evidence_status"], "-").replace(/_/g, " ").toUpperCase();
 const campaignPrep = formatCampaignStage(
 firstNum(item.campaign, ["current_prep_stage"]),
 firstText(item.campaign, ["prep_stage_label"], "-"),
 );
 const campaignWindow = formatCampaignWindow(
 firstNum(item.campaign, ["peak_window_start"]),
 firstNum(item.campaign, ["peak_window_end"]),
 );
 const connectionRow = connectionSourceRow(item);
 const connectionLoaded = hasConnectionPayload(connectionRow);
 const connectionBand = firstText(connectionRow, ["connection_band"], "-").replace(/_/g, " ").toUpperCase();
 const connectionNarrative = firstText(connectionRow, ["connection_narrative", "connection_summary_for_decision_engine"], "");
 const connectionPositive = firstText(connectionRow, ["connection_positive_1"], "");
 const price = limitedAdjustedPrice(item) ?? fairPrice(item.row, item.bet);
 const tabPrice = livePrice(item.row, item.bet);

 return {
 item,
 rating,
 projectionGap,
 dna,
 dnaBand,
 distanceBand,
 conditionBand,
 classBand,
 sectionals,
 latePower,
 pace,
 paceBand,
 paceRole,
 trackFit,
 jockey,
 trainer,
 connection,
 ratedHistoryCount: ratedHistory.length,
 lastStart,
 avg5,
 peak,
 campaignProfile,
 campaignRisk,
 campaignEvidence,
 campaignPrep,
 campaignWindow,
 connectionLoaded,
 connectionBand,
 connectionNarrative,
 connectionPositive,
 price,
 tabPrice,
 };
 });
 const factorCoverageThreshold = 0.35;
 const factorEligibleRows = factorMatrixRows.filter((row) => !isScratched(row.item));
 const factorCoverage = (selector: (row: (typeof factorMatrixRows)[number]) => number | null): number => {
 if (!factorEligibleRows.length) return 0;
 const populated = factorEligibleRows.filter((row) => selector(row) !== null).length;
 return populated / factorEligibleRows.length;
 };
 const showFactorSectionals = factorCoverage((row) => row.sectionals) >= factorCoverageThreshold;
 const showFactorLatePower = factorCoverage((row) => row.latePower) >= factorCoverageThreshold;
 const showFactorTrackFit = factorCoverage((row) => row.trackFit) >= factorCoverageThreshold;
 const factorFieldSize = factorEligibleRows.length;
 const coverageCount = (predicate: (row: (typeof factorMatrixRows)[number]) => boolean): number =>
 factorEligibleRows.filter(predicate).length;
 const ratingCoverageCount = coverageCount((row) => row.rating !== null);
 const projectionHistoryCoverageCount = coverageCount((row) => row.rating !== null && row.ratedHistoryCount >= 1);
 const dnaCoverageCount = coverageCount((row) => hasDnaPayload(row.item));
 const paceCoverageCount = raceShapeFallbackLoaded
 ? factorFieldSize
 : coverageCount((row) => row.pace !== null || row.paceRole !== "-");
 const sectionalsCoverageCount = coverageCount((row) => row.sectionals !== null);
 const latePowerCoverageCount = coverageCount((row) => row.latePower !== null);
 const trackFitCoverageCount = coverageCount((row) => row.trackFit !== null);
 const campaignCoverageCount = coverageCount((row) => row.campaignEvidence !== "-" && row.campaignEvidence !== "NO HISTORY");
 const historyCoverageCount = coverageCount((row) => row.ratedHistoryCount >= 1);
 const connectionsCoverageCount = coverageCount((row) => commandEvidencevailable(row.item, ["edgeiq_connection_evidence_available_v3", "edgeiq_connection_evidence_available_v2", "edgeiq_connection_evidence_available"], ["edgeiq_connection_angle_summary_v3", "edgeiq_connection_angle_summary_v2", "edgeiq_connection_angle_summary"]));
 const marketCoverageCount = coverageCount((row) => commandEvidencevailable(row.item, ["edgeiq_market_evidence_available_v3", "edgeiq_market_evidence_available_v2", "edgeiq_market_evidence_available"], ["edgeiq_market_signal_summary_v3", "edgeiq_market_signal_summary_v2", "edgeiq_market_signal_summary"]));
 const hiddenGemCoverageCount = coverageCount((row) => commandEvidencevailable(row.item, ["edgeiq_hidden_gem_evidence_available_v3", "edgeiq_hidden_gem_evidence_available_v2", "edgeiq_hidden_gem_evidence_available"], ["edgeiq_hidden_gem_summary_v3", "edgeiq_hidden_gem_summary_v2", "edgeiq_hidden_gem_summary"]));
 const commandRaceSummary = factorEligibleRows.map((row) => commandEvidenceSource(row.item)).find((source) => firstNum(source, ["race_field_size_v3", "race_field_size_v2"]) !== null);
 const commandRaceFieldSize = firstNum(commandRaceSummary, ["race_field_size_v3", "race_field_size_v2"]);
 const commandRaceConnectionCount = firstNum(commandRaceSummary, ["race_connection_available_count_v3", "race_connection_count_v2"]);
 const commandRaceMarketCount = firstNum(commandRaceSummary, ["race_market_available_count_v3", "race_market_count_v2"]);
 const commandRaceHiddenGemCount = firstNum(commandRaceSummary, ["race_hidden_gem_available_count_v3", "race_hidden_gem_count_v2"]);
 const commandRaceConnectionSourceMatchedCount = firstNum(commandRaceSummary, ["race_connection_source_matched_count_v3"]);
 const commandRaceEdgeiqPriceCount = firstNum(commandRaceSummary, ["race_edgeiq_price_count_v3"]);
 const displayConnectionsCoverageCount = commandRaceConnectionCount ?? connectionsCoverageCount;
 const displayMarketCoverageCount = commandRaceMarketCount ?? marketCoverageCount;
 const displayHiddenGemCoverageCount = commandRaceHiddenGemCount ?? hiddenGemCoverageCount;
 const displayConnectionSourceMatchedCount = commandRaceConnectionSourceMatchedCount ?? displayConnectionsCoverageCount;
 const displayEdgeiqPriceCount = commandRaceEdgeiqPriceCount ?? coverageCount((row) => fairPrice(row.item.row, row.item.bet) !== null);
 const displayEvidenceFieldSize = commandRaceFieldSize ?? factorFieldSize;
 const factorCoverageTiles = [
 { label: "Rating", count: ratingCoverageCount, explanation: "Current race rating reference loaded for today's field." },
 { label: "Projection / Today vs history", count: projectionHistoryCoverageCount, explanation: "Compares today's number against at least one rated historical run." },
 { label: "DN", count: dnaCoverageCount, explanation: "Runner suitability profile across distance, condition and class." },
 { label: "Pace", count: paceCoverageCount, explanation: "Expected settling role and race-shape context for this race, including the fallback pace engine when runner-level map evidence is sparse." },
 { label: "Sectionals", count: sectionalsCoverageCount, explanation: "Closing-speed evidence is only shown when sectional coverage is present." },
 { label: "Late Power", count: latePowerCoverageCount, explanation: "Late-run strength appears only when pace-side evidence is loaded." },
 { label: "Track Fit", count: trackFitCoverageCount, explanation: "Track-specific suitability is hidden until meaningful coverage is available." },
 { label: "Campaign", count: campaignCoverageCount, explanation: "Preparation-stage history based on the horse's own campaign pattern." },
 { label: "History", count: historyCoverageCount, explanation: "Historical rated run spine behind last starts, averages and peak figures." },
 { label: "Connections", count: displayConnectionsCoverageCount, explanation: "Trainer, jockey and combination evidence for the current race universe." },
 { label: "Market", count: displayMarketCoverageCount, explanation: "Current market signal evidence surfaced from the governed runner board." },
 { label: "Hidden Gem", count: displayHiddenGemCoverageCount, explanation: "Performance intelligence flags surfaced from current evidence." },
 ].map((tile) => ({
 ...tile,
 total: factorFieldSize,
 status: coverageStatus(tile.count, factorFieldSize),
 }));
 const hiddenFactorColumns = [
 !showFactorSectionals ? "Sectionals" : null,
 !showFactorLatePower ? "Late Power" : null,
 !showFactorTrackFit ? "Track Fit" : null,
 ].filter((label): label is string => !!label);
 const factorMatrixGridCols = "220px 150px 150px 170px 150px 160px 150px 170px";
 const selectedPriceSummary = selected
 ? [
 { label: "Win %", value: selectedIsScratched ? "-" : pct(winPct(selected.row, selected.bet)), tone: "#f8fafc" },
 { label: "EDGEiQ Price", value: selectedFairPrice, tone: "#f8fafc" },
 { label: "TB", value: selectedLivePrice, tone: "#f8fafc" },
 { label: "Edge", value: selectedEdge, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedCurrentDecision) },
 { label: "Market", value: selectedIsScratched ? "SCRATCHED" : selectedCurrentDecision, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedCurrentDecision) },
 ]
 : [];
 const selectedModelSummary = selected
 ? [
 { label: "Race Rank", value: selectedModelRank ? `#${selectedModelRank}` : "-", tone: "#ffffff" },
 { label: "Projected Rating", value: selectedIsScratched ? "-" : renderMetricValue(projectionRatingValue(selected), 1), tone: selectedIsScratched ? "#94a3b8" : scoreTone(projectionRatingValue(selected)) },
 { label: "Projection Gap", value: selectedIsScratched ? "-" : renderMetricValue(selectedProjectionGap, 2, true), tone: selectedProjectionGap === null ? "#94a3b8" : selectedProjectionGap >= 0 ? "#34d399" : "#f87171" },
 { label: "Runner Profile", value: selectedRunnerProfileDnaDisplay, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedDnaBand) },
 { label: "Confidence", value: selectedIsScratched ? "SCRATCHED" : selectedDisplayGrade, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedDisplayGrade) },
 ]
 : [];
 const selectedPerformanceSummary = selected
 ? [
 { label: "Settling", value: selectedIsScratched ? "-" : paceMapRole(selected), tone: selectedIsScratched ? "#94a3b8" : paceRoleTone(paceMapRole(selected)) },
 { label: "Projected SPD", value: selectedIsScratched ? "N/" : renderMetricValue(selectedProjectedSpd, 1), tone: "#ffffff" },
 { label: "Sectionals", value: selectedIsScratched ? "-" : renderMetricValue(selectedSectional, 0), tone: "#a78bfa" },
 { label: "Late Power", value: selectedIsScratched ? "-" : renderMetricValue(selectedLatePower, 0), tone: "#ffffff" },
 { label: "Pace Fit", value: selectedIsScratched ? "N/" : renderMetricValue(factorScoreValue(selected, "PCE"), 0), tone: selectedIsScratched ? "#94a3b8" : cellTone(factorBandValue(selected, "PCE")) },
 ]
 : [];
 const selectedTrackFitSummary = selected
 ? [
 { label: "Distance", value: selectedIsScratched ? "-" : selectedDistanceBand, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedDistanceBand) },
 { label: "Condition", value: selectedIsScratched ? "-" : selectedConditionBand, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedConditionBand) },
 { label: "Track", value: selectedIsScratched ? "-" : renderMetricValue(selectedTrackFitScore, 0), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedTrackFitScore) },
 { label: "Class", value: selectedIsScratched ? "-" : selectedClassBand, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedClassBand) },
 ]
 : [];
 const selectedConnectionSummary = selected
 ? [
 { label: "Band", value: selectedIsScratched ? "SCRATCHED" : selectedConnectionLoaded ? selectedConnectionBand : "NO MTERIL RED", tone: selectedIsScratched || !selectedConnectionLoaded ? "#94a3b8" : connectionTone(selectedConnectionBand) },
 { label: "Evidence", value: selectedIsScratched ? "-" : selectedConnectionLoaded ? selectedConnectionEvidenceQuality : "-", tone: selectedIsScratched || !selectedConnectionLoaded ? "#94a3b8" : evidenceQualityTone(selectedConnectionEvidenceQuality) },
 { label: "Patterns", value: selectedIsScratched ? "-" : selectedConnectionLoaded ? renderMetricValue(selectedConnectionEvidencePatterns.length, 0) : "-", tone: selectedIsScratched || !selectedConnectionLoaded ? "#94a3b8" : "#ffffff" },
 { label: "Risk Context", value: selectedIsScratched ? "-" : selectedConnectionRiskMeaningful ? "PRESENT" : "CLER", tone: selectedIsScratched ? "#94a3b8" : selectedConnectionRiskMeaningful ? "#ffffff" : "#34d399" },
 ]
 : [];
 const selectedrchetypeSummary = selected
 ? [
 { label: "rchetype", value: selectedIsScratched ? "SCRATCHED" : selectedCareerrchetype, tone: selectedIsScratched ? "#94a3b8" : "#ffffff" },
 { label: "Stage", value: selectedIsScratched ? "-" : selectedDevelopmentStage, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedDevelopmentStage) },
 { label: "Improvement", value: selectedIsScratched ? "-" : selectedImprovementProfile, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedImprovementProfile) },
 { label: "Freshness", value: selectedIsScratched ? "-" : selectedFreshnessProfile, tone: selectedIsScratched ? "#94a3b8" : "#ffffff" },
 { label: "Distance Profile", value: selectedIsScratched ? "-" : selectedrchetypeDistanceProfile, tone: selectedIsScratched ? "#94a3b8" : "#34d399" },
 { label: "Seasonality", value: selectedIsScratched ? "-" : selectedSeasonalityProfile, tone: selectedIsScratched ? "#94a3b8" : "#ffffff" },
 ]
 : [];
 const selectedTrajectorySummary = selected
 ? [
 { label: "Trajectory", value: selectedIsScratched ? "SCRATCHED" : selectedTrajectoryDirection, tone: selectedIsScratched ? "#94a3b8" : trajectoryTone(selectedTrajectoryDirection) },
 { label: "Career Phase", value: selectedIsScratched ? "-" : selectedCareerPhase, tone: selectedIsScratched ? "#94a3b8" : trajectoryTone(selectedCareerPhase) },
 { label: "Points Off Peak", value: selectedIsScratched ? "-" : renderMetricValue(selectedPointsOffPeak, 1), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedPointsOffPeak === null ? null : Math.max(0, 100 - (selectedPointsOffPeak * 8)), 70, 45) },
 { label: "Breakout Potential", value: selectedIsScratched ? "-" : selectedBreakoutPotential, tone: selectedIsScratched ? "#94a3b8" : opportunityTone(selectedBreakoutPotential) },
 { label: "Bounce Risk", value: selectedIsScratched ? "-" : selectedBounceRisk, tone: selectedIsScratched ? "#94a3b8" : riskTone(selectedBounceRisk) },
 { label: "Trend Strength", value: selectedIsScratched ? "-" : selectedTrajectoryStrength, tone: selectedIsScratched ? "#94a3b8" : trajectoryTone(selectedTrajectoryStrength) },
 ]
 : [];
 const selectedProjectionSummary = selected
 ? [
 { label: "Projection Band", value: selectedIsScratched ? "SCRATCHED" : selectedProjectionOutlookBand, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedProjectionOutlookBand) },
 { label: "Confidence", value: selectedIsScratched ? "-" : selectedProjectionOutlookConfidence, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedProjectionOutlookConfidence) },
 { label: "Next Run Projection", value: selectedIsScratched ? "-" : renderMetricValue(selectedNextRunProjection, 1), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedNextRunProjection, 70, 55) },
 { label: "Ceiling Projection", value: selectedIsScratched ? "-" : renderMetricValue(selectedCeilingProjection, 1), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedCeilingProjection, 72, 58) },
 { label: "Floor Projection", value: selectedIsScratched ? "-" : renderMetricValue(selectedFloorProjection, 1), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedFloorProjection, 60, 45) },
 { label: "Expected Improvement", value: selectedIsScratched ? "-" : signed(selectedExpectedImprovement, 1), tone: selectedIsScratched ? "#94a3b8" : selectedExpectedImprovement === null ? "#94a3b8" : selectedExpectedImprovement > 0 ? "#34d399" : selectedExpectedImprovement < 0 ? "#f87171" : "#cbd5e1" },
 { label: "Improvement Probability", value: selectedIsScratched ? "-" : pct(selectedImprovementProbability), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedImprovementProbability, 65, 45) },
 { label: "Regression Probability", value: selectedIsScratched ? "-" : pct(selectedRegressionProbability), tone: selectedIsScratched ? "#94a3b8" : selectedRegressionProbability === null ? "#94a3b8" : selectedRegressionProbability >= 65 ? "#f87171" : selectedRegressionProbability >= 45 ? "#ffffff" : "#34d399" },
 { label: "Peak Revisit Probability", value: selectedIsScratched ? "-" : pct(selectedPeakRevisitProbability), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedPeakRevisitProbability, 60, 40) },
 ]
 : [];
 const selectedCampaignSummary = selected
 ? [
 { label: "Campaign Profile", value: selectedIsScratched ? "SCRATCHED" : selectedCampaignProfile, tone: selectedIsScratched ? "#94a3b8" : campaignEvidenceTone(selectedCampaignProfileBand) },
 { label: "Preparation Stage", value: selectedIsScratched ? "-" : selectedCampaignPrepDisplay, tone: selectedIsScratched ? "#94a3b8" : "#ffffff" },
 { label: "Peak Window", value: selectedIsScratched ? "-" : selectedCampaignPeakWindowDisplay, tone: selectedIsScratched ? "#94a3b8" : "#cbd5e1" },
 { label: "Preparation Risk", value: selectedIsScratched ? "-" : selectedCampaignRiskBand, tone: selectedIsScratched ? "#94a3b8" : riskTone(selectedCampaignRiskBand) },
 { label: "Evidence Status", value: selectedIsScratched ? "-" : selectedCampaignEvidenceStatus, tone: selectedIsScratched ? "#94a3b8" : campaignEvidenceTone(selectedCampaignEvidenceStatus) },
 { label: "History Runs", value: selectedIsScratched ? "-" : renderMetricValue(selectedCampaignHistoryRuns, 0), tone: selectedIsScratched ? "#94a3b8" : "#f8fafc" },
 ]
 : [];
 const selectedHiddenGemSummary = selected
 ? [
 { label: "Case", value: selectedIsScratched ? "SCRATCHED" : selectedPerformanceIntelligenceBand, tone: selectedIsScratched ? "#94a3b8" : hiddenGemTone(selectedPerformanceIntelligenceBand) },
 { label: "Evidence", value: selectedIsScratched ? "SCRATCHED" : selectedHiddenGemStatusDisplay, tone: selectedIsScratched ? "#94a3b8" : hiddenGemTone(selectedHiddenGemStatusDisplay) },
 { label: "Recency", value: selectedIsScratched ? "-" : selectedHiddenGemRecencyBand, tone: selectedIsScratched ? "#94a3b8" : hiddenGemTone(selectedHiddenGemRecencyBand) },
 { label: "Days Since", value: selectedIsScratched ? "-" : selectedHiddenGemgeDisplay, tone: selectedIsScratched ? "#94a3b8" : "#f8fafc" },
 { label: "djusted Score", value: selectedIsScratched ? "-" : renderMetricValue(selectedHiddenGemScore, 1), tone: selectedIsScratched ? "#94a3b8" : hiddenGemTone(selectedHiddenGemDisplayBand) },
 { label: "Last Evidence", value: selectedIsScratched ? "-" : (selectedHiddenGemDate !== "-" ? formatHistoryDate(selectedHiddenGemDate) : "-"), tone: selectedIsScratched ? "#94a3b8" : "#cbd5e1" },
 ]
 : [];
 const selectedCareerSummary = selected
 ? [
 { label: "Career Peak", value: selectedIsScratched ? "-" : renderMetricValue(selectedCareerPeakRating, 1), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedCareerPeakRating, 70, 55) },
 { label: "Career Trend", value: selectedIsScratched ? "-" : selectedCareerTrend, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedCareerTrend) },
 { label: "Last 3 vg", value: selectedIsScratched ? "-" : renderMetricValue(selectedCareerLast3verage, 1), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedCareerLast3verage, 70, 55) },
 { label: "Peak Trend", value: selectedIsScratched ? "-" : selectedPeakTrend, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedPeakTrend) },
 { label: "Consistency", value: selectedIsScratched ? "-" : renderMetricValue(selectedCareerConsistency, 0), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedCareerConsistency, 70, 50) },
 { label: "Volatility", value: selectedIsScratched ? "-" : renderMetricValue(selectedCareerVolatility, 0), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedCareerVolatility, 70, 50) },
 { label: "Career %ile", value: selectedIsScratched ? "-" : renderMetricValue(selectedCareerPercentileScore, 1), tone: selectedIsScratched ? "#94a3b8" : scoreTone(selectedCareerPercentileScore, 80, 55) },
 { label: "Peak Stage", value: selectedIsScratched ? "-" : selectedCareerPeakgeStage, tone: selectedIsScratched ? "#94a3b8" : "#ffffff" },
 { label: "Runs Since Peak", value: selectedIsScratched ? "-" : selectedRunsSincePeak, tone: selectedIsScratched ? "#94a3b8" : "#ffffff" },
 { label: "Best Track", value: selectedIsScratched ? "-" : selectedCareerBestTrack, tone: "#ffffff" },
 { label: "Best Distance", value: selectedIsScratched ? "-" : selectedCareerBestDistance, tone: "#ffffff" },
 { label: "Best Conditions", value: selectedIsScratched ? "-" : selectedCareerBestCondition, tone: "#34d399" },
 { label: "Best Class", value: selectedIsScratched ? "-" : selectedCareerBestClass, tone: "#ffffff" },
 ]
 : [];
 const selectedStats = selected
 ? selectedIsScratched
 ? [
 { label: "Status", value: "SCRATCHED", tone: "#9ca3af" },
 { label: "Win Chance", value: "-", tone: "#64748b" },
 { label: "EDGEiQ Price", value: "-", tone: "#64748b" },
 { label: "Market", value: "-", tone: "#64748b" },
 { label: "Setup Gap", value: "-", tone: "#64748b" },
 { label: "EDGEiQ Confidence", value: "SCRATCHED", tone: "#9ca3af" },
 { label: "Market", value: "SCRATCHED", tone: "#9ca3af" },
 ]
 : [
 { label: "Win Chance", value: pct(winPct(selected.row, selected.bet)) },
 { label: "EDGEiQ Price", value: money(limitedAdjustedPrice(selected) ?? fairPrice(selected.row, selected.bet)) },
 { label: "Market", value: money(livePrice(selected.row, selected.bet)) },
 { label: "Setup Gap", value: pct(edgePct(selected.row, selected.bet)) },
 { label: "EDGEiQ Confidence", value: displayGradeValue(selected), tone: cellTone(displayGradeValue(selected)) },
 { label: "Market", value: decision(selected.row, selected.bet), tone: cellTone(decision(selected.row, selected.bet)) },
 ]
 : [];
 const intelModeTabs: Array<{ mode: IntelMode; label: string; hint: string }> = [
 { mode: "COMMND", label: "RACE", hint: "Race overview" },
 { mode: "RUNNERS", label: "FIELD", hint: "Race field" },
 { mode: "PERFORMANCE", label: "PERFORMANCE", hint: "Performance Index" },
 { mode: "FORM", label: "FORM", hint: "Form study" },
 { mode: "MP", label: "MAP", hint: "Speed map" },
 { mode: "NEXUS", label: "LAB", hint: "Research laboratory" },
 { mode: "STATS", label: "STATS", hint: "Jockeys and trainers" },
 { mode: "DVNCED", label: "MARKET", hint: "Price comparison" },
 { mode: "RESULTS", label: "RESULTS", hint: "Post-race" },
 { mode: "WEATHER", label: "CONDITIONS", hint: "Track and weather" },
 ];
 const selectedExplainabilityConfidenceDisplay = selectedIsScratched
 ? "SCRATCHED"
 : selectedExplainabilityConfidenceBand !== "-" && selectedExplainabilityConfidenceScore !== null
 ? `${selectedExplainabilityConfidenceBand} (${renderMetricValue(selectedExplainabilityConfidenceScore, 1)})`
 : selectedExplainabilityConfidenceBand !== "-"
 ? selectedExplainabilityConfidenceBand
 : selectedDisplayGrade;
 const selectedConnectionDisplay = selectedIsScratched
 ? "SCRATCHED"
 : selectedConnectionBand !== "-" && selectedExplainabilityConnectionScore !== null
 ? `${selectedConnectionBand} (${renderMetricValue(selectedExplainabilityConnectionScore, 0)})`
 : selectedConnectionBand !== "-"
 ? selectedConnectionBand
 : selectedExplainabilityConnectionScore !== null
 ? renderMetricValue(selectedExplainabilityConnectionScore, 0)
 : "N/";
 const decisionSupportItems = selectedIsScratched
 ? []
 : (selectedExplainabilitySupports.length
 ? selectedExplainabilitySupports
 : selectedSupportPoints.map((item) => ({ factor: item.factor, value: item.impact }))).slice(0, 3);
 const decisionRiskItems = selectedIsScratched
 ? []
 : (selectedExplainabilityRisks.length
 ? selectedExplainabilityRisks
 : selectedRiskPoints.map((item) => ({ factor: item.factor, value: item.impact }))).slice(0, 3);
 const commandDecisionTiles = selected
 ? [
 { label: "Model Rank", value: selectedExplainabilityModelRank, tone: selectedIsScratched ? "#94a3b8" : "#ffffff" },
 { label: "Confidence", value: selectedExplainabilityConfidenceDisplay ? selectedExplainabilityConfidenceDisplay : "-", tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedExplainabilityConfidenceBand || selectedDisplayGrade) },
 { label: "Trend", value: selectedExplainabilityTrendDisplay, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedExplainabilityTrendLabel) },
 { label: "Market", value: selectedIsScratched ? "SCRATCHED" : selectedCurrentDecision, tone: selectedIsScratched ? "#94a3b8" : cellTone(selectedCurrentDecision) },
 { label: "Race Shape", value: selectedIsScratched ? "SCRATCHED" : `${selectedExplainabilityRaceShape || "-"} | ${selectedExplainabilityRaceTempo || "-"}`, tone: selectedIsScratched ? "#94a3b8" : "#ffffff" },
 ]
 : [];
 const selectedMapSummary = selected
 ? [
 { label: "Selected Runner", value: horse(selected.row), tone: selectedIsScratched ? "#94a3b8" : "#f8fafc" },
 { label: "Settling", value: selectedIsScratched ? "SCRATCHED" : paceMapRole(selected), tone: selectedIsScratched ? "#94a3b8" : paceRoleTone(paceMapRole(selected)) },
 { label: "Projected SPD", value: selectedIsScratched ? "N/" : renderMetricValue(selectedProjectedSpd, 1), tone: "#ffffff" },
 { label: "Pace Fit", value: selectedIsScratched ? "N/" : renderMetricValue(factorScoreValue(selected, "PCE"), 0), tone: selectedIsScratched ? "#94a3b8" : cellTone(factorBandValue(selected, "PCE")) },
 { label: "Pressure Risk", value: selectedRacePressureDisplay || "Standard", tone: selectedRacePressureRiskRunner ? "#f87171" : selectedRacePressureDisplay ? "#ffffff" : "#94a3b8" },
 { label: "Late Power", value: selectedRaceLatePowerBeneficiary || (selectedLatePower !== null ? renderMetricValue(selectedLatePower, 0) : "No key closer"), tone: "#ffffff" },
 ]
 : [];
 const selectedCampaignEvidenceLoaded = selectedCampaignEvidenceStatus !== "-" && selectedCampaignEvidenceStatus !== "NO HISTORY";
 const selectedFactorDetailSections = selected
 ? [
 {
 title: "Rating",
 tone: "#ffffff",
 currentRead: selectedIsScratched
 ? "Runner scratched."
 : `TODAY ${selectedTodayProjectionFigure === null ? "-" : renderMetricValue(selectedTodayProjectionFigure, 1)} | 1LS ${selectedLastStartRating} | PEK ${selectedCareerPeakRating === null ? "-" : renderMetricValue(selectedCareerPeakRating, 1)}`,
 why: selectedRatedHistory.length >= 3
 ? "Shows whether today's projection is building from a credible recent figure and how far it sits from the horse's established ceiling."
 : "Historical rating evidence is limited, so today's number should be read with more caution than usual.",
 evidenceQuality: selectedIsScratched
 ? "SCRATCHED"
 : selectedRatedHistory.length >= 5
 ? "vailable"
 : selectedRatedHistory.length >= 1
 ? "Limited"
 : "Unavailable",
 evidenceDetail: selectedIsScratched
 ? "SCRATCHED"
 : `${selectedRatedHistory.length} rated run${selectedRatedHistory.length === 1 ? "" : "s"} loaded from the history spine.`,
 },
 {
 title: "Form",
 tone: cellTone(selectedFormSignal),
 currentRead: selectedIsScratched
 ? "Runner scratched."
 : `${selectedFormSignal} | ${selectedFormCycle} | AVG5 ${selectedAVGRatingLast5}`,
 why: selectedFormNarrative || "Summarises the runner's recent form pattern, cycle and last-start rating context.",
 evidenceQuality: selectedIsScratched
 ? "SCRATCHED"
 : firstText(selectedRunnerForm, ["evidence_quality"], selectedRatedHistory.length ? "vailable" : "Limited"),
 evidenceDetail: selectedIsScratched
 ? "SCRATCHED"
 : [
 firstText(selectedRunnerForm, ["recent_runs_found"], ""),
 selectedRatingTrend !== "-" ? `Trend ${selectedRatingTrend}` : "",
 selectedRatingTrendDelta !== "-" ? `Delta ${selectedRatingTrendDelta}` : "",
 ].filter(Boolean).join(" | ") || "Form intelligence loaded.",
 },
 {
 title: "Performance",
 tone: hiddenGemTone(selectedHiddenGemDisplayBand),
 currentRead: selectedIsScratched
 ? "Runner scratched."
 : selectedHiddenGemctionable
 ? `${selectedPerformanceIntelligenceBand} | ${selectedHiddenGemRecencyBand} | ${selectedHiddenGemgeDisplay}`
 : selectedHiddenGemHistorical
 ? `IMPROVING | ${selectedHiddenGemRecencyBand} | ${selectedHiddenGemgeDisplay}`
 : selectedHiddenGemLoaded
 ? "NEUTRAL"
 : "NEUTRAL",
 why: "Looks for recent runs where the underlying performance figure was stronger than the finishing position or beaten margin made it appear.",
 evidenceQuality: selectedIsScratched
 ? "SCRATCHED"
 : selectedHiddenGemLoaded
 ? "vailable"
 : "Limited",
 evidenceDetail: selectedIsScratched
 ? "SCRATCHED"
 : selectedHiddenGemLoaded
 ? [
 selectedMergedHiddenGemvailable ? selectedMergedHiddenGemSummary : "",
 selectedHiddenGemTrigger,
 selectedHiddenGemHistorical && selectedHiddenGemDate !== "-"
 ? `Profile evidence from ${formatHistoryDate(selectedHiddenGemDate)}`
 : "",
 !selectedHiddenGemctionable && !selectedHiddenGemHistorical
 ? "Neutral current performance intelligence."
 : "",
 ].filter(Boolean).join(" | ") || selectedHiddenGemNarrative
 : selectedMergedHiddenGemvailable
 ? selectedMergedHiddenGemSummary || "Hidden gem evidence loaded."
 : "No hidden gem flagged.",
 },
 {
 title: "Pace",
 tone: paceRoleTone(paceMapRole(selected)),
 currentRead: selectedIsScratched
 ? "Runner scratched."
 : `${paceMapRole(selected)} | SPD ${selectedProjectedSpd === null ? "-" : renderMetricValue(selectedProjectedSpd, 1)} | Tempo ${selectedRaceTempoLabel}`,
 why: "Shows where the runner is expected to settle and whether the projected race shape helps or hurts that run style.",
 evidenceQuality: selectedIsScratched
 ? "SCRATCHED"
 : selectedRaceShapeLabel !== "-" || selectedProjectedSpd !== null
 ? "vailable"
 : "Unavailable",
 evidenceDetail: selectedIsScratched
 ? "SCRATCHED"
 : selectedRaceShapeLabel !== "-" || selectedProjectedSpd !== null
 ? "Pace map and race-shape briefing loaded."
 : "Race-shape evidence pending for this runner.",
 },
 {
 title: "Campaign",
 tone: campaignEvidenceTone(selectedCampaignRiskBand),
 currentRead: selectedIsScratched
 ? "Runner scratched."
 : `Prep ${selectedCampaignPrepDisplay} | Peak Window ${selectedCampaignPeakWindowDisplay} | Risk ${selectedCampaignRiskBand}`,
 why: "Uses the horse's own preparation history to show whether today sits inside or outside its preferred campaign window.",
 evidenceQuality: selectedIsScratched
 ? "SCRATCHED"
 : selectedCampaignEvidenceLoaded
 ? "vailable"
 : "Limited",
 evidenceDetail: selectedIsScratched
 ? "SCRATCHED"
 : selectedCampaignEvidenceLoaded
 ? `Campaign evidence ${selectedCampaignEvidenceStatus}.`
 : "Campaign history is limited for this runner.",
 },
 {
 title: "Connections",
 tone: selectedConnectionLoaded ? connectionTone(selectedConnectionBand) : "#94a3b8",
 currentRead: selectedIsScratched
 ? "Runner scratched."
 : selectedConnectionLoaded
 ? `${selectedConnectionDisplay}${selectedConnectionEvidencePatterns[0]?.value ? ` | ${selectedConnectionEvidencePatterns[0].value}` : ""}`
 : "Connection profile is still forming.",
 why: selectedConnectionLoaded
 ? selectedConnectionNarrative || "Trainer, jockey, partnership, market and preparation patterns add context to this runner's profile."
 : "Connection intelligence is hidden unless the current-race profile has meaningful evidence.",
 evidenceQuality: selectedIsScratched
 ? "SCRATCHED"
 : selectedConnectionLoaded
 ? selectedConnectionEvidenceQuality || selectedConnectionEvidenceStatus || "vailable"
 : "Unavailable",
 evidenceDetail: selectedIsScratched
 ? "SCRATCHED"
 : selectedConnectionLoaded
 ? selectedConnectionEvidencePatterns.map((item) => `${item.label}: ${item.value}`).join(" | ") || selectedConnectionNarrative
 : "Connection profile is still forming for this runner.",
 },
 {
 title: "Market",
 tone: "#f8fafc",
 currentRead: selectedIsScratched
 ? "Runner scratched."
 : `EDGEiQ ${selectedFairPrice} | TB ${selectedLivePrice} | Market ${selectedCurrentDecision}`,
 why: "This is a market reference only. It shows the current market position beside the EDGEiQ line without changing pricing logic.",
 evidenceQuality: selectedIsScratched
 ? "SCRATCHED"
 : selectedLivePrice !== "-"
 ? "vailable"
 : "Limited",
 evidenceDetail: selectedIsScratched
 ? "SCRATCHED"
 : selectedMergedMarketvailable
 ? selectedMergedMarketSummary || "Market signal evidence loaded."
 : selectedLivePrice !== "-"
 ? "Market reference loaded. No market signals triggered."
 : "No market signals triggered.",
 },
 ].filter((section) => section.title !== "Connections" || selectedConnectionLoaded || selectedIsScratched)
 : [];
 const commandTopCall = topModelRow;
 const commandBestValue = bestValueRows[0] || null;
 const commandMainRisk =
 [...activeRaceRows]
 .filter((item) => (edgePct(item.row, item.bet) ?? 999) < 0)
 .sort(
 (a, b) =>
 (((livePrice(a.row, a.bet) ?? 0) > 0 ? 0 : 1) - ((livePrice(b.row, b.bet) ?? 0) > 0 ? 0 : 1)) ||
 ((livePrice(a.row, a.bet) ?? 999) - (livePrice(b.row, b.bet) ?? 999)) ||
 ((edgePct(a.row, a.bet) ?? 999) - (edgePct(b.row, b.bet) ?? 999)) ||
 ((a.modelRank ?? 999) - (b.modelRank ?? 999))
 )[0] || underlayRows[0] || null;
 const commandConfidenceDisplay = (item: EnrichedRunner | null | undefined): string => {
 if (!item) return "N/";
 if (isScratched(item)) return "SCRATCHED";
 const band = firstText(item.explainability, ["confidence_band"], "").replace(/_/g, " ").toUpperCase();
 const score = firstNum(item.explainability, ["final_confidence_score"]) ?? computedLimitedScore(item);
 if (band && band !== "N/") {
 return score !== null ? `${band} (${renderMetricValue(score, 1)})` : band;
 }
 return displayGradeValue(item);
 };
 const commandConnectionBadge = (item: EnrichedRunner | null | undefined) => {
 if (!item || isScratched(item)) return null;
 const connectionRow = connectionSourceRow(item);
 const band = firstText(connectionRow, ["connection_band"], "").replace(/_/g, " ").toUpperCase();
 const score = firstNum(connectionRow, ["connection_score"]);
 if (!band && score === null) return null;
 const label = `CONN: ${band || "N/"}${score !== null ? ` ${renderMetricValue(score, 0)}` : ""}`;
 const tone = connectionTone(band || "");
 return (
 <div style={fitBadgeRowStyle}>
 <span style={fitBadge(label, tone, "rgba(8,15,28,.9)", `1px solid ${tone}55`)}>
 {label}
 </span>
 </div>
 );
 };
 const renderConnectionDnaSection = () => (
 <div style={{ ...narrativeInsetStyle, marginTop: 0 }}>
 <strong style={{ display: "block", marginBottom: 8, color: connectionTone(selectedConnectionBand), fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>
 CONNECTION INTELLIGENCE
 </strong>
 <div style={compactValueGridStyle(4)}>
 <div style={valueTileStyle}>
 <span style={miniLabelStyle}>Connection Band</span>
 <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : connectionTone(selectedConnectionBand) }}>
 {selectedIsScratched ? "SCRATCHED" : selectedConnectionLoaded ? selectedConnectionDisplay : "NO MTERIL RED"}
 </strong>
 </div>
 <div style={valueTileStyle}>
 <span style={miniLabelStyle}>Coverage</span>
 <strong style={{ ...miniValueStyle, color: selectedIsScratched || !selectedConnectionLoaded ? "#94a3b8" : evidenceQualityTone(selectedConnectionEvidenceQuality) }}>
 {selectedIsScratched ? "SCRATCHED" : selectedConnectionLoaded ? selectedConnectionEvidenceQuality : "-"}
 </strong>
 </div>
 <div style={valueTileStyle}>
 <span style={miniLabelStyle}>Patterns</span>
 <strong style={{ ...miniValueStyle, color: selectedIsScratched || !selectedConnectionLoaded ? "#94a3b8" : "#ffffff" }}>
 {selectedIsScratched ? "SCRATCHED" : selectedConnectionLoaded ? renderMetricValue(selectedConnectionEvidencePatterns.length, 0) : "-"}
 </strong>
 </div>
 <div style={valueTileStyle}>
 <span style={miniLabelStyle}>Risk Context</span>
 <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : selectedConnectionRiskMeaningful ? "#ffffff" : "#34d399" }}>
 {selectedIsScratched ? "SCRATCHED" : selectedConnectionRiskMeaningful ? "PRESENT" : "CLER"}
 </strong>
 </div>
 </div>

 {selectedConnectionLoaded && selectedConnectionEvidencePatterns.length ? (
 <div style={whyRankedGridStyle}>
 <div style={{ ...narrativeInsetStyle, marginTop: 0 }}>
 <strong style={{ display: "block", marginBottom: 6, color: "#34d399", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>Evidence Patterns</strong>
 <div style={{ display: "grid", gap: 6 }}>
 {selectedConnectionEvidencePatterns.map((item, index) => (
 <div key={`connection-insight-${index}-${item.label}`} style={{ display: "grid", gap: 2 }}>
 <span style={{ color: "#94a3b8", fontWeight: 900, fontSize: 10, textTransform: "uppercase", letterSpacing: ".07em" }}>{item.label}</span>
 <span style={{ color: "#eaf2ff", fontWeight: 900, fontSize: 11 }}>{item.value}</span>
 </div>
 ))}
 </div>
 </div>

 {selectedConnectionRiskMeaningful ? (
 <div style={{ ...narrativeInsetStyle, marginTop: 0 }}>
 <strong style={{ display: "block", marginBottom: 6, color: "#ffffff", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>Risk Context</strong>
 <span style={{ color: "#eaf2ff", fontWeight: 900, fontSize: 11 }}>{selectedConnectionRisk}</span>
 </div>
 ) : null}
 </div>
 ) : (
 <div style={{ ...narrativeInsetStyle, marginTop: 0, color: "#94a3b8", fontSize: 11 }}>
 {selectedIsScratched ? "Runner scratched." : "Connection intelligence not material for this runner."}
 </div>
 )}

 <p style={{ margin: "8px 0 0", color: "#dbe7fb", fontSize: 12, lineHeight: 1.55 }}>
 {selectedIsScratched ? "Runner scratched." : selectedConnectionNarrative || "Connection intelligence not material for this runner."}
 </p>
 </div>
 );
 const commandTopCallWhy = commandTopCall
 ? firstText(commandTopCall.explainability, ["why_ranked_here"], "") || selectedReason
 : raceAssessmentNarrative;
 const commandBestValueSupport = commandBestValue
 ? {
 factor: firstText(commandBestValue.explainability, ["positive_1"], "Price edge"),
 value: firstText(commandBestValue.explainability, ["positive_1_value"], pct(edgePct(commandBestValue.row, commandBestValue.bet))),
 }
 : null;
 const commandMainRiskReason = commandMainRisk
 ? {
 factor: firstText(commandMainRisk.explainability, ["risk_1"], "Market caution"),
 value: firstText(commandMainRisk.explainability, ["risk_1_value"], pct(edgePct(commandMainRisk.row, commandMainRisk.bet))),
 }
 : null;
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
 const intelModeBarStyle: React.CSSProperties = {
 display: "flex",
 gap: 8,
 flexWrap: "wrap",
 alignItems: "center",
 };
 const intelModeButtonStyle = (mode: IntelMode): React.CSSProperties => ({
 appearance: "none",
 border: intelMode === mode ? "1px solid rgba(52,211,153,.58)" : "1px solid rgba(80,120,180,.28)",
 background: intelMode === mode ? "rgba(10,34,28,.92)" : "rgba(5,12,22,.82)",
 color: intelMode === mode ? "#d1fae5" : "#94a3b8",
 borderRadius: 999,
 padding: "8px 12px",
 fontSize: 11,
 fontWeight: 900,
 letterSpacing: ".08em",
 textTransform: "uppercase",
 cursor: "pointer",
 boxShadow: intelMode === mode ? "0 0 0 1px rgba(52,211,153,.15), 0 0 16px rgba(16,185,129,.16)" : "none",
 });

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
 const assessmentCardStyle: React.CSSProperties = {
 ...panelStyle,
 border: "1px solid rgba(91,229,169,.24)",
 background: "linear-gradient(180deg,rgba(12,25,39,.97),rgba(6,14,24,.94))",
 display: "grid",
 gap: 10,
 };
 const assessmentTopRowStyle: React.CSSProperties = {
 display: "flex",
 justifyContent: "space-between",
 alignItems: "center",
 gap: 10,
 flexWrap: "wrap",
 };
 const supportInfoGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
 gap: 8,
 alignItems: "stretch",
 };
 const supportCardStyle: React.CSSProperties = {
 ...narrativeCardStyle,
 padding: 9,
 gap: 6,
 };
 const evidenceMatrixGridCols =
 "72px 240px 82px 82px 82px 82px 92px 82px 78px 72px 72px 96px 110px";
 const evidenceMatrixCellStyle: React.CSSProperties = {
 display: "grid",
 gap: 4,
 alignContent: "center",
 justifyItems: "center",
 color: "#e5edf8",
 fontSize: 11,
 minHeight: 40,
 };
 const evidenceMetricTrackStyle: React.CSSProperties = {
 width: "100%",
 height: 3,
 borderRadius: 999,
 background: "rgba(51,65,85,.55)",
 overflow: "hidden",
 };
 const evidenceSectionStyle: React.CSSProperties = {
 ...panelStyle,
 overflowX: "auto",
 display: "grid",
 gap: 8,
 };
 const evidenceMatrixRowStyle = (scratched: boolean, selectedRow: boolean): React.CSSProperties => ({
 display: "grid",
 gridTemplateColumns: evidenceMatrixGridCols,
 gap: 8,
 alignItems: "center",
 padding: "10px 12px",
 borderRadius: 10,
 border: scratched ? "1px solid rgba(100,116,139,.28)" : "1px solid rgba(80,120,180,.22)",
 background: scratched
 ? "rgba(30,41,59,.18)"
 : selectedRow
 ? "rgba(18,80,62,.38)"
 : "rgba(5,12,22,.82)",
 opacity: scratched ? 0.45 : 1,
 filter: scratched ? "grayscale(0.9)" : undefined,
 cursor: "pointer",
 });
 const selectedInsightGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
 gap: 6,
 alignItems: "stretch",
 };
 const runnerFactorsGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(120px,1fr))",
 gap: 6,
 alignItems: "stretch",
 };
 const runnerFactorCardStyle: React.CSSProperties = {
 ...miniTileStyle,
 minHeight: 56,
 gap: 5,
 };
 const factorCoverageGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))",
 gap: 8,
 alignItems: "stretch",
 };
 const factorCoverageTileStyle: React.CSSProperties = {
 border: "1px solid rgba(51,65,85,.72)",
 borderRadius: 12,
 background: "rgba(3,11,20,.8)",
 padding: "10px 11px",
 display: "grid",
 gap: 6,
 minHeight: 96,
 alignContent: "start",
 };
 const factorExplanationCellStyle: React.CSSProperties = {
 border: "1px solid rgba(51,65,85,.68)",
 borderRadius: 9,
 background: "rgba(3,11,20,.74)",
 padding: "8px 9px",
 display: "grid",
 gap: 3,
 minHeight: 60,
 alignContent: "start",
 textAlign: "left",
 };
 const factorDetailGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))",
 gap: 8,
 alignItems: "stretch",
 };
 const factorDetailCardStyle: React.CSSProperties = {
 border: "1px solid rgba(51,65,85,.72)",
 borderRadius: 12,
 background: "rgba(3,11,20,.8)",
 padding: "11px 12px",
 display: "grid",
 gap: 8,
 alignContent: "start",
 minHeight: 132,
 };
 const advancedPanelStyle: React.CSSProperties = {
 display: "grid",
 gap: 8,
 };
 const advancedSectionStyle: React.CSSProperties = {
 ...panelStyle,
 display: "grid",
 gap: 8,
 };
 const advancedGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
 gap: 6,
 };
 const raceContextGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))",
 gap: 8,
 };
 const topBarGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(132px,1fr))",
 gap: 6,
 };
 const topBarCardStyle: React.CSSProperties = {
 border: "1px solid rgba(51,65,85,.75)",
 borderRadius: 10,
 background: "rgba(3,11,20,.78)",
 padding: "8px 9px",
 display: "grid",
 gap: 3,
 minHeight: 54,
 alignContent: "start",
 };
 const commandSummaryStyle: React.CSSProperties = {
 color: "#dce7f7",
 fontSize: 12.5,
 lineHeight: 1.45,
 maxWidth: 900,
 };
 const workspaceSectionStyle: React.CSSProperties = {
 ...panelStyle,
 display: "grid",
 gap: 8,
 overflowX: "auto",
 };
 const speedMapGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(4,minmax(0,1fr))",
 gap: 8,
 minWidth: 1080,
 };
 const speedMapLaneStyle: React.CSSProperties = {
 border: "1px solid rgba(51,65,85,.75)",
 borderRadius: 12,
 background: "rgba(3,11,20,.78)",
 padding: 10,
 display: "grid",
 gap: 8,
 alignContent: "start",
 };
 const speedMapRunnerGridStyle: React.CSSProperties = {
 display: "grid",
 gap: 6,
 alignContent: "start",
 };
 const speedMapVisualShellStyle: React.CSSProperties = {
 border: "1px solid rgba(80,120,180,.24)",
 borderRadius: 14,
 background: "linear-gradient(180deg, rgba(8,16,30,.96), rgba(4,10,20,.9))",
 padding: 12,
 display: "grid",
 gap: 10,
 minWidth: 1080,
 };
 const speedMapVisualStageStyle: React.CSSProperties = {
 position: "relative",
 height: 360,
 borderRadius: 14,
 overflow: "hidden",
 border: "1px solid rgba(80,120,180,.22)",
 background: "linear-gradient(180deg, rgba(4,10,20,.95), rgba(10,19,34,.92))",
 };
 const speedMapVisualxisStyle: React.CSSProperties = {
 display: "flex",
 justifyContent: "space-between",
 gap: 12,
 alignItems: "center",
 color: "#94a3b8",
 fontSize: 10.5,
 fontWeight: 800,
 letterSpacing: ".08em",
 textTransform: "uppercase",
 };
 const speedMapLegendStyle: React.CSSProperties = {
 display: "flex",
 flexWrap: "wrap",
 gap: 8,
 alignItems: "center",
 };
 const speedMapCardStyle: React.CSSProperties = {
 border: "1px solid rgba(80,120,180,.22)",
 borderRadius: 10,
 background: "rgba(5,12,22,.84)",
 padding: "8px 9px",
 display: "grid",
 gap: 4,
 };
 const speedMapCardMetaStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "44px 1fr 56px 56px",
 gap: 6,
 alignItems: "center",
 fontSize: 10.5,
 };
 const speedMapFooterStyle: React.CSSProperties = {
 display: "flex",
 justifyContent: "space-between",
 alignItems: "center",
 gap: 8,
 color: "#94a3b8",
 fontSize: 10,
 lineHeight: 1.3,
 };
 const speedMapBarShellStyle: React.CSSProperties = {
 border: "1px solid rgba(80,120,180,.24)",
 borderRadius: 14,
 background: "linear-gradient(180deg, rgba(8,16,30,.96), rgba(4,10,20,.92))",
 padding: 10,
 display: "grid",
 gap: 8,
 minWidth: 880,
 };
 const speedMapBarLayoutStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "minmax(0,1fr) minmax(320px,.92fr)",
 gap: 8,
 alignItems: "start",
 };
 const speedMapBarInfoGridCols =
 "34px minmax(120px,1fr) 38px 74px 44px";
 const speedMapBarInfoHeaderStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: speedMapBarInfoGridCols,
 gap: 6,
 alignItems: "center",
 color: "#94a3b8",
 fontSize: 9.5,
 fontWeight: 900,
 textTransform: "uppercase",
 letterSpacing: ".08em",
 minHeight: 28,
 padding: "0 2px",
 };
 const speedMapBarMapHeaderStyle: React.CSSProperties = {
 display: "grid",
 gap: 4,
 minHeight: 28,
 };
 const speedMapScalexisNotesStyle: React.CSSProperties = {
 display: "flex",
 justifyContent: "space-between",
 gap: 12,
 color: "#94a3b8",
 fontSize: 9.5,
 fontWeight: 800,
 letterSpacing: ".06em",
 textTransform: "uppercase",
 };
 const speedMapScaleDirectionNoteStyle: React.CSSProperties = {
 color: "#ffffff",
 fontSize: 9.5,
 fontWeight: 800,
 letterSpacing: ".06em",
 textTransform: "uppercase",
 textAlign: "center",
 };
 const speedMapScaleGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(10, minmax(0,1fr))",
 gap: 0,
 color: "#94a3b8",
 fontSize: 9.5,
 fontWeight: 800,
 textAlign: "center",
 };
 const speedMapBarMapCellStyle: React.CSSProperties = {
 display: "grid",
 alignItems: "center",
 padding: "4px 6px",
 borderRadius: 8,
 border: "1px solid rgba(80,120,180,.20)",
 background: "rgba(5,12,22,.82)",
 minHeight: 28,
 };
 const speedMapBarInfoCellStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: speedMapBarInfoGridCols,
 gap: 6,
 alignItems: "center",
 padding: "4px 6px",
 borderRadius: 8,
 border: "1px solid rgba(80,120,180,.20)",
 background: "rgba(5,12,22,.82)",
 minHeight: 28,
 };
 const speedMapTrackStripStyle: React.CSSProperties = {
 position: "relative",
 height: 20,
 borderRadius: 999,
 overflow: "hidden",
 border: "1px solid rgba(80,120,180,.22)",
 background: "linear-gradient(180deg, rgba(7,16,28,.96), rgba(10,19,34,.94))",
 };
 const ratingsLadderGridCols = "46px 210px 58px 58px 58px 58px 58px 68px 68px 98px 72px 98px 84px";
 const boardGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))",
 gap: 8,
 alignItems: "stretch",
 };
 const boardPanelStyle: React.CSSProperties = {
 border: "1px solid rgba(51,65,85,.75)",
 borderRadius: 12,
 background: "rgba(3,11,20,.78)",
 padding: 10,
 display: "grid",
 gap: 8,
 };
 const commandHighlightGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(250px,1fr))",
 gap: 8,
 alignItems: "stretch",
 };
 const commandHighlightCardStyle = (tone: string, background: string): React.CSSProperties => ({
 ...boardPanelStyle,
 border: `1px solid ${tone}`,
 background,
 gap: 10,
 });
 const commandHighlightTopStyle: React.CSSProperties = {
 display: "flex",
 justifyContent: "space-between",
 alignItems: "flex-start",
 gap: 10,
 };
 const commandHighlightTitleStyle: React.CSSProperties = {
 color: "#cbd5e1",
 fontSize: 10.5,
 fontWeight: 900,
 letterSpacing: ".08em",
 textTransform: "uppercase",
 };
 const commandHighlightNameStyle: React.CSSProperties = {
 color: "#f8fafc",
 fontSize: 18,
 fontWeight: 950,
 lineHeight: 1.15,
 };
 const commandQuickStripStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
 gap: 8,
 };
 const commandQuickItemStyle = (tone: string): React.CSSProperties => ({
 border: `1px solid ${tone}`,
 borderRadius: 10,
 background: "rgba(3,11,20,.78)",
 padding: "8px 10px",
 display: "grid",
 gap: 4,
 alignContent: "start",
 });
 const intelligenceDotStyle = (colour: string): React.CSSProperties => ({
 width: 8,
 height: 8,
 borderRadius: "50%",
 background: colour,
 flexShrink: 0,
 boxShadow: `0 0 0 1px ${colour}55`,
 });

 const runnerSelectorButtonStyle = (active: boolean): React.CSSProperties => ({
 border: active ? "1px solid #38bdf8" : "1px solid rgba(148,163,184,.22)",
 background: active ? "rgba(14,165,233,.16)" : "rgba(2,6,23,.72)",
 color: active ? "#e0f2fe" : "#cbd5e1",
 padding: "8px 11px",
 borderRadius: 8,
 cursor: "pointer",
 whiteSpace: "nowrap",
 fontWeight: 850,
 fontSize: 11,
 letterSpacing: ".01em",
 flexShrink: 0,
 });

 const boardPanelHeaderStyle: React.CSSProperties = {
 display: "flex",
 justifyContent: "space-between",
 alignItems: "center",
 gap: 10,
 color: "#dbe7f3",
 fontWeight: 900,
 textTransform: "uppercase",
 letterSpacing: ".08em",
 fontSize: 11,
 };
 const boardPanelSubStyle: React.CSSProperties = {
 color: "#94a3b8",
 fontSize: 10.5,
 fontWeight: 700,
 textTransform: "none",
 letterSpacing: "normal",
 };
 const compactBoardTableStyle: React.CSSProperties = {
 display: "grid",
 gap: 6,
 };
 const compactBoardHeaderStyle = (columns: string): React.CSSProperties => ({
 display: "grid",
 gridTemplateColumns: columns,
 gap: 8,
 paddingBottom: 6,
 borderBottom: "1px solid rgba(51,65,85,.6)",
 color: "#7f8ea3",
 fontSize: 10,
 fontWeight: 900,
 textTransform: "uppercase",
 letterSpacing: ".08em",
 });
 const compactBoardRowStyle = (columns: string): React.CSSProperties => ({
 display: "grid",
 gridTemplateColumns: columns,
 gap: 8,
 alignItems: "center",
 padding: "6px 0",
 borderBottom: "1px solid rgba(15,23,42,.55)",
 color: "#e5edf8",
 fontSize: 11,
 });
 const selectedWorkspaceGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "minmax(0,1.25fr) minmax(0,1fr)",
 gap: 8,
 alignItems: "start",
 };
 const selectedWorkspaceRightGridStyle: React.CSSProperties = {
 display: "grid",
 gap: 8,
 };
 const compactValueGridStyle = (columns = 4): React.CSSProperties => ({
 display: "grid",
 gridTemplateColumns: `repeat(${columns}, minmax(0,1fr))`,
 gap: 6,
 });
 const valueTileStyle: React.CSSProperties = {
 border: "1px solid rgba(51,65,85,.75)",
 borderRadius: 10,
 background: "rgba(2,8,16,.74)",
 padding: "8px 9px",
 display: "grid",
 gap: 3,
 };

 const dossierSectionStyle: React.CSSProperties = {
 border: "1px solid rgba(51,65,85,.75)",
 borderRadius: 12,
 background: "linear-gradient(180deg, rgba(9,15,26,.95), rgba(3,8,18,.92))",
 padding: 12,
 display: "grid",
 gap: 10,
 };

 const dossierHeaderStyle: React.CSSProperties = {
 display: "flex",
 justifyContent: "space-between",
 alignItems: "center",
 gap: 12,
 };

 const dossierTitleStyle: React.CSSProperties = {
 color: "#eaf2ff",
 fontWeight: 1000,
 fontSize: 14,
 letterSpacing: ".08em",
 textTransform: "uppercase",
 };

 const dossierSubTitleStyle: React.CSSProperties = {
 color: "#94a3b8",
 fontSize: 11,
 };

 const dossierMetricGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(4,minmax(0,1fr))",
 gap: 8,
 };

 const dossierNarrativeStyle: React.CSSProperties = {
 borderTop: "1px solid rgba(51,65,85,.5)",
 paddingTop: 10,
 color: "#dbe7fb",
 fontSize: 12,
 lineHeight: 1.6,
 };
 const advancedDetailsStyle: React.CSSProperties = {
 ...panelStyle,
 padding: 0,
 overflow: "hidden",
 };
 const advancedSummaryStyle: React.CSSProperties = {
 listStyle: "none",
 cursor: "pointer",
 padding: "12px 14px",
 display: "flex",
 justifyContent: "space-between",
 alignItems: "center",
 gap: 10,
 color: "#c9d7ee",
 fontWeight: 900,
 textTransform: "uppercase",
 letterSpacing: ".08em",
 background: "rgba(7,16,29,.96)",
 borderBottom: "1px solid rgba(51,65,85,.7)",
 };
 const whyRankedGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
 gap: 8,
 };
 function renderMetricValue(value: number | null, digits = 0, signedMode = false): string {
 if (value === null || !Number.isFinite(value)) return "-";
 return signedMode ? signed(value, digits) : value.toFixed(digits);
 }
 const ratingDotColor = (value: number | null): string => {
 if (value === null || !Number.isFinite(value)) return "#64748b";
 if (value >= 80) return "#34d399";
 if (value >= 70) return "#ffffff";
 if (value >= 60) return "#eaf2ff";
 if (value >= 50) return "#ffffff";
 return "#f87171";
 };

 const ratingBandLabel = (value: number | null): string => {
 if (value === null || !Number.isFinite(value)) return "No rating";
 if (value >= 80) return "Elite";
 if (value >= 70) return "Strong";
 if (value >= 60) return "Competitive";
 if (value >= 50) return "Moderate";
 return "Weak";
 };

 const renderRatingDot = (value: number | null, label: string) => {
 const dotColor = ratingDotColor(value);
 return (
 <span
 title={`${label}: ${ratingBandLabel(value)}${value !== null && Number.isFinite(value) ? ` (${renderMetricValue(value, 1)})` : ""}`}
 style={{
 width: 7,
 height: 7,
 borderRadius: 999,
 background: dotColor,
 boxShadow: `0 0 8px ${dotColor}88`,
 display: "inline-block",
 flexShrink: 0,
 }}
 />
 );
 };

 const renderRatingCell = (value: number | null, label: string) => (
 <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 6, color: "#edf3fb", fontWeight: 600, fontSize: 11 }}>
 <span>{renderMetricValue(value, 1)}</span>
 {renderRatingDot(value, label)}
 </span>
 );
 const ratingHoverCardStyle: React.CSSProperties = {
 position: "fixed",
 zIndex: 80,
 width: 320,
 maxWidth: "min(92vw, 320px)",
 padding: 12,
 borderRadius: 12,
 border: "1px solid rgba(125,211,252,.28)",
 background: "rgba(3,10,18,.97)",
 boxShadow: "0 18px 40px rgba(2,6,23,.48)",
 backdropFilter: "blur(10px)",
 pointerEvents: "none",
 display: "grid",
 gap: 10,
 };
 const ratingHoverGridStyle: React.CSSProperties = {
 display: "grid",
 gridTemplateColumns: "repeat(2,minmax(0,1fr))",
 gap: 8,
 };
 const ratingHoverTileStyle: React.CSSProperties = {
 borderRadius: 10,
 border: "1px solid rgba(51,65,85,.65)",
 background: "rgba(8,15,28,.9)",
 padding: "7px 8px",
 display: "grid",
 gap: 3,
 };
 const ratingHoverWrapStyle: React.CSSProperties = {
 display: "inline-flex",
 alignItems: "center",
 justifyContent: "center",
 width: "100%",
 cursor: "help",
 };

 const placeRatingHoverCard = (
 event: React.MouseEvent<HTMLElement>,
 card: Omit<RatingHoverCard, "x" | "y">,
 ) => {
 const width = 320;
 const estimatedHeight = 300;
 const viewportWidth = typeof window !== "undefined" ? window.innerWidth : 1440;
 const viewportHeight = typeof window !== "undefined" ? window.innerHeight : 900;
 const margin = 18;
 let x = event.clientX + 18;
 let y = event.clientY + 18;

 if (x + width > viewportWidth - margin) {
 x = Math.max(margin, event.clientX - width - 18);
 }
 if (y + estimatedHeight > viewportHeight - margin) {
 y = Math.max(margin, viewportHeight - estimatedHeight - margin);
 }

 setRatingHover({ ...card, x, y });
 };

 const clearRatingHover = () => setRatingHover(null);

 const hoverWrap = (
 content: React.ReactNode,
 card: Omit<RatingHoverCard, "x" | "y"> | null,
 onctivate?: () => void,
 ) => {
 if (!card && !onctivate) return content;
 const interactive = !!onctivate;
 return (
 <span
 role={interactive ? "button" : undefined}
 tabIndex={interactive ? 0 : undefined}
 style={{
 ...ratingHoverWrapStyle,
 cursor: interactive ? "pointer" : "help",
 }}
 onMouseEnter={(event) => {
 if (card) placeRatingHoverCard(event, card);
 }}
 onMouseMove={(event) => {
 if (card) placeRatingHoverCard(event, card);
 }}
 onMouseLeave={clearRatingHover}
 onClick={(event) => {
 if (!onctivate) return;
 event.stopPropagation();
 onctivate();
 }}
 onKeyDown={(event) => {
 if (!onctivate) return;
 if (event.key === "Enter" || event.key === " ") {
 event.preventDefault();
 event.stopPropagation();
 onctivate();
 }
 }}
 >
 {content}
 </span>
 );
 };

 const buildRunHoverCard = (
 runnerName: string,
 run: Row | undefined,
 title: string,
 footer?: string,
 ): Omit<RatingHoverCard, "x" | "y"> | null => {
 if (!run) return null;

 const figure = historyRatingValue(run);
 const metrics: RatingHoverMetric[] = [
 { label: "Date", value: formatHistoryDate(historyDateText(run)), tone: "#ffffff" },
 { label: "Track", value: historyTrackText(run) },
 { label: "Distance", value: historyDistanceText(run) },
 { label: "Class", value: historyClassText(run) },
 { label: "Position", value: historyFinishText(run) },
 { label: "Figure", value: renderStaticMetricValue(figure, 1), tone: ratingDotColor(figure) },
 { label: "SP", value: historySpText(run) },
 {
 label: "In-Run",
 value: [firstText(run, ["pos_800"], ""), firstText(run, ["pos_400"], "")]
 .filter(Boolean)
 .map((value, index) => (index === 0 ? `800m ${value}` : `400m ${value}`))
 .join(" | ") || "-",
 },
 ];

 const extraLines = [
 historyGoingText(run) !== "-" ? `Going ${historyGoingText(run)}` : "",
 historyBarrierText(run) !== "-" ? `Barrier ${historyBarrierText(run)}` : "",
 historyJockeyText(run) !== "-" ? `Jockey ${historyJockeyText(run)}` : "",
 historyWeightText(run) !== "-" ? `Weight ${historyWeightText(run)}` : "",
 historyRaceStrengthText(run) !== "-" ? `Race Strength ${historyRaceStrengthText(run)}` : "",
 firstText(run, ["margin"], "-") !== "-" ? `Margin ${firstText(run, ["margin"], "-")}` : "",
 ].filter(Boolean);

 return {
 title,
 subtitle: runnerName,
 metrics,
 sections: extraLines.length ? [{ title: "Run Detail", lines: extraLines }] : [],
 footer: footer || "Historical run evidence from EDGEiQ rating history.",
 };
 };

 const buildAverageHoverCard = (
 runnerName: string,
 historyRows: Row[],
 averageRating: number | null,
 peakRatingValue: number | null,
 ): Omit<RatingHoverCard, "x" | "y"> | null => {
 const ratedRuns = historyRows
 .map((row) => ({ row, rating: historyRatingValue(row) }))
 .filter((entry): entry is { row: Row; rating: number } => entry.rating !== null && Number.isFinite(entry.rating))
 .slice(0, 5);

 if (!averageRating && !ratedRuns.length) return null;

 const ratings = ratedRuns.map((entry) => entry.rating);
 const best = ratings.length ? Math.max(...ratings) : peakRatingValue;
 const worst = ratings.length ? Math.min(...ratings) : null;
 const variance = ratingVariance(ratings);

 return {
 title: "verage Last 5",
 subtitle: runnerName,
 metrics: [
 { label: "verage", value: renderStaticMetricValue(averageRating, 1), tone: "#f8fafc" },
 { label: "Best", value: renderStaticMetricValue(best, 1), tone: ratingDotColor(best) },
 { label: "Worst", value: renderStaticMetricValue(worst, 1), tone: ratingDotColor(worst) },
 { label: "Variance", value: renderStaticMetricValue(variance, 2), tone: "#94a3b8" },
 { label: "Runs", value: String(ratedRuns.length || 0) },
 ],
 sections: ratedRuns.length
 ? [{ title: "Last five ratings", lines: ratedRuns.map((entry) => compactHistoryLine(entry.row)) }]
 : [{ title: "Last five ratings", lines: ["Detailed run history is not available in the current form feed."] }],
 footer: "LS / AVG5 / PEK use the EDGEiQ runner form engine and current rating history source.",
 };
 };

 const buildPeakHoverCard = (
 runnerName: string,
 peakRun: Row | undefined,
 peakRatingValue: number | null,
 todayRatingValue: number | null,
 lastRatingValue: number | null,
 ): Omit<RatingHoverCard, "x" | "y"> | null => {
 if (!peakRun && peakRatingValue === null) return null;
 const deltaVsLast =
 todayRatingValue !== null && lastRatingValue !== null ? todayRatingValue - lastRatingValue : null;
 const peakProximity =
 todayRatingValue !== null && peakRatingValue !== null && peakRatingValue > 0
 ? (todayRatingValue / peakRatingValue) * 100
 : null;

 return {
 title: "Peak Rating",
 subtitle: runnerName,
 metrics: [
 { label: "Peak", value: renderStaticMetricValue(peakRatingValue, 1), tone: ratingDotColor(peakRatingValue) },
 { label: "Today", value: renderStaticMetricValue(todayRatingValue, 1), tone: ratingDotColor(todayRatingValue) },
 { label: "Delta vs LS", value: deltaVsLast === null ? "-" : signed(deltaVsLast, 1), tone: "#94a3b8" },
 { label: "Peak %", value: peakProximity === null ? "-" : `${peakProximity.toFixed(0)}%`, tone: "#ffffff" },
 ],
 sections: peakRun
 ? [{ title: "Peak run", lines: [compactHistoryLine(peakRun)] }]
 : [{ title: "Peak run", lines: ["Peak run detail is not available in the current history feed."] }],
 footer: "Peak proximity compares today's projected figure with the best rated historical run.",
 };
 };

 const buildTodayProjectionHoverCard = (
 runnerName: string,
 todayRatingValue: number | null,
 lastRatingValue: number | null,
 peakRatingValue: number | null,
 trendLabel: string,
 ): Omit<RatingHoverCard, "x" | "y"> | null => {
 if (todayRatingValue === null && lastRatingValue === null && peakRatingValue === null) return null;
 const deltaVsLast =
 todayRatingValue !== null && lastRatingValue !== null ? todayRatingValue - lastRatingValue : null;
 const peakProximity =
 todayRatingValue !== null && peakRatingValue !== null && peakRatingValue > 0
 ? (todayRatingValue / peakRatingValue) * 100
 : null;

 return {
 title: "Today Projection",
 subtitle: runnerName,
 metrics: [
 { label: "Today", value: renderStaticMetricValue(todayRatingValue, 1), tone: ratingDotColor(todayRatingValue) },
 { label: "Last Start", value: renderStaticMetricValue(lastRatingValue, 1), tone: ratingDotColor(lastRatingValue) },
 { label: "Delta", value: deltaVsLast === null ? "-" : signed(deltaVsLast, 1), tone: "#94a3b8" },
 { label: "Peak", value: renderStaticMetricValue(peakRatingValue, 1), tone: ratingDotColor(peakRatingValue) },
 { label: "Peak %", value: peakProximity === null ? "-" : `${peakProximity.toFixed(0)}%`, tone: "#ffffff" },
 { label: "Trend", value: trendLabel || "-", tone: cellTone(trendLabel || "") },
 ],
 sections: [
 {
 title: "Projection context",
 lines: [
 deltaVsLast === null
 ? "No last-start comparison available."
 : `Today's figure is ${signed(deltaVsLast, 1)} versus last start.`,
 peakProximity === null
 ? "Peak proximity unavailable."
 : `Today's figure sits at ${peakProximity.toFixed(0)}% of historical peak.`,
 ],
 },
 ],
 footer: "Today uses the current EDGEiQ projected performance figure. It is a rating reference, not a wagering instruction.",
 };
 };
 const resetHistoricalDrawer = () => {
 setHistoricalDrawerOpen(false);
 setSelectedHistoricalRun(null);
 setHistoricalDrawerRuns([]);
 setHistoricalDrawerSourceLabel("LST STRT");
 setHistoricalDrawerRunnerKey("");
 setHistoricalDrawerRunnerName("");
 };

 const openHistoricalRunDrawer = (options: {
 runnerKey: string;
 runnerName: string;
 sourceLabel: string;
 runs: Row[];
 selectedRun?: Row;
 }) => {
 const seen = new Set<string>();
 const uniqueRuns = options.runs.filter((run) => {
 const key = historyRunKey(run);
 if (!key || seen.has(key)) return false;
 seen.add(key);
 return true;
 });
 const fallbackRun = options.selectedRun || uniqueRuns[0];
 if (!fallbackRun) return;
 clearRatingHover();
 setSelectedKey(options.runnerKey);
 setDrawerOpen(true);
 setRunnerSubMode("FORM");
 setHistoricalDrawerOpen(true);
 setHistoricalDrawerRuns(uniqueRuns.length ? uniqueRuns : [fallbackRun]);
 setSelectedHistoricalRun(fallbackRun);
 setHistoricalDrawerSourceLabel(options.sourceLabel);
 setHistoricalDrawerRunnerKey(options.runnerKey);
 setHistoricalDrawerRunnerName(options.runnerName);
 };

 useEffect(() => {
 if (!historicalDrawerOpen || !historicalDrawerRunnerKey) return;
 if (!selectedKey || selectedKey === historicalDrawerRunnerKey) return;
 resetHistoricalDrawer();
 }, [historicalDrawerOpen, historicalDrawerRunnerKey, selectedKey]);

 const renderEvidenceBar = (value: number | null, maxValue: number, color: string) => {
 if (value === null || !Number.isFinite(value)) {
 return <div style={evidenceMetricTrackStyle}><div style={barFill(0, "#475569")} /></div>;
 }
 return (
 <div style={evidenceMetricTrackStyle}>
 <div style={barFill(performanceBarPct(value, maxValue), color)} />
 </div>
 );
 };

 if (loading) {
 return <div style={pageStyle}><section style={panelStyle}>Loading Race Intelligence...</section></div>;
 }

 if (futureMeetingWithoutFields) {
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
 <div className="edgeiq-mini-note-label">Intelligence Pending</div>
 <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
 Fields are not available yet. EDGEiQ is monitoring this meeting and will populate race intelligence, track profile and market views automatically once runners are released.
 </div>
 </div>

 <div style={miniGridStyle}>
 <div style={miniTileStyle}><span style={miniLabelStyle}>Market</span><strong style={{ ...miniValueStyle, color: "#ffffff" }}>WITING FEED</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>TB prices not available yet</em></div>
 <div style={miniTileStyle}><span style={miniLabelStyle}>Track Profile</span><strong style={{ ...miniValueStyle, color: "#ffffff" }}>PROFILE PENDING</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>Track intelligence pending</em></div>
 <div style={miniTileStyle}><span style={miniLabelStyle}>Race Intelligence</span><strong style={{ ...miniValueStyle, color: "#34d399" }}>INTELLIGENCE PENDING</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>Race intelligence will populate automatically</em></div>
 </div>
 </div>
 </section>
 </div>
 );
 }

 if (futureMeetingWithFields && !raceRows.length) {
 return (
 <div style={pageStyle}>
 <section style={panelStyle}>
 <div style={titleStyle}>
 <span>Meeting Preview</span>
 <em>{futureMeetingDayBucket}</em>
 </div>

 <div style={{ display: "grid", gap: 10 }}>
 <div style={miniGridStyle}>
 <div className="edgeiq-mini-note">
 <div className="edgeiq-mini-note-label">Selected Meeting</div>
 <div className="edgeiq-mini-note-value">{futureMeetingTrack || "Upcoming meeting"}</div>
 <div className="edgeiq-mini-note-sub">
 {futureMeetingDate || "Date TBC"} | {futureMeetingStatus}
 </div>
 </div>
 <div className="edgeiq-mini-note">
 <div className="edgeiq-mini-note-label">Selected Race</div>
 <div className="edgeiq-mini-note-value">{futureMeetingSelectedRace}</div>
 <div className="edgeiq-mini-note-sub">
 {futureMeetingSelectedMeta || "Fields are loaded and EDGEiQ is monitoring this race."}
 </div>
 </div>
 </div>

 <div className="edgeiq-mini-note">
 <div className="edgeiq-mini-note-label">Intelligence Pending</div>
 <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
 Runner fields are loaded for this future race. Race intelligence, track profile and TB-linked market views will populate automatically closer to race day.
 </div>
 </div>

 <div style={miniGridStyle}>
 <div style={miniTileStyle}><span style={miniLabelStyle}>Market</span><strong style={{ ...miniValueStyle, color: "#ffffff" }}>WITING FEED</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>TB prices not available yet</em></div>
 <div style={miniTileStyle}><span style={miniLabelStyle}>Track Profile</span><strong style={{ ...miniValueStyle, color: "#ffffff" }}>PROFILE PENDING</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>Track intelligence pending</em></div>
 <div style={miniTileStyle}><span style={miniLabelStyle}>Race Intelligence</span><strong style={{ ...miniValueStyle, color: "#34d399" }}>INTELLIGENCE PENDING</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>Race intelligence will populate automatically</em></div>
 <div style={miniTileStyle}><span style={miniLabelStyle}>Declared Field</span><strong style={{ ...miniValueStyle, color: "#e2e8f0" }}>{futureMeetingFieldCount || "FIELDS READY"}</strong><em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal", lineHeight: 1.3 }}>{futureMeetingFieldCount ? "runners currently loaded" : "runner fields available"}</em></div>
 </div>
 </div>
 </section>

 {raceRows.length ? (
 <section style={{ ...panelStyle, overflowX: "auto" }}>
 <div style={titleStyle}>
 <span>Declared Field</span>
 <em>{futureMeetingFieldCount} runners loaded</em>
 </div>

 <div style={{ display: "grid", gap: 6, minWidth: 760 }}>
 <div
 style={{
 display: "grid",
 gridTemplateColumns: "55px 1.7fr 80px 160px 140px",
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
 <span style={{ textAlign: "center" }}>Status</span>
 </div>

 {raceRows.map((row) => {
 const scratched = isScratchedRunner(row);
 return (
 <div
 key={`${track(row)}|${raceNo(row)}|${cleanHorse(horse(row))}`}
 style={{
 display: "grid",
 gridTemplateColumns: "55px 1.7fr 80px 160px 140px",
 gap: 8,
 alignItems: "center",
 padding: "11px 12px",
 border: scratched
 ? "1px solid rgba(100,116,139,.28)"
 : "1px solid rgba(80,120,180,.22)",
 borderRadius: 10,
 background: scratched ? "rgba(30,41,59,.18)" : "rgba(5,12,22,.82)",
 opacity: scratched ? 0.46 : 1,
 filter: scratched ? "grayscale(0.85)" : undefined,
 }}
 >
 <span style={{ textAlign: "center", color: scratched ? "#94a3b8" : "#dbeafe" }}>{saddle(row) === 999 ? "-" : saddle(row)}</span>
 <strong style={{ color: scratched ? "#cbd5e1" : "#f4f7fb", textDecoration: scratched ? "line-through" : "none", textAlign: "center" }}>{horse(row)}</strong>
 <span style={{ textAlign: "center", color: scratched ? "#94a3b8" : "#dbeafe" }}>{barrier(row)}</span>
 <span style={{ textAlign: "center", color: scratched ? "#94a3b8" : "#dbeafe" }}>{firstText(row, ["jockey", "rider"], "-")}</span>
 <span style={{ textAlign: "center", color: scratched ? "#94a3b8" : "#bbf7d0", fontWeight: 900 }}>{scratched ? "SCRATCHED" : "FIELDS READY"}</span>
 </div>
 );
 })}
 </div>
 </section>
 ) : null}
 </div>
 );
 }

 if (productView === "HOME") {
  return (
    <HomeScreen
      productShellMeetings={productShellMeetings}
      updateProductView={updateProductView}
      shellTrack={shellTrack}
      shellRaceNo={shellRaceNo}
      setIntelMode={setIntelMode}
      openShellMeeting={openShellMeeting}
    />
  );
}

if (productView === "MEETINGS") {
  return (
    <MeetingsScreen
      productShellMeetings={productShellMeetings}
      productShellRaces={productShellRaces}
      selectedShellMeeting={selectedShellMeeting}
      selectedShellMeetingRaces={selectedShellMeetingRaces}
      runnerRows={runnerRows}
      shellTrack={shellTrack}
      shellRaceNo={shellRaceNo}
      pageStyle={pageStyle}
      intelModeTabs={intelModeTabs}
      updateProductView={updateProductView}
      openShellMeeting={openShellMeeting}
      openShellRace={openShellRace}
      setShellMeetingKey={setShellMeetingKey}
      setIntelMode={setIntelMode}
    />
  );
}

 if (!raceRows.length || !header) {
 const emptyRaceLabel = selectedShellRace
 ? `${selectedShellRace.trackName} R${selectedShellRace.raceNoValue}`
 : [shellTrack || props.selectedTrack || props.currentRace?.track, selectedRaceNo ? `R${selectedRaceNo}` : ""].filter(Boolean).join(" ") || "Selected race";
 const emptyRaceReason = selectedRaceDate
 ? `No runner-board rows matched ${emptyRaceLabel} on ${selectedRaceDate}.`
 : `No runner-board rows matched ${emptyRaceLabel}.`;
  return (
  <div style={pageStyle}>
  <section style={panelStyle}>
  <div style={titleStyle}>
  <span>Race Intelligence</span>
  <em>No runner rows available.</em>
  </div>
  <div style={{ color: "#94a3b8" }}>
  {emptyRaceReason} Open a meeting/race with fields loaded, or refresh the governed runner board feed for this race.
  </div>
  </section>
  </div>
 );
 }

 const activeTabShell = (() => {
 const fallbackRunner = selected ? `${saddle(selected.row) === 999 ? "-" : saddle(selected.row)} ${horse(selected.row)}` : "Select runner";
 const raceMeta = [track(header) ? `${track(header)} R${raceNo(header)}` : "", distance(header), raceClass(header), `${activeRaceRows.length} runners`].filter((value) => value && value !== "-").join(" | ");
 const map: Record<IntelMode, { kicker: string; title: string; meta: string }> = {
 COMMND: { kicker: "RACE", title: "Race Intelligence", meta: raceMeta },
 RUNNERS: { kicker: "FIELD", title: "Race Field", meta: raceMeta },
 PERFORMANCE: { kicker: "PERFORMANCE", title: "EDGEiQ Performance Index", meta: raceMeta },
 FORM: { kicker: "FORM", title: "Runner Profile", meta: `${fallbackRunner} / career and recent form` },
 MP: { kicker: "MAP", title: "Speed Map & Race Shape", meta: raceMeta },
 NEXUS: { kicker: "LAB", title: "Racing Research Laboratory", meta: "Research / Profile / Compare / Discover" },
 STATS: { kicker: "STATS", title: statsMode === "TRAINERS" ? "Trainer Analytics" : "Jockey Analytics", meta: "Deep analytics and performance profiling" },
 DVNCED: { kicker: "MARKET", title: "EDGEiQ Trading Floor", meta: "Market intelligence / Fluctuations / Value / Context" },
 RESULTS: { kicker: "RESULTS", title: "Race Review & Intelligence", meta: "official result / sectionals / race review" },
 TRACK: { kicker: "TRACK", title: "Track Profile", meta: `${track(header)} / ${railDisplay !== "-" ? `Rail ${railDisplay}` : trackCondition(header)}` },
 WEATHER: { kicker: "CONDITIONS", title: "Conditions Intelligence", meta: `${track(header)} / ${trackCondition(header)} / ${distance(header)}` },
 };
 return map[intelMode] || map.COMMND;
 })();
 const activeRaceContextLine = [distance(header), raceClass(header), trackCondition(header).toUpperCase(), `${activeRaceRows.length} RUNNERS`].filter((value) => value && value !== "-").join(" | ");
 const activeRaceStartText = firstText(header, ["race_time", "jump_time", "start_time"], text(props.currentRace?.raceTime));
 const raceV3DisplayValue = (value: unknown) => { const raw = String(value ?? "").trim(); return raw && raw !== "-" ? raw : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"; };
 const raceV3RaceCountLabel = (value: unknown) => { const count = Number(value); return Number.isFinite(count) && count > 0 ? `${count} races` : "Race list pending"; };
 const raceV3FieldCountLabel = (value: unknown) => { const count = Number(value); return Number.isFinite(count) && count > 0 ? `${count} runners` : "Fields pending"; };
 const formatMeetingDateLong = (value: string) => {
 const parsed = value ? new Date(`${value}T12:00:00`) : null;
 if (!parsed || Number.isNaN(parsed.getTime())) return raceV3DisplayValue(value);
 return parsed.toLocaleDateString("en-AU", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
 };
 const switchShellRaceInPlace = (race: typeof productShellRaces[number]) => {
 if (race.fieldSize <= 0) {
 openShellRace(race);
 return;
 }
 setShellMeetingKey(race.meetingKey);
 setShellTrack(race.trackName);
 setShellRaceNo(race.raceNoValue);
 setShellRaceDate(race.meetingDate);
 setShellRaceKey(race.raceKey);
 setSelectedKey("");
 updateProductView("RCE");
 };
 const raceRail = selectedShellMeeting && selectedShellMeetingRaces.length ? (
 <aside className={`edgeiq-race-v3-rail ${raceRailCollapsed ? "is-collapsed" : ""}`} aria-label="Meeting race navigator">
 <div className="edgeiq-race-v3-rail-head">
 <strong>{selectedShellMeeting.trackName}</strong>
 <span>{formatMeetingDateLong(selectedShellMeeting.meetingDate)}</span>
 <em>{raceV3RaceCountLabel(selectedShellMeetingRaces.length || selectedShellMeeting.raceCount)}</em>
 </div>
 <button type="button" className="edgeiq-race-v3-collapse" onClick={() => setRaceRailCollapsed((value) => !value)}>
 {raceRailCollapsed ? "Expand" : "Collapse"}
 </button>
 <div className="edgeiq-race-v3-race-list">
 {selectedShellMeetingRaces.map((race) => {
 const active = shellRaceKey ? race.raceKey === shellRaceKey : race.raceNoValue === selectedRaceNo;
 return (
 <button type="button" key={`race-v3-nav-${race.raceKey}`} className={active ? "is-active" : ""} disabled={race.fieldSize <= 0} onClick={() => switchShellRaceInPlace(race)}>
 <b>{raceRailCollapsed ? race.raceNoValue : `R${race.raceNoValue}`}</b>
 <span>{race.raceClassValue}</span>
 <em>{race.distanceValue}</em>
 <i className="edgeiq-race-v3-hover-card">
 <strong>R{race.raceNoValue}</strong>
 <span>{race.raceClassValue}</span>
 <span>{race.distanceValue}</span>
 <span>{raceV3FieldCountLabel(race.fieldSize)}</span>
 <span>{activeRaceStartText ? `${activeRaceStartText} jump` : "Time TBC"}</span>
 <span>{race.trackConditionValue}</span>
 <span>Rail {race.railValue && race.railValue !== "-" ? race.railValue : "Pending"}</span>
 <small>Click to view</small>
 </i>
 </button>
 );
 })}
 </div>
 <section className="edgeiq-race-v3-status">
 <strong>Race Status</strong>
 <span><i /> Upcoming</span>
 <span><i /> In Progress</span>
 <span><i /> Results</span>
 <span><i /> Completed</span>
 </section>
 <button type="button" className="edgeiq-race-v3-pin">Pin Meeting</button>
 <p>Updated: {new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })}</p>
 </aside>
 ) : null;

 return (
 <div className="edgeiq-product-app edgeiq-product-race edgeiq-product-surface edgeiq-product-v4-page" style={pageStyle}>
 <section className="edgeiq-product-v4-shell" aria-label="EDGEiQ race workspace">
 <div className="edgeiq-home-v4-top edgeiq-product-v4-top">
 <button type="button" className="edgeiq-home-v4-brand edgeiq-product-v4-brand edgeiq-race-v3-brand" onClick={() => updateProductView("HOME")}>
 <span className="edgeiq-home-v4-brand-copy edgeiq-product-v4-brand-copy">
 <strong>EDGE<span>iQ</span></strong>
 <em>RACE INTELLIGENCE</em>
 </span>
 </button>
 <button type="button" className="edgeiq-race-v3-menu" aria-label="Collapse race navigator" onClick={() => setRaceRailCollapsed((value) => !value)}>ÃƒÂ¢Ã‹Å“Ã‚Â°</button>

 <nav className="edgeiq-home-v4-nav edgeiq-product-v4-nav" aria-label="Race navigation">
 <button
 type="button"
 className="edgeiq-product-v4-nav-button"
 onClick={() => updateProductView("HOME")}
 >
 HOME
 </button>
 <button
 type="button"
 className="edgeiq-product-v4-nav-button"
 onClick={() => { setShellMeetingKey(""); updateProductView("MEETINGS"); }}
 >
 MEETINGS
 </button>
 {intelModeTabs.map((tab) => (
 <button
 key={`product-race-nav-${tab.mode}`}
 type="button"
 className={`edgeiq-product-v4-nav-button ${intelMode === tab.mode ? "is-active" : ""}`}
 onClick={() => setIntelMode(tab.mode)}
 >
 {tab.label}
 </button>
 ))}
 </nav>

 <div className="edgeiq-home-v4-terminal edgeiq-product-v4-terminal" aria-label="Terminal status">
 <span>TERMINAL</span>
 <i />
 <strong>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</strong>
 <button type="button" aria-label="Search">ÃƒÂ¢Ã…â€™Ã¢â‚¬Â¢</button>
 <button type="button" aria-label="Notifications">ÃƒÂ¢Ã¢â€žÂ¢Ã‚Â§</button>
 <button type="button" className="edgeiq-product-v4-account-chip" aria-label="Account">T</button>
 </div>
 </div>

 <div className={`edgeiq-race-v3-layout ${raceRail ? "has-rail" : ""}`}>
 {raceRail}
 <main className="edgeiq-race-v3-main">
 {intelMode !== "COMMND" ? <div className="edgeiq-race-lock-context">
 <div>
 <span>{activeTabShell.kicker}</span>
 <h1>{track(header) || shellTrack} <em>ÃƒÂ¢Ã¢â€šÂ¬Ã‚Âº</em> R{raceNo(header) || selectedRaceNo}</h1>
 <p>{raceClass(header)} <i /> {distance(header)} <i /> {activeRaceStartText || "Time TBC"}</p>
 </div>
 <section>
 <span>{trackCondition(header)}</span>
 <span>Rail {railDisplay !== "-" ? railDisplay : "Pending"}</span>
 <span>{firstText(header, ["minutes_to_jump", "time_to_jump", "jump_countdown"], "Pending to jump")}</span>
 </section>
 </div> : null}

 {intelMode === "COMMND" ? (() => {
 const raceRowsForTab = activeRaceRows.filter((item) => !isScratched(item));
 const raceFieldSize = raceRowsForTab.length || activeRaceRows.length;
 const runnerEpiValue = (item: EnrichedRunner) => firstNum(item.ratingsHeatmap, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(item);
 const projectedRating = (item: EnrichedRunner) => projectionRatingValue(item);
 const raceStandardValue = activeRaceRows.map((item) => firstNum(item.ratingsHeatmap, ["expected_rating"])).find((value) => value !== null) ?? null;
 const runnerRatings = activeRaceRows.map((item) => runnerEpiValue(item)).filter((value): value is number => value !== null);
 const ratingSpread = runnerRatings.length ? Math.max(...runnerRatings) - Math.min(...runnerRatings) : null;
 const averageRating = runnerRatings.length ? runnerRatings.reduce((sum, value) => sum + value, 0) / runnerRatings.length : null;
 const raceShapeText = displayExpectedTempo !== "-" ? displayExpectedTempo : fallbackTempoLabel !== "-" ? fallbackTempoLabel : "Balanced";
 const raceStrengthText = ratingSpread === null ? "Pending" : ratingSpread >= 12 ? "Deep" : ratingSpread >= 7 ? "Competitive" : "Even";
 const raceQualityText = averageRating === null ? "Pending" : averageRating >= 82 ? "High" : averageRating >= 68 ? "Solid" : "Building";
 const cleanWeight = (row: Row) => firstText(row, ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg", "wgt"], "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â");
 const weightValues = activeRaceRows.map((item) => num(cleanWeight(item.row))).filter((value): value is number => value !== null);
 const weightRange = weightValues.length ? `${Math.min(...weightValues).toFixed(1)} - ${Math.max(...weightValues).toFixed(1)}kg` : "Pending";
 const raceMapSource = activeRaceRows.map((item) => item.mapEnrichment).find(Boolean) || {};
 const racePacePressure = firstText(raceMapSource, ["race_pressure_band_v3", "race_pressure_band_v2", "race_pressure_band_display"], raceShapeText);
 const raceMapAdvantage = firstText(raceMapSource, ["pace_advantage_display_v3", "pace_advantage_display"], "Balanced");
 const raceKeyRisk = firstText(raceMapSource, ["race_shape_verdict_v3", "race_shape_verdict_v2"], "");
 const trackPlaying = firstText(trackIntel, ["track_playing", "track_pattern", "track_advantage_summary"], "Pending");
 const trueTrackRating = firstText(trackIntel, ["edgeiq_true_track_rating", "true_track_rating", "track_rating_true"], trackCondition(header));
 const trackLengths = firstText(trackIntel, ["lengths_faster_slower", "track_lengths_delta", "track_speed_delta"], "Pending");
 const topRated = [...activeRaceRows].sort((a, b) => (runnerEpiValue(b) ?? -999) - (runnerEpiValue(a) ?? -999))[0];
 const bestValue = [...activeRaceRows].filter((item) => edgePct(item.row, item.bet) !== null).sort((a, b) => (edgePct(b.row, b.bet) ?? -999) - (edgePct(a.row, a.bet) ?? -999))[0];
 const openPriceFor = (item: EnrichedRunner) => firstNum({ ...(item.row || {}), ...(item.bet || {}) }, ["open_price", "opening_price", "display_open_price", "market_open_price"]);
 const livePriceRows = [...activeRaceRows].filter((item) => livePrice(item.row, item.bet) !== null).sort((a, b) => (livePrice(a.row, a.bet) ?? 999) - (livePrice(b.row, b.bet) ?? 999));
 const favourite = livePriceRows[0];
 const secondFavourite = livePriceRows[1];
 const priceTimestamp = firstText(header, ["price_timestamp", "market_timestamp", "last_updated", "updated_at"], "");
 const flucFor = (item: EnrichedRunner) => {
 const open = openPriceFor(item);
 const current = livePrice(item.row, item.bet);
 return open !== null && current !== null && open > 0 ? ((current - open) / open) * 100 : null;
 };
 const raceTopThreeRows = [...activeRaceRows].sort((a, b) => (runnerEpiValue(b) ?? -999) - (runnerEpiValue(a) ?? -999)).slice(0, 3);
 const raceMiniMapRows = [...activeRaceRows].sort((a, b) => {
 const roleOrder: Record<string, number> = { LEADER: 1, "ON PACE": 2, MIDFIELD: 3, BACKMARKER: 4 };
 const aRole = roleOrder[paceMapRole(a)] || 9;
 const bRole = roleOrder[paceMapRole(b)] || 9;
 if (aRole !== bRole) return aRole - bRole;
 const aBarrier = Number(barrier(a.row) || 999);
 const bBarrier = Number(barrier(b.row) || 999);
 return aBarrier - bBarrier;
 }).slice(0, 12);
 const expectedLeader = raceMiniMapRows.find((item) => paceMapRole(item) === "LEADER") || raceMiniMapRows[0];
 const whatMatters = [
 racePacePressure !== "-" ? `${racePacePressure} tempo expected.` : "",
 raceMapAdvantage !== "-" ? `${raceMapAdvantage} map advantage in play.` : "",
 trackLengths !== "Pending" ? `Track playing ${trackLengths}.` : "",
 runnerRatings.length >= 3 ? "Two or more high-rating runners shape the race." : "",
 bettingConfidence !== "-" ? `Market confidence ${bettingConfidence.toLowerCase()}.` : "Market confidence pending.",
 raceKeyRisk,
 ].filter((value) => value && value !== "-").slice(0, 5);
 const headerCondition = trackCondition(header);
 const headerRail = railDisplay !== "-" ? railDisplay : "Pending";
 const selectedRaceLabel = `${track(header) || shellTrack} > R${raceNo(header) || selectedRaceNo}`;
 const overviewCards = [
 ["Prizemoney", firstText(header, ["prizemoney", "prize_money", "total_prizemoney"], "Pending")],
 ["Class", raceClass(header)],
 ["Weight Range", weightRange],
 ["Acceptances", String(activeRaceRows.length)],
 ["Scratchings", String(activeRaceRows.filter(isScratched).length)],
 ];
 return (
 <section className="edgeiq-race-v3 edgeiq-product-section" aria-label="EDGEiQ Race Intelligence">
 <div className="edgeiq-race-v3-header">
 <div>
 <h1>{selectedRaceLabel}</h1>
 <div className="edgeiq-race-v3-meta"><span>{raceClass(header)}</span><span>{distance(header)}</span><span>{activeRaceStartText || "Time TBC"}</span></div>
 <div className="edgeiq-race-v3-submeta"><span>{headerCondition}</span><span>Rail {headerRail}</span><span>{firstText(header, ["minutes_to_jump", "time_to_jump", "jump_countdown"], "Pending to jump")}</span></div>
 </div>
 <section className="edgeiq-race-v3-overview">
 <strong>Race Overview</strong>
 {overviewCards.map(([label, value]) => <div key={`race-v3-overview-${label}`}><span>{label}</span><em>{value && value !== "-" ? value : "Pending"}</em></div>)}
 </section>
 </div>
 <div className="edgeiq-race-v3-hero-cards">
 <article className="edgeiq-race-v3-card top-rated">
 <span>Top Rated</span>
 <div className="edgeiq-race-v3-runner-feature"><span className="edgeiq-field-silk" aria-label={`${topRated ? horse(topRated.row) : "Runner"} silk`}><i /></span><b>{topRated ? saddle(topRated.row) === 999 ? "-" : saddle(topRated.row) : "-"}</b><strong>{topRated ? horse(topRated.row) : "Pending"}</strong></div>
 <div className="edgeiq-race-v3-card-pair"><em>EPI Rating <b>{topRated && runnerEpiValue(topRated) !== null ? renderMetricValue(runnerEpiValue(topRated), 1) : "Pending"}</b></em><em>Projected Rating <b>{topRated && projectedRating(topRated) !== null ? renderMetricValue(projectedRating(topRated), 1) : "Pending"}</b></em></div>
 </article>
 <article className="edgeiq-race-v3-card best-value">
 <span>Best Value</span>
 <div className="edgeiq-race-v3-runner-feature"><span className="edgeiq-field-silk" aria-label={`${bestValue ? horse(bestValue.row) : "Runner"} silk`}><i /></span><b>{bestValue ? saddle(bestValue.row) === 999 ? "-" : saddle(bestValue.row) : "-"}</b><strong>{bestValue ? horse(bestValue.row) : "Pending"}</strong></div>
 <div className="edgeiq-race-v3-card-pair"><em>Fair Price <b>{bestValue ? money(fairPrice(bestValue.row, bestValue.bet)) : "Pending Market"}</b></em><em>Edge <b>{bestValue ? pct(edgePct(bestValue.row, bestValue.bet)) : "Pending"}</b></em></div>
 </article>
 <article className="edgeiq-race-v3-card">
 <span>Track Condition</span>
 <em>Official</em><strong>{headerCondition}</strong>
 <em>EDGEiQ True Track Rating</em><b>{trueTrackRating}</b>
 <small>Track playing {trackPlaying !== "Pending" ? trackPlaying : trackLengths}</small>
 </article>
 <article className="edgeiq-race-v3-card">
 <span>Race Shape</span>
 <em>Pressure</em><strong>{racePacePressure}</strong>
 <em>Race Shape</em><b>{raceShapeText}</b>
 <small>On-speed: {raceMapAdvantage} | Backmarkers: {raceKeyRisk || "Pending"}</small>
 </article>
 </div>
 <div className="edgeiq-race-v3-mid-grid">
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-matters">
 <strong>What Matters Today</strong>
 {whatMatters.map((item, index) => <p key={`race-v3-matter-${index}`}><i />{item}</p>)}
 </section>
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-speed">
 <strong>Speed Map Preview</strong>
 <div className="edgeiq-race-v3-speed-map">
 <div className="edgeiq-race-v3-lanes">{["Lead","On Speed","Midfield","Back","Widest Back"].map((lane) => <span key={`race-v3-lane-${lane}`}>{lane}</span>)}</div>
 {raceMiniMapRows.map((item) => {
 const role = paceMapRole(item);
 const rolePosition: Record<string, number> = { LEADER: 12, "ON PACE": 31, MIDFIELD: 50, BACKMARKER: 70 };
 const runnerBarrier = Number(barrier(item.row) || 1);
 const runnerNo = firstText(item.row, ["runner_number", "saddlecloth", "number", "tab_number", "runner_no", "horse_number"], "-");
 const laneX = role === "BACKMARKER" && runnerBarrier >= Math.max(8, raceFieldSize - 1) ? 89 : rolePosition[role] || 50;
 return <button type="button" key={`race-v3-mini-map-${runnerRowKey(item.row)}`} style={{ left: `${laneX}%`, top: `${22 + ((runnerBarrier + Number(runnerNo || 0)) % 4) * 18}%` }} onClick={() => { setSelectedKey(runnerRowKey(item.row)); setIntelMode("FORM"); }}>{runnerNo}</button>;
 })}
 </div>
 <footer><span>Expected Leader: {expectedLeader ? `${saddle(expectedLeader.row) === 999 ? "-" : saddle(expectedLeader.row)}. ${horse(expectedLeader.row)}` : "Pending"}</span><span>Expected Tempo: <b>{racePacePressure}</b></span></footer>
 </section>
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-market">
 <strong>Quick Market Snapshot</strong>
 <div><span>Favourite</span><em>{favourite ? `${saddle(favourite.row)}. ${horse(favourite.row)}` : "Pending Market"}</em><b>{favourite ? marketMoney(livePrice(favourite.row, favourite.bet)) : "Pending Market"}</b></div>
 <div><span>2nd Fav</span><em>{secondFavourite ? `${saddle(secondFavourite.row)}. ${horse(secondFavourite.row)}` : "Pending Market"}</em><b>{secondFavourite ? marketMoney(livePrice(secondFavourite.row, secondFavourite.bet)) : "Pending Market"}</b></div>
 <div><span>Best Value</span><em>{bestValue ? `${saddle(bestValue.row)}. ${horse(bestValue.row)}` : "Pending"}</em><b>{bestValue ? money(fairPrice(bestValue.row, bestValue.bet)) : "Pending Market"}</b></div>
 <div><span>Market Confidence</span><em>{bettingConfidence !== "-" ? bettingConfidence : "Pending"}</em><b>{priceTimestamp || "Pending Market"}</b></div>
 </section>
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-stats">
 <strong>Key Stats At A Glance</strong>
 {[["Race Rating", raceStandardValue === null ? "Pending" : renderMetricValue(raceStandardValue, 1)], ["Average Field Rating", averageRating === null ? "Pending" : renderMetricValue(averageRating, 1)], ["Race Quality", raceQualityText], ["Tempo Pressure", racePacePressure], ["Field Depth", raceStrengthText], ["Sectional Quality", sectionalWeaponValue(topRated) === null ? "Pending" : "High"]].map(([label, value]) => <div key={`race-v3-stat-${label}`}><span>{label}</span><em>{value}</em></div>)}
 </section>
 </div>
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-rankings">
 <strong>Top 3 Rankings</strong>
 <div className="edgeiq-race-v3-rank-row head" role="row">{["NO","SILK","RUNNER","BARRIER","JOCKEY","TRAINER","EPI","PROJECTED","FAIR PRICE","EDGE","LIVE","FLUC"].map((label) => <span key={`race-v3-rank-head-${label}`}>{label}</span>)}</div>
 {raceTopThreeRows.map((item) => {
 const fluc = flucFor(item);
 return <button type="button" className="edgeiq-race-v3-rank-row" role="row" key={`race-v3-rank-${runnerRowKey(item.row)}`} onClick={() => { setSelectedKey(runnerRowKey(item.row)); setIntelMode("FORM"); }}>
 <span>{saddle(item.row) === 999 ? "-" : saddle(item.row)}</span>
 <span className="edgeiq-field-silk" aria-label={`${horse(item.row)} silk`}><i /></span>
 <strong>{horse(item.row)}</strong>
 <span>{barrier(item.row)}</span>
 <span>{firstText(item.row, ["jockey", "jockey_name", "rider"], "-")}</span>
 <span>{firstText(item.row, ["trainer", "trainer_name"], "-")}</span>
 <span>{runnerEpiValue(item) === null ? "Pending" : renderMetricValue(runnerEpiValue(item), 1)}</span>
 <span>{projectedRating(item) === null ? "Pending" : renderMetricValue(projectedRating(item), 1)}</span>
 <span>{money(fairPrice(item.row, item.bet))}</span>
 <span className={(edgePct(item.row, item.bet) ?? 0) > 0 ? "positive" : ""}>{edgePct(item.row, item.bet) === null ? "Pending" : pct(edgePct(item.row, item.bet))}</span>
 <span>{marketMoney(livePrice(item.row, item.bet))}</span>
 <span>{fluc === null ? "Pending Market" : pct(fluc)}</span>
 </button>;
 })}
 <button type="button" className="edgeiq-race-v3-field-link" onClick={() => setIntelMode("RUNNERS")}>View Full Field</button>
 </section>
 <footer className="edgeiq-race-v3-foot">EDGEiQ Race Intelligence <span>|</span> Data is modelled and subject to change</footer>
 </section>
 );
 })() : null}
 {intelMode === "MP" ? (() => {
 const mapSourceRow = (item: EnrichedRunner): Row => ({ ...(item.row || {}), ...(item.mapEnrichment || {}) });
 const mapClean = (value: unknown, fallback = "-") => {
 const raw = String(value ?? "").trim();
 if (!raw || /^(UNKNOWN|NOT LOADED|SOURCE_MISSING|SOURCE GAP|NULL|NN|UNDEFINED|0\.0)$/i.test(raw)) return fallback;
 return raw;
 };
 const mapRowsV2 = [...activeRaceRows].map((item) => {
 const src = mapSourceRow(item);
 const x = firstNum(src, ["map_x_pct_display_v3", "map_x_pct_display", "map_x_pct"]);
 const y = firstNum(src, ["map_y_px_display_v3", "map_y_px_display", "map_y_px"]);
 return {
 item,
 key: runnerRowKey(item.row),
 horseName: horse(item.row),
 shortName: shortHorseName(horse(item.row), 13),
 saddle: mapClean(firstText(item.row, ["saddlecloth", "horse_no", "runner_no", "runner_number", "number"], saddle(item.row) === 999 ? "" : String(saddle(item.row)))),
 barrier: mapClean(firstText(item.row, ["barrier", "draw"], barrier(item.row))),
 runStyle: mapClean(firstText(src, ["run_style_display_v3", "run_style_display", "run_style", "speed_map_bucket"], "")),
 earlySpeed: mapClean(firstText(src, ["early_speed_rating_display", "projected_speed_display", "early_speed", "projected_speed"], "")),
 paceFit: mapClean(firstText(src, ["pace_fit_display", "pace_fit_band", "pace_fit"], "")),
 settling: mapClean(firstText(src, ["settling_band_display_v3", "settling_band_display", "settling_band", "settling_position"], "")),
 wideRisk: mapClean(firstText(src, ["wide_risk_display", "wide_risk"], "")),
 coverRisk: mapClean(firstText(src, ["cover_risk_display", "cover_risk"], "")),
 pressureRole: mapClean(firstText(src, ["pressure_role_display", "pressure_role"], "")),
 lateSpeed: mapClean(firstText(src, ["late_speed_display", "late_speed"], "")),
 confidence: mapClean(firstText(src, ["map_confidence_display_v3", "map_confidence_display", "map_confidence"], "")),
 speedRank: mapClean(firstText(src, ["speed_rank_v3"], "")),
 speedGap: mapClean(firstText(src, ["speed_gap_to_leader_v3"], "")),
 relativeBand: mapClean(firstText(src, ["relative_speed_band_v3"], "")),
 evidence: mapClean(firstText(src, ["map_evidence_display", "map_evidence"], "")),
 lane: mapClean(firstText(src, ["map_lane_display", "map_lane"], "")),
 zone: mapClean(firstText(src, ["map_zone_display", "map_zone"], "")),
 jockeyName: firstText(item.row, ["jockey", "jockey_name", "rider"], "-"),
 trainerName: firstText(item.row, ["trainer", "trainer_name"], "-"),
 weight: firstText(item.row, ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg", "wgt"], "-"),
 epiSpd: renderMetricValue(projectedSpdValue(item), 1),
 x: x !== null ? clamp(x, 4, 96) : 74,
 y: y !== null ? clamp(y, 8, 94) : 50,
 selected: !!selected && runnerRowKey(item.row) === runnerRowKey(selected.row),
 };
 }).sort((a, b) => a.x - b.x || Number(a.barrier || 99) - Number(b.barrier || 99));
 const mapTableRowsV2 = [...mapRowsV2].sort((a, b) => Number(a.saddle || 999) - Number(b.saddle || 999));
 const mapLaneRowsV1 = [...mapRowsV2].sort((a, b) => {
 const barrier = Number(a.barrier);
 const barrierB = Number(b.barrier);
 const valid = Number.isFinite(barrier) && barrier > 0;
 const validB = Number.isFinite(barrierB) && barrierB > 0;
 if (valid && validB) return barrierB - barrier;
 if (valid) return -1;
 if (validB) return 1;
 return a.x - b.x;
 });
 const mapBarrierMax = Math.max(...mapLaneRowsV1.map((row) => Number(row.barrier)).filter((value) => Number.isFinite(value) && value > 0), activeRaceRows.length, 1);
 const mapBarrierLaneRows = Array.from({ length: mapBarrierMax }, (_, index) => {
 const barrierNo = mapBarrierMax - index;
 return {
 barrierNo,
 runners: mapRowsV2
 .filter((row) => Number(row.barrier) === barrierNo)
 .sort((a, b) => a.x - b.x || Number(a.saddle || 99) - Number(b.saddle || 99)),
 };
 });
 return (
 <section className="edgeiq-map-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-map-final-lock">
 <section className="edgeiq-map-final-visual" aria-label="Speed map and barrier stack">
 <div className="edgeiq-map-final-track">
 {mapBarrierLaneRows.map((lane) => (
 <div key={`map-final-lane-${lane.barrierNo}`} className={`edgeiq-map-final-lane ${lane.runners.some((row) => row.selected) ? "is-selected" : ""}`}>
 {lane.runners.map((row, runnerIndex) => {
 const xPct = clamp(row.x, 7, 76);
 const stackOffset = runnerIndex * 16;
 return (
 <button
 key={`map-final-runner-${row.key}`}
 type="button"
 className="edgeiq-map-final-runner"
 onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }}
 title={`${row.horseName} | B${lane.barrierNo}`}
 style={{ ["--map-runner-x" as string]: `${xPct}%`, ["--map-runner-offset" as string]: `${stackOffset}px` }}
 >
 <span className="edgeiq-map-final-speed-line" />
 <span className="edgeiq-map-final-pill">
 <b>{row.saddle}</b>
 <strong>{row.shortName}</strong>
 </span>
 </button>
 );
 })}
 </div>
 ))}
 </div>
 <div className="edgeiq-map-final-axis" aria-hidden="true">
 {Array.from({ length: mapBarrierMax }, (_, index) => mapBarrierMax - index).map((barrierNo) => <span key={`map-final-axis-${barrierNo}`}>B{barrierNo}</span>)}
 </div>
 <div className="edgeiq-map-final-direction">ÃƒÂ¢Ã¢â‚¬Â Ã‚Â DIRECTION OF RACE</div>
 </section>

 <section className="edgeiq-map-final-table edgeiq-product-v4-table">
 <div className="edgeiq-map-runner-table-head">
 {['NO','SILK','RUNNER','BARRIER','JOCKEY','TRAINER','WEIGHT','EPI SPD'].map((label) => <span key={`map-v3-table-head-${label}`}>{label}</span>)}
</div>
{mapTableRowsV2.map((row) => (
 <button className="edgeiq-map-runner-table-row" key={`map-v3-table-${row.key}`} type="button" onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }}>
<strong>{row.saddle}</strong>
 <span className="edgeiq-field-silk" aria-label={`${row.horseName} silk`}><i /></span>
<strong>{row.horseName}</strong>
<span>{row.barrier}</span>
<span>{row.jockeyName}</span>
<span>{row.trainerName}</span>
<span>{row.weight}</span>
<span>{row.epiSpd}</span>
</button>
 ))}
 </section>
 </section>
 );
 })() : null}
{intelMode === "FORM" ? (() => {
 const formSelectorRows = [...activeRaceRows].sort((a, b) => saddle(a.row) - saddle(b.row));
 const toggleFormDossier = (item: EnrichedRunner) => {
 const key = runnerRowKey(item.row);
 setSelectedKey((current) => current === key ? "" : key);
 };
 const formSelector = (
 <div className="edgeiq-form-runner-selector" aria-label="Runner form selector">
 {formSelectorRows.map((item) => {
 const key = runnerRowKey(item.row);
 const active = selectedKey === key;
 return (
 <button key={`form-selector-${key}`} type="button" className={active ? "is-active" : ""} onClick={() => toggleFormDossier(item)}>
 <span>{saddle(item.row) === 999 ? "-" : saddle(item.row)}</span>
 <span className="edgeiq-field-silk" aria-label={`${horse(item.row)} silk`}><i /></span>
 <strong>{horse(item.row)}</strong>
 </button>
 );
 })}
 </div>
 );
 if (!selectedKey || !selected) return <section className="edgeiq-form-showcase edgeiq-product-section edgeiq-product-v4-panel edgeiq-form-dossier-match edgeiq-form-selector-only"><div className="edgeiq-form-selector-state"><span>FORM</span><strong>Select Runner</strong><em>Open one runner dossier at a time.</em>{formSelector}</div></section>;
 const formRows = selectedFormRunCards.slice(0, 5);
 const projected = selectedTodayProjectionFigure;
 const formNarrative = selectedFormNarrative ? selectedFormNarrative.split(/(?<=[.!?])\s+/).slice(0, 1).join(" ") : "";
 const fieldLimit = Math.max(activeRaceRows.length, 1);
 const cleanRunText = (value: unknown) => {
 const raw = String(value ?? "").trim();
 if (!raw || /^(UNKNOWN|NOT LOADED|SOURCE GAP|SOURCE_MISSING|NULL|N\/A|NA|UNDEFINED|0\.0)$/i.test(raw)) return "-";
 return raw;
 };
 const cleanPosition = (value: unknown) => {
 const raw = cleanRunText(value);
 const numeric = Number(String(raw).replace(/[^0-9.-]/g, ""));
 if (Number.isFinite(numeric) && (numeric > fieldLimit || numeric > 30 || numeric <= 0)) return "-";
 return raw;
 };
 const posClass = (value: string) => {
 const numeric = Number(String(value).replace(/[^0-9.-]/g, ""));
 if (!Number.isFinite(numeric)) return "";
 if (numeric === 1) return "pos-good";
 if (numeric >= 7) return "pos-bad";
 return "";
 };
 const trajectoryValues = Array.from({ length: 5 }, (_, index) => {
 const run = formRows[4 - index];
 return { label: `L${5 - index}`, value: run ? run.rating : null };
 });
 const formHeatClass = (value: number | null) => {
 if (value === null) return "epi-heat-cell epi-heat-missing";
 const scoreBand = value >= 80 ? "epi-heat-elite" : value >= 70 ? "epi-heat-strong" : value >= 60 ? "epi-heat-positive" : value >= 50 ? "epi-heat-neutral" : value >= 40 ? "epi-heat-risk" : "epi-heat-poor";
 return `epi-heat-cell ${scoreBand}`;
 };
 const historyRowsForProfile = selected.runnerHistory || [];
 const profileRowsFor = (title: string, getter: (row: Row) => string) => {
 const buckets = new Map<string, { starts: number; wins: number; places: number; ratingTotal: number; ratingCount: number }>();
 historyRowsForProfile.forEach((run) => {
 const key = cleanRunText(getter(run));
 if (key === "-") return;
 const finish = Number(String(historyFinishText(run)).replace(/[^0-9.-]/g, ""));
 const rating = historyRatingValue(run);
 const bucket = buckets.get(key) || { starts: 0, wins: 0, places: 0, ratingTotal: 0, ratingCount: 0 };
 bucket.starts += 1;
 if (Number.isFinite(finish) && finish === 1) bucket.wins += 1;
 if (Number.isFinite(finish) && finish > 0 && finish <= 3) bucket.places += 1;
 if (rating !== null) {
 bucket.ratingTotal += rating;
 bucket.ratingCount += 1;
 }
 buckets.set(key, bucket);
 });
 return { title, rows: Array.from(buckets.entries()).sort((a, b) => b[1].starts - a[1].starts).slice(0, 4) };
 };
 const profileGroups = [
 profileRowsFor("Distance", historyDistanceText),
 profileRowsFor("Going", historyGoingText),
 profileRowsFor("Class", historyClassText),
 ];
 const career = selected.runnerCareer || {};
 const careerStarts = firstNum(career, ["career_starts", "starts"]) ?? historyRowsForProfile.length;
 const careerWins = firstNum(career, ["career_wins", "wins"]) ?? historyRowsForProfile.filter((run) => Number(String(historyFinishText(run)).replace(/[^0-9.-]/g, "")) === 1).length;
 const careerPlaces = firstNum(career, ["career_places", "places"]) ?? historyRowsForProfile.filter((run) => { const pos = Number(String(historyFinishText(run)).replace(/[^0-9.-]/g, "")); return Number.isFinite(pos) && pos > 0 && pos <= 3; }).length;
 const careerWinPct = careerStarts ? (careerWins / careerStarts) * 100 : null;
 const careerPlacePct = careerStarts ? (careerPlaces / careerStarts) * 100 : null;
 const selectedRunnerToken = cleanHorse(firstText(selected.row, ["normalized_runner", "runner", "runner_name", "horse"], horse(selected.row)));
 const dateToken = (value: unknown) => {
 const raw = cleanRunText(value);
 const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
 if (iso) return `${iso[1]}${iso[2]}${iso[3]}`;
 const compact = raw.match(/^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{2,4})$/);
 if (compact) {
 const months: Record<string, string> = { JAN: "01", FEB: "02", MAR: "03", APR: "04", MAY: "05", JUN: "06", JUL: "07", AUG: "08", SEP: "09", SEPT: "09", OCT: "10", NOV: "11", DEC: "12" };
 const year = compact[3].length === 2 ? `20${compact[3]}` : compact[3];
 return `${year}${months[compact[2].slice(0, 3).toUpperCase()] || "00"}${compact[1].padStart(2, "0")}`;
 }
 return raw.replace(/[^0-9A-Z]/gi, "").toUpperCase();
 };
 const gearRowsForRunner = gearProfileRows
 .filter((row) => cleanHorse(firstText(row, ["normalized_runner", "runner"], "")) === selectedRunnerToken)
 .sort((a, b) => dateToken(b.race_date).localeCompare(dateToken(a.race_date)));
 const sectionalRowsForRunner = formSectionalProfileRows
 .filter((row) => cleanHorse(firstText(row, ["normalized_runner", "runner"], "")) === selectedRunnerToken && firstText(row, ["benchmark_mode"], "") === formBenchmarkMode)
 .sort((a, b) => dateToken(b.race_date).localeCompare(dateToken(a.race_date)));
 const matchHistoricalFeedRow = (rows: Row[], run: (typeof formRows)[number]) => {
 const runDate = dateToken(run.date);
 const runTrack = cleanTrack(run.track);
 return rows.find((row) => dateToken(row.race_date) === runDate && (!runTrack || cleanTrack(row.track) === runTrack)) || null;
 };
 const gearForRun = (run: (typeof formRows)[number]) => matchHistoricalFeedRow(gearRowsForRunner, run);
 const currentGearRow = gearRowsForRunner[0] || null;
 const currentGear = cleanRunText(firstText(currentGearRow || undefined, ["gear_current"], ""));
 const currentGearChange = cleanRunText(firstText(currentGearRow || undefined, ["gear_changes", "gear_added", "gear_removed"], ""));
 const sectionalForRun = (run: (typeof formRows)[number]) => matchHistoricalFeedRow(sectionalRowsForRunner, run);
 const leadingSectionalRow = formRows.map((run) => sectionalForRun(run)).find((row): row is Row => !!row) || sectionalRowsForRunner[0] || null;
 const splitLabels = text(leadingSectionalRow?.split_labels).split(";").filter(Boolean);
 const splitLengths = text(leadingSectionalRow?.split_lengths).split(";").map((value) => num(value));
 const splitPairs = splitLabels.map((label, index) => ({ label, value: splitLengths[index] ?? null })).filter((entry) => entry.label);
 return <section className="edgeiq-form-showcase edgeiq-product-section edgeiq-product-v4-panel edgeiq-form-showcase-v2 edgeiq-form-clean-v3 edgeiq-form-study-v2 edgeiq-form-profile-v4 edgeiq-form-dossier-match">{formSelector}<div className="edgeiq-form-study-header edgeiq-form-profile-header"><span className="edgeiq-field-silk edgeiq-form-profile-silk" aria-label={`${horse(selected.row)} silk`}><i /></span><div><span>FORM</span><strong>{saddle(selected.row) === 999 ? "-" : saddle(selected.row)} {horse(selected.row)}</strong><em>{firstText(selected.row, ["jockey", "jockey_name", "rider"], "-")} / {firstText(selected.row, ["trainer", "trainer_name"], "-")}</em></div><div className="edgeiq-form-study-inline-metrics">{[["Current EPI", projected], ["Peak", selectedBestRatingLast5Value], ["Average", selectedAVGRatingLast5Value]].map(([label, value]) => <span key={`form-study-inline-${label}`}><b>{label}</b><strong>{typeof value === "number" ? renderMetricValue(value, 1) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</strong></span>)}</div></div><div className="edgeiq-form-gear-bar"><span><b>Current Gear</b><strong>{currentGear === "-" ? "No gear listed" : currentGear}</strong></span><span><b>Gear Change</b><strong>{currentGearChange === "-" ? "No recorded change" : currentGearChange}</strong></span></div><section className="edgeiq-form-sectional-strip-panel"><div className="edgeiq-form-sectional-strip-head"><div><span>EDGEiQ Standardised Sectionals</span><strong>{formBenchmarkMode === "CLASS_BENCHMARK" ? "Class benchmark" : "All-classes benchmark"}</strong></div><div className="edgeiq-form-benchmark-toggle">{(["CLASS_BENCHMARK", "ALL_CLASSES_BENCHMARK"] as BenchmarkMode[]).map((mode) => <button type="button" key={`form-benchmark-${mode}`} className={formBenchmarkMode === mode ? "is-active" : ""} onClick={() => setFormBenchmarkMode(mode)}>{mode === "CLASS_BENCHMARK" ? "Class" : "All-classes"}</button>)}</div></div>{splitPairs.length ? <div className="edgeiq-form-sectional-strip">{splitPairs.map((entry) => <span key={`form-split-${entry.label}`} className={entry.value === null ? "is-missing" : entry.value < 0 ? "is-fast" : "is-neutral"}><b>{entry.label}</b><strong>{entry.value === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : `${signed(entry.value, 1)}L`}</strong></span>)}</div> : <div className="edgeiq-form-sectional-empty">No benchmark-backed sectional splits available for this runner.</div>}</section><section className="edgeiq-form-last-five edgeiq-form-last-five-wide"><div className="edgeiq-form-table-title">Last Five Starts</div><div className="edgeiq-form-table edgeiq-product-v4-table"><div className="edgeiq-form-table-row head">{['Date','Track','Dist','Class','Going','Bar','Jockey','Gear','Pos','Margin','SP','Rating'].map((label) => <span key={`form-main-head-${label}`}>{label}</span>)}</div>{!formRows.length ? <div className="edgeiq-form-table-empty">No detailed performance-history lines available.</div> : formRows.map((run) => { const pos = cleanPosition(run.finishingPosition); const runGear = gearForRun(run); const gearText = cleanRunText(firstText(runGear || undefined, ["gear_changes", "gear_current", "gear_added", "gear_removed"], "")); return <div key={`form-main-row-${run.key}`} className="edgeiq-form-table-row edgeiq-form-profile-row edgeiq-form-table-row-gear"><span>{cleanRunText(run.date)}</span><span>{cleanRunText(run.track)}</span><span>{cleanRunText(run.distance)}</span><span>{cleanRunText(run.raceClass)}</span><span>{cleanRunText(run.going)}</span><span>{cleanRunText(run.barrier)}</span><span>{cleanRunText(run.jockey)}</span><span>{gearText}</span><span className={posClass(pos)}>{pos}</span><span>{cleanRunText(run.beatenMargin)}</span><span>{cleanRunText(run.sp)}</span><span>{run.rating !== null ? renderMetricValue(run.rating, 1) : "-"}</span></div>; })}</div></section><div className="edgeiq-form-trajectory-strip" aria-label="Rating progression">{trajectoryValues.map((entry) => <span key={`form-trajectory-${entry.label}`} className={formHeatClass(entry.value)}><b>{entry.label}</b><strong>{entry.value === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : renderMetricValue(entry.value, 1)}</strong></span>)}</div><div className="edgeiq-form-profile-grid">{profileGroups.map((group) => <section key={`form-profile-${group.title}`} className="edgeiq-form-profile-panel"><strong>{group.title} Profile</strong><div className="edgeiq-form-profile-table edgeiq-product-v4-table"><div className="edgeiq-form-profile-table-row head"><span>{group.title}</span><span>Starts</span><span>Wins</span><span>Places</span><span>Rating</span></div>{group.rows.length ? group.rows.map(([label, bucket]) => <div className="edgeiq-form-profile-table-row" key={`profile-${group.title}-${label}`}><span>{label}</span><span>{bucket.starts}</span><span>{bucket.wins}</span><span>{bucket.places}</span><span>{bucket.ratingCount ? renderMetricValue(bucket.ratingTotal / bucket.ratingCount, 1) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</span></div>) : <div className="edgeiq-form-profile-empty">Profile not loaded</div>}</div></section>)}</div><section className="edgeiq-form-career-summary"><strong>Career Summary</strong><div>{[["Starts", careerStarts], ["Wins", careerWins], ["Places", careerPlaces], ["Win %", careerWinPct], ["Place %", careerPlacePct]].map(([label, value]) => <article key={`form-career-${label}`}><span>{label}</span><b>{typeof value === "number" ? (String(label).includes("%") ? `${value.toFixed(1)}%` : String(Math.trunc(value))) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</b></article>)}<button type="button" className="edgeiq-field-history-link" onClick={() => setFullHistoryRunner(selected)}>Full history</button></div></section>{formNarrative ? <p className="edgeiq-form-short-read">{formNarrative}</p> : null}</section>;
 })() : null}
 {intelMode === "RUNNERS" ? (() => {
 const fieldRows = [...activeRaceRows].sort((a, b) => saddle(a.row) - saddle(b.row));
 const cleanMarket = (item: EnrichedRunner) => {
 return marketMoney(livePrice(item.row, item.bet));
 };
 const cleanWeight = (row: Row) => firstText(row, ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg", "wgt"], "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â");
 const runnerEpiValue = (item: EnrichedRunner) => firstNum(item.ratingsHeatmap, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(item);
 const openRunnerForm = (item: EnrichedRunner) => {
 setSelectedKey(runnerRowKey(item.row));
 setIntelMode("FORM");
 };
 return (
 <section className="edgeiq-field-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-field-lock-v1">
 <div className="edgeiq-field-guide-table edgeiq-product-v4-table" role="table" aria-label="EDGEiQ Race Field">
 <div className="edgeiq-field-guide-row head" role="row">{['NO','SILK','RUNNER','BAR','WGT','JOCKEY','TRAINER','EDGEiQ','MARKET','STATUS'].map((label) => <span key={`field-head-${label}`}>{label}</span>)}</div>
 {fieldRows.map((item) => {
 const row = item.row;
 const rowKey = runnerRowKey(row);
 const epi = runnerEpiValue(item);
 const status = isScratched(item) ? "SCRATCHED" : "ACTIVE";
 return <button key={`field-row-wrap-${rowKey}`} type="button" className={`edgeiq-field-guide-row ${isScratched(item) ? "is-scratched" : ""}`} onClick={() => openRunnerForm(item)} role="row" aria-label={`Open ${horse(row)} form profile`}><span>{saddle(row) === 999 ? "-" : saddle(row)}</span><span className="edgeiq-field-silk" aria-label={`${horse(row)} silk`}><i /></span><strong>{horse(row)}</strong><span>{barrier(row)}</span><span>{cleanWeight(row)}</span><span>{firstText(row, ["jockey", "jockey_name", "rider"], "-")}</span><span>{firstText(row, ["trainer", "trainer_name"], "-")}</span><span>{epi === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : renderMetricValue(epi, 1)}</span><span>{cleanMarket(item)}</span><span className="edgeiq-field-status-text">{status}</span></button>;
 })}
 </div>
 </section>
 );
 })() : null}
 {intelMode === "PERFORMANCE" ? (() => {
 const heatRows = activeRaceRows.map((item) => ({ item, heat: item.ratingsHeatmap || {} }));
 const heatRowsWithRatings = heatRows.filter((entry) => (firstNum(entry.heat, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(entry.item)) !== null);
 const expectedRaceRating = heatRows.map((entry) => firstNum(entry.heat, ["expected_rating"])).find((value) => value !== null) ?? null;
 const currentFigureFor = (item: EnrichedRunner, heat: Row) => firstNum(heat, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(item);
 const runnerPerformance = heatRows.map((entry) => currentFigureFor(entry.item, entry.heat)).filter((value): value is number => value !== null).sort((a, b) => a - b);
 const averageFigure = runnerPerformance.length ? runnerPerformance.reduce((sum, value) => sum + value, 0) / runnerPerformance.length : null;
 const performanceSpread = runnerPerformance.length ? Math.max(...runnerPerformance) - Math.min(...runnerPerformance) : null;
 const topFigureEntry = heatRows.reduce<{ item: EnrichedRunner; value: number } | null>((best, entry) => {
 const value = currentFigureFor(entry.item, entry.heat);
 if (value === null) return best;
 if (!best || value > best.value) return { item: entry.item, value };
 return best;
 }, null);
 const epiHeatClass = (value: number | null) => {
 if (value === null) return "edgeiq-epi-cell is-missing";
 if (value >= 105) return "edgeiq-epi-cell is-elite";
 if (value >= 100) return "edgeiq-epi-cell is-strong";
 if (value >= 95) return "edgeiq-epi-cell is-positive";
 if (value >= 90) return "edgeiq-epi-cell is-warning";
 return "edgeiq-epi-cell is-risk";
 };
 const staticFigureText = (value: number | null) => value === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : renderMetricValue(value, 1);
 const historyResultAvailable = (run: Row | undefined) => !!run && historyFinishText(run) !== "-";
 const buildPerformanceRunCard = (runnerName: string, label: string, run: Row | undefined, figure: number | null): Omit<RatingHoverCard, "x" | "y"> | null => {
 if (!run) return null;
 return {
 title: `${runnerName} ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â ${label} Figure: ${staticFigureText(figure)}`,
 metrics: [
 { label: "Date", value: formatHistoryDate(historyDateText(run)) },
 { label: "Track", value: historyTrackText(run) },
 { label: "Race", value: historyRaceNoText(run) },
 { label: "Distance", value: historyDistanceText(run) },
 { label: "Class", value: historyClassText(run) },
 { label: "Going", value: historyGoingText(run) },
 { label: "Barrier", value: historyBarrierText(run) },
 { label: "Jockey", value: historyJockeyText(run) },
 { label: "Trainer", value: firstText(run, ["trainer", "trainer_name"], firstText(header, ["trainer", "trainer_name"], "-")) },
 { label: "Position", value: historyFinishText(run) },
 { label: "Margin", value: firstText(run, ["margin", "beaten_margin"], "-") },
 { label: "SP", value: historySpText(run) },
 { label: "EPI Figure", value: staticFigureText(figure), tone: figure !== null && figure >= 100 ? "#43efc6" : "#f4f8f8" },
 ],
 footer: historyResultAvailable(run) ? "Click to open this historical result in RESULTS." : "Result detail unavailable for this historical race.",
 };
 };
 const openHistoricalResult = (item: EnrichedRunner, run: Row | undefined) => {
 if (!historyResultAvailable(run)) return;
 clearRatingHover();
 setSelectedKey(runnerRowKey(item.row));
 setSelectedHistoricalRun(run || null);
 setIntelMode("RESULTS");
 };
 if (!heatRowsWithRatings.length) {
 return <section className="edgeiq-ratings-tab edgeiq-performance-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-performance-rebuild-v2"><div className="edgeiq-performance-panel-head"><strong>PERFORMANCE INDEX TABLE</strong></div><div className="edgeiq-product-empty">Performance Index pending for this race.</div></section>;
 }
 const performanceCards = [
 { label: "Race Standard", value: staticFigureText(expectedRaceRating), detail: "Expected Figure", visual: "spark" },
 { label: "Top Figure", value: staticFigureText(topFigureEntry?.value ?? null), detail: topFigureEntry ? horse(topFigureEntry.item.row) : "Peak EPI in Field", visual: "trophy" },
 { label: "Average Figure", value: staticFigureText(averageFigure), detail: "Average EPI in Field", visual: "bars" },
 { label: "Field Spread", value: staticFigureText(performanceSpread), detail: "EPI Points", visual: "range" },
 ];
 return (
 <section className="edgeiq-ratings-tab edgeiq-performance-tab edgeiq-product-section edgeiq-performance-rebuild-v2">
 <div className="edgeiq-performance-summary-grid">
 {performanceCards.map((card) => <article key={`performance-card-${card.label}`} className={`edgeiq-performance-summary-card visual-${card.visual}`}><span>{card.label}</span><strong>{card.value}</strong><em>{card.detail}</em><i aria-hidden="true" /></article>)}
 </div>
 <div className="edgeiq-performance-index-panel edgeiq-product-v4-panel">
 <div className="edgeiq-performance-panel-head"><strong>PERFORMANCE INDEX TABLE</strong></div>
 <div className="edgeiq-performance-index-table edgeiq-product-v4-table" role="table" aria-label="EDGEiQ Performance Index">
 <div className="edgeiq-performance-index-row head" role="row">{['NO','SILK','HORSE','EPI','CURRENT','PEAK','AVG','LAST','L5','L4','L3','L2','L1'].map((label) => <span key={`performance-v2-head-${label}`}>{label}</span>)}</div>
 {heatRows.map(({ item, heat }) => {
 const current = currentFigureFor(item, heat);
 const rated = ratedHistoryRows(item.runnerHistory || []);
 const recent = rated.slice(0, 5);
 const l5ToL1Runs = Array.from({ length: 5 }, (_, index) => recent[4 - index]);
 const peak = rated.length ? Math.max(...rated.map((run) => historyRatingValue(run) ?? Number.NEGATIVE_INFINITY).filter((value) => Number.isFinite(value))) : null;
 const avg = recent.length ? recent.reduce((sum, run) => sum + (historyRatingValue(run) ?? 0), 0) / recent.length : null;
 const last = recent.length ? historyRatingValue(recent[0]) : firstNum(item.runnerForm, ["form_last_start_rating", "last_start_rating", "rating_1"]);
 return <div className="edgeiq-performance-index-row" role="row" key={`performance-tab-${runnerRowKey(item.row)}`}><span>{saddle(item.row) === 999 ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : saddle(item.row)}</span><span className="edgeiq-field-silk" aria-label={`${horse(item.row)} silk`}><i /></span><strong>{horse(item.row)}</strong><span className="edgeiq-performance-epi">{staticFigureText(current)}</span><span>{staticFigureText(current)}</span><span>{staticFigureText(peak)}</span><span>{staticFigureText(avg)}</span><span>{staticFigureText(last)}</span>{l5ToL1Runs.map((run, index) => {
 const label = `L${5 - index}`;
 const rating = historyRatingValue(run);
 const card = buildPerformanceRunCard(horse(item.row), label, run, rating);
 const canOpen = historyResultAvailable(run);
 return <button key={`epi-${label.toLowerCase()}-${runnerRowKey(item.row)}`} type="button" className={epiHeatClass(rating)} disabled={!canOpen} onMouseEnter={(event) => { if (card) placeRatingHoverCard(event, card); }} onMouseMove={(event) => { if (card) placeRatingHoverCard(event, card); }} onMouseLeave={clearRatingHover} onClick={() => openHistoricalResult(item, run)}>{staticFigureText(rating)}</button>;
 })}</div>;
 })}
 </div>
 <div className="edgeiq-performance-table-footer">
 <div className="edgeiq-performance-scale"><span>EPI SCALE</span><i className="is-risk">&lt; 90</i><i className="is-warning">90 - 94</i><i className="is-positive">95 - 99</i><i className="is-strong">100 - 104</i><i className="is-elite">105+</i></div>
 <span>Click or hover a rating for race details</span>
 <button type="button" onClick={() => setIntelMode("PERFORMANCE")}>View full performance report ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢</button>
 </div>
 </div>
 </section>
 );
 })() : null}
 {intelMode === "NEXUS" ? (() => {
 const source: Row = selected?.nexusContextual || selectedConnectionSource || {};
 const trainerName = firstText(source, ["trainer"], selected ? firstText(selected.row, ["trainer", "trainer_name"], "-") : "-");
 const jockeyName = firstText(source, ["jockey"], selected ? firstText(selected.row, ["jockey", "jockey_name", "rider"], "-") : "-");
 const cleanNexusValue = (value: unknown) => { const raw = text(value).trim(); return raw && raw !== "-" ? raw : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"; };
 const cleanNexusPct = (value: unknown) => {
 const raw = text(value);
 const valueNum = num(raw);
 if (valueNum === null) return cleanNexusValue(raw);
 return pct(valueNum);
 };
 const cleanNexusScore = (value: unknown, digits = 1) => {
 const valueNum = num(value);
 return valueNum === null ? cleanNexusValue(value) : valueNum.toFixed(digits);
 };
 const calibratedScore = cleanNexusScore(firstText(source, ["nexus_context_score_calibrated"], ""));
 const calibratedBand = cleanNexusValue(firstText(source, ["nexus_context_band_calibrated"], ""));
 const percentile = cleanNexusPct(firstText(source, ["nexus_context_percentile"], ""));
 const raceRank = cleanNexusValue(firstText(source, ["nexus_context_rank_in_race"], ""));
 const fieldRank = cleanNexusValue(firstText(source, ["nexus_context_field_rank"], ""));
 const rawContext = cleanNexusValue(firstText(source, ["raw_nexus_context_score", "nexus_context_score"], ""));
 const rawBand = cleanNexusValue(firstText(source, ["raw_nexus_context_band", "nexus_context_band"], ""));
 const nexusPanels = [
 { title: "Trainer", name: trainerName, metrics: [["25 win", cleanNexusPct(source.trainer_recent_25_win_pct)], ["50 win", cleanNexusPct(source.trainer_recent_50_win_pct)], ["100 win", cleanNexusPct(source.trainer_recent_100_win_pct)], ["Best context", cleanNexusValue(source.trainer_best_context)]] },
 { title: "Jockey", name: jockeyName, metrics: [["25 win", cleanNexusPct(source.jockey_recent_25_win_pct)], ["50 win", cleanNexusPct(source.jockey_recent_50_win_pct)], ["100 win", cleanNexusPct(source.jockey_recent_100_win_pct)], ["Best context", cleanNexusValue(source.jockey_best_context)]] },
 { title: "Partnership", name: cleanNexusValue(source.partnership_band), metrics: [["Score", cleanNexusScore(source.partnership_score)], ["Starts", cleanNexusValue(source.partnership_starts)], ["Wins", cleanNexusValue(source.partnership_wins)], ["ROI / A/E", `${cleanNexusValue(source.partnership_roi)} / ${cleanNexusValue(source.partnership_ae)}`]] },
 { title: "Style Fit", name: cleanNexusValue(source.style_alignment_band), metrics: [["Score", cleanNexusScore(source.style_alignment_score)], ["Horse style", cleanNexusValue(source.horse_run_style)], ["Trainer style", cleanNexusValue(source.trainer_best_style)], ["Jockey style", cleanNexusValue(source.jockey_best_style)]] },
 ];
 const positives = ["top_positive_1", "top_positive_2", "top_positive_3"].map((key) => cleanNexusValue(source[key])).filter((value) => value !== "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â");
 const risks = ["top_risk_1", "top_risk_2", "top_risk_3"].map((key) => cleanNexusValue(source[key])).filter((value) => value !== "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â");
 const narrative = cleanNexusValue(firstText(source, ["nexus_summary", "connection_narrative"], selectedConnectionNarrative || "")).replace(/\bNexus\b/gi, "EDGEiQ Insight");
 const labModules = ["TRAINERS", "JOCKEYS", "PARTNERSHIPS", "TRACKS", "DISTANCES", "BARRIERS", "RUN STYLES", "FIRST UP", "SECOND UP", "CLASS", "PRICE ENGINE"];
 const activeLabPanel = nexusPanels.find((panel) => panel.title.toUpperCase() === labModule.replace(/S$/, "")) || nexusPanels[0];
 const labHeroSubject = labModule === "PRICE ENGINE" ? "Price Engine Research" : labModule === "JOCKEYS" ? jockeyName : labModule === "PARTNERSHIPS" ? cleanNexusValue(source.partnership_band) : labModule === "RUN STYLES" ? cleanNexusValue(source.horse_run_style) : labModule === "TRACKS" ? track(header) : labModule === "DISTANCES" ? distance(header) : labModule === "CLASS" ? raceClass(header) : trainerName;
 const labRaceNoToken = text(integer(selectedRaceNo) ?? selectedRaceNo);
 const labSelectedDate = text(selectedRaceDate);
 const labPriceMatches = labPriceEngineRows.filter((row) => cleanTrack(row.track) === selectedTrack && text(integer(row.race_no) ?? row.race_no) === labRaceNoToken && (!labSelectedDate || text(row.race_date) === labSelectedDate));
 const fallbackPriceRaceKey = labPriceEngineRows[0] ? `${text(labPriceEngineRows[0].race_date)}|${cleanTrack(labPriceEngineRows[0].track)}|${text(integer(labPriceEngineRows[0].race_no) ?? labPriceEngineRows[0].race_no)}` : "";
 const fallbackPriceRows = fallbackPriceRaceKey ? labPriceEngineRows.filter((row) => `${text(row.race_date)}|${cleanTrack(row.track)}|${text(integer(row.race_no) ?? row.race_no)}` === fallbackPriceRaceKey) : [];
 const labPriceRows = (labPriceMatches.length ? labPriceMatches : fallbackPriceRows).slice(0, 16);
 const labPriceKey = (row: Row) => `${text(row.race_date)}|${cleanTrack(row.track)}|${text(integer(row.race_no) ?? row.race_no)}|${cleanHorse(row.runner)}`;
 const labPriceRawRows = labPriceRows.map((row) => {
 const key = labPriceKey(row);
 const adjustment = priceEngineAdjustments[key] ?? 0;
 const baseRating = firstNum(row, ["base_rating", "editable_rating"]);
 const baseProbability = firstNum(row, ["base_probability"]) ?? 0;
 const pointToLengths = firstNum(row, ["rating_point_to_lengths"]) ?? 0.1382;
 const rawProbability = Math.max(0.0001, baseProbability * Math.exp((adjustment * pointToLengths) / 2));
 return { row, key, adjustment, baseRating, adjustedRating: baseRating === null ? null : baseRating + adjustment, baseProbability, rawProbability };
 });
 const labPriceTotal = labPriceRawRows.reduce((sum, entry) => sum + entry.rawProbability, 0);
 const labPriceDisplayRows = labPriceRawRows.map((entry) => {
 const adjustedProbability = labPriceTotal > 0 ? entry.rawProbability / labPriceTotal : 0;
 return { ...entry, adjustedProbability, adjustedPrice: adjustedProbability > 0 ? 1 / adjustedProbability : null };
 });
 const labPriceAverageConfidence = labPriceDisplayRows.length ? labPriceDisplayRows.reduce((sum, entry) => sum + (firstNum(entry.row, ["data_confidence"]) ?? 0), 0) / labPriceDisplayRows.length : null;
 return <section className="edgeiq-connections-tab edgeiq-lab-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-lab-v1-lock"><div className="edgeiq-tab-heading edgeiq-product-v4-section-title"><span>LAB</span><strong>Racing Research Laboratory</strong><em>Research, profile, compare and discover.</em></div><div className="edgeiq-lab-v1-layout"><aside className="edgeiq-lab-v1-modules"><strong>Research Modules</strong>{labModules.map((module) => <button type="button" className={labModule === module ? "is-active" : ""} key={`lab-module-${module}`} onClick={() => setLabModule(module)}>{module}</button>)}</aside><section className="edgeiq-lab-v1-main"><div className="edgeiq-lab-v1-subject edgeiq-lab-v1-hero"><span>{labModule}</span><strong>{labHeroSubject}</strong><em>{track(header)} / {distance(header)} / {raceClass(header)}</em></div>{labModule === "PRICE ENGINE" ? <><div className="edgeiq-lab-price-research-banner"><span>Research only</span><strong>Editable rating points do not alter production prices.</strong><em>{labPriceMatches.length ? "Current race feed" : "Fallback research race feed"} / Confidence {labPriceAverageConfidence === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : pct(labPriceAverageConfidence * 100)}</em></div><div className="edgeiq-lab-price-table edgeiq-product-v4-table" role="table" aria-label="Price Engine research table"><div className="edgeiq-lab-price-row head" role="row">{['Runner','Base','Adj Pts','Adj Rating','Base Prob','Adj Prob','Base Price','Adj Price','Status'].map((label) => <span key={`lab-price-head-${label}`}>{label}</span>)}</div>{labPriceDisplayRows.length ? labPriceDisplayRows.map((entry) => <div className="edgeiq-lab-price-row" role="row" key={`lab-price-row-${entry.key}`}><strong>{firstText(entry.row, ["runner"], "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â")}</strong><span>{entry.baseRating === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : renderMetricValue(entry.baseRating, 2)}</span><input aria-label={`Adjust rating points for ${firstText(entry.row, ["runner"], "runner")}`} type="number" step="0.5" value={entry.adjustment} onChange={(event) => { const next = Number(event.currentTarget.value); setPriceEngineAdjustments((current) => ({ ...current, [entry.key]: Number.isFinite(next) ? next : 0 })); }} /><span>{entry.adjustedRating === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : renderMetricValue(entry.adjustedRating, 2)}</span><span>{pct(entry.baseProbability * 100)}</span><span>{pct(entry.adjustedProbability * 100)}</span><span>{money(firstNum(entry.row, ["base_price"]))}</span><span>{money(entry.adjustedPrice)}</span><span>{firstText(entry.row, ["pricing_status"], "RESEARCH_ONLY")}</span></div>) : <div className="edgeiq-lab-price-empty">Price Engine research feed is not loaded for this race.</div>}</div></> : <><div className="edgeiq-lab-v1-metrics">{(activeLabPanel ? [activeLabPanel, ...nexusPanels.filter((panel) => panel.title !== activeLabPanel.title)] : nexusPanels).slice(0, 4).map((panel) => <article key={`lab-metric-${panel.title}`}><span>{panel.title}</span><strong>{panel.metrics[0]?.[1] || "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</strong><em>{cleanNexusValue(panel.name)}</em></article>)}</div><div className="edgeiq-lab-v1-table edgeiq-product-v4-table" role="table" aria-label="Lab research leaderboard"><div className="edgeiq-lab-v1-row head" role="row">{['Research Area','Subject','Metric 1','Metric 2','Metric 3','Context'].map((label) => <span key={`lab-research-head-${label}`}>{label}</span>)}</div>{nexusPanels.map((panel) => <div className="edgeiq-lab-v1-row" role="row" key={`lab-research-${panel.title}`}><strong>{panel.title}</strong><span>{cleanNexusValue(panel.name)}</span>{panel.metrics.slice(0, 3).map(([label, value]) => <span key={`lab-research-${panel.title}-${label}`}>{label}: {cleanNexusValue(value)}</span>)}<span>{panel.metrics[3] ? `${panel.metrics[3][0]}: ${cleanNexusValue(panel.metrics[3][1])}` : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</span></div>)}</div></>}</section><aside className="edgeiq-lab-v1-insight"><span>EDGEiQ Insight</span><p>{labModule === "PRICE ENGINE" ? "Price Engine research lets rating-point assumptions be tested against adjusted probability and research price without writing to production pricing feeds." : narrative}</p><strong>{labModule === "PRICE ENGINE" ? "Research Guardrail" : "Saved Studies"}</strong><em>{labModule === "PRICE ENGINE" ? "Local adjustments reset with the browser session and remain research-only." : positives[0] || risks[0] || "Research context pending."}</em></aside></div></section>;
 })() : null}
 {intelMode === "STATS" ? (() => {
 const entityKey = statsMode === "TRAINERS" ? "trainer" : "jockey";
 const entityLabel = statsMode === "TRAINERS" ? "TRAINERS" : "JOCKEYS";
 const entityDisplay = statsMode === "TRAINERS" ? "Trainer" : "Jockey";
 const entityNameFor = (item: EnrichedRunner) => firstText(item.row, statsMode === "TRAINERS" ? ["trainer", "trainer_name"] : ["jockey", "jockey_name", "rider"], "Unknown");
 const statsGroups = activeRaceRows.reduce<Record<string, EnrichedRunner[]>>((acc, item) => {
 const name = entityNameFor(item);
 const key = cleanHorse(name);
 if (!acc[key]) acc[key] = [];
 acc[key].push(item);
 return acc;
 }, {});
 const statsGroupEntries = Object.entries(statsGroups).map(([key, rows]) => {
 const allRuns = rows.flatMap((item) => item.runnerHistory || []);
 const rated = allRuns.map((run) => historyRatingValue(run)).filter((value): value is number => value !== null);
 const wins = allRuns.filter((run) => /^1(ST)?$/i.test(historyFinishText(run))).length;
 const places = allRuns.filter((run) => {
 const pos = integer(historyFinishText(run));
 return pos !== null && pos <= 3;
 }).length;
 const starts = allRuns.length || rows.length;
 const winRate = starts ? (wins / starts) * 100 : null;
 const placeRate = starts ? (places / starts) * 100 : null;
 const avgRating = rated.length ? rated.reduce((sum, value) => sum + value, 0) / rated.length : null;
 const edgeAverage = rows.map((row) => edgePct(row.row, row.bet)).filter((value): value is number => value !== null);
 const roi = edgeAverage.length ? edgeAverage.reduce((sum, value) => sum + value, 0) / edgeAverage.length : null;
 return { key, name: entityNameFor(rows[0]), rows, starts, wins, places, winRate, placeRate, avgRating, roi };
 }).sort((a, b) => (b.avgRating ?? -999) - (a.avgRating ?? -999));
 const activeStatsEntity = statsGroupEntries[0] || null;
 const runnerForStats = activeStatsEntity?.rows[0] || activeRaceRows[0];
 const statRaceRows = activeStatsEntity?.rows || activeRaceRows.slice(0, 5);
 const statsRecentCards = [
 ["Last 10 Starts", activeStatsEntity?.wins ?? 0, activeStatsEntity?.places ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
 ["Last 25 Starts", activeStatsEntity?.wins ?? 0, activeStatsEntity?.places ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
 ["Last 50 Starts", activeStatsEntity?.wins ?? 0, activeStatsEntity?.places ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
 ["Last 100 Starts", activeStatsEntity?.wins ?? 0, activeStatsEntity?.places ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
 ];
 const statsProfileRows = [
 ["Flemington", activeStatsEntity?.starts ?? activeRaceRows.length, activeStatsEntity?.wins ?? 0, activeStatsEntity?.winRate ?? null, activeStatsEntity?.roi ?? null],
 [trackCondition(header), activeStatsEntity?.starts ?? activeRaceRows.length, activeStatsEntity?.places ?? 0, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
 [distance(header), statRaceRows.length, statRaceRows.filter((item) => paceMapRole(item) === "LEADER").length, activeStatsEntity?.winRate ?? null, activeStatsEntity?.roi ?? null],
 [raceClass(header), statRaceRows.length, statRaceRows.filter((item) => !isScratched(item)).length, activeStatsEntity?.placeRate ?? null, activeStatsEntity?.roi ?? null],
 ];
 const statsStyleRows = ["LEADER", "ON PACE", "MIDFIELD", "BACKMARKER"].map((style) => {
 const count = activeRaceRows.filter((item) => paceMapRole(item) === style).length;
 return [style, count, activeRaceRows.length ? (count / activeRaceRows.length) * 100 : null];
 });
 return (
 <section className="edgeiq-stats-tab edgeiq-product-section edgeiq-stats-lock">
 <div className="edgeiq-stats-toolbar">
 <div><span>STATS</span><strong>{entityLabel}</strong><em>Deep analytics and performance profiling for {entityLabel.toLowerCase()}.</em></div>
 <div className="edgeiq-stats-switch">{(["JOCKEYS", "TRAINERS"] as StatsMode[]).map((mode) => <button type="button" key={`stats-mode-${mode}`} className={statsMode === mode ? "is-active" : ""} onClick={() => setStatsMode(mode)}>{mode}</button>)}</div>
 </div>
 <div className="edgeiq-stats-grid">
 <section className="edgeiq-stats-main">
 <header className="edgeiq-stats-profile">
 <div className="edgeiq-stats-avatar">{statsMode === "TRAINERS" ? "T" : "J"}</div>
 <div><strong>{activeStatsEntity?.name || (statsMode === "TRAINERS" ? "Trainer Profile" : "Jockey Profile")}</strong><span>Top rated {entityDisplay.toLowerCase()}</span><em>{track(header)} / {distance(header)} / {raceClass(header)}</em></div>
 <div className="edgeiq-stats-season">{[["Starts", activeStatsEntity?.starts ?? 0], ["Wins", activeStatsEntity?.wins ?? 0], ["Places", activeStatsEntity?.places ?? 0], ["Win %", activeStatsEntity?.winRate ?? null], ["Place %", activeStatsEntity?.placeRate ?? null], ["ROI", activeStatsEntity?.roi ?? null]].map(([label, value]) => <span key={`stats-season-${label}`}><b>{label}</b><strong>{typeof value === "number" ? (String(label).includes("%") || label === "ROI" ? pct(value) : String(value)) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</strong></span>)}</div>
 </header>
 <div className="edgeiq-stats-recent">{statsRecentCards.map(([label, wins, places, winRate, placeRate, roi]) => <article key={`stats-card-${label}`}><span>{label}</span><strong>{wins}</strong><em>Wins</em><strong>{places}</strong><em>Places</em><b>{typeof winRate === "number" ? pct(winRate) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</b><small>ROI {typeof roi === "number" ? pct(roi) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</small></article>)}</div>
 <div className="edgeiq-stats-two">
 <section className="edgeiq-stats-panel"><strong>Performance by {statsMode === "TRAINERS" ? "Track / Class" : "Barrier / Track"}</strong><div className="edgeiq-stats-table">{statsProfileRows.map(([label, starts, wins, winRate, roi]) => <div key={`stats-profile-${label}`}><span>{label}</span><em>{starts}</em><em>{wins}</em><b>{typeof winRate === "number" ? pct(winRate) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</b><b>{typeof roi === "number" ? pct(roi) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</b></div>)}</div></section>
 <section className="edgeiq-stats-panel"><strong>Run Style Match-ups</strong><div className="edgeiq-stats-bars">{statsStyleRows.map(([label, count, rate]) => <div key={`stats-style-${label}`}><span>{label}</span><i><b style={{ width: `${Math.max(8, Number(rate) || 0)}%` }} /></i><em>{count}</em></div>)}</div></section>
 </div>
 <section className="edgeiq-stats-panel"><strong>{statsMode === "TRAINERS" ? "Upcoming Runners" : "Current Race Rides"}</strong><div className="edgeiq-stats-runners">{statRaceRows.slice(0, 8).map((item) => <div key={`stats-runner-${runnerRowKey(item.row)}`}><span>{saddle(item.row) === 999 ? "-" : saddle(item.row)}</span><strong>{horse(item.row)}</strong><em>{firstText(item.row, ["jockey", "jockey_name", "rider"], "-")}</em><em>{firstText(item.row, ["trainer", "trainer_name"], "-")}</em><b>{renderMetricValue(projectionRatingValue(item), 1)}</b></div>)}</div></section>
 </section>
 <aside className="edgeiq-stats-side">
 <section><strong>{entityDisplay} Profile Summary</strong><div className="edgeiq-stats-radar"><i /></div>{[["Win Rate", activeStatsEntity?.winRate], ["Place Rate", activeStatsEntity?.placeRate], ["Consistency", activeStatsEntity?.avgRating], ["Market Perf.", activeStatsEntity?.roi], ["Overall Score", activeStatsEntity?.avgRating]].map(([label, value]) => <div key={`stats-summary-${label}`}><span>{label}</span><em>{typeof value === "number" ? (String(label).includes("Rate") || String(label).includes("Perf") ? pct(value) : renderMetricValue(value, 1)) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</em></div>)}</section>
 <section><strong>Top Tracks</strong>{statsGroupEntries.slice(0, 5).map((entry) => <div key={`stats-top-${entry.key}`}><span>{entry.name}</span><i><b style={{ width: `${Math.max(10, Math.min(100, entry.avgRating ?? 0))}%` }} /></i><em>{entry.avgRating === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : renderMetricValue(entry.avgRating, 1)}</em></div>)}</section>
 <section><strong>Key Insights</strong><p>{activeStatsEntity ? `${activeStatsEntity.name} profiles strongest around ${track(header)} with ${activeStatsEntity.starts} available starts in the terminal sample.` : "Stats profile will populate when runner context is available."}</p><p>Figures are research context only and do not alter ratings or production prices.</p></section>
 </aside>
 </div>
 </section>
 );
 })() : null}
 {intelMode === "DVNCED" ? (() => {
 const marketRows = activeRaceRows;
 const priceFrom = (item: EnrichedRunner, keys: string[]) => firstNum({ ...(item.row || {}), ...(item.bet || {}) }, keys);
 const enrichedMarketRows = marketRows.map((item) => {
 const fair = limitedAdjustedPrice(item) ?? fairPrice(item.row, item.bet);
 const open = priceFrom(item, ["open_price", "opening_price", "market_open", "tab_open_price", "fixed_open_price"]);
 const current = livePrice(item.row, item.bet);
 const fluc = open !== null && current !== null && open > 0 ? ((current - open) / open) * 100 : null;
 const diff = edgePct(item.row, item.bet);
 return { item, fair, open, current, fluc, diff };
 });
 const firmers = enrichedMarketRows.filter((row) => row.fluc !== null && row.fluc < 0);
 const drifters = enrichedMarketRows.filter((row) => row.fluc !== null && row.fluc > 0);
 const unchanged = enrichedMarketRows.filter((row) => row.fluc === null || row.fluc === 0);
 const strongestEdge = [...enrichedMarketRows].filter((row) => row.diff !== null).sort((a, b) => (b.diff ?? -999) - (a.diff ?? -999))[0];
 const biggestFirm = [...firmers].sort((a, b) => (a.fluc ?? 0) - (b.fluc ?? 0))[0];
 const biggestDrift = [...drifters].sort((a, b) => (b.fluc ?? 0) - (a.fluc ?? 0))[0];
 return <section className="edgeiq-market-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-market-v1-lock edgeiq-market-final-lock"><div className="edgeiq-tab-heading edgeiq-product-v4-section-title"><span>MARKET</span><strong>EDGEiQ Trading Floor</strong><em>Market intelligence, fluctuations, value and context.</em></div><div className="edgeiq-market-final-cards">{[["Largest Overlay", strongestEdge ? horse(strongestEdge.item.row) : "Pending", strongestEdge?.diff === null || !strongestEdge ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : pct(strongestEdge.diff)], ["Biggest Firm", biggestFirm ? horse(biggestFirm.item.row) : "Pending", biggestFirm?.fluc === null || !biggestFirm ? "Pending Market" : `ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Å“ ${Math.abs(biggestFirm.fluc).toFixed(1)}%`], ["Biggest Drift", biggestDrift ? horse(biggestDrift.item.row) : "Pending", biggestDrift?.fluc === null || !biggestDrift ? "Pending Market" : `ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Ëœ ${Math.abs(biggestDrift.fluc).toFixed(1)}%`], ["Market Confidence", bettingConfidence !== "-" ? bettingConfidence : "Pending", ""]].map(([label, value, detail]) => <article key={`market-card-${label}`}><span>{label}</span><strong>{value}</strong><em>{detail}</em></article>)}</div><div className="edgeiq-market-content-grid"><div className="edgeiq-market-table edgeiq-product-table edgeiq-product-v4-table" role="table" aria-label="Market comparison table"><div className="edgeiq-market-row head" role="row">{['NO','RUNNER','EDGEIQ','OPEN','CURRENT','FLUC','EDGE %'].map((label) => <span key={`market-head-${label}`}>{label}</span>)}</div>{enrichedMarketRows.map(({ item, fair, open, current, fluc, diff }) => { const flucClass = fluc === null ? "neutral" : fluc > 0 ? "drift" : fluc < 0 ? "firm" : "neutral"; const flucDisplay = fluc === null ? "Pending Market" : fluc > 0 ? `ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Ëœ ${Math.abs(fluc).toFixed(1)}%` : fluc < 0 ? `ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Å“ ${Math.abs(fluc).toFixed(1)}%` : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 0.0%"; return <div className="edgeiq-market-row" role="row" key={`market-row-${runnerRowKey(item.row)}`}><span>{saddle(item.row) === 999 ? "-" : saddle(item.row)}</span><strong>{horse(item.row)}</strong><span>{money(fair)}</span><span>{marketMoney(open)}</span><span>{marketMoney(current)}</span><span className={flucClass}>{flucDisplay}</span><span className={diff === null ? "neutral" : diff > 0 ? "positive" : "negative"}>{diff === null ? "-" : pct(diff)}</span></div>; })}</div><aside className="edgeiq-market-fluc-panel edgeiq-market-final-side"><section><span>Market Pulse</span>{[["Firmers", firmers.length], ["Drifters", drifters.length], ["Unchanged", unchanged.length]].map(([label, value]) => <div key={`market-pulse-${label}`}><em>{label}</em><strong>{value}</strong></div>)}</section><section><span>Money Flow</span>{[...firmers].sort((a, b) => (a.fluc ?? 0) - (b.fluc ?? 0)).slice(0, 3).map((row, index) => <div key={`market-flow-${runnerRowKey(row.item.row)}`}><em>{index + 1}. {horse(row.item.row)}</em><strong className="firm">ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Å“ {Math.abs(row.fluc ?? 0).toFixed(1)}%</strong></div>)}</section><section><span>Market Narrative</span><p>Market board shows live price movement and EDGEiQ fair-price context only. No recommendation language is shown.</p></section></aside></div></section>;
 })() : null}
 {intelMode === "RESULTS" ? (() => {
 const resultRows = [...activeRaceRows].sort((a, b) => saddle(a.row) - saddle(b.row));
 const resultValue = (row: Row, keys: string[], fallback = "Pending") => {
 const raw = firstText(row, keys, "");
 return raw && raw !== "-" ? raw : fallback;
 };
 const resultPosition = (item: EnrichedRunner, index: number) => resultValue(item.row, ["finish_position", "finishing_position", "result_position", "pos"], String(index + 1));
 const resultMargin = (row: Row) => resultValue(row, ["margin", "beaten_margin", "official_margin"], "Pending");
 const resultEpi = (item: EnrichedRunner) => firstNum(item.ratingsHeatmap, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(item);
 const sectional = (row: Row, keys: string[]) => resultValue(row, keys, "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â");
 const sectionalNumber = (value: string) => num(String(value).replace(/[Ll]/g, ""));
 const sectionalClass = (value: string) => {
 const parsed = sectionalNumber(value);
 return parsed !== null && parsed < 0 ? "inside-standard" : "outside-standard";
 };
 const sectionalsFor = (row: Row) => ({
 s800: sectional(row, ["last_800_vs_standard", "last_800_lengths", "last800", "sectional_800"]),
 s600: sectional(row, ["last_600_vs_standard", "last_600_lengths", "last600", "sectional_600"]),
 s400: sectional(row, ["last_400_vs_standard", "last_400_lengths", "last400", "sectional_400"]),
 s200: sectional(row, ["last_200_vs_standard", "last_200_lengths", "last200", "sectional_200"]),
 finish: sectional(row, ["finish_vs_standard", "finish_lengths", "last_finish", "sectional_finish"]),
 });
 const rankingMetrics = [
 { label: "Best Last 800m", key: "s800" as const },
 { label: "Best Last 600m", key: "s600" as const },
 { label: "Best Last 400m", key: "s400" as const },
 { label: "Best Last 200m", key: "s200" as const },
 { label: "Strongest Finish", key: "finish" as const },
 ].map((metric) => {
 const ranked = resultRows
 .map((item) => ({ item, value: sectionalsFor(item.row)[metric.key] }))
 .map((entry) => ({ ...entry, numeric: sectionalNumber(entry.value) }))
 .filter((entry): entry is typeof entry & { numeric: number } => entry.numeric !== null)
 .sort((a, b) => a.numeric - b.numeric);
 return { ...metric, winner: ranked[0] || null, runnerUp: ranked[1] || null };
 });
 const officialTime = firstText(header, ["official_time", "winning_time", "race_time_official"], "Pending");
 const last600 = firstText(header, ["race_last_600", "last_600", "overall_last_600"], "Pending");
 const raceTempo = firstText(header, ["race_tempo", "tempo", "race_shape"], displayExpectedTempo !== "-" ? displayExpectedTempo : "Pending");
 return (
 <section className="edgeiq-results-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-results-v1-lock">
 <div className="edgeiq-tab-heading edgeiq-product-v4-section-title"><span>RESULTS</span><strong>Race Review & Intelligence</strong><em>Official result and standardised sectional performance.</em></div>
 <div className="edgeiq-results-v1-grid edgeiq-results-v1-top-grid">
 <section className="edgeiq-results-v1-panel">
 <div className="edgeiq-results-v1-title">Official Results</div>
 <div className="edgeiq-results-v1-table edgeiq-product-v4-table" role="table" aria-label="Official results">
 <div className="edgeiq-results-v1-row head" role="row">{["POS","NO","SILK","RUNNER","MARGIN (BEATEN BY)","EPI"].map((label) => <span key={`results-official-head-${label}`}>{label}</span>)}</div>
 {resultRows.map((item, index) => <div className="edgeiq-results-v1-row" role="row" key={`results-official-${runnerRowKey(item.row)}`}><span>{resultPosition(item, index)}</span><span>{saddle(item.row) === 999 ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : saddle(item.row)}</span><span className="edgeiq-field-silk" aria-label={`${horse(item.row)} silk`}><i /></span><strong>{horse(item.row)}</strong><span>{resultMargin(item.row)}</span><span>{resultEpi(item) === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : renderMetricValue(resultEpi(item), 1)}</span></div>)}
 </div>
 <div className="edgeiq-results-v1-meta">Official Time: <span>{officialTime}</span> <i /> Last 600m: <span>{last600}</span> <i /> Track Condition: <span>{trackCondition(header)}</span> <i /> Rail: <span>{railDisplay}</span></div>
 </section>
 <section className="edgeiq-results-v1-panel">
 <div className="edgeiq-results-v1-title">Sectionals <em>(Lengths Faster Than Standard)</em></div>
 <div className="edgeiq-sectionals-v1-table edgeiq-product-v4-table" role="table" aria-label="Sectionals">
 <div className="edgeiq-sectionals-v1-row head" role="row">{["POS","RUNNER","800M","600M","400M","200M","FINISH"].map((label) => <span key={`sectionals-head-${label}`}>{label}</span>)}</div>
 {resultRows.map((item, index) => {
 const values = sectionalsFor(item.row);
 return <div className="edgeiq-sectionals-v1-row" role="row" key={`sectionals-${runnerRowKey(item.row)}`}><span>{resultPosition(item, index)}</span><strong>{horse(item.row)}</strong>{[values.s800, values.s600, values.s400, values.s200, values.finish].map((value, valueIndex) => <span key={`sectionals-${runnerRowKey(item.row)}-${valueIndex}`} className={sectionalClass(value)}>{value}</span>)}</div>;
 })}
 </div>
 <div className="edgeiq-results-v1-scale"><span>Faster than standard</span><i>ÃƒÂ¢Ã¢â‚¬Â°Ã‚Â¤ -4.0L</i><i>-4.0L to -2.0L</i><i>-2.0L to -0.1L</i><b>0.0L Standard</b><em>Slower than standard</em><strong>+0.1L or more</strong></div>
 <p className="edgeiq-results-v1-data-label">Data is EDGEiQ Standardised Sectionals</p>
 </section>
 </div>
 <div className="edgeiq-results-v1-bottom-grid">
 <section className="edgeiq-results-v1-panel">
 <div className="edgeiq-results-v1-title">Sectional Rankings</div>
 <div className="edgeiq-results-ranking-table edgeiq-product-v4-table" role="table" aria-label="Sectional rankings">
 <div className="edgeiq-results-ranking-row head" role="row">{["METRIC","WINNER","FIGURE","RUNNER UP","FIGURE"].map((label) => <span key={`ranking-head-${label}`}>{label}</span>)}</div>
 {rankingMetrics.map((metric) => <div className="edgeiq-results-ranking-row" role="row" key={`sectional-ranking-${metric.label}`}><span>{metric.label}</span><strong>{metric.winner ? horse(metric.winner.item.row) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</strong><span>{metric.winner?.value || "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</span><strong>{metric.runnerUp ? horse(metric.runnerUp.item.row) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</strong><span>{metric.runnerUp?.value || "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</span></div>)}
 </div>
 </section>
 <section className="edgeiq-results-v1-panel edgeiq-results-review-panel">
 <div className="edgeiq-results-v1-title">Race Review</div>
 <p>Race review is based on official finishing order, EDGEiQ performance ratings and standardised sectional context.</p>
 <p>{raceTempo !== "Pending" ? `Tempo profile: ${raceTempo}.` : "Tempo profile pending."} Faster-than-standard sectional cells are highlighted in green; slower values remain neutral.</p>
 </section>
 <section className="edgeiq-results-v1-panel edgeiq-results-info-panel">
 {[["Winning Time", officialTime], ["Last 600m", last600], ["Race Tempo", raceTempo], ["Track Condition", trackCondition(header)], ["Rail Position", railDisplay], ["Race Grade", raceClass(header)], ["Number of Runners", String(activeRaceRows.length)]].map(([label, value]) => <article key={`results-info-${label}`}><span>{label}</span><strong>{value}</strong></article>)}
 </section>
 </div>
 </section>
 );
 })() : null}
 {intelMode === "TRACK" ? (
 <section className="edgeiq-track-tab edgeiq-product-section edgeiq-product-v4-panel">
 <div className="edgeiq-tab-heading edgeiq-product-v4-section-title"><span>TRACK</span><strong>Track Profile</strong><em>Track map, rail and race-day profile.</em></div>
 <div className="edgeiq-product-v4-fact-grid">
 {[["Track", track(header)], ["Distance", distance(header)], ["Condition", trackCondition(header)], ["Rail", railDisplay], ["Race", `R${raceNo(header)}`], ["Runners", String(activeRaceRows.length)]].map(([label, value]) => <article key={`track-v4-${label}`}><span>{label}</span><strong>{value && value !== "-" ? value : "Pending"}</strong></article>)}
 </div>
 </section>
 ) : null}
{intelMode === "WEATHER" ? (() => {
 const conditionValue = (keys: string[], fallback = "Pending") => {
 const raw = firstText(header, keys, "");
 return raw && raw !== "-" ? raw : fallback;
 };
 const trackPattern = conditionValue(["track_pattern", "bias_pattern", "current_track_pattern"], "Neutral");
 const leaderBias = conditionValue(["leader_bias", "front_runner_bias"], "Neutral");
 const insideBias = conditionValue(["inside_bias", "inside_lane_bias"], "Neutral");
 const outsideBias = conditionValue(["outside_bias", "outside_lane_bias"], "Neutral");
 const wind = [conditionValue(["wind_direction", "wind_dir"], ""), conditionValue(["wind_speed", "wind"], "")].filter((value) => value && value !== "Pending").join(" ") || "Pending";
 const conditionCards = [
 { label: "Track", value: trackCondition(header), icon: "track" },
 { label: "Rail", value: railDisplay, icon: "rail" },
 { label: "Wind", value: wind, icon: "wind" },
 { label: "Rainfall", value: conditionValue(["rainfall", "rainfall_24h", "rain_24h"]), icon: "rain" },
 { label: "Irrigation", value: conditionValue(["irrigation", "irrigation_24h"]), icon: "water" },
 { label: "Temperature", value: conditionValue(["temperature", "temp"]), icon: "temp" },
 { label: "Humidity", value: conditionValue(["humidity"]), icon: "humidity" },
 { label: "Penetrometer", value: conditionValue(["penetrometer", "penetrometer_reading"]), icon: "pen" },
 ];
 return (
 <section className="edgeiq-weather-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-conditions-v1-lock edgeiq-conditions-final-lock">
 <div className="edgeiq-tab-heading edgeiq-product-v4-section-title"><span>CONDITIONS</span><strong>Conditions Intelligence</strong><em>Track, weather, bias and race impact.</em></div>
 <div className="edgeiq-conditions-v1-cards edgeiq-conditions-final-cards">
 {conditionCards.map((card) => <article key={`conditions-v1-${card.label}`}><i className={`edgeiq-conditions-card-icon is-${card.icon}`} aria-hidden="true" /><span>{card.label}</span><strong>{card.value && card.value !== "-" ? card.value : "Pending"}</strong></article>)}
 </div>
 <div className="edgeiq-conditions-final-grid">
 <section><strong>Track Pattern Intelligence</strong>{[["Current Track Pattern", trackPattern], ["Leader Bias", leaderBias], ["Inside Bias", insideBias], ["Outside Bias", outsideBias], ["Track Evolution", conditionValue(["track_evolution", "track_trend"], "Pending")]].map(([label, value]) => <div key={`conditions-pattern-${label}`}><span>{label}</span><em>{value}</em></div>)}</section>
 <section><strong>Historical Profile</strong>{[["Track", track(header)], ["Distance", distance(header)], ["Condition", trackCondition(header)], ["Rail", railDisplay], ["Race Grade", raceClass(header)]].map(([label, value]) => <div key={`conditions-history-${label}`}><span>{label}</span><em>{value}</em></div>)}</section>
 <section><strong>Weather Impact</strong>{[["Wind", wind], ["Rainfall", conditionCards[3].value], ["Temperature", conditionCards[5].value], ["Humidity", conditionCards[6].value], ["Surface Change", conditionValue(["surface_change", "track_condition_change"], "Pending")]].map(([label, value]) => <div key={`conditions-weather-${label}`}><span>{label}</span><em>{value}</em></div>)}</section>
 <section><strong>Expected Race Shape</strong>{[["Tempo Impact", displayExpectedTempo !== "-" ? displayExpectedTempo : "Pending"], ["Lane Impact", insideBias !== "Neutral" ? `Inside: ${insideBias}` : outsideBias !== "Neutral" ? `Outside: ${outsideBias}` : "Neutral"], ["Likely Suited", conditionValue(["conditions_suited", "track_suited"], "Pending")], ["Likely Disadvantaged", conditionValue(["conditions_disadvantaged", "track_disadvantaged"], "Pending")]].map(([label, value]) => <div key={`conditions-shape-${label}`}><span>{label}</span><em>{value}</em></div>)}</section>
 <section className="edgeiq-conditions-final-summary"><strong>EDGEiQ Conditions Summary</strong><p>{conditionValue(["conditions_summary", "track_weather_summary"], `Current profile: ${trackCondition(header)} with rail ${railDisplay}. Bias intelligence is ${trackPattern.toLowerCase()}.`)}</p></section>
 </div>
 </section>
 );
})() : null}
 </main>
 </div>
 {ratingHover ? (
 <div className="edgeiq-performance-tooltip" style={{ left: ratingHover.x, top: ratingHover.y }} role="tooltip">
 <strong>{ratingHover.title}</strong>
 {ratingHover.subtitle ? <em>{ratingHover.subtitle}</em> : null}
 <div>
 {ratingHover.metrics.map((metric) => <span key={`rating-hover-${metric.label}`}><b>{metric.label}</b><i style={{ color: metric.tone || undefined }}>{metric.value}</i></span>)}
 </div>
 {ratingHover.footer ? <p>{ratingHover.footer}</p> : null}
 </div>
 ) : null}
 <footer className="edgeiq-home-v4-footer edgeiq-product-v4-footer">
 <div>EDGEiQ ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â ADAPTIVE RACING INTELLIGENCE</div>
 <div>NOT NOISE. <span>JUST CONTEXT.</span></div>
 </footer>
{fullHistoryRunner ? (() => {
 const modalRows = fullHistoryRunner.runnerHistory || [];
 const ratedRows = ratedHistoryRows(modalRows);
 const career = fullHistoryRunner.runnerCareer || {};
 const starts = firstNum(career, ["career_starts", "starts"]) ?? modalRows.length;
 const wins = firstNum(career, ["career_wins", "wins"]) ?? modalRows.filter((run) => Number(String(historyFinishText(run)).replace(/[^0-9.-]/g, "")) === 1).length;
 const places = firstNum(career, ["career_places", "places"]) ?? modalRows.filter((run) => { const pos = Number(String(historyFinishText(run)).replace(/[^0-9.-]/g, "")); return Number.isFinite(pos) && pos > 0 && pos <= 3; }).length;
 const winRate = firstNum(career, ["career_win_pct", "win_pct"]) ?? (starts ? (wins / starts) * 100 : null);
 const placeRate = firstNum(career, ["career_place_pct", "place_pct"]) ?? (starts ? (places / starts) * 100 : null);
 const peak = ratedRows.length ? Math.max(...ratedRows.map((run) => historyRatingValue(run) ?? Number.NEGATIVE_INFINITY).filter((value) => Number.isFinite(value))) : null;
 const avg = ratedRows.length ? ratedRows.reduce((sum, run) => sum + (historyRatingValue(run) ?? 0), 0) / ratedRows.length : null;
 const cleanHistory = (value: unknown) => {
 const raw = String(value ?? "").trim();
 if (!raw || /^(UNKNOWN|NOT LOADED|SOURCE GAP|SOURCE_MISSING|NULL|N\/A|NA|UNDEFINED|0\.0)$/i.test(raw)) return "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â";
 return raw;
 };
 return <div className="edgeiq-career-modal-backdrop" role="dialog" aria-modal="true" aria-label="Full career history"><section className="edgeiq-career-modal"><header><div><span>Full Career History</span><strong>{horse(fullHistoryRunner.row)}</strong><em>{firstText(fullHistoryRunner.row, ["trainer", "trainer_name"], "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â")} / {firstText(fullHistoryRunner.row, ["jockey", "jockey_name", "rider"], "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â")}</em></div><button type="button" onClick={() => setFullHistoryRunner(null)} aria-label="Close full career history">Close</button></header><div className="edgeiq-career-summary">{[["Starts", starts], ["Wins", wins], ["Places", places], ["Win %", winRate], ["Place %", placeRate], ["Peak EPI", peak], ["Average EPI", avg]].map(([label, value]) => <article key={`career-summary-${label}`}><span>{label}</span><strong>{typeof value === "number" ? (String(label).includes("%") ? `${value.toFixed(1)}%` : renderMetricValue(value, 1)) : "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}</strong></article>)}</div><div className="edgeiq-career-history-table" role="table" aria-label="Runner full career history"><div className="edgeiq-career-history-row head" role="row">{['DATE','TRACK','DIST','CLASS','GOING','BAR','JOCKEY','POS','MARGIN','SP','EPI','SETTLED / RUN STYLE'].map((label) => <span key={`career-head-${label}`}>{label}</span>)}</div>{modalRows.length ? modalRows.map((run, index) => <div className="edgeiq-career-history-row" role="row" key={`career-history-${index}-${historyRunKey(run)}`}><span>{cleanHistory(formatHistoryDate(historyDateText(run)))}</span><span>{cleanHistory(historyTrackText(run))}</span><span>{cleanHistory(historyDistanceText(run))}</span><span>{cleanHistory(historyClassText(run))}</span><span>{cleanHistory(historyGoingText(run))}</span><span>{cleanHistory(firstText(run, ["barrier", "draw", "barrier_number"], ""))}</span><span>{cleanHistory(historyJockeyText(run))}</span><span>{cleanHistory(historyFinishText(run))}</span><span>{cleanHistory(firstText(run, ["margin", "beaten_margin"], ""))}</span><span>{cleanHistory(historySpText(run))}</span><span>{historyRatingValue(run) === null ? "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â" : renderMetricValue(historyRatingValue(run), 1)}</span><span>{cleanHistory(firstText(run, ["settling_position", "run_style", "pos_800", "pos_400"], ""))}</span></div>) : <div className="edgeiq-career-history-empty">Career history not loaded for this runner.</div>}</div></section></div>;
 })() : null}

 </section>
 </div>
 );
}








































