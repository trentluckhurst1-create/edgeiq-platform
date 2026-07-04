import type { CsvRow } from "../utils/edgeiqCsv";
import { cleanHorse, cleanHorseLoose, cleanTrack, text } from "../utils/edgeiqFormat";
import { firstText, horse, raceDate, raceNo, track } from "../utils/raceRowHelpers";

type Row = CsvRow;

export function sameRunner(a: Row, b: Row): boolean {
 const aRunnerKey = text(a.runner_key || a.runnerKey);
 const bRunnerKey = text(b.runner_key || b.runnerKey);
 if (aRunnerKey && bRunnerKey && aRunnerKey === bRunnerKey) return true;

 const aRaceKey = text(a.race_key || a.raceKey);
 const bRaceKey = text(b.race_key || b.raceKey);
 const aHorseKey = cleanHorse(a.horse_key || a.horseKey);
 const bHorseKey = cleanHorse(b.horse_key || b.horseKey);
 if (aRaceKey && bRaceKey && aHorseKey && bHorseKey && aRaceKey === bRaceKey && aHorseKey === bHorseKey) return true;

 const aDate = raceDate(a);
 const bDate = raceDate(b);
 if (aDate && bDate && aDate !== bDate) return false;
 if (cleanTrack(track(a)) !== cleanTrack(track(b))) return false;
 if (raceNo(a) !== raceNo(b)) return false;

 const ah = [
 cleanHorse(a.horse_key),
 cleanHorse(a.horse_canon),
 cleanHorse(horse(a)),
 cleanHorseLoose(a.horse_key),
 cleanHorseLoose(a.horse_canon),
 cleanHorseLoose(horse(a)),
 ].filter(Boolean);

 const bh = [
 cleanHorse(b.horse_key),
 cleanHorse(b.horse_canon),
 cleanHorse(horse(b)),
 cleanHorseLoose(b.horse_key),
 cleanHorseLoose(b.horse_canon),
 cleanHorseLoose(horse(b)),
 ].filter(Boolean);

 return ah.some((x) => bh.includes(x));
}

export function findSidecar(rows: Row[], base: Row): Row | undefined {
 return rows.find((row) => sameRunner(row, base));
}

export function findFormEnrichmentSidecar(rows: Row[], base: Row): Row | undefined {
 const baseDate = raceDate(base);
 const baseTrack = cleanTrack(track(base));
 const baseRace = raceNo(base);
 const baseHorse = cleanHorse(horse(base));
 const baseHorseLoose = cleanHorseLoose(firstText(base, ["horse_key"], "")) || cleanHorseLoose(horse(base));

 return rows.find((row) => {
 const dateOk = !baseDate || !raceDate(row) || raceDate(row) === baseDate;
 const trackOk = cleanTrack(track(row)) === baseTrack;
 const raceOk = raceNo(row) === baseRace;
 const horseOk =
 cleanHorse(horse(row)) === baseHorse ||
 cleanHorseLoose(firstText(row, ["horse_key"], "")) === baseHorseLoose ||
 cleanHorseLoose(horse(row)) === baseHorseLoose;
 return dateOk && trackOk && raceOk && horseOk;
 });
}

export function findCommandEnrichmentSidecar(rows: Row[], base: Row): Row | undefined {
 const baseDate = raceDate(base);
 const baseTrack = cleanTrack(track(base));
 const baseRaceNo = raceNo(base);
 const baseHorseStrict = cleanHorse(firstText(base, ["horse_key", "horseKey"], "")) || cleanHorse(horse(base));
 const baseHorseLoose = cleanHorseLoose(horse(base));

 return rows.find((row) => {
 const rowDate = raceDate(row);
 const rowTrack = cleanTrack(track(row));
 const rowRaceNo = raceNo(row);
 const rowHorseStrict = cleanHorse(firstText(row, ["horse_key", "horseKey"], "")) || cleanHorse(horse(row));
 const rowHorseLoose = cleanHorseLoose(horse(row));
 if (baseDate && rowDate && baseDate !== rowDate) return false;
 if (baseTrack && rowTrack && baseTrack !== rowTrack) return false;
 if (baseRaceNo && rowRaceNo && baseRaceNo !== rowRaceNo) return false;
 if (baseHorseStrict && rowHorseStrict && baseHorseStrict === rowHorseStrict) return true;
 return !!baseHorseLoose && !!rowHorseLoose && baseHorseLoose === rowHorseLoose;
 });
}

