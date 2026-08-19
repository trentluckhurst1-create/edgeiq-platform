from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT_DIR = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"GEAR_CHANGES_FINAL_SPEC_V1_{STAMP}"

COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingGearChangesWorkspace.tsx"
MEETING_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "gearChangesFeed.ts"
CSS_FILE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE_FILE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_GEAR_CHANGES_TRACE_V1.md"


COMPONENT_SOURCE = r'''import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import {
  buildMeetingGearChangesViewModel,
  loadGearTerminalFeed,
  type GearChangeRecordViewModel,
  type GearTerminalRow,
  type MeetingGearChangesViewModel,
} from "../services/gearChangesFeed";

type MeetingGearChangesWorkspaceProps = {
  meeting: ThreeDayMeeting;
};

const ALL_RACES = "ALL_RACES";
const ALL_CHANGES = "ALL_CHANGES";

function valueOrUnavailable(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined || value === "") return "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function formatDateTime(value: string | null): string {
  if (!value) return "Unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-AU", {
    day: "2-digit",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Sydney",
  })
    .format(parsed)
    .replace(/\s/g, " ");
}

function SummaryStrip({ model }: { model: MeetingGearChangesViewModel }) {
  const summary = [
    ["TOTAL GEAR CHANGES", model.summary.totalGearChanges],
    ["FIRST TIME", model.summary.firstTime],
    ["GEAR ADDED", model.summary.gearAdded],
    ["GEAR REMOVED", model.summary.gearRemoved],
    ["AFFECTED RUNNERS", model.summary.affectedRunners],
    ["LATEST UPDATE", formatDateTime(model.summary.latestUpdate)],
  ];

  return (
    <section className="eiq-gear-v1-summary-strip" aria-label="Gear changes summary">
      {summary.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{valueOrUnavailable(value)}</strong>
        </div>
      ))}
    </section>
  );
}

function GearFilters({
  model,
  raceFilter,
  changeFilter,
  search,
  onRaceFilter,
  onChangeFilter,
  onSearch,
}: {
  model: MeetingGearChangesViewModel;
  raceFilter: string;
  changeFilter: string;
  search: string;
  onRaceFilter: (value: string) => void;
  onChangeFilter: (value: string) => void;
  onSearch: (value: string) => void;
}) {
  const changes = Array.from(
    new Set(
      model.raceGroups
        .flatMap((group) => group.records.map((record) => record.change))
        .filter((value): value is string => Boolean(value)),
    ),
  );

  return (
    <section className="eiq-gear-v1-filters" aria-label="Gear changes filters">
      <label>
        <span>RACE</span>
        <select value={raceFilter} onChange={(event) => onRaceFilter(event.target.value)}>
          <option value={ALL_RACES}>ALL RACES</option>
          {model.raceGroups.map((group) => (
            <option key={group.raceKey} value={group.raceKey}>
              R{group.raceNumber}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>CHANGE</span>
        <select value={changeFilter} onChange={(event) => onChangeFilter(event.target.value)}>
          <option value={ALL_CHANGES}>ALL CHANGES</option>
          {changes.map((change) => (
            <option key={change} value={change}>
              {change}
            </option>
          ))}
        </select>
      </label>
      <label className="is-search">
        <span>SEARCH HORSE / GEAR</span>
        <input
          value={search}
          placeholder="SEARCH HORSE / GEAR"
          onChange={(event) => onSearch(event.target.value)}
        />
      </label>
    </section>
  );
}

function rowMatchesSearch(record: GearChangeRecordViewModel, search: string): boolean {
  if (!search.trim()) return true;
  const needle = search.trim().toLowerCase();
  return [record.horse, record.trainer, record.jockey, record.change, record.previous, record.today]
    .some((value) => String(value ?? "").toLowerCase().includes(needle));
}

function GearTable({
  model,
  raceFilter,
  changeFilter,
  search,
  selectedKey,
  onSelect,
}: {
  model: MeetingGearChangesViewModel;
  raceFilter: string;
  changeFilter: string;
  search: string;
  selectedKey: string | null;
  onSelect: (record: GearChangeRecordViewModel) => void;
}) {
  const groups = model.raceGroups
    .filter((group) => raceFilter === ALL_RACES || group.raceKey === raceFilter)
    .map((group) => ({
      ...group,
      records: group.records.filter(
        (record) =>
          (changeFilter === ALL_CHANGES || record.change === changeFilter) &&
          rowMatchesSearch(record, search),
      ),
    }))
    .filter((group) => group.records.length > 0);

  if (!groups.length) {
    const message =
      model.status === "error"
        ? "Official gear changes could not be loaded for this meeting."
        : model.status === "unavailable"
          ? "Official gear changes are currently unavailable for this meeting."
          : model.raceGroups.length
            ? "No gear changes match the current filters."
            : "No official gear changes have been received for this meeting.";
    return (
      <section className="eiq-gear-v1-empty" aria-label="Gear changes unavailable state">
        <span>GEAR CHANGES</span>
        <strong>{message}</strong>
        <p>Runner equipment remains governed by official race fields where available.</p>
      </section>
    );
  }

  return (
    <section className="eiq-gear-v1-table-card" aria-label="Race grouped gear changes table">
      {groups.map((group) => (
        <div className="eiq-gear-v1-race-group" key={group.raceKey}>
          <header>
            <strong>R{group.raceNumber}</strong>
            <span>{group.raceName ?? "Race"}</span>
            <small>
              {valueOrUnavailable(group.scheduledTime)} / {group.records.length} gear changes
            </small>
          </header>
          <div className="eiq-gear-v1-table-scroll">
            <table className="eiq-gear-v1-table">
              <thead>
                <tr>
                  <th>RACE</th>
                  <th>NO</th>
                  <th>SILK</th>
                  <th className="is-left">HORSE</th>
                  <th className="is-left">TRAINER</th>
                  <th className="is-left">JOCKEY</th>
                  <th className="is-left">PREVIOUS GEAR</th>
                  <th className="is-left">TODAY GEAR</th>
                  <th className="is-left">CHANGE</th>
                  <th>FIRST TIME</th>
                  <th>UPDATED</th>
                </tr>
              </thead>
              <tbody>
                {group.records.map((record) => (
                  <tr
                    key={record.eventKey}
                    className={record.eventKey === selectedKey ? "is-selected" : ""}
                    onClick={() => onSelect(record)}
                  >
                    <td>R{group.raceNumber}</td>
                    <td>{valueOrUnavailable(record.no)}</td>
                    <td>
                      {record.silk ? <img src={record.silk} alt={`${record.horse} silk`} /> : <span className="eiq-silk-missing" />}
                    </td>
                    <td className="is-left">
                      <strong>{record.horse}</strong>
                    </td>
                    <td className="is-left">{valueOrUnavailable(record.trainer)}</td>
                    <td className="is-left">{valueOrUnavailable(record.jockey)}</td>
                    <td className="is-left">{valueOrUnavailable(record.previous)}</td>
                    <td className="is-left">{valueOrUnavailable(record.today)}</td>
                    <td className="is-left">{valueOrUnavailable(record.change)}</td>
                    <td>
                      <span className={record.firstTime === "YES" ? "eiq-gear-v1-first-time" : ""}>
                        {record.firstTime ?? "No"}
                      </span>
                    </td>
                    <td>{formatDateTime(record.sourceTimestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </section>
  );
}

function DetailPanel({ record }: { record: GearChangeRecordViewModel | null }) {
  if (!record) {
    return (
      <section className="eiq-gear-v1-detail">
        <span>RUNNER GEAR DETAIL</span>
        <strong>Select a gear change.</strong>
        <p>Official equipment details will appear when a supplied runner record is selected.</p>
      </section>
    );
  }

  const rows: Array<[string, string | number | null]> = [
    ["Race", `R${record.raceNumber}`],
    ["Runner", record.horse],
    ["Trainer", record.trainer],
    ["Jockey", record.jockey],
    ["Previous gear", record.previous],
    ["Today gear", record.today],
    ["Official change", record.change],
    ["First time", record.firstTime ?? "No"],
    ["Updated", formatDateTime(record.sourceTimestamp)],
  ];

  return (
    <section className="eiq-gear-v1-detail">
      <span>RUNNER GEAR DETAIL</span>
      <strong>{record.horse}</strong>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{valueOrUnavailable(value)}</dd>
          </div>
        ))}
      </dl>
      {record.historical.length ? (
        <div className="eiq-gear-v1-history-list">
          <h3>Recent supplied gear records</h3>
          {record.historical.map((history, index) => (
            <div key={`${record.eventKey}-history-${index}`}>
              <span>{valueOrUnavailable(history.date)}</span>
              <strong>{valueOrUnavailable(history.today)}</strong>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function MeetingGearChangesWorkspace({ meeting }: MeetingGearChangesWorkspaceProps) {
  const [rows, setRows] = useState<GearTerminalRow[]>([]);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [raceFilter, setRaceFilter] = useState(ALL_RACES);
  const [changeFilter, setChangeFilter] = useState(ALL_CHANGES);
  const [search, setSearch] = useState("");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setSourceError(null);
    loadGearTerminalFeed()
      .then((feedRows) => {
        if (!active) return;
        setRows(feedRows);
      })
      .catch((error) => {
        if (!active) return;
        setRows([]);
        setSourceError(error instanceof Error ? error.message : "Official gear changes could not be loaded");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const model = useMemo(
    () => buildMeetingGearChangesViewModel(meeting, rows, { sourceError }),
    [meeting, rows, sourceError],
  );

  useEffect(() => {
    const allRecords = model.raceGroups.flatMap((group) => group.records);
    if (!allRecords.some((record) => record.eventKey === selectedKey)) {
      setSelectedKey(allRecords[0]?.eventKey ?? null);
    }
  }, [model, selectedKey]);

  const selectedRecord =
    model.raceGroups.flatMap((group) => group.records).find((record) => record.eventKey === selectedKey) ??
    model.raceGroups[0]?.records[0] ??
    null;

  return (
    <div className="eiq-gear-v1">
      <header className="eiq-gear-v1-header">
        <div>
          <span>GEAR CHANGES</span>
          <h2>Official gear changes and equipment updates</h2>
        </div>
        <div>
          <small>Latest official update</small>
          <strong>{formatDateTime(model.summary.latestUpdate)}</strong>
        </div>
      </header>

      <SummaryStrip model={model} />

      <GearFilters
        model={model}
        raceFilter={raceFilter}
        changeFilter={changeFilter}
        search={search}
        onRaceFilter={setRaceFilter}
        onChangeFilter={setChangeFilter}
        onSearch={setSearch}
      />

      {isLoading ? (
        <section className="eiq-gear-v1-empty" aria-label="Gear changes loading state">
          <span>GEAR CHANGES</span>
          <strong>Loading official gear changes.</strong>
          <p>Equipment changes will appear when governed current meeting records are available.</p>
        </section>
      ) : (
        <div className="eiq-gear-v1-grid">
          <GearTable
            model={model}
            raceFilter={raceFilter}
            changeFilter={changeFilter}
            search={search}
            selectedKey={selectedRecord?.eventKey ?? null}
            onSelect={(record) => setSelectedKey(record.eventKey)}
          />
          <DetailPanel record={selectedRecord} />
        </div>
      )}
    </div>
  );
}
'''


