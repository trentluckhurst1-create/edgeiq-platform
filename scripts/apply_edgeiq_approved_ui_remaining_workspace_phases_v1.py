from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
CHECKPOINT = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "approved-ui"
    / "edgeiqApprovedUiRebuildV1_CHECKPOINT_PRE_REMAINING_PHASES_20260719.css"
)
REPORT = (
    ROOT
    / "docs"
    / "full-product-implementation"
    / "screenshots"
    / "approved-ui-rebuild"
    / "EDGEIQ_APPROVED_UI_REMAINING_PHASES_V1_REPORT.txt"
)

WRAPPERS = {
    "scripts/apply_edgeiq_approved_ui_phase09_epi_v1.py": "phase09 EPI",
    "scripts/apply_edgeiq_approved_ui_phase10_market_v1.py": "phase10 MARKET",
    "scripts/apply_edgeiq_approved_ui_phase11_overview_v1.py": "phase11 OVERVIEW",
    "scripts/apply_edgeiq_approved_ui_phase12_scratchings_v1.py": "phase12 SCRATCHINGS",
    "scripts/apply_edgeiq_approved_ui_phase13_gear_changes_v1.py": "phase13 GEAR CHANGES",
    "scripts/apply_edgeiq_approved_ui_phase14_track_v1.py": "phase14 TRACK",
    "scripts/apply_edgeiq_approved_ui_phase15_weather_v1.py": "phase15 WEATHER",
    "scripts/apply_edgeiq_approved_ui_phase16_results_v1.py": "phase16 RESULTS",
    "scripts/apply_edgeiq_approved_ui_phase17_insights_v1.py": "phase17 INSIGHTS",
    "scripts/apply_edgeiq_approved_ui_phase18_lab_v1.py": "phase18 LAB",
    "scripts/apply_edgeiq_approved_ui_phase19_compare_v1.py": "phase19 COMPARE",
    "scripts/apply_edgeiq_approved_ui_phase20_review_v1.py": "phase20 REVIEW",
    "scripts/apply_edgeiq_approved_ui_phase21_settings_shell_conformance_v1.py": "phase21 SETTINGS",
}

CSS_MARKER = "/* EDGEIQ APPROVED UI PHASE 09-21 REMAINING WORKSPACES */"

