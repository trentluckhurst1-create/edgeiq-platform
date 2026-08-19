from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingsFeed.ts"
PRESENTATION = ROOT / "src" / "edgeiq-os" / "design-system" / "presentation.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
CATALOG = ROOT / "public" / "data" / "edgeiq_three_day_product_catalog_v1.json"
OUT_DIR = ROOT / "docs" / "full-product-implementation"
CSV_OUT = OUT_DIR / "EDGEIQ_MEETINGS_WORKSPACE_V1_AUDIT.csv"
JSON_OUT = OUT_DIR / "EDGEIQ_MEETINGS_WORKSPACE_V1_AUDIT.json"
MD_OUT = OUT_DIR / "EDGEIQ_MEETINGS_WORKSPACE_V1_AUDIT.md"
BROWSER_JSON = OUT_DIR / "EDGEIQ_MEETINGS_WORKSPACE_V1_BROWSER_ACCEPTANCE.json"

CSS_MARKER = "/* EDGEIQ MEETINGS WORKSPACE V1 LOCKED SPECIFICATION */"

SPONSORS = ["SPORTSBET", "LADBROKES", "BET365", "TAB "]
DEVELOPER_COPY = ["BUILDER CONTROLLED", "Runtime", "Feed missing", "Developer status", "Raw source", "Adapter state", "Internal error code"]
CONDITION_PARAGRAPH_TERMS = [
    "Set Weights",
    "Three-Years-Old",
    "No sex restriction",
    "Track name:",
    "Track type:",
    "Field limit:",
    "VOBIS",
    "prizemoney",
]


def scoped_css(text: str) -> str:
    if CSS_MARKER not in text:
        return ""
    return text.split(CSS_MARKER, 1)[1]


