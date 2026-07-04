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
  const sortedSnapshots = rows
    .map((row) => text(row[key]))
    .filter(Boolean)
    .sort();

  const latest = sortedSnapshots[sortedSnapshots.length - 1];

  if (!latest) return rows;
  return rows.filter((row) => text(row[key]) === latest);
}

function uniqueCount(rows: CsvRow[], col: string): number {
  return new Set(rows.map((row) => text(row[col])).filter(Boolean)).size;
}

function topRows(rows: CsvRow[], scoreCols: string[], limit = 8): CsvRow[] {
  return [...rows]
    .sort((a, b) => {
      const av = scoreCols.map((col) => num(a[col]) ?? -999).find((v) => v !== -999) ?? -999;
      const bv = scoreCols.map((col) => num(b[col]) ?? -999).find((v) => v !== -999) ?? -999;
      return bv - av;
    })
    .slice(0, limit);
}

export default function CommandCentreTab() {
  const [feedback, setFeedback] = useState<CsvRow[]>([]);
  const [telemetry, setTelemetry] = useState<CsvRow[]>([]);
  const [reaction, setReaction] = useState<CsvRow[]>([]);
  const [settlement, setSettlement] = useState<CsvRow[]>([]);
  const [alignment, setAlignment] = useState<CsvRow[]>([]);
  const [learning, setLearning] = useState<CsvRow[]>([]);
  const [loadedAt, setLoadedAt] = useState("");

  useEffect(() => {
    let alive = true;

    async function load() {
      const [
        feedbackRows,
        telemetryRows,
        reactionRows,
        settlementRows,
        alignmentRows,
        learningRows,
      ] = await Promise.all([
        readCsv("/data/edgeiq_execution_feedback_board.csv"),
        readCsv("/data/edgeiq_execution_telemetry.csv"),
        readCsv("/data/edgeiq_market_reaction_board.csv"),
        readCsv("/data/edgeiq_settlement_board.csv"),
        readCsv("/data/edgeiq_live_event_alignment.csv"),
        readCsv("/data/edgeiq_clv_learning_board.csv"),
      ]);

      if (!alive) return;

      setFeedback(feedbackRows);
      setTelemetry(telemetryRows);
      setReaction(reactionRows);
      setSettlement(settlementRows);
      setAlignment(alignmentRows);
      setLearning(learningRows);
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

  const activeSignals = useMemo(() => {
    return feedback.filter((row) => {
      const state = text(row.execution_state || row.final_execution_state || row.action).toUpperCase();
      return ["PRIORITY EXECUTE", "EXECUTE", "WATCH", "MONITOR", "LEAN"].some((x) => state.includes(x));
    });
  }, [feedback]);

  const liveEvents = useMemo(() => {
    return alignment.filter((row) => text(row.alignment_state || row.event_state || row.status).toUpperCase().includes("LIKELY"));
  }, [alignment]);

  const resultedEvents = useMemo(() => {
    return alignment.filter((row) => {
      const results = num(row.results_count) ?? 0;
      const state = text(row.event_state || row.lifecycle_state).toUpperCase();
      return results > 0 || state.includes("RESULT");
    });
  }, [alignment]);

  const pendingSettlement = useMemo(() => {
    return settlement.filter((row) => {
      const state = text(row.result_state || row.settlement_state || row.lifecycle_state || row.status).toUpperCase();
      return !state.includes("SETTLED") && !state.includes("WON") && !state.includes("LOST");
    });
  }, [settlement]);

  const topSetups = useMemo(() => {
    return topRows(activeSignals.length ? activeSignals : feedback, [
      "settlement_quality_score",
      "execution_quality_score",
      "edgeiq_score",
      "confidence_score",
      "overlay_score",
      "edge_pct",
    ]);
  }, [activeSignals, feedback]);

  const marketMoves = useMemo(() => {
    return topRows(reaction.length ? reaction : latestTelemetry, [
      "move_pct",
      "price_move_pct",
      "reaction_score",
      "steam_score",
      "volatility_score",
    ]);
  }, [reaction, latestTelemetry]);

  const learningRows = useMemo(() => {
    return topRows(learning, [
      "learning_score",
      "clv_score",
      "signal_score",
      "edgeiq_score",
    ], 6);
  }, [learning]);

  return (
    <div className="edgeiq-command-centre">
      <div className="edgeiq-command-header">
        <div>
          <div className="edgeiq-kicker">EDGEIQ RACING</div>
          <h1>Command Centre</h1>
          <p>Live market intelligence, execution state, lifecycle alignment and settlement readiness.</p>
        </div>
        <div className="edgeiq-heartbeat">
          <span className="pulse-dot" />
          LIVE CSV HEARTBEAT
          <strong>{loadedAt || "LOADING"}</strong>
        </div>
      </div>

      <div className="edgeiq-command-grid">
        <div className="edgeiq-stat-card">
          <div className="label">ACTIVE SIGNALS</div>
          <div className="value emerald">{activeSignals.length}</div>
          <div className="sub">{feedback.length} feedback rows</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">LIKELY LIVE EVENTS</div>
          <div className="value blue">{liveEvents.length || alignment.length}</div>
          <div className="sub">{resultedEvents.length} resulted</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">TELEMETRY SNAPSHOT</div>
          <div className="value purple">{latestTelemetry.length || telemetry.length}</div>
          <div className="sub">{uniqueCount(telemetry, "snapshot_ts")} snapshots</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">SETTLEMENT QUEUE</div>
          <div className="value gold">{pendingSettlement.length || settlement.length}</div>
          <div className="sub">waiting on lifecycle/results</div>
        </div>
      </div>

      <div className="edgeiq-command-layout">
        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">TOP EXECUTION SETUPS</div>
          <div className="edgeiq-mini-table">
            {topSetups.map((row, idx) => (
              <div className="edgeiq-mini-row" key={`${text(row.horse)}-${idx}`}>
                <span className="rank">{idx + 1}</span>
                <span className="horse">{text(row.horse || row.runner || row.selection) || "UNKNOWN"}</span>
                <span>{text(row.track)}</span>
                <span>{text(row.execution_state || row.final_execution_state || row.action) || "WATCH"}</span>
                <strong>{text(row.settlement_quality_score || row.execution_quality_score || row.edgeiq_score || row.confidence_score || row.edge_pct) || "-"}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">MARKET MOVEMENT WATCH</div>
          <div className="edgeiq-mini-table">
            {marketMoves.map((row, idx) => (
              <div className="edgeiq-mini-row" key={`${text(row.horse)}-${idx}`}>
                <span className="rank">{idx + 1}</span>
                <span className="horse">{text(row.horse || row.runner || row.selection) || "UNKNOWN"}</span>
                <span>{text(row.track)}</span>
                <span>{text(row.market_regime || row.regime || row.reaction_state) || "MARKET"}</span>
                <strong>{text(row.move_pct || row.price_move_pct || row.reaction_score || row.steam_score || row.volatility_score) || "-"}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">ADAPTIVE LEARNING</div>
          <div className="edgeiq-mini-table">
            {learningRows.map((row, idx) => (
              <div className="edgeiq-mini-row" key={`${text(row.horse)}-${idx}`}>
                <span className="rank">{idx + 1}</span>
                <span className="horse">{text(row.horse || row.signal || row.runner) || "SIGNAL"}</span>
                <span>{text(row.learning_tier || row.tier || row.status) || "LOW"}</span>
                <span>{text(row.track || row.regime || row.signal_family)}</span>
                <strong>{text(row.learning_score || row.clv_score || row.signal_score || row.edgeiq_score) || "-"}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="edgeiq-panel">
          <div className="edgeiq-panel-title">SYSTEM READINESS</div>
          <div className="edgeiq-system-list">
            <div><span>Feedback engine</span><strong className="emerald">{feedback.length ? "ONLINE" : "WAITING"}</strong></div>
            <div><span>Telemetry engine</span><strong className="emerald">{telemetry.length ? "ONLINE" : "WAITING"}</strong></div>
            <div><span>Reaction engine</span><strong className="emerald">{reaction.length ? "ONLINE" : "WAITING"}</strong></div>
            <div><span>Event alignment</span><strong className="blue">{alignment.length ? "TRACKING" : "WAITING"}</strong></div>
            <div><span>Settlement engine</span><strong className="gold">{settlement.length ? "ARMED" : "WAITING"}</strong></div>
          </div>
        </section>
      </div>
    </div>
  );
}
