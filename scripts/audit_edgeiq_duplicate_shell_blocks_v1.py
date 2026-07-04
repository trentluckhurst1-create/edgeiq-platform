from pathlib import Path
from datetime import datetime, timezone
import csv
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = ROOT / "public" / "data" / "edgeiq_duplicate_shell_blocks_v1.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_duplicate_shell_blocks_v1_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_duplicate_shell_blocks_v1_report.txt"

LEGACY_PATTERNS = [
    ("EDGEIQ_RACING_TICKER", re.compile(r"EDGEIQ\s+RACING", re.I), "legacy ticker/header"),
    ("RACING_INTELLIGENCE_TERMINAL", re.compile(r"Racing Intelligence Terminal", re.I), "legacy terminal title"),
    ("LEGACY_MEETING_SELECTOR", re.compile(r"updateProductView\(\"MEETING\"\)|>Meeting<|Back to Home", re.I), "legacy meeting selector on race page"),
    ("LEGACY_RACE_SELECTOR", re.compile(r"shell-race-|selectedShellMeetingRaces|>Open Race<|\bR[1-8]\b", re.I), "legacy race selector on race page"),
    ("FIXED_DATE_STRIP", re.compile(r"DATE\s*25\s*JUN", re.I), "old fixed date strip"),
    ("FIXED_TRACK_STRIP", re.compile(r"TRACK\s+BENDIGO", re.I), "old fixed track strip"),
    ("FIELDS_READY_STRIP", re.compile(r"FIELDS READY", re.I), "old field status strip"),
    ("OLD_TAB_STRIP", re.compile(r"OVERVIEW[\s\S]{0,160}INTELLIGENCE[\s\S]{0,160}MARKET[\s\S]{0,160}TRACKING[\s\S]{0,160}RESULTS", re.I), "old overview/intelligence/market/tracking/results tab strip"),
    ("RACE_PAGE_SECONDARY", re.compile(r">\s*RACE PAGE\s*<|Race Page", re.I), "old secondary race page tab strip"),
    ("LEGACY_HEADER_CLASS", re.compile(r"edgeiq-command-header|edgeiq-workspace-tabs|edgeiq-primary-product-tabs", re.I), "legacy header/tab class"),
    ("COMMAND_WORKSPACE_DUPLICATE", re.compile(r"edgeiq-command-workspace|>\s*Command\s*<|COMMAND WORKSPACE", re.I), "old command workspace visible wrapper"),
]

PRODUCT_NAV_LABELS = ["RACE", "FIELD", "MAP", "INSIGHTS", "MARKET", "RESULTS"]


def lines(text: str):
    return text.splitlines()