SERVICE_SOURCE = r'''import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "./threeDayCatalog";

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
'''


CSS_BLOCK = r'''/* EDGEIQ GEAR CHANGES FINAL SPEC V1 */
.eiq-gear-v1 {
  display: grid;
  gap: 14px;
  min-width: 0;
  color: #172033;
}

.eiq-gear-v1-header,
.eiq-gear-v1-summary-strip,
.eiq-gear-v1-filters,
.eiq-gear-v1-table-card,
.eiq-gear-v1-detail,
.eiq-gear-v1-empty {
  background: #ffffff;
  border: 1px solid #e5e8ee;
  border-radius: 14px;
  box-shadow: none;
  color: #172033;
}

.eiq-gear-v1-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
}

.eiq-gear-v1-header span,
.eiq-gear-v1-detail > span,
.eiq-gear-v1-empty span {
  display: block;
  color: #1f5fd6;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.eiq-gear-v1-header h2 {
  margin: 5px 0 0;
  color: #172033;
  font-size: 22px;
  font-weight: 760;
  letter-spacing: -.025em;
}

.eiq-gear-v1-header > div:last-child {
  display: grid;
  gap: 4px;
  justify-items: end;
  color: #5c6675;
  font-size: 12px;
}

.eiq-gear-v1-header > div:last-child strong {
  color: #172033;
  font-size: 13px;
}

.eiq-gear-v1-filters select,
.eiq-gear-v1-filters input {
  min-height: 32px;
  border: 1px solid #d7dce5;
  border-radius: 9px;
  background: #ffffff;
  color: #172033;
  font-size: 12px;
}

.eiq-gear-v1-summary-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  padding: 12px;
}

.eiq-gear-v1-summary-strip div {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #e5e8ee;
  border-radius: 10px;
  background: #fafbfc;
}

.eiq-gear-v1-summary-strip span,
.eiq-gear-v1-filters span,
.eiq-gear-v1-detail dt {
  display: block;
  color: #7c8798;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.eiq-gear-v1-summary-strip strong {
  display: block;
  margin-top: 4px;
  color: #172033;
  font-size: 15px;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.eiq-gear-v1-filters {
  display: grid;
  grid-template-columns: minmax(145px, .3fr) minmax(190px, .4fr) minmax(280px, 1fr);
  gap: 12px;
  padding: 12px;
}

.eiq-gear-v1-filters label {
  display: grid;
  gap: 5px;
}

.eiq-gear-v1-filters select,
.eiq-gear-v1-filters input {
  width: 100%;
  padding: 0 10px;
}

.eiq-gear-v1-grid {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(340px, 1fr);
  gap: 14px;
  align-items: start;
}

.eiq-gear-v1-table-card {
  display: grid;
  gap: 0;
  overflow: hidden;
}

.eiq-gear-v1-race-group + .eiq-gear-v1-race-group {
  border-top: 1px solid #e5e8ee;
}

.eiq-gear-v1-race-group > header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
  background: #fafbfc;
  border-bottom: 1px solid #e5e8ee;
}

.eiq-gear-v1-race-group > header strong {
  color: #1f5fd6;
  font-size: 13px;
  font-weight: 850;
}

.eiq-gear-v1-race-group > header span {
  color: #172033;
  font-size: 14px;
  font-weight: 780;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eiq-gear-v1-race-group > header small {
  color: #7c8798;
  font-size: 12px;
}

.eiq-gear-v1-table-scroll {
  width: 100%;
  overflow-x: auto;
}

.eiq-gear-v1-table {
  width: 100%;
  min-width: 1120px;
  border-collapse: collapse;
  color: #172033;
}

.eiq-gear-v1-table th {
  height: 36px;
  padding: 0 6px;
  border-bottom: 1px solid #d7dce5;
  color: #5c6675;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: .08em;
  text-align: center;
  text-transform: uppercase;
  white-space: nowrap;
}

.eiq-gear-v1-table td {
  height: 40px;
  padding: 0 6px;
  border-bottom: 1px solid #e5e8ee;
  color: #172033;
  font-size: 12px;
  text-align: center;
  white-space: nowrap;
}

.eiq-gear-v1-table th.is-left,
.eiq-gear-v1-table td.is-left {
  text-align: left;
}

.eiq-gear-v1-table tbody tr {
  cursor: pointer;
}

.eiq-gear-v1-table tbody tr:hover td,
.eiq-gear-v1-table tbody tr.is-selected td {
  background: #eef4ff;
}

.eiq-gear-v1-table td strong {
  color: #172033;
  font-weight: 780;
}

.eiq-gear-v1-table img {
  display: inline-block;
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.eiq-gear-v1-first-time {
  color: #1f5fd6;
  font-weight: 850;
}

.eiq-gear-v1-detail,
.eiq-gear-v1-empty {
  padding: 14px;
}

.eiq-gear-v1-detail strong,
.eiq-gear-v1-empty strong {
  display: block;
  margin-top: 5px;
  color: #172033;
  font-size: 16px;
  font-weight: 780;
}

.eiq-gear-v1-detail p,
.eiq-gear-v1-empty p {
  margin: 8px 0 0;
  color: #5c6675;
  font-size: 13px;
  line-height: 1.45;
}

.eiq-gear-v1-detail dl {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
}

.eiq-gear-v1-detail dl div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e8ee;
}

.eiq-gear-v1-detail dd {
  margin: 0;
  color: #172033;
  font-size: 13px;
  font-weight: 750;
  text-align: right;
}

.eiq-gear-v1-history-list {
  display: grid;
  gap: 7px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #e5e8ee;
}

.eiq-gear-v1-history-list h3 {
  margin: 0 0 4px;
  color: #172033;
  font-size: 13px;
  font-weight: 800;
}

.eiq-gear-v1-history-list div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #5c6675;
  font-size: 12px;
}

.eiq-gear-v1-history-list div strong {
  margin: 0;
  font-size: 12px;
  text-align: right;
}

@media (max-width: 1200px) {
  .eiq-gear-v1-summary-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .eiq-gear-v1-filters,
  .eiq-gear-v1-grid {
    grid-template-columns: 1fr;
  }
}
'''


