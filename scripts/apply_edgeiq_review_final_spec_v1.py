from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SERVICE = r'''export type ReviewWorkspaceItem = {
  id: string;
  label: string;
  state: string;
  detail: string;
  actionTab?: "FORM GUIDE" | "MAP" | "MARKET" | "OVERVIEW" | "INSIGHTS" | "EPI" | "REVIEW";
};

export type ReviewWorkspaceViewModel = {
  raceLabel: string;
  raceName: string;
  status: string;
  statusTone: "ready" | "pending" | "unavailable";
  meta: Array<{ label: string; value: string }>;
  reviewableItems: ReviewWorkspaceItem[];
  savedState: {
    title: string;
    detail: string;
  };
  sourceBoundary: string[];
};

const UNAVAILABLE = "Unavailable";

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function value(...values: unknown[]): string {
  for (const item of values) {
    const text = clean(item);
    if (text) return text;
  }
  return UNAVAILABLE;
}

function upper(value: unknown): string {
  return clean(value).toUpperCase();
}

function hasObject(value: unknown): boolean {
  return Boolean(value && typeof value === "object" && Object.keys(value as Record<string, unknown>).length > 0);
}

function hasMarket(field: any[]): boolean {
  return field.some((runner) => clean(runner?.official?.market) || clean(runner?.source?.market) || clean(runner?.source?.live_price));
}

function resultState(raceBook: any): { label: string; tone: ReviewWorkspaceViewModel["statusTone"] } {
  const official = raceBook?.official ?? {};
  const source = raceBook?.source ?? {};
  const raw = upper(official.status || source.result_status || source.race_status || source.status);
  if (raw.includes("OFFICIAL") || raw.includes("UNOFFICIAL") || clean(source.winner) || clean(official.winner)) {
    return { label: raw.includes("UNOFFICIAL") ? "Result supplied" : "Official result supplied", tone: "ready" };
  }
  if (raw.includes("ABANDON")) return { label: "Race abandoned", tone: "unavailable" };
  return { label: "Awaiting result", tone: "pending" };
}

export function buildReviewWorkspaceViewModel(
  raceBook: any,
  field: any[],
  selectedRaceKey?: string | null,
): ReviewWorkspaceViewModel {
  const official = raceBook?.official ?? {};
  const source = raceBook?.source ?? {};
  const result = resultState(raceBook);
  const meeting = value(official.meeting, source.meeting, source.track);
  const raceNumber = value(official.raceNumber, source.race_no, source.raceNumber);
  const raceLabel = `${meeting} R${raceNumber.replace(/^R/i, "")}`;
  const raceName = value(official.raceName, source.race_name, source.name, raceLabel);
  const runnerCount = field.length || Number(clean(official.fieldSize || source.field_size || source.runners)) || 0;

  const items: ReviewWorkspaceItem[] = [];
  if (runnerCount > 0) {
    items.push({
      id: "field",
      label: "Form guide",
      state: "Available",
      detail: `${runnerCount} runners loaded for this race.`,
      actionTab: "FORM GUIDE",
    });
  }
  if (hasObject(raceBook?.intelligence)) {
    items.push({
      id: "overview",
      label: "Race intelligence",
      state: "Available",
      detail: "Race overview and current intelligence are available for review.",
      actionTab: "OVERVIEW",
    });
  }
  if (hasObject(raceBook?.map) || hasObject(raceBook?.raceMap) || hasObject(raceBook?.intelligence?.map)) {
    items.push({
      id: "map",
      label: "Speed map",
      state: "Available",
      detail: "Race shape and settling-position work is available.",
      actionTab: "MAP",
    });
  }
  if (hasMarket(field)) {
    items.push({
      id: "market",
      label: "Market worksheet",
      state: "Available",
      detail: "Market values exist in the current field feed.",
      actionTab: "MARKET",
    });
  }
  if (result.tone === "ready") {
    items.push({
      id: "result",
      label: "Result review",
      state: "Ready",
      detail: "Result data has been supplied for this race.",
      actionTab: "REVIEW",
    });
  }

  if (!items.length) {
    items.push({
      id: "none",
      label: "Review record",
      state: "Unavailable",
      detail: "No reviewable race work has been created for this context.",
    });
  }

  return {
    raceLabel,
    raceName,
    status: result.label,
    statusTone: result.tone,
    meta: [
      { label: "Race Key", value: value(selectedRaceKey, official.raceKey, source.race_key) },
      { label: "Distance", value: value(official.distance, source.distance) },
      { label: "Class", value: value(official.raceClass, source.class, source.race_class) },
      { label: "Track", value: value(official.trackCondition, source.track_condition) },
      { label: "Rail", value: value(official.rail, source.rail) },
      { label: "Field", value: runnerCount ? String(runnerCount) : UNAVAILABLE },
    ],
    reviewableItems: items,
    savedState: {
      title: "No saved review record",
      detail: "Review persistence is not connected for this race, so EDGEiQ is not showing saved notes or completed analysis that the product has not created.",
    },
    sourceBoundary: [
      "Review only displays race work already available in the current product state.",
      "Official result analysis remains held until a result is supplied.",
      "No saved item is shown without a real saved record.",
    ],
  };
}
'''

