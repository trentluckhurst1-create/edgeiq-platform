import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type MovementRow = {
  snapshot_time?: string;
  track?: string;
  race_no?: string | number;
  horse?: string;
  movement_signal?: string;
  open_price?: string | number;
  current_price?: string | number;
  move_pct?: string | number;
  calibrated_edge_pct?: string | number;
  edge_persistence?: string;
  execution_action?: string;
  confidence_tier?: string;
  risk_flags?: string;
  speed_map_bucket?: string;
  pace_pressure?: string;
  snapshot_count?: string | number;
  priority?: string | number;
  market_regime?: string;
  market_regime_score?: string | number;
  regime_priority?: string | number;
};

function safe(v?: unknown): string {
  const s = String(v ?? "").trim();
  return s || "-";
}

function n(v?: unknown): number | null {
  const x = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(x) ? x : null;
}

function price(v?: unknown): string {
  const x = n(v);
  if (x === null || x <= 0) return "-";
  return x.toFixed(2);
}

function pct(v?: unknown): string {
  const x = n(v);
  if (x === null) return "-";
  return `${x.toFixed(1)}%`;
}

function moveClass(v?: string): string {
  const s = safe(v).toUpperCase();

  if (s.includes("MAJOR STEAM")) return "market-move-pill market-move-major-steam";
  if (s.includes("STEAM")) return "market-move-pill market-move-steam";
  if (s.includes("FIRMING")) return "market-move-pill market-move-firming";

  if (s.includes("MAJOR DRIFT")) return "market-move-pill market-move-major-drift";
  if (s.includes("DRIFT")) return "market-move-pill market-move-drift";
  if (s.includes("WEAKENING")) return "market-move-pill market-move-weakening";

  return "market-move-pill market-move-stable";
}

function actionClass(v?: string): string {
  const s = safe(v).toUpperCase();

  if (s === "EXECUTE") return "exec-action exec-action-execute";
  if (s === "LEAN") return "exec-action exec-action-lean";
  if (s === "WATCH") return "exec-action exec-action-watch";

  return "exec-action exec-action-pass";
}

function edgeClass(v?: unknown): string {
  const x = n(v);

  if (x === null) return "edgeiq-muted";
  if (x >= 25) return "edgeiq-green";
  if (x >= 12) return "edgeiq-lime";
  if (x > 0) return "edgeiq-muted";

  return "edgeiq-red";
}

