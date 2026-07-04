import type { CsvRow } from "../utils/edgeiqCsv";
import { cleanHorseLoose, cleanTrack, money, num } from "../utils/edgeiqFormat";
import { firstNum, firstText, raceNo, track } from "../utils/raceRowHelpers";

type Row = CsvRow;

export function historyDateText(row: Row | undefined): string {
 return firstText(row, ["run_date_iso", "run_date", "race_date"], "-");
}

export function historyDateValue(row: Row | undefined): number {
 const value = historyDateText(row);
 if (value === "-") return 0;
 const parsed = Date.parse(value);
 return Number.isFinite(parsed) ? parsed : 0;
}

export function historyRunnerLookupKey(row: Row | undefined): string {
 if (!row) return "";
 return (
 cleanHorseLoose(firstText(row, ["horse_key", "horseKey", "runner_key", "runnerKey"], "")) ||
 cleanHorseLoose(firstText(row, ["horse", "horseName", "runner", "runner_name"], ""))
 );
}

export function historyRatingValue(row: Row | undefined): number | null {
 return firstNum(row, ["run_rating_final", "run_rating", "recovered_rating", "performance_rating", "performance_rating_v6_1_research", "rating"]);
}

export function hasHistoricalRating(row: Row | undefined): boolean {
 return historyDateText(row) !== "-" && historyRatingValue(row) !== null;
}

export function ratedHistoryRows(rows: Row[]): Row[] {
 return rows.filter((row) => hasHistoricalRating(row));
}

export function historyTrackText(row: Row | undefined): string {
 return firstText(row, ["track"], "-");
}

export function historyDistanceText(row: Row | undefined): string {
 const distanceValue = firstText(row, ["distance"], "");
 if (!distanceValue || distanceValue === "-") return "-";
 const numericDistance = num(distanceValue);
 if (numericDistance === null) return `${distanceValue}m`.replace("mm", "m");
 return `${numericDistance % 1 === 0 ? numericDistance.toFixed(0) : numericDistance.toFixed(1)}m`;
}

export function historyClassText(row: Row | undefined): string {
 return firstText(row, ["class_name", "race_class_clean", "race_class", "class_name_recovered"], "-");
}

export function historyGoingText(row: Row | undefined): string {
 return firstText(row, ["going", "condition", "track_condition", "condition_recovered"], "-");
}

export function historyFinishText(row: Row | undefined): string {
 return firstText(row, ["finish_pos", "finish_position", "finish_pos_raw"], "-");
}

export function historyBarrierText(row: Row | undefined): string {
 return firstText(row, ["barrier"], "-");
}

export function historyJockeyText(row: Row | undefined): string {
 return firstText(row, ["jockey"], "-");
}

export function historyWeightText(row: Row | undefined): string {
 return firstText(row, ["weight"], "-");
}

export function historyRaceStrengthText(row: Row | undefined): string {
 return firstText(row, ["race_strength", "field_strength", "race_strength_rating"], "-");
}

export function historySpText(row: Row | undefined): string {
 const spValue = firstNum(row, ["sp"]);
 if (spValue !== null && Number.isFinite(spValue) && spValue > 0) return money(spValue);
 const raw = firstText(row, ["sp"], "-");
 if (raw === "-") return "-";
 if (/^\$?\d+(?:\.\d+)?$/.test(raw)) return raw.startsWith("$") ? raw : `$${raw}`;
 return raw;
}

export function formatHistoryDate(value: string): string {
 if (!value || value === "-") return "-";
 const parsed = new Date(value.length === 10 ? `${value}T00:00:00` : value);
 if (Number.isNaN(parsed.getTime())) return value;
 return parsed.toLocaleDateString("en-AU", {
 day: "2-digit",
 month: "short",
 year: "numeric",
 });
}

export function ratingVariance(values: number[]): number | null {
 if (!values.length) return null;
 const average = values.reduce((sum, value) => sum + value, 0) / values.length;
 const variance = values.reduce((sum, value) => sum + (value - average) ** 2, 0) / values.length;
 return Number.isFinite(variance) ? variance : null;
}

