from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_INVESTIGATION_QUEUE_V7_20260709.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_INVESTIGATION_QUEUE_V7_20260709.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

text = text.replace('return "PRIMARY";', 'return "PRIMARY";')
text = text.replace('return "HIGH";', 'return "SUPPORTING";')
text = text.replace('return "MEDIUM";', 'return "REFERENCE";')
text = text.replace('return "LOW";', 'return "BACKGROUND";')

text = text.replace("Evidence Confidence", "Assignment Confidence")
text = text.replace("Evidence is earned from similarity", "Confidence is earned from similarity")

text = text.replace(
'''          <section className="eiq-start-investigation">
            <div>
              <span>Analyst Summary</span>
              <strong>{bestRun ? `${importance(bestRun)} evidence · ${score(bestRun)}% assignment match` : "Evidence still building"}</strong>
              <p>{bestRun ? "Start with the highlighted historical run. Open it, inspect the counter evidence, then decide whether to compare or trace the evidence." : "No historical runs available."}</p>
            </div>
            <button type="button" onClick={() => document.querySelector(".eiq-investigation-table")?.scrollIntoView({ behavior: "smooth", block: "start" })}>
              Start Investigation →
            </button>
          </section>''',
'''          <section className="eiq-start-investigation eiq-investigation-queue-row">
            <div>
              <span>Analyst Summary</span>
              <strong>{bestRun ? `${importance(bestRun)} evidence · ${score(bestRun)}% assignment match` : "Evidence still building"}</strong>
              <p>{bestRun ? "Start with the highlighted historical run. Open it, inspect the counter evidence, then decide whether to compare or trace the evidence." : "No historical runs available."}</p>
            </div>

            <aside className="eiq-investigation-queue">
              <span>Investigation Queue</span>
              <ol>
                <li className="is-done">Primary historical run</li>
                <li>Compare closest assignment</li>
                <li>Open historical race</li>
                <li>Trace evidence</li>
              </ol>
            </aside>

            <button type="button" onClick={() => document.querySelector(".eiq-investigation-table")?.scrollIntoView({ behavior: "smooth", block: "start" })}>
              Start Investigation →
            </button>
          </section>'''
)

tsx.write_text(text, encoding="utf-8")

style = r'''

/* EDGEIQ FORM DESK — INVESTIGATION QUEUE + DARK STEEL BLUE V7 */
.eiq-investigation-workbench,
.eiq-form-workbench-v2 {
  --eiq-soft-teal: #5f86b8 !important;
  --eiq-soft-line: rgba(95,134,184,.18) !important;
  --eiq-soft-fill: rgba(95,134,184,.055) !important;
}

.eiq-investigation-workbench span,
.eiq-investigation-workbench dt,
.eiq-form-workbench-v2 span,
.eiq-form-workbench-v2 dt,
.eiq-professional-form-table td b,
.eiq-investigation-report header b,
.eiq-start-investigation button,
.eiq-investigation-report footer button {
  color: #5f86b8 !important;
}

.eiq-form-toolbar button.is-active,
.eiq-form-toolbar button:hover,
.eiq-start-investigation button,
.eiq-investigation-report footer button {
  border-color: rgba(95,134,184,.34) !important;
  background: rgba(95,134,184,.055) !important;
}

.eiq-professional-form-table tbody tr:hover td,
.eiq-professional-form-table tbody tr.is-open td {
  background: rgba(95,134,184,.045) !important;
}

.eiq-investigation-report {
  border-left-color: rgba(95,134,184,.72) !important;
}

.eiq-investigation-brief,
.eiq-analyst-ribbon,
.eiq-start-investigation,
.eiq-professional-form-table,
.eiq-investigation-report,
.eiq-investigation-grid article,
.eiq-investigation-record,
.eiq-investigation-metrics article {
  border-color: rgba(95,134,184,.16) !important;
}

.eiq-investigation-queue-row {
  grid-template-columns: minmax(0, 1fr) 410px auto !important;
}

.eiq-investigation-queue {
  padding: 0 18px;
  border-left: 1px solid rgba(95,134,184,.14);
  border-right: 1px solid rgba(95,134,184,.14);
}

.eiq-investigation-queue ol {
  display: grid;
  grid-template-columns: repeat(2, minmax(0,1fr));
  gap: 7px 14px;
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}

.eiq-investigation-queue li {
  position: relative;
  padding-left: 16px;
  color: rgba(244,248,248,.68);
  font-size: 11px;
  font-weight: 700;
}

.eiq-investigation-queue li::before {
  content: "○";
  position: absolute;
  left: 0;
  color: rgba(244,248,248,.36);
}

.eiq-investigation-queue li.is-done::before {
  content: "✓";
  color: #5f86b8;
}

.eiq-investigation-queue li.is-done {
  color: #f4f8f8;
}

.eiq-investigation-table td:nth-child(17) b {
  letter-spacing: .05em;
}

.eiq-investigation-table td:nth-child(17) em {
  color: rgba(244,248,248,.52) !important;
}

@media (max-width: 1350px) {
  .eiq-investigation-queue-row {
    grid-template-columns: 1fr !important;
  }

  .eiq-investigation-queue {
    padding: 12px 0;
    border-left: 0;
    border-right: 0;
    border-top: 1px solid rgba(95,134,184,.14);
    border-bottom: 1px solid rgba(95,134,184,.14);
  }
}
'''

existing = css.read_text(encoding="utf-8")
if "EDGEIQ FORM DESK — INVESTIGATION QUEUE + DARK STEEL BLUE V7" not in existing:
    existing += style
css.write_text(existing, encoding="utf-8")

print("[EDGEIQ] Investigation Queue V7 applied")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
