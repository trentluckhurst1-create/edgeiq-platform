export type RunnerProfileStats = {
  resolved_runner_key?: string;
  source_key_method?: string;
  runner?: string;
  normalized_runner?: string;
  latest_runner_name?: string;
  latest_trainer?: string;
  latest_jockey?: string;
  latest_track?: string;
  latest_race_date?: string;
  latest_distance?: string;
  latest_class?: string;
  latest_condition?: string;
  career_starts?: string;
  career_wins?: string;
  career_seconds?: string;
  career_thirds?: string;
  career_places?: string;
  career_win_pct?: string;
  career_place_pct?: string;
  best_track_by_starts?: string;
  latest_track_starts?: string;
  latest_track_wins?: string;
  latest_track_seconds?: string;
  latest_track_thirds?: string;
  latest_track_places?: string;
  latest_track_win_pct?: string;
  latest_track_place_pct?: string;
  best_distance_by_starts?: string;
  latest_distance_starts?: string;
  latest_distance_wins?: string;
  latest_distance_seconds?: string;
  latest_distance_thirds?: string;
  latest_distance_places?: string;
  latest_distance_win_pct?: string;
  latest_distance_place_pct?: string;
  good_starts?: string;
  good_wins?: string;
  good_seconds?: string;
  good_thirds?: string;
  good_places?: string;
  soft_starts?: string;
  soft_wins?: string;
  soft_seconds?: string;
  soft_thirds?: string;
  soft_places?: string;
  heavy_starts?: string;
  heavy_wins?: string;
  heavy_seconds?: string;
  heavy_thirds?: string;
  heavy_places?: string;
  firm_starts?: string;
  firm_wins?: string;
  firm_seconds?: string;
  firm_thirds?: string;
  firm_places?: string;
  synthetic_starts?: string;
  synthetic_wins?: string;
  synthetic_seconds?: string;
  synthetic_thirds?: string;
  synthetic_places?: string;
  latest_track_distance_starts?: string;
  latest_track_distance_wins?: string;
  latest_track_distance_seconds?: string;
  latest_track_distance_thirds?: string;
  latest_track_distance_places?: string;
  latest_class_starts?: string;
  latest_class_wins?: string;
  latest_class_seconds?: string;
  latest_class_thirds?: string;
  latest_class_places?: string;
  latest_class_win_pct?: string;
  latest_class_place_pct?: string;
  latest_jockey_starts?: string;
  latest_jockey_wins?: string;
  latest_jockey_seconds?: string;
  latest_jockey_thirds?: string;
  latest_jockey_places?: string;
  first_up_starts?: string;
  first_up_wins?: string;
  first_up_seconds?: string;
  first_up_thirds?: string;
  first_up_places?: string;
  second_up_starts?: string;
  second_up_wins?: string;
  second_up_seconds?: string;
  second_up_thirds?: string;
  second_up_places?: string;
  third_up_starts?: string;
  third_up_wins?: string;
  third_up_seconds?: string;
  third_up_thirds?: string;
  third_up_places?: string;
  last_5_starts?: string;
  last_5_wins?: string;
  last_5_seconds?: string;
  last_5_thirds?: string;
  last_5_places?: string;
  last_5_avg_finish?: string;
  last_10_starts?: string;
  last_10_wins?: string;
  last_10_seconds?: string;
  last_10_thirds?: string;
  last_10_places?: string;
  last_10_avg_finish?: string;
  avg_sp?: string;
  best_sp?: string;
  last_start_sp?: string;
};

let cachedRows: RunnerProfileStats[] | null = null;
let pendingRows: Promise<RunnerProfileStats[]> | null = null;

export function normaliseRunnerName(value?: string | null) {
  return String(value ?? "")
    .replace(/[\u2018\u2019`\u00b4]/g, "'")
    .trim()
    .replace(/\s+\((NZ|IRE|GB|USA|FR|JPN|AUS|SAF|GER)\)\s*$/i, "")
    .toUpperCase()
    .replace(/[^A-Z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compactRunnerKey(value?: string | null) {
  return normaliseRunnerName(value).replace(/\s+/g, "");
}

export function toNumber(value: any): number | undefined {
  if (value === null || value === undefined || value === "" || value === "-") return undefined;
  const parsed = Number(String(value).replace(/[$,%]/g, ""));
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function hasPositiveNumber(value: any): boolean {
  return (toNumber(value) ?? 0) > 0;
}

export function formatRecord(starts: any, wins: any, places: any): string {
  const startCount = toNumber(starts);
  if (startCount === undefined) return "";
  return `${startCount}: ${toNumber(wins) ?? 0}-${toNumber(places) ?? 0}`;
}

export function formatRaceRecord(starts: any, wins: any, seconds: any, thirds: any): string {
  const startCount = toNumber(starts);
  if (startCount === undefined) return "";
  return `${startCount}: ${toNumber(wins) ?? 0}-${toNumber(seconds) ?? 0}-${toNumber(thirds) ?? 0}`;
}

export function formatPct(value: any): string {
  const numeric = toNumber(value);
  return numeric === undefined ? "" : `${numeric.toFixed(1)}%`;
}

export function formatSp(value: any): string {
  const numeric = toNumber(value);
  if (numeric === undefined || numeric <= 1) return "";
  return `$${numeric.toFixed(2)}`;
}

function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        cell += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      row.push(cell);
      cell = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value.trim() !== "")) rows.push(row);
      row = [];
      cell = "";
      continue;
    }

    cell += char;
  }

  if (cell || row.length) {
    row.push(cell);
    if (row.some((value) => value.trim() !== "")) rows.push(row);
  }

  const [headers = [], ...dataRows] = rows;
  return dataRows.map((values) => {
    const record: Record<string, string> = {};
    headers.forEach((header, index) => {
      record[header.trim()] = (values[index] ?? "").trim();
    });
    return record;
  });
}

export async function loadRunnerProfileStats(): Promise<RunnerProfileStats[]> {
  if (cachedRows) return cachedRows;
  if (pendingRows) return pendingRows;

  pendingRows = fetch("/data/edgeiq_runner_profile_stats_v1.csv")
    .then(async (response) => {
      if (!response.ok) return [];
      const text = await response.text();
      cachedRows = parseCsv(text) as RunnerProfileStats[];
      return cachedRows;
    })
    .catch((error) => {
      console.warn("EDGEIQ runner profile stats feed unavailable", error);
      cachedRows = [];
      return cachedRows;
    })
    .finally(() => {
      pendingRows = null;
    });

  return pendingRows;
}

export function findRunnerProfileStats(
  rows: RunnerProfileStats[],
  runnerName?: string | null,
): RunnerProfileStats | undefined {
  const target = normaliseRunnerName(runnerName);
  const compactTarget = compactRunnerKey(runnerName);
  if (!target) return undefined;

  return rows.find((row) => {
    const candidates = [row.normalized_runner, row.runner, row.latest_runner_name];
    return candidates.some((candidate) => (
      normaliseRunnerName(candidate) === target ||
      compactRunnerKey(candidate) === compactTarget
    ));
  });
}
