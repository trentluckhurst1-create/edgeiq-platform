import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type CsvRow = Record<string, string>;

function text(value: unknown): string {
  return String(value ?? "").trim();
}

function num(value: unknown): number | null {
  const raw = text(value).replace("%", "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function readCsv(path: string): Promise<CsvRow[]> {
  return new Promise((resolve) => {
    Papa.parse<CsvRow>(`${path}?v=${Date.now()}`, {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (result) => resolve((result.data ?? []) as CsvRow[]),
      error: () => resolve([]),
    });
  });
}

function latestRows(rows: CsvRow[], key = "snapshot_ts"): CsvRow[] {
  if (!rows.length) return [];

  const sorted = rows
    .map((row) => text(row[key]))
    .filter(Boolean)
    .sort();

  const latest = sorted[sorted.length - 1];
  if (!latest) return rows;

  return rows.filter((row) => text(row[key]) === latest);
}

function topMovement(rows: CsvRow[]): CsvRow[] {
  return [...rows]
    .sort((a, b) => {
      const av =
        Math.abs(num(a.move_pct) ?? num(a.price_move_pct) ?? num(a.reaction_score) ?? 0);
      const bv =
        Math.abs(num(b.move_pct) ?? num(b.price_move_pct) ?? num(b.reaction_score) ?? 0);

      return bv - av;
    })
    .slice(0, 6);
}

export default function MarketsCommandHeader() {
  const [telemetry, setTelemetry] = useState<CsvRow[]>([]);
  const [reaction, setReaction] = useState<CsvRow[]>([]);
  const [regime, setRegime] = useState<CsvRow[]>([]);
  const [loadedAt, setLoadedAt] = useState("");

  useEffect(() => {
    let alive = true;

    async function load() {
      const [telemetryRows, reactionRows, regimeRows] = await Promise.all([
        readCsv("/data/edgeiq_execution_telemetry.csv"),
        readCsv("/data/edgeiq_market_reaction_board.csv"),
        readCsv("/data/market_regime_board.csv"),
      ]);

      if (!alive) return;

      setTelemetry(telemetryRows);
      setReaction(reactionRows);
      setRegime(regimeRows);
      setLoadedAt(new Date().toLocaleTimeString());
    }

    load();
    const timer = window.setInterval(load, 60000);

    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const latestTelemetry = useMemo(() => latestRows(telemetry), [telemetry]);
  const movers = useMemo(() => topMovement(reaction.length ? reaction : latestTelemetry), [reaction, latestTelemetry]);

  const steamerCount = movers.filter((row) => {
    const value = num(row.move_pct) ?? num(row.price_move_pct) ?? num(row.reaction_score) ?? 0;
    return value > 0;
  }).length;

  const drifterCount = movers.filter((row) => {
    const value = num(row.move_pct) ?? num(row.price_move_pct) ?? num(row.reaction_score) ?? 0;
    return value < 0;
  }).length;

  const volatilityCount = reaction.filter((row) => {
    const state = text(row.volatility_state || row.market_volatility || row.reaction_state).toUpperCase();
    const score = num(row.volatility_score) ?? 0;
    return state.includes("VOL") || score > 0;
  }).length;

  return (
    <div className="edgeiq-markets-lab">

      <div className="edgeiq-markets-hero">
        <div>
          <div className="edgeiq-kicker">MARKETS</div>
          <h1>Live Market Tape</h1>
          <p>
            Price movement, steam, drift, volatility, regime shifts and reaction intelligence.
          </p>
        </div>

        <div className="edgeiq-heartbeat">
          <span className="pulse-dot" />
          MARKET HEARTBEAT
          <strong>{loadedAt || "LOADING"}</strong>
        </div>
      </div>

      <div className="edgeiq-command-grid">

        <div className="edgeiq-stat-card">
          <div className="label">LATEST SNAPSHOT</div>
          <div className="value emerald">{latestTelemetry.length || telemetry.length}</div>
          <div className="sub">telemetry rows</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">STEAM WATCH</div>
          <div className="value blue">{steamerCount}</div>
          <div className="sub">positive movement signals</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">DRIFT WATCH</div>
          <div className="value gold">{drifterCount}</div>
          <div className="sub">negative movement signals</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">VOLATILITY</div>
          <div className="value purple">{volatilityCount}</div>
          <div className="sub">{regime.length} regime rows loaded</div>
        </div>

      </div>

      <div className="edgeiq-panel">
        <div className="edgeiq-panel-title">TOP MARKET MOVES</div>

        <div className="edgeiq-market-move-list">
          {movers.map((row, idx) => {
            const move =
              num(row.move_pct) ??
              num(row.price_move_pct) ??
              num(row.reaction_score) ??
              0;

            return (
              <div
                key={`${text(row.horse || row.runner || row.selection)}-${idx}`}
                className={move >= 0 ? "market-move up" : "market-move down"}
              >
                <span className="rank">{idx + 1}</span>
                <span className="horse">{text(row.horse || row.runner || row.selection) || "UNKNOWN"}</span>
                <span>{text(row.track)}</span>
                <span>{text(row.market_regime || row.regime || row.reaction_state) || "MARKET"}</span>
                <strong>{move.toFixed(2)}</strong>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
