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

    fetch(`/data/market_history/edgeiq_market_tape.csv?t=${Date.now()}`, { cache: "no-store" })
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

  const latest = useMemo(() => {
    const byRunner = new Map<string, TapeRow>();
    rows.forEach((r) => {
      const key = r.edgeiq_runner_id || `${r.race_date}|${r.track}|${r.race_no}|${r.horse_key || r.horse}`;
      const prev = byRunner.get(key);
      if (!prev || safe(r.snapshot_ts) > safe(prev.snapshot_ts)) byRunner.set(key, r);
    });
    return Array.from(byRunner.values());
  }, [rows]);

  const ranked = useMemo(() => {
    return [...latest]
      .filter((r) => safe(r.execution_action_calibrated).toUpperCase() !== "NO MARKET")
      .sort((a, b) => (n(b.calibrated_edge_pct) ?? -999) - (n(a.calibrated_edge_pct) ?? -999))
      .slice(0, 80);
  }, [latest]);

  const stats = useMemo(() => {
    return {
      snapshots: new Set(rows.map((r) => r.snapshot_id).filter(Boolean)).size,
      runners: latest.length,
      execute: latest.filter((r) => safe(r.execution_action_calibrated).toUpperCase() === "EXECUTE").length,
      lean: latest.filter((r) => safe(r.execution_action_calibrated).toUpperCase() === "LEAN").length,
      watch: latest.filter((r) => safe(r.execution_action_calibrated).toUpperCase() === "WATCH").length,
      avgEdge:
        latest.length > 0
          ? latest.reduce((sum, r) => sum + (n(r.calibrated_edge_pct) ?? 0), 0) / latest.length
          : 0,
    };
  }, [rows, latest]);

  return (
    <section className="edgeiq-ws terminal-panel-stack">
      <div className="edgeiq-ws-card terminal-card">
        <div className="edgeiq-ws-head terminal-card-head">
          <div>
            <div className="edgeiq-ws-kicker">EDGEiQ RACING / MARKET TAPE</div>
            <div className="text-[11px] text-[#7f8da0]">
              Snapshot memory · overlay persistence · steam/drift foundation
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
          <Metric label="Snapshots" value={stats.snapshots} />
          <Metric label="Runners" value={stats.runners} />
          <Metric label="Execute" value={stats.execute} />
          <Metric label="Lean / Watch" value={stats.lean + stats.watch} />
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
                <th>Time</th>
                <th>Track</th>
                <th>Race</th>
                <th>Runner</th>
                <th>Action</th>
                <th>Market</th>
                <th>Raw Rated</th>
                <th>Cal Price</th>
                <th>Raw Edge</th>
                <th>Cal Edge</th>
                <th>Conf</th>
                <th>Risk</th>
                <th>Map</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((r, i) => (
                <tr key={`${r.market_tape_key || r.edgeiq_runner_id || i}`}>
                  <td>{snapshotTime(r)}</td>
                  <td>{safe(r.track)}</td>
                  <td className="num">R{safe(r.race_no)}</td>
                  <td>
                    <strong>{safe(r.horse)}</strong>
                    <div className="text-[10px] text-[#718096]">{safe(r.trainer)} · {safe(r.jockey)}</div>
                  </td>
                  <td><span className={actionClass(r.execution_action_calibrated)}>{safe(r.execution_action_calibrated)}</span></td>
                  <td className="num">{price(r.market_price)}</td>
                  <td className="num">{price(r.rated_price)}</td>
                  <td className="num strong">{price(r.calibrated_price)}</td>
                  <td className={`num ${edgeTone(r.edge_pct)}`}>{pct(r.edge_pct)}</td>
                  <td className={`num strong ${edgeTone(r.calibrated_edge_pct)}`}>{pct(r.calibrated_edge_pct)}</td>
                  <td>{safe(r.confidence_tier)}</td>
                  <td className="text-[10px]">{safe(r.risk_flags)}</td>
                  <td className="text-[10px]">{safe(r.speed_map_bucket)} · {safe(r.pace_pressure)}</td>
                </tr>
              ))}

              {!ranked.length ? (
                <tr>
                  <td colSpan={13} className="empty">
                    No market tape rows yet. Run the snapshot capture script to populate this screen.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="mt-3 text-[10px] text-[#64748b]">
          Movement detection activates once multiple snapshots exist for the same runner.
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