CSS_BLOCK = r"""
/* EDGEIQ APPROVED UI PHASE 09-21 REMAINING WORKSPACES */
.eiq-field-workspace-v1,
.eiq-epi-v1,
.eiq-market-v1,
.eiq-overview-v3,
.eiq-meeting-v1,
.eiq-global-results-v1,
.eiq-insights-v1,
.eiq-lab-v1,
.eiq-review-v1,
.eiq-settings-v1 {
  color: var(--eiq-approved-text);
}

.eiq-field-workspace-v1 .eiq-workspace-panel__title,
.eiq-epi-v1-hero,
.eiq-market-v1-hero,
.eiq-meeting-v1-hero,
.eiq-global-results-v1-hero,
.eiq-insights-v1-hero,
.eiq-lab-v1-hero,
.eiq-review-v1-hero,
.eiq-settings-v1-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 16px;
  margin: 0 0 12px;
  padding: 12px 14px;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 4px;
  background: linear-gradient(180deg, #ffffff 0%, #f7f9fc 100%);
}

.eiq-field-workspace-v1 .eiq-workspace-panel__title span,
.eiq-epi-v1-hero p,
.eiq-market-v1-hero p,
.eiq-meeting-v1-hero span,
.eiq-global-results-v1-hero span,
.eiq-insights-v1-hero span,
.eiq-lab-v1-hero span,
.eiq-review-v1-hero span,
.eiq-settings-v1-hero span {
  display: block;
  margin: 0 0 3px;
  color: var(--eiq-approved-muted);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eiq-field-workspace-v1 .eiq-workspace-panel__title strong,
.eiq-epi-v1-hero h3,
.eiq-market-v1-hero h3,
.eiq-meeting-v1-hero h2,
.eiq-global-results-v1-hero h2,
.eiq-insights-v1-hero h2,
.eiq-lab-v1-hero h2,
.eiq-review-v1-hero h2,
.eiq-settings-v1-hero h2 {
  margin: 0;
  color: var(--eiq-approved-navy);
  font-size: 18px;
  font-weight: 900;
  line-height: 1.05;
  letter-spacing: -0.01em;
}

.eiq-field-workspace-v1 .eiq-workspace-panel__title p,
.eiq-epi-v1-hero span,
.eiq-market-v1-hero span,
.eiq-meeting-v1-hero p,
.eiq-global-results-v1-hero p,
.eiq-insights-v1-hero p,
.eiq-lab-v1-hero p,
.eiq-review-v1-hero p,
.eiq-settings-v1-hero p {
  margin: 4px 0 0;
  color: var(--eiq-approved-muted);
  font-size: 11px;
  line-height: 1.35;
}

.eiq-epi-v1-hero dl,
.eiq-market-v1-hero dl {
  display: grid;
  grid-auto-flow: column;
  gap: 8px;
  margin: 0;
}

.eiq-epi-v1-hero dl div,
.eiq-market-v1-hero dl div,
.eiq-meeting-v1-detail-grid div,
.eiq-meeting-v1-summary-strip div,
.eiq-meeting-v1-condition-strip div,
.eiq-market-v1-facts div,
.eiq-epi-v1-facts div,
.eiq-overview-v3-card {
  min-width: 82px;
  padding: 8px 10px;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 4px;
  background: #fff;
}

.eiq-epi-v1-hero dt,
.eiq-market-v1-hero dt,
.eiq-meeting-v1-detail-grid dt,
.eiq-meeting-v1-summary-strip span,
.eiq-meeting-v1-condition-strip span,
.eiq-market-v1-facts dt,
.eiq-epi-v1-facts dt,
.eiq-overview-v3-card span {
  display: block;
  color: var(--eiq-approved-muted);
  font-size: 8.5px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.eiq-epi-v1-hero dd,
.eiq-market-v1-hero dd,
.eiq-meeting-v1-detail-grid dd,
.eiq-meeting-v1-summary-strip strong,
.eiq-meeting-v1-condition-strip strong,
.eiq-market-v1-facts dd,
.eiq-epi-v1-facts dd,
.eiq-overview-v3-card strong {
  margin: 3px 0 0;
  color: var(--eiq-approved-navy);
  font-size: 12px;
  font-weight: 900;
}

.eiq-field-table-v1,
.eiq-epi-v1-table,
.eiq-market-v1-table,
.eiq-meeting-v1-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: #fff;
}

.eiq-field-table-v1 th,
.eiq-field-table-v1 td,
.eiq-epi-v1-table th,
.eiq-epi-v1-table td,
.eiq-market-v1-table th,
.eiq-market-v1-table td,
.eiq-meeting-v1-table th,
.eiq-meeting-v1-table td {
  height: 26px;
  padding: 0 7px;
  border-bottom: 1px solid var(--eiq-approved-line);
  color: var(--eiq-approved-text);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eiq-field-table-v1 th,
.eiq-epi-v1-table th,
.eiq-market-v1-table th,
.eiq-meeting-v1-table th {
  height: 30px;
  color: var(--eiq-approved-muted);
  font-size: 8.5px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: #f8fafc;
}

.eiq-field-table-v1 .is-left,
.eiq-epi-v1-table .is-left,
.eiq-market-v1-table .is-left,
.eiq-meeting-v1-table .is-left {
  text-align: left;
}

.eiq-field-runner-button,
.eiq-epi-v1-horse-button,
.eiq-meetings-approved__meeting,
.eiq-meetings-approved__select {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--eiq-approved-navy);
  font: inherit;
  font-weight: 900;
  text-align: left;
  cursor: pointer;
}

.eiq-field-expanded-row td {
  padding: 0;
  background: #f8fafc;
}

.eiq-field-recent-panel,
.eiq-epi-v1-panel,
.eiq-market-v1-panel,
.eiq-meeting-v1-panel,
.eiq-overview-v3-card,
.eiq-meeting-v1-pending {
  border: 1px solid var(--eiq-approved-line);
  border-radius: 4px;
  background: #fff;
}

.eiq-field-recent-panel {
  display: grid;
  gap: 8px;
  padding: 10px;
}

.eiq-field-recent-panel > div,
.eiq-epi-v1-panel__title,
.eiq-market-v1-panel__title,
.eiq-meeting-v1-panel > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 30px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--eiq-approved-line);
}

.eiq-field-recent-panel span,
.eiq-epi-v1-panel__title span,
.eiq-market-v1-panel__title span,
.eiq-meeting-v1-panel header span {
  color: var(--eiq-approved-muted);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.eiq-epi-v1-grid,
.eiq-market-v1-grid,
.eiq-meeting-v1-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 250px;
  gap: 12px;
  align-items: start;
}

.eiq-market-v1-table-panel,
.eiq-epi-v1-table-panel {
  min-width: 0;
}

.eiq-epi-v1-summary,
.eiq-overview-v3-summary,
.eiq-meeting-v1-summary-strip,
.eiq-meeting-v1-condition-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 10px;
}

.eiq-epi-v1-tile {
  display: inline-block;
  width: 17px;
  height: 17px;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 3px;
  background: #f3f5f8;
}

.eiq-epi-v1-tile.is-elite,
.eiq-epi-v1-tile.is-positive,
.is-positive {
  color: #166534;
  background: rgba(34, 197, 94, 0.12);
}

.eiq-epi-v1-tile.is-risk,
.is-negative,
.is-risk {
  color: #991b1b;
  background: rgba(239, 68, 68, 0.1);
}

.eiq-epi-v1-tile.is-neutral,
.is-neutral,
.is-partial,
.is-pending {
  color: var(--eiq-approved-text);
  background: #f8fafc;
}

.eiq-context-tabs,
.eiq-meeting-v1-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0 0 10px;
  padding: 4px;
  border: 1px solid var(--eiq-approved-line);
  background: #fff;
}

.eiq-context-tabs button,
.eiq-meeting-v1-tabs button {
  height: 26px;
  border: 0;
  border-radius: 3px;
  padding: 0 10px;
  color: var(--eiq-approved-muted);
  background: transparent;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-context-tabs button.is-active,
.eiq-meeting-v1-tabs button.is-active {
  color: #fff;
  background: var(--eiq-approved-navy);
}

.eiq-global-results-v1,
.eiq-insights-v1,
.eiq-lab-v1,
.eiq-review-v1,
.eiq-settings-v1,
.eiq-overview-v3,
.eiq-market-v1,
.eiq-epi-v1 {
  display: grid;
  gap: 12px;
}

.eiq-market-v1-empty,
.eiq-epi-v1-empty,
.eiq-meeting-v1-pending {
  min-height: 140px;
  display: grid;
  place-items: center;
  padding: 18px;
  color: var(--eiq-approved-muted);
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 1100px) {
  .eiq-epi-v1-grid,
  .eiq-market-v1-grid,
  .eiq-meeting-v1-layout,
  .eiq-field-workspace-v1 .eiq-workspace-panel__title,
  .eiq-epi-v1-hero,
  .eiq-market-v1-hero,
  .eiq-meeting-v1-hero {
    grid-template-columns: 1fr;
  }

  .eiq-epi-v1-summary,
  .eiq-overview-v3-summary,
  .eiq-meeting-v1-summary-strip,
  .eiq-meeting-v1-condition-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
"""


