import { cleanHorse, cleanTrack, text } from "../utils/edgeiqFormat";
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