export function compactHistoryLine(row: Row): string {
 const parts = [
 formatHistoryDate(historyDateText(row)),
 historyTrackText(row),
 historyDistanceText(row),
 historyClassText(row),
 historyFinishText(row) === "-" ? "" : `Pos ${historyFinishText(row)}`,
 historyRatingValue(row) === null ? "" : `PF ${renderStaticMetricValue(historyRatingValue(row), 1)}`,
 ].filter(Boolean);
 return parts.join(" | ");
}

export function renderStaticMetricValue(value: number | null, digits = 0): string {
 if (value === null || !Number.isFinite(value)) return "-";
 return value.toFixed(digits);
}

export function historyRunKey(row: Row | undefined): string {
 if (!row) return "";
 return [
 cleanHorseLoose(firstText(row, ["horse_key", "horse"], "")),
 historyDateText(row),
 historyTrackText(row),
 historyDistanceText(row),
 historyClassText(row),
 historyFinishText(row),
 firstText(row, ["run_rating"], ""),
 ].join("|");
}

export function historyDetailMergeKey(row: Row | undefined): string {
 if (!row) return "";
 const historyKey = historyRunnerLookupKey(row);
 if (!historyKey) return "";
 return [
 historyKey,
 historyDateText(row),
 cleanTrack(historyTrackText(row)),
 historyRaceNoText(row),
 historyDistanceText(row),
 ].join("|");
}

export function historyDetailMergeKeyLoose(row: Row | undefined): string {
 if (!row) return "";
 const historyKey = historyRunnerLookupKey(row);
 if (!historyKey) return "";
 return [
 historyKey,
 historyDateText(row),
 cleanTrack(historyTrackText(row)),
 historyDistanceText(row),
 ].join("|");
}

export function findHistoryMasterRowsForRunner(
 base: Row,
 historyMasterByHorse: Map<string, Row[]>,
 historyMasterByTrackRaceHorse: Map<string, Row[]>,
): Row[] {
 const horseKey = historyRunnerLookupKey(base);
 const trackRaceKey = horseKey ? [horseKey, cleanTrack(track(base)), raceNo(base)].join("|") : "";

 if (horseKey && historyMasterByHorse.has(horseKey)) {
 return historyMasterByHorse.get(horseKey) || [];
 }
 if (trackRaceKey && historyMasterByTrackRaceHorse.has(trackRaceKey)) {
 return historyMasterByTrackRaceHorse.get(trackRaceKey) || [];
 }
 return [];
}

export function mergeRunnerHistoryRows(
 primaryRows: Row[],
 secondaryRows: Row[],
 tertiaryRows: Row[],
 historyDetailByMergeKey: Map<string, Row>,
 historyDetailByLooseMergeKey: Map<string, Row>,
): Row[] {
 const mergedRows = primaryRows.map((historyRow) => {
 const detailRow =
 historyDetailByMergeKey.get(historyDetailMergeKey(historyRow)) ||
 historyDetailByLooseMergeKey.get(historyDetailMergeKeyLoose(historyRow));
 return detailRow ? { ...detailRow, ...historyRow } : historyRow;
 });

 const combined = mergedRows.length ? [...mergedRows, ...secondaryRows, ...tertiaryRows] : [...secondaryRows, ...tertiaryRows];
 const deduped = new Map<string, Row>();

 combined.forEach((historyRow) => {
 const key =
 historyDetailMergeKey(historyRow) ||
 historyDetailMergeKeyLoose(historyRow) ||
 historyRunKey(historyRow);
 if (!key || deduped.has(key)) return;
 deduped.set(key, historyRow);
 });

 return [...deduped.values()].sort((a, b) => historyDateValue(b) - historyDateValue(a));
}

export function historyRaceNoText(row: Row | undefined): string {
 return firstText(row, ["race_no", "race_number", "race"], "-");
}

export function historyFieldSizeText(row: Row | undefined): string {
 return firstText(row, ["field_size", "fieldSize", "runners"], "-");
}
