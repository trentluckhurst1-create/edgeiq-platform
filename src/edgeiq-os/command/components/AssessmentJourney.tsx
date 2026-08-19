import type { AssessmentJourneyModel } from "../../services/assessment-journey";
import { formatIntelligenceStatus } from "../../design-system";

type AssessmentJourneyProps = {
  journey: AssessmentJourneyModel;
};

function marker(status: string): string {
  return status === "READY" ? "✓" : "○";
}

export function AssessmentJourney({ journey }: AssessmentJourneyProps) {
  return (
    <section className="eiq-assessment-journey">
      <header>
        <span>Reasoning</span>
        <strong>{journey.title}</strong>
      </header>

      <div className="eiq-assessment-journey__path">
        {journey.stages.map((stage) => (
          <article key={stage.id}>
            <div className="eiq-assessment-journey__marker">{marker(stage.status)}</div>
            <div>
              <span>{formatIntelligenceStatus(stage.status)}</span>
              <strong>{stage.label}</strong>
              <p>{stage.summary}</p>
              <small>Watch: {stage.watch}</small>
            </div>
          </article>
        ))}

        <article className="is-decision">
          <div className="eiq-assessment-journey__marker">◎</div>
          <div>
            <span>Current Position</span>
            <strong>{journey.decision}</strong>
            <p>{journey.confidence} confidence. Maintain focus on the next material confirmation signal.</p>
          </div>
        </article>
      </div>
    </section>
  );
}
