from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

TSX = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

tsx_backup = TSX.with_name(
    f"{TSX.stem}_CHECKPOINT_BEFORE_LOCKED_FORM_GUIDE_UI_{stamp}{TSX.suffix}"
)
css_backup = CSS.with_name(
    f"{CSS.stem}_CHECKPOINT_BEFORE_LOCKED_FORM_GUIDE_UI_{stamp}{CSS.suffix}"
)

shutil.copy2(TSX, tsx_backup)
shutil.copy2(CSS, css_backup)

tsx = TSX.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

# ------------------------------------------------------------
# COPY / LABEL RECOVERY
# ------------------------------------------------------------

replacements = {
    ">MATCH READ<": ">TODAY'S MATCH INSIGHTS<",
    ">HORSE PROFILE (CAREER)<": ">HORSE PROFILE<",
    ">CURRENT EPI<": ">EPI TODAY<",
    ">EDGEIQ PRICE<": ">EDGEiQ PRICE (FAIR)<",
    "Complete runner form dossiers": "Complete runner profiles",
    "Full governed profile and recent-form evidence in saddlecloth order.":
        "Governed profile and recent-form evidence in saddlecloth order.",
}

for old, new in replacements.items():
    tsx = tsx.replace(old, new)

# ------------------------------------------------------------
# FINAL LOCKED UI OVERRIDES
# ------------------------------------------------------------

START = "/* EDGEIQ_FORM_GUIDE_LOCKED_UI_V3_START */"
END = "/* EDGEIQ_FORM_GUIDE_LOCKED_UI_V3_END */"

