from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"
TOKENS = ROOT / "docs/product-specification/FORM_GUIDE_APPROVED_STYLE_TOKENS_V1.css"
REPORT = ROOT / "docs/product-specification/FORM_GUIDE_EXACT_STYLES_APPLY_V1.json"
MARKER_START = "/* EDGEIQ FORM GUIDE APPROVED EXACT PIXEL SPEC V1 START */"
MARKER_END = "/* EDGEIQ FORM GUIDE APPROVED EXACT PIXEL SPEC V1 END */"

EXACT_CSS = r'''
/* EDGEIQ FORM GUIDE APPROVED EXACT PIXEL SPEC V1 START */
:root {
  --fg-approved-blue: #0759d7;
  --fg-approved-blue-dark: #07166c;
  --fg-approved-navy: #091a44;
  --fg-approved-text: #07135f;
  --fg-approved-muted: #52637f;
  --fg-approved-line: #dde5ef;
  --fg-approved-line-strong: #c8d3df;
  --fg-approved-surface: #ffffff;
  --fg-approved-surface-soft: #f7f9fc;
  --fg-approved-blue-soft: #edf4ff;
  --fg-approved-green: #087e2f;
  --fg-approved-green-soft: #eaf7ee;
  --fg-approved-red: #cc3340;
  --fg-approved-red-soft: #fdecec;
  --fg-approved-font: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.eiq-race-workspace--form-guide {
  background: #ffffff !important;
  color: var(--fg-approved-text) !important;
  font-family: var(--fg-approved-font) !important;
  gap: 10px !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header {
  display: grid !important;
  gap: 10px !important;
  padding: 0 0 8px !important;
  border: 0 !important;
  background: #ffffff !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__crumb {
  min-height: 18px !important;
  gap: 8px !important;
  color: var(--fg-approved-blue) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  letter-spacing: .045em !important;
  text-transform: uppercase !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__title {
  min-height: 34px !important;
  align-items: flex-start !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__title h1 {
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
  gap: 22px !important;
  color: var(--fg-approved-blue) !important;
  font-size: 26px !important;
  line-height: 1 !important;
  font-weight: 900 !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__title h1 strong {
  color: var(--fg-approved-navy) !important;
  font-size: 20px !important;
  font-weight: 900 !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__title h1 em {
  min-height: 27px !important;
  display: inline-flex !important;
  align-items: center !important;
  border-radius: 5px !important;
  background: #dbeaff !important;
  color: var(--fg-approved-blue) !important;
  padding: 0 10px !important;
  font-size: 14px !important;
  font-weight: 900 !important;
  font-style: normal !important;
}

.eiq-race-workspace--form-guide .eiq-approved-button {
  min-height: 28px !important;
  min-width: 140px !important;
  border: 1px solid var(--fg-approved-blue) !important;
  border-radius: 5px !important;
  background: #fff !important;
  color: var(--fg-approved-blue) !important;
  font-size: 12px !important;
  font-weight: 900 !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__meta {
  margin: 4px 0 0 !important;
  min-height: 23px !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: #ffffff !important;
  display: flex !important;
  gap: 24px !important;
  overflow: visible !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__meta div {
  min-height: 20px !important;
  border: 0 !important;
  padding: 0 20px 0 0 !important;
  border-right: 1px solid var(--fg-approved-line) !important;
  display: flex !important;
  align-items: center !important;
  gap: 7px !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__meta dt {
  font-size: 0 !important;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__meta dt::before {
  content: "";
  width: 16px;
  height: 16px;
  display: inline-block;
  border: 1.5px solid var(--fg-approved-blue);
  border-radius: 4px;
}

.eiq-race-workspace--form-guide .eiq-approved-racefile-header__meta dd {
  margin: 0 !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 12px !important;
  font-weight: 800 !important;
}

.eiq-race-workspace--form-guide > .eiq-context-tabs {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)) !important;
  min-height: 40px !important;
  border: 1px solid var(--fg-approved-line) !important;
  border-radius: 5px !important;
  background: #ffffff !important;
  overflow: hidden !important;
}

.eiq-race-workspace--form-guide > .eiq-context-tabs button {
  min-height: 40px !important;
  border: 0 !important;
  border-right: 1px solid var(--fg-approved-line) !important;
  background: #ffffff !important;
  color: var(--fg-approved-navy) !important;
  font-size: 11px !important;
  font-weight: 900 !important;
  letter-spacing: 0 !important;
}

.eiq-race-workspace--form-guide > .eiq-context-tabs button.is-active {
  color: var(--fg-approved-blue) !important;
  background: #ffffff !important;
  box-shadow: inset 0 -2px 0 var(--fg-approved-blue) !important;
}

.eiq-race-form-guide--approved-exact {
  display: grid !important;
  gap: 10px !important;
  background: #ffffff !important;
  color: var(--fg-approved-text) !important;
  font-family: var(--fg-approved-font) !important;
}

.eiq-race-form-guide--approved-exact > .eiq-form-race-header,
.eiq-race-form-guide--approved-exact > .eiq-form-race-selector,
.eiq-race-form-guide--approved-exact > .eiq-form-v33-tools,
.eiq-race-form-guide--approved-exact > .eiq-form-v3-footer {
  display: none !important;
}

.eiq-form-approved-tools {
  min-height: 28px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  color: var(--fg-approved-blue-dark);
  font-size: 10px;
  font-weight: 900;
}

.eiq-form-approved-tools label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.eiq-form-approved-tools select,
.eiq-form-approved-tools button {
  height: 27px;
  border: 1px solid #cfe0ff;
  border-radius: 5px;
  background: #ffffff;
  color: var(--fg-approved-blue);
  padding: 0 12px;
  font: inherit;
  font-size: 10px;
  font-weight: 900;
}

.eiq-form-approved-tools select {
  min-width: 74px;
  color: var(--fg-approved-navy);
}

.eiq-race-form-guide--approved-exact .eiq-form-summary-table--all-runner {
  overflow: hidden !important;
  border: 1px solid var(--fg-approved-line) !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  box-shadow: none !important;
  --edgeiq-form-guide-row-height: 32px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-summary-table--all-runner table {
  width: 100% !important;
  min-width: 1300px !important;
  table-layout: fixed !important;
  border-collapse: collapse !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-summary-table th,
.eiq-race-form-guide--approved-exact .eiq-form-summary-table td {
  height: 32px !important;
  padding: 0 7px !important;
  border: 1px solid var(--fg-approved-line) !important;
  background: #ffffff !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 11px !important;
  line-height: 1.05 !important;
  font-weight: 800 !important;
  vertical-align: middle !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-summary-table th {
  height: 28px !important;
  background: #fbfdff !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 8.2px !important;
  font-weight: 900 !important;
  letter-spacing: .025em !important;
  text-transform: uppercase !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-summary-table th button {
  color: inherit !important;
  font-size: inherit !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-silk {
  width: 24px !important;
  height: 24px !important;
  object-fit: contain !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-last5-strip {
  min-width: 72px !important;
  gap: 2px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-last5-strip span {
  min-width: 15px !important;
  height: 16px !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-runner-expand strong {
  color: var(--fg-approved-blue-dark) !important;
  font-size: 11px !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--approved-exact .eiq-cell-epi,
.eiq-race-form-guide--approved-exact .eiq-cell-edgeiq-price,
.eiq-race-form-guide--approved-exact .eiq-cell-market {
  color: var(--fg-approved-blue-dark) !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--approved-exact .eiq-cell-edge[data-edge="positive"],
.eiq-race-form-guide--approved-exact .eiq-cell-fluc[data-edge="positive"] {
  color: var(--fg-approved-green) !important;
}

.eiq-race-form-guide--approved-exact .eiq-cell-edge[data-edge="negative"],
.eiq-race-form-guide--approved-exact .eiq-cell-fluc[data-edge="negative"] {
  color: var(--fg-approved-red) !important;
}

.eiq-race-form-guide--approved-exact .eiq-cell-momentum[data-direction="up"] {
  color: var(--fg-approved-green) !important;
}

.eiq-race-form-guide--approved-exact .eiq-cell-momentum[data-direction="down"] {
  color: var(--fg-approved-red) !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-expanded-row > td {
  padding: 10px 0 0 !important;
  border: 0 !important;
  background: #ffffff !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-runner-sheet {
  display: grid !important;
  gap: 8px !important;
  padding: 10px !important;
  border: 1.5px solid var(--fg-approved-blue) !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-runner-header {
  min-height: 62px !important;
  display: grid !important;
  grid-template-columns: 92px minmax(280px, .95fr) minmax(610px, 1.75fr) !important;
  align-items: center !important;
  gap: 10px !important;
  padding: 0 !important;
  background: #ffffff !important;
  border: 0 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-detail-silk {
  width: 48px !important;
  height: 48px !important;
  justify-self: center !important;
  object-fit: contain !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v3-runner-identity {
  min-width: 0 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v3-runner-identity span {
  display: none !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v3-runner-identity strong {
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
  gap: 13px !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 22px !important;
  line-height: 1 !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v3-runner-identity strong em {
  width: 42px !important;
  height: 42px !important;
  display: inline-grid !important;
  place-items: center !important;
  margin: 0 4px 0 0 !important;
  border-radius: 6px !important;
  background: var(--fg-approved-blue) !important;
  color: #ffffff !important;
  font-style: normal !important;
  font-size: 24px !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v3-runner-identity p {
  margin: 8px 0 0 !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 11px !important;
  font-weight: 800 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-current-strip {
  display: grid !important;
  grid-template-columns: repeat(7, minmax(74px, 1fr)) !important;
  border: 1px solid var(--fg-approved-line) !important;
  border-radius: 5px !important;
  background: #ffffff !important;
  overflow: hidden !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-current-strip div {
  min-height: 61px !important;
  padding: 8px 10px !important;
  border-right: 1px solid var(--fg-approved-line) !important;
  text-align: center !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-current-strip dt {
  color: var(--fg-approved-blue-dark) !important;
  font-size: 8px !important;
  font-weight: 900 !important;
  letter-spacing: 0 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-current-strip dd {
  margin: 6px 0 0 !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 18px !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-approved-dossier-grid {
  display: grid !important;
  grid-template-columns: 205px minmax(0, 1fr) 198px !important;
  gap: 8px !important;
  align-items: stretch !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-today-match,
.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-block,
.eiq-race-form-guide--approved-exact .eiq-form-v4-key-insights,
.eiq-race-form-guide--approved-exact .eiq-form-v4-recent-form {
  border: 1px solid var(--fg-approved-line) !important;
  border-radius: 5px !important;
  background: #ffffff !important;
  padding: 10px !important;
  box-shadow: none !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-current-details {
  display: none !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-block {
  min-height: 232px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-block header {
  height: 20px !important;
  padding: 0 !important;
  margin: 0 0 6px !important;
  border: 0 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-block header span,
.eiq-race-form-guide--approved-exact .eiq-form-v4-today-match h3,
.eiq-race-form-guide--approved-exact .eiq-form-v4-key-insights h3,
.eiq-race-form-guide--approved-exact .eiq-form-v4-recent-form header span {
  color: var(--fg-approved-blue-dark) !important;
  font-size: 10px !important;
  line-height: 1 !important;
  font-weight: 900 !important;
  letter-spacing: .03em !important;
  text-transform: uppercase !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-block header strong,
.eiq-race-form-guide--approved-exact .eiq-form-v4-recent-form header p {
  display: none !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-group {
  border: 0 !important;
  padding: 4px 0 !important;
  gap: 4px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-group h3 {
  display: none !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-tiles {
  display: grid !important;
  grid-template-columns: repeat(8, minmax(62px, 1fr)) !important;
  gap: 4px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-tiles article {
  min-height: 51px !important;
  padding: 5px 5px !important;
  border: 1px solid var(--fg-approved-line) !important;
  border-radius: 5px !important;
  background: #ffffff !important;
  text-align: center !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-tiles article.is-current-match {
  border-color: #7caeff !important;
  background: #eef5ff !important;
  box-shadow: inset 0 0 0 1px #7caeff !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-tiles span {
  color: var(--fg-approved-blue-dark) !important;
  font-size: 8px !important;
  font-weight: 900 !important;
  letter-spacing: 0 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-tiles strong {
  margin-top: 4px !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 12px !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-profile-tiles small {
  margin-top: 2px !important;
  color: var(--fg-approved-muted) !important;
  font-size: 8px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-today-match ul,
.eiq-race-form-guide--approved-exact .eiq-form-v4-key-insights ul {
  margin: 8px 0 0 !important;
  display: grid !important;
  gap: 6px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-today-match li,
.eiq-race-form-guide--approved-exact .eiq-form-v4-key-insights li {
  min-height: 24px !important;
  border: 0 !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 10px !important;
  font-weight: 800 !important;
  line-height: 1.25 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-today-match li span,
.eiq-race-form-guide--approved-exact .eiq-form-v4-today-match li small {
  color: var(--fg-approved-green) !important;
  font-size: 9px !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-key-insights article {
  border: 0 !important;
  padding: 0 !important;
  background: transparent !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-key-insights article strong {
  display: none !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-key-insights li::before {
  content: "✓";
  display: inline-grid;
  place-items: center;
  width: 14px;
  height: 14px;
  margin-right: 6px;
  border: 1px solid var(--fg-approved-green);
  border-radius: 50%;
  color: var(--fg-approved-green);
  font-size: 9px;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-recent-form {
  min-height: 210px !important;
  padding-top: 8px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-v4-recent-form header {
  min-height: 20px !important;
  margin: 0 0 4px !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-run-table--v4 table {
  width: 100% !important;
  min-width: 1180px !important;
  table-layout: fixed !important;
  border-collapse: collapse !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-run-table--v4 th,
.eiq-race-form-guide--approved-exact .eiq-form-run-table--v4 td {
  height: 20px !important;
  padding: 0 5px !important;
  border: 0 !important;
  background: #ffffff !important;
  color: var(--fg-approved-blue-dark) !important;
  font-size: 9.5px !important;
  font-weight: 800 !important;
  text-align: center !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-run-table--v4 th {
  color: var(--fg-approved-blue-dark) !important;
  font-size: 8px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-run-table--v4 td:nth-child(5) {
  border-radius: 4px !important;
  background: #e8f5ec !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-run-table--v4 td.is-negative {
  color: var(--fg-approved-green) !important;
  background: var(--fg-approved-green-soft) !important;
}

.eiq-race-form-guide--approved-exact .eiq-form-run-table--v4 td.is-positive {
  color: var(--fg-approved-red) !important;
  background: var(--fg-approved-red-soft) !important;
}

@media (max-width: 1180px) {
  .eiq-race-form-guide--approved-exact .eiq-form-v4-runner-header,
  .eiq-race-form-guide--approved-exact .eiq-form-approved-dossier-grid {
    grid-template-columns: 1fr !important;
  }

  .eiq-race-form-guide--approved-exact .eiq-form-summary-table--all-runner,
  .eiq-race-form-guide--approved-exact .eiq-form-run-table--v4 {
    overflow-x: auto !important;
  }
}
/* EDGEIQ FORM GUIDE APPROVED EXACT PIXEL SPEC V1 END */
'''

def main():
    text = CSS.read_text(encoding="utf-8")
    if MARKER_START in text and MARKER_END in text:
        before, rest = text.split(MARKER_START, 1)
        _, after = rest.split(MARKER_END, 1)
        text = before.rstrip() + "\n\n" + EXACT_CSS + after
    else:
        text = text.rstrip() + "\n\n" + EXACT_CSS + "\n"
    CSS.write_text(text, encoding="utf-8")
    REPORT.write_text(json.dumps({"status":"FORM_GUIDE_EXACT_STYLES_APPLIED", "css_file":str(CSS), "timestamp":datetime.now().isoformat(), "marker":"EDGEIQ FORM GUIDE APPROVED EXACT PIXEL SPEC V1"}, indent=2), encoding="utf-8")
    print(json.dumps({"status":"FORM_GUIDE_EXACT_STYLES_APPLIED", "css_file":str(CSS)}, indent=2))

if __name__ == "__main__":
    main()
