import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "./threeDayCatalog";

export type GearChangeStatus = "CURRENT" | "UNAVAILABLE";

export type GearChangeRecordViewModel = {
  eventKey: string;
  meetingKey: string;
  raceKey: string;
  raceNumber: number;
  runnerKey: string;
  no: number | null;
  silk: string | null;
  horse: string;
  trainer: string | null;
  jockey: string | null;
  change: string | null;
  previous: string | null;
  today: string | null;
  firstTime: string | null;
  status: GearChangeStatus;
  sourceTimestamp: string | null;
  historical: GearChangeHistoryRecord[];
};

export type GearChangeHistoryRecord = {
  date: string | null;
  track: string | null;
  raceNumber: number | null;
  change: string | null;
  today: string | null;
  removed: string | null;
  firstTime: string | null;
};

export type GearChangesRaceGroupViewModel = {
  raceKey: string;
  raceNumber: number;
  raceName: string | null;
  scheduledTime: string | null;
  records: GearChangeRecordViewModel[];
};

export type MeetingGearChangesViewModel = {
  workspaceId: "BETA-005";
  meetingKey: string;
  generatedAt: string | null;
  status: "loading" | "empty" | "unavailable" | "error" | "current";
  summary: {
    totalGearChanges: number;
    firstTime: number;
    gearAdded: number;
    gearRemoved: number;
    affectedRunners: number;
    latestUpdate: string | null;
  };
  raceGroups: GearChangesRaceGroupViewModel[];
};

export type GearTerminalRow = {
  race_date?: string;
  track?: string;
  race_no?: string;
  race_key?: string;
  runner?: string;
  normalized_runner?: string;
  gear_current?: string;
  gear_changes?: string;
  gear_added?: string;
  gear_removed?: string;
  first_time_gear?: string;
  gear_change_flag?: string;
  source_confidence?: string;
  source_timestamp?: string;
  updated_at?: string;
  generated_at?: string;
};

const URL = "/data/edgeiq_gear_terminal_feed_v1.csv";
let cachedRows: GearTerminalRow[] | null = null;
let pendingRows: Promise<GearTerminalRow[]> | null = null;

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-") return "";
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
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"' && line[i + 1] === '"') {
      value += '"';
      i += 1;
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