locked_css = r'''
/* EDGEIQ_FORM_GUIDE_LOCKED_UI_V3_START */

.eiq-race-form-guide--final-locked {
  --locked-blue: #075fe4;
  --locked-navy: #07145d;
  --locked-text: #17224d;
  --locked-muted: #69728b;
  --locked-line: #d9e2ef;
  --locked-soft: #f7f9fc;
  --locked-today: #eef5ff;
  --locked-positive: #18743c;
  --locked-positive-bg: #eef8f1;
  width: 100%;
  padding: 18px 20px 38px;
  background: #ffffff;
  color: var(--locked-text);
}

/* Summary table */
.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked {
  border: 1px solid #d7dfeb;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: none;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked th {
  height: 39px;
  padding: 8px 7px;
  background: #ffffff;
  border-bottom: 1px solid #cad6e5;
  color: var(--locked-navy);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.025em;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked td {
  height: 39px;
  padding: 7px 7px;
  border-bottom: 1px solid #e4e9f0;
  color: var(--locked-navy);
  font-size: 11px;
  font-weight: 700;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked tbody tr:hover td {
  background: #f4f8ff;
}

/* Section introduction */
.eiq-form-all-runner-dossiers {
  margin-top: 18px;
}

.eiq-form-all-runner-dossiers__header {
  min-height: 56px;
  margin-bottom: 10px;
  padding: 11px 15px;
  border: 1px solid #cbd9ec;
  border-left: 4px solid var(--locked-blue);
  border-radius: 5px;
  background: #ffffff;
  box-shadow: none;
}

.eiq-form-all-runner-dossiers__header span {
  color: var(--locked-blue);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.eiq-form-all-runner-dossiers__header h3 {
  color: var(--locked-navy);
  font-size: 17px;
  font-weight: 900;
}

.eiq-form-all-runner-dossiers__header p {
  color: var(--locked-muted);
  font-size: 10px;
}

/* Runner shell */
.eiq-form-all-runner-dossiers__list {
  gap: 15px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-runner-sheet {
  border: 1px solid #8fb6ff;
  border-radius: 7px;
  background: #ffffff;
  box-shadow: none;
  overflow: hidden;
}

/* Runner hero header */
.eiq-race-form-guide--final-locked .eiq-form-final-runner-header {
  display: grid;
  grid-template-columns: 54px minmax(300px, 1fr) minmax(680px, 1.55fr);
  align-items: center;
  gap: 14px;
  min-height: 86px;
  padding: 10px 12px;
  background: #ffffff;
  border-bottom: 1px solid #d7e1ee;
}

.eiq-race-form-guide--final-locked .eiq-form-detail-silk {
  width: 48px;
  height: 56px;
}

.eiq-race-form-guide--final-locked
.eiq-form-v3-runner-identity > span {
  display: none;
}

.eiq-race-form-guide--final-locked
.eiq-form-v3-runner-identity strong {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--locked-navy);
  font-size: 21px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-v3-runner-identity strong em {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  place-items: center;
  border-radius: 5px;
  background: var(--locked-blue);
  color: #ffffff;
  font-size: 21px;
  font-style: normal;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-v3-runner-identity p {
  margin: 6px 0 0 54px;
  color: #27325f;
  font-size: 10.5px;
  font-weight: 700;
}

/* Metric ribbon */
.eiq-race-form-guide--final-locked .eiq-form-final-current-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(92px, 1fr));
  width: 100%;
  border: 1px solid #d5deea;
  border-radius: 5px;
  background: #ffffff;
  overflow: hidden;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip > div {
  min-height: 60px;
  padding: 7px 8px;
  border-right: 1px solid #dce4ee;
  text-align: center;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip > div:last-child {
  border-right: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip dt {
  color: var(--locked-navy);
  font-size: 8px;
  font-weight: 900;
  line-height: 1.2;
  text-transform: none;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip dd {
  margin-top: 5px;
  color: var(--locked-navy);
  font-size: 18px;
  font-weight: 900;
  line-height: 1;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-current-strip small {
  margin-top: 4px;
  color: var(--locked-positive);
  font-size: 9px;
  font-weight: 800;
}

/* Core three-column dossier */
.eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
  display: grid;
  grid-template-columns: minmax(205px, 0.8fr) minmax(780px, 3.35fr) minmax(230px, 0.9fr);
  align-items: start;
  gap: 8px;
  padding: 8px 9px 7px;
  background: #ffffff;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match,
.eiq-race-form-guide--final-locked .eiq-form-final-dossier-main,
.eiq-race-form-guide--final-locked .eiq-form-final-match-read {
  min-height: 0;
  height: auto;
  border: 1px solid #d9e2ed;
  border-radius: 5px;
  background: #ffffff;
  overflow: hidden;
}

/* Section titles */
.eiq-race-form-guide--final-locked .eiq-form-final-today-match h3,
.eiq-race-form-guide--final-locked
.eiq-form-final-profile-matrix header,
.eiq-race-form-guide--final-locked .eiq-form-final-match-read h3,
.eiq-race-form-guide--final-locked .eiq-form-final-recent-form header {
  min-height: 34px;
  margin: 0;
  padding: 8px 10px;
  background: #ffffff;
  border-bottom: 1px solid #d7e1ed;
  color: var(--locked-navy);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.02em;
}

/* Today's Match */
.eiq-race-form-guide--final-locked
.eiq-form-final-today-match ul {
  margin: 0;
  padding: 4px 9px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li {
  display: grid;
  grid-template-columns: 11px minmax(58px, 0.8fr) minmax(76px, 1.2fr);
  gap: 6px;
  min-height: 35px;
  padding: 7px 0;
  border-bottom: 1px solid #edf0f5;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li:last-child {
  border-bottom: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li i {
  width: 5px;
  height: 5px;
  margin-top: 4px;
  border-radius: 50%;
  background: var(--locked-blue);
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li strong {
  color: var(--locked-navy);
  font-size: 9px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li span,
.eiq-race-form-guide--final-locked
.eiq-form-final-today-match li small {
  color: var(--locked-positive);
  font-size: 9px;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-rating {
  margin: 7px 9px 9px;
  padding: 8px 9px;
  border: 1px solid #d9e1eb;
  border-radius: 4px;
  background: #ffffff;
  color: var(--locked-navy);
  font-size: 9px;
  font-weight: 800;
}

/* Horse profile */
.eiq-race-form-guide--final-locked
.eiq-form-final-profile-matrix,
.eiq-race-form-guide--final-locked
.eiq-form-final-dossier-main {
  height: auto !important;
  min-height: 0 !important;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-grid {
  align-content: start;
  min-height: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell {
  min-width: 56px;
  min-height: 35px;
  padding: 6px 5px;
  border-right: 1px solid #e0e6ee;
  border-bottom: 1px solid #e0e6ee;
  background: #ffffff;
  color: var(--locked-navy);
  font-size: 9.5px;
  font-weight: 750;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell--head {
  min-height: 44px;
  background: #ffffff;
  color: var(--locked-navy);
  font-size: 8px;
  font-weight: 900;
  line-height: 1.2;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell--rowhead {
  justify-content: flex-start;
  min-width: 70px;
  padding-left: 8px;
  background: #f5f2ea;
  color: #27325f;
  font-size: 8.5px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell.is-today {
  background: var(--locked-today);
  box-shadow:
    inset 1px 0 0 #7caeff,
    inset -1px 0 0 #7caeff;
  color: var(--locked-navy);
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell.is-primary {
  background: var(--locked-positive-bg);
  box-shadow:
    inset 1px 0 0 #7ab38b,
    inset -1px 0 0 #7ab38b;
  color: #165d31;
  font-weight: 900;
}

/* Insights */
.eiq-race-form-guide--final-locked
.eiq-form-final-match-read ul {
  display: grid;
  gap: 7px;
  margin: 0;
  padding: 10px 10px 11px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li {
  position: relative;
  padding-left: 15px;
  color: var(--locked-navy);
  font-size: 9px;
  font-weight: 750;
  line-height: 1.35;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li::before {
  position: absolute;
  top: 2px;
  left: 0;
  width: 9px;
  height: 9px;
  border: 1px solid #6ca881;
  border-radius: 50%;
  color: #287445;
  content: "";
}

/* Recent form */
.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form {
  margin: 0 9px 7px;
  border: 0;
  border-top: 1px solid #d9e2ed;
  border-radius: 0;
  background: #ffffff;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form header {
  padding: 8px 1px 6px;
  border-bottom: 0;
  background: #ffffff;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 table {
  min-width: 1460px;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 th {
  height: 30px;
  padding: 5px 6px;
  border-right: 0;
  border-bottom: 1px solid #d9e0ea;
  background: #ffffff;
  color: var(--locked-navy);
  font-size: 8px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 td {
  height: 29px;
  padding: 5px 6px;
  border-right: 0;
  border-bottom: 1px solid #edf0f4;
  color: var(--locked-navy);
  font-size: 8.5px;
  font-weight: 700;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 tbody tr:nth-child(even) td {
  background: #ffffff;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 tbody tr:hover td {
  background: #f5f8fc;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-sectional-legend {
  min-height: 24px;
  margin: 0 9px 7px;
  padding: 5px 2px;
  gap: 16px;
  border: 0;
  background: #ffffff;
  color: #505a73;
  font-size: 8px;
}

/* Remove decorative treatment */
.eiq-race-form-guide--final-locked
.eiq-form-final-runner-sheet::before,
.eiq-race-form-guide--final-locked
.eiq-form-final-runner-sheet::after {
  display: none;
}

/* Responsive */
@media (max-width: 1350px) {
  .eiq-race-form-guide--final-locked .eiq-form-final-runner-header {
    grid-template-columns: 50px minmax(260px, 1fr);
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-current-strip {
    grid-column: 1 / -1;
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
    grid-template-columns: minmax(190px, 0.8fr) minmax(680px, 3fr);
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-match-read {
    grid-column: 1 / -1;
  }
}

/* EDGEIQ_FORM_GUIDE_LOCKED_UI_V3_END */
'''

if START in css and END in css:
    start = css.index(START)
    end = css.index(END) + len(END)
    css = css[:start] + locked_css.strip() + css[end:]
else:
    css = css.rstrip() + "\n\n" + locked_css.strip() + "\n"

TSX.write_text(tsx, encoding="utf-8", newline="\n")
CSS.write_text(css, encoding="utf-8", newline="\n")

print(f"UPDATED_TSX={TSX}")
print(f"UPDATED_CSS={CSS}")
print(f"CHECKPOINT_TSX={tsx_backup}")
print(f"CHECKPOINT_CSS={css_backup}")
print("FORM_GUIDE_LOCKED_UI_V3_PATCH_PASS")
