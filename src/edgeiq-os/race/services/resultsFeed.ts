import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "./threeDayCatalog";

export type ResultsStatus = "current" | "pending" | "unavailable" | "error";

export type ResultsTerminalRow = {
  meeting_key?: string;
  race_key?: string;
  race_date?: string;
  track?: string;
  race_no?: string;
  time?: string;
  winner?: string;
  jockey?: string;
  trainer?: string;
  sp_tab?: string;
  margin?: string;
  official_time?: string;
  track_condition?: string;
  status?: string;
  open?: string;
  source?: string;
  source_timestamp?: string;
  source_confidence?: string;
};

export type MeetingResultsRaceRow = {
  raceKey: string;
  raceNumber: number;
  race: ThreeDayRace;
  time: string | null;
  winner: string | null;
  jockey: string | null;
  trainer: string | null;
  spTab: string | null;
  margin: string | null;
  track: string | null;
  status: string;
  open: string;
  source: string | null;
  sourceTimestamp: string | null;
  sourceConfidence: string | null;
};

export type IndividualResultRunner = {
  key: string;
  no: string | null;
  silk: string | null;
  horse: string;
  jockey: string | null;
  trainer: string | null;
  barrier: string | null;
  weight: string | null;
  sp: string | null;
  finish: string | null;
  margin: string | null;
  position800: string | null;
  position600: string | null;
  position400: string | null;
  position200: string | null;
  sectional800: string | null;
  sectional600: string | null;
  sectional400: string | null;
  sectional200: string | null;
  sectionalFinish: string | null;
  epi: string | null;
  eri: string | null;
  stewards: string | null;
};

export type IndividualRaceResultViewModel = {
  raceKey: string;
  raceLabel: string;
  raceName: string;
  identity: Array<{ label: string; value: string | null }>;
  snapshot: Array<{ label: string; value: string | null }>;
  status: string;
  runners: IndividualResultRunner[];
  stewardRows: Array<{ horse: string; note: string | null; source: string | null }>;
};

export type MeetingResultsViewModel = {
  workspaceId: "BETA-008";
  meetingKey: string;
  generatedAt: string | null;
  status: ResultsStatus;
  summary: {
    racesCompleted: number;
    officialResults: number;
    pendingResults: number;
    averageFieldSize: string | null;
  };
  rows: MeetingResultsRaceRow[];
  source: {
    feed: string;
    loadedRows: number;
    matchedRows: number;
    sourceStatus: string;
    generatedAt: string | null;
  };
};

const URL = "/data/edgeiq_meeting_results_terminal_feed_v1.csv";
let cachedRows: ResultsTerminalRow[] | null = null;
let pendingRows: Promise<ResultsTerminalRow[]> | null = null;

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text === "—" || text === "-") return "";
  if (["null", "undefined", "none", "n/a", "na"].includes(text.toLowerCase())) return "";
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

