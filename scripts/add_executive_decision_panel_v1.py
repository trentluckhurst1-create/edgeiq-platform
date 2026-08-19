from pathlib import Path

component = Path("src/edgeiq-os/command/components/ExecutiveDecisionPanel.tsx")

component.write_text(r'''
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
''', encoding="utf-8")

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = workspace.read_text(encoding="utf-8")

if 'ExecutiveDecisionPanel' not in text:
    text = text.replace(
        'import { CommandBlock } from "./components/CommandBlock";',
        'import { CommandBlock } from "./components/CommandBlock";\nimport { ExecutiveDecisionPanel } from "./components/ExecutiveDecisionPanel";'
    )

if "<ExecutiveDecisionPanel" not in text:
    text = text.replace(
'''          <div className="eiq-command-live__content">''',
'''          <div className="eiq-command-live__content">
            <ExecutiveDecisionPanel summary={raceState.executiveSummary} />'''
    )

workspace.write_text(text, encoding="utf-8")

print("[EDGEIQ] ExecutiveDecisionPanel created and mounted")