function parseCsv(text: string): GearTerminalRow[] {
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

export async function loadGearTerminalFeed(force = false): Promise<GearTerminalRow[]> {
  if (!force && cachedRows) return cachedRows;
  if (pendingRows) return pendingRows;
  pendingRows = fetch(`${URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Official gear changes request failed with ${response.status}`);
      const text = await response.text();
      const rows = parseCsv(text);
      if (rows.length > 10000) {
        console.warn("EDGEiQ rejected oversized gear feed", rows.length);
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

function normaliseRunner(value: unknown): string {
  return String(value ?? "").toUpperCase().replace(/[^A-Z0-9]+/g, "");
}

function raceNo(value: unknown): string {
  const match = String(value ?? "").match(/\d+/);
  return match?.[0] ?? "";
}

function intValue(value: unknown): number | null {
  const text = firstText(value);
  if (!text) return null;
  const num = Number(text.replace(/[^\d.-]/g, ""));
  return Number.isFinite(num) ? Math.trunc(num) : null;
}

function runnerName(runner: ThreeDayRunner): string {
  return firstText(runner.official.runner, runner.source?.horse, runner.source?.runner, "Runner");
}

function trainerName(runner: ThreeDayRunner): string | null {
  return firstText(runner.official.trainer, runner.source?.trainer) || null;
}

function jockeyName(runner: ThreeDayRunner): string | null {
  return firstText(runner.official.jockey, runner.source?.jockey) || null;
}

function runnerNumber(runner: ThreeDayRunner): number | null {
  return intValue(runner.official.no ?? runner.official.number ?? runner.source?.horse_no ?? runner.source?.saddlecloth);
}

function silkUrl(runner: ThreeDayRunner): string | null {
  return firstText(runner.source?.silkUrl, runner.source?.silk_url, runner.source?.mobile_silk_image) || null;
}

function raceTime(race: ThreeDayRace): string | null {
  return firstText(race.raceTime, race.source?.race_time, race.source?.raceTime) || null;
}

function currentRaceKey(meeting: ThreeDayMeeting, race: ThreeDayRace): string {
  return [meeting.date, normaliseTrack(meeting.meeting), String(race.raceNumber)].join("|");
}

function rowRaceKey(row: GearTerminalRow): string {
  return firstText(row.race_key) || [row.race_date, normaliseTrack(row.track), raceNo(row.race_no)].join("|");
}

function isFirstTime(row: GearTerminalRow): boolean {
  return firstText(row.first_time_gear).toUpperCase() === "YES" || /FIRST TIME/i.test(firstText(row.gear_changes));
}

function changeStatus(row: GearTerminalRow): GearChangeStatus {
  if (!firstText(row.gear_changes, row.gear_added, row.gear_removed, row.gear_current)) return "UNAVAILABLE";
  return "CURRENT";
}

function sourceTimestamp(row: GearTerminalRow): string | null {
  return firstText(row.source_timestamp, row.updated_at, row.generated_at) || null;
}

export function buildMeetingGearChangesViewModel(
  meeting: ThreeDayMeeting,
  terminalRows: GearTerminalRow[],
  options: { sourceError?: string | null } = {},
): MeetingGearChangesViewModel {
  const recordsByRace = new Map<string, GearChangeRecordViewModel[]>();

  meeting.races.forEach((race) => {
    const key = currentRaceKey(meeting, race);
    const raceRows = terminalRows.filter((row) => rowRaceKey(row) === key);
    const records: GearChangeRecordViewModel[] = [];
    race.runners.forEach((runner, index) => {
      const name = runnerName(runner);
      const row = raceRows.find((candidate) => normaliseRunner(candidate.runner ?? candidate.normalized_runner) === normaliseRunner(name));
      if (!row || changeStatus(row) === "UNAVAILABLE") return;
      const added = firstText(row.gear_added);
      const removed = firstText(row.gear_removed);
      const today = firstText(row.gear_current, row.gear_changes, added);
      const previous = removed ? removed.replace(/\bOFF\b/gi, "").trim() : "";
      const record: GearChangeRecordViewModel = {
        eventKey: `${key}_${normaliseRunner(name)}_${index}`,
        meetingKey: meeting.meetingKey,
        raceKey: race.raceKey,
        raceNumber: race.raceNumber,
        runnerKey: firstText(runner.source?.runner_key, `${key}_${normaliseRunner(name)}_${index}`),
        no: runnerNumber(runner),
        silk: silkUrl(runner),
        horse: name,
        trainer: trainerName(runner),
        jockey: jockeyName(runner),
        change: firstText(row.gear_changes, added, removed) || null,
        previous: previous || null,
        today: today || null,
        firstTime: isFirstTime(row) ? "YES" : null,
        status: changeStatus(row),
        sourceTimestamp: sourceTimestamp(row),
        historical: terminalRows
          .filter((candidate) => normaliseRunner(candidate.runner ?? candidate.normalized_runner) === normaliseRunner(name))
          .slice(0, 8)
          .map((candidate) => ({
            date: firstText(candidate.race_date) || null,
            track: firstText(candidate.track) || null,
            raceNumber: intValue(candidate.race_no),
            change: firstText(candidate.gear_changes) || null,
            today: firstText(candidate.gear_current) || null,
            removed: firstText(candidate.gear_removed) || null,
            firstTime: isFirstTime(candidate) ? "YES" : null,
          })),
      };
      records.push(record);
    });
    recordsByRace.set(race.raceKey, records);
  });

  const raceGroups = meeting.races
    .map((race) => ({
      raceKey: race.raceKey,
      raceNumber: race.raceNumber,
      raceName: race.raceName || null,
      scheduledTime: raceTime(race),
      records: recordsByRace.get(race.raceKey) ?? [],
    }))
    .filter((group) => group.records.length > 0);
  const allRecords = raceGroups.flatMap((group) => group.records);
  const timestamps = allRecords.map((record) => record.sourceTimestamp).filter((value): value is string => Boolean(value));

  return {
    workspaceId: "BETA-005",
    meetingKey: meeting.meetingKey,
    generatedAt: null,
    status: options.sourceError ? "error" : allRecords.length ? "current" : terminalRows.length ? "empty" : "unavailable",
    summary: {
      totalGearChanges: allRecords.length,
      firstTime: allRecords.filter((record) => record.firstTime === "YES").length,
      gearAdded: allRecords.filter((record) => record.today).length,
      gearRemoved: allRecords.filter((record) => record.previous).length,
      affectedRunners: new Set(allRecords.map((record) => record.runnerKey)).size,
      latestUpdate: timestamps[0] ?? null,
    },
    raceGroups,
  };
}
