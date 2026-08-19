from pathlib import Path
import shutil
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
FORM = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
MARKER = "/* EDGEIQ APPROVED UI PHASE 06 FORM GUIDE */"


def checkpoint() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = CHECKPOINT_ROOT / f"CHECKPOINT_APPROVED_UI_PHASE06_FORM_GUIDE_PATCH_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in (CSS, FORM):
        shutil.copy2(path, out / path.name)
    return out


def patch_form_widths() -> bool:
    text = FORM.read_text(encoding="utf-8")
    old = '''const summaryColumnWidths = [
  "44px",
  "56px",
  "108px",
  "210px",
  "172px",
  "154px",
  "56px",
  "48px",
  "58px",
  "64px",
  "84px",
  "82px",
  "92px",
  "106px",
  "82px",
  "96px",
];'''
    new = '''const summaryColumnWidths = [
  "36px",
  "42px",
  "78px",
  "158px",
  "128px",
  "124px",
  "44px",
  "38px",
  "44px",
  "52px",
  "72px",
  "72px",
  "78px",
  "94px",
  "68px",
  "82px",
];'''
    if old not in text:
        raise SystemExit("Expected summaryColumnWidths block not found; source changed unexpectedly.")
    FORM.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    return True


def patch_css() -> bool:
    text = CSS.read_text(encoding="utf-8")
    block = f'''

{MARKER}
:root {{
  --eiq-approved-sidebar: 186px;
}}

.eiq-approved-shell__frame {{
  grid-template-rows: 66px minmax(0, 1fr) 36px;
}}

.eiq-approved-topbar {{
  padding: 0 18px 0 20px;
}}

.eiq-approved-topbar__identity strong {{
  font-size: 20px;
  line-height: 1.05;
}}

.eiq-approved-topbar__identity span {{
  margin-top: 4px;
  font-size: 13px;
}}

.eiq-approved-topbar__ops {{
  gap: 13px;
  font-size: 12px;
}}

.eiq-approved-topbar__ops span {{
  padding-left: 13px;
}}

.eiq-approved-shell__content {{
  padding: 18px 18px 12px 20px;
}}

.eiq-approved-shell__footer {{
  padding: 0 18px;
  font-size: 11px;
}}

.eiq-app-nav {{
  padding: 12px 8px 12px;
  gap: 13px;
}}

.eiq-app-nav__brand {{
  height: 64px;
  padding-left: 4px;
}}

.eiq-app-nav__brand strong {{
  font-size: 31px;
  letter-spacing: -0.055em;
}}

.eiq-app-nav__brand em {{
  font-size: 10px;
  letter-spacing: 0.075em;
}}

.eiq-app-nav nav {{
  gap: 1px;
}}

.eiq-app-nav button {{
  min-height: 34px;
  grid-template-columns: 25px minmax(0, 1fr);
  gap: 7px;
  padding: 0 8px;
}}

.eiq-app-nav button strong {{
  font-size: 12px;
  letter-spacing: 0;
}}

.eiq-app-nav button span svg {{
  width: 17px;
  height: 17px;
}}

.eiq-race-form-guide--v4 {{
  display: grid;
  gap: 8px;
}}

.eiq-race-form-guide--v4 .eiq-form-race-header--v3 {{
  min-height: 96px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(430px, 0.72fr);
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 6px;
}}

.eiq-race-form-guide--v4 .eiq-form-v3-race-title span {{
  font-size: 10px;
  letter-spacing: 0.12em;
}}

.eiq-race-form-guide--v4 .eiq-form-v3-race-title strong {{
  display: block;
  margin-top: 6px;
  font-size: 22px;
  line-height: 1.12;
}}

.eiq-race-form-guide--v4 .eiq-form-race-header h2 {{
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.2;
}}

.eiq-race-form-guide--v4 .eiq-form-race-header--v3 dl {{
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}}

.eiq-race-form-guide--v4 .eiq-form-race-header--v3 dl div {{
  min-height: 48px;
  padding: 8px 10px;
  border-radius: 5px;
}}

.eiq-race-form-guide--v4 .eiq-form-race-header dt {{
  font-size: 9px;
}}

.eiq-race-form-guide--v4 .eiq-form-race-header dd {{
  margin-top: 4px;
  font-size: 13px;
}}

.eiq-race-form-guide--v4 .eiq-form-race-selector {{
  gap: 8px;
  margin: 0;
}}

.eiq-race-form-guide--v4 .eiq-form-race-selector button {{
  width: 40px;
  height: 30px;
  min-height: 30px;
  border-radius: 5px;
  font-size: 12px;
}}

.eiq-race-form-guide--v4 .eiq-form-v33-tools {{
  margin-top: -1px;
}}

.eiq-race-form-guide--v4 .eiq-form-metric-guide-button {{
  height: 28px;
  padding: 0 12px;
  border-radius: 5px;
  font-size: 10px;
}}

.eiq-race-form-guide--v4 .eiq-form-summary-table--all-runner {{
  overflow: hidden;
  --edgeiq-form-guide-row-height: 32px;
}}

.eiq-race-form-guide--v4 .eiq-form-summary-table--all-runner table {{
  min-width: 0 !important;
  width: 100% !important;
  table-layout: fixed;
}}

.eiq-race-form-guide--v4 .eiq-form-summary-table th,
.eiq-race-form-guide--v4 .eiq-form-summary-table td {{
  height: 32px;
  padding: 0 6px;
  font-size: 11px;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

.eiq-race-form-guide--v4 .eiq-form-summary-table th {{
  height: 34px;
  font-size: 9px;
  letter-spacing: 0.045em;
}}

.eiq-race-form-guide--v4 .eiq-form-summary-table th button {{
  font-size: inherit;
}}

.eiq-race-form-guide--v4 .eiq-form-summary-table .eiq-form-silk {{
  width: 26px;
  height: 26px;
}}

.eiq-race-form-guide--v4 .eiq-form-last5-strip {{
  gap: 3px;
}}

.eiq-race-form-guide--v4 .eiq-form-last5-strip span {{
  min-width: 17px;
  height: 18px;
  border-radius: 4px;
  font-size: 10px;
}}

.eiq-race-form-guide--v4 .eiq-form-runner-expand {{
  min-width: 0;
}}

.eiq-race-form-guide--v4 .eiq-form-runner-anchor strong {{
  font-size: 11px;
  line-height: 1;
}}

.eiq-race-form-guide--v4 .eiq-form-expanded-row > td {{
  padding: 8px 10px 10px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-runner-sheet {{
  border-radius: 6px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-runner-header {{
  min-height: 76px;
  grid-template-columns: 54px minmax(210px, 0.9fr) minmax(0, 1.7fr);
  gap: 12px;
  padding: 10px 12px;
}}

.eiq-race-form-guide--v4 .eiq-form-detail-silk {{
  width: 42px;
  height: 42px;
}}

.eiq-race-form-guide--v4 .eiq-form-v3-runner-identity span {{
  font-size: 9px;
  letter-spacing: 0.1em;
}}

.eiq-race-form-guide--v4 .eiq-form-v3-runner-identity strong {{
  font-size: 22px;
  line-height: 1.05;
}}

.eiq-race-form-guide--v4 .eiq-form-v3-runner-identity strong em {{
  width: 31px;
  height: 31px;
  margin-right: 10px;
  font-size: 16px;
}}

.eiq-race-form-guide--v4 .eiq-form-v3-runner-identity p {{
  margin-top: 4px;
  font-size: 11px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-current-strip {{
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-current-strip div {{
  min-height: 56px;
  padding: 8px 9px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-current-strip dt {{
  font-size: 8px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-current-strip dd {{
  font-size: 16px;
  line-height: 1.05;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-dossier-grid {{
  grid-template-columns: minmax(0, 1.75fr) minmax(260px, 0.58fr);
  gap: 8px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-current-details {{
  grid-template-columns: repeat(8, minmax(0, 1fr));
}}

.eiq-race-form-guide--v4 .eiq-form-v4-current-details div {{
  min-height: 40px;
  padding: 7px 9px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-profile-block,
.eiq-race-form-guide--v4 .eiq-form-v4-today-match,
.eiq-race-form-guide--v4 .eiq-form-v4-key-insights,
.eiq-race-form-guide--v4 .eiq-form-v4-recent-form {{
  border-radius: 5px;
  padding: 9px 10px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-profile-tiles {{
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 6px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-profile-tiles article {{
  min-height: 44px;
  padding: 6px 7px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-profile-tiles span {{
  font-size: 8px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-profile-tiles strong {{
  margin-top: 3px;
  font-size: 12px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-profile-tiles small {{
  margin-top: 2px;
  font-size: 9px;
}}

.eiq-race-form-guide--v4 .eiq-form-v4-today-match li {{
  min-height: 30px;
  padding: 5px 0;
}}

.eiq-race-form-guide--v4 .eiq-form-v31-recent-form header {{
  min-height: 26px;
  margin-bottom: 5px;
}}

.eiq-race-form-guide--v4 .eiq-form-run-table--v4 table {{
  min-width: 0;
  width: 100%;
  table-layout: fixed;
}}

.eiq-race-form-guide--v4 .eiq-form-run-table--v4 th,
.eiq-race-form-guide--v4 .eiq-form-run-table--v4 td {{
  height: 23px;
  padding: 0 5px;
  font-size: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

.eiq-race-form-guide--v4 .eiq-form-run-table--v4 th {{
  font-size: 8px;
  letter-spacing: 0.04em;
}}
'''
    if MARKER in text:
        before = text[: text.index(MARKER)].rstrip()
        CSS.write_text(before + block, encoding="utf-8", newline="\n")
    else:
        CSS.write_text(text.rstrip() + block, encoding="utf-8", newline="\n")
    return True


def main() -> None:
    cp = checkpoint()
    patch_form_widths()
    patch_css()
    print(f"checkpoint={cp}")
    print("files_changed:")
    print(f"- {FORM}")
    print(f"- {CSS}")
    print("EDGEIQ_APPROVED_UI_PHASE06_FORM_GUIDE_PASS")


if __name__ == "__main__":
    main()
