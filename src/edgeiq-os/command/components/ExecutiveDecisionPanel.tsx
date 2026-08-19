
import type { ExecutiveSummary } from "../../services/operational-state";

type ExecutiveDecisionPanelProps = {
  summary: ExecutiveSummary;
};

export function ExecutiveDecisionPanel({ summary }: ExecutiveDecisionPanelProps) {
  const decision = summary.decision;

  return (
    <section className="eiq-executive-decision">
      <header>
        <span>Executive Decision</span>
        <strong>{decision.state}</strong>
      </header>

      <div className="eiq-executive-decision__hero">
        <div>
          <small>Priority</small>
          <b>{decision.priority}</b>
        </div>

        <div>
          <small>Confidence</small>
          <b>{decision.confidence}%</b>
        </div>

        <div>
          <small>Agreement</small>
          <b>{summary.correlation.agreementScore}%</b>
        </div>

        <div>
          <small>Coverage</small>
          <b>{summary.systemHealth.coverage}%</b>
        </div>
      </div>

      <p>{summary.headline}</p>
      <small>{summary.summary}</small>

      <div className="eiq-executive-decision__findings">
        {summary.topFindings.map((finding) => (
          <article key={finding.id}>
            <span>{finding.priority}</span>
            <strong>{finding.title}</strong>
            <p>{finding.summary}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
