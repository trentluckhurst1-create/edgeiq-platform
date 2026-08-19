from pathlib import Path

path = Path("src/edgeiq-os/styles/edgeiqOsV2.css")
backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_STEEL_BLUE_ACCENT_TEST_20260709.css")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

css = r'''

/* EDGEIQ FORM DESK — STEEL BLUE ACCENT TEST V8 */
.eiq-investigation-workbench {
  --eiq-soft-teal: #7fa7d8 !important;
  --eiq-soft-line: rgba(127,167,216,.18) !important;
  --eiq-soft-fill: rgba(127,167,216,.055) !important;
}

.eiq-investigation-workbench span,
.eiq-investigation-workbench dt,
.eiq-form-workbench-v2 span,
.eiq-form-workbench-v2 dt,
.eiq-professional-form-table td b,
.eiq-investigation-report header b,
.eiq-start-investigation button,
.eiq-investigation-report footer button {
  color: #7fa7d8 !important;
}

.eiq-form-toolbar button.is-active,
.eiq-form-toolbar button:hover,
.eiq-start-investigation button,
.eiq-investigation-report footer button {
  border-color: rgba(127,167,216,.34) !important;
  background: rgba(127,167,216,.055) !important;
}

.eiq-professional-form-table tbody tr:hover td,
.eiq-professional-form-table tbody tr.is-open td {
  background: rgba(127,167,216,.045) !important;
}

.eiq-investigation-report {
  border-left-color: rgba(127,167,216,.72) !important;
}

.eiq-investigation-brief,
.eiq-analyst-ribbon,
.eiq-start-investigation,
.eiq-professional-form-table,
.eiq-investigation-report,
.eiq-investigation-grid article,
.eiq-investigation-record,
.eiq-investigation-metrics article {
  border-color: rgba(127,167,216,.16) !important;
}
'''

text = path.read_text(encoding="utf-8")
if "EDGEIQ FORM DESK — STEEL BLUE ACCENT TEST V8" not in text:
    text += css

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] Steel blue accent test applied")
print(f"[EDGEIQ] checkpoint: {backup}")
