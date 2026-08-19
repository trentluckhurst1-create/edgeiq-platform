
import type { OperationalEvidenceItem } from "../../services/operational-state";

type EvidenceDrawerProps = {
  activeEvidence: string;
  evidence: OperationalEvidenceItem[];
  onClose: () => void;
};

function confidenceLabel(confidence: number): string {
  if (confidence >= 80) return "HIGH";
  if (confidence >= 60) return "MEDIUM";
  if (confidence > 0) return "LOW";
  return "PENDING";
}

export function EvidenceDrawer({
  activeEvidence,
  evidence,
  onClose,
}: EvidenceDrawerProps) {
  const item = evidence.find((entry) => entry.title === activeEvidence);

  return (
    <aside className="eiq-command-drawer">
      <header>
        <h2>{item?.title || "Supporting Intelligence"}</h2>
        <button type="button" onClick={onClose}>×</button>
      </header>

      {item ? (
        <>
          <section>
            <span>Current Interpretation</span>
            <p>{item.summary}</p>
          </section>

          <section>
            <span>Evidence Category</span>
            <strong>{item.category.replace("_", " ")}</strong>
          </section>

          <section>
            <span>Operational Importance</span>
            <strong>{item.importance}/100</strong>
          </section>

          <section>
            <span>Feed Status</span>
            <strong className={item.status === "READY" ? "is-info" : "is-risk"}>
              {item.status}
            </strong>
          </section>

          <section>
            <span>Confidence</span>
            <strong className="is-info">{confidenceLabel(item.confidence)}</strong>
            <i className="eiq-command-confidence"><em /><em /><em /><em /><em /></i>
          </section>
        </>
      ) : (
        <p>Select a supporting evidence item.</p>
      )}
    </aside>
  );
}
