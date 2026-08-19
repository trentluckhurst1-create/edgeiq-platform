import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import { EDGEIQ_REFRESH_MS } from "../config/edgeiqLiveFeeds";
import { isVicTrack } from "../config/edgeiqVicTracks";

type CsvRow = Record<string, string>;
type Tone = "good" | "warn" | "bad" | "neutral";

const FILES = {
  tape: "/data/edgeiq_market_tape_summary.csv",
  memory: "/data/edgeiq_market_tape_memory.csv",
  execution: "/data/edgeiq_execution_engine_v4.csv",
  clock: "/data/edgeiq_race_clock_engine.csv",
  truth: "/data/edgeiq_market_truth_engine_v3.csv",
  suppression: "/data/edgeiq_execution_suppression_v2.csv",
  freshnessSummary: "/data/edgeiq_racing_public_data_freshness_summary_v1.csv",
};

function clean(value: unknown): string {
  const output = String(value ?? "").trim();
  return output && output !== "-" && output.toUpperCase() !== "NAN" ? output : "";
}

function upper(value: unknown): string {
  return clean(value).toUpperCase();
}

function num(value: unknown): number | null {
  const raw = clean(value).replace(/[$,%]/g, "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function fmtPrice(value: unknown): string {
  const parsed = num(value);
  return parsed === null || parsed <= 0 ? "-" : parsed.toFixed(2);
}

function fmtPct(value: unknown): string {
  const parsed = num(value);
  return parsed === null ? "-" : `${parsed.toFixed(1)}%`;
}

function horseKey(value: unknown): string {
  return clean(value)
    .toUpperCase()
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/\([^)]*\)/g, "")
    .replace(/[^A-Z0-9]/g, "");
}

function trackKey(value: unknown): string {
  return clean(value).toUpperCase().replace(/[^A-Z0-9]+/g, " ").trim();
}

function rowKey(row: CsvRow, withHorse = true): string {
  const race = num(row.race_no || row.race_number) ?? 0;
  return `${trackKey(row.track || row.meeting)}|${race}${withHorse ? `|${horseKey(row.horse || row.horse_key)}` : ""}`;
}

function toneFrom(value: unknown): Tone {
  const status = upper(value);
  if (status.includes("EXECUTE") || status.includes("ALLOW") || status.includes("STEAM") || status.includes("OK")) return "good";
  if (status.includes("FAIL") || status.includes("KILL") || status.includes("SUPPRESS") || status.includes("REJECT")) return "bad";
  if (status.includes("WARN") || status.includes("STALE") || status.includes("DRIFT") || status.includes("MONITOR") || status.includes("QUESTION")) return "warn";
  return "neutral";
}

function toneClass(value: Tone): string {
  if (value === "good") return "positive";
  if (value === "warn") return "warning";
  if (value === "bad") return "negative";
  return "neutral";
}

async function readCsv(path: string): Promise<CsvRow[]> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return [];
    const csv = await response.text();
    return Papa.parse<CsvRow>(csv, { header: true, skipEmptyLines: true }).data ?? [];
  } catch {
    return [];
  }
}

function firstMetric(rows: CsvRow[], key: string, fallback = ""): string {
  return clean(rows.find((row) => clean(row.metric) === key)?.value) || fallback;
}

