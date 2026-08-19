import type { OperationalEvidenceItem, OperationalRaceState } from "../../services/operational-state";

type IntelligenceExplorerProps = {
  raceState: OperationalRaceState;
  activeEvidence: string;
  onSelect: (title: string) => void;
};

function label(value: string): string {
  return value.split("_").join(" ");
}

function statusText(items: OperationalEvidenceItem[]): string {
  return items.some((item) => item.status === "READY") ? "Available" : "Building";
}

export function IntelligenceExplorer({ raceState, activeEvidence, onSelect }: IntelligenceExplorerProps) {
  const grouped = raceState.evidence.reduce<Record<string, OperationalEvidenceItem[]>>((acc, item) => {
    const key = item.category;
    acc[key] = acc[key] ?? [];
    acc[key].push(item);
    return acc;
  }, {});

  return (
    <section className="eiq-command-v4-explorer">
      <header>
        <span>Intelligence Explorer</span>
        <strong>{Object.keys(grouped).length} systems</strong>
      </header>

      <div className="eiq-command-v4-explorer__list">
        {Object.entries(grouped).map(([category, items]) => {
          const selected = items.some((item) => item.title === activeEvidence);

          return (
            <button
              key={category}
              type="button"
              className={selected ? "is-active" : ""}
              onClick={() => onSelect(items[0]?.title ?? "")}
            >
              <span>{label(category)}</span>
              <strong>{statusText(items)}</strong>
              <small>{items.length} observation{items.length === 1 ? "" : "s"}</small>
            </button>
          );
        })}
      </div>
    </section>
  );
}