COMPONENT = r'''import { buildReviewWorkspaceViewModel, type ReviewWorkspaceItem } from "../services/reviewWorkspaceData";
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
          <strong>Race review workspace</strong>
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

      <div className="eiq-review-final__grid">
        <section className="eiq-review-final-panel eiq-review-final-table">
          <header>
            <span>Reviewable Work</span>
            <strong>Available product state</strong>
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
'''

CSS = r'''

/* EDGEIQ REVIEW FINAL SPEC V1 */
.eiq-review-final {
  display: grid;
  gap: 16px;
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-review-final__header,
.eiq-review-final__meta,
.eiq-review-final-panel {
  background: var(--edgeiq-surface, #ffffff);
  border: 1px solid var(--edgeiq-border, #d9e2ec);
  border-radius: 14px;
  box-shadow: 0 10px 28px rgba(15, 31, 48, 0.06);
}

.eiq-review-final__header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 18px;
}

.eiq-review-final__header span,
.eiq-review-final__meta span,
.eiq-review-final-panel > span,
.eiq-review-final-panel > header span {
  display: block;
  color: var(--edgeiq-primary, #1167b1);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-review-final__header strong {
  display: block;
  margin-top: 6px;
  color: var(--edgeiq-text-primary, #172033);
  font-size: 24px;
}

.eiq-review-final__header p,
.eiq-review-final-panel p {
  margin: 8px 0 0;
  color: var(--edgeiq-text-secondary, #5f6f82);
  line-height: 1.45;
}

.eiq-review-final__status {
  min-width: 190px;
  border-left: 1px solid var(--edgeiq-border, #d9e2ec);
  padding-left: 18px;
}

.eiq-review-final__status strong {
  font-size: 18px;
}

.eiq-review-final__status.is-ready strong {
  color: #126b45;
}

.eiq-review-final__status.is-pending strong {
  color: #84620d;
}

.eiq-review-final__status.is-unavailable strong {
  color: #8a3342;
}

.eiq-review-final__meta {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0;
  overflow: hidden;
}

.eiq-review-final__meta div {
  min-height: 68px;
  display: grid;
  align-content: center;
  gap: 5px;
  padding: 12px 14px;
  border-right: 1px solid var(--edgeiq-border, #d9e2ec);
}

.eiq-review-final__meta div:last-child {
  border-right: 0;
}

.eiq-review-final__meta strong {
  color: var(--edgeiq-text-primary, #172033);
  font-size: 14px;
}

.eiq-review-final__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
}

.eiq-review-final-panel {
  padding: 16px;
}

.eiq-review-final-panel > strong,
.eiq-review-final-panel > header strong {
  display: block;
  margin-top: 6px;
  color: var(--edgeiq-text-primary, #172033);
  font-size: 18px;
}

.eiq-review-final-table {
  overflow: hidden;
  padding: 0;
}

.eiq-review-final-table > header {
  padding: 14px 16px;
  border-bottom: 1px solid var(--edgeiq-border, #d9e2ec);
}

.eiq-review-final-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.eiq-review-final-table th,
.eiq-review-final-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--edgeiq-border, #d9e2ec);
  color: var(--edgeiq-text-primary, #172033);
  text-align: left;
  vertical-align: top;
}

.eiq-review-final-table thead th {
  background: var(--edgeiq-page-bg, #f5f8fb);
  color: var(--edgeiq-text-secondary, #5f6f82);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.eiq-review-final-table tbody th {
  color: var(--edgeiq-primary, #1167b1);
}

.eiq-review-final-table button {
  border: 1px solid var(--edgeiq-primary, #1167b1);
  border-radius: 9px;
  background: #ffffff;
  color: var(--edgeiq-primary, #1167b1);
  font: inherit;
  font-weight: 800;
  padding: 7px 10px;
}

.eiq-review-final__muted {
  color: var(--edgeiq-text-secondary, #5f6f82);
}

.eiq-review-final__boundary {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
  padding-left: 18px;
  color: var(--edgeiq-text-primary, #172033);
}

@media (max-width: 1100px) {
  .eiq-review-final__grid,
  .eiq-review-final__meta {
    grid-template-columns: 1fr;
  }

  .eiq-review-final__meta div {
    border-right: 0;
    border-bottom: 1px solid var(--edgeiq-border, #d9e2ec);
  }
}
'''