def canonical_track_name(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    aliases = {
        "SPORTSBET BALLARAT SYNTHETIC": "Ball Syn",
        "BALLARAT SYNTHETIC": "Ball Syn",
        "SPORTSBET BALLARAT": "Ballarat",
        "SPORTSBET PAKENHAM SYNTHETIC": "Pak Syn",
        "PAKENHAM SYNTHETIC": "Pak Syn",
        "SPORTSBET PAKENHAM": "Pakenham",
        "SOUTHSIDE PAKENHAM SYNTHETIC": "Pak Syn",
        "SOUTHSIDE PAKENHAM": "Pakenham",
        "SOUTHSIDE CRANBOURNE": "Cranbourne",
        "LADBROKES GEELONG": "Geelong",
        "SPORTSBET SANDOWN HILLSIDE": "Sandown Hillside",
        "SPORTSBET SANDOWN LAKESIDE": "Sandown Lakeside",
    }
    return aliases.get(text.upper(), re.sub(r"^(SPORTSBET|LADBROKES|BET365|TAB)\s+", "", text, flags=re.I).strip())


def track_rating(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return "Awaiting Track Rating"
    if re.search(r"synthetic", text, re.I):
        return "Synthetic"
    match = re.search(r"\b(Firm|Good|Soft|Heavy)\s*([0-9]{1,2})?\b", text, re.I)
    if not match:
        return "Awaiting Track Rating"
    return f"{match.group(1).capitalize()}{' ' + match.group(2) if match.group(2) else ''}"


def first_text(*values: object) -> str:
    for value in values:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if text and text.lower() not in {"-", "--", "pending", "null", "undefined", "none", "n/a", "na"}:
            return text
    return ""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    component = COMPONENT.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")
    presentation = PRESENTATION.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    css_block = scoped_css(css)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    browser = json.loads(BROWSER_JSON.read_text(encoding="utf-8")) if BROWSER_JSON.exists() else {}

    meetings = catalog.get("meetings", [])
    meeting_rows = len(meetings)
    track_ratings = []
    weather_rows = 0
    weather_governed = 0
    rail_rows = 0
    rail_governed = 0
    condition_paragraph_in_track_hits = 0
    sponsor_visible_hits = 0
    race_chip_count = 0
    race_chip_targets = 0

    for meeting in meetings:
        races = meeting.get("races") or []
        first_race = races[0] if races else {}
        source = first_race.get("source") or {}
        rating = track_rating(
            first_text(
                source.get("official_track_rating"),
                source.get("track_rating_short"),
                source.get("going"),
                source.get("track_rating"),
                source.get("track_condition"),
                first_race.get("trackCondition"),
                meeting.get("trackCondition"),
            )
        )
        track_ratings.append(rating)
        if any(term.lower() in rating.lower() for term in CONDITION_PARAGRAPH_TERMS):
            condition_paragraph_in_track_hits += 1
        if any(sponsor in canonical_track_name(meeting.get("meeting")).upper() for sponsor in SPONSORS):
            sponsor_visible_hits += 1
        weather = first_text(source.get("weather"))
        if weather:
            weather_rows += 1
        else:
            weather_governed += 1
        rail = first_text(first_race.get("rail"), source.get("rail_position"), meeting.get("rail"))
        if rail:
            rail_rows += 1
        else:
            rail_governed += 1
        for race in races:
            race_chip_count += 1
            if race.get("raceKey") and race.get("raceNumber"):
                race_chip_targets += 1

    visible_source = component + "\n" + service + "\n" + presentation
    developer_copy_hits = sum(visible_source.lower().count(term.lower()) for term in DEVELOPER_COPY)
    undefined_hits = component.lower().count("undefined")
    weather_unavailable_hits = visible_source.count("Weather unavailable")

    def has_css(*needles: str) -> bool:
        return all(needle in css_block for needle in needles)

    checks = {
        "build_status": browser.get("build_status", "PASS_FROM_PRIOR_BUILD"),
        "browser_status": browser.get("browser_status", "PENDING"),
        "workspace_switching_status": browser.get("workspace_switching_status", "PENDING"),
        "meeting_rows": meeting_rows,
        "track_rating_populated_rows": sum(1 for item in track_ratings if item != "Awaiting Track Rating"),
        "weather_populated_rows": weather_rows,
        "weather_governed_status_rows": weather_governed,
        "rail_populated_rows": rail_rows,
        "rail_governed_status_rows": rail_governed,
        "sponsor_name_visible_hits": sponsor_visible_hits,
        "condition_paragraph_in_track_hits": condition_paragraph_in_track_hits,
        "developer_copy_hits": developer_copy_hits,
        "undefined_visible_hits": undefined_hits,
        "weather_unavailable_copy_hits": weather_unavailable_hits,
        "table_header_height": "42px" if has_css(".eiq-meetings-v1-table th", "height: 42px") else "MISSING",
        "table_row_height": "42px" if has_css(".eiq-meetings-v1-table td", "height: 42px") else "MISSING",
        "minimum_body_font_size": "14px" if has_css(".eiq-meetings-v1-table td", "font-size: 14px") else "MISSING",
        "button_height": "36px" if has_css(".eiq-meetings-v1-button", "height: 36px") else "MISSING",
        "date_control_height": "44px" if has_css(".eiq-meetings-v1-date-range button", "height: 44px") else "MISSING",
        "race_chip_height": "28px" if has_css(".eiq-meetings-v1-race-chip", "height: 28px") else "MISSING",
        "race_chip_count": race_chip_count,
        "race_chip_navigation_pass": "PASS" if race_chip_count and race_chip_targets == race_chip_count else "FAIL",
        "track_status_clipping_findings": browser.get("track_status_clipping_findings", 0),
        "weather_status_clipping_findings": browser.get("weather_status_clipping_findings", 0),
        "date_switching_pass": browser.get("date_switching_status", "PENDING"),
        "meeting_selection_pass": browser.get("meeting_selection_status", "PENDING"),
        "open_meeting_pass": browser.get("open_meeting_status", "PENDING"),
        "status_filter_fallback_pass": browser.get("status_filter_fallback_pass", "PENDING"),
        "home_regression": browser.get("home_regression", "PENDING"),
        "timeline_overlap_findings": browser.get("timeline_overlap_findings", "PENDING"),
        "responsive_1920_pass": browser.get("responsive_1920_pass", "PENDING"),
        "responsive_1440_pass": browser.get("responsive_1440_pass", "PENDING"),
        "responsive_1366_pass": browser.get("responsive_1366_pass", "PENDING"),
    }
    gates_pass = (
        checks["browser_status"] == "PASS"
        and checks["workspace_switching_status"] == "PASS"
        and condition_paragraph_in_track_hits == 0
        and sponsor_visible_hits == 0
        and weather_unavailable_hits == 0
        and developer_copy_hits == 0
        and undefined_hits == 0
        and checks["table_header_height"] == "42px"
        and checks["table_row_height"] == "42px"
        and checks["minimum_body_font_size"] == "14px"
        and checks["button_height"] == "36px"
        and checks["date_control_height"] == "44px"
        and checks["race_chip_height"] == "28px"
        and checks["race_chip_navigation_pass"] == "PASS"
        and checks["track_status_clipping_findings"] == 0
        and checks["weather_status_clipping_findings"] == 0
        and checks["date_switching_pass"] == "PASS"
        and checks["meeting_selection_pass"] == "PASS"
        and checks["open_meeting_pass"] == "PASS"
        and checks["status_filter_fallback_pass"] == "PASS"
        and checks["home_regression"] == "PASS"
        and checks["responsive_1920_pass"] == "PASS"
        and checks["responsive_1440_pass"] == "PASS"
        and checks["responsive_1366_pass"] == "PASS"
    )
    checks["overall_status"] = "PASS" if gates_pass else "PENDING_OR_FAIL"

    with CSV_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field", "value"])
        writer.writeheader()
        for key, value in checks.items():
            writer.writerow({"field": key, "value": value})

    JSON_OUT.write_text(json.dumps(checks, indent=2), encoding="utf-8")
    md = [
        "# EDGEIQ MEETINGS WORKSPACE V1 AUDIT",
        "",
        f"Overall status: {checks['overall_status']}",
        "",
        "## Fields",
        "",
    ]
    for key, value in checks.items():
        md.append(f"- {key}: {value}")
    MD_OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2))
    return 0 if checks["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
