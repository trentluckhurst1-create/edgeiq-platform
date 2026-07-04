import type { CsvRow } from "../utils/edgeiqCsv";
import { text } from "../utils/edgeiqFormat";
import { firstNum, firstText, horse } from "../utils/raceRowHelpers";

type Row = CsvRow;
type EnrichedRunnerLike = {
  row: Row;
  runnerIntel?: Row;
  drawer?: Row;
  intel?: Row;
  dna?: Row;
  runnerProfile?: Row;
  mapEnrichment?: Row;
  factorRows?: Row[];
  connection?: Row;
  explainability?: Row;
  limited?: Row;
  bet?: Row;
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

function connectionSourceRow(item: EnrichedRunnerLike): Row | undefined {
  if (hasMergedEvidencePayload(item.row)) return item.row;
  if (hasConnectionPayload(item.connection)) return item.connection;
  if (hasConnectionPayload(item.explainability)) return item.explainability;
  return item.explainability || item.connection || item.row;
}

export function confidenceScoreValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.runnerProfile, ["confidence_score"]) ??
 firstNum(item.runnerIntel, ["confidence_score"]) ??
 firstNum(item.drawer, ["confidence_score"]) ??
 firstNum(item.intel, ["confidence_score", "intelligence_reliability_component_v1"]) ??
 firstNum(item.row, ["confidence_score"]);
}

export function dnaScoreValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.dna, ["dna_v6_2_score", "runner_dna_v6_1_score", "dna_score"]) ??
 firstNum(item.runnerProfile, ["dna_v6_2_score", "dna_score"]) ??
 firstNum(item.row, ["dna_v6_2_score", "runner_dna_v6_1_score", "dna_score"]);
}

export function projectionGapValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.row, ["projection_gap_V6_1_RESERCH", "projection_gap_v5_2"]);
}

export function projectedSpdValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.mapEnrichment, ["projected_speed"]) ??
 firstNum(item.runnerIntel, ["projected_spd"]) ??
 firstNum(item.row, ["projected_spd", "early_speed_rating"]);
}

export function sectionalWeaponValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.runnerIntel, ["sectional_weapon_score"]) ??
 firstNum(item.drawer, ["sectional_weapon_score"]) ??
 firstNum(item.intel, ["intelligence_sectional_component_v1"]) ??
 firstNum(item.row, ["sectional_weapon_score"]);
}

export function latePowerMetricValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.mapEnrichment, ["late_speed"]) ??
 firstNum(item.runnerIntel, ["late_power_index", "late_power_score"]) ??
 firstNum(item.drawer, ["late_power_index", "late_power_score"]) ??
 firstNum(item.row, ["late_power_index", "late_power_score"]);
}

export function trackFitScoreValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.drawer, ["track_fit_score"]) ??
 firstNum(item.row, ["track_fit_score"]) ??
 firstNum(item.intel, ["track_fit_score"]);
}

export function jockeyScoreValue(item: EnrichedRunnerLike): number | null {
 const connectionRow = connectionSourceRow(item);
 return firstNum(factorRowValue(item, "JOCKEY"), ["factor_score"]) ??
 firstNum(item.runnerIntel, ["jockey_score"]) ??
 firstNum(item.drawer, ["jockey_score"]) ??
 firstNum(item.row, ["jockey_score"]) ??
 firstNum(connectionRow, ["jockey_track_sr", "connection_score"]);
}

export function trainerScoreValue(item: EnrichedRunnerLike): number | null {
 const connectionRow = connectionSourceRow(item);
 return firstNum(factorRowValue(item, "TRINER"), ["factor_score"]) ??
 firstNum(item.runnerIntel, ["trainer_score"]) ??
 firstNum(item.drawer, ["trainer_score"]) ??
 firstNum(item.row, ["trainer_score"]) ??
 firstNum(connectionRow, ["trainer_track_sr", "connection_score"]);
}

export function connectionScoreValue(item: EnrichedRunnerLike): number | null {
 const connectionRow = connectionSourceRow(item);
 return firstNum(factorRowValue(item, "CONNECTION"), ["factor_score"]) ??
 firstNum(item.runnerIntel, ["connection_score"]) ??
 firstNum(item.drawer, ["connection_score"]) ??
 firstNum(item.row, ["connection_score"]) ??
 firstNum(connectionRow, ["connection_score"]);
}

export function projectionRatingValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.row, ["projected_rating_V6_1_RESERCH", "projected_rating_v5_2"]) ??
 firstNum(item.runnerProfile, ["projected_rating", "rating_ladder_score"]);
}

export function factorRowValue(item: EnrichedRunnerLike, factorName: string): Row | undefined {
 return item.factorRows?.find(
 (factorRow) => firstText(factorRow, ["factor"], "").toUpperCase() === factorName.toUpperCase()
 );
}

export function factorScoreValue(item: EnrichedRunnerLike, factorName: string): number | null {
 if (factorName.toUpperCase() === "PCE") {
 return firstNum(item.mapEnrichment, ["pace_fit"]) ?? firstNum(factorRowValue(item, factorName), ["factor_score"]);
 }
 return firstNum(factorRowValue(item, factorName), ["factor_score"]);
}

