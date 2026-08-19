from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE08_MAP_{STAMP}"
MAP = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"

CHECKPOINT.mkdir(parents=True, exist_ok=True)
for path in (MAP, CSS):
    shutil.copy2(path, CHECKPOINT / path.name)

text = MAP.read_text(encoding="utf-8")
text = text.replace('import { resolveTrackMapAsset } from "../services/trackMapAssets";\n', "")

start = text.find("function MapVisual(")
end = text.find("function MapTable(", start)
if start < 0 or end < 0:
    raise SystemExit("Expected MapVisual/MapTable anchors not found; source changed unexpectedly.")

new_map_visual = r'''function MapVisual({
  rows,
  onOpenRunner,
}: {
  rows: BETA009Row[];
  onOpenRunner?: (runner: RaceFieldRunner) => void;
}) {
  const barrierRows = rows.map((row) => {
    const barrier = barrierNumber(row);
    return { row, barrier };
  });

  return (
    <section className="eiq-map-v1-panel eiq-map-v1-visual-panel">
      <div className="eiq-map-v1-panel__title">
        <span>Race Map - Predicted Settling Positions</span>
        <small>Victorian orientation. Barrier 1 bottom. Travel right to left.</small>
      </div>
      <div className="eiq-map-v1-direction" aria-hidden="true">
        <span>Racing direction</span>
        <strong>←</strong>
      </div>
      <div className="eiq-map-v1-visual" data-map-orientation="victorian-right-to-left">
        <div className="eiq-map-v1-visual__surface">
          {barrierRows.map(({ row }) => {
            const runner = row.runner as RaceFieldRunner | null | undefined;
            const speed = rowSpeed(row);
            const hasEvidence = rowHasMapEvidence(row);
            return (
              <button
                type="button"
                className={`eiq-map-v1-runner-line${hasEvidence ? "" : " is-unavailable"}`}
                style={mapLineStyle(row)}
                key={`${rowNumber(row)}-${rowRunnerName(row)}`}
                onClick={() => runner && onOpenRunner?.(runner)}
                disabled={!runner}
                aria-label={`${rowNumber(row)} ${rowRunnerName(row)} ${rowEvidenceLabel(row)}`}
              >
                <span className="eiq-map-v1-runner-line__bar" aria-hidden="true" />
                <span className="eiq-map-v1-runner-line__label">
                  <strong>{rowNumber(row)}</strong>
                  <em>{rowRunnerName(row)}</em>
                  {speed ? <span>{speed}</span> : null}
                </span>
              </button>
            );
          })}
        </div>
        <div className="eiq-map-v1-barriers" aria-label="Barriers">
          {barrierRows.map(({ row, barrier }) => (
            <span key={`barrier-${rowNumber(row)}-${rowRunnerName(row)}`}>{barrier ?? "-"}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

'''

text = text[:start] + new_map_visual + text[end:]

start = text.find("function TrackAssetPanel(")
end = text.find("function RunnerMap(", start)
if start < 0 or end < 0:
    raise SystemExit("Expected TrackAssetPanel/RunnerMap anchors not found; source changed unexpectedly.")

