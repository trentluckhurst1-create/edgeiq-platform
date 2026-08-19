from pathlib import Path

path = Path("src/edgeiq-os/styles/edgeiqOsV2.css")
backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_FIXED_FORM_TABLE_POLISH_20260709.css")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

css = r'''

/* EDGEIQ FORM DESK — FIXED TABLE POLISH V5 */
.eiq-professional-form-table {
  overflow-x: auto !important;
  overflow-y: visible !important;
}

.eiq-professional-form-table table {
  min-width: 1500px !important;
  table-layout: fixed !important;
}

.eiq-professional-form-table th,
.eiq-professional-form-table td {
  padding-left: 10px !important;
  padding-right: 10px !important;
}

.eiq-professional-form-table th:nth-child(1), .eiq-professional-form-table td:nth-child(1) { width: 34px !important; }
.eiq-professional-form-table th:nth-child(2), .eiq-professional-form-table td:nth-child(2) { width: 92px !important; }
.eiq-professional-form-table th:nth-child(3), .eiq-professional-form-table td:nth-child(3) { width: 70px !important; }
.eiq-professional-form-table th:nth-child(4), .eiq-professional-form-table td:nth-child(4) { width: 70px !important; }
.eiq-professional-form-table th:nth-child(5), .eiq-professional-form-table td:nth-child(5) { width: 72px !important; }
.eiq-professional-form-table th:nth-child(6), .eiq-professional-form-table td:nth-child(6) { width: 76px !important; }
.eiq-professional-form-table th:nth-child(7), .eiq-professional-form-table td:nth-child(7) { width: 48px !important; }
.eiq-professional-form-table th:nth-child(8), .eiq-professional-form-table td:nth-child(8) { width: 62px !important; }
.eiq-professional-form-table th:nth-child(9), .eiq-professional-form-table td:nth-child(9) { width: 92px !important; }
.eiq-professional-form-table th:nth-child(10), .eiq-professional-form-table td:nth-child(10) { width: 64px !important; }
.eiq-professional-form-table th:nth-child(11), .eiq-professional-form-table td:nth-child(11) { width: 54px !important; }
.eiq-professional-form-table th:nth-child(12), .eiq-professional-form-table td:nth-child(12) { width: 70px !important; }
.eiq-professional-form-table th:nth-child(13), .eiq-professional-form-table td:nth-child(13) { width: 76px !important; }
.eiq-professional-form-table th:nth-child(14), .eiq-professional-form-table td:nth-child(14) { width: 86px !important; }
.eiq-professional-form-table th:nth-child(15), .eiq-professional-form-table td:nth-child(15) { width: 74px !important; }
.eiq-professional-form-table th:nth-child(16), .eiq-professional-form-table td:nth-child(16) { width: 70px !important; }
.eiq-professional-form-table th:nth-child(17), .eiq-professional-form-table td:nth-child(17) { width: 96px !important; }
.eiq-professional-form-table th:nth-child(18), .eiq-professional-form-table td:nth-child(18) { width: 84px !important; }
.eiq-professional-form-table th:nth-child(19), .eiq-professional-form-table td:nth-child(19) { width: 270px !important; }

.eiq-professional-form-table th:nth-child(2),
.eiq-professional-form-table td:nth-child(2),
.eiq-professional-form-table th:nth-child(3),
.eiq-professional-form-table td:nth-child(3) {
  position: static !important;
}

.eiq-professional-form-table td:nth-child(19) {
  max-width: 270px !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.eiq-form-report-row td {
  white-space: normal !important;
}

.eiq-run-report {
  min-width: 0 !important;
}

.eiq-run-report__grid {
  grid-template-columns: .85fr 1.45fr 1.2fr !important;
}

.eiq-run-report article > strong,
.eiq-run-report p,
.eiq-run-report dd {
  white-space: normal !important;
}

.eiq-run-report footer {
  justify-content: flex-start !important;
}
'''

text = path.read_text(encoding="utf-8")
if "EDGEIQ FORM DESK — FIXED TABLE POLISH V5" not in text:
    text += css

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] Fixed professional form table polish applied")
print(f"[EDGEIQ] checkpoint: {backup}")
