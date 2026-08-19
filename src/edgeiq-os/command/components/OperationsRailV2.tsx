import type { OperationalRaceState } from "../../services/operational-state";
import { formatDecisionState, formatConfidenceLabel } from "../../design-system";

type OperationsRailV2Props = {
  raceState: OperationalRaceState;
};

export function OperationsRailV2({ raceState }: OperationsRailV2Props) {
  const ready = raceState.feedHealth.filter((engine) => engine.status === "READY");
  const waiting = raceState.feedHealth.filter((engine) => engine.status !== "READY");

  return (
    <section className="eiq-command-v5-rail">
      <header>
        <span>System</span>
        <strong>{ready.length}/{raceState.feedHealth.length}</strong>
      </header>

      <div className="eiq-command-v5-rail__list">
        {ready.map((engine) => (
          <article key={engine.key}>
            <i className="is-ready" />
            <strong>{engine.label}</strong>
          </article>
        ))}

        {waiting.map((engine) => (
          <article key={engine.key}>
            <i />
            <strong>{engine.label}</strong>
          </article>
        ))}
      </div>

      <footer>
        <span>Position</span>
        <strong>{formatDecisionState(raceState.decision.state)}</strong>
        <small>{formatConfidenceLabel(raceState.confidence)} confidence</small>
      </footer>
    </section>
  );
}