export default function MarketTapeTab(): React.ReactElement {
  const [tapeRows, setTapeRows] = useState<CsvRow[]>([]);
  const [memoryRows, setMemoryRows] = useState<CsvRow[]>([]);
  const [executionRows, setExecutionRows] = useState<CsvRow[]>([]);
  const [clockRows, setClockRows] = useState<CsvRow[]>([]);
  const [truthRows, setTruthRows] = useState<CsvRow[]>([]);
  const [suppressionRows, setSuppressionRows] = useState<CsvRow[]>([]);
  const [freshnessSummary, setFreshnessSummary] = useState<CsvRow[]>([]);
  const [trackFilter, setTrackFilter] = useState("ALL");
  const [mode, setMode] = useState<"ACTIVE" | "MOVERS" | "ALL">("ALL");
  const [loadedAt, setLoadedAt] = useState("");

  useEffect(() => {
    let alive = true;

    async function load(): Promise<void> {
      const [tape, memory, execution, clock, truth, suppression, freshness] = await Promise.all([
        readCsv(FILES.tape),
        readCsv(FILES.memory),
        readCsv(FILES.execution),
        readCsv(FILES.clock),
        readCsv(FILES.truth),
        readCsv(FILES.suppression),
        readCsv(FILES.freshnessSummary),
      ]);

      if (!alive) return;

      setTapeRows(tape.filter((row) => isVicTrack(row.track)));
      setMemoryRows(memory.filter((row) => isVicTrack(row.track)));
      setExecutionRows(execution.filter((row) => isVicTrack(row.track)));
      setClockRows(clock.filter((row) => isVicTrack(row.track)));
      setTruthRows(truth.filter((row) => isVicTrack(row.track)));
      setSuppressionRows(suppression.filter((row) => isVicTrack(row.track)));
      setFreshnessSummary(freshness);
      setLoadedAt(new Date().toLocaleTimeString());
    }

    load();
    const timer = window.setInterval(load, EDGEIQ_REFRESH_MS || 15000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const executionLookup = useMemo(() => {
    const map = new Map<string, CsvRow>();
    executionRows.forEach((row) => {
      const id = rowKey(row);
      if (id && !map.has(id)) map.set(id, row);
    });
    return map;
  }, [executionRows]);

  const truthLookup = useMemo(() => {
    const map = new Map<string, CsvRow>();
    truthRows.forEach((row) => {
      const id = rowKey(row);
      if (id && !map.has(id)) map.set(id, row);
    });
    return map;
  }, [truthRows]);

  const suppressionLookup = useMemo(() => {
    const map = new Map<string, CsvRow>();
    suppressionRows.forEach((row) => {
      const id = rowKey(row);
      if (id && !map.has(id)) map.set(id, row);
    });
    return map;
  }, [suppressionRows]);

  const clockLookup = useMemo(() => {
    const map = new Map<string, CsvRow>();
    clockRows.forEach((row) => {
      const id = rowKey(row, false);
      if (id && !map.has(id)) map.set(id, row);
    });
    return map;
  }, [clockRows]);

  const rows = useMemo(() => {
    return tapeRows.map((row) => {
      const execution = executionLookup.get(rowKey(row));
      const truth = truthLookup.get(rowKey(row));
      const suppression = suppressionLookup.get(rowKey(row));
      const clock = clockLookup.get(rowKey(row, false));

      return {
        ...row,
        execution_decision: clean(execution?.execution_decision),
        truth_grade: clean(truth?.truth_grade),
        suppression_action: clean(suppression?.suppression_action || execution?.suppression_action),
        lifecycle_state: clean(clock?.lifecycle_state || execution?.race_lifecycle),
        minutes_to_jump: clean(clock?.minutes_to_jump),
        reason: clean(execution?.reason || suppression?.suppression_reason || truth?.liquidity_grade),
      } as CsvRow;
    });
  }, [clockLookup, executionLookup, suppressionLookup, tapeRows, truthLookup]);

  const tracks = useMemo(() => ["ALL", ...Array.from(new Set(rows.map((row) => clean(row.track)).filter(Boolean))).sort()], [rows]);

  const staleStatus = firstMetric(freshnessSummary, "top_blocker_status", "UNKNOWN");
  const staleReason = firstMetric(freshnessSummary, "top_blocker_reason", "No tape freshness summary available.");
  const staleFeed = firstMetric(freshnessSummary, "top_blocker_feed", "");

  const activeRows = useMemo(
    () => rows.filter((row) => ["OPEN", "NEXT_UP", "JUMPING", "INPLAY", "PREOPEN"].includes(upper(row.lifecycle_state))),
    [rows],
  );

  const moverRows = useMemo(
    () => rows.filter((row) => upper(row.steam_drift) !== "FLAT" || upper(row.late_move_flag) === "YES"),
    [rows],
  );

  const filtered = useMemo(() => {
    let base = rows;
    if (trackFilter !== "ALL") {
      base = base.filter((row) => clean(row.track) === trackFilter);
    }

    if (mode === "ACTIVE") {
      return base.filter((row) => ["OPEN", "NEXT_UP", "JUMPING", "INPLAY", "PREOPEN"].includes(upper(row.lifecycle_state)));
    }

    if (mode === "MOVERS") {
      return base.filter((row) => upper(row.steam_drift) !== "FLAT" || upper(row.late_move_flag) === "YES");
    }

    return base;
  }, [mode, rows, trackFilter]);

  const displayRows = useMemo(() => {
    const base = filtered.length
      ? filtered
      : mode === "ACTIVE"
        ? activeRows
        : mode === "MOVERS"
          ? moverRows
          : rows;

    return [...base]
      .sort((a, b) => {
        const late = (upper(b.late_move_flag) === "YES" ? 1 : 0) - (upper(a.late_move_flag) === "YES" ? 1 : 0);
        if (late) return late;

        const seenA = clean(a.last_seen);
        const seenB = clean(b.last_seen);
        if (seenA !== seenB) return seenB.localeCompare(seenA);

        return Math.abs(num(b.move_pct) ?? 0) - Math.abs(num(a.move_pct) ?? 0);
      })
      .slice(0, 16);
  }, [activeRows, filtered, mode, moverRows, rows]);

  const stats = useMemo(() => {
    return {
      summaryRows: rows.length,
      memoryRows: memoryRows.length,
      activeRows: activeRows.length,
      moverRows: moverRows.length,
      lateFlags: rows.filter((row) => upper(row.late_move_flag) === "YES").length,
    };
  }, [activeRows.length, memoryRows.length, moverRows.length, rows]);

  return (
    <section className="edgeiq-ws terminal-panel-stack">
      <div className="terminal-card edgeiq-ws-card">
        <div className="edgeiq-ws-head terminal-card-head">
          <div>
            <div className="edgeiq-ws-kicker">EDGEIQ MARKET / TAPE MEMORY</div>
            <div className="terminal-muted">
              continuous VIC price snapshots | steam, drift, volatility, lifecycle and execution gates
            </div>
          </div>
          <div className="text-right">
            <div className="terminal-meta terminal-faint">UI poll</div>
            <div className="terminal-positive text-[13px] font-black">{loadedAt || "-"}</div>
          </div>
        </div>

        <div className="terminal-band">
          <span className={`terminal-chip ${toneClass(toneFrom(staleStatus))}`}>
            Tape {staleStatus}
          </span>
          {staleFeed ? (
            <span className="terminal-chip neutral">
              Blocker {staleFeed}
            </span>
          ) : null}
          <span className="terminal-text text-[11px]">{staleReason}</span>
        </div>

        <div className="terminal-grid five">
          <Metric label="Summary rows" value={stats.summaryRows} />
          <Metric label="Memory rows" value={stats.memoryRows} />
          <Metric label="Active rows" value={stats.activeRows} tone={stats.activeRows ? "good" : "warn"} />
          <Metric label="Mover rows" value={stats.moverRows} tone={stats.moverRows ? "good" : "neutral"} />
          <Metric label="Late flags" value={stats.lateFlags} tone={stats.lateFlags ? "warn" : "neutral"} />
        </div>

        <div className="mb-3 flex flex-wrap items-center gap-2">
          {(["ACTIVE", "MOVERS", "ALL"] as const).map((next) => (
            <button
              key={next}
              type="button"
              onClick={() => setMode(next)}
              className={`terminal-chip ${mode === next ? toneClass(next === "MOVERS" ? "warn" : "good") : "neutral"}`}
            >
              {next}
            </button>
          ))}
          <select
            value={trackFilter}
            onChange={(event) => setTrackFilter(event.target.value)}
            className="terminal-select"
          >
            {tracks.map((track) => (
              <option key={track} value={track}>
                {track}
              </option>
            ))}
          </select>
          {!filtered.length && rows.length ? (
            <span className="terminal-warning terminal-meta">
              showing nearest available tape rows because the current filter is empty
            </span>
          ) : null}
        </div>

        <div className="edgeiq-ws-table-wrap aligned-table-wrap worksheet-grid-wrap">
          <table className="edgeiq-ws-table aligned-runner-table worksheet-terminal-table">
            <thead>
              <tr>
                <th>State</th>
                <th>Track</th>
                <th>Race</th>
                <th>Runner</th>
                <th>Open</th>
                <th>Last</th>
                <th>Low</th>
                <th>High</th>
                <th>Move %</th>
                <th>Vol</th>
                <th>Decision</th>
                <th>Truth</th>
                <th>Last seen</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {displayRows.length ? (
                displayRows.map((row, index) => (
                  <tr key={`${row.track}-${row.race_no}-${row.horse}-${index}`}>
                    <td><Badge value={clean(row.steam_drift) || clean(row.lifecycle_state) || "TAPE"} tone={toneFrom(row.steam_drift || row.lifecycle_state)} /></td>
                    <td>{clean(row.track)}</td>
                    <td className="num">R{clean(row.race_no)}</td>
                    <td>
                      <strong>{clean(row.horse)}</strong>
                      <div className="terminal-meta terminal-faint">
                        {clean(row.snapshots) || "0"} snapshots | {clean(row.minutes_to_jump) ? `${clean(row.minutes_to_jump)}m` : clean(row.lifecycle_state) || "no clock"}
                      </div>
                    </td>
                    <td className="num">{fmtPrice(row.open_price)}</td>
                    <td className="num strong">{fmtPrice(row.last_price)}</td>
                    <td className="num">{fmtPrice(row.low_price)}</td>
                    <td className="num">{fmtPrice(row.high_price)}</td>
                    <td className={`num strong ${toneClass(toneFrom(row.steam_drift))}`}>{fmtPct(row.move_pct)}</td>
                    <td className="num">{fmtPct(row.market_volatility)}</td>
                    <td><Badge value={clean(row.execution_decision) || clean(row.suppression_action) || "OBSERVE"} tone={toneFrom(row.execution_decision || row.suppression_action)} /></td>
                    <td><Badge value={clean(row.truth_grade) || "TRUTH"} tone={toneFrom(row.truth_grade)} /></td>
                    <td>{clean(row.last_seen) || "-"}</td>
                    <td className="max-w-[280px] truncate" title={clean(row.reason)}>{clean(row.reason) || "-"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={14} className="empty">
                    No VIC market tape rows are available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function Badge({ value, tone }: { value: string; tone: Tone }): React.ReactElement {
  return (
    <span className={`terminal-chip ${toneClass(tone)}`}>
      {value || "-"}
    </span>
  );
}

function Metric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  tone?: Tone;
}): React.ReactElement {
  const color = tone === "good" ? "terminal-positive" : tone === "bad" ? "terminal-negative" : tone === "warn" ? "terminal-warning" : "terminal-text";
  return (
    <div className={`terminal-metric ${tone}`}>
      <span>{label}</span>
      <div className={`text-[20px] font-black leading-tight ${color}`}>{value}</div>
    </div>
  );
}

