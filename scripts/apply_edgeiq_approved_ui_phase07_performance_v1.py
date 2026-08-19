from pathlib import Path
import shutil
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
PERF = ROOT / "src" / "edgeiq-os" / "race" / "components" / "PerformanceWorkspace.tsx"
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
MARKER = "/* EDGEIQ APPROVED UI PHASE 07 PERFORMANCE */"


def checkpoint() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = CHECKPOINT_ROOT / f"CHECKPOINT_APPROVED_UI_PHASE07_PERFORMANCE_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in (CSS, PERF):
        shutil.copy2(path, out / path.name)
    return out


def patch_performance() -> None:
    raw = PERF.read_text(encoding="utf-8")
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    old = '''    <section className="eiq-epi-v1 eiq-performance-v2">
      <div className="eiq-epi-v1-hero">
        <div>
          <p>PERFORMANCE</p>
          <h3>{raceLabel || "Historical Performance"}</h3>
          <span>Historical performance heat map with available run context.</span>
        </div>
        <dl>
          <div><dt>Status</dt><dd className={statusClass(viewModel.sourceSummary)}>{viewModel.sourceSummary}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Historical Runs</dt><dd>{viewModel.historicalRuns}</dd></div>
        </dl>
      </div>

      <section className="eiq-epi-v1-summary">
        <div>
          <span>Race Benchmark</span>
          <strong>{raceLabel || "Selected Race"}</strong>
        </div>
        <dl>
          {viewModel.raceBenchmark.map((item) => (
            <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>
          ))}
        </dl>
      </section>
'''
    new = '''    <section className="eiq-epi-v1 eiq-performance-v2">
      <section className="eiq-performance-approved-modules" aria-label="Performance modules">
        {[
          ["FIELD EPI MATRIX", "Quick field scan"],
          ["PERFORMANCE DNA", "Single horse analysis"],
          ["PEAK PERFORMANCES", "Top runs in career"],
          ["TRENDS & PROFILES", "Performance analytics"],
          ["RECORD BOOK", "Career bests"],
          ["SECTIONALS", "Speed and sectional data"],
        ].map(([label, description], index) => (
          <button key={label} type="button" className={index === 0 ? "is-active" : ""}>
            <strong>{label}</strong>
            <span>{description}</span>
          </button>
        ))}
      </section>

      <section className="eiq-performance-approved-toolbar" aria-label="Performance controls">
        <div>
          <span>VIEW</span>
          <button type="button" className="is-active">EPI</button>
          <button type="button">ERI</button>
          <button type="button">EARLY SPEED</button>
          <button type="button">LATE SPEED</button>
          <button type="button">SUITABILITY</button>
          <button type="button">FORM MOMENTUM</button>
        </div>
        <dl>
          <div><dt>Status</dt><dd className={statusClass(viewModel.sourceSummary)}>{viewModel.sourceSummary}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Historical Runs</dt><dd>{viewModel.historicalRuns}</dd></div>
        </dl>
      </section>
'''
    start = text.find('    <section className="eiq-epi-v1 eiq-performance-v2">')
    if start < 0:
        raise SystemExit("PerformanceWorkspace root section not found; source changed unexpectedly.")
    end = text.find('      <div className="eiq-epi-v1-grid">', start)
    if end < 0:
        raise SystemExit("PerformanceWorkspace matrix grid anchor not found; source changed unexpectedly.")
    updated = text[:start] + new + text[end:]
    PERF.write_text(updated, encoding="utf-8", newline="\n")


