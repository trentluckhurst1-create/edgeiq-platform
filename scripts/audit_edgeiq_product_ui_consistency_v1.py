from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
OUT = ROOT / "public" / "data" / "edgeiq_product_ui_consistency_audit_v1.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_product_ui_consistency_summary_v1.csv"


def row(check: str, status: str, detail: str) -> dict[str, str]:
    return {"check": check, "status": status, "detail": detail}


def count(pattern: str, text: str, flags: int = re.IGNORECASE) -> int:
    return len(re.findall(pattern, text, flags))


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    css_tail = css[-18000:]

    rows: list[dict[str, str]] = []
    required_tokens = [
        "--edgeiq-home-bg",
        "--edgeiq-home-panel",
        "--edgeiq-home-accent",
        "--edgeiq-home-text",
        "--edgeiq-home-border",
        "--edgeiq-home-hover",
        "EDGEiQ PRODUCT-WIDE DESIGN UNIFICATION PASS",
    ]
    missing_tokens = [token for token in required_tokens if token not in css]
    rows.append(row(
        "home_v4_design_tokens_present",
        "PASS" if not missing_tokens else "FAIL",
        "missing=" + "|".join(missing_tokens) if missing_tokens else "final design tokens present",
    ))

    tab_classes = [
        "edgeiq-race-pro-v1",
        "edgeiq-field-guide-v3",
        "edgeiq-performance-heatmap-v2",
        "edgeiq-form-study-v2",
        "edgeiq-race-map",
        "edgeiq-nexus-v21",
        "edgeiq-market-tab",
        "edgeiq-results-tab",
        "edgeiq-meeting-card-v2",
    ]
    missing_tab_refs = [klass for klass in tab_classes if klass not in css_tail]
    rows.append(row(
        "tab_surfaces_covered_by_final_layer",
        "PASS" if not missing_tab_refs else "WARN",
        "missing_tail_refs=" + "|".join(missing_tab_refs) if missing_tab_refs else "all active tab surfaces covered by final layer",
    ))

    table_refs = [
        "edgeiq-field-guide-table",
        "edgeiq-performance-heatmap-table",
        "edgeiq-form-table",
        "edgeiq-market-table",
        "edgeiq-career-history-table",
    ]
    missing_tables = [klass for klass in table_refs if klass not in css_tail]
    rows.append(row(
        "table_system_covered",
        "PASS" if not missing_tables else "FAIL",
        "missing=" + "|".join(missing_tables) if missing_tables else "shared table styling covered",
    ))

    monochrome_tokens = [
        ".epi-heat-cell",
        ".epi-heat-elite",
        ".heat-elite",
        ".edgeiq-market-row .positive",
        ".edgeiq-market-row .negative",
    ]
    missing_mono = [token for token in monochrome_tokens if token not in css_tail]
    rows.append(row(
        "heatmap_colour_neutralisation_present",
        "PASS" if not missing_mono else "FAIL",
        "missing=" + "|".join(missing_mono) if missing_mono else "heatmap/positive/negative styles neutralised in final layer",
    ))

    pill_chip_count = count(r"pill|chip|badge", css)
    rows.append(row(
        "legacy_pill_chip_selectors_reported",
        "WARN" if pill_chip_count else "PASS",
        f"legacy_token_count={pill_chip_count}; final layer restyles visible surfaces without pill treatment",
    ))

    old_colour_count = sum(count(re.escape(token), css, 0) for token in ["#34d399", "#f87171", "#9d7cff", "#f5c451", "#3191ff"])
    rows.append(row(
        "legacy_colour_tokens_reported",
        "WARN" if old_colour_count else "PASS",
        f"legacy_colour_token_count={old_colour_count}; final layer uses #43efc6 and HOME palette",
    ))

    radius_legacy_count = count(r"border-radius:\s*(1[6-9]|2\d)px", css)
    rows.append(row(
        "legacy_large_radius_reported",
        "WARN" if radius_legacy_count else "PASS",
        f"legacy_large_radius_count={radius_legacy_count}; final layer normalises active panels to 10-12px",
    ))

    css_icon_checks = [
        "edgeiq-home-v4-access-icon-map::before",
        "edgeiq-home-v4-access-icon-map::after",
        "edgeiq-home-v4-access-icon-nexus::before",
        "edgeiq-home-v4-access-icon-track::before",
    ]
    missing_icons = [token for token in css_icon_checks if token not in css]
    rows.append(row(
        "css_drawn_home_icons_present",
        "PASS" if not missing_icons else "FAIL",
        "missing=" + "|".join(missing_icons) if missing_icons else "map, nexus and track icons are CSS drawn",
    ))

    thumb_script = ROOT / "scripts" / "build_edgeiq_track_thumbnails_v3.py"
    rows.append(row(
        "track_thumbnail_builder_present",
        "PASS" if thumb_script.exists() else "FAIL",
        thumb_script.name,
    ))

    banned_visible = [
        ("home_not_tips_removed", "NOT TIPS" not in src and "Real time edge" not in src),
        ("race_no_selection_copy", "No selections" not in src),
    ]
    for check, ok in banned_visible:
        rows.append(row(check, "PASS" if ok else "FAIL", "visible copy checked"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    pass_count = sum(1 for item in rows if item["status"] == "PASS")
    warn_count = sum(1 for item in rows if item["status"] == "WARN")
    fail_count = sum(1 for item in rows if item["status"] == "FAIL")
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows([
            {"metric": "status", "value": "FAIL" if fail_count else "PASS_WITH_WARNINGS" if warn_count else "PASS"},
            {"metric": "pass_count", "value": pass_count},
            {"metric": "warn_count", "value": warn_count},
            {"metric": "fail_count", "value": fail_count},
            {"metric": "audit_rows", "value": len(rows)},
        ])

    print(f"Product UI consistency audit: PASS={pass_count} WARN={warn_count} FAIL={fail_count}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
