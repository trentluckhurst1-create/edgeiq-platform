from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
OUT = ROOT / "public" / "data" / "edgeiq_tab_layout_copy_audit_v1.csv"


def write(rows: list[dict[str, Any]]) -> None:
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    tsx = TSX.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    rows: list[dict[str, Any]] = []

    def add(check: str, passed: bool, detail: str) -> None:
        rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})

    add(
        "no_centred_race_field_large_heading",
        '<div className="edgeiq-tab-heading"><span>FIELD</span><strong>Race Field</strong>' not in tsx,
        "FIELD uses compact header instead of large tab heading",
    )
    add(
        "legacy_market_title_absent",
        "EDGEiQ and market price comparison" not in tsx,
        "old market title removed",
    )
    add(
        "race_list_zero_field_size_hidden",
        "<span>{race.fieldSize}</span>" not in tsx and "raceFieldCountLabel(race.fieldSize)" in tsx,
        "race-list field size uses Fields pending fallback",
    )
    add(
        "performance_heatmap_classes_present",
        all(token in tsx + css for token in ["edgeiq-performance-heatmap-row", "heat-elite", "heat-positive", "heat-neutral", "heat-risk"]),
        "Performance tab has heatmap row and cell intensity classes",
    )
    add(
        "performance_heatmap_columns_present",
        all(label in tsx for label in ["Performance Index", "Gap", "Distance", "Condition", "Class", "Pace", "Profile", "Confidence"]),
        "Performance heatmap columns present",
    )
    add(
        "field_quick_profile_present",
        "edgeiq-field-quick-profile" in tsx and "aria-expanded={isOpen}" in tsx,
        "Field row click expands compact quick profile",
    )
    add(
        "map_speed_visual_retained",
        "Speed Map Visual" in tsx and "mapLaneRowsV1.map" in tsx,
        "Map visual lane renderer retained",
    )
    add(
        "map_clutter_heading_removed",
        "Lane-based speed map with barrier context" not in tsx and "edgeiq-map-summary-strip" in tsx,
        "Map redundant title removed and slim summary strip present",
    )
    add(
        "form_clean_header_present",
        "edgeiq-form-clean-header" in tsx and "edgeiq-form-clean-summary" in tsx,
        "Form tab uses cleaner hierarchy",
    )

    write(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"EDGEiQ tab layout/copy audit: {len(rows) - len(failures)}/{len(rows)} PASS")
    if failures:
        for row in failures:
            print(f"FAIL {row['check']}: {row['detail']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
