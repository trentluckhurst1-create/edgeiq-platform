from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "selectedRunnerProfileService.ts"

start = text.index(" const selectedCareerIntel = selected?.runnerCareer;")
end = text.index("\n const selectedLast5Form = selected ? firstText(selected.drawer", start)

block = text[start:end].strip()

names = []
for match in re.finditer(r"const\s+(selected[A-Za-z0-9_]+)\s*=", block):
    name = match.group(1)
    if name not in names:
        names.append(name)

service_text = f'''type Row = Record<string, any>;
type SelectedRunnerLike = {{
  row: Row;
  runnerCareer?: Row;
  runnerrchetype?: Row;
  runnerTrajectory?: Row;
  runnerProjection?: Row;
  campaign?: Row;
  hiddenGem?: Row;
  formEnrichment?: Row;
  runnerHistory?: Row[];
  runnerProfile?: Row;
  [key: string]: any;
}};

export function buildSelectedRunnerProfile(params: {{
  selected: SelectedRunnerLike | undefined;
  selectedIsScratched: boolean;
  selectedProfileCareerStarts: string;
  selectedProfileCareerWins: string;
  selectedProfileCareerPlaces: string;
  selectedHorserchetype: string;
  selectedDistanceProfile: string;
  selectedCareerPercentile: number | null;
  selectedCareerDaysSincePeak: string;
  selectedPerformanceIntelligenceBand: string;
  selectedHistoricalRun: Row | undefined;

  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  renderMetricValue: (value: number | null, digits?: number, signed?: boolean) => string;
  customerPerformanceNarrative: (value: string) => string;
  performanceIntelligenceLabel: (label: string, actionable?: boolean, historical?: boolean) => string;
  formatCampaignStage: (stage: number | null, label: string) => string;
  formatCampaignWindow: (start: number | null, end: number | null) => string;
  ratedHistoryRows: (rows: Row[]) => Row[];
  historyDateValue: (row: Row | undefined) => number;
  historyRatingValue: (row: Row | undefined) => number | null;
  historyRunKey: (row: Row | undefined) => string;
  formatHistoryDate: (value: string) => string;
  historyDateText: (row: Row | undefined) => string;
  drawerValue: (value: string) => string;
  historyTrackText: (row: Row | undefined) => string;
  historyDistanceText: (row: Row | undefined) => string;
  historyClassText: (row: Row | undefined) => string;
  historyGoingText: (row: Row | undefined) => string;
  historyJockeyText: (row: Row | undefined) => string;
  historyFinishText: (row: Row | undefined) => string;
  historySpText: (row: Row | undefined) => string;
  historyRaceNoText: (row: Row | undefined) => string;
  historyFieldSizeText: (row: Row | undefined) => string;
  historyBarrierText: (row: Row | undefined) => string;
  historyWeightText: (row: Row | undefined) => string;
  historyRaceStrengthText: (row: Row | undefined) => string;
  ordinal: (value: number | null) => string;
  projectionRatingValue: (item: SelectedRunnerLike) => number | null;
  num: (value: unknown) => number | null;
}}) {{
 const {{
  selected,
  selectedIsScratched,
  selectedProfileCareerStarts,
  selectedProfileCareerWins,
  selectedProfileCareerPlaces,
  selectedHorserchetype,
  selectedDistanceProfile,
  selectedCareerPercentile,
  selectedCareerDaysSincePeak,
  selectedPerformanceIntelligenceBand,
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
 }} = params;

 {block}

 return {{
{chr(10).join("  " + name + "," for name in names)}
 }};
}}
'''

service.write_text(service_text, encoding="utf-8")

replacement = " const {\n" + "\n".join(f"  {name}," for name in names) + "\n } = useMemo(() => buildSelectedRunnerProfile({\n" + """  selected,
  selectedIsScratched,
  selectedProfileCareerStarts,
  selectedProfileCareerWins,
  selectedProfileCareerPlaces,
  selectedHorserchetype,
  selectedDistanceProfile,
  selectedCareerPercentile,
  selectedCareerDaysSincePeak,
  selectedPerformanceIntelligenceBand,
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
 }), [selected, selectedIsScratched, selectedProfileCareerStarts, selectedProfileCareerWins, selectedProfileCareerPlaces, selectedHorserchetype, selectedDistanceProfile, selectedCareerPercentile, selectedCareerDaysSincePeak, selectedPerformanceIntelligenceBand, selectedHistoricalRun]);
"""

text = text[:start] + replacement + text[end:]

import_line = 'import { buildSelectedRunnerProfile } from "../services/selectedRunnerProfileService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[SELECTED_RUNNER_PROFILE_EXTRACT] complete")
