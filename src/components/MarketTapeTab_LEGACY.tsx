import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type TapeRow = Record<string, string>;

function n(v: unknown): number | null {
  const x = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(x) ? x : null;
}

function safe(v: unknown): string {
  const s = String(v ?? "").trim();
  return s || "-";
}

function price(v: unknown): string {
  const x = n(v);
  if (x === null || x <= 0) return "-";
  return x.toFixed(2);
}

function pct(v: unknown): string {
  const x = n(v);
  if (x === null) return "-";
  return `${x.toFixed(1)}%`;
}

function edgeTone(v: unknown): string {
  const x = n(v);
  if (x === null) return "edgeiq-muted";
  if (x >= 24) return "edgeiq-green";
  if (x >= 12) return "edgeiq-lime";
  if (x < 0) return "edgeiq-red";
  return "edgeiq-muted";
}

function actionClass(v: unknown): string {
  const s = safe(v).toUpperCase();
  if (s === "EXECUTE") return "exec-action exec-action-execute";
  if (s === "LEAN") return "exec-action exec-action-lean";
  if (s === "WATCH") return "exec-action exec-action-watch";
  if (s === "SPEC WATCH") return "exec-action exec-action-spec";
  if (s === "NO MARKET") return "exec-action exec-action-no-market";
  return "exec-action exec-action-pass";
}

function snapshotTime(row: TapeRow): string {
  const raw = row.snapshot_ts || row.snapshot_id || "";
  if (!raw) return "-";
  const d = new Date(raw);
  if (!Number.isNaN(d.getTime())) {
    return d.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" });
  }
  return raw;
}

export default function MarketTapeTab(): React.ReactElement {
  const [rows, setRows] = useState<TapeRow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    fetch(`/data/market_history/market_movement_board.csv?t=${Date.now()}`, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => {
        if (!active) return;
        const parsed = Papa.parse<TapeRow>(text, { header: true, skipEmptyLines: true });
        setRows(parsed.data || []);
        setError("");
      })
      .catch((e) => {
        if (!active) return;
        setRows([]);
        setError(String(e?.message || e));
      });

    return () => {
      active = false;
    };
  }, []);

  const ranked = useMemo(() => {
    const priority: Record<string, number> = {
      "MAJOR STEAM": 1,
      "STEAM": 2,
      "FIRMING": 3,
      "WEAKENING": 4,
      "DRIFT": 5,
      "MAJOR DRIFT": 6,
      "STABLE": 7,
    };

    return [...rows]
      .sort((a, b) => {
        const pa = priority[safe(a.movement_signal).toUpperCase()] ?? 99;
        const pb = priority[safe(b.movement_signal).toUpperCase()] ?? 99;
        if (pa !== pb) return pa - pb;
        return (n(b.calibrated_edge_pct) ?? -999) - (n(a.calibrated_edge_pct) ?? -999);
      })
      .slice(0, 100);
  }, [rows]);

  const stats = useMemo(() => {
    return {
      steamers: rows.filter((r) => safe(r.movement_signal).toUpperCase().includes("STEAM")).length,
      drifters: rows.filter((r) => safe(r.movement_signal).toUpperCase().includes("DRIFT")).length,
      stable: rows.filter((r) => safe(r.movement_signal).toUpperCase() === "STABLE").length,
      tracked: rows.length,
      avgEdge:
        rows.length > 0
          ? rows.reduce((sum, r) => sum + (n(r.calibrated_edge_pct) ?? 0), 0) / rows.length
          : 0,
    };
  }, [rows]);

  return (
    <section className="edgeiq-ws terminal-panel-stack">
      <div className="edgeiq-ws-card terminal-card">
        <div className="edgeiq-ws-head terminal-card-head">
          <div>
            <div className="edgeiq-ws-kicker">EDGEiQ RACING / MARKET TAPE</div>
            <div className="text-[11px] text-[#7f8da0]">
              Steam · drift · overlay persistence · market movement
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
          <Metric label="Steamers" value={stats.steamers} />
          <Metric label="Tracked" value={stats.tracked} />
          <Metric label="Drifters" value={stats.drifters} />
          <Metric label="Stable" value={stats.stable} />
          <Metric label="Avg Cal Edge" value={`${stats.avgEdge.toFixed(1)}%`} />
        </div>

        {error ? (
          <div className="border border-[#7f1d1d] bg-[#180808] px-3 py-3 text-[12px] text-[#fca5a5]">
            Market tape not loaded: {error}
          </div>
        ) : null}

        <div className="edgeiq-ws-table-wrap aligned-table-wrap worksheet-grid-wrap">
          <table className="edgeiq-ws-table aligned-runner-table worksheet-terminal-table">
            <thead>
              <tr>
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
                <th>Map</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((r, i) => (
                <tr key={`${r.market_tape_key || r.edgeiq_runner_id || i}`}>
                  <td><span className={`market-move-pill market-move-${safe(r.movement_signal).toLowerCase().replaceAll(" ", "-")}`}>{safe(r.movement_signal)}</span></td>
                  <td>{safe(r.track)}</td>
                  <td className="num">R{safe(r.race_no)}</td>
                  <td>
                    <strong>{safe(r.horse)}</strong>
                    <div className="text-[10px] text-[#718096]">snapshots: {safe(r.snapshot_count)}</div>
                  </td>
                  <td><span className={actionClass(r.execution_action)}>{safe(r.execution_action)}</span></td>
                  <td className="num">{price(r.open_price)}</td>
                  <td className="num">{price(r.current_price)}</td>
                  <td className={`num strong ${edgeTone(r.move_pct)}`}>{pct(r.move_pct)}</td>
                  <td className={`num strong ${edgeTone(r.calibrated_edge_pct)}`}>{pct(r.calibrated_edge_pct)}</td>
                  <td>{safe(r.edge_persistence)}</td>
                  <td>{safe(r.confidence_tier)}</td>
                  <td className="text-[10px]">{safe(r.risk_flags)}</td>
                  <td className="text-[10px]">{safe(r.speed_map_bucket)} · {safe(r.pace_pressure)}</td>
                </tr>
              ))}

              {!ranked.length ? (
                <tr>
                  <td colSpan={13} className="empty">
                    No market movement rows yet. Capture at least one market snapshot, then run the movement board script.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="mt-3 text-[10px] text-[#64748b]">
          Steam/drift signals strengthen as multiple snapshots accumulate for the same runner.
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="terminal-card px-3 py-2 exec-metric">
      <div className="text-[9px] uppercase tracking-[0.18em] text-[#7f8da0]">{label}</div>
      <div className="text-[20px] font-black text-white leading-tight">{value}</div>
    </div>
  );
}
