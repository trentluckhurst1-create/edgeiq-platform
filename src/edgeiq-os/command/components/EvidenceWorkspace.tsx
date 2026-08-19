import type { OperationalEvidenceItem } from "../../services/operational-state";

type EvidenceWorkspaceProps = {
  evidence: OperationalEvidenceItem[];
  activeEvidence: string;
};

function label(value: string): string {
  return value.split("_").join(" ");
}

function statusText(value: string): string {
  return value === "READY" ? "Confirmed" : "Still building";
}

export function EvidenceWorkspace({ evidence, activeEvidence }: EvidenceWorkspaceProps) {
  const item = evidence.find((entry) => entry.title === activeEvidence) ?? evidence[0];

  if (!item) {
    return (
      <section className="eiq-command-v4-evidence">
        <header><span>Why This Decision</span><strong>No intelligence selected</strong></header>
      </section>
    );
  }

  return (
    <section className="eiq-command-v4-evidence">
      <header>
        <span>Why This Decision</span>
        <strong>{label(item.category)}</strong>
      </header>

      <article>
        <span>{statusText(item.status)}</span>
        <h3>{item.title}</h3>
        <p>{item.summary}</p>
      </article>

      <div className="eiq-command-v4-evidence__metrics">
        <div><span>Confidence</span><strong>{item.confidence}</strong></div>
        <div><span>Influence</span><strong>{item.importance}/100</strong></div>
        <div><span>Assessment</span><strong>{statusText(item.status)}</strong></div>
      </div>
    </section>
  );
}
