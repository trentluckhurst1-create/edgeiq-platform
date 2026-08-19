import { useEffect, useMemo, useState } from "react";
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
