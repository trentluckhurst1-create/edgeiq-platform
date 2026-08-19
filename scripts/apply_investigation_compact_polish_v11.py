from pathlib import Path

css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")
backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_INVESTIGATION_COMPACT_POLISH_V11_20260709.css")
backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

add = r'''

/* EDGEIQ INVESTIGATION COMPACT POLISH — V11 */
.eiq-investigation-report-v2 {
  padding: 14px !important;
}

.eiq-investigation-core article {
  min-height: 155px !important;
}

.eiq-investigation-core ul {
  gap: 6px !important;
}

.eiq-rating-strip {
  grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
}

.eiq-rating-tile {
  min-height: 68px !important;
  padding: 10px 12px !important;
}

.eiq-rating-tile strong {
  font-size: 17px !important;
}

.eiq-what-changed,
.eiq-factor-score-panel,
.eiq-verdict-panel,
.eiq-official-record {
  padding: 12px !important;
}

.eiq-what-changed th,
.eiq-what-changed td,
.eiq-factor-score-panel th,
.eiq-factor-score-panel td {
  height: 30px !important;
}

.eiq-factor-score-panel b {
  min-width: 30px !important;
  max-width: 30px !important;
  width: 30px !important;
  height: 20px !important;
  padding: 0 !important;
}

.eiq-factor-score-panel td:nth-child(3) {
  width: 92px !important;
}

.eiq-factor-score-panel b.is-plus {
  background: rgba(36,92,67,.42) !important;
  color: #d8fff0 !important;
}

.eiq-factor-score-panel b.is-watch {
  background: rgba(107,75,48,.40) !important;
  color: #ffe0bc !important;
}

.eiq-verdict-panel {
  grid-template-columns: minmax(0, 1.2fr) 190px 1fr 1fr !important;
  gap: 12px !important;
}

.eiq-verdict-panel strong {
  font-size: 17px !important;
}

.eiq-verdict-panel ul {
  gap: 5px !important;
}

.eiq-investigation-table-v2 td {
  height: 40px !important;
}

.eiq-investigation-table-v2 th {
  height: 38px !important;
}

.eiq-evidence-badge {
  max-width: 96px !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.eiq-official-record dl {
  grid-template-columns: repeat(12, minmax(0,1fr)) !important;
}
'''

if "EDGEIQ INVESTIGATION COMPACT POLISH — V11" not in css.read_text(encoding="utf-8"):
    css.write_text(css.read_text(encoding="utf-8") + add, encoding="utf-8")

print("[EDGEIQ] Investigation Compact Polish V11 applied")
print(f"[EDGEIQ] checkpoint: {backup}")
