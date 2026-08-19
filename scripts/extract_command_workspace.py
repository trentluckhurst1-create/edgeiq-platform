from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

start_marker = '{intelMode === "COMMND" ? (() => {'
end_marker = '{intelMode === "MP" ? ('

start = text.find(start_marker)
if start == -1:
    raise SystemExit("COMMAND start marker not found")

end = text.find(end_marker, start)
if end == -1:
    raise SystemExit("MP marker after COMMAND not found")

block = text[start:end]
inner = block[len(start_marker):]
inner = inner.rsplit("})() : null}", 1)[0].strip()

component = f'''import {{ buildCommandWorkspaceSummary }} from "../../services/commandWorkspaceSummaryService";

type RaceCommandWorkspaceProps = {{
  activeRaceRows: any[];
  displayExpectedTempo: any;
  fallbackTempoLabel: any;
  bettingConfidence: any;
  trackIntel: any;
  header: any;
  railDisplay: any;
  shellTrack: any;
  selectedRaceNo: any;
  isScratched: any;
  firstNum: any;
  firstText: any;
  projectionRatingValue: any;
  edgePct: any;
  livePrice: any;
  paceMapRole: any;
  barrier: any;
  num: any;
  trackCondition: any;
  track: any;
  raceNo: any;
  raceClass: any;
  distance: any;
  activeRaceStartText: any;
  horse: any;
  saddle: any;
  renderMetricValue: any;
  money: any;
  fairPrice: any;
  pct: any;
  sectionalWeaponValue: any;
  runnerRowKey: any;
  setSelectedKey: any;
  setIntelMode: any;
  marketMoney: any;
}};

export function RaceCommandWorkspace({{
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
  distance,
  activeRaceStartText,
  horse,
  saddle,
  renderMetricValue,
  money,
  fairPrice,
  pct,
  sectionalWeaponValue,
  runnerRowKey,
  setSelectedKey,
  setIntelMode,
  marketMoney,
}}: RaceCommandWorkspaceProps) {{
{inner}
}}
'''

Path("src/components/workspaces/RaceCommandWorkspace.tsx").write_text(component, encoding="utf-8")

replacement = '''{intelMode === "COMMND" ? (
<RaceCommandWorkspace
  activeRaceRows={activeRaceRows}
  displayExpectedTempo={displayExpectedTempo}
  fallbackTempoLabel={fallbackTempoLabel}
  bettingConfidence={bettingConfidence}
  trackIntel={trackIntel}
  header={header}
  railDisplay={railDisplay}
  shellTrack={shellTrack}
  selectedRaceNo={selectedRaceNo}
  isScratched={isScratched}
  firstNum={firstNum}
  firstText={firstText}
  projectionRatingValue={projectionRatingValue}
  edgePct={edgePct}
  livePrice={livePrice}
  paceMapRole={paceMapRole}
  barrier={barrier}
  num={num}
  trackCondition={trackCondition}
  track={track}
  raceNo={raceNo}
  raceClass={raceClass}
  distance={distance}
  activeRaceStartText={activeRaceStartText}
  horse={horse}
  saddle={saddle}
  renderMetricValue={renderMetricValue}
  money={money}
  fairPrice={fairPrice}
  pct={pct}
  sectionalWeaponValue={sectionalWeaponValue}
  runnerRowKey={runnerRowKey}
  setSelectedKey={setSelectedKey}
  setIntelMode={setIntelMode}
  marketMoney={marketMoney}
/>
) : null}
'''

text = text[:start] + replacement + text[end:]

import_line = 'import { RaceCommandWorkspace } from "./workspaces/RaceCommandWorkspace";\n'
if import_line.strip() not in text:
    marker = 'import { RaceStatsWorkspace } from "./workspaces/RaceStatsWorkspace";\n'
    if marker in text:
        text = text.replace(marker, import_line + marker, 1)
    else:
        first_import_end = text.find("\n", text.find("import "))
        text = text[:first_import_end + 1] + import_line + text[first_import_end + 1:]

path.write_text(text, encoding="utf-8")
print("[COMMAND_EXTRACT] RaceCommandWorkspace extracted")
