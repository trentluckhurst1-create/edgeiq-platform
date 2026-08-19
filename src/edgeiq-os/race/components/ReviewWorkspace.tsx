import { buildReviewWorkspaceViewModel, type ReviewWorkspaceItem } from "../services/reviewWorkspaceData";
import type { RaceTab } from "./RaceWorkspace";

type ReviewWorkspaceProps = {
  raceBook: any;
  field: any[];
  selectedRaceKey?: string | null;
  clean: (value: any) => string;
  onOpenTab: (tab: RaceTab) => void;
};

function ReviewAction({ item, onOpenTab }: { item: ReviewWorkspaceItem; onOpenTab: (tab: RaceTab) => void }) {
  if (!item.actionTab || item.actionTab === "REVIEW") return <span className="eiq-review-final__muted">Current</span>;
  return (
    <button type="button" onClick={() => onOpenTab(item.actionTab as RaceTab)}>
      Open {item.label}
    </button>
  );
}

export function ReviewWorkspace({ raceBook, field, selectedRaceKey, clean, onOpenTab }: ReviewWorkspaceProps) {
  const model = buildReviewWorkspaceViewModel(raceBook, field, selectedRaceKey);

  return (
    <section className="eiq-review-final">
      <header className="eiq-review-final__header">
        <div>
          <span>REVIEW</span>
          <strong>Sectional and performance review</strong>
          <p>{model.raceLabel} | {model.raceName}</p>
        </div>
        <aside className={`eiq-review-final__status is-${model.statusTone}`}>
          <span>Status</span>
          <strong>{model.status}</strong>
        </aside>
      </header>

      <section className="eiq-review-final__meta">
        {model.meta.map((item) => (
          <div key={item.label}>
            <span>{item.label}</span>
            <strong>{clean(item.value)}</strong>
          </div>
        ))}
      </section>

      <section className="eiq-review-final__meta" aria-label="Post-race review modules">
        {["Winner", "Runners / Scratchings", "Sectional Summary", "Sectional Profile", "Runner Performance Snapshot", "Stewards / Notes"].map((label) => (
          <div key={label}>
            <span>{label}</span>
            <strong>Pending result</strong>
          </div>
        ))}
      </section>

      <div className="eiq-review-final__grid">
        <section className="eiq-review-final-panel eiq-review-final-table">
          <header>
            <span>Review Structure</span>
            <strong>Race analysis modules</strong>
          </header>
          <table>
            <thead>
              <tr>
                <th>Area</th>
                <th>State</th>
                <th>Detail</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {model.reviewableItems.map((item) => (
                <tr key={item.id}>
                  <th scope="row">{item.label}</th>
                  <td>{item.state}</td>
                  <td>{item.detail}</td>
                  <td><ReviewAction item={item} onOpenTab={onOpenTab} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <aside className="eiq-review-final-panel">
          <span>Saved Review</span>
          <strong>{model.savedState.title}</strong>
          <p>{model.savedState.detail}</p>
        </aside>
      </div>

      <section className="eiq-review-final-panel">
        <header>
          <span>Review Boundary</span>
          <strong>What EDGEiQ can show now</strong>
        </header>
        <ul className="eiq-review-final__boundary">
          {model.sourceBoundary.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
    </section>
  );
}
