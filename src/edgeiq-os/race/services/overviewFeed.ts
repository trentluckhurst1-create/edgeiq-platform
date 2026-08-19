export type EngineeringStatus = "current" | "loading" | "empty" | "unavailable" | "stale" | "error";

export type BETA011Row = {
  section: string | null;
  evidence: string | null;
  source: string | null;
  status: string | null;
  open: string | null;
  sourceTimestamp: string | null;
  sourceConfidence: "official" | "governed" | "derived" | "unavailable" | null;
  rowStatus: string | null;
};

export type BETA011ViewModel = {
  workspaceId: "BETA-011";
  meetingKey: string | null;
  raceKey: string | null;
  generatedAt: string | null;
  status: EngineeringStatus;
  rows: BETA011Row[];
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
  race_date?: string;
  track?: string;
  race_no?: string;
  section?: string;
  evidence?: string;
  source?: string;
  status?: string;
  open?: string;
  source_timestamp?: string;
  source_confidence?: string;
  row_status?: string;
};

const URL = "/data/edgeiq_overview_terminal_feed_v1.csv";
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

export async function loadOverviewTerminalFeed(force = false): Promise<TerminalRow[]> {
  if (!force && cachedRows) return cachedRows;
  if (pendingRows) return pendingRows;
  pendingRows = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Overview terminal feed failed with ${response.status}`);
      const rows = parseCsv(await response.text());
      if (rows.length > 10000) {
        console.warn("EDGEiQ rejected oversized overview feed", rows.length);
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

function sourceConfidence(value: string): BETA011Row["sourceConfidence"] {
  const text = value.toLowerCase();
  if (text === "official" || text === "governed" || text === "derived" || text === "unavailable") return text;
  return null;
}

function rowFromTerminal(row: TerminalRow): BETA011Row {
  return {
    section: firstText(row.section) || null,
    evidence: firstText(row.evidence) || null,
    source: firstText(row.source) || null,
    status: firstText(row.status) || null,
    open: firstText(row.open) || null,
    sourceTimestamp: firstText(row.source_timestamp, row.generated_at) || null,
    sourceConfidence: sourceConfidence(firstText(row.source_confidence)),
    rowStatus: firstText(row.row_status) || null,
  };
}

export function buildOverviewViewModel(
  raceKey: string | null | undefined,
  terminalRows: TerminalRow[],
  meetingKey: string | null = null,
): BETA011ViewModel {
  const selectedRows = terminalRows.filter((row) => firstText(row.race_key) === firstText(raceKey));
  const rows = selectedRows.map(rowFromTerminal);
  const generatedAt = firstText(selectedRows[0]?.generated_at, selectedRows[0]?.source_timestamp) || null;
  const hasEvidence = rows.some((row) => row.evidence);
  return {
    workspaceId: "BETA-011",
    meetingKey,
    raceKey: firstText(raceKey) || null,
    generatedAt,
    status: rows.length ? (hasEvidence ? "current" : "unavailable") : "empty",
    rows,
    source: {
      feed: "edgeiq_overview_terminal_feed_v1.csv",
      loadedRows: terminalRows.length,
      matchedRows: selectedRows.length,
      sourceStatus: terminalRows.length ? "Loaded" : "No terminal rows supplied",
    },
  };
}
