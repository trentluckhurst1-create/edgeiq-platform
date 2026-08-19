
import type { OperationalRaceState } from "../../services/operational-state";

type EngineAgreementMatrixProps = {
  raceState: OperationalRaceState;
};

export function EngineAgreementMatrix({ raceState }: EngineAgreementMatrixProps) {
  return (
    <section className="eiq-engine-matrix">
      <header>
        <span>Engine Agreement</span>
        <strong>{raceState.correlation.agreementBand}</strong>
      </header>

      <div className="eiq-engine-matrix__grid">
        {raceState.feedHealth.map((feed) => {
          const coverage = raceState.coverage.find((item) => item.key === feed.key);
          const ready = feed.status === "READY";

          return (
            <article key={feed.key} className={ready ? "is-ready" : "is-partial"}>
              <span>{ready ? "✓" : "△"}</span>
              <strong>{feed.label}</strong>
              <small>{ready ? "Aligned" : "Pending"}</small>
              <em>{coverage?.coveragePct ?? 0}%</em>
            </article>
          );
        })}
      </div>
    </section>
  );
}
