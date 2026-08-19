import { useEffect, useMemo, useState } from "react";
import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { marketDisplayStatus } from "../../design-system/presentation";
import {
  buildMarketViewModel,
  loadMarketTerminalFeed,
  type BETA010Row,
  type BETA010ViewModel,
} from "../services/marketFeed";

type RaceBook = Record<string, unknown>;
type RaceFieldRunner = ThreeDayRunner & Record<string, unknown>;

type MarketWorkspaceProps = {
  raceBook: RaceBook;
  field?: RaceFieldRunner[];
  meetingKey?: string | null;
};

function readValue(record: unknown, path: string[]): unknown {
  let current = record;
  for (const key of path) {
    if (current && typeof current === "object" && key in current) {
      current = (current as Record<string, unknown>)[key];
    } else {
      return undefined;
    }
  }
  return current;
}

function text(value: unknown): string {
  if (value === null || value === undefined) return "";
  const output = String(value).trim();
  return output === "-" ? "" : output;
}

function fieldFromRaceBook(raceBook: RaceBook): RaceFieldRunner[] {
  const value = readValue(raceBook, ["field"]);
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is RaceFieldRunner => Boolean(entry) && typeof entry === "object");
}

function officialRace(raceBook: RaceBook, field: RaceFieldRunner[]): ThreeDayRace {
  const official = (raceBook.official ?? {}) as Record<string, unknown>;
  const source = (raceBook.source ?? {}) as Record<string, unknown>;
  return {
    raceKey: text(official.raceKey) || text(source.raceKey) || `${text(official.meeting)}|R${text(official.raceNumber)}`,
    raceNumber: Number(text(official.raceNumber) || text(source.raceNumber) || 0),
    raceName: text(official.raceName) || text(source.raceName) || `Race ${text(official.raceNumber)}`,
    distance: text(official.distance) || null,
    raceClass: text(official.raceClass) || null,
    raceTime: text(official.raceTime) || null,
    trackCondition: text(official.trackCondition) || text(official.condition) || null,
    rail: text(official.rail) || null,
    runners: field,
    source,
  };
}

function value(rowValue: string | null): string {
  return rowValue && rowValue.trim() ? rowValue : "";
}

function price(rowValue: string | null): string {
  const raw = value(rowValue);
  if (!raw) return "";
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? `$${parsed.toFixed(parsed < 10 ? 2 : 0)}` : raw;
}

function moveClass(row: BETA010Row): string {
  const parsed = Number(value(row.move).replace(/[%+]/g, ""));
  if (!Number.isFinite(parsed) || parsed === 0) return "is-neutral";
  return parsed < 0 ? "is-positive" : "is-negative";
}
function flucText(row: BETA010Row): string {
  const raw = value(row.move);
  if (!row.marketIsLive || !raw) return "Movement not published";
  const parsed = Number(raw.replace(/[%+]/g, ""));
  if (!Number.isFinite(parsed) || parsed === 0) return "Movement not published";
  return `${parsed > 0 ? "+" : ""}${parsed.toFixed(1)}%`;
}
function marketDisclosureLabel(row: BETA010Row): string {
  if (row.marketIsLive) return "Market Available";
  if (row.marketAvailabilityStatus === "MARKET_SNAPSHOT") return "Market Available";
  if (row.marketFreshnessStatus === "MARKET_STALE") return "Market Closed";
  return "Awaiting Feed";
}
function statusLabel(row: BETA010Row): string {
  return marketDisplayStatus(row.status, Boolean(row.market || row.edgeiq_price), row.rowStatus === "scratched");
}

function edgeClass(row: BETA010Row): string {
  const raw = value(row.edge);
  if (!raw) return "is-neutral";
  return raw.startsWith("+") ? "is-positive" : raw.startsWith("-") ? "is-negative" : "is-neutral";
}

