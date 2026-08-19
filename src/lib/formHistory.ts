export type RunnerHistoryRow = {
  horse?: string;
  horse_key?: string;
  run_date?: string;
  run_date_iso?: string;
  track?: string;
  track_hist?: string;
  distance?: number | string | null;
  class_name?: string;
  finish_pos?: number | string | null;
  run_rating?: number | string | null;
  pos_800?: string | null;
  pos_400?: string | null;
  margin?: string | null;
  sp?: string | null;
  barrier?: string | number | null;
  jockey?: string | null;
  is_official_race?: boolean | string | number | null;
  is_official_race_int?: number | string | null;
  history_status?: string;
};

export type OfficialRun = RunnerHistoryRow & {
  run_rating_num: number | null;
  parsed_run_date: Date | null;
  official: boolean;
};

function cleanText(value: unknown): string {
  if (value === null || value === undefined) return "";
  const s = String(value).trim();
  if (!s) return "";
  const lower = s.toLowerCase();
  if (lower === "nan" || lower === "undefined" || lower === "null") return "";
  return s;
}

export function normaliseHorseKey(value: unknown): string {
  return cleanText(value)
    .toUpperCase()
    .replace(/\(.*?\)/g, "")
    .replace(/[""'`"]/g, "")
    .replace(/[^A-Z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function toNumber(value: unknown): number | null {
  const s = cleanText(value);
  if (!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function isOfficialRace(value: unknown, intValue?: unknown): boolean {
  const intNum = toNumber(intValue);
  if (intNum !== null) return intNum === 1;

  if (value === true) return true;
  if (value === false) return false;

  const s = cleanText(value).toLowerCase();
  return s === "true" || s === "1" || s === "yes" || s === "y";
}

export function parseRunDate(value: unknown, isoValue?: unknown): Date | null {
  const iso = cleanText(isoValue);
  if (iso) {
    const isoDate = new Date(`${iso}T00:00:00`);
    if (!Number.isNaN(isoDate.getTime())) return isoDate;
  }

  const raw = cleanText(value);
  if (!raw) return null;

  const ddMmmYy = raw.match(/^(\d{1,2})([A-Za-z]{3})(\d{2})$/);
  if (ddMmmYy) {
    const [, dd, mmm, yy] = ddMmmYy;
    const monthMap: Record<string, number> = {
      jan: 0,
      feb: 1,
      mar: 2,
      apr: 3,
      may: 4,
      jun: 5,
      jul: 6,
      aug: 7,
      sep: 8,
      oct: 9,
      nov: 10,
      dec: 11,
    };

    const month = monthMap[mmm.toLowerCase()];
    if (month !== undefined) {
      const d = new Date(2000 + Number(yy), month, Number(dd));
      if (!Number.isNaN(d.getTime())) return d;
    }
  }

  const fallback = new Date(raw);
  if (!Number.isNaN(fallback.getTime())) return fallback;

  return null;
}

function rowHorseMatches(row: RunnerHistoryRow, horseName: string): boolean {
  const target = normaliseHorseKey(horseName);
  if (!target) return false;

  const rowHorse = normaliseHorseKey(row.horse);
  const rowHorseKey = normaliseHorseKey(row.horse_key);

  return rowHorse === target || rowHorseKey === target;
}

function isRealRaceClass(className: unknown): boolean {
  const c = cleanText(className).toUpperCase();

  if (!c) return true;

  //  HARD EXCLUSIONS (covers all variations)
  const badPatterns = [
    "JUMP",
    "J/O",
    "J-O",
    "JUMP OUT",
    "JUMPOUT",
    "TRIAL",
    "HEAT",
    "BARRIER",
    "TRACKWORK",
    "EXHIBITION",
    "SCHOOLING",
  ];

  for (const p of badPatterns) {
    if (c.includes(p)) return false;
  }

  return true;
}

export function getOfficialRunsForHorse(
  historyRows: RunnerHistoryRow[],
  horseName: string
): OfficialRun[] {
  if (!Array.isArray(historyRows) || !horseName) return [];

  return historyRows
    .filter((row) => rowHorseMatches(row, horseName))
    .map((row) => {
      const runRating = toNumber(row.run_rating);
      const parsedDate = parseRunDate(row.run_date, row.run_date_iso);
      const official = isOfficialRace(row.is_official_race, row.is_official_race_int);

      return {
        ...row,
        run_rating_num: runRating,
        parsed_run_date: parsedDate,
        official,
      };
    })
    .filter((row) => {
      if (!row.official) return false;
      if (row.run_rating_num === null) return false;
      if (!isRealRaceClass(row.class_name)) return false;
      return true;
    })
    .sort((a, b) => {
      const at = a.parsed_run_date ? a.parsed_run_date.getTime() : 0;
      const bt = b.parsed_run_date ? b.parsed_run_date.getTime() : 0;
      return bt - at;
    });
}

export function getLast5Ratings(historyRows: RunnerHistoryRow[], horseName: string) {
  const officialRuns = getOfficialRunsForHorse(historyRows, horseName);
  const last5 = officialRuns.slice(0, 5);

  const oneLS = last5[0]?.run_rating_num ?? null;
  const twoLS = last5[1]?.run_rating_num ?? null;
  const threeLS = last5[2]?.run_rating_num ?? null;
  const fourLS = last5[3]?.run_rating_num ?? null;
  const fiveLS = last5[4]?.run_rating_num ?? null;

  const avg = (vals: Array<number | null>) => {
    const valid = vals.filter((v): v is number => v !== null);
    if (!valid.length) return null;
    return valid.reduce((a, b) => a + b, 0) / valid.length;
  };

  const ratings = [oneLS, twoLS, threeLS, fourLS, fiveLS].filter(
    (v): v is number => v !== null
  );

  return {
    officialRuns,
    oneLS,
    twoLS,
    threeLS,
    fourLS,
    fiveLS,
    avg3: avg([oneLS, twoLS, threeLS]),
    avg5: avg([oneLS, twoLS, threeLS, fourLS, fiveLS]),
    peak: ratings.length ? Math.max(...ratings) : null,
  };
}