def patch_css() -> None:
    text = CSS.read_text(encoding="utf-8")
    block = f'''

{MARKER}
.eiq-performance-v2 {{
  display: grid;
  gap: 8px;
}}

.eiq-performance-approved-modules {{
  min-height: 42px;
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  border: 1px solid var(--eiq-approved-line);
  border-radius: 5px;
  overflow: hidden;
  background: #ffffff;
}}

.eiq-performance-approved-modules button {{
  min-width: 0;
  border: 0;
  border-right: 1px solid var(--eiq-approved-line);
  background: #ffffff;
  color: var(--eiq-approved-navy);
  padding: 7px 8px;
  font: inherit;
  text-align: left;
  cursor: pointer;
}}

.eiq-performance-approved-modules button:last-child {{
  border-right: 0;
}}

.eiq-performance-approved-modules button.is-active {{
  background: var(--eiq-approved-blue);
  color: #ffffff;
}}

.eiq-performance-approved-modules strong,
.eiq-performance-approved-modules span {{
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}

.eiq-performance-approved-modules strong {{
  font-size: 10px;
  line-height: 1.05;
  font-weight: 900;
}}

.eiq-performance-approved-modules span {{
  margin-top: 3px;
  font-size: 9px;
  color: inherit;
  opacity: 0.74;
}}

.eiq-performance-approved-toolbar {{
  min-height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 0 2px;
}}

.eiq-performance-approved-toolbar > div {{
  display: flex;
  align-items: center;
  gap: 6px;
}}

.eiq-performance-approved-toolbar span,
.eiq-performance-approved-toolbar dt {{
  color: var(--eiq-approved-muted);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}}

.eiq-performance-approved-toolbar button {{
  height: 26px;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 4px;
  background: #ffffff;
  color: var(--eiq-approved-navy);
  padding: 0 10px;
  font: inherit;
  font-size: 10px;
  font-weight: 900;
}}

.eiq-performance-approved-toolbar button.is-active {{
  background: var(--eiq-approved-blue);
  border-color: var(--eiq-approved-blue);
  color: #ffffff;
}}

.eiq-performance-approved-toolbar dl {{
  margin: 0;
  display: flex;
  align-items: center;
  gap: 16px;
}}

.eiq-performance-approved-toolbar dd {{
  margin: 2px 0 0;
  color: var(--eiq-approved-navy);
  font-size: 12px;
  font-weight: 900;
}}

.eiq-performance-v2 .eiq-epi-v1-grid {{
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 10px;
}}

.eiq-performance-v2 .eiq-epi-v1-panel {{
  border-radius: 5px;
  background: #ffffff;
  border-color: var(--eiq-approved-line);
  box-shadow: none;
}}

.eiq-performance-v2 .eiq-epi-v1-panel__title {{
  min-height: 34px;
  padding: 0 10px;
}}

.eiq-performance-v2 .eiq-epi-v1-panel__title span {{
  font-size: 11px;
  letter-spacing: 0.08em;
}}

.eiq-performance-v2 .eiq-epi-v1-table-scroll {{
  overflow: auto;
}}

.eiq-performance-v2 .eiq-epi-v1-table {{
  width: 100%;
  min-width: 0;
  table-layout: fixed;
}}

.eiq-performance-v2 .eiq-epi-v1-table th,
.eiq-performance-v2 .eiq-epi-v1-table td {{
  height: 31px;
  padding: 0 6px;
  font-size: 11px;
}}

.eiq-performance-v2 .eiq-epi-v1-table th {{
  height: 32px;
  font-size: 9px;
}}

.eiq-performance-v2 .eiq-performance-v2-silk {{
  width: 24px;
  height: 24px;
}}

.eiq-performance-v2 .eiq-epi-v1-tile {{
  width: 54px;
  height: 24px;
  border-radius: 4px;
  font-size: 10px;
}}

.eiq-performance-v2 .eiq-epi-v1-legend {{
  min-height: 34px;
  padding: 0 12px;
  font-size: 11px;
}}

.eiq-performance-v2 .eiq-epi-v1-side .eiq-epi-v1-panel {{
  min-height: 146px;
}}

.eiq-performance-v2 .eiq-epi-v1-copy {{
  font-size: 12px;
  line-height: 1.45;
}}
'''
    if MARKER in text:
        before = text[: text.index(MARKER)].rstrip()
        CSS.write_text(before + block, encoding="utf-8", newline="\n")
    else:
        CSS.write_text(text.rstrip() + block, encoding="utf-8", newline="\n")


def main() -> None:
    cp = checkpoint()
    patch_performance()
    patch_css()
    print(f"checkpoint={cp}")
    print("files_changed:")
    print(f"- {PERF}")
    print(f"- {CSS}")
    print("EDGEIQ_APPROVED_UI_PHASE07_PERFORMANCE_PASS")


if __name__ == "__main__":
    main()