AUDIT = r'''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
component = ROOT / "src/edgeiq-os/race/components/ReviewWorkspace.tsx"
service = ROOT / "src/edgeiq-os/race/services/reviewWorkspaceData.ts"
race_workspace = ROOT / "src/edgeiq-os/race/components/RaceWorkspace.tsx"
css = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"

def fail(message: str) -> None:
    raise SystemExit(f"EDGEIQ_REVIEW_FINAL_SPEC_AUDIT_FAIL: {message}")

component_text = component.read_text(encoding="utf-8")
service_text = service.read_text(encoding="utf-8")
race_text = race_workspace.read_text(encoding="utf-8")
css_text = css.read_text(encoding="utf-8")

for token in ["Race review workspace", "Reviewable Work", "Saved Review", "Review Boundary"]:
    if token not in component_text:
        fail(f"missing component token {token}")

for token in ["buildReviewWorkspaceViewModel", "No saved review record", "No saved item is shown without a real saved record"]:
    if token not in service_text:
        fail(f"missing service token {token}")

if "<ReviewWorkspace" not in race_text:
    fail("RaceWorkspace does not render ReviewWorkspace")

for token in ["Race review pending", "review pending", "fake", "mock", "demo", "recommendation", "tip", "bet", "developer log", "activity feed", "Confidence", "confidence"]:
    if token in component_text or token in service_text:
        fail(f"rejected review token remains {token}")

if "EDGEIQ REVIEW FINAL SPEC V1" not in css_text:
    fail("missing review css marker")

report = ROOT / "docs/full-product-implementation/EDGEIQ_REVIEW_FINAL_SPEC_V1_AUDIT.md"
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(
    "\n".join(
        [
            "# EDGEiQ Review Final Spec V1 Audit",
            "",
            "Status: EDGEIQ_REVIEW_FINAL_SPEC_AUDIT_PASS",
            "",
            "- Review placeholder replaced with a governed review boundary.",
            "- Saved review state is honest where persistence is not connected.",
            "- Reviewable work is derived from current product state only.",
            "- Rejected product language was not found.",
            "- White theme review styling is present.",
            "",
        ]
    ),
    encoding="utf-8",
)
print("EDGEIQ_REVIEW_FINAL_SPEC_AUDIT_PASS")
'''

def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")

def append_once(path: str, marker: str, text: str) -> None:
    target = ROOT / path
    current = target.read_text(encoding="utf-8")
    if marker not in current:
        target.write_text(current.rstrip() + "\n" + text.lstrip(), encoding="utf-8")

def patch_race_workspace() -> None:
    target = ROOT / "src/edgeiq-os/race/components/RaceWorkspace.tsx"
    text = target.read_text(encoding="utf-8")
    if 'import { ReviewWorkspace } from "./ReviewWorkspace";' not in text:
        text = text.replace('import { RaceFormGuideWorkspace } from "./RaceFormGuideWorkspace";\n', 'import { RaceFormGuideWorkspace } from "./RaceFormGuideWorkspace";\nimport { ReviewWorkspace } from "./ReviewWorkspace";\n')

    old = '''      ) : tab === "REVIEW" ? (
        <section className="eiq-workspace-panel eiq-review-workspace-shell">
          <div className="eiq-workspace-panel__title">
            <span>REVIEW</span>
            <strong>Race review pending</strong>
            <p>Review becomes available after official results are received.</p>
          </div>
          <div className="eiq-workspace-unavailable eiq-review-pending-state">
            <strong>Pre-race state</strong>
            <p>Official placings, margins, sectionals and expected-versus-actual analysis are deliberately held back until the result feed confirms this race.</p>
            <dl>
              <div><dt>Race</dt><dd>{clean(official.meeting)} R{clean(official.raceNumber)}</dd></div>
              <div><dt>Status</dt><dd>Awaiting official result</dd></div>
              <div><dt>Sectionals</dt><dd>Pending result feed</dd></div>
              <div><dt>Review</dt><dd>Not yet available</dd></div>
            </dl>
          </div>
        </section>
'''
    new = '''      ) : tab === "REVIEW" ? (
        <ReviewWorkspace
          raceBook={raceBook}
          field={field}
          selectedRaceKey={clean(official.raceKey) || selectedRaceKey}
          clean={clean}
          onOpenTab={setTab}
        />
'''
    if old not in text:
        raise RuntimeError("Review placeholder block not found in RaceWorkspace.")
    target.write_text(text.replace(old, new), encoding="utf-8")

write("src/edgeiq-os/race/services/reviewWorkspaceData.ts", SERVICE)
write("src/edgeiq-os/race/components/ReviewWorkspace.tsx", COMPONENT)
append_once("src/edgeiq-os/styles/edgeiqOsV2.css", "EDGEIQ REVIEW FINAL SPEC V1", CSS)
write("scripts/audit_edgeiq_review_final_spec_v1.py", AUDIT)
patch_race_workspace()

print("EDGEIQ_REVIEW_FINAL_SPEC_APPLIED")
