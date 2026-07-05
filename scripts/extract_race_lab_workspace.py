from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

start_marker = '{intelMode === "NEXUS" ? (() => {'
end_marker = '{intelMode === "STATS" ? ('

start = text.find(start_marker)
if start == -1:
    raise SystemExit("NEXUS start marker not found")

end = text.find(end_marker, start)
if end == -1:
    raise SystemExit("STATS marker after NEXUS not found")

block = text[start:end]
inner = block[len(start_marker):]
inner = inner.rsplit("})() : null}", 1)[0].strip()

component = f'''type Row = Record<string, any>;

type RaceLabWorkspaceProps = {{
  selected: any;
  selectedConnectionSource: Row | null | undefined;
  firstText: any;
  text: any;
  num: any;
  pct: any;
  money: any;
  renderMetricValue: any;
  header: Row;
  track: any;
  distance: any;
  raceClass: any;
  selectedConnectionNarrative: string;
  labModule: string;
  setLabModule: any;
  labPriceEngineRows: Row[];
  selectedTrack: string;
  selectedRaceNo: any;
  selectedRaceDate: any;
  cleanTrack: any;
  cleanHorse: any;
  integer: any;
  firstNum: any;
  priceEngineAdjustments: Record<string, number>;
  setPriceEngineAdjustments: any;
}};

export function RaceLabWorkspace({{
  selected,
  selectedConnectionSource,
  firstText,
  text,
  num,
  pct,
  money,
  renderMetricValue,
  header,
  track,
  distance,
  raceClass,
  selectedConnectionNarrative,
  labModule,
  setLabModule,
  labPriceEngineRows,
  selectedTrack,
  selectedRaceNo,
  selectedRaceDate,
  cleanTrack,
  cleanHorse,
  integer,
  firstNum,
  priceEngineAdjustments,
  setPriceEngineAdjustments,
}}: RaceLabWorkspaceProps) {{
{inner}
}}
'''

Path("src/components/workspaces/RaceLabWorkspace.tsx").write_text(component, encoding="utf-8")

replacement = '''{intelMode === "NEXUS" ? (
<RaceLabWorkspace
  selected={selected}
  selectedConnectionSource={selectedConnectionSource}
  firstText={firstText}
  text={text}
  num={num}
  pct={pct}
  money={money}
  renderMetricValue={renderMetricValue}
  header={header}
  track={track}
  distance={distance}
  raceClass={raceClass}
  selectedConnectionNarrative={selectedConnectionNarrative}
  labModule={labModule}
  setLabModule={setLabModule}
  labPriceEngineRows={labPriceEngineRows}
  selectedTrack={selectedTrack}
  selectedRaceNo={selectedRaceNo}
  selectedRaceDate={selectedRaceDate}
  cleanTrack={cleanTrack}
  cleanHorse={cleanHorse}
  integer={integer}
  firstNum={firstNum}
  priceEngineAdjustments={priceEngineAdjustments}
  setPriceEngineAdjustments={setPriceEngineAdjustments}
/>
) : null}
'''

text = text[:start] + replacement + text[end:]

if 'RaceLabWorkspace' not in text.split(start_marker)[0]:
    import_line = 'import { RaceLabWorkspace } from "./workspaces/RaceLabWorkspace";\n'
    marker = 'import { RaceStatsWorkspace } from "./workspaces/RaceStatsWorkspace";\n'
    if marker in text:
        text = text.replace(marker, marker + import_line, 1)
    else:
        first_import_end = text.find("\n", text.find("import "))
        text = text[:first_import_end + 1] + import_line + text[first_import_end + 1:]

path.write_text(text, encoding="utf-8")

print("[LAB_EXTRACT] RaceLabWorkspace extracted")
