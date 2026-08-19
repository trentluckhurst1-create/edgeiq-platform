from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "selectedRunnerCoreService.ts"

start = text.index(" const selectedIsScratched = selected ? isScratched(selected) : false;")
end = text.index("\n const selectedProjectionBand = selected", start)

block = text[start:end].strip()

names = []
for match in re.finditer(r"const\s+(selected[A-Za-z0-9_]+)\s*=", block):
    name = match.group(1)
    if name not in names and name != "selectedConnectionngleLabel":
        names.append(name)

service_text = f'''type Row = Record<string, any>;
type SelectedRunnerLike = {{
  row: Row;
  bet?: Row;
  explainability?: Row;
  customerIntel?: Row;
  intelligenceSummary?: Row;
  raceDayIntelligence?: Row;
  connection?: Row;
  modelRank?: number | null;
  [key: string]: any;
}};

export function buildSelectedRunnerCore(params: {{
  selected: SelectedRunnerLike | undefined;
  topModelRow: SelectedRunnerLike | undefined;
  activeRaceRows: SelectedRunnerLike[];

  displayExpectedTempo: string;
  fallbackRaceShapeLabel: string;
  fallbackTempoLabel: string;
  fallbackPressureLabel: string;
  fallbackPacedvantageLabel: string;
  fallbackRaceShapeNarrative: string;
  raceAssessmentNarrative: string;
  raceClarity: string;

  isScratched: (item: SelectedRunnerLike) => boolean;
  displayBetValue: (item: SelectedRunnerLike) => string;
  displayGradeValue: (item: SelectedRunnerLike) => string;
  limitedScoreValue: (item: SelectedRunnerLike) => string;
  computedLimitedScore: (item: SelectedRunnerLike) => number;
  connectionSourceRow: (item: SelectedRunnerLike) => Row | undefined;
  hasConnectionPayload: (row: Row | undefined) => boolean;
  evidenceFlag: (row: Row | undefined, keys: string[]) => boolean;
  limitedDecisionValue: (item: SelectedRunnerLike) => string;
  displayBetQualityValue: (item: SelectedRunnerLike) => string;

  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  renderMetricValue: (value: number | null, digits?: number, signed?: boolean) => string;
  text: (value: unknown) => string;
}}) {{
 const {{
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
 }} = params;

 {block}

 return {{
{chr(10).join("  " + name + "," for name in names)}
 }};
}}
'''

service.write_text(service_text, encoding="utf-8")

replacement = " const {\n" + "\n".join(f"  {name}," for name in names) + "\n } = useMemo(() => buildSelectedRunnerCore({\n" + """  selected,
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
"""

text = text[:start] + replacement + text[end:]

import_line = 'import { buildSelectedRunnerCore } from "../services/selectedRunnerCoreService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[SELECTED_RUNNER_CORE_EXTRACT] complete")
