from pathlib import Path

path = Path("src/edgeiq-os/styles/edgeiqOsV2.css")
backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_SOFT_TEAL_AND_RUN_REPORT_POLISH_20260709.css")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

css = r'''

/* EDGEIQ FORM DESK — SOFT TEAL + EXPANDABLE REPORT POLISH V3 */
.eiq-form-workbench-v2 {
  --eiq-soft-teal: #73c8b8;
  --eiq-soft-teal-muted: rgba(115,200,184,.74);
  --eiq-soft-teal-dim: rgba(115,200,184,.28);
  --eiq-soft-teal-line: rgba(115,200,184,.16);
}

.eiq-form-workbench-v2 span,
.eiq-form-workbench-v2 dt,
.eiq-assignment-command span,
.eiq-runner-strip span,
.eiq-runner-strip dt,
.eiq-form-action-row span,
.eiq-form-toolbar span,
.eiq-run-report span,
.eiq-professional-form-table td b,
.eiq-run-report__top b,
.eiq-form-action-row button,
.eiq-run-report footer button {
  color: var(--eiq-soft-teal) !important;
}

.eiq-form-action-row button,
.eiq-form-toolbar button.is-active,
.eiq-form-toolbar button:hover {
  border-color: var(--eiq-soft-teal-dim) !important;
  background: rgba(115,200,184,.065) !important;
}

.eiq-assignment-command,
.eiq-runner-strip,
.eiq-form-action-row,
.eiq-form-toolbar,
.eiq-professional-form-table,
.eiq-run-report,
.eiq-run-report article {
  border-color: var(--eiq-soft-teal-line) !important;
}

.eiq-professional-form-table tbody tr:hover td,
.eiq-professional-form-table tbody tr.is-open td {
  background: rgba(115,200,184,.045) !important;
}

.eiq-run-report {
  border-left-color: var(--eiq-soft-teal-muted) !important;
  padding: 18px 18px 16px !important;
}

.eiq-run-report__grid {
  grid-template-columns: .8fr 1.35fr 1.05fr !important;
}

.eiq-run-report article {
  min-height: 178px !important;
}

.eiq-run-report footer {
  justify-content: flex-start !important;
  flex-wrap: wrap !important;
  padding-top: 14px !important;
  border-top: 1px solid rgba(115,200,184,.10) !important;
}

.eiq-run-report footer button {
  height: 34px !important;
  padding: 0 14px !important;
  border: 1px solid rgba(115,200,184,.20) !important;
  border-radius: 999px !important;
  background: rgba(115,200,184,.045) !important;
}

.eiq-run-report__reasons em {
  border-color: rgba(115,200,184,.16) !important;
  background: rgba(255,255,255,.025) !important;
}

.eiq-professional-form-table td:nth-child(19) {
  max-width: 520px !important;
}

.eiq-professional-form-table::-webkit-scrollbar-thumb {
  background: rgba(115,200,184,.24) !important;
}

.eiq-professional-form-table::-webkit-scrollbar-thumb:hover {
  background: rgba(115,200,184,.36) !important;
}
'''

text = path.read_text(encoding="utf-8")
if "EDGEIQ FORM DESK — SOFT TEAL + EXPANDABLE REPORT POLISH V3" not in text:
    text += css

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] Soft teal + expandable report polish applied")
print(f"[EDGEIQ] checkpoint: {backup}")
