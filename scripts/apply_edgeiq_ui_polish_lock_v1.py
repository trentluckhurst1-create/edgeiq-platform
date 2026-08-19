from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def patch_text(path: str, replacements: list[tuple[str, str]]) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    original = text
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"Missing expected text in {path}: {old!r}")
        text = text.replace(old, new, 1)
    if text != original:
        target.write_text(text, encoding="utf-8")


def append_css_lock() -> None:
    target = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"
    text = target.read_text(encoding="utf-8")
    marker = "/* EDGEiQ UI Polish Lock V1"
    if marker in text:
        print("EDGEIQ_UI_POLISH_LOCK_V1_CSS_ALREADY_PRESENT")
        return

    css = r'''

/* EDGEiQ UI Polish Lock V1
   Permanent enterprise polish layer for completed workspaces only.
   UI refinement only: no data, model, routing, or calculation logic belongs here.
*/
:root {
  --eiq-lock-blue: #1f5fd6;
  --eiq-lock-blue-soft: #eef4ff;
  --eiq-lock-border: #dfe5ee;
  --eiq-lock-border-soft: #edf1f6;
  --eiq-lock-panel: #ffffff;
  --eiq-lock-panel-soft: #f8fafc;
  --eiq-lock-page: #f3f6fa;
  --eiq-lock-text: #151922;
  --eiq-lock-muted: #5f6b7a;
  --eiq-lock-faint: #8a94a3;
  --eiq-lock-green: #1f8f5f;
  --eiq-lock-amber: #a36a00;
  --eiq-lock-red: #b42318;
  --eiq-lock-shadow: 0 12px 32px rgba(18, 27, 45, 0.06);
  --eiq-lock-shadow-soft: 0 2px 8px rgba(18, 27, 45, 0.045);
}

.edgeiq-os {
  background: var(--eiq-lock-page);
  color: var(--eiq-lock-text);
  font-size: 15px;
  line-height: 1.42;
}

.edgeiq-os__primary-rail,
.edgeiq-os__workspace-rail,
.edgeiq-os__nav {
  background: #ffffff !important;
  color: var(--eiq-lock-text);
  border-color: var(--eiq-lock-border);
  box-shadow: 1px 0 0 rgba(18, 27, 45, 0.02);
}

.edgeiq-os__primary-item,
.edgeiq-os__workspace-item,
.edgeiq-os__rail-footer button {
  color: var(--eiq-lock-muted);
  font-size: 0.72rem;
}

.edgeiq-os__primary-item.is-active,
.edgeiq-os__primary-item:hover,
.edgeiq-os__workspace-item.is-active,
.edgeiq-os__workspace-item:hover {
  background: var(--eiq-lock-blue-soft);
  color: var(--eiq-lock-blue);
  border-left-color: var(--eiq-lock-blue);
}

.edgeiq-os__brand-mark {
  background: #ffffff;
  border-color: var(--eiq-lock-border);
  color: var(--eiq-lock-blue);
}

.edgeiq-os__main {
  padding: 1.45rem 3.1vw 4.25rem;
}

.edgeiq-os__status {
  color: var(--eiq-lock-text);
  border-bottom-color: var(--eiq-lock-border);
  margin-bottom: 2.2rem;
}

.edgeiq-os__status span,
.edgeiq-os__workspace-title span,
.edgeiq-os__brand-sub {
  color: var(--eiq-lock-faint);
}

.edgeiq-os__status strong,
.edgeiq-os__workspace-title strong,
.edgeiq-os__brand-name {
  color: var(--eiq-lock-text);
}

.eiq-meetings-workspace,
.eiq-form-guide-v3,
.eiq-map-v1,
.eiq-market-v1,
.eiq-epi-v1,
.eiq-overview-v1,
.eiq-insights-v1,
.eiq-results-v1 {
  gap: 18px;
  color: var(--eiq-lock-text);
  font-size: 15px;
}

.eiq-workspace-panel,
.eiq-meetings-engineering__header,
.eiq-meetings-engineering__summary > div,
.eiq-meetings-engineering__table-panel,
.eiq-meetings-engineering__selected,
.eiq-meetings-engineering__race-card,
.eiq-form-race-header,
.eiq-form-summary-table,
.eiq-form-v31-runner-sheet,
.eiq-form-v31-profile-card,
.eiq-form-v31-recent-form,
.eiq-map-v1-hero,
.eiq-map-v1-panel,
.eiq-market-v1-hero,
.eiq-market-v1-panel,
.eiq-overview-v1-hero,
.eiq-overview-v1-panel,
.eiq-overview-v1-card,
.eiq-insights-v1-hero,
.eiq-insights-v1-panel,
.eiq-insights-v1-card,
.eiq-epi-v1-hero,
.eiq-epi-v1-summary,
.eiq-epi-v1-panel,
.eiq-results-v1-header,
.eiq-results-v1-panel,
.eiq-results-v1-summary-strip,
.eiq-results-v1-snapshot,
.eiq-results-v1-data-status,
.eiq-results-v1-empty {
  border-color: var(--eiq-lock-border);
  border-radius: 16px;
  background: var(--eiq-lock-panel);
  box-shadow: var(--eiq-lock-shadow-soft);
}

.eiq-meetings-engineering__header,
.eiq-map-v1-hero,
.eiq-market-v1-hero,
.eiq-overview-v1-hero,
.eiq-insights-v1-hero,
.eiq-epi-v1-hero,
.eiq-results-v1-header {
  padding: 20px 22px;
}

.eiq-meetings-engineering__header h2,
.eiq-map-v1-hero h3,
.eiq-market-v1-hero h3,
.eiq-overview-v1-hero h3,
.eiq-insights-v1-hero h3,
.eiq-epi-v1-hero h3,
.eiq-results-v1-header h2 {
  color: var(--eiq-lock-text);
  font-size: clamp(24px, 2.2vw, 31px);
  font-weight: 780;
  letter-spacing: -0.025em;
  line-height: 1.12;
}

.eiq-meetings-engineering__header span,
.eiq-meetings-engineering__table-panel header span,
.eiq-map-v1-hero p,
.eiq-map-v1-panel__title span,
.eiq-market-v1-hero p,
.eiq-market-v1-panel__title span,
.eiq-overview-v1-hero p,
.eiq-overview-v1-panel__title span,
.eiq-overview-v1-card__head span,
.eiq-insights-v1-hero p,
.eiq-insights-v1-panel__title span,
.eiq-insights-v1-card span,
.eiq-epi-v1-hero p,
.eiq-epi-v1-summary span,
.eiq-epi-v1-panel__title span,
.eiq-results-v1-header span,
.eiq-results-v1-panel header span {
  color: var(--eiq-lock-blue);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.eiq-meetings-engineering__header p,
.eiq-map-v1-hero span,
.eiq-market-v1-hero span,
.eiq-overview-v1-hero span,
.eiq-insights-v1-hero span,
.eiq-epi-v1-hero span,
.eiq-results-v1-header p,
.eiq-overview-v1-copy,
.eiq-insights-v1-copy,
.eiq-market-v1-copy,
.eiq-map-v1-copy,
.eiq-epi-v1-copy {
  color: var(--eiq-lock-muted);
  font-size: 14px;
  line-height: 1.52;
}

.eiq-meetings-engineering__days {
  gap: 8px;
  padding: 4px;
  border: 1px solid var(--eiq-lock-border);
  border-radius: 16px;
  background: #ffffff;
  width: fit-content;
  box-shadow: var(--eiq-lock-shadow-soft);
}

.eiq-meetings-engineering__days button {
  border-radius: 12px;
  min-height: 48px;
  padding: 8px 18px;
  border: 1px solid transparent;
  background: transparent;
}

.eiq-meetings-engineering__days button.is-active {
  border-color: #b9cdf7;
  background: var(--eiq-lock-blue-soft);
  color: var(--eiq-lock-blue);
}

.eiq-meetings-engineering__summary > div {
  min-height: 104px;
  padding: 18px;
}

.eiq-meetings-engineering__summary span,
.eiq-meetings-engineering__header dt,
.eiq-meetings-engineering__selected dt,
.eiq-form-summary-table th,
.eiq-form-v31-table th,
.eiq-map-v1-table th,
.eiq-market-v1-table th,
.eiq-overview-v1-table th,
.eiq-insights-v1-table th,
.eiq-epi-v1-table th,
.eiq-results-v1-table th {
  color: var(--eiq-lock-faint);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.eiq-meetings-engineering__summary strong,
.eiq-meetings-engineering__header dd,
.eiq-meetings-engineering__selected dd,
.eiq-map-v1-hero dd,
.eiq-market-v1-hero dd,
.eiq-overview-v1-hero dd,
.eiq-insights-v1-hero dd,
.eiq-epi-v1-hero dd,
.eiq-epi-v1-summary dd,
.eiq-results-v1-summary-strip strong,
.eiq-results-v1-snapshot strong {
  color: var(--eiq-lock-text);
  font-size: 17px;
  font-weight: 820;
}

.eiq-meetings-engineering__table th,
.eiq-meetings-engineering__table td,
.eiq-form-summary-table th,
.eiq-form-summary-table td,
.eiq-form-v31-table th,
.eiq-form-v31-table td,
.eiq-map-v1-table th,
.eiq-map-v1-table td,
.eiq-market-v1-table th,
.eiq-market-v1-table td,
.eiq-overview-v1-table th,
.eiq-overview-v1-table td,
.eiq-insights-v1-table th,
.eiq-insights-v1-table td,
.eiq-epi-v1-table th,
.eiq-epi-v1-table td,
.eiq-results-v1-table th,
.eiq-results-v1-table td {
  font-size: 14px;
  border-bottom-color: var(--eiq-lock-border-soft);
}

.eiq-meetings-engineering__table td,
.eiq-form-summary-table td,
.eiq-form-v31-table td,
.eiq-map-v1-table td,
.eiq-market-v1-table td,
.eiq-overview-v1-table td,
.eiq-insights-v1-table td,
.eiq-epi-v1-table td,
.eiq-results-v1-table td {
  min-height: 42px;
  padding-top: 10px;
  padding-bottom: 10px;
}

.eiq-meetings-engineering__table tbody tr:hover,
.eiq-form-summary-table tbody tr:hover,
.eiq-form-v31-table tbody tr:hover,
.eiq-map-v1-table tbody tr:hover,
.eiq-market-v1-table tbody tr:hover,
.eiq-overview-v1-table tbody tr:hover,
.eiq-insights-v1-table tbody tr:hover,
.eiq-epi-v1-table tbody tr:hover,
.eiq-results-v1-table tbody tr:hover {
  background: #f6f9ff;
}

.eiq-meetings-engineering__table tbody tr.is-selected,
.eiq-meetings-engineering__table tbody tr:has(button[aria-pressed="true"]) {
  background: #edf4ff;
}

.eiq-meetings-engineering__race-card {
  padding: 18px;
}

.eiq-meetings-engineering__race-card > strong,
.eiq-form-v31-runner-name,
.eiq-form-v31-profile-card strong,
.eiq-map-v1-runner-line__label em,
.eiq-market-v1-table td strong,
.eiq-overview-v1-card__head b,
.eiq-insights-v1-card strong,
.eiq-epi-v1-horse-button {
  color: var(--eiq-lock-text);
  font-weight: 820;
}

.eiq-map-v1-panel,
.eiq-market-v1-panel,
.eiq-overview-v1-panel,
.eiq-insights-v1-panel,
.eiq-epi-v1-panel,
.eiq-results-v1-panel {
  padding: 16px;
}

.eiq-map-v1-panel__title,
.eiq-market-v1-panel__title,
.eiq-overview-v1-panel__title,
.eiq-insights-v1-panel__title,
.eiq-epi-v1-panel__title {
  padding: 0 0 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--eiq-lock-border-soft);
}

.eiq-map-v1-visual {
  min-height: 440px;
  border-radius: 14px;
  border-color: var(--eiq-lock-border);
}

.eiq-map-v1-runner-line__label {
  padding: 6px 11px 6px 7px;
  border-radius: 999px;
}

.eiq-map-v1-runner-line__label strong {
  background: #eef4ff;
  color: var(--eiq-lock-blue);
  border: 1px solid #c9d7f5;
}

.eiq-epi-v1-table th:first-child,
.eiq-epi-v1-table td:first-child,
.eiq-map-v1-table th:first-child,
.eiq-map-v1-table td:first-child {
  min-width: 54px;
}

.eiq-epi-v1-tile {
  width: 58px;
  min-height: 32px;
  border-radius: 8px;
  font-size: 14px;
}

.eiq-epi-v1-legend {
  gap: 18px;
  padding: 14px 16px 16px;
  font-size: 13px;
}

.eiq-epi-v1-legend i {
  width: 14px;
  height: 14px;
}

.eiq-overview-v1-cards {
  gap: 16px;
}

.eiq-overview-v1-card,
.eiq-insights-v1-card {
  min-height: 136px;
  padding: 18px;
}

.eiq-insights-v1-cards {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 16px;
}

.eiq-market-v1-grid,
.eiq-map-v1-grid,
.eiq-overview-v1-grid,
.eiq-insights-v1-grid,
.eiq-epi-v1-grid {
  gap: 18px;
}

.eiq-form-summary-table img,
.eiq-form-v31-runner-sheet img,
.eiq-form-v31-table img,
.eiq-epi-v1-table img,
.eiq-map-v1-table img {
  border-radius: 0 !important;
  background: transparent !important;
}

.eiq-market-v1 .is-positive,
.eiq-overview-v1 .is-available,
.eiq-insights-v1 .is-current,
.eiq-epi-v1 .is-positive,
.eiq-results-v1-sectional.is-negative {
  color: var(--eiq-lock-green) !important;
}

.eiq-market-v1 .is-negative,
.eiq-epi-v1 .is-negative,
.eiq-results-v1-sectional.is-positive {
  color: var(--eiq-lock-red) !important;
}

.eiq-overview-v1 .is-partial,
.eiq-epi-v1 .is-pending {
  color: var(--eiq-lock-amber) !important;
}

@media (max-width: 1180px) {
  .edgeiq-os__main {
    padding-inline: 1.25rem;
  }

  .eiq-meetings-engineering__days {
    width: 100%;
  }
}
'''
    target.write_text(text.rstrip() + css + "\n", encoding="utf-8")


