from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "raceSelectionService.ts"
service.write_text(r'''import { cleanHorse, cleanTrack, text } from "../utils/edgeiqFormat";
import type { CsvRow } from "../utils/edgeiqCsv";
import { horse, raceDate, raceNo, track } from "../utils/raceRowHelpers";

export function runnerRowKey(row: CsvRow): string {
  return `${track(row)}|${raceNo(row)}|${cleanHorse(horse(row))}`;
}

export function buildRaceRows(params: {
  runnerRows: CsvRow[];
  selectedTrack: string;
  selectedRaceNo: string;
  selectedRaceDate: string;
  currentRace?: any;
  saddle: (row: CsvRow) => number;
}): CsvRow[] {
  const { runnerRows, selectedTrack, selectedRaceNo, selectedRaceDate, currentRace, saddle } = params;

  let rows = runnerRows;

  if (selectedRaceDate) rows = rows.filter((row) => !raceDate(row) || raceDate(row) === selectedRaceDate);
  if (selectedTrack) rows = rows.filter((row) => cleanTrack(track(row)) === selectedTrack);
  if (selectedRaceNo) rows = rows.filter((row) => raceNo(row) === selectedRaceNo);

  if (!rows.length && currentRace?.track && currentRace?.raceNo) {
    rows = runnerRows.filter(
      (row) =>
        (!selectedRaceDate || !raceDate(row) || raceDate(row) === selectedRaceDate) &&
        cleanTrack(track(row)) === cleanTrack(currentRace.track) &&
        raceNo(row) === text(currentRace.raceNo)
    );
  }

  if (!rows.length && Array.isArray(currentRace?.rows) && currentRace.rows.length) {
    rows = (currentRace.rows as CsvRow[]).filter((row) => {
      const trackMatch = !selectedTrack || cleanTrack(track(row)) === selectedTrack;
      const raceMatch = !selectedRaceNo || raceNo(row) === selectedRaceNo;
      return trackMatch && raceMatch;
    });
  }

  return [...rows].sort((a, b) => saddle(a) - saddle(b));
}
''', encoding="utf-8")

old = ''' const runnerRowKey = (row: Row) => `${track(row)}|${raceNo(row)}|${cleanHorse(horse(row))}`;

 const raceRows = useMemo(() => {
 let rows = runnerRows;

 if (selectedRaceDate) rows = rows.filter((row) => !raceDate(row) || raceDate(row) === selectedRaceDate);
 if (selectedTrack) rows = rows.filter((row) => cleanTrack(track(row)) === selectedTrack);
 if (selectedRaceNo) rows = rows.filter((row) => raceNo(row) === selectedRaceNo);

 if (!rows.length && props.currentRace?.track && props.currentRace?.raceNo) {
 rows = runnerRows.filter(
 (row) =>
 (!selectedRaceDate || !raceDate(row) || raceDate(row) === selectedRaceDate) &&
 cleanTrack(track(row)) === cleanTrack(props.currentRace.track) &&
 raceNo(row) === text(props.currentRace.raceNo)
 );
 }

 if (!rows.length && Array.isArray(props.currentRace?.rows) && props.currentRace.rows.length) {
 rows = (props.currentRace.rows as Row[]).filter((row) => {
 const trackMatch = !selectedTrack || cleanTrack(track(row)) === selectedTrack;
 const raceMatch = !selectedRaceNo || raceNo(row) === selectedRaceNo;
 return trackMatch && raceMatch;
 });
 }

 return [...rows].sort((a, b) => saddle(a) - saddle(b));
 }, [runnerRows, selectedTrack, selectedRaceNo, selectedRaceDate, props.currentRace]);
'''

new = ''' const raceRows = useMemo(() => buildRaceRows({
  runnerRows,
  selectedTrack,
  selectedRaceNo,
  selectedRaceDate,
  currentRace: props.currentRace,
  saddle,
 }), [runnerRows, selectedTrack, selectedRaceNo, selectedRaceDate, props.currentRace]);
'''

if old not in text:
    raise SystemExit("[ERROR] exact raceRows block not found")

text = text.replace(old, new, 1)

import_line = 'import { buildRaceRows, runnerRowKey } from "../services/raceSelectionService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[RACE_SELECTION_EXTRACT] complete")