TRACE = r'''# EDGEiQ Gear Changes Trace V1

Status: implemented as the GEAR CHANGES final-spec tranche.

## Canonical Inputs

- Current meeting and race context: `src/edgeiq-os/race/services/threeDayCatalog.ts`.
- Gear terminal rows: `public/data/edgeiq_gear_terminal_feed_v1.csv`, loaded by `src/edgeiq-os/race/services/gearChangesFeed.ts`.
- Runner identity, number, silk, trainer and jockey: selected `ThreeDayMeeting` runner fields.

## Display Contract

- GEAR CHANGES shows official current gear changes only.
- The workspace displays race, number, silk, horse, trainer, jockey, previous gear where supplied, today gear, official change, first-time indicator where supplied, and update time where supplied.
- No gear impact, positive/negative label, score, price, tip, or confidence is generated in React.
- When no current gear changes are matched, the workspace renders an honest compact unavailable/no-change state.

## Removed Development/Product Leakage

- Removed the GEAR CHANGES fixture query path.
- Removed development fixture rows from the service.
- Removed visible SOURCE columns, DATA FRESHNESS panels, builder/feed labels, and source confidence values from the product UI.

## Legitimate Gaps

- If the governed gear feed does not supply previous gear or update timestamp, EDGEiQ displays `Unavailable` rather than inventing values.
- If the selected meeting has no matched gear rows, EDGEiQ states that no official gear changes have been received for the meeting.
'''


