import type { ThreeDayRace, ThreeDayRunner } from "./threeDayCatalog";

export type EngineeringStatus = "current" | "loading" | "empty" | "unavailable" | "stale" | "error";

export type BETA009Row = {
  no: string | null;
  horse: string | null;
  barrier: string | null;
  effective_barrier: string | null;
  run_style: string | null;
  early_speed: string | null;
  projected_position: string | null;
  source: string | null;
  sourceTimestamp: string | null;
  sourceConfidence: "official" | "governed" | "derived" | "unavailable" | null;
  rowStatus: string | null;
  runner?: ThreeDayRunner | null;
};

export type BETA009ViewModel = {
  workspaceId: "BETA-009";
  meetingKey: string | null;
  raceKey: string | null;
  generatedAt: string | null;
  status: EngineeringStatus;
  rows: BETA009Row[];
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
  barrier?: string;
  effective_barrier?: string;
  run_style?: string;
  early_speed?: string;
  projected_position?: string;
  source?: string;
  source_timestamp?: string;
  source_confidence?: string;
  row_status?: string;
};

const URL = "/data/edgeiq_map_terminal_feed_v1.csv";
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

export async function loadMapTerminalFeed(force = false): Promise<TerminalRow[]> {
  if (!force && cachedRows) return cachedRows;
  if (pendingRows) return pendingRows;
  pendingRows = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Map terminal feed failed with ${response.status}`);
      const rows = parseCsv(await response.text());
      if (rows.length > 10000) {
        console.warn("EDGEiQ rejected oversized map feed", rows.length);
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

function isScratchedRunner(runner: ThreeDayRunner): boolean {
  const official = runner.official as Record<string, unknown>;
  const source = runner.source ?? {};
  const statusText = [
    official.status,
    source.status,
    source.runnerStatus,
    source.scratchingStatus,
    source.scratched,
    source.market,
    source.fixedOdds,
    source.price,
  ]
    .map((value) => String(value ?? "").toUpperCase())
    .join(" ");
  return statusText.includes("SCRATCH");
}

function sourceConfidence(value: string): BETA009Row["sourceConfidence"] {
  const text = value.toLowerCase();
  if (text === "official" || text === "governed" || text === "derived" || text === "unavailable") return text;
  return null;
}

function rowFromTerminal(row: TerminalRow, runner?: ThreeDayRunner | null): BETA009Row {
  return {
    no: firstText(row.no) || null,
    horse: firstText(row.horse) || null,
    barrier: firstText(row.barrier) || null,
    effective_barrier: firstText(row.effective_barrier) || null,
    run_style: firstText(row.run_style) || null,
    early_speed: firstText(row.early_speed) || null,
    projected_position: firstText(row.projected_position) || null,
    source: firstText(row.source) || null,
    sourceTimestamp: firstText(row.source_timestamp, row.generated_at) || null,
    sourceConfidence: sourceConfidence(firstText(row.source_confidence)),
    rowStatus: firstText(row.row_status) || null,
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

function effectiveBarrierValue(row: BETA009Row): number {
  const parsed = Number(row.effective_barrier ?? row.barrier ?? "");
  return Number.isFinite(parsed) ? parsed : -1;
}

function raceRows(race: ThreeDayRace, rows: TerminalRow[]): BETA009Row[] {
  const activeRunners = race.runners.filter((runner) => !isScratchedRunner(runner));
  const shaped = activeRunners.map((runner, index) => {
    const terminal = matchTerminalRow(race, runner, rows);
    if (terminal) return rowFromTerminal(terminal, runner);
    return {
      no: runnerNo(runner, index),
      horse: runnerName(runner) || null,
      barrier: firstText(runner.official.barrier, runner.source?.barrierNumber, runner.source?.barrier) || null,
      effective_barrier: firstText(runner.official.barrier, runner.source?.barrierNumber, runner.source?.barrier) || null,
      run_style: null,
      early_speed: null,
      projected_position: null,
      source: "RACE_CONTEXT",
      sourceTimestamp: null,
      sourceConfidence: "official" as const,
      rowStatus: "pending_map_evidence",
      runner,
    };
  });
  return shaped.sort((a, b) => {
    const barrierDiff = effectiveBarrierValue(b) - effectiveBarrierValue(a);
    if (barrierDiff !== 0) return barrierDiff;
    return Number(a.no ?? 999) - Number(b.no ?? 999);
  });
}

export function buildMapViewModel(
  race: ThreeDayRace,
  terminalRows: TerminalRow[],
  meetingKey: string | null = null,
): BETA009ViewModel {
  const selectedRows = terminalRows.filter((row) => firstText(row.race_key) === race.raceKey);
  const rows = raceRows(race, terminalRows);
  const generatedAt = firstText(selectedRows[0]?.generated_at, selectedRows[0]?.source_timestamp) || null;
  const hasGovernedEvidence = rows.some((row) => row.run_style || row.early_speed || row.projected_position);
  return {
    workspaceId: "BETA-009",
    meetingKey,
    raceKey: race.raceKey,
    generatedAt,
    status: rows.length ? (hasGovernedEvidence ? "current" : "unavailable") : "empty",
    rows,
    source: {
      feed: "edgeiq_map_terminal_feed_v1.csv",
      loadedRows: terminalRows.length,
      matchedRows: selectedRows.length,
      sourceStatus: terminalRows.length ? "Loaded" : "No terminal rows supplied",
    },
  };
}