def write_wrappers() -> list[str]:
    written: list[str] = []
    for rel, label in WRAPPERS.items():
        path = ROOT / rel
        if path.exists():
            continue
        path.write_text(
            "from apply_edgeiq_approved_ui_remaining_workspace_phases_v1 import main\n\n"
            "if __name__ == \"__main__\":\n"
            f"    print(\"EDGEIQ_APPROVED_UI_{label.upper().replace(' ', '_')}_APPLY\")\n"
            "    main()\n",
            encoding="utf-8",
        )
        written.append(rel)
    return written


def main() -> None:
    if not CSS_PATH.exists():
        raise SystemExit(f"Missing CSS file: {CSS_PATH}")

    if not CHECKPOINT.exists():
        CHECKPOINT.write_text(CSS_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    css = CSS_PATH.read_text(encoding="utf-8")
    css_changed = False
    if CSS_MARKER not in css:
        CSS_PATH.write_text(css.rstrip() + "\n\n" + CSS_BLOCK.strip() + "\n", encoding="utf-8")
        css_changed = True

    wrappers = write_wrappers()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "\n".join(
            [
                "EDGEIQ_APPROVED_UI_REMAINING_PHASES_V1",
                f"built_at={datetime.now().astimezone().isoformat(timespec='seconds')}",
                f"css_changed={css_changed}",
                f"checkpoint={CHECKPOINT.relative_to(ROOT)}",
                f"wrappers_created={len(wrappers)}",
                "data_pipeline_changed=NO",
                "pricing_changed=NO",
                "ratings_changed=NO",
                "v6_1_changed=NO",
                "v7_2g2_changed=NO",
                *wrappers,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
