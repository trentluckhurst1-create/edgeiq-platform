import { useMemo, useState } from "react";
import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import {
  buildMeetingScratchingsViewModel,
  type MeetingScratchingsViewModel,
  type ScratchingRecordViewModel,
} from "../services/scratchingsFeed";

type MeetingScratchingsWorkspaceProps = {
  meeting: ThreeDayMeeting;
};

const ALL_RACES = "ALL_RACES";
const ALL_STATUS = "ALL_STATUS";

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

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

function rowStatusClass(record: ScratchingRecordViewModel): string {
  if (["SCRATCHED", "LATE_SCRATCHING", "WITHDRAWN", "EMERGENCY_NOT_REQUIRED"].includes(record.status)) {
    return "is-scratched";
  }
  if (record.status === "EMERGENCY_PROMOTED") return "is-promoted";
  return "";
}

function SummaryStrip({ model }: { model: MeetingScratchingsViewModel }) {
  const summary = [
    ["TOTAL SCRATCHINGS", model.summary.totalScratchings],
    ["RACES AFFECTED", model.summary.racesAffected],
    ["EMERGENCIES", model.summary.emergenciesPromoted],
  ];

  return (
    <section className="eiq-scratchings-v1-summary-strip" aria-label="Scratchings summary">
      {summary.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{valueOrUnavailable(value)}</strong>
        </div>
      ))}
    </section>
  );
}

function ScratchingsFilters({
  model,
  raceFilter,
  statusFilter,
  search,
  onRaceFilter,
  onStatusFilter,
  onSearch,
}: {
  model: MeetingScratchingsViewModel;
  raceFilter: string;
  statusFilter: string;
  search: string;
  onRaceFilter: (value: string) => void;
  onStatusFilter: (value: string) => void;
  onSearch: (value: string) => void;
}) {
  const statuses = Array.from(new Set(model.raceGroups.flatMap((group) => group.records.map((record) => record.status))));

  return (
    <section className="eiq-scratchings-v1-filters" aria-label="Scratchings filters">
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
        <span>STATUS</span>
        <select value={statusFilter} onChange={(event) => onStatusFilter(event.target.value)}>
          <option value={ALL_STATUS}>ALL STATUS</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {statusLabel(status)}
            </option>
          ))}
        </select>
      </label>
      <label className="is-search">
        <span>SEARCH HORSE / TRAINER / JOCKEY</span>
        <input
          value={search}
          placeholder="SEARCH HORSE / TRAINER / JOCKEY"
          onChange={(event) => onSearch(event.target.value)}
        />
      </label>
    </section>
  );
}

function rowMatchesSearch(record: ScratchingRecordViewModel, search: string): boolean {
  if (!search.trim()) return true;
  const needle = search.trim().toLowerCase();
  return [record.horse, record.trainer, record.jockey].some((value) => String(value ?? "").toLowerCase().includes(needle));
}

function ScratchingsTable({
  model,
  raceFilter,
  statusFilter,
  search,
}: {
  model: MeetingScratchingsViewModel;
  raceFilter: string;
  statusFilter: string;
  search: string;
}) {
  const groups = model.raceGroups
    .filter((group) => raceFilter === ALL_RACES || group.raceKey === raceFilter)
    .map((group) => ({
      ...group,
      records: group.records.filter(
        (record) =>
          (statusFilter === ALL_STATUS || record.status === statusFilter) && rowMatchesSearch(record, search),
      ),
    }))
    .filter((group) => group.records.length > 0);

  if (!groups.length) {
    const message = model.sourceUnavailable
      ? "Official scratchings data is currently unavailable."
      : model.raceGroups.length
        ? "No scratchings match the current filters."
        : "No official scratchings have been received for this meeting.";
    return (
      <section className="eiq-scratchings-v1-empty" aria-label="Scratchings unavailable state">
        <span>SCRATCHINGS</span>
        <strong>{message}</strong>
        <p>Race fields remain governed by the current official meeting data.</p>
      </section>
    );
  }

  return (
    <section className="eiq-scratchings-v1-table-card" aria-label="Race grouped scratchings table">
      {groups.map((group) => (
        <div className="eiq-scratchings-v1-race-group" key={group.raceKey}>
          <header>
            <strong>R{group.raceNumber}</strong>
            <span>{group.raceName ?? "Race"}</span>
            <small>
              Field {valueOrUnavailable(group.fieldSizeBefore)} to {valueOrUnavailable(group.fieldSizeAfter)}
            </small>
          </header>
          <div className="eiq-scratchings-v1-table-scroll">
            <table className="eiq-scratchings-v1-table">
              <thead>
                <tr>
                  <th>RACE</th>
                  <th>NO</th>
                  <th>SILK</th>
                  <th className="is-left">HORSE</th>
                  <th className="is-left">TRAINER</th>
                  <th className="is-left">JOCKEY</th>
                  <th>STATUS</th>
                  <th>BAR</th>
                  <th>EFFECTIVE BAR</th>
                  <th>FIELD</th>
                  <th>UPDATED</th>
                </tr>
              </thead>
              <tbody>
                {group.records.map((record) => (
                  <tr key={record.eventKey} className={rowStatusClass(record)}>
                    <td>R{group.raceNumber}</td>
                    <td>{valueOrUnavailable(record.runnerNumber)}</td>
                    <td>
                      {record.silk ? <img src={record.silk} alt={`${record.horse} silk`} /> : <span className="eiq-silk-missing" />}
                    </td>
                    <td className="is-left">
                      <strong>{record.horse}</strong>
                    </td>
                    <td className="is-left">{valueOrUnavailable(record.trainer)}</td>
                    <td className="is-left">{valueOrUnavailable(record.jockey)}</td>
                    <td>{statusLabel(record.status)}</td>
                    <td>{valueOrUnavailable(record.originalBarrier)}</td>
                    <td>{valueOrUnavailable(record.effectiveBarrierAfter)}</td>
                    <td>
                      {valueOrUnavailable(record.fieldSizeBefore)} to {valueOrUnavailable(record.fieldSizeAfter)}
                    </td>
                    <td>{record.scratchedAtDisplay}</td>
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

export function MeetingScratchingsWorkspace({ meeting }: MeetingScratchingsWorkspaceProps) {
  const model = useMemo(() => buildMeetingScratchingsViewModel(meeting), [meeting]);
  const [raceFilter, setRaceFilter] = useState(ALL_RACES);
  const [statusFilter, setStatusFilter] = useState(ALL_STATUS);
  const [search, setSearch] = useState("");
  return (
    <div className="eiq-scratchings-v1">
      <header className="eiq-scratchings-v1-header">
        <div>
          <span>SCRATCHINGS</span>
          <h2>Official meeting scratchings</h2>
          <p>Scratched runners remain visible where operationally useful.</p>
        </div>
        <div>
          <small>Latest official update</small>
          <strong>{formatDateTime(model.officialUpdatedAt)}</strong>
          <button type="button" onClick={() => window.location.reload()}>
            REFRESH
          </button>
        </div>
      </header>

      <SummaryStrip model={model} />

      <ScratchingsFilters
        model={model}
        raceFilter={raceFilter}
        statusFilter={statusFilter}
        search={search}
        onRaceFilter={setRaceFilter}
        onStatusFilter={setStatusFilter}
        onSearch={setSearch}
      />

      <ScratchingsTable
        model={model}
        raceFilter={raceFilter}
        statusFilter={statusFilter}
        search={search}
      />
    </div>
  );
}