export function findConnectionSidecar(rows: Row[], base: Row): Row | undefined {
 const baseDate = raceDate(base);
 const baseTrack = cleanTrack(track(base));
 const baseRaceNo = raceNo(base);
 const baseHorseKey = cleanHorse(firstText(base, ["horse_key", "horseKey"], ""));
 const baseHorseStrict = baseHorseKey || cleanHorse(horse(base));
 const baseHorseLoose = cleanHorseLoose(horse(base));

 if (!baseTrack || !baseRaceNo || !(baseHorseStrict || baseHorseLoose)) return findSidecar(rows, base);

 const exact = rows.find((row) => {
 const rowDate = raceDate(row);
 const rowTrack = cleanTrack(track(row));
 const rowRaceNo = raceNo(row);
 const rowHorseKey = cleanHorse(firstText(row, ["horse_key", "horseKey"], ""));
 const rowHorseStrict = rowHorseKey || cleanHorse(horse(row));

 if (!rowTrack || !rowRaceNo || !(rowHorseStrict || cleanHorseLoose(horse(row)))) return false;
 if (baseDate && rowDate && baseDate !== rowDate) return false;
 if (baseTrack !== rowTrack) return false;
 if (baseRaceNo !== rowRaceNo) return false;
 if (baseHorseStrict && rowHorseStrict && baseHorseStrict === rowHorseStrict) return true;
 if (!baseHorseKey || !rowHorseKey) {
 const rowHorseLoose = cleanHorseLoose(horse(row));
 return !!baseHorseLoose && !!rowHorseLoose && baseHorseLoose === rowHorseLoose;
 }
 return false;
 });

 if (exact) return exact;
 if (baseDate && baseTrack && baseRaceNo) return undefined;
 return findSidecar(rows, base);
}

export function findCampaignSidecar(rows: Row[], base: Row): Row | undefined {
 const baseDate = raceDate(base);
 const baseTrack = cleanTrack(track(base));
 const baseRaceNo = raceNo(base);
 const baseHorseKey = cleanHorse(firstText(base, ["horse_key", "horseKey"], ""));
 const baseHorseStrict = baseHorseKey || cleanHorse(horse(base));
 const baseHorseLoose = cleanHorseLoose(horse(base));

 if (!baseTrack || !baseRaceNo || !baseHorseStrict) return undefined;

 return rows.find((row) => {
 const rowDate = text(row.current_race_date || row.race_date || row.meeting_date || row.date || row.raceDate);
 const rowTrack = cleanTrack(track(row));
 const rowRaceNo = raceNo(row);
 const rowHorseKey = cleanHorse(firstText(row, ["horse_key", "horseKey"], ""));
 const rowHorseStrict = rowHorseKey || cleanHorse(horse(row));

 if (!rowTrack || !rowRaceNo || !rowHorseStrict) return false;
 if (baseDate && rowDate && baseDate !== rowDate) return false;
 if (baseTrack !== rowTrack) return false;
 if (baseRaceNo !== rowRaceNo) return false;
 if (baseHorseStrict === rowHorseStrict) return true;

 if (!baseHorseKey || !rowHorseKey) {
 const rowHorseLoose = cleanHorseLoose(horse(row));
 return !!baseHorseLoose && !!rowHorseLoose && baseHorseLoose === rowHorseLoose;
 }

 return false;
 });
}

export function findHiddenGemForRunner(rows: Row[], base: Row): Row | undefined {
 const baseDate = raceDate(base);
 const baseTrack = cleanTrack(track(base));
 const baseRaceNo = raceNo(base);
 const baseHorseKey = cleanHorse(firstText(base, ["horse_key", "horseKey"], ""));
 const baseHorseStrict = baseHorseKey || cleanHorse(horse(base));
 const baseHorseLoose = cleanHorseLoose(horse(base));

 if (!(baseHorseStrict || baseHorseLoose)) return undefined;

 const exactMatch = rows.find((row) => {
 const rowDate = text(row.current_race_date || row.race_date || row.meeting_date || row.date || row.raceDate);
 const rowTrack = cleanTrack(track(row));
 const rowRaceNo = raceNo(row);
 const rowHorseKey = cleanHorse(firstText(row, ["horse_key", "horseKey"], ""));
 const rowHorseStrict = rowHorseKey || cleanHorse(horse(row));

 if (!rowDate || !rowTrack || !rowRaceNo || !rowHorseStrict) return false;
 if (baseDate && rowDate && baseDate !== rowDate) return false;
 if (baseTrack !== rowTrack) return false;
 if (baseRaceNo !== rowRaceNo) return false;
 if (baseHorseStrict && rowHorseStrict && baseHorseStrict === rowHorseStrict) return true;

 if (!baseHorseKey || !rowHorseKey) {
 const rowHorseLoose = cleanHorseLoose(horse(row));
 return !!baseHorseLoose && !!rowHorseLoose && baseHorseLoose === rowHorseLoose;
 }

 return false;
 });

 if (exactMatch) return exactMatch;
 if (baseDate && baseTrack && baseRaceNo) return undefined;

 return rows.find((row) => {
 const rowHorseKey = cleanHorse(firstText(row, ["horse_key", "horseKey"], ""));
 const rowHorseStrict = rowHorseKey || cleanHorse(horse(row));
 if (baseHorseStrict && rowHorseStrict && baseHorseStrict === rowHorseStrict) return true;
 if (!baseHorseKey || !rowHorseKey) {
 const rowHorseLoose = cleanHorseLoose(horse(row));
 return !!baseHorseLoose && !!rowHorseLoose && baseHorseLoose === rowHorseLoose;
 }
 return false;
 });
}

