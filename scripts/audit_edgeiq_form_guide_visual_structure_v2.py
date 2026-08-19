from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TXT = ROOT / "public/data/edgeiq_form_guide_visual_structure_v2_audit.txt"
OUT_JSON = ROOT / "public/data/edgeiq_form_guide_visual_structure_v2_audit.json"

COMPONENT = ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
CSS = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"


def main() -> int:
    component = COMPONENT.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    recent_position = component.find("<RecentForm")
    insights_position = component.find("<KeyInsights")

    checks = [
        {
            "name": "form_guide_engineering_css_layer_present",
            "pass": "EDGEIQ FORM GUIDE ENGINEERING BUILD V1" in css,
        },
        {
            "name": "recent_form_before_insights",
            "pass": recent_position >= 0 and insights_position > recent_position,
        },
        {
            "name": "latest_run_panel_not_rendered",
            "pass": "<LatestRun" not in component and "function LatestRun" not in component,
        },
        {
            "name": "insights_full_width_grid",
            "pass": "eiq-form-v31-insight-grid" in component and ".eiq-product-shell-v4 .eiq-form-v31-insight-grid" in css,
        },
        {
            "name": "current_match_blue_treatment",
            "pass": "is-current-match" in component and "#eaf2ff" in css and "#123d79" in css and "box-shadow: none" in css,
        },
        {
            "name": "no_visible_vertical_table_dividers",
            "pass": "border-left: 0 !important" in css and "border-right: 0 !important" in css,
        },
        {
            "name": "last5_compact_rule",
            "pass": ".eiq-product-shell-v4 .eiq-cell-last-five" in css and "letter-spacing: 0 !important" in css,
        },
        {
            "name": "sectional_sign_colours",
            "pass": all(token in css for token in ("td.is-negative", "td.is-positive", "td.is-neutral")),
        },
        {
            "name": "runner_header_required_identity_sources",
            "pass": all(token in component for token in ("runner.age", "runner.sex", "runner.breeding", "runner.trainer", "runner.jockey", "runner.weight")),
        },
        {
            "name": "metric_band_locked_metrics",
            "pass": all(token in component for token in ("Race Rank", "Field Average", "Difference", "Suitability", "Form Momentum"))
            and "Race Shape" not in component[component.find("function MetricBand") : component.find("function ProfileTable")],
        },
    ]

    status = "PASS" if all(item["pass"] for item in checks) else "FAIL"
    result = {
        "status": f"EDGEIQ_FORM_GUIDE_VISUAL_STRUCTURE_V2_AUDIT_{status}",
        "checks": checks,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join([result["status"], "", *[f"{'PASS' if item['pass'] else 'FAIL'} {item['name']}" for item in checks]]),
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