function parseCsv(text: string): ResultsTerminalRow[] {
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

export async function loadResultsTerminalFeed(force = false): Promise<ResultsTerminalRow[]> {
  if (!force && cachedRows) return cachedRows;
  if (pendingRows) return pendingRows;
  pendingRows = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Results terminal feed failed with ${response.status}`);
      const rows = parseCsv(await response.text());
      if (rows.length > 10000) {
        console.warn("EDGEiQ rejected oversized results feed", rows.length);
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

function normaliseTrack(value: unknown): string {
  return String(value ?? "")
    .toUpperCase()
    .replace(/\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b/g, " ")
    .replace(/\b(RACECOURSE|RACING|TRACK)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, "");
}

function raceNo(value: unknown): string {
  const match = String(value ?? "").match(/\d+/);
  return match?.[0] ?? "";
}

function matchRow(meeting: ThreeDayMeeting, race: ThreeDayRace, rows: ResultsTerminalRow[]): ResultsTerminalRow | null {
  return (
    rows.find((row) => firstText(row.meeting_key) === meeting.meetingKey && firstText(row.race_key) === race.raceKey) ??
    rows.find((row) => {
      const sameDate = firstText(row.race_date) === meeting.date;
      const sameTrack = normaliseTrack(row.track) === normaliseTrack(meeting.meeting);
      const sameRace = raceNo(row.race_no) === String(race.raceNumber);
      return sameDate && sameTrack && sameRace;
    }) ??
    null
  );
}

function raceTime(race: ThreeDayRace): string | null {
  return firstText(race.raceTime, race.source?.race_time, race.source?.race_time_utc) || null;
}

function statusFromRace(race: ThreeDayRace, row: ResultsTerminalRow | null): string {
  const raw = firstText(race.source?.result_status, row?.status, race.source?.race_status, race.source?.full_status).toUpperCase();
  if (raw.includes("OFFICIAL")) return "OFFICIAL";
  if (raw.includes("UNOFFICIAL")) return "UNOFFICIAL";
  if (raw.includes("ABANDON")) return "ABANDONED";
  if (raw.includes("UPCOMING")) return "UPCOMING";
  if (raw.includes("RESULT")) return "OFFICIAL";
  if (firstText(row?.winner)) return "OFFICIAL";
  return "UPCOMING";
}

function valueOrNull(...values: unknown[]): string | null {
  return firstText(...values) || null;
}

function raceRow(meeting: ThreeDayMeeting, race: ThreeDayRace, rows: ResultsTerminalRow[]): MeetingResultsRaceRow {
  const row = matchRow(meeting, race, rows);
  const status = statusFromRace(race, row);
  return {
    raceKey: race.raceKey,
    raceNumber: race.raceNumber,
    race,
    time: valueOrNull(row?.time, raceTime(race)),
    winner: valueOrNull(row?.winner),
    jockey: valueOrNull(row?.jockey),
    trainer: valueOrNull(row?.trainer),
    spTab: valueOrNull(row?.sp_tab),
    margin: valueOrNull(row?.margin),
    track: valueOrNull(row?.track_condition, race.trackCondition, meeting.trackCondition),
    status,
    open: status === "OFFICIAL" || status === "UNOFFICIAL" ? "Open Race Result" : "Pending result",
    source: valueOrNull(row?.source),
    sourceTimestamp: valueOrNull(row?.source_timestamp, race.source?.built_at, meeting.source?.built_at),
    sourceConfidence: valueOrNull(row?.source_confidence),
  };
}

function runnerNumber(runner: ThreeDayRunner, index: number): string | null {
  return valueOrNull(runner.official.no, runner.official.number, runner.source?.runner_no, runner.source?.saddlecloth, index + 1);
}

function runnerName(runner: ThreeDayRunner): string {
  return firstText(runner.official.runner, runner.source?.horse, runner.source?.horseName, "Runner");
}

function finishText(runner: ThreeDayRunner, index: number): string | null {
  return valueOrNull(runner.source?.finishAbv, runner.source?.finish, runner.source?.position, runner.source?.finishing_position, index + 1);
}

function runnerKey(race: ThreeDayRace, runner: ThreeDayRunner, index: number): string {
  return `${race.raceKey}_${runnerName(runner).replace(/\W+/g, "").toUpperCase()}_${index}`;
}

function buildRunners(race: ThreeDayRace): IndividualResultRunner[] {
  return race.runners.map((runner, index) => ({
    key: runnerKey(race, runner, index),
    no: runnerNumber(runner, index),
    silk: valueOrNull((runner.official as Record<string, unknown>).silkUrl, runner.source?.silkUrl, runner.source?.silk_url),
    horse: runnerName(runner),
    jockey: valueOrNull(runner.official.jockey, runner.source?.jockeyName, runner.source?.jockey),
    trainer: valueOrNull(runner.official.trainer, runner.source?.trainerName, runner.source?.trainer),
    barrier: valueOrNull(runner.official.barrier, runner.source?.barrierNumber, runner.source?.barrier),
    weight: valueOrNull(runner.official.weight, runner.source?.weight),
    sp: valueOrNull(runner.source?.startingPrice, runner.source?.sp, runner.official.market),
    finish: finishText(runner, index),
    margin: valueOrNull(runner.source?.margin, runner.source?.beaten_margin),
    position800: valueOrNull(runner.source?.positionAt800Abv, runner.source?.position_at_800),
    position600: valueOrNull(runner.source?.positionAt600Abv, runner.source?.position_at_600),
    position400: valueOrNull(runner.source?.positionAt400Abv, runner.source?.position_at_400),
    position200: valueOrNull(runner.source?.positionAt200Abv, runner.source?.position_at_200),
    sectional800: valueOrNull(runner.source?.std_800_len),
    sectional600: valueOrNull(runner.source?.std_600_len),
    sectional400: valueOrNull(runner.source?.std_400_len),
    sectional200: valueOrNull(runner.source?.std_200_len),
    sectionalFinish: valueOrNull(runner.source?.std_finish_len),
    epi: valueOrNull(runner.source?.epi_post, runner.source?.epi, runner.source?.rating),
    eri: valueOrNull(runner.source?.eri, race.source?.eri, race.source?.race_rating),
    stewards: valueOrNull(runner.source?.commentStewards, runner.source?.stewards, runner.source?.stewards_note),
  }));
}

export function buildMeetingResultsViewModel(
  sourceMeeting: ThreeDayMeeting,
  feedRows: ResultsTerminalRow[],
  options: { sourceError?: string | null } = {},
): MeetingResultsViewModel {
  const meeting = sourceMeeting;
  const rows = meeting.races.map((race) => raceRow(meeting, race, feedRows));
  const matchedRows = rows.filter((row) => row.source !== null).length;
  const completed = rows.filter((row) => row.status === "OFFICIAL" || row.status === "UNOFFICIAL").length;
  const runnerCounts = meeting.races.map((race) => race.runners.length).filter((count) => count > 0);
  return {
    workspaceId: "BETA-008",
    meetingKey: meeting.meetingKey,
    generatedAt: firstText(feedRows[0]?.source_timestamp, meeting.source?.built_at) || null,
    status: options.sourceError ? "error" : completed ? "current" : "pending",
    summary: {
      racesCompleted: completed,
      officialResults: rows.filter((row) => row.status === "OFFICIAL").length,
      pendingResults: rows.filter((row) => row.status === "PENDING" || row.status === "UPCOMING").length,
      averageFieldSize: runnerCounts.length
        ? (runnerCounts.reduce((total, count) => total + count, 0) / runnerCounts.length).toFixed(1)
        : null,
    },
    rows,
    source: {
      feed: "edgeiq_meeting_results_terminal_feed_v1.csv",
      loadedRows: feedRows.length,
      matchedRows,
      sourceStatus: options.sourceError ?? (feedRows.length ? "Loaded" : "No rows supplied"),
      generatedAt: firstText(feedRows[0]?.source_timestamp) || null,
    },
  };
}

export function buildIndividualRaceResultViewModel(
  meeting: ThreeDayMeeting,
  row: MeetingResultsRaceRow,
): IndividualRaceResultViewModel {
  const workingMeeting = meeting;
  const race = workingMeeting.races.find((item) => item.raceKey === row.raceKey) ?? row.race;
  const runners = buildRunners(race);
  const status = statusFromRace(race, row.source ? {
    status: row.status,
    winner: row.winner ?? "",
  } : null);
  return {
    raceKey: race.raceKey,
    raceLabel: `R${race.raceNumber}`,
    raceName: race.raceName || `Race ${race.raceNumber}`,
    identity: [
      { label: "Distance", value: valueOrNull(race.distance) },
      { label: "Class", value: valueOrNull(race.raceClass) },
      { label: "Track", value: valueOrNull(race.trackCondition, workingMeeting.trackCondition) },
      { label: "Rail", value: valueOrNull(race.rail, workingMeeting.rail) },
      { label: "Field", value: race.runners.length ? String(race.runners.length) : null },
    ],
    snapshot: [
      { label: "Penetrometer Average", value: valueOrNull(race.source?.penetrometer_average) },
      { label: "Prize Money", value: valueOrNull(race.source?.prize_money, race.source?.prizemoney) },
    ],
    status,
    runners,
    stewardRows: runners.map((runner) => ({
      horse: runner.horse,
      note: runner.stewards,
      source: runner.stewards ? "Official stewards report" : null,
    })),
  };
}