new_side = r'''function MapReadPanel({ viewModel }: { viewModel: BETA009ViewModel }) {
  const mappedRows = viewModel.rows.filter((row) => rowHasMapEvidence(row));
  const leaders = mappedRows
    .filter((row) => rowValue(row.run_style).toUpperCase().includes("LEAD"))
    .slice(0, 3);
  const onPace = mappedRows
    .filter((row) => /PACE|FORWARD/i.test(rowValue(row.run_style)))
    .slice(0, 3);
  const pendingCount = Math.max(0, viewModel.rows.length - mappedRows.length);

  return (
    <aside className="eiq-map-v1-side">
      <section className="eiq-map-v1-panel">
        <div className="eiq-map-v1-panel__title"><span>Race Shape Summary</span></div>
        <dl className="eiq-map-v1-facts">
          <div><dt>Active Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Position Reads</dt><dd>{mappedRows.length}</dd></div>
          <div><dt>Awaiting Evidence</dt><dd>{pendingCount}</dd></div>
          <div><dt>Map Status</dt><dd>{viewModel.status === "current" ? "Current" : "Governed Pending"}</dd></div>
        </dl>
      </section>
      <section className="eiq-map-v1-panel">
        <div className="eiq-map-v1-panel__title"><span>Tactical Notes</span></div>
        {mappedRows.length ? (
          <ul className="eiq-map-v1-notes">
            <li>Settling positions use governed speed/map reads where available.</li>
            <li>Barriers are compressed after scratchings and shown high-to-low.</li>
            <li>Plain blue lanes show race orientation without heat-map colouring.</li>
          </ul>
        ) : (
          <p className="eiq-map-v1-copy">
            Governed speed-position evidence is pending. Barrier order remains available for race-shape review.
          </p>
        )}
      </section>
      <section className="eiq-map-v1-panel">
        <div className="eiq-map-v1-panel__title"><span>Key Runner Positions</span></div>
        <div className="eiq-map-v1-key-positions">
          <div>
            <span>Leaders</span>
            <strong>{leaders.map(rowRunnerName).join(", ") || "Pending"}</strong>
          </div>
          <div>
            <span>On pace</span>
            <strong>{onPace.map(rowRunnerName).join(", ") || "Pending"}</strong>
          </div>
          <div>
            <span>Evidence</span>
            <strong>{mappedRows.length ? "Governed map feed" : "Barrier order only"}</strong>
          </div>
        </div>
      </section>
    </aside>
  );
}

'''

text = text[:start] + new_side + text[end:]
text = text.replace("<MapReadPanel viewModel={viewModel} raceBook={props.raceBook} race={race} />", "<MapReadPanel viewModel={viewModel} />")
text = text.replace("<h3>How will this race be run?</h3>\n          <span>Victorian orientation. Barriers right. Active runners only.</span>", "<h3>How will this race be run?</h3>\n          <span>Traditional barrier map. Right-to-left travel. Plain blue lanes.</span>")

MAP.write_text(text, encoding="utf-8", newline="\n")

