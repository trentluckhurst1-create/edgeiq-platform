import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import type { FormHistoryRow, RatingDisplayRow } from "../App";
import { DEFAULT_SILK_URL, getSilksUrl, silkFallback } from "../utils/silks";

type Props = {
  runners: RatingDisplayRow[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
  selectedHorseHistory?: FormHistoryRow[];
};

type ExecutionRow = Record<string, string>;

function safe(v?: unknown): string {
  if (v === null || v === undefined || String(v).trim() === "") return "-";
  return String(v);
}

function n(v: unknown): number | null {
  const x = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(x) ? x : null;
}

function price(v: unknown): string {
  const x = n(v);
  if (x === null || x <= 0) return "-";
  return x.toFixed(2);
}

function pct(v: unknown): string {
  const x = n(v);
  if (x === null) return "-";
  return `${Math.max(-99.9, Math.min(999.9, x)).toFixed(1)}%`;
}

function hardKey(v: unknown): string {
  return String(v ?? "")
    .toUpperCase()
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/\s*\([A-Z]+\)/g, "")
    .replace(/[’'`]/g, "")
    .replace(/[^A-Z0-9]/g, "")
    .trim();
}

function raceKey(date: unknown, track: unknown, raceNo: unknown): string {
  return `${safe(date)}|${hardKey(track)}|${String(raceNo ?? "").replace(/\.0$/, "").trim()}`;
}

function runnerKey(row: Pick<RatingDisplayRow, "raceDate" | "track" | "raceNo" | "horseKey" | "horse">): string {
  return `${raceKey(row.raceDate, row.track, row.raceNo)}|${hardKey(row.horseKey || row.horse)}`;
}

function execRunnerKey(row: ExecutionRow): string {
  return `${raceKey(row.race_date, row.track, row.race_no)}|${hardKey(row.horse_key || row.horse)}`;
}

function silkFor(row?: Pick<RatingDisplayRow, "horse" | "silkUrl"> | null): string {
  if (!row) return DEFAULT_SILK_URL;
  return row.silkUrl || getSilksUrl(row.horse);
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

function edgeClass(v: unknown): string {
  const x = n(v);
  if (x === null) return "edgeiq-muted";
  if (x >= 24) return "edgeiq-green";
  if (x >= 12) return "edgeiq-lime";
  if (x > 0) return "edgeiq-muted";
  return "edgeiq-red";
}

function rating(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "-";
  return v.toFixed(1);
}

function dateShort(d: string): string {
  const x = new Date(d);
  if (Number.isNaN(x.getTime())) return d || "-";
  return x.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "2-digit" });
}

export default function Worksheet({
  runners,
  selectedHorseKey,
  onSelectHorse,
  selectedHorseHistory = [],
}: Props): React.ReactElement {
  const [executionRows, setExecutionRows] = useState<ExecutionRow[]>([]);
  const [showPass, setShowPass] = useState(false);
  const [showNoMarket, setShowNoMarket] = useState(false);
  const [priorityOnly, setPriorityOnly] = useState(true);

  useEffect(() => {
    let active = true;

    fetch(`/data/edgeiq_calibrated_execution_board.csv?t=${Date.now()}`, { cache: "no-store" })
      .then((r) => r.text())
      .then((text) => {
        if (!active) return;
        const parsed = Papa.parse<ExecutionRow>(text, { header: true, skipEmptyLines: true });
        setExecutionRows(parsed.data || []);
      })
      .catch(() => {
        if (active) setExecutionRows([]);
      });

    return () => {
      active = false;
    };
  }, []);

  const execByRunner = useMemo(() => {
    const map = new Map<string, ExecutionRow>();
    executionRows.forEach((row) => map.set(execRunnerKey(row), row));
    return map;
  }, [executionRows]);

  const rows = useMemo(() => {
    return runners
      .filter((r) => !r.isScratched)
      .map((r) => ({ runner: r, exec: execByRunner.get(runnerKey(r)) }))
      .filter(({ exec }) => {
        const action = safe(exec?.execution_action_calibrated).toUpperCase();
        if (priorityOnly && !["EXECUTE", "LEAN", "WATCH", "SPEC WATCH"].includes(action)) return false;
        if (!showNoMarket && action === "NO MARKET") return false;
        if (!showPass && (!action || action === "PASS")) return false;
        return true;
      })
      .sort((a, b) => {
        const order: Record<string, number> = {
          EXECUTE: 1,
          LEAN: 2,
          WATCH: 3,
          "SPEC WATCH": 4,
          PASS: 5,
          "NO MARKET": 6,
        };
        const aa = order[safe(a.exec?.execution_action_calibrated).toUpperCase()] ?? 9;
        const bb = order[safe(b.exec?.execution_action_calibrated).toUpperCase()] ?? 9;
        if (aa !== bb) return aa - bb;
        return (n(b.exec?.calibrated_edge_pct) ?? -999) - (n(a.exec?.calibrated_edge_pct) ?? -999);
      });
  }, [runners, execByRunner, showPass, showNoMarket]);

  const selected = runners.find((r) => r.horseKey === selectedHorseKey) ?? null;
  const selectedExec = selected ? execByRunner.get(runnerKey(selected)) : null;
  const lastFive = useMemo(() => selectedHorseHistory.slice(0, 5), [selectedHorseHistory]);

  const counts = useMemo(() => {
    const currentKeys = new Set(runners.map((r) => runnerKey(r)));
    const currentExec = executionRows.filter((r) => currentKeys.has(execRunnerKey(r)));
    return {
      execute: currentExec.filter((r) => safe(r.execution_action_calibrated).toUpperCase() === "EXECUTE").length,
      lean: currentExec.filter((r) => safe(r.execution_action_calibrated).toUpperCase() === "LEAN").length,
      watch: currentExec.filter((r) => safe(r.execution_action_calibrated).toUpperCase() === "WATCH").length,
      pass: currentExec.filter((r) => safe(r.execution_action_calibrated).toUpperCase() === "PASS").length,
      noMarket: currentExec.filter((r) => safe(r.execution_action_calibrated).toUpperCase() === "NO MARKET").length,
    };
  }, [executionRows, runners]);

  return (
    <section className="edgeiq-ws terminal-panel-stack">
      <div className="edgeiq-ws-card terminal-card">
        <div className="edgeiq-ws-head terminal-card-head">
          <div>
            <div className="edgeiq-ws-kicker">EDGEiQ RACING / EXECUTION TERMINAL</div>
            <div className="text-[11px] text-[#7f8da0]">
              Calibrated market board · confidence-weighted · market-anchored
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button type="button" className="edgeiq-scr-toggle" onClick={() => setPriorityOnly((v) => !v)}>
              {priorityOnly ? "Priority Mode" : "All Mode"}
            </button>
            <button type="button" className="edgeiq-scr-toggle" onClick={() => setShowPass((v) => !v)}>
              {showPass ? "Hide PASS" : `Include PASS (${counts.pass})`}
            </button>
            <button type="button" className="edgeiq-scr-toggle" onClick={() => setShowNoMarket((v) => !v)}>
              {showNoMarket ? "Hide NO MARKET" : `Include NO MARKET (${counts.noMarket})`}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
          <Metric label="EXECUTE" value={counts.execute} tone="execute" />
          <Metric label="LEAN" value={counts.lean} tone="lean" />
          <Metric label="WATCH" value={counts.watch} tone="watch" />
          <Metric label="PASS" value={counts.pass} tone="pass" />
          <Metric label="NO MARKET" value={counts.noMarket} tone="none" />
        </div>

        <div className="edgeiq-ws-table-wrap aligned-table-wrap worksheet-grid-wrap">
          <table className="edgeiq-ws-table aligned-runner-table worksheet-terminal-table worksheet-fixed-table">
            <thead>
              <tr>
                <th>No</th>
                <th>Silk</th>
                <th>Runner</th>
                <th>Action</th>
                <th>Jockey</th>
                <th>Trainer</th>
                <th>Bar</th>
                <th>Market</th>
                <th>Raw Rated</th>
                <th>Cal Price</th>
                <th>Raw Edge</th>
                <th>Cal Edge</th>
                <th>Conf</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ runner, exec }) => {
                const active = runner.horseKey === selectedHorseKey;
                const action = safe(exec?.execution_action_calibrated || "PASS");
                return (
                  <tr
                    key={runner.id}
                    onClick={() => onSelectHorse(runner.horseKey)}
                    className={`${active ? "selected is-selected" : ""}`}
                  >
                    <td className="num saddle-cell"><span>{runner.horseNo ?? "-"}</span></td>
                    <td className="silk-cell"><img src={silkFor(runner)} alt="" onError={silkFallback} /></td>
                    <td className="runner-text-cell worksheet-runner-name-only">
                      <strong>{runner.horse}</strong>
                      <div className="text-[10px] text-[#718096]">{safe(exec?.speed_map_bucket)} · {safe(exec?.pace_pressure)}</div>
                    </td>
                    <td><span className={actionClass(action)}>{action}</span></td>
                    <td>{safe(runner.jockey)}</td>
                    <td>{safe(runner.trainer)}</td>
                    <td className="num">{runner.barrier ?? "-"}</td>
                    <td className="num">{price(exec?.market_price ?? runner.marketPrice)}</td>
                    <td className="num">{price(exec?.rated_price ?? runner.ratedPrice)}</td>
                    <td className="num strong">{price(exec?.calibrated_price)}</td>
                    <td className={`num ${edgeClass(exec?.edge_pct)}`}>{pct(exec?.edge_pct)}</td>
                    <td className={`num strong ${edgeClass(exec?.calibrated_edge_pct)}`}>{pct(exec?.calibrated_edge_pct)}</td>
                    <td>{safe(exec?.confidence_tier)}</td>
                    <td className="text-[10px]">{safe(exec?.risk_flags)}</td>
                  </tr>
                );
              })}

              {!rows.length && (
                <tr>
                  <td colSpan={14} className="empty">No EXECUTE / LEAN / WATCH runners for this race. Use All Mode or include PASS / NO MARKET to audit the full field.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="edgeiq-ws-card terminal-card edgeiq-snapshot-card">
          <div className="edgeiq-snap-head">
            <div className="edgeiq-runner aligned-runner snapshot-runner">
              <img src={silkFor(selected)} alt="" onError={silkFallback} />
              <div className="edgeiq-runner-meta">
                <strong>{selected.horse}</strong>
                <span>No {selected.horseNo ?? "-"} | Bar {selected.barrier ?? "-"} | {safe(selected.raceClass)}</span>
              </div>
            </div>
            <div className="edgeiq-snap-metrics">
              <div><span>Action</span><strong>{safe(selectedExec?.execution_action_calibrated)}</strong></div>
              <div><span>Cal Price</span><strong>{price(selectedExec?.calibrated_price)}</strong></div>
              <div><span>Cal Edge</span><strong className={edgeClass(selectedExec?.calibrated_edge_pct)}>{pct(selectedExec?.calibrated_edge_pct)}</strong></div>
              <div><span>Confidence</span><strong>{safe(selectedExec?.confidence_tier)}</strong></div>
            </div>
          </div>

          <div className="text-[11px] text-[#8b97a6] mb-3">
            {safe(selectedExec?.calibration_reason)}
          </div>

          <div className="edgeiq-form-title">Last 5 official starts</div>
          <div className="edgeiq-ws-table-wrap aligned-table-wrap">
            <table className="edgeiq-ws-table edgeiq-form-table compact-form-table">
              <thead>
                <tr><th>Date</th><th>Track</th><th>Dist</th><th>Class</th><th>Cond</th><th>Fin</th><th>Margin</th><th>Jockey</th><th>SP</th><th>Rating</th><th>Type</th></tr>
              </thead>
              <tbody>
                {lastFive.map((run, i) => (
                  <tr key={`${run.id ?? selected.horseKey}-${i}`}>
                    <td>{dateShort(run.runDate)}</td>
                    <td>{safe(run.track)}</td>
                    <td>{safe(run.distance)}</td>
                    <td>{safe(run.raceClass)}</td>
                    <td>{safe(run.trackCondition)}</td>
                    <td>{safe(run.finishPos)}</td>
                    <td>{safe(run.margin)}</td>
                    <td>{safe(run.jockey)}</td>
                    <td>{safe(run.sp)}</td>
                    <td>{run.runType === "RACE" ? rating(run.runRating) : "-"}</td>
                    <td>{safe(run.runType)}</td>
                  </tr>
                ))}
                {lastFive.length === 0 && <tr><td colSpan={11} className="empty">No official form history</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className={`terminal-card px-3 py-2 exec-metric exec-metric-${tone}`}>
      <div className="text-[9px] uppercase tracking-[0.18em] text-[#7f8da0]">{label}</div>
      <div className="text-[20px] font-black text-white leading-tight">{value}</div>
    </div>
  );
}
