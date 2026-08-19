from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / 'src' / 'edgeiq-os' / 'styles' / 'edgeiqOsV2.css'
REPORT = ROOT / 'docs' / 'product-specification' / 'FORM_GUIDE_FINAL_RUNNER_HERO_APPLY_V2.json'
MARKER_START = '/* EDGEIQ FORM GUIDE FINAL LOCKED V2 START */'
MARKER_END = '/* EDGEIQ FORM GUIDE FINAL LOCKED V2 END */'
BLOCK = r'''
/* EDGEIQ FORM GUIDE FINAL LOCKED V2 START */
.eiq-race-form-guide--final-locked {
  --edgeiq-form-guide-columns: 38px 46px 86px 170px 138px 132px 48px 42px 48px 58px 78px 76px 90px 104px 72px 88px;
  --edgeiq-form-guide-min-width: 1308px;
  --edgeiq-form-guide-row-height: 42px;
  background: linear-gradient(180deg, #f6f1e7 0%, #ece4d7 100%);
  color: #172033;
  border: 1px solid rgba(23, 32, 51, 0.14);
  box-shadow: 0 18px 60px rgba(4, 8, 16, 0.24);
}

.eiq-race-form-guide--final-locked .eiq-form-race-header--v3 {
  background: linear-gradient(135deg, #1f3f68 0%, #254c78 100%);
  color: #fff;
  border: 0;
  border-radius: 0;
  padding: 12px 16px;
  min-height: 78px;
}

.eiq-race-form-guide--final-locked .eiq-form-v3-race-title span,
.eiq-race-form-guide--final-locked .eiq-form-v3-footer,
.eiq-race-form-guide--final-locked .eiq-form-v3-race-title strong {
  letter-spacing: 0.08em;
}

.eiq-race-form-guide--final-locked .eiq-form-approved-tools,
.eiq-race-form-guide--final-locked .eiq-form-final-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8f4ea;
  border-bottom: 1px solid rgba(23, 32, 51, 0.14);
}

.eiq-race-form-guide--final-locked .eiq-form-final-tools button,
.eiq-race-form-guide--final-locked .eiq-form-final-tools select {
  border: 1px solid rgba(23, 32, 51, 0.16);
  background: #fffdf7;
  color: #172033;
  border-radius: 4px;
  min-height: 28px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked {
  border-radius: 0;
  background: #f8f4ea;
  border-top: 1px solid rgba(23, 32, 51, 0.12);
}

.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked table {
  min-width: var(--edgeiq-form-guide-min-width);
  table-layout: fixed;
}

.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked th,
.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked td {
  height: var(--edgeiq-form-guide-row-height);
  padding: 5px 7px;
  border-color: rgba(23, 32, 51, 0.12);
  font-size: 12px;
  color: #172033;
}

.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked th {
  background: #e5eef8;
  color: #253b58;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.03em;
}

.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked tbody tr.is-expanded > td,
.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked tbody tr:hover > td {
  background: rgba(47, 128, 237, 0.10);
}

.eiq-race-form-guide--final-locked .eiq-form-runner-expand {
  color: #172033;
  text-align: left;
  width: 100%;
}

.eiq-race-form-guide--final-locked .eiq-form-last5-strip span {
  background: #fffdf7;
  border: 1px solid rgba(23, 32, 51, 0.12);
  color: #172033;
}

.eiq-race-form-guide--final-locked .eiq-form-expanded-row > td {
  padding: 0 !important;
  background: #f3efe4 !important;
}

.eiq-race-form-guide--final-locked .eiq-form-final-runner-sheet {
  margin: 0;
  border: 2px solid #2e5c88;
  border-top: 0;
  background: #f7f2e9;
  color: #172033;
}

.eiq-race-form-guide--final-locked .eiq-form-final-runner-header {
  display: grid;
  grid-template-columns: 92px minmax(240px, 1fr) minmax(520px, 1.8fr);
  gap: 14px;
  align-items: center;
  padding: 14px 16px;
  min-height: 112px;
  background: #fffaf0;
  border-bottom: 1px solid rgba(23, 32, 51, 0.14);
}

.eiq-race-form-guide--final-locked .eiq-form-detail-silk {
  width: 70px;
  height: 70px;
  object-fit: contain;
  border-radius: 50%;
  background: #fff;
  border: 1px solid rgba(23, 32, 51, 0.14);
}

.eiq-race-form-guide--final-locked .eiq-form-v3-runner-identity span,
.eiq-race-form-guide--final-locked .eiq-form-v3-runner-identity p,
.eiq-race-form-guide--final-locked .eiq-form-final-current-strip dt,
.eiq-race-form-guide--final-locked .eiq-form-final-current-strip small {
  color: #6f7480;
}

.eiq-race-form-guide--final-locked .eiq-form-v3-runner-identity strong {
  color: #172033;
  font-size: 22px;
  letter-spacing: 0;
}

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(74px, 1fr));
  gap: 7px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip > div {
  background: #ffffff;
  border: 1px solid rgba(23, 32, 51, 0.13);
  border-radius: 4px;
  padding: 8px 9px;
  min-height: 58px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip dd {
  color: #172033;
  font-size: 17px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 220px;
  gap: 10px;
  padding: 12px 16px;
  align-items: stretch;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match,
.eiq-race-form-guide--final-locked .eiq-form-final-dossier-main,
.eiq-race-form-guide--final-locked .eiq-form-final-match-read {
  background: #fffdf7;
  border: 1px solid rgba(23, 32, 51, 0.14);
  border-radius: 4px;
  box-shadow: none;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match h3,
.eiq-race-form-guide--final-locked .eiq-form-final-profile-matrix header,
.eiq-race-form-guide--final-locked .eiq-form-final-match-read h3,
.eiq-race-form-guide--final-locked .eiq-form-final-recent-form header {
  margin: 0;
  padding: 8px 10px;
  color: #253b58;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.06em;
  border-bottom: 1px solid rgba(23, 32, 51, 0.13);
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match ul {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match li {
  display: grid;
  grid-template-columns: 8px 70px 1fr;
  gap: 6px;
  padding: 7px 9px;
  border-bottom: 1px solid rgba(23, 32, 51, 0.08);
  align-items: center;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match li i {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #2f80ed;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match li strong,
.eiq-race-form-guide--final-locked .eiq-form-final-today-match li small {
  color: #6f7480;
  font-size: 10px;
  font-weight: 800;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match li span {
  color: #172033;
  font-size: 12px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked .eiq-form-final-match-rating {
  margin: 8px;
  padding: 9px;
  background: #eaf2fb;
  border-radius: 4px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-grid {
  display: grid;
  grid-template-columns: 86px repeat(13, minmax(58px, 1fr));
  overflow: auto;
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-cell {
  min-height: 28px;
  padding: 5px 6px;
  border-right: 1px solid rgba(23, 32, 51, 0.10);
  border-bottom: 1px solid rgba(23, 32, 51, 0.10);
  background: #fffdf7;
  color: #172033;
  font-size: 11px;
  font-weight: 800;
  text-align: center;
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-cell--head {
  background: #e5eef8;
  color: #253b58;
  font-size: 9px;
  min-height: 36px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-cell--rowhead {
  background: #f0eadf;
  text-align: left;
  color: #253b58;
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-cell.is-today {
  background: rgba(56, 161, 105, 0.13);
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-cell.is-primary {
  box-shadow: inset 0 0 0 1px rgba(56, 161, 105, 0.45);
}

.eiq-race-form-guide--final-locked .eiq-form-final-match-read {
  padding-bottom: 8px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-match-read ul {
  margin: 0;
  padding: 9px 13px 9px 26px;
  color: #172033;
  font-size: 12px;
  line-height: 1.45;
}

.eiq-race-form-guide--final-locked .eiq-form-final-recent-form {
  margin: 0 16px 12px;
  background: #fffdf7;
  border: 1px solid rgba(23, 32, 51, 0.14);
  border-radius: 4px;
  overflow: hidden;
}

.eiq-race-form-guide--final-locked .eiq-form-final-recent-form header {
  display: flex;
  justify-content: space-between;
  background: #254c78;
  color: #fff;
}

.eiq-race-form-guide--final-locked .eiq-form-final-recent-form header span,
.eiq-race-form-guide--final-locked .eiq-form-final-recent-form header strong {
  color: #fff;
}

.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 table {
  min-width: 1320px;
  table-layout: fixed;
}

.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 th,
.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 td {
  padding: 5px 7px;
  border-color: rgba(23, 32, 51, 0.10);
  color: #172033;
  font-size: 11px;
  line-height: 1.25;
}

.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 th {
  background: #254c78;
  color: #fff;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked .eiq-going-cell.is-good,
.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 .is-negative,
.eiq-race-form-guide--final-locked .eiq-cell-momentum[data-direction="up"] {
  background: rgba(56, 161, 105, 0.22);
  color: #14532d;
}

.eiq-race-form-guide--final-locked .eiq-going-cell.is-soft {
  background: rgba(47, 128, 237, 0.16);
  color: #1d4f8f;
}

.eiq-race-form-guide--final-locked .eiq-going-cell.is-heavy,
.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 .is-positive,
.eiq-race-form-guide--final-locked .eiq-cell-momentum[data-direction="down"] {
  background: rgba(194, 65, 58, 0.18);
  color: #8f1f1a;
}

.eiq-race-form-guide--final-locked .eiq-form-final-sectional-legend {
  display: flex;
  gap: 14px;
  align-items: center;
  margin: -6px 16px 14px;
  padding: 8px 10px;
  background: #f0eadf;
  border: 1px solid rgba(23, 32, 51, 0.12);
  border-radius: 4px;
  color: #253b58;
  font-size: 11px;
  font-weight: 700;
}

@media (max-width: 980px) {
  .eiq-race-form-guide--final-locked .eiq-form-final-runner-header,
  .eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
    grid-template-columns: 1fr;
  }
}
/* EDGEIQ FORM GUIDE FINAL LOCKED V2 END */
'''

def main():
    text = CSS.read_text(encoding='utf-8')
    if MARKER_START in text and MARKER_END in text:
        before = text.split(MARKER_START)[0].rstrip()
        after = text.split(MARKER_END, 1)[1].lstrip()
        text = before + '\n\n' + BLOCK.strip() + '\n\n' + after
    else:
        text = text.rstrip() + '\n\n' + BLOCK.strip() + '\n'
    CSS.write_text(text, encoding='utf-8')
    REPORT.write_text(json.dumps({'status':'FORM_GUIDE_FINAL_RUNNER_HERO_V2_CSS_APPLIED','timestamp':datetime.now().isoformat(timespec='seconds')}, indent=2), encoding='utf-8')
    print('FORM_GUIDE_FINAL_RUNNER_HERO_V2_CSS_APPLIED')

if __name__ == '__main__':
    main()
