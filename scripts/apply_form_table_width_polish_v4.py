from pathlib import Path

path = Path("src/edgeiq-os/styles/edgeiqOsV2.css")
backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_FORM_TABLE_WIDTH_POLISH_20260709.css")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

css = r'''

/* EDGEIQ FORM DESK — TABLE WIDTH + REPORT READABILITY V4 */
.eiq-form-workbench-v2 {
  max-width: 1680px !important;
}

.eiq-professional-form-table {
  overflow-x: auto !important;
  overflow-y: visible !important;
}

.eiq-professional-form-table table {
  min-width: 1880px !important;
}

.eiq-professional-form-table th,
.eiq-professional-form-table td {
  padding-left: 14px !important;
  padding-right: 14px !important;
}

.eiq-professional-form-table th:nth-child(19),
.eiq-professional-form-table td:nth-child(19) {
  min-width: 420px !important;
}

.eiq-professional-form-table td:nth-child(19) {
  max-width: 420px !important;
}

.eiq-form-report-row td {
  white-space: normal !important;
}

.eiq-run-report {
  min-width: 1820px !important;
}

.eiq-run-report__grid {
  grid-template-columns: 340px 600px minmax(520px, 1fr) !important;
}

.eiq-run-report article {
  min-height: 190px !important;
}

.eiq-run-report article > strong,
.eiq-run-report p,
.eiq-run-report dd,
.eiq-run-report__reasons em {
  white-space: normal !important;
}

.eiq-run-report__reasons {
  max-width: 100% !important;
}

.eiq-run-report__reasons em {
  line-height: 1.25 !important;
}

.eiq-run-report footer {
  position: sticky !important;
  left: 0 !important;
  background: rgba(3,8,10,.72) !important;
}

.eiq-form-toolbar,
.eiq-form-action-row,
.eiq-assignment-command,
.eiq-runner-strip {
  max-width: 100% !important;
}

.eiq-form-toolbar nav {
  justify-content: flex-end !important;
}
'''

text = path.read_text(encoding="utf-8")
if "EDGEIQ FORM DESK — TABLE WIDTH + REPORT READABILITY V4" not in text:
    text += css

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] Table width and report readability polish applied")
print(f"[EDGEIQ] checkpoint: {backup}")
