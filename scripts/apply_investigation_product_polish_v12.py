from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_PRODUCT_POLISH_V12_20260709.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_PRODUCT_POLISH_V12_20260709.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

text = text.replace("Why this historical run was opened", "Evidence Transfer")
text = text.replace("EDGEIQ Evidence Story", "Analyst Verdict")
text = text.replace("This run explains context, not today’s full assignment.", "Background evidence. Useful context, not a standalone benchmark.")
text = text.replace("This run supports the case but needs confirmation.", "Supporting evidence. Useful benchmark once today’s differences are checked.")
text = text.replace("This run is suitable as a primary benchmark.", "Primary evidence. Suitable benchmark for today’s assessment.")
text = text.replace("What changed today", "Today vs Historical")
text = text.replace("Evidence Score Breakdown", "Evidence Weighting")
text = text.replace("Can this run transfer to today?", "Historical Transfer Test")

tsx.write_text(text, encoding="utf-8")

add = r'''

/* EDGEIQ PRODUCT POLISH — INVESTIGATION WORKBENCH V12 */
.eiq-investigation-workbench-v2 {
  --eiq-blue: #557aa8 !important;
  --eiq-green: #2f6b51 !important;
  --eiq-amber: #8a6841 !important;
  --eiq-red: #7b3434 !important;
  --eiq-text: #f5f7f8 !important;
  --eiq-muted: rgba(245,247,248,.58) !important;
  --eiq-faint: rgba(245,247,248,.36) !important;
}

.eiq-investigation-report-v2 {
  background: linear-gradient(180deg, rgba(8,13,18,.88), rgba(3,7,10,.88)) !important;
}

.eiq-investigation-report-v2 header {
  min-height: 104px !important;
}

.eiq-investigation-report-v2 header strong {
  font-size: 22px !important;
  letter-spacing: -.025em !important;
}

.eiq-investigation-core {
  grid-template-columns: 1.15fr 1.15fr .8fr !important;
}

.eiq-investigation-core article {
  min-height: 128px !important;
  border-color: rgba(245,247,248,.075) !important;
  background: rgba(255,255,255,.012) !important;
}

.eiq-rating-strip {
  margin-top: 10px !important;
}

.eiq-rating-tile {
  min-height: 74px !important;
  border-color: rgba(245,247,248,.07) !important;
}

.eiq-rating-tile strong {
  font-size: 20px !important;
}

.eiq-similarity-engine {
  border-left: 3px solid rgba(85,122,168,.7) !important;
  background: rgba(255,255,255,.012) !important;
}

.eiq-similarity-engine header {
  grid-template-columns: minmax(0, 1fr) 260px !important;
}

.eiq-similarity-engine header strong {
  font-size: 22px !important;
}

.eiq-similarity-grid {
  grid-template-columns: repeat(4, minmax(0,1fr)) !important;
  gap: 8px !important;
}

.eiq-similarity-grid article {
  min-height: 82px !important;
  padding: 10px 12px !important;
  border-color: rgba(245,247,248,.07) !important;
  background: rgba(255,255,255,.012) !important;
}

.eiq-similarity-grid article strong {
  font-size: 17px !important;
}

.eiq-similarity-grid i {
  height: 8px !important;
}

.eiq-similarity-grid i b {
  background: linear-gradient(90deg, #557aa8, #6f93bf) !important;
}

.eiq-what-changed,
.eiq-factor-score-panel {
  border-color: rgba(245,247,248,.07) !important;
  background: rgba(255,255,255,.01) !important;
}

.eiq-what-changed table,
.eiq-factor-score-panel table {
  margin-top: 8px !important;
}

.eiq-what-changed th,
.eiq-what-changed td,
.eiq-factor-score-panel th,
.eiq-factor-score-panel td {
  height: 28px !important;
}

.eiq-what-changed td:last-child {
  font-weight: 900 !important;
}

.eiq-what-changed td:last-child:has(+ *) {
  color: inherit;
}

.eiq-factor-score-panel b {
  font-size: 11px !important;
}

.eiq-factor-score-panel b.is-plus {
  background: rgba(47,107,81,.55) !important;
}

.eiq-factor-score-panel b.is-watch {
  background: rgba(138,104,65,.50) !important;
}

.eiq-evidence-story {
  background: rgba(85,122,168,.055) !important;
  border-color: rgba(85,122,168,.18) !important;
  border-left-color: rgba(85,122,168,.78) !important;
}

.eiq-evidence-story strong {
  font-size: 21px !important;
}

.eiq-verdict-panel {
  background: rgba(255,255,255,.014) !important;
  border-color: rgba(245,247,248,.08) !important;
  border-left-color: rgba(85,122,168,.78) !important;
}

.eiq-verdict-panel strong {
  font-size: 20px !important;
}

.eiq-verdict-panel > div {
  padding-right: 20px !important;
}

.eiq-official-record {
  background: rgba(0,0,0,.12) !important;
  border-color: rgba(245,247,248,.07) !important;
}

.eiq-investigation-table-v2 th,
.eiq-investigation-table-v2 td {
  font-size: 11px !important;
}

.eiq-investigation-table-v2 td b {
  color: #7fa7d8 !important;
}

.eiq-evidence-badge {
  max-width: none !important;
  min-width: 86px !important;
  justify-content: center !important;
}

.eiq-evidence-badge.is-background {
  background: rgba(85,122,168,.14) !important;
  color: rgba(245,247,248,.78) !important;
}

.eiq-match-bar {
  grid-template-columns: minmax(120px, 1fr) 42px !important;
}

.eiq-match-bar i {
  background: rgba(245,247,248,.10) !important;
  position: relative !important;
}

.eiq-match-bar i::after {
  content: "";
  display: block;
  height: 100%;
  width: inherit;
  background: #6f93bf;
}

@media (max-width: 1350px) {
  .eiq-investigation-core,
  .eiq-similarity-grid,
  .eiq-similarity-engine header {
    grid-template-columns: 1fr !important;
  }
}
'''

if "EDGEIQ PRODUCT POLISH — INVESTIGATION WORKBENCH V12" not in css.read_text(encoding="utf-8"):
    css.write_text(css.read_text(encoding="utf-8") + add, encoding="utf-8")

print("[EDGEIQ] Product Polish V12 applied")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