def checkpoint(path: Path) -> None:
  if path.exists():
    target = CHECKPOINT_DIR / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
  start_index = text.find(start)
  if start_index == -1:
    raise RuntimeError(f"Start marker not found: {start}")
  end_index = text.find(end, start_index)
  if end_index == -1:
    raise RuntimeError(f"End marker not found: {end}")
  return text[:start_index] + replacement.rstrip() + "\n\n" + text[end_index:]


def main() -> int:
  for path in [COMPONENT, MEETING_COMPONENT, SERVICE, CSS_FILE]:
    checkpoint(path)

  COMPONENT.write_text(COMPONENT_SOURCE, encoding="utf-8")
  SERVICE.write_text(SERVICE_SOURCE, encoding="utf-8")

  meeting = MEETING_COMPONENT.read_text(encoding="utf-8")
  meeting = meeting.replace(
    '''  const gearFixtureMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqGearFixture") === "1";
''',
    "",
  )
  meeting = meeting.replace(
    '<MeetingGearChangesWorkspace meeting={meeting} fixtureMode={gearFixtureMode} />',
    '<MeetingGearChangesWorkspace meeting={meeting} />',
  )
  MEETING_COMPONENT.write_text(meeting, encoding="utf-8")

  css = CSS_FILE.read_text(encoding="utf-8")
  css = replace_between(
    css,
    "/* EDGEIQ GEAR CHANGES ENGINEERING WORKSPACE V1 */",
    ".eiq-meeting-v1-rail section",
    CSS_BLOCK,
  )
  CSS_FILE.write_text(css, encoding="utf-8")

  TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
  TRACE_FILE.write_text(TRACE, encoding="utf-8")

  print(f"EDGEIQ_GEAR_CHANGES_FINAL_SPEC_PATCH_APPLIED")
  print(f"Checkpoint: {CHECKPOINT_DIR}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
