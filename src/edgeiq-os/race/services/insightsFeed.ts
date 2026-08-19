export type EngineeringStatus = "current" | "loading" | "empty" | "unavailable" | "stale" | "error";

export type BETA012Card = {
  cardType: string | null;
  title: string | null;
  value: string | null;
  detail: string | null;
  source: string | null;
  sourceTimestamp: string | null;
  sourceConfidence: "official" | "governed" | "derived" | "unavailable" | null;
  rowStatus: string | null;
};

export type BETA012Row = {
  no: string | null;
  horse: string | null;
  key_insight: string | null;
  edge: string | null;
  confidence: string | null;
  source: string | null;
  sourceTimestamp: string | null;
  sourceConfidence: "official" | "governed" | "derived" | "unavailable" | null;
  coverage: string | null;
  supportingEvidence: string | null;
  rowStatus: string | null;
};

export type BETA012ViewModel = {
  workspaceId: "BETA-012";
  meetingKey: string | null;
  raceKey: string | null;
  generatedAt: string | null;
  status: EngineeringStatus;
  cards: BETA012Card[];
  rows: BETA012Row[];
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
  row_kind?: string;
  card_type?: string;
  card_title?: string;
  card_value?: string;
  card_detail?: string;
  no?: string;
  horse?: string;
  key_insight?: string;
  edge?: string;
  confidence?: string;
  source?: string;
  source_timestamp?: string;
  source_confidence?: string;
  coverage?: string;
  supporting_evidence?: string;
  row_status?: string;
};

const URL = "/data/edgeiq_insights_terminal_feed_v1.csv";
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

export async function loadInsightsTerminalFeed(force = false): Promise<TerminalRow[]> {
  if (!force && cachedRows) return cachedRows;
  if (pendingRows) return pendingRows;
  pendingRows = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Insights terminal feed failed with ${response.status}`);
      const rows = parseCsv(await response.text());
      if (rows.length > 10000) {
        console.warn("EDGEiQ rejected oversized insights feed", rows.length);
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

function sourceConfidence(value: string): BETA012Row["sourceConfidence"] {
  const text = value.toLowerCase();
  if (text === "official" || text === "governed" || text === "derived" || text === "unavailable") return text;
  return null;
}

function cardFromTerminal(row: TerminalRow): BETA012Card {
  return {
    cardType: firstText(row.card_type) || null,
    title: firstText(row.card_title) || null,
    value: firstText(row.card_value) || null,
    detail: firstText(row.card_detail) || null,
    source: firstText(row.source) || null,
    sourceTimestamp: firstText(row.source_timestamp, row.generated_at) || null,
    sourceConfidence: sourceConfidence(firstText(row.source_confidence)),
    rowStatus: firstText(row.row_status) || null,
  };
}

function rowFromTerminal(row: TerminalRow): BETA012Row {
  return {
    no: firstText(row.no) || null,
    horse: firstText(row.horse) || null,
    key_insight: firstText(row.key_insight) || null,
    edge: firstText(row.edge) || null,
    confidence: firstText(row.confidence) || null,
    source: firstText(row.source) || null,
    sourceTimestamp: firstText(row.source_timestamp, row.generated_at) || null,
    sourceConfidence: sourceConfidence(firstText(row.source_confidence)),
    coverage: firstText(row.coverage) || null,
    supportingEvidence: firstText(row.supporting_evidence) || null,
    rowStatus: firstText(row.row_status) || null,
  };
}

export function buildInsightsViewModel(
  raceKey: string | null | undefined,
  terminalRows: TerminalRow[],
  meetingKey: string | null = null,
): BETA012ViewModel {
  const selectedRows = terminalRows.filter((row) => firstText(row.race_key) === firstText(raceKey));
  const cards = selectedRows.filter((row) => firstText(row.row_kind) === "card").map(cardFromTerminal);
  const rows = selectedRows.filter((row) => firstText(row.row_kind) === "runner").map(rowFromTerminal);
  const generatedAt = firstText(selectedRows[0]?.generated_at, selectedRows[0]?.source_timestamp) || null;
  const hasEvidence = cards.some((card) => card.value) || rows.some((row) => row.key_insight || row.edge);
  return {
    workspaceId: "BETA-012",
    meetingKey,
    raceKey: firstText(raceKey) || null,
    generatedAt,
    status: rows.length || cards.length ? (hasEvidence ? "current" : "unavailable") : "empty",
    cards,
    rows,
    source: {
      feed: "edgeiq_insights_terminal_feed_v1.csv",
      loadedRows: terminalRows.length,
      matchedRows: selectedRows.length,
      sourceStatus: terminalRows.length ? "Loaded" : "No terminal rows supplied",
    },
  };
}
