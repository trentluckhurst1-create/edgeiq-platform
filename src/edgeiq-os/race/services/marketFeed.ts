import type { ThreeDayRace, ThreeDayRunner } from "./threeDayCatalog";

export type EngineeringStatus = "current" | "loading" | "empty" | "unavailable" | "stale" | "error";

export type BETA010Row = {
  no: string | null;
  horse: string | null;
  epi: string | null;
  market: string | null;
  open: string | null;
  high: string | null;
  low: string | null;
  move: string | null;
  edgeiq_price: string | null;
  edge: string | null;
  status: string | null;
  source: string | null;
  sourceTimestamp: string | null;
  sourceConfidence: "official" | "governed" | "derived" | "unavailable" | null;
  rowStatus: string | null;
  marketAvailabilityStatus: string | null;
  marketSourceStatus: string | null;
  marketObservedAt: string | null;
  marketGeneratedAt: string | null;
  marketAgeMinutes: string | null;
  marketFreshnessStatus: string | null;
  marketIsLive: boolean;
  runner?: ThreeDayRunner | null;
};

export type BETA010ViewModel = {
  workspaceId: "BETA-010";
  meetingKey: string | null;
  raceKey: string | null;
  generatedAt: string | null;
  status: EngineeringStatus;
  rows: BETA010Row[];
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
  no?: string;
  horse?: string;
  epi?: string;
  market?: string;
  open?: string;
  high?: string;
  low?: string;
  move?: string;
  edgeiq_price?: string;
  edge?: string;
  status?: string;
  source?: string;
  source_timestamp?: string;
  source_confidence?: string;
  row_status?: string;
  market_availability_status?: string;
  market_source_status?: string;
  market_observed_at?: string;
  market_generated_at?: string;
  market_age_minutes?: string;
  market_freshness_status?: string;
  market_is_live?: string;
};

const URL = "/data/edgeiq_market_terminal_feed_v1.csv";
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

export async function loadMarketTerminalFeed(force = false): Promise<TerminalRow[]> {
  if (!force && cachedRows) return cachedRows;
  if (pendingRows) return pendingRows;
  pendingRows = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Market terminal feed failed with ${response.status}`);
      const rows = parseCsv(await response.text());
      if (rows.length > 10000) {
        console.warn("EDGEiQ rejected oversized market feed", rows.length);
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

function normalise(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toUpperCase()
    .replace(/\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, "");
}

function runnerName(runner: ThreeDayRunner): string {
  return firstText(runner.official.runner, runner.source?.horseName, runner.source?.runnerName, runner.source?.horse);
}

function runnerNo(runner: ThreeDayRunner, index: number): string {
  return firstText(runner.official.no, runner.official.number, runner.source?.runnerNumber, runner.source?.runner_no, runner.source?.saddlecloth, index + 1);
}

function sourceConfidence(value: string): BETA010Row["sourceConfidence"] {
  const text = value.toLowerCase();
  if (text === "official" || text === "governed" || text === "derived" || text === "unavailable") return text;
  return null;
}

function rowFromTerminal(row: TerminalRow, runner?: ThreeDayRunner | null): BETA010Row {
  return {
    no: firstText(row.no) || null,
    horse: firstText(row.horse) || null,
    epi: firstText(row.epi) || null,
    market: firstText(row.market) || null,
    open: firstText(row.open) || null,
    high: firstText(row.high) || null,
    low: firstText(row.low) || null,
    move: firstText(row.move) || null,
    edgeiq_price: firstText(row.edgeiq_price) || null,
    edge: firstText(row.edge) || null,
    status: firstText(row.status) || null,
    source: firstText(row.source) || null,
    sourceTimestamp: firstText(row.source_timestamp, row.generated_at) || null,
    sourceConfidence: sourceConfidence(firstText(row.source_confidence)),
    rowStatus: firstText(row.row_status) || null,
    marketAvailabilityStatus: firstText(row.market_availability_status) || (firstText(row.market) ? "MARKET_SNAPSHOT" : "MARKET_UNAVAILABLE"),
    marketSourceStatus: firstText(row.market_source_status) || (firstText(row.market) ? "STATIC_SNAPSHOT" : "UNAVAILABLE"),
    marketObservedAt: firstText(row.market_observed_at) || null,
    marketGeneratedAt: firstText(row.market_generated_at, row.generated_at) || null,
    marketAgeMinutes: firstText(row.market_age_minutes) || null,
    marketFreshnessStatus: firstText(row.market_freshness_status) || (firstText(row.market) ? "MARKET_TIMESTAMP_UNKNOWN" : "MARKET_UNAVAILABLE"),
    marketIsLive: firstText(row.market_is_live).toLowerCase() === "true",
    runner: runner ?? null,
  };
}

function matchTerminalRow(race: ThreeDayRace, runner: ThreeDayRunner, rows: TerminalRow[]): TerminalRow | null {
  const no = runnerNo(runner, -1);
  const horse = normalise(runnerName(runner));
  return (
    rows.find((row) => firstText(row.race_key) === race.raceKey && normalise(row.horse) === horse) ??
    rows.find((row) => firstText(row.race_key) === race.raceKey && firstText(row.no) === no) ??
    null
  );
}

function raceRows(race: ThreeDayRace, rows: TerminalRow[]): BETA010Row[] {
  return race.runners.map((runner, index) => {
    const terminal = matchTerminalRow(race, runner, rows);
    if (terminal) return rowFromTerminal(terminal, runner);
    return {
      no: runnerNo(runner, index),
      horse: runnerName(runner) || null,
      epi: null,
      market: null,
      open: null,
      high: null,
      low: null,
      move: null,
      edgeiq_price: null,
      edge: null,
      status: "Pending Market",
      source: "RACE_CONTEXT",
      sourceTimestamp: null,
      sourceConfidence: "official" as const,
      rowStatus: "pending_market",
      marketAvailabilityStatus: "MARKET_UNAVAILABLE",
      marketSourceStatus: "UNAVAILABLE",
      marketObservedAt: null,
      marketGeneratedAt: null,
      marketAgeMinutes: null,
      marketFreshnessStatus: "MARKET_UNAVAILABLE",
      marketIsLive: false,
      runner,
    };
  });
}

export function buildMarketViewModel(
  race: ThreeDayRace,
  terminalRows: TerminalRow[],
  meetingKey: string | null = null,
): BETA010ViewModel {
  const selectedRows = terminalRows.filter((row) => firstText(row.race_key) === race.raceKey);
  const rows = raceRows(race, terminalRows);
  const generatedAt = firstText(selectedRows[0]?.generated_at, selectedRows[0]?.source_timestamp) || null;
  const hasMarket = rows.some((row) => row.market || row.edgeiq_price || row.epi);
  return {
    workspaceId: "BETA-010",
    meetingKey,
    raceKey: race.raceKey,
    generatedAt,
    status: rows.length ? (hasMarket ? "current" : "unavailable") : "empty",
    rows,
    source: {
      feed: "edgeiq_market_terminal_feed_v1.csv",
      loadedRows: terminalRows.length,
      matchedRows: selectedRows.length,
      sourceStatus: terminalRows.length ? "Loaded" : "No terminal rows supplied",
    },
  };
}