def line_no_for(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def race_page_bounds(text: str):
    start = text.find('<div className="edgeiq-product-app')
    if start == -1:
        start = text.find('<div className="edgeiq-product-race')
    if start == -1:
        start = text.find('className="edgeiq-product-race')
    end = text.find('{ratingHover ?', start if start != -1 else 0)
    if end == -1:
        end = len(text)
    return start, end


def is_non_race_allowed(category: str, in_race: bool) -> bool:
    return category in {"LEGACY_MEETING_SELECTOR", "LEGACY_RACE_SELECTOR", "FIELDS_READY_STRIP"} and not in_race


def is_internal_allowed(category: str, line: str) -> bool:
    compact = line.strip()
    if category == "COMMAND_WORKSPACE_DUPLICATE" and ("IntelMode" in compact or "mode:" in compact or "setIntelMode" in compact):
        return True
    if category == "RACING_INTELLIGENCE_TERMINAL" and "professional racing intelligence terminal" in compact.lower():
        return True
    return False


def run_audit():
    text = TSX.read_text(encoding="utf-8")
    all_lines = lines(text)
    race_start, race_end = race_page_bounds(text)
    rows = []
    for category, pattern, description in LEGACY_PATTERNS:
        for match in pattern.finditer(text):
            idx = match.start()
            line_no = line_no_for(text, idx)
            line = all_lines[line_no - 1] if 0 <= line_no - 1 < len(all_lines) else ""
            in_race = race_start != -1 and race_start <= idx <= race_end
            allowed = is_non_race_allowed(category, in_race) or is_internal_allowed(category, line)
            visible_risk = in_race and not allowed
            rows.append({
                "category": category,
                "description": description,
                "line_number": line_no,
                "in_race_page_return": "YES" if in_race else "NO",
                "visible_risk": "YES" if visible_risk else "NO",
                "classification": "RACE_PAGE_VISIBLE_RISK" if visible_risk else ("ALLOWED_NON_RACE_OR_INTERNAL" if allowed else "SOURCE_PRESENT"),
                "matched_text": match.group(0).replace("\n", " ")[:220],
                "line": line.strip()[:600],
            })

    product_nav_visible = all(f'label: "{label}"' in text for label in PRODUCT_NAV_LABELS) and "edgeiq-product-nav" in text and "setIntelMode(tab.mode)" in text
    product_shell_visible = "edgeiq-product-app" in text and "edgeiq-product-topbar" in text and "edgeiq-product-race-hero" in text
    visible_risk_count = sum(1 for row in rows if row["visible_risk"] == "YES")
    old_ticker_visible = any(row for row in rows if row["category"] == "EDGEIQ_RACING_TICKER" and row["visible_risk"] == "YES")
    old_meeting_selector_visible = any(row for row in rows if row["category"] == "LEGACY_MEETING_SELECTOR" and row["visible_risk"] == "YES")
    old_race_selector_visible = any(row for row in rows if row["category"] == "LEGACY_RACE_SELECTOR" and row["visible_risk"] == "YES")
    old_tab_strip_visible = any(row for row in rows if row["category"] == "OLD_TAB_STRIP" and row["visible_risk"] == "YES")
    command_duplicate_visible = any(row for row in rows if row["category"] in {"COMMAND_WORKSPACE_DUPLICATE", "LEGACY_HEADER_CLASS"} and row["visible_risk"] == "YES")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "description", "line_number", "in_race_page_return", "visible_risk", "classification", "matched_text", "line"])
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = [
        {"metric": "status", "value": "DUPLICATE_SHELL_AUDIT_COMPLETE" if visible_risk_count == 0 and product_nav_visible and product_shell_visible else "DUPLICATE_SHELL_REVIEW_REQUIRED"},
        {"metric": "total_matches", "value": str(len(rows))},
        {"metric": "visible_risk_count", "value": str(visible_risk_count)},
        {"metric": "old_ticker_visible", "value": "YES" if old_ticker_visible else "NO"},
        {"metric": "old_meeting_selector_visible", "value": "YES" if old_meeting_selector_visible else "NO"},
        {"metric": "old_race_selector_visible", "value": "YES" if old_race_selector_visible else "NO"},
        {"metric": "old_tab_strip_visible", "value": "YES" if old_tab_strip_visible else "NO"},
        {"metric": "command_workspace_duplicate_visible", "value": "YES" if command_duplicate_visible else "NO"},
        {"metric": "product_shell_visible", "value": "YES" if product_shell_visible else "NO"},
        {"metric": "product_nav_visible", "value": "YES" if product_nav_visible else "NO"},
        {"metric": "product_nav_controls_tabs", "value": "YES" if "setIntelMode(tab.mode)" in text else "NO"},
        {"metric": "audited_at", "value": datetime.now(timezone.utc).isoformat()},
    ]
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(summary_rows)

    with REPORT.open("w", encoding="utf-8") as f:
        f.write("EDGEiQ Duplicate Shell Blocks V1 Audit\n")
        for row in summary_rows:
            f.write(f"{row['metric']}: {row['value']}\n")
        f.write("\nThis audit treats Home/Meeting page meeting lists as allowed; it flags duplicate chrome only when it can render inside the race page return.\n")

    print(summary_rows[0]["value"])


if __name__ == "__main__":
    run_audit()
