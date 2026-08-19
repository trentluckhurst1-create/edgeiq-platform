from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "src" / "edgeiq-os" / "home" / "EdgeiqOsHome.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_DIR = ROOT / "docs" / "full-product-implementation"
CSV_OUT = OUT_DIR / "EDGEIQ_HOME_WORKSPACE_V1_AUDIT.csv"
JSON_OUT = OUT_DIR / "EDGEIQ_HOME_WORKSPACE_V1_AUDIT.json"
MD_OUT = OUT_DIR / "EDGEIQ_HOME_WORKSPACE_V1_AUDIT.md"

CSS_MARKER = "/* EDGEIQ HOME WORKSPACE V1 LOCKED SPECIFICATION */"


def contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def home_css_block(css: str) -> str:
    if CSS_MARKER not in css:
        return ""
    return css.split(CSS_MARKER, 1)[1]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    home = HOME.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    scoped_css = home_css_block(css)

    checks: list[dict[str, str]] = []

    def add(check: str, status: bool, evidence: str) -> None:
        checks.append(
            {
                "check": check,
                "status": "PASS" if status else "FAIL",
                "evidence": evidence,
            }
        )

    add("home_component_exists", HOME.exists(), str(HOME))
    add("home_css_marker_exists", CSS_MARKER in css, CSS_MARKER)
    add("home_shell_class_exists", "eiq-home-v1" in home and ".eiq-home-v1" in scoped_css, "eiq-home-v1")
    add("page_max_width_1600", "max-width: 1600px" in scoped_css, "max-width: 1600px")
    add("page_padding_24", "padding: 24px" in scoped_css, "padding: 24px")
    add("section_gap_20", "gap: 20px" in scoped_css, "gap: 20px")
    add("card_padding_20", "padding: 20px" in scoped_css, "padding: 20px")
    add("card_radius_8", "border-radius: 8px" in scoped_css, "border-radius: 8px")
    add("welcome_heading_locked", "Welcome to EDGEIQ" in home, "Welcome to EDGEIQ")
    add(
        "value_panels_locked",
        contains_all(home, ["Evidence First", "Built For Professionals", "Complete Intelligence"]),
        "Evidence First | Built For Professionals | Complete Intelligence",
    )
    add(
        "meetings_columns_locked",
        contains_all(home, ["Meeting", "State", "Rail", "Track", "Weather", "Races", "Declared", "Scratchings"]),
        "Meeting | State | Rail | Track | Weather | Races | Declared | Scratchings",
    )
    add(
        "workspace_launcher_rows_locked",
        contains_all(home, ["Race Intelligence", "Performance", "Market", "Track Bias", "Compare", "Lab", "Review", "Settings"]),
        "Race Intelligence | Performance | Market | Track Bias | Compare | Lab | Review | Settings",
    )
    add(
        "data_quality_rows_locked",
        contains_all(home, ["Pipeline", "Status", "Window", "Meetings", "Races", "Declared", "Scratchings", "Last Build"]),
        "Pipeline | Status | Window | Meetings | Races | Declared | Scratchings | Last Build",
    )
    add("recent_analysis_exists", "Recent Analysis" in home, "Recent Analysis")
    add("floating_status_exists", "eiq-home-v1__floating-status" in home and "eiq-home-v1__floating-status" in scoped_css, "floating data status")
    add("table_header_height_40", ".eiq-home-v1-table th" in scoped_css and "height: 40px" in scoped_css, "table header height 40")
    add("table_row_height_40", ".eiq-home-v1-table td" in scoped_css and "height: 40px" in scoped_css, "table row height 40")
    add("button_height_36", "height: 36px" in scoped_css, "button height 36")
    add("no_home_gradients", "linear-gradient" not in scoped_css and "radial-gradient" not in scoped_css, "no gradients in scoped Home block")
    add(
        "forbidden_visible_copy_absent",
        not any(
            forbidden in home
            for forbidden in [
                "Weather unavailable",
                "Unavailable",
                "Builder",
                "Implementation",
                "Source Aware",
                "Evidence Quality",
                "Operational Status",
                "Data Connected",
                "Engine Active",
                "Gear Unavailable",
                "Sportsbet",
                "Ladbrokes",
            ]
        ),
        "forbidden user-facing copy absent",
    )

    pass_count = sum(1 for row in checks if row["status"] == "PASS")
    fail_count = len(checks) - pass_count
    verdict = "PASS" if fail_count == 0 else "FAIL"

    with CSV_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "evidence"])
        writer.writeheader()
        writer.writerows(checks)

    payload = {
        "verdict": verdict,
        "checks": len(checks),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "home_file": str(HOME),
        "css_file": str(CSS),
        "outputs": [str(CSV_OUT), str(JSON_OUT), str(MD_OUT)],
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# EDGEIQ HOME WORKSPACE V1 AUDIT",
        "",
        f"Verdict: {verdict}",
        f"Checks: {len(checks)}",
        f"Pass: {pass_count}",
        f"Fail: {fail_count}",
        "",
        "## Findings",
        "",
    ]
    for row in checks:
        lines.append(f"- {row['status']}: {row['check']} - {row['evidence']}")
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