function MarketReadPanel({ viewModel }: { viewModel: BETA010ViewModel }) {
  const pricedCount = viewModel.rows.filter((row) => row.market || row.edgeiq_price).length;
  const pendingCount = Math.max(0, viewModel.rows.length - pricedCount);

  return (
    <aside className="eiq-market-v1-side">
      <section className="eiq-market-v1-panel">
        <div className="eiq-market-v1-panel__title"><span>Market Read</span></div>
        <dl className="eiq-market-v1-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Priced</dt><dd>{pricedCount}</dd></div>
          <div><dt>Pending</dt><dd>{pendingCount}</dd></div>
        </dl>
      </section>
      <section className="eiq-market-v1-panel">
        <div className="eiq-market-v1-panel__title"><span>Market Note</span></div>
        <p className="eiq-market-v1-copy">
          Market prices use the governed observation feed. Movement appears only where timestamp-safe fluctuation evidence is published.
        </p>
      </section>
    </aside>
  );
}

function MarketTable({ rows }: { rows: BETA010Row[] }) {
  return (
    <section className="eiq-market-v1-panel eiq-market-v1-table-panel">
      <div className="eiq-market-v1-panel__title">
        <span>Market Board</span>
        <small>NO / RUNNER / EDGEIQ / MARKET / FAIR / EDGE / FLUCTUATION / STATUS</small>
      </div>
      <div className="eiq-market-v1-table-scroll">
        <table className="eiq-market-v1-table">
          <thead>
            <tr>
              <th>NO</th>
              <th>RUNNER</th>
              <th>EDGEIQ</th>
              <th>MARKET</th>
              <th>FAIR</th>
              <th>EDGE</th>
              <th>FLUCTUATION</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${value(row.no)}-${value(row.horse)}`} className={row.rowStatus === "scratched" ? "is-scratched" : ""}>
                <td>{value(row.no)}</td>
                <td><strong>{value(row.horse) || "Runner"}</strong></td>
                <td>{value(row.epi) || "-"}</td>
                <td>{price(row.market)}</td>
                <td>{price(row.edgeiq_price)}</td>
                <td><b className={edgeClass(row)}>{value(row.edge) || "-"}</b></td>
                <td><b className={moveClass(row)}>{flucText(row)}</b></td>
                <td>{statusLabel(row)}<br /><small>{marketDisclosureLabel(row)}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function MarketWorkspace(props: MarketWorkspaceProps) {
  const field = props.field ?? fieldFromRaceBook(props.raceBook);
  const race = useMemo(() => officialRace(props.raceBook, field), [props.raceBook, field]);
  const [rows, setRows] = useState<Awaited<ReturnType<typeof loadMarketTerminalFeed>>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadMarketTerminalFeed()
      .then((feedRows) => {
        if (!cancelled) {
          setRows(feedRows);
          setError(null);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setRows([]);
          setError(loadError instanceof Error ? loadError.message : "Market feed failed");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const viewModel = useMemo(() => buildMarketViewModel(race, rows, props.meetingKey ?? null), [race, rows, props.meetingKey]);

  if (error) {
    return <section className="eiq-market-v1"><div className="eiq-market-v1-empty">{error}</div></section>;
  }

  if (!viewModel.rows.length) {
    return (
      <section className="eiq-market-v1">
        <div className="eiq-market-v1-empty">Governed market rows are not published for this race.</div>
      </section>
    );
  }

  return (
    <section className="eiq-market-v1">
      <div className="eiq-market-v1-hero">
        <div>
          <p>MARKET</p>
          <h3>Market and EDGEiQ price context</h3>
          <span>Market snapshots, EDGEiQ assessed price and governed context for every runner.</span>
        </div>
        <dl>
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Market State</dt><dd>{viewModel.rows.some((row) => row.market || row.edgeiq_price) ? "Market Available" : "Awaiting Feed"}</dd></div>
        </dl>
      </div>
      <div className="eiq-market-v1-grid">
        <MarketTable rows={viewModel.rows} />
        <MarketReadPanel viewModel={viewModel} />
      </div>
    </section>
  );
}
