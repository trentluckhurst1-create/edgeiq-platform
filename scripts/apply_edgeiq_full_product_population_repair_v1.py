
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "scripts" / "run_edgeiq_daily_product_refresh_v1.py"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
REPORT = ROOT / "docs" / "operations-readiness" / "data-population" / "edgeiq_full_product_population_repair_v1_report.txt"

TARGET_STAGES = [
    'scripts/build_edgeiq_three_day_window_v1.py',
    'scripts/build_edgeiq_vic_three_day_meeting_universe.py',
    'scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py',
    'scripts/build_edgeiq_racingcom_three_day_race_list_v1.py',
    'scripts/build_edgeiq_three_day_product_catalog_v1.py',
    'scripts/build_edgeiq_current_race_fields_from_product_catalog_v1.py',
    'scripts/build_edgeiq_form_guide_current_base_v1.py',
    'scripts/build_edgeiq_current_early_speed_v1.py',
    'scripts/build_edgeiq_current_late_speed_v1.py',
    'scripts/build_edgeiq_current_suitability_v1.py',
    'scripts/build_edgeiq_current_form_momentum_v1.py',
    'scripts/build_edgeiq_current_race_shape_v2.py',
    'scripts/build_edgeiq_current_map_v1.py',
    'scripts/build_edgeiq_form_guide_enriched_v2.py',
    'scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py',
    'scripts/build_edgeiq_map_terminal_feed_v1.py',
    'scripts/build_edgeiq_market_terminal_feed_v1.py',
    'scripts/build_edgeiq_overview_terminal_feed_v1.py',
    'scripts/build_edgeiq_insights_terminal_feed_v1.py',
    'scripts/build_edgeiq_gear_terminal_feed_v1.py',
    'scripts/build_edgeiq_meeting_results_terminal_feed_v1.py',
    'scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py',
    'scripts/build_edgeiq_on_track_weather_governed_v1_2.py',
    'scripts/build_edgeiq_victorian_track_weather_v1.py',
    'scripts/audit_edgeiq_victorian_track_weather_v1.py',
]

CSS_MARKER = "EDGEIQ FULL PRODUCT TYPOGRAPHY RECOVERY V1"
CSS_BLOCK = """

/* EDGEIQ FULL PRODUCT TYPOGRAPHY RECOVERY V1
   Keeps product workspaces readable at 100% browser zoom without changing intelligence calculations. */
.edgeiq-os,
.edgeiq-os * {
  text-rendering: optimizeLegibility;
}

.edgeiq-os {
  font-size: 14px;
  line-height: 1.45;
}

.edgeiq-os button,
.edgeiq-os input,
.edgeiq-os select,
.edgeiq-os textarea,
.edgeiq-os__workspace-item,
.edgeiq-os__workspace-title span,
.eiq-workspace__header span {
  font-size: 14px;
}

.edgeiq-os table,
.eiq-workspace table,
.edgeiq-data-table,
.edgeiq-product-table {
  font-size: 14px;
  line-height: 1.35;
}

.edgeiq-os th,
.edgeiq-os td,
.eiq-workspace th,
.eiq-workspace td {
  font-size: inherit;
  min-width: 64px;
  padding: 0.62rem 0.68rem;
  vertical-align: middle;
}

.edgeiq-os th,
.eiq-workspace th {
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
}

.edgeiq-os td,
.eiq-workspace td {
  font-size: 14px;
}

.edgeiq-os .metric-label,
.edgeiq-os .stat-label,
.edgeiq-os .status-label,
.edgeiq-os .eiq-label,
.eiq-workspace .metric-label,
.eiq-workspace .stat-label,
.eiq-workspace .status-label,
.eiq-workspace .eiq-label {
  font-size: 13px;
}

.edgeiq-os .metric-value,
.edgeiq-os .stat-value,
.edgeiq-os .eiq-value,
.eiq-workspace .metric-value,
.eiq-workspace .stat-value,
.eiq-workspace .eiq-value {
  font-size: 16px;
}

.edgeiq-os .runner-name,
.edgeiq-os .horse-name,
.eiq-workspace .runner-name,
.eiq-workspace .horse-name {
  font-size: 18px;
  line-height: 1.2;
}

.edgeiq-os .badge,
.edgeiq-os .status-chip,
.edgeiq-os .eiq-chip,
.eiq-workspace .badge,
.eiq-workspace .status-chip,
.eiq-workspace .eiq-chip {
  font-size: 12px;
  line-height: 1.25;
}

.edgeiq-os .table-scroll,
.eiq-workspace .table-scroll,
.edgeiq-os .edgeiq-table-scroll,
.eiq-workspace .edgeiq-table-scroll {
  overflow-x: auto;
}
"""


def checkpoint(path: Path) -> Path | None:
    if not path.exists():
        return None
    cp = path.with_name(path.stem + "_CHECKPOINT_PRE_FULL_PRODUCT_POPULATION_REPAIR_20260726" + path.suffix)
    if not cp.exists():
        shutil.copy2(path, cp)
    return cp


def patch_daily() -> bool:
    text = DAILY.read_text(encoding="utf-8")
    replacement = "CRITICAL=['edgeiq_three_day_window_v1.json', 'edgeiq_three_day_product_catalog_v1.json', 'edgeiq_vic_three_day_race_list_v1.csv', 'edgeiq_live_terminal_feed_v1.csv', 'edgeiq_vic_live_terminal_feed_v1.csv']; STAGES=" + repr(TARGET_STAGES)
    new_text, count = re.subn(r"CRITICAL=\[[^\n]+?\]; STAGES=\[[^\n]+?\]", replacement, text, count=1)
    if count != 1:
        raise RuntimeError("Could not locate compact CRITICAL/STAGES declaration")
    if new_text != text:
        checkpoint(DAILY)
        DAILY.write_text(new_text, encoding="utf-8")
        return True
    return False


def patch_css() -> bool:
    text = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    if CSS_MARKER in text:
        return False
    checkpoint(CSS)
    CSS.write_text(text.rstrip() + CSS_BLOCK + "\n", encoding="utf-8")
    return True


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    daily_changed = patch_daily()
    css_changed = patch_css()
    REPORT.write_text("\n".join([
        "EDGEIQ FULL PRODUCT POPULATION REPAIR V1",
        f"daily_refresh_order_changed={'YES' if daily_changed else 'NO'}",
        f"typography_recovery_changed={'YES' if css_changed else 'NO'}",
        "model_math_changed=NO",
        "pricing_math_changed=NO",
        "epi_math_changed=NO",
    ]) + "\n", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
