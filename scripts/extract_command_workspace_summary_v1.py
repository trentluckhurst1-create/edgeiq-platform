from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "commandWorkspaceSummaryService.ts"

start = text.index(" const raceRowsForTab = activeRaceRows.filter((item) => !isScratched(item));")
end = text.index("\n return (", start)

block = text[start:end].strip()

names = []
for match in re.finditer(r"const\s+([A-Za-z0-9_]+)\s*=", block):
    name = match.group(1)
    if name not in names:
        names.append(name)

service_text = f'''type Row = Record<string, any>;
type EnrichedRunnerLike = {{
  row: Row;
  bet?: Row;
  ratingsHeatmap?: Row;
  mapEnrichment?: Row;
  [key: string]: any;
}};

export function buildCommandWorkspaceSummary(params: {{
  activeRaceRows: EnrichedRunnerLike[];
  displayExpectedTempo: string;
  fallbackTempoLabel: string;
  bettingConfidence: string;
  trackIntel: Row | undefined;
  header: Row;
  railDisplay: string;
  shellTrack: string;
  selectedRaceNo: string;

  isScratched: (item: EnrichedRunnerLike) => boolean;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  projectionRatingValue: (item: EnrichedRunnerLike) => number | null;
  edgePct: (row: Row, bet?: Row) => number | null;
  livePrice: (row: Row, bet?: Row) => number | null;
  paceMapRole: (item: EnrichedRunnerLike) => string;
  barrier: (row: Row) => string;
  num: (value: unknown) => number | null;
  trackCondition: (row: Row) => string;
  track: (row: Row) => string;
  raceNo: (row: Row) => string;
  raceClass: (row: Row) => string;
}}) {{
 const {{
  activeRaceRows,
  displayExpectedTempo,
  fallbackTempoLabel,
  bettingConfidence,
  trackIntel,
  header,
  railDisplay,
  shellTrack,
  selectedRaceNo,
  isScratched,
  firstNum,
  firstText,
  projectionRatingValue,
  edgePct,
  livePrice,
  paceMapRole,
  barrier,
  num,
  trackCondition,
  track,
  raceNo,
  raceClass,
 }} = params;

 {block}

 return {{
{chr(10).join("  " + name + "," for name in names)}
 }};
}}
'''

service.write_text(service_text, encoding="utf-8")

replacement = " const {\n" + "\n".join(f"  {name}," for name in names) + "\n } = buildCommandWorkspaceSummary({\n" + """  activeRaceRows,
  displayExpectedTempo,
  fallbackTempoLabel,
  bettingConfidence,
  trackIntel,
  header,
  railDisplay,
  shellTrack,
  selectedRaceNo,
  isScratched,
  firstNum,
  firstText,
  projectionRatingValue,
  edgePct,
  livePrice,
  paceMapRole,
  barrier,
  num,
  trackCondition,
  track,
  raceNo,
  raceClass,
 });"""

text = text[:start] + replacement + text[end:]

import_line = 'import { buildCommandWorkspaceSummary } from "../services/commandWorkspaceSummaryService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[COMMAND_WORKSPACE_SUMMARY_EXTRACT] complete")
