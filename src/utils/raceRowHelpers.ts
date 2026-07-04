import { num, text } from "./edgeiqFormat";
import type { CsvRow } from "./edgeiqCsv";

export type RaceRow = CsvRow;

export function raceDate(row: RaceRow): string {
  return text(row.current_race_date || row.race_date || row.meeting_date || row.date || row.raceDate);
}

export function track(row: RaceRow): string {
  return text(row.track || row.meeting || row.meeting_name);
}

export function raceNo(row: RaceRow): string {
  return text(row.race_no || row.raceNo || row.race_number || row.race);
}

export function horse(row: RaceRow): string {
  return text(row.horse || row.horseName || row.runner || row.runner_name);
}

export function distance(row: RaceRow): string {
  const d = text(row.distance || row.race_distance || row.dist);
  return d ? `${d}m`.replace("mm", "m") : "-";
}

export function raceClass(row: RaceRow): string {
  return text(row.race_class_clean || row.race_class || row.class || row.raceClass || row.grade || row.race_grade) || "-";
}

export function trackCondition(row: RaceRow): string {
  return text(row.track_condition || row.condition || row.going || row.trackCondition) || "-";
}

export function railPosition(row: RaceRow): string {
  return text(row.rail_position || row.rail || row.track_rail || row.railPosition) || "-";
}

export function integer(v: string): number | null {
  const match = text(v).match(/-?\d+/);
  return match ? Number(match[0]) : null;
}

export function firstNum(row: RaceRow | undefined, keys: string[]): number | null {
  if (!row) return null;
  for (const key of keys) {
    const value = num(row[key]);
    if (value !== null) return value;
  }
  return null;
}

export function firstText(row: RaceRow | undefined, keys: string[], fallback = "-"): string {
  if (!row) return fallback;
  for (const key of keys) {
    const value = text(row[key]);
    if (value) return value;
  }
  return fallback;
}