export function findDnaSidecar(rows: Row[], base: Row): Row | undefined {
 const baseDate = raceDate(base);
 const baseTrack = cleanTrack(track(base));
 const baseRaceNo = raceNo(base);
 const baseHorseKey = cleanHorse(firstText(base, ["horse_key", "horseKey"], ""));
 const baseHorseStrict = baseHorseKey || cleanHorse(horse(base));
 const baseHorseLoose = cleanHorseLoose(horse(base));

 if (!baseTrack || !baseRaceNo || !(baseHorseStrict || baseHorseLoose)) return undefined;

 return rows.find((row) => {
 const rowDate = raceDate(row);
 const rowTrack = cleanTrack(track(row));
 const rowRaceNo = raceNo(row);
 const rowHorseKey = cleanHorse(firstText(row, ["horse_key", "horseKey", "horse_key_panel"], ""));
 const rowHorseStrict = rowHorseKey || cleanHorse(horse(row));

 if (!rowTrack || !rowRaceNo || !(rowHorseStrict || cleanHorseLoose(horse(row)))) return false;
 if (baseDate && rowDate && baseDate !== rowDate) return false;
 if (baseTrack !== rowTrack) return false;
 if (baseRaceNo !== rowRaceNo) return false;
 if (baseHorseStrict && rowHorseStrict && baseHorseStrict === rowHorseStrict) return true;

 if (!baseHorseKey || !rowHorseKey) {
 const rowHorseLoose = cleanHorseLoose(horse(row));
 return !!baseHorseLoose && !!rowHorseLoose && baseHorseLoose === rowHorseLoose;
 }

 return false;
 });
}


export function compactKey(value: unknown): string {
 return String(value ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}

export function findSidecarByRaceHorse(rows: Row[], row: Row): Row | undefined {
 const raceKey = String(row.race_key ?? "").trim();
 const horseKey = compactKey(row.horse ?? row.runner ?? row.runner_name);
 if (!horseKey) return undefined;

 return rows.find((side) => {
 const sideRaceKey = String(side.race_key ?? "").trim();
 const sideHorseKey = compactKey(side.horse ?? side.runner ?? side.runner_name);
 if (!sideHorseKey || sideHorseKey !== horseKey) return false;
 if (raceKey && sideRaceKey) return sideRaceKey === raceKey;
 return true;
 });
}

export function findNexusContextualSidecar(rows: Row[], base: Row): Row | undefined {
 const baseRunnerKey = firstText(base, ["runner_key"], "");
 const baseDate = raceDate(base);
 const baseTrack = cleanTrack(track(base));
 const baseRace = raceNo(base).replace(/^R/i, "");
 const baseHorseStrict = cleanHorse(firstText(base, ["horse_key", "horseKey"], "")) || cleanHorse(horse(base));
 const baseHorseLoose = cleanHorseLoose(horse(base));

 return rows.find((row) => {
 const rowRunnerKey = firstText(row, ["runner_key"], "");
 if (baseRunnerKey && rowRunnerKey && baseRunnerKey === rowRunnerKey) return true;

 const rowDate = raceDate(row);
 const dateOk = !baseDate || !rowDate || rowDate === baseDate;
 const trackOk = cleanTrack(track(row)) === baseTrack;
 const raceOk = raceNo(row).replace(/^R/i, "") === baseRace;
 const rowHorseStrict = cleanHorse(firstText(row, ["runner_name", "horse", "runner"], ""));
 const rowHorseLoose = cleanHorseLoose(firstText(row, ["runner_name", "horse", "runner"], ""));
 return dateOk && trackOk && raceOk && (
 (baseHorseStrict && rowHorseStrict === baseHorseStrict) ||
 (baseHorseLoose && rowHorseLoose === baseHorseLoose)
 );
 });
}
