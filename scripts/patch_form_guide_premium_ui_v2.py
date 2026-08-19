from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
CSS_PATH = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = CSS_PATH.with_name(
    f"{CSS_PATH.stem}_CHECKPOINT_BEFORE_FORM_GUIDE_PREMIUM_UI_{timestamp}{CSS_PATH.suffix}"
)

shutil.copy2(CSS_PATH, backup)

css = CSS_PATH.read_text(encoding="utf-8")

START = "/* EDGEIQ_FORM_GUIDE_PREMIUM_UI_V2_START */"
END = "/* EDGEIQ_FORM_GUIDE_PREMIUM_UI_V2_END */"

premium_css = r'''
/* EDGEIQ_FORM_GUIDE_PREMIUM_UI_V2_START */

/* ================================================================
   FORM GUIDE — PREMIUM ALL-RUNNER DOSSIER
   Presentation only. No feed, engine or calculation changes.
   ================================================================ */

.eiq-race-form-guide--final-locked {
  --form-blue-900: #102f50;
  --form-blue-800: #17476f;
  --form-blue-700: #1263a5;
  --form-blue-600: #1976bd;
  --form-blue-200: #c9dcef;
  --form-blue-100: #e8f1fa;
  --form-blue-050: #f4f8fc;
  --form-text: #1c3045;
  --form-muted: #63778b;
  --form-border: #ccd9e6;
  --form-soft-border: #dde6ef;
  --form-white: #ffffff;

  box-sizing: border-box;
  width: 100%;
  max-width: none;
  padding: 20px 22px 44px;
  background: #f3f6fa;
  color: var(--form-text);
  font-size: 14px;
}

/* Keep every child on predictable box sizing. */
.eiq-race-form-guide--final-locked *,
.eiq-race-form-guide--final-locked *::before,
.eiq-race-form-guide--final-locked *::after {
  box-sizing: border-box;
}

/* ----------------------------------------------------------------
   RACE HEADER
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-race-header--v3 {
  padding: 20px 22px;
  border: 1px solid var(--form-blue-200);
  border-top: 5px solid var(--form-blue-700);
  border-radius: 7px;
  background: var(--form-white);
  box-shadow: 0 4px 14px rgba(22, 58, 94, 0.08);
}

.eiq-race-form-guide--final-locked .eiq-form-v3-race-title span {
  margin-bottom: 5px;
  color: var(--form-blue-600);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.eiq-race-form-guide--final-locked .eiq-form-v3-race-title strong {
  color: var(--form-muted);
  font-size: 13px;
  font-weight: 700;
}

.eiq-race-form-guide--final-locked .eiq-form-v3-race-title h2 {
  margin: 4px 0 0;
  color: var(--form-blue-900);
  font-size: 25px;
  font-weight: 900;
  line-height: 1.15;
}

/* ----------------------------------------------------------------
   TOOLS
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-approved-tools,
.eiq-race-form-guide--final-locked .eiq-form-final-tools {
  min-height: 48px;
  margin: 12px 0;
  padding: 8px 10px;
  gap: 8px;
  border: 1px solid var(--form-border);
  border-radius: 6px;
  background: var(--form-white);
}

.eiq-race-form-guide--final-locked .eiq-form-final-tools label span {
  font-size: 11px;
  font-weight: 800;
  color: var(--form-blue-800);
}

.eiq-race-form-guide--final-locked .eiq-form-final-tools button,
.eiq-race-form-guide--final-locked .eiq-form-final-tools select {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #b9cada;
  border-radius: 4px;
  background: #ffffff;
  color: var(--form-blue-800);
  font-size: 11px;
  font-weight: 800;
}

/* ----------------------------------------------------------------
   FIELD SUMMARY TABLE
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked {
  border: 1px solid var(--form-border);
  border-radius: 7px;
  background: var(--form-white);
  box-shadow: 0 3px 10px rgba(23, 60, 96, 0.06);
  overflow-x: auto;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked table {
  min-width: 1380px;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked th {
  height: 43px;
  padding: 9px 8px;
  border-bottom: 1px solid #b9cde0;
  background: #e9f1f9;
  color: var(--form-blue-900);
  font-size: 10.5px;
  font-weight: 900;
  letter-spacing: 0.035em;
  line-height: 1.15;
  white-space: nowrap;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked td {
  height: 42px;
  padding: 8px 8px;
  border-bottom: 1px solid #e2e9f0;
  color: #253b52;
  font-size: 12px;
  font-weight: 600;
  vertical-align: middle;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked tbody tr:last-child td {
  border-bottom: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked tbody tr:nth-child(even) td {
  background: #fafbfd;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked tbody tr:hover td {
  background: #edf5fd;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked tbody tr.is-targeted td {
  background: #dcecff;
  box-shadow:
    inset 0 1px 0 #87b9e4,
    inset 0 -1px 0 #87b9e4;
}

.eiq-race-form-guide--final-locked .eiq-cell-no {
  color: var(--form-blue-800);
  font-size: 13px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked .eiq-form-silk {
  width: 27px;
  height: 31px;
  object-fit: contain;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-navigator {
  min-width: 145px;
  padding: 2px 0;
  border: 0;
  background: transparent;
  color: var(--form-blue-900);
  text-align: left;
  cursor: pointer;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-navigator strong {
  display: block;
  font-size: 12.5px;
  font-weight: 900;
  line-height: 1.25;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-navigator small {
  display: block;
  margin-top: 3px;
  color: #a62f35;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.05em;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-navigator:hover strong {
  color: var(--form-blue-600);
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* ----------------------------------------------------------------
   COMPLETE FIELD DIVIDER
   ---------------------------------------------------------------- */

.eiq-form-all-runner-dossiers {
  margin-top: 26px;
}

.eiq-form-all-runner-dossiers__header {
  min-height: 68px;
  margin-bottom: 14px;
  padding: 14px 18px;
  align-items: center;
  border: 1px solid var(--form-blue-200);
  border-left: 5px solid var(--form-blue-700);
  border-radius: 7px;
  background: var(--form-white);
  box-shadow: 0 2px 7px rgba(23, 60, 96, 0.05);
}

.eiq-form-all-runner-dossiers__header span {
  margin: 0 0 4px;
  color: var(--form-blue-600);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.eiq-form-all-runner-dossiers__header h3 {
  margin: 0;
  color: var(--form-blue-900);
  font-size: 21px;
  font-weight: 900;
  line-height: 1.1;
}

.eiq-form-all-runner-dossiers__header p {
  max-width: 470px;
  color: var(--form-muted);
  font-size: 12px;
  line-height: 1.4;
  text-align: right;
}

.eiq-form-all-runner-dossiers__list {
  display: grid;
  gap: 22px;
}

/* ----------------------------------------------------------------
   RUNNER DOSSIER SHELL
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-final-runner-sheet {
  width: 100%;
  margin: 0;
  border: 1px solid #b9cde1;
  border-top: 5px solid var(--form-blue-700);
  border-radius: 8px;
  background: var(--form-white);
  box-shadow: 0 5px 18px rgba(23, 60, 96, 0.09);
  overflow: hidden;
}

.eiq-form-all-runner-dossiers__list > div {
  scroll-margin-top: 100px;
}

.eiq-form-all-runner-dossiers__list > div.is-targeted
.eiq-form-final-runner-sheet {
  border-color: #4b96d0;
  box-shadow:
    0 0 0 3px rgba(44, 133, 200, 0.18),
    0 8px 22px rgba(23, 60, 96, 0.13);
}

.eiq-race-form-guide--final-locked
.eiq-form-final-runner-sheet.is-scratched {
  opacity: 0.62;
  filter: grayscale(0.3);
}

/* ----------------------------------------------------------------
   RUNNER IDENTITY HEADER
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-final-runner-header {
  display: grid;
  grid-template-columns: 64px minmax(260px, 0.9fr) minmax(620px, 1.5fr);
  align-items: center;
  gap: 16px;
  min-height: 108px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--form-border);
  background:
    linear-gradient(
      100deg,
      #eef5fc 0%,
      #ffffff 42%,
      #ffffff 100%
    );
}

.eiq-race-form-guide--final-locked .eiq-form-detail-silk {
  width: 58px;
  height: 68px;
  object-fit: contain;
}

.eiq-race-form-guide--final-locked .eiq-form-silk--fallback {
  border: 1px solid #d3dce5;
  border-radius: 50%;
  background: #f5f7f9;
}

.eiq-race-form-guide--final-locked .eiq-form-v3-runner-identity {
  min-width: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-v3-runner-identity > span {
  display: block;
  margin-bottom: 5px;
  color: var(--form-blue-600);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.13em;
}

.eiq-race-form-guide--final-locked
.eiq-form-v3-runner-identity strong {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--form-blue-900);
  font-size: 24px;
  font-weight: 900;
  line-height: 1.1;
}

.eiq-race-form-guide--final-locked
.eiq-form-v3-runner-identity strong em {
  display: inline-grid;
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  place-items: center;
  border-radius: 5px;
  background: var(--form-blue-700);
  color: #ffffff;
  font-size: 19px;
  font-style: normal;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-v3-runner-identity p {
  margin: 8px 0 0;
  color: #566c82;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
}

/* ----------------------------------------------------------------
   CURRENT METRIC STRIP
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(92px, 1fr));
  width: 100%;
  gap: 0;
  border: 1px solid #c7d7e7;
  border-radius: 6px;
  background: #ffffff;
  overflow: hidden;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip > div {
  display: flex;
  min-width: 0;
  min-height: 62px;
  padding: 9px 8px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-right: 1px solid #d9e3ed;
  text-align: center;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip > div:last-child {
  border-right: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip dt {
  min-height: 21px;
  color: #4d6680;
  font-size: 8.5px;
  font-weight: 900;
  letter-spacing: 0.03em;
  line-height: 1.15;
  text-transform: uppercase;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip dd {
  margin: 4px 0 0;
  color: var(--form-blue-900);
  font-size: 17px;
  font-weight: 900;
  line-height: 1;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip small {
  margin-top: 3px;
  color: var(--form-muted);
  font-size: 8.5px;
  font-weight: 700;
}

/* ----------------------------------------------------------------
   THREE-COLUMN INTELLIGENCE DOSSIER
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
  display: grid;
  grid-template-columns:
    minmax(235px, 0.9fr)
    minmax(760px, 3.25fr)
    minmax(235px, 0.9fr);
  align-items: start;
  gap: 12px;
  padding: 14px 16px;
  background: #f5f8fb;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match,
.eiq-race-form-guide--final-locked .eiq-form-final-dossier-main,
.eiq-race-form-guide--final-locked .eiq-form-final-match-read {
  min-width: 0;
  min-height: 0;
  height: auto;
  align-self: start;
  border: 1px solid var(--form-border);
  border-radius: 6px;
  background: var(--form-white);
  overflow: hidden;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match h3,
.eiq-race-form-guide--final-locked
.eiq-form-final-profile-matrix header,
.eiq-race-form-guide--final-locked .eiq-form-final-match-read h3 {
  display: flex;
  align-items: center;
  min-height: 42px;
  margin: 0;
  padding: 10px 12px;
  border-bottom: 1px solid #c9d9e8;
  background: #e7f0f9;
  color: var(--form-blue-900);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.045em;
}

/* Remove the large blank panel beneath the profile matrix. */
.eiq-race-form-guide--final-locked .eiq-form-final-dossier-main,
.eiq-race-form-guide--final-locked .eiq-form-final-profile-matrix {
  height: auto !important;
  min-height: 0 !important;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-matrix {
  display: block;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-grid {
  height: auto;
  min-height: 0;
  align-content: start;
}

/* ----------------------------------------------------------------
   TODAY'S MATCH
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match ul {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 6px 11px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li {
  display: grid;
  grid-template-columns: 12px minmax(72px, 1fr) minmax(80px, 1fr);
  align-items: start;
  gap: 7px;
  min-height: 43px;
  padding: 9px 2px;
  border-bottom: 1px solid #e1e8ef;
  font-size: 11px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li:last-child {
  border-bottom: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li i {
  width: 7px;
  height: 7px;
  margin-top: 4px;
  border-radius: 50%;
  background: var(--form-blue-600);
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li strong {
  color: #314b64;
  font-size: 10px;
  font-weight: 800;
  line-height: 1.3;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li span,
.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li small {
  color: #2b7a43;
  font-size: 10px;
  font-weight: 800;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-rating {
  margin: 8px 11px 11px;
  padding: 11px;
  border: 1px solid #d5e1ed;
  border-radius: 5px;
  background: #f2f6fa;
  color: #344e68;
  font-size: 11px;
  line-height: 1.4;
}

/* ----------------------------------------------------------------
   HORSE PROFILE MATRIX
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-grid {
  display: grid;
  width: 100%;
  overflow-x: auto;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  min-height: 40px;
  padding: 8px 6px;
  border-right: 1px solid #dde5ed;
  border-bottom: 1px solid #dde5ed;
  color: #243d55;
  background: #ffffff;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.15;
  text-align: center;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell--head {
  min-height: 48px;
  padding: 7px 5px;
  background: #e7f0f9;
  color: var(--form-blue-900);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.025em;
  line-height: 1.2;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell--rowhead {
  justify-content: flex-start;
  min-width: 74px;
  padding-left: 10px;
  background: #eeeae1;
  color: #31475d;
  font-size: 10px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell.is-today {
  background: #dfeeff;
  color: #0f568f;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell.is-primary {
  box-shadow: inset 0 0 0 1px #80b8a2;
  background: #e7f4ef;
  color: #245c47;
  font-weight: 900;
}

/* ----------------------------------------------------------------
   MATCH READ
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read ul {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 13px 13px 15px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li {
  position: relative;
  padding-left: 18px;
  color: #28435d;
  font-size: 10.5px;
  font-weight: 700;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li::before {
  position: absolute;
  top: 1px;
  left: 0;
  display: grid;
  width: 13px;
  height: 13px;
  place-items: center;
  border: 1px solid #73a887;
  border-radius: 50%;
  color: #3e8c5c;
  content: "✓";
  font-size: 8px;
  font-weight: 900;
}

/* ----------------------------------------------------------------
   RECENT FORM
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form {
  margin: 0 16px 14px;
  border: 1px solid var(--form-border);
  border-radius: 6px;
  background: var(--form-white);
  overflow: hidden;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form header {
  display: flex;
  align-items: center;
  min-height: 44px;
  margin: 0;
  padding: 9px 13px;
  border-bottom: 1px solid #c9d9e8;
  background: #e7f0f9;
  color: var(--form-blue-900);
}

.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form header span {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.045em;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form header strong {
  font-size: 11px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 {
  width: 100%;
  overflow-x: auto;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 table {
  width: 100%;
  min-width: 1500px;
  border-collapse: collapse;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 th {
  height: 37px;
  padding: 8px 7px;
  border-right: 1px solid #dde5ed;
  border-bottom: 1px solid #d2dde8;
  background: #f0f4f8;
  color: #21466b;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.025em;
  line-height: 1.15;
  text-align: center;
  white-space: nowrap;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 td {
  height: 38px;
  padding: 7px 7px;
  border-right: 1px solid #e6ebf0;
  border-bottom: 1px solid #e4eaf0;
  color: #263f58;
  font-size: 10.5px;
  font-weight: 650;
  line-height: 1.2;
  text-align: center;
  white-space: nowrap;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 tbody tr:nth-child(even) td {
  background: #f8fafc;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 tbody tr:hover td {
  background: #edf5fc;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-sectional-legend {
  display: flex;
  min-height: 35px;
  margin: 0 16px 15px;
  padding: 8px 11px;
  align-items: center;
  gap: 20px;
  border: 1px solid #d6e0e9;
  border-radius: 5px;
  background: #f2f5f8;
  color: #5b6e82;
  font-size: 9.5px;
  font-weight: 700;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-sectional-legend strong {
  color: #344e67;
}

/* ----------------------------------------------------------------
   EMPTY DATA
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-empty {
  margin: 0;
  padding: 18px;
  color: var(--form-muted);
  font-size: 12px;
  text-align: center;
}

/* ----------------------------------------------------------------
   FOOTER
   ---------------------------------------------------------------- */

.eiq-race-form-guide--final-locked .eiq-form-v3-footer {
  min-height: 42px;
  margin-top: 20px;
  padding: 10px 14px;
  border: 1px solid var(--form-border);
  border-radius: 5px;
  background: #ffffff;
  color: var(--form-muted);
  font-size: 10px;
}

/* ----------------------------------------------------------------
   RESPONSIVE LAYOUTS
   ---------------------------------------------------------------- */

@media (max-width: 1500px) {
  .eiq-race-form-guide--final-locked
  .eiq-form-final-runner-header {
    grid-template-columns: 58px minmax(260px, 0.8fr) minmax(560px, 1.6fr);
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-dossier-grid {
    grid-template-columns:
      minmax(210px, 0.85fr)
      minmax(680px, 3fr)
      minmax(210px, 0.85fr);
  }
}

@media (max-width: 1250px) {
  .eiq-race-form-guide--final-locked
  .eiq-form-final-runner-header {
    grid-template-columns: 58px minmax(260px, 1fr);
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-current-strip {
    grid-column: 1 / -1;
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-dossier-grid {
    grid-template-columns: minmax(210px, 0.8fr) minmax(650px, 2.6fr);
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-match-read {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .eiq-race-form-guide--final-locked {
    padding: 10px 8px 30px;
  }

  .eiq-form-all-runner-dossiers__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .eiq-form-all-runner-dossiers__header p {
    text-align: left;
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-runner-header {
    grid-template-columns: 52px minmax(220px, 1fr);
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-current-strip {
    grid-template-columns: repeat(3, minmax(90px, 1fr));
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-current-strip > div:nth-child(3) {
    border-right: 0;
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-current-strip > div:nth-child(-n + 3) {
    border-bottom: 1px solid #d9e3ed;
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-dossier-grid {
    grid-template-columns: 1fr;
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-match-read {
    grid-column: auto;
  }
}

/* EDGEIQ_FORM_GUIDE_PREMIUM_UI_V2_END */
'''

if START in css and END in css:
    start_index = css.index(START)
    end_index = css.index(END) + len(END)
    css = css[:start_index] + premium_css.strip() + css[end_index:]
else:
    css = css.rstrip() + "\n\n" + premium_css.strip() + "\n"

CSS_PATH.write_text(css, encoding="utf-8", newline="\n")

print(f"CHECKPOINT={backup}")
print(f"UPDATED={CSS_PATH}")
print("FORM_GUIDE_PREMIUM_UI_V2_PATCH_PASS")