css = CSS.read_text(encoding="utf-8")
addition = r'''

/* EDGEIQ APPROVED UI PHASE 08 MAP */
.eiq-race-workspace--map .eiq-map-v1 {
  gap: 10px;
}

.eiq-race-workspace--map .eiq-map-v1-hero {
  min-height: 74px;
  padding: 12px 16px;
  border-radius: 5px;
}

.eiq-race-workspace--map .eiq-map-v1-hero h3 {
  font-size: 21px;
}

.eiq-race-workspace--map .eiq-map-v1-grid {
  grid-template-columns: minmax(0, 1fr) 294px;
  gap: 10px;
  align-items: stretch;
}

.eiq-race-workspace--map .eiq-map-v1-panel {
  border-radius: 5px;
  background: #ffffff;
  border: 1px solid var(--eiq-approved-line);
  box-shadow: none;
}

.eiq-race-workspace--map .eiq-map-v1-panel__title {
  min-height: 36px;
  padding: 0 10px;
  border-bottom: 1px solid var(--eiq-approved-line);
}

.eiq-race-workspace--map .eiq-map-v1-panel__title span {
  color: var(--eiq-approved-blue);
  font-size: 11px;
  letter-spacing: 0.08em;
}

.eiq-race-workspace--map .eiq-map-v1-panel__title small {
  color: var(--eiq-approved-muted);
  font-size: 10px;
}

.eiq-race-workspace--map .eiq-map-v1-direction {
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--eiq-approved-navy);
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.eiq-race-workspace--map .eiq-map-v1-direction strong {
  color: var(--eiq-approved-blue);
  font-size: 20px;
  line-height: 1;
}

.eiq-race-workspace--map .eiq-map-v1-visual {
  min-height: 448px;
  padding: 0 14px 14px;
  grid-template-columns: minmax(0, 1fr) 36px;
  background:
    linear-gradient(90deg, rgba(37, 99, 235, 0.05) 0 1px, transparent 1px 100%),
    #ffffff;
  background-size: 96px 100%;
}

.eiq-race-workspace--map .eiq-map-v1-visual__surface,
.eiq-race-workspace--map .eiq-map-v1-barriers {
  grid-template-rows: repeat(var(--eiq-map-row-count, 18), minmax(20px, 1fr));
}

.eiq-race-workspace--map .eiq-map-v1-runner-line {
  min-height: 21px;
  border-bottom: 1px dashed rgba(37, 99, 235, 0.2);
}

.eiq-race-workspace--map .eiq-map-v1-runner-line__bar {
  display: block;
  left: var(--eiq-map-left);
  right: 8px;
  height: 2px;
  background: rgba(37, 99, 235, 0.68);
}

.eiq-race-workspace--map .eiq-map-v1-runner-line.is-unavailable .eiq-map-v1-runner-line__bar {
  background: rgba(37, 99, 235, 0.28);
}

.eiq-race-workspace--map .eiq-map-v1-runner-line__label {
  min-height: 21px;
  max-width: 260px;
  margin-left: var(--eiq-map-left);
  transform: translateX(-50%);
  padding: 2px 7px 2px 3px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 3px;
  border: 1px solid rgba(37, 99, 235, 0.22);
  background: #ffffff;
  color: var(--eiq-approved-navy);
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}

.eiq-race-workspace--map .eiq-map-v1-runner-line__label strong {
  width: 18px;
  height: 18px;
  border: 1px solid var(--eiq-approved-blue);
  border-radius: 3px;
  background: transparent;
  color: var(--eiq-approved-blue);
  font-size: 10px;
}

.eiq-race-workspace--map .eiq-map-v1-runner-line__label em {
  max-width: 148px;
  font-size: 10px;
  font-weight: 800;
}

.eiq-race-workspace--map .eiq-map-v1-runner-line__label span {
  color: var(--eiq-approved-muted);
  font-size: 9px;
  font-weight: 800;
}

.eiq-race-workspace--map .eiq-map-v1-barriers {
  border-left: 1px solid var(--eiq-approved-line);
}

.eiq-race-workspace--map .eiq-map-v1-barriers span {
  color: var(--eiq-approved-navy);
  font-size: 11px;
  font-weight: 800;
  border-bottom: 1px dashed rgba(37, 99, 235, 0.16);
}

.eiq-race-workspace--map .eiq-map-v1-side {
  gap: 10px;
}

.eiq-race-workspace--map .eiq-map-v1-facts {
  padding: 10px;
  gap: 8px;
}

.eiq-race-workspace--map .eiq-map-v1-facts div,
.eiq-race-workspace--map .eiq-map-v1-key-positions div {
  border-bottom: 1px solid var(--eiq-approved-line);
}

.eiq-race-workspace--map .eiq-map-v1-notes {
  margin: 0;
  padding: 10px 14px 12px 26px;
  color: var(--eiq-approved-text);
  font-size: 11px;
  line-height: 1.45;
}

.eiq-race-workspace--map .eiq-map-v1-copy {
  margin: 0;
  padding: 10px 12px 12px;
  color: var(--eiq-approved-text);
  font-size: 11px;
}

.eiq-race-workspace--map .eiq-map-v1-key-positions {
  display: grid;
  gap: 0;
  padding: 8px 10px 10px;
}

.eiq-race-workspace--map .eiq-map-v1-key-positions div {
  padding: 7px 0;
}

.eiq-race-workspace--map .eiq-map-v1-key-positions span {
  display: block;
  color: var(--eiq-approved-muted);
  font-size: 9px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.eiq-race-workspace--map .eiq-map-v1-key-positions strong {
  display: block;
  margin-top: 3px;
  color: var(--eiq-approved-navy);
  font-size: 12px;
  line-height: 1.25;
}

.eiq-race-workspace--map .eiq-map-v1-table th,
.eiq-race-workspace--map .eiq-map-v1-table td {
  height: 25px;
  padding: 0 7px;
  font-size: 10px;
}

.eiq-race-workspace--map .eiq-map-v1-table th {
  height: 29px;
}
'''

if "/* EDGEIQ APPROVED UI PHASE 08 MAP */" not in css:
    CSS.write_text(css.rstrip() + addition + "\n", encoding="utf-8", newline="\n")

print(f"Checkpoint: {CHECKPOINT}")
print(f"Changed: {MAP}")
print(f"Changed: {CSS}")
print("EDGEIQ_APPROVED_UI_PHASE08_MAP_PASS")
