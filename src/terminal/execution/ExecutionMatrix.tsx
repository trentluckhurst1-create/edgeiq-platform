import { useMemo, useState } from "react";

type RunnerRow = Record<string, any>;

type Props = {
  runners: RunnerRow[];
  executionRows?: RunnerRow[];
};

const FILTERS = ["ALL", "PRIORITY", "EXECUTE", "WATCH", "PASS"] as const;

function text(value: unknown): string {
  return String(value ?? "").trim();
}

function num(value: unknown): number | null {
  const raw = text(value).replace("%", "");
  if (!raw) return null;

  const parsed = Number(raw);

  return Number.isFinite(parsed) ? parsed : null;
}

function compact(value: unknown): string {
  return text(value).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function money(value: unknown): string {
  const parsed = num(value);

  if (parsed === null || parsed <= 0) {
    return "-";
  }

  if (parsed >= 100) {
    return parsed.toFixed(0);
  }

  if (parsed >= 10) {
    return parsed.toFixed(1);
  }

  return parsed.toFixed(2);
}

function pct(value: unknown): string {
  const parsed = num(value);

  if (parsed === null) {
    return "-";
  }

  return parsed.toFixed(1);
}

function whole(value: unknown): string {
  const parsed = num(value);

  if (parsed === null) {
    return "-";
  }

  return parsed.toFixed(0);
}

function keyOf(row: RunnerRow): string {
  return [
    text(row.race_date ?? row.raceDate),
    text(row.track),
    text(row.race_no ?? row.raceNo),
    compact(row.horse ?? row.runner ?? row.selection),
  ].join("|");
}

function getMarketPrice(row: RunnerRow): number | null {
  return (
    num(row.best_odds) ??
    num(row.market_price) ??
    num(row.marketPrice) ??
    num(row.price) ??
    num(row.odds) ??
    null
  );
}

function getRatedPrice(row: RunnerRow): number | null {
  return (
    num(row.rated_price) ??
    num(row.ratedPrice) ??
    num(row.model_price) ??
    num(row.edgeiq_price) ??
    num(row.fair_price) ??
    null
  );
}

function getOverlay(row: RunnerRow): number {
  const explicit =
    num(row.overlay_score) ??
    num(row.overlay_pct) ??
    num(row.edge_pct) ??
    num(row.edgePct) ??
    num(row.value_pct) ??
    num(row.expected_value_pct) ??
    num(row.ev_pct);

  if (explicit !== null) {
    return explicit;
  }

  const market = getMarketPrice(row);
  const rated = getRatedPrice(row);

  if (!market || !rated || market <= 0 || rated <= 0) {
    return 0;
  }

  return ((market - rated) / rated) * 100;
}


function movementState(row: RunnerRow): string {
  const current =
    num(row.best_odds) ??
    num(row.market_price) ??
    num(row.marketPrice) ??
    num(row.price);

  const previous =
    num(row.previous_price) ??
    num(row.opening_price) ??
    num(row.prev_price) ??
    num(row.last_price);

  if (current === null || previous === null) {
    return "neutral";
  }

  const delta = current - previous;

  if (delta <= -0.25) return "steam";
  if (delta >= 0.25) return "drift";

  return "neutral";
}

function movementLabel(state: string): string {
  switch (state) {
    case "steam":
      return "STEAM";
    case "drift":
      return "DRIFT";
    default:
      return "HOLD";
  }
}


function getConfidence(row: RunnerRow): number {
  return (
    num(row.confidence_score) ??
    num(row.model_confidence) ??
    num(row.rating_confidence) ??
    num(row.execution_confidence) ??
    num(row.execution_quality_score) ??
    num(row.settlement_quality_score) ??
    0
  );
}

function getMarketRank(row: RunnerRow): number {
  return (
    num(row.market_rank) ??
    num(row.modelRank) ??
    999
  );
}

function getExecutionState(row: RunnerRow): string {
  return text(
    row.execution_state ??
    row.final_execution_state ??
    row.action ??
    row.signal_state ??
    ""
  ).toUpperCase();
}

function mergeExecution(
  runner: RunnerRow,
  executionRows: RunnerRow[]
): RunnerRow {
  const fullKey = keyOf(runner);
  const horseKey = compact(runner.horse);

  const exact = executionRows.find((row) => keyOf(row) === fullKey);

  if (exact) {
    return {
      ...runner,
      ...exact,
      horse: runner.horse,
      jockey: runner.jockey,
      barrier: runner.barrier,
      isScratched: runner.isScratched,
    };
  }

  const loose = executionRows.find((row) => {
    const executionHorse = compact(row.horse ?? row.runner ?? row.selection);
    return executionHorse && executionHorse === horseKey;
  });

  if (loose) {
    return {
      ...runner,
      ...loose,
      horse: runner.horse,
      jockey: runner.jockey,
      barrier: runner.barrier,
      isScratched: runner.isScratched,
    };
  }

  return runner;
}

function executionTier(row: RunnerRow): string {
  const state = getExecutionState(row);
  const overlay = getOverlay(row);
  const confidence = getConfidence(row);

  if (state.includes("PRIORITY")) return "PRIORITY";
  if (state.includes("EXECUTE")) return "EXECUTE";
  if (state.includes("WATCH")) return "WATCH";
  if (state.includes("MONITOR")) return "WATCH";
  if (state.includes("LEAN")) return "WATCH";
  if (state.includes("PASS")) return "PASS";

  if (overlay >= 15 && confidence >= 80) return "PRIORITY";
  if (overlay >= 10 && confidence >= 65) return "EXECUTE";
  if (overlay >= 5) return "WATCH";

  return "PASS";
}

function tierClass(tier: string): string {
  switch (tier) {
    case "PRIORITY":
      return "priority";
    case "EXECUTE":
      return "execute";
    case "WATCH":
      return "watch";
    default:
      return "pass";
  }
}

function overlayClass(value: number): string {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

function confidenceClass(value: number): string {
  return value >= 70 ? "high" : "low";
}


function overlayVelocity(row: RunnerRow): number {
  const current =
    num(row.overlay_pct) ??
    num(row.overlay_score) ??
    num(row.edge_pct) ??
    num(row.edgePct);

  const previous =
    num(row.previous_overlay_pct) ??
    num(row.prev_overlay_pct) ??
    num(row.last_overlay_pct) ??
    num(row.opening_overlay_pct);

  if (current === null || previous === null) {
    return 0;
  }

  return current - previous;
}

function velocityLabel(value: number): string {
  if (value >= 5) return "BUILDING";
  if (value <= -5) return "COLLAPSING";
  return "STABLE";
}

function velocityClass(value: number): string {
  if (value >= 5) return "building";
  if (value <= -5) return "collapsing";
  return "stable";
}

function reasonStack(row: RunnerRow): string[] {
  const reasons: string[] = [];
  const state = getExecutionState(row);
  const overlay = getOverlay(row);
  const confidence = getConfidence(row);

  const regime = text(
    row.market_regime ??
    row.regime ??
    row.temporal_regime ??
    row.reaction_regime
  );

  const timing = text(
    row.timing_quality ??
    row.execution_timing ??
    row.timing_state
  );

  const volatility = text(
    row.volatility_state ??
    row.market_volatility ??
    row.volatility
  );

  const clv = text(
    row.clv_state ??
    row.learning_tier ??
    row.clv_tier
  );

  if (state) reasons.push(state);
  if (overlay >= 15) reasons.push("Major overlay");
  else if (overlay >= 10) reasons.push("Strong overlay");
  else if (overlay >= 5) reasons.push("Value watch");

  if (confidence >= 85) reasons.push("Elite confidence");
  else if (confidence >= 70) reasons.push("Strong confidence");
  else if (confidence >= 55) reasons.push("Developing confidence");

  if (regime) reasons.push(`Regime: ${regime}`);
  if (timing) reasons.push(`Timing: ${timing}`);
  if (volatility) reasons.push(`Vol: ${volatility}`);
  if (clv) reasons.push(`Learning: ${clv}`);

  if (!reasons.length) reasons.push("No active execution trigger");

  return reasons.slice(0, 5);
}

export default function ExecutionMatrix({
  runners,
  executionRows = [],
}: Props) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");

  const mergedRows = useMemo(() => {
    return [...runners]
      .filter((row) => !row.isScratched)
      .map((row) => mergeExecution(row, executionRows));
  }, [runners, executionRows]);

  const counts = useMemo(() => {
    return FILTERS.reduce((acc, item) => {
      acc[item] =
        item === "ALL"
          ? mergedRows.length
          : mergedRows.filter((row) => executionTier(row) === item).length;

      return acc;
    }, {} as Record<(typeof FILTERS)[number], number>);
  }, [mergedRows]);

  const sorted = useMemo(() => {
    return [...mergedRows]
      .filter((row) => filter === "ALL" || executionTier(row) === filter)
      .sort((a, b) => {
        const tierOrder: Record<string, number> = {
          PRIORITY: 0,
          EXECUTE: 1,
          WATCH: 2,
          PASS: 3,
        };

        const ta = tierOrder[executionTier(a)] ?? 9;
        const tb = tierOrder[executionTier(b)] ?? 9;

        if (ta !== tb) return ta - tb;

        const oa = getOverlay(a);
        const ob = getOverlay(b);

        if (ob !== oa) return ob - oa;

        return getMarketRank(a) - getMarketRank(b);
      });
  }, [mergedRows, filter]);

  return (
    <div className="edgeiq-execution-matrix">
      <div className="edgeiq-execution-filters">
        {FILTERS.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setFilter(item)}
            className={filter === item ? "active" : ""}
          >
            <span>{item}</span>
            <strong>{counts[item] ?? 0}</strong>
          </button>
        ))}
      </div>

      <div className="edgeiq-matrix-header">
        <div>#</div>
        <div>RUNNER</div>
        <div>PRICE</div>
        <div>RATED</div>
        <div>OVERLAY</div>
        <div>CONF</div>
        <div>TIER</div>
      </div>

      {sorted.map((row, idx) => {
        const market = getMarketPrice(row);
        const rated = getRatedPrice(row);
        const overlay = getOverlay(row);
        const confidence = getConfidence(row);
        const velocity = overlayVelocity(row);
        const tier = executionTier(row);
        const reasons = reasonStack(row);

        return (
          <div
            key={`${text(row.horse)}-${idx}`}
            className={`edgeiq-matrix-row ${tierClass(tier)}`}
          >
            <div className="rank">{idx + 1}</div>

            <div className="runner">
              <div className="horse">{text(row.horse)}</div>

              <div className="meta">
                {text(row.barrier) ? `B${text(row.barrier)}` : "-"} -{" "}
                {text(row.jockey) || "JOCKEY TBC"}
              </div>

              <div className="reason-stack">
                {reasons.map((reason) => (
                  <span key={reason}>{reason}</span>
                ))}
              </div>
            </div>

            <div className="price">{money(market)}</div>
            <div className="rated">{money(rated)}</div>
            <div className="overlay-stack">
              <div className={`overlay ${overlayClass(overlay)}`}>
                {pct(overlay)}
              </div>

              <div className={`movement-chip ${movementState(row)}`}>
                {movementLabel(movementState(row))}
              </div>

              <div className={`velocity-chip ${velocityClass(velocity)}`}>
                {velocityLabel(velocity)}
              </div>
            </div>
            <div className={`confidence ${confidenceClass(confidence)}`}>
              {whole(confidence)}
            </div>
            <div className={`tier ${tierClass(tier)}`}>{tier}</div>
          </div>
        );
      })}
    </div>
  );
}
