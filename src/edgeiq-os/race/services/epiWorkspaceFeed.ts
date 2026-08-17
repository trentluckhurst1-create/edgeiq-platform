export type EngineeringStatus = "current" | "loading" | "empty" | "unavailable" | "stale" | "error";

export type EpiTileClass = "positive" | "neutral" | "negative" | "missing";

export type BETA013StartContext = {
  "DATE": string;
  "TRACK": string;
  "MEETING / RACE": string;
  "DISTANCE": string;
  "CLASS": string;
  "CONDITION": string;
  "BARRIER": string;
  "WEIGHT": string;
  "JOCKEY": string;
  "TRAINER": string;
  "FINISH": string;
  "MARGIN": string;
  "SP": string;
  "EPI": string;
  "ERI": string;
  "8-6": string;
  "6-4": string;
  "4-2": string;
  "2-F": string;
  "SOURCE": string;
  "VERSION / TIMESTAMP": string;
};

export type BETA013Start = {
  key: string;
  label: string;
  value: string | null;
  tileClass: EpiTileClass;
  context: BETA013StartContext | null;
};

export type BETA013Row = {
  no: string | null;
  horse: string | null;
  epr?: string | null;
  current_epi: string | null;
  rank: string | null;
  field_avg: string | null;
  diff: string | null;
  peak_last_10: string | null;
  average_last_10: string | null;
  governed_trend: string | null;
  source: string | null;
  sourceTimestamp: string | null;
  sourceConfidence: "official" | "governed" | "derived" | "unavailable" | null;
  rowStatus: string | null;
  starts: BETA013Start[];
};

export type BETA013ViewModel = {
  workspaceId: "BETA-013";
  meetingKey: string | null;
  raceKey: string | null;
  generatedAt: string | null;
  status: EngineeringStatus;
  rows: BETA013Row[];
  selectedRow: BETA013Row | null;
  source: {
    feed: string;
    loadedRows: number;
    matchedRows: number;
    sourceStatus: string;
  };
};

type TerminalRow = {
  workspace_id?: string;
  meeting_key?: string;
  race_key?: string;
  generated_at?: string;
  no?: string;
  horse?: string;
  epr?: string;
  current_epi?: string;
  rank?: string;
  field_avg?: string;
  diff?: string;
  peak_last_10?: string;
  average_last_10?: string;
  governed_trend?: string;
  source?: string;
  source_timestamp?: string;
  source_confidence?: string;
  row_status?: string;
  [key: string]: string | undefined;
};

const URL = "/data/edgeiq_epi_workspace_terminal_feed_v1.csv";
const START_KEYS = ["start_10", "start_9", "start_8", "start_7", "start_6", "start_5", "start_4", "start_3", "start_2", "start_1"] as const;

let cachedRows: TerminalRow[] | null = null;
let pendingRows: Promise<TerminalRow[]> | null = null;

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text === "null" || text === "undefined" || text.toLowerCase() === "none") return "";
  return text;
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = usable(value);
    if (text) return text;
  }
  return "";
}

function csvCells(line: string): string[] {
  const cells: string[] = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"' && line[index + 1] === '"') {
      value += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      cells.push(value);
      value = "";
    } else {
      value += char;
    }
  }
  cells.push(value);
  return cells;
}

function parseCsv(text: string): TerminalRow[] {
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  if (!lines.length) return [];
  const headers = csvCells(lines[0]).map((header) => header.trim());
  return lines.slice(1).map((line) => {
    const cells = csvCells(line);
    const row: Record<string, string> = {};
    headers.forEach((header, index) => {
      row[header] = cells[index] ?? "";
    });
    return row;
  });
}

export async function loadEpiWorkspaceTerminalFeed(force = false): Promise<TerminalRow[]> {
  if (!force && cachedRows) return cachedRows;
  if (pendingRows) return pendingRows;
  pendingRows = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`EPI workspace feed failed with ${response.status}`);
      const rows = parseCsv(await response.text());
      if (rows.length > 10000) {
        console.warn("EDGEiQ rejected oversized EPI workspace feed", rows.length);
        return [];
      }
      return rows;
    })
    .then((rows) => {
      cachedRows = rows;
      return rows;
    })
    .finally(() => {
      pendingRows = null;
    });
  return pendingRows;
}

