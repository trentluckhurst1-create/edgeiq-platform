from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "marketPricingService.ts"
service.write_text(r'''import type { CsvRow } from "../utils/edgeiqCsv";
import { text } from "../utils/edgeiqFormat";
import { firstNum, firstText } from "../utils/raceRowHelpers";

type Row = CsvRow;

export function isV72FeatureOn(row: Row | undefined): boolean {
  return text(row?.edgeiq_v7_2_feature_flag).toUpperCase() === "ON";
}

export function getV72wareProbability(row: Row | undefined): number | null {
  if (isV72FeatureOn(row)) {
    return firstNum(row, ["edgeiq_v7_2_preview_probability", "edgeiq_probability_v7_2"]);
  }
  return firstNum(row, ["win_pct", "V6_1_RESERCH_probability", "probability_normalised_v1"]);
}

export function getV72wareFairPrice(row: Row | undefined): number | null {
  if (isV72FeatureOn(row)) {
    return firstNum(row, ["edgeiq_v7_2_preview_fair_price", "edgeiq_fair_price_v7_2"]);
  }
  return firstNum(row, ["fair_price", "ui_fair_price", "display_fair_price", "rated_price"]);
}

export function getV72wareDisplayFairPrice(row: Row | undefined): number | null {
  if (isV72FeatureOn(row)) {
    return firstNum(row, ["edgeiq_v7_2_preview_display_fair_price", "edgeiq_display_fair_price_v7_2"]);
  }
  return firstNum(row, ["ui_fair_price", "display_fair_price", "fair_price", "rated_price"]);
}

export function getV72PriceSource(row: Row | undefined): string {
  if (isV72FeatureOn(row)) {
    return firstText(row, ["edgeiq_v7_2_preview_price_source", "edgeiq_v7_2_probability_source", "probability_source_v7_2"], "V7_2_FETURE_FLG_ON");
  }
  return firstText(row, ["edgeiq_active_price_source_shadow"], "PRODUCTION_FLLBCK_FETURE_FLG_OFF");
}

export function fairPrice(row: Row, bet?: Row): number | null {
  return getV72wareDisplayFairPrice(row) ??
    firstNum(bet, ["bet_quality_fair_price_used_v1_1", "fair_price"]);
}

export function livePrice(row: Row, bet?: Row): number | null {
  return firstNum(row, ["market_price", "display_market_price", "display_live_price", "live_price", "sportsbet_price", "fixed_win", "tab_fixed_win"]) ??
    firstNum(bet, ["bet_quality_live_price_used_v1_1", "live_price"]);
}

export function edgePct(row: Row, bet?: Row): number | null {
  const direct =
    firstNum(row, ["display_edge_pct", "edge_pct", "ui_edge_pct"]) ??
    firstNum(bet, ["bet_quality_overlay_pct_v1_1", "edge_pct"]);

  if (direct !== null) return direct;

  const live = livePrice(row, bet);
  const fair = fairPrice(row, bet);
  if (live && fair) return ((live / fair) - 1) * 100;
  return null;
}

export function winPct(row: Row, bet?: Row): number | null {
  const p = getV72wareProbability(row) ??
    firstNum(row, ["v3_probability", "edgeiq_probability", "rated_probability", "win_probability"]) ??
    firstNum(bet, ["v3_probability"]);

  if (p !== null && p > 0) return p > 1 ? p : p * 100;

  const fair = fairPrice(row, bet);
  return fair && fair > 0 ? 100 / fair : null;
}

export function v8Fair(v8?: Row, bet?: Row): number | null {
  return firstNum(v8, ["v8_candidate_price_display", "v8_interaction_candidate_price"]) ??
    firstNum(bet, ["v8_candidate_price_display"]);
}

export function v8Conf(v8?: Row, bet?: Row): string {
  return firstText(v8, ["brc_match_level_v8", "v8_confidence"], firstText(bet, ["brc_match_level_v8"], "-"))
    .replace("TRACK_DISTNCE_RIL_CONDITION_WIDE", "LOW")
    .replace("TRACK_DISTNCE_RIL_CONDITION", "MEDIUM")
    .replace("EXCT", "HIGH")
    .replace(/_/g, " ");
}

export function betScore(bet?: Row): string {
  const n = firstNum(bet, ["bet_quality_score_v1_1", "bet_quality_score"]);
  return n === null ? "-" : n.toFixed(0);
}

export function betGrade(bet?: Row): string {
  return firstText(bet, ["bet_quality_grade_v1_1", "bet_quality_grade"], "-").toUpperCase();
}
''', encoding="utf-8")

patterns = [
  r'\nfunction isV72FeatureOn\(row: Row \| undefined\): boolean \{.*?\n\}\n\s*\nfunction getV72wareProbability\(row: Row \| undefined\): number \| null \{.*?\n\}\n\s*\nfunction getV72wareFairPrice\(row: Row \| undefined\): number \| null \{.*?\n\}\n\s*\nfunction getV72wareDisplayFairPrice\(row: Row \| undefined\): number \| null \{.*?\n\}\n\s*\nfunction getV72PriceSource\(row: Row \| undefined\): string \{.*?\n\}\n',
  r'\nfunction fairPrice\(row: Row, bet\?: Row\): number \| null \{.*?\n\}\n\s*\nfunction livePrice\(row: Row, bet\?: Row\): number \| null \{.*?\n\}\n\s*\nfunction edgePct\(row: Row, bet\?: Row\): number \| null \{.*?\n\}\n\s*\nfunction winPct\(row: Row, bet\?: Row\): number \| null \{.*?\n\}\n\s*\nfunction v8Fair\(v8\?: Row, bet\?: Row\): number \| null \{.*?\n\}\n\s*\nfunction v8Conf\(v8\?: Row, bet\?: Row\): string \{.*?\n\}\n\s*\nfunction betScore\(bet\?: Row\): string \{.*?\n\}\n\s*\nfunction betGrade\(bet\?: Row\): string \{.*?\n\}\n'
]

for pattern in patterns:
    text, count = re.subn(pattern, "\n", text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("[ERROR] market/pricing helper pattern not replaced")

import_line = 'import { betGrade, betScore, edgePct, fairPrice, getV72PriceSource, getV72wareDisplayFairPrice, getV72wareFairPrice, getV72wareProbability, isV72FeatureOn, livePrice, v8Conf, v8Fair, winPct } from "../services/marketPricingService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[MARKET_PRICING_SERVICE_EXTRACT] complete")