export function factorBandValue(item: EnrichedRunnerLike, factorName: string): string {
 if (factorName.toUpperCase() === "PCE") {
 const mapBand = firstText(item.mapEnrichment, ["pace_fit_band"], "");
 if (mapBand) return mapBand.replace(/_/g, " ").toUpperCase();
 }
 return firstText(factorRowValue(item, factorName), ["factor_band"], "-").replace(/_/g, " ").toUpperCase();
}

export function comboScoreValue(item: EnrichedRunnerLike): number | null {
 const connectionRow = connectionSourceRow(item);
 return factorScoreValue(item, "COMBO") ??
 firstNum(connectionRow, ["combo_sr", "combo_track_sr", "connection_score"]) ??
 connectionScoreValue(item);
}

export function paceMapRole(item: EnrichedRunnerLike): string {
 const raw = firstText(
 item.mapEnrichment,
 ["settling_position", "run_style", "lane"],
 firstText(
 item.row,
 ["settling_band", "run_style", "speed_map_bucket", "early_speed_band"],
 firstText(
 item.runnerIntel,
 ["settling_band", "run_style", "early_speed_band"],
 firstText(item.drawer, ["dominant_run_style"], "")
 )
 )
 )
 .replace(/_/g, " ")
 .toUpperCase()
 .trim();

 if (!raw) return "MIDFIELD";
 if (raw.includes("LEADER")) return "LEADERS";
 if (raw.includes("ON PACE") || raw === "PCE") return "ON PACE";
 if (raw.includes("BCKMRK")) return "BACKMARKERS";
 if (raw.includes("OFF PCE")) return "MIDFIELD";
 if (raw.includes("MIDFIELD")) return "MIDFIELD";
 return "MIDFIELD";
}

export function paceMapXPercent(item: EnrichedRunnerLike): number {
 const explicit = firstNum(item.mapEnrichment, ["map_x_pct"]) ?? firstNum(item.row, ["map_x_pct"]);
 if (explicit !== null && Number.isFinite(explicit)) {
 return Math.max(6, Math.min(94, explicit));
 }
 const role = paceMapRole(item);
 if (role === "LEADERS") return 12;
 if (role === "ON PACE") return 30;
 if (role === "MIDFIELD") return 55;
 if (role === "BACKMARKERS") return 78;
 return 50;
}

export function shortHorseName(value: string, maxLength = 16): string {
 const clean = text(value);
 if (!clean) return "Runner";
 if (clean.length <= maxLength) return clean;
 return `${clean.slice(0, maxLength - 1).trimEnd()}`;
}

export function paceRoleTone(role: string): string {
 const normalized = role.toUpperCase();
 if (normalized === "LEADERS") return "#34d399";
 if (normalized === "ON PACE") return "#ffffff";
 if (normalized === "MIDFIELD") return "#ffffff";
 if (normalized === "BACKMARKERS") return "#f87171";
 return "#94a3b8";
}

export function paceRoleSpeedValue(role: string): number {
 const normalized = role.toUpperCase();
 if (normalized === "LEADERS") return 82;
 if (normalized === "ON PACE") return 68;
 if (normalized === "MIDFIELD") return 48;
 if (normalized === "BACKMARKERS") return 28;
 return 45;
}

export function scoreTone(value: number | null, high = 60, medium = 45): string {
 if (value === null || !Number.isFinite(value)) return "#94a3b8";
 if (value >= high) return "#34d399";
 if (value >= medium) return "#ffffff";
 return "#f87171";
}

export function intelligenceScoreValue(item: EnrichedRunnerLike): number | null {
 return firstNum(item.intel, ["intelligence_score_v1"]);
}

export function normalizeGradeLabel(value: string): string {
 const v = value.toUpperCase();
 if (!v || v === "-") return "";
 if (v.includes("SCRTCH")) return "SCRATCHED";
 if (v.includes("LOW DT")) return "LOW DT";
 if (v.includes("HIGH") || v.includes("ELITE") || v.includes("STRONG")) return "HIGH";
 if (v.includes("MEDIUM") || v.includes("PSS") || v.includes("WATCH") || v.includes("NEUTRAL")) return "MEDIUM";
 if (v.includes("LOW") || v.includes("POOR") || v.includes("NEGATIVE") || v.includes("WEK")) return "LOW";
 return v;
}

export function limitedAdjustedPrice(item: EnrichedRunnerLike): number | null {
 return firstNum(item.limited, ["limited_data_adjusted_price_v1"]) ??
 firstNum(item.row, ["limited_data_adjusted_price_v1"]);
}

export function betQualityNumeric(item: EnrichedRunnerLike): number | null {
 return firstNum(item.bet, ["bet_quality_score_v1_1", "bet_quality_score"]) ??
 firstNum(item.drawer, ["bet_quality_score"]) ??
 firstNum(item.intel, ["intelligence_bet_quality_component_v1", "bet_quality_score"]) ??
 firstNum(item.row, ["bet_quality_score_v1_1", "bet_quality_score"]);
}

export function sourceBetQualityGrade(item: EnrichedRunnerLike): string {
 return normalizeGradeLabel(firstText(item.bet, ["bet_quality_grade_v1_1", "bet_quality_grade"], ""));
}