export default function MarketTapeTab(): React.ReactElement {
  const [rows, setRows] = useState<MovementRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [focusMode, setFocusMode] = useState(true);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        setLoading(true);

        const res = await fetch(
          `/data/market_regime_board.csv?t=${Date.now()}`,
          { cache: "no-store" }
        );

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const text = await res.text();

        const parsed = Papa.parse<MovementRow>(text, {
          header: true,
          skipEmptyLines: true,
        });

        console.log("MARKET REGIME CSV:", parsed.data?.slice(0, 5));

        if (!active) return;

        const cleaned = (parsed.data || []).filter(
          (r) =>
            safe(r.horse) !== "-" &&
            safe(r.track) !== "-"
        );

        console.log("CLEANED REGIME ROWS:", cleaned.slice(0, 5));

        setRows(cleaned);
        setError("");
      } catch (err) {
        if (!active) return;

        setRows([]);
        setError(String(err));
      } finally {
        if (active) setLoading(false);
      }
    }

    load();

    return () => {
      active = false;
    };
  }, []);

  const ranked = useMemo(() => {
    const priority: Record<string, number> = {
      "ACTIONABLE EDGE": 1,
      "CONFIRMED STEAM": 2,
      "DRIFTING OVERLAY": 3,
      "STABLE OVERLAY": 4,
      "PUBLIC STEAM": 5,
      "FALSE STEAM": 6,
      "EARLY READ": 7,
      "NEGATIVE VALUE": 8,
      "NO EDGE": 9,
    };

    const base = focusMode
      ? rows.filter((r) =>
          ["ACTIONABLE EDGE", "CONFIRMED STEAM", "DRIFTING OVERLAY", "STABLE OVERLAY", "FALSE STEAM", "PUBLIC STEAM"]
            .includes(safe(r.market_regime).toUpperCase())
        )
      : rows;

    return [...base]
      .sort((a, b) => {
        const pa = priority[safe(a.market_regime).toUpperCase()] ?? 99;
        const pb = priority[safe(b.market_regime).toUpperCase()] ?? 99;

        if (pa !== pb) return pa - pb;

        return (
          (n(b.market_regime_score) ?? -999) -
          (n(a.market_regime_score) ?? -999)
        );
      })
      .slice(0, 120);
  }, [rows, focusMode]);

  const stats = useMemo(() => {
    return {
      steamers: rows.filter((r) =>
        safe(r.market_regime).toUpperCase().includes("ACTIONABLE")
      ).length,

      drifters: rows.filter((r) =>
        safe(r.market_regime).toUpperCase().includes("FALSE")
      ).length,

      stable: rows.filter(
        (r) => safe(r.market_regime).toUpperCase().includes("NEGATIVE")
      ).length,

      tracked: rows.length,

      avgEdge:
        rows.length > 0
          ? rows.reduce(
              (sum, r) => sum + (n(r.calibrated_edge_pct) ?? 0),
              0
            ) / rows.length
          : 0,
    };
  }, [rows]);

  return (
    <section className="edgeiq-ws terminal-panel-stack">
      <div className="edgeiq-ws-card terminal-card">
        <div className="edgeiq-ws-head terminal-card-head">
          <div>
            <div className="edgeiq-ws-kicker">
              EDGEiQ RACING / MARKET TAPE
            </div>

            <div className="text-[11px] text-[#7f8da0]">
              Regime classification · steam quality · false-move detection
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-3">
          <button type="button" className="edgeiq-scr-toggle" onClick={() => setFocusMode((v) => !v)}>
            {focusMode ? "Focus Mode" : "All Regimes"}
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
          <Metric label="Actionable" value={stats.steamers} />
          <Metric label="Tracked" value={stats.tracked} />
          <Metric label="False Steam" value={stats.drifters} />
          <Metric label="Negative" value={stats.stable} />
          <Metric
            label="Avg Cal Edge"
            value={`${stats.avgEdge.toFixed(1)}%`}
          />
        </div>

        {loading ? (
          <div className="px-3 py-8 text-[12px] text-[#7f8da0]">
            Loading market movement board...
          </div>
        ) : error ? (
          <div className="border border-[#7f1d1d] bg-[#180808] px-3 py-3 text-[12px] text-[#fca5a5]">
            {error}
          </div>
        ) : (
          <div className="edgeiq-ws-table-wrap aligned-table-wrap worksheet-grid-wrap">
            <table className="edgeiq-ws-table aligned-runner-table worksheet-terminal-table">
              <thead>
                <tr>
                  <th>Regime</th>
                  <th>Score</th>
                  <th>Move</th>
                  <th>Track</th>
                  <th>Race</th>
                  <th>Runner</th>
                  <th>Action</th>
                  <th>Open</th>
                  <th>Now</th>
                  <th>Move %</th>
                  <th>Cal Edge</th>
                  <th>Persist</th>
                  <th>Conf</th>
                  <th>Risk</th>
                </tr>
              </thead>

              <tbody>
                {ranked.map((r, i) => (
                  <tr key={`${safe(r.track)}-${safe(r.race_no)}-${safe(r.horse)}-${i}`} className={`market-regime-row market-regime-row-${safe(r.market_regime).toLowerCase().replaceAll(" ", "-")}`}>
                    <td>
                      <span className={`market-regime-pill market-regime-${safe(r.market_regime).toLowerCase().replaceAll(" ", "-")}`}>
                        {safe(r.market_regime)}
                      </span>
                    </td>

                    <td className={`num strong ${edgeClass(r.market_regime_score)}`}>
                      {safe(r.market_regime_score)}
                    </td>

                    <td>
                      <span className={moveClass(r.movement_signal)}>
                        {safe(r.movement_signal)}
                      </span>
                    </td>

                    <td>{safe(r.track)}</td>

                    <td className="num">R{safe(r.race_no)}</td>

                    <td>
                      <strong>{safe(r.horse)}</strong>
                      <div className="text-[10px] text-[#718096]">
                        {safe(r.speed_map_bucket)} · {safe(r.pace_pressure)} · snapshots: {safe(r.snapshot_count)}
                      </div>
                    </td>

                    <td>
                      <span className={actionClass(r.execution_action)}>
                        {safe(r.execution_action)}
                      </span>
                    </td>

                    <td className="num">{price(r.open_price)}</td>
                    <td className="num">{price(r.current_price)}</td>
                    <td className={`num strong ${edgeClass(r.move_pct)}`}>{pct(r.move_pct)}</td>
                    <td className={`num strong ${edgeClass(r.calibrated_edge_pct)}`}>{pct(r.calibrated_edge_pct)}</td>
                    <td>{safe(r.edge_persistence)}</td>
                    <td>{safe(r.confidence_tier)}</td>
                    <td className="text-[10px]">{safe(r.risk_flags)}</td>
                  </tr>
                ))}

                {!ranked.length && (
                  <tr>
                    <td colSpan={14} className="empty">
                      No market regime rows generated yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-3 text-[10px] text-[#64748b]">
          Regime intelligence strengthens as snapshot history, CLV, and results accumulate.
        </div>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="terminal-card px-3 py-2 exec-metric">
      <div className="text-[9px] uppercase tracking-[0.18em] text-[#7f8da0]">
        {label}
      </div>

      <div className="text-[20px] font-black text-white leading-tight">
        {value}
      </div>
    </div>
  );
}