def main() -> None:
    patch_text(
        "src/edgeiq-os/race/components/MeetingsWorkspace.tsx",
        [
            ("<span>MEETINGS</span>\n          <h2>Meetings</h2>", "<span>MEETINGS</span>\n          <h2>Meeting Centre</h2>"),
        ],
    )
    patch_text(
        "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx",
        [
            ("<span><i className=\"is-positive\" /> Above historical race context</span>", "<span><i className=\"is-positive\" /> Exceptional</span>"),
            ("<span><i className=\"is-neutral\" /> In line with historical race context</span>", "<span><i className=\"is-neutral\" /> Above Benchmark</span>"),
            ("<span><i className=\"is-negative\" /> Below historical race context</span>", "<span><i className=\"is-negative\" /> Around Benchmark</span>"),
            ("<span><i className=\"is-missing\" /> Missing start evidence</span>", "<span><i className=\"is-missing\" /> Insufficient Evidence</span>"),
        ],
    )
    patch_text(
        "src/edgeiq-os/race/components/OverviewWorkspace.tsx",
        [
            ("<p>OVERVIEW</p>\n          <h3>{raceLabel || \"Race overview\"}</h3>\n          <span>Supported race evidence across environment, map, field intelligence and operational state.</span>", "<p>OVERVIEW</p>\n          <h3>{raceLabel || \"Mission Control\"}</h3>\n          <span>What to know before analysing this race: environment, map, field intelligence and data readiness.</span>"),
            ("<span>Overview Evidence Table</span>", "<span>Mission Control Evidence</span>"),
        ],
    )
    patch_text(
        "src/edgeiq-os/race/components/InsightsWorkspace.tsx",
        [
            ("<h3>{raceLabel || \"Race insights\"}</h3>\n          <span>Governed insight summary with source, timestamp, coverage and evidence-quality confidence.</span>", "<h3>{raceLabel || \"Racing Intelligence\"}</h3>\n          <span>Governed analyst intelligence across angles, patterns, pressure points, watch factors and evidence confidence.</span>"),
            ("<div className=\"eiq-insights-v1-panel__title\"><span>Insight Summary</span></div>", "<div className=\"eiq-insights-v1-panel__title\"><span>Key Insights</span></div>"),
          ],
    )
    append_css_lock()
    print("EDGEIQ_UI_POLISH_LOCK_V1_APPLIED")


if __name__ == "__main__":
    main()