function sourceConfidence(value: string): BETA013Row["sourceConfidence"] {
  const text = value.toLowerCase();
  if (text === "official" || text === "governed" || text === "derived" || text === "unavailable") return text;
  return null;
}

function tileClass(value: string): EpiTileClass {
  if (value === "positive" || value === "neutral" || value === "negative" || value === "missing") return value;
  return "missing";
}

function parseContext(value: string): BETA013StartContext | null {
  const text = firstText(value);
  if (!text) return null;
  try {
    const parsed = JSON.parse(text) as BETA013StartContext;
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

function rowFromTerminal(row: TerminalRow): BETA013Row {
  return {
    no: firstText(row.no) || null,
    horse: firstText(row.horse) || null,
    epr: firstText(row.epr, row.current_epi) || null,
    current_epi: firstText(row.epr, row.current_epi) || null,
    rank: firstText(row.rank) || null,
    field_avg: firstText(row.field_avg) || null,
    diff: firstText(row.diff) || null,
    peak_last_10: firstText(row.peak_last_10) || null,
    average_last_10: firstText(row.average_last_10) || null,
    governed_trend: firstText(row.governed_trend) || null,
    source: firstText(row.source) || null,
    sourceTimestamp: firstText(row.source_timestamp, row.generated_at) || null,
    sourceConfidence: sourceConfidence(firstText(row.source_confidence)),
    rowStatus: firstText(row.row_status) || null,
    starts: START_KEYS.map((key) => ({
      key,
      label: key.replace("_", " ").toUpperCase(),
      value: firstText(row[key]) || null,
      tileClass: tileClass(firstText(row[`${key}_class`])),
      context: parseContext(firstText(row[`${key}_context`])),
    })),
  };
}


function normaliseRaceToken(input: unknown): string {
  return firstText(input)
    .toUpperCase()
    .replace(/&/g, " AND ")
    .replace(/[^A-Z0-9]+/g, "|")
    .replace(/^\|+|\|+$/g, "")
    .replace(/\|+/g, "|");
}

function canonicalTrackToken(input: unknown): string {
  const token = normaliseRaceToken(input);

  if (!token) return "";

  // Governed track-family aliases used by the current catalogue/feed.
  if (token.includes("SANDOWN")) return "SANDOWN";
  if (token.includes("MOE")) return "MOE";

  return token
    .split("|")
    .filter(Boolean)
    .filter((part) => !/^\d{4}$/.test(part))
    .filter((part) => !/^\d{1,2}$/.test(part))
    .filter((part) => !/^R\d+$/.test(part))
    .filter((part) => part !== "RACE")
    .filter((part) => part !== "MEETING")
    .join("|");
}

function extractRaceDate(input: unknown): string {
  const raw = firstText(input);
  const match = raw.match(/\b(\d{4}-\d{2}-\d{2})\b/);
  return match?.[1] ?? "";
}

function extractRaceNumber(input: unknown): string {
  const raw = firstText(input).toUpperCase();

  const labelled = raw.match(
    /(?:^|[^A-Z0-9])R(?:ACE)?[\s|:_-]*0*(\d{1,2})(?:$|[^0-9])/,
  );

  if (labelled?.[1]) {
    return String(Number(labelled[1]));
  }

  const normalised = normaliseRaceToken(raw).split("|");

  for (let index = normalised.length - 1; index >= 0; index -= 1) {
    const token = normalised[index];

    if (/^R\d{1,2}$/.test(token)) {
      return String(Number(token.slice(1)));
    }
  }

  return "";
}

function canonicalRaceIdentity(
  raceKey: unknown,
  meetingKey: unknown,
): string {
  const raceText = firstText(raceKey);
  const meetingText = firstText(meetingKey);
  const combined = [meetingText, raceText].filter(Boolean).join("|");

  const date =
    extractRaceDate(raceText) ||
    extractRaceDate(meetingText) ||
    extractRaceDate(combined);

  const raceNumber =
    extractRaceNumber(raceText) ||
    extractRaceNumber(combined);

  const meetingTrackSource = normaliseRaceToken(meetingText)
    .split("|")
    .filter((part) => !/^\d{4}$/.test(part))
    .filter((part) => !/^\d{2}$/.test(part))
    .filter((part) => !/^\d{1,2}$/.test(part))
    .filter((part) => !/^R\d+$/.test(part))
    .join("|");

  const raceTrackSource = normaliseRaceToken(raceText)
    .split("|")
    .filter((part) => !/^\d{4}$/.test(part))
    .filter((part) => !/^\d{2}$/.test(part))
    .filter((part) => !/^\d{1,2}$/.test(part))
    .filter((part) => !/^R\d+$/.test(part))
    .join("|");

  const track =
    canonicalTrackToken(meetingTrackSource) ||
    canonicalTrackToken(raceTrackSource);

  if (!date || !track || !raceNumber) return "";

  return `${date}|${track}|R${raceNumber}`;
}

function canonicalTerminalRaceIdentity(row: TerminalRow): string {
  const directKey = firstText(row.race_key);

  const directDate = extractRaceDate(directKey);
  const directRaceNumber = extractRaceNumber(directKey);

  const directParts = normaliseRaceToken(directKey).split("|");
  const directTrack = directParts
    .filter((part) => !/^\d{4}$/.test(part))
    .filter((part) => !/^\d{2}$/.test(part))
    .filter((part) => !/^\d{1,2}$/.test(part))
    .filter((part) => !/^R\d+$/.test(part))
    .join("|");

  const rowDate = firstText(
    (row as TerminalRow & { race_date?: string }).race_date,
  );

  const rowTrack = firstText(
    (row as TerminalRow & { track?: string }).track,
  );

  const rowRaceNumber = firstText(
    (row as TerminalRow & { race_no?: string }).race_no,
  ).replace(/^R/i, "");

  const date = rowDate || directDate;
  const track =
    canonicalTrackToken(rowTrack) ||
    canonicalTrackToken(directTrack);
  const raceNumber = rowRaceNumber || directRaceNumber;

  if (!date || !track || !raceNumber) return "";

  return `${date}|${track}|R${Number(raceNumber)}`;
}

export function buildEpiWorkspaceViewModel(
  raceKey: string | null | undefined,
  terminalRows: TerminalRow[],
  meetingKey: string | null = null,
): BETA013ViewModel {
  const incomingIdentity = canonicalRaceIdentity(raceKey, meetingKey);

  const selectedRows = terminalRows.filter((row) => {
    const exactMatch =
      firstText(row.race_key) === firstText(raceKey);

    if (exactMatch) return true;
    if (!incomingIdentity) return false;

    const rowIdentity = canonicalTerminalRaceIdentity(row);
    return Boolean(rowIdentity && rowIdentity === incomingIdentity);
  });
  const rows = selectedRows.map(rowFromTerminal);
  const generatedAt = firstText(selectedRows[0]?.generated_at, selectedRows[0]?.source_timestamp) || null;
  const hasCurrent = rows.some((row) => row.current_epi || row.starts.some((start) => start.value));
  return {
    workspaceId: "BETA-013",
    meetingKey,
    raceKey: firstText(raceKey) || null,
    generatedAt,
    status: rows.length ? (hasCurrent ? "current" : "unavailable") : "empty",
    rows,
    selectedRow: rows.find((row) => row.current_epi || row.starts.some((start) => start.value)) ?? rows[0] ?? null,
    source: {
      feed: "edgeiq_epi_workspace_terminal_feed_v1.csv",
      loadedRows: terminalRows.length,
      matchedRows: selectedRows.length,
      sourceStatus: terminalRows.length ? "Loaded" : "No terminal rows supplied",
    },
  };
}
