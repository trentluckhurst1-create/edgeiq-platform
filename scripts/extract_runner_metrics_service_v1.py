from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "runnerMetricsService.ts"

start = text.index("function confidenceScoreValue(item: EnrichedRunner): number | null {")
end = text.index("\nfunction computedLimitedScore(item: EnrichedRunner): number {", start)

block = text[start:end]

service_prefix = '''import type { CsvRow } from "../utils/edgeiqCsv";
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

'''

service_text = service_prefix + block
service_text = service_text.replace("EnrichedRunner", "EnrichedRunnerLike")
service_text = service_text.replace("function ", "export function ")

# Keep private helpers private.
for name in ["evidenceFlag", "hasMergedEvidencePayload", "hasConnectionPayload", "connectionSourceRow"]:
    service_text = service_text.replace(f"export function {name}", f"function {name}")

service.write_text(service_text, encoding="utf-8")

text = text[:start] + text[end:]

import_line = 'import { betQualityNumeric, comboScoreValue, confidenceScoreValue, connectionScoreValue, dnaScoreValue, factorBandValue, factorRowValue, factorScoreValue, intelligenceScoreValue, jockeyScoreValue, latePowerMetricValue, limitedAdjustedPrice, normalizeGradeLabel, paceMapRole, paceMapXPercent, paceRoleSpeedValue, paceRoleTone, projectedSpdValue, projectionGapValue, projectionRatingValue, scoreTone, sectionalWeaponValue, shortHorseName, sourceBetQualityGrade, trackFitScoreValue, trainerScoreValue } from "../services/runnerMetricsService";'

if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[RUNNER_METRICS_SERVICE_EXTRACT] complete")
