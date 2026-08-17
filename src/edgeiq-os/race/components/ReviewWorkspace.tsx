import { buildReviewWorkspaceViewModel, type ReviewWorkspaceItem } from "../services/reviewWorkspaceData";
import type { RaceTab } from "./RaceWorkspace";
import {
  EiqBadge,
  EiqButton,
  EiqCard,
  EiqDataTable,
  EiqMetric,
  EiqPanel,
  EiqSectionHeader,
  EiqSidePanel,
  EiqStatusBadge,
} from "../../design-system/v1";

type ReviewWorkspaceProps = {
  raceBook: any;
  field: any[];
  selectedRaceKey?: string | null;
  clean: (value: any) => string;
  onOpenTab: (tab: RaceTab) => void;
};

function ReviewAction({ item, onOpenTab }: { item: ReviewWorkspaceItem; onOpenTab: (tab: RaceTab) => void }) {
  if (!item.actionTab || item.actionTab === "REVIEW") return <EiqBadge>Current</EiqBadge>;
  return (
    <EiqButton size="compact" onClick={() => onOpenTab(item.actionTab as RaceTab)}>
      Open {item.label}
    </EiqButton>
  );
}

export function ReviewWorkspace({ raceBook, field, selectedRaceKey, clean, onOpenTab }: ReviewWorkspaceProps) {
  const model = buildReviewWorkspaceViewModel(raceBook, field, selectedRaceKey);

  return (
    <section className="eiq-review-v2-workspace eiq-v1-standard-workspace">
      <EiqPanel className="eiq-review-v2-intro">
        <EiqSectionHeader
          eyebrow="REVIEW"
          title="Sectional and performance review"
          meta={<EiqStatusBadge status={model.status} />}
        />
        <p className="eiq-v1-analytical-copy">{model.raceLabel} | {model.raceName}</p>
      </EiqPanel>

      <section className="eiq-review-v2-meta">
        {model.meta.map((item) => (
          <EiqCard density="compact" key={item.label}>
            <EiqMetric label={item.label} value={clean(item.value)} />
          </EiqCard>
        ))}
      </section>

      <section className="eiq-review-v2-meta" aria-label="Post-race review modules">
        {["Winner", "Runners / Scratchings", "Sectional Summary", "Sectional Profile", "Runner Performance Snapshot", "Stewards / Notes"].map((label) => (
          <EiqCard density="compact" key={label}>
            <EiqMetric label={label} value="Pending result" />
          </EiqCard>
        ))}
      </section>

      <div className="eiq-review-v2-grid eiq-v1-analytical-grid">
        <EiqPanel className="eiq-v1-standard-table-panel">
          <EiqSectionHeader eyebrow="Review Structure" title="Race analysis modules" />
          <EiqDataTable
            density="compact"
            className="eiq-review-v2-table"
            wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}
          >
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
          </EiqDataTable>
        </EiqPanel>

        <EiqSidePanel className="eiq-v1-analytical-side-panel">
          <section className="eiq-v1-side-panel-section">
            <EiqSectionHeader eyebrow="Saved Review" title={model.savedState.title} />
            <p className="eiq-v1-analytical-copy">{model.savedState.detail}</p>
          </section>
        </EiqSidePanel>
      </div>

      <EiqPanel>
        <EiqSectionHeader eyebrow="Review Boundary" title="What EDGEiQ can show now" />
        <ul className="eiq-review-final__boundary eiq-v1-standard-list">
          {model.sourceBoundary.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </EiqPanel>
    </section>
  );
}
