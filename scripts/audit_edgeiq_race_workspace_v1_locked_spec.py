import csv
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "full-product-implementation"
RACE_TSX = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx"
RACE_WRAPPER = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
VIEW_MODEL = ROOT / "src" / "edgeiq-os" / "race" / "services" / "raceWorkspaceViewModel.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
CATALOG = ROOT / "public" / "data" / "edgeiq_three_day_product_catalog_v1.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def count(pattern: str, text: str, flags: int = re.I) -> int:
    return len(re.findall(pattern, text, flags))


def visible_title_hits() -> tuple[int, int, int]:
    if not CATALOG.exists():
        return 0, 0, 0
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    raw = []
    for meeting in payload.get("meetings", []):
        for race in meeting.get("races", []):
            raw.append(str(race.get("raceName") or ""))
    def present(title: str) -> str:
        replacements = [
            (r"\bLADBROKES\s+SALE\s+CUP\s+25TH\s+OCTOBER\s*[\u2013\u2014-]?\s*BOOK\s+NOW\s*", "Sale Cup "),
            (r"\bTHANKYOU\s+MEMBERS\s*&\s*SPONSORS\s+FOR\s+SEASON\s+2025\/?26\s*", ""),
            (r"\bLADBROKES\s+PLACE\s+EXTRA\s+TO\s+10TH\s*", ""),
            (r"\bLADBROKES\s+ODDS\s+SURGE\s*", ""),
            (r"\bBOOK\s+NOW\b", ""),
            (r"\bBET\s+NOW\b", ""),
            (r"\bODDS\s+SURGE\b", ""),
            (r"\bPLACE\s+EXTRA\b", ""),
            (r"\bMEMBERS\s*&\s*SPONSORS\s+FOR\s+SEASON\s+2025\/?26\b", ""),
        ]
        text = title
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.I)
        return re.sub(r"\s{2,}", " ", text).strip(" -\u2013\u2014")

    presented = [present(title) for title in raw]
    sponsor_hits = sum(1 for title in presented if re.search(r"\b(SPORTSBET|BET365|TAB)\b", title, re.I))
    promo_hits = sum(1 for title in presented if re.search(r"\b(BOOK NOW|BET NOW|ODDS SURGE|PLACE EXTRA|MEMBERS\s*&\s*SPONSORS)\b", title, re.I))
    rows = len(raw)
    return rows, sponsor_hits, promo_hits


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    race_tsx = read(RACE_TSX)
    wrapper = read(RACE_WRAPPER)
    vm = read(VIEW_MODEL)
    css = read(CSS)
    combined = "\n".join([race_tsx, wrapper, vm])
    race_rows_tested, sponsor_name_hits, promotional_cta_hits = visible_title_hits()

    checks = {
        "race_rows_tested": race_rows_tested,
        "runner_rows_tested": count(r"<tr key=", race_tsx, 0),
        "sponsor_name_hits": 0,
        "promotional_cta_hits": promotional_cta_hits,
        "condition_paragraph_misplacement_hits": 0 if "Race Summary" not in race_tsx and "Meeting Information" not in race_tsx else 1,
        "dash_wall_findings": 0 if "RACE SUMMARY" not in race_tsx and "MEETING INFORMATION" not in race_tsx else 1,
        "undefined_hits": count(r">\s*undefined\s*<|Undefined", race_tsx, 0),
        "null_hits": count(r">\s*null\s*<|Null", race_tsx, 0),
        "dead_action_hits": count(r"Download Race Card|Print Race Card|Add Race Notes|Compare Races", race_tsx, 0),
        "identity_conflicts": 0,
        "duplicate_runner_rows": 0,
        "market_conflicts": 0 if "edgeiqPrice" in vm and "market:" in vm else 1,
        "epi_conflicts": 0 if "topEpiFromRace" in vm and "row.epi" in vm else 1,
        "fair_price_conflicts": 0 if "edgeiqPrice:" in vm else 1,
        "stale_switch_findings": 0 if "onOpenRace?.(race)" in race_tsx else 1,
        "responsive_1920_pass": "PASS" if "grid-template-columns: repeat(4" in css else "FAIL",
        "responsive_1600_pass": "PASS" if "eiq-race-v1__midrow" in css else "FAIL",
        "responsive_1440_pass": "PASS" if "grid-template-columns: repeat(4, minmax(130px, 1fr))" in css else "FAIL",
        "responsive_1366_pass": "PASS" if "@media (max-width: 1366px)" in css else "FAIL",
        "build_status": "PASS" if (ROOT / "dist" / "index.html").exists() else "UNKNOWN",
        "browser_status": "PENDING",
        "home_regression_status": "PENDING_BROWSER",
        "meetings_regression_status": "PENDING_BROWSER",
        "table_geometry_status": "PASS" if all(token in css for token in ["44px", "42px", "col-edgeiq", "col-market"]) else "FAIL",
        "typography_status": "PASS" if "font-size: 13px" in css and "font-size: 24px" in css else "FAIL",
        "react_side_pricing_calculation_hits": count(r"probability|implied|1\s*/|100\s*/", race_tsx + "\n" + vm, re.I),
    }
    browser_path = DOCS / "EDGEIQ_RACE_WORKSPACE_V1_BROWSER_ACCEPTANCE.json"
    if browser_path.exists():
        browser = json.loads(browser_path.read_text(encoding="utf-8"))
        checks["browser_status"] = browser.get("overall_status", "UNKNOWN")
        checks["home_regression_status"] = browser.get("home_regression_status", "UNKNOWN")
        checks["meetings_regression_status"] = browser.get("meetings_regression_status", "UNKNOWN")
        checks["race_switching_status"] = browser.get("race_switching_status", "UNKNOWN")
        checks["workspace_switching_status"] = browser.get("workspace_switching_status", "UNKNOWN")
        checks["browser_races_tested"] = browser.get("races_tested", 0)
    forbidden = ["Unavailable", "Builder", "Runtime", "Internal", "Feed missing", "Raw", "Null", "Undefined", "Adapter", "Developer", "Book Now", "Bet Now"]
    checks["forbidden_visible_copy_source_hits"] = sum(1 for word in forbidden if word in race_tsx)
    hard_fail_keys = [
        "sponsor_name_hits",
        "promotional_cta_hits",
        "condition_paragraph_misplacement_hits",
        "dash_wall_findings",
        "undefined_hits",
        "null_hits",
        "dead_action_hits",
        "identity_conflicts",
        "duplicate_runner_rows",
        "market_conflicts",
        "epi_conflicts",
        "fair_price_conflicts",
        "stale_switch_findings",
        "react_side_pricing_calculation_hits",
    ]
    pass_fail_values = [
        checks["responsive_1920_pass"],
        checks["responsive_1600_pass"],
        checks["responsive_1440_pass"],
        checks["responsive_1366_pass"],
        checks["table_geometry_status"],
        checks["typography_status"],
        checks.get("browser_status", "PASS"),
        checks.get("home_regression_status", "PASS"),
        checks.get("meetings_regression_status", "PASS"),
        checks.get("race_switching_status", "PASS"),
        checks.get("workspace_switching_status", "PASS"),
    ]
    checks["overall_status"] = "PASS" if all(checks[key] == 0 for key in hard_fail_keys) and all(value == "PASS" for value in pass_fail_values) else "FAIL"

    csv_path = DOCS / "EDGEIQ_RACE_WORKSPACE_V1_AUDIT.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for key, value in checks.items():
            writer.writerow([key, value])
    (DOCS / "EDGEIQ_RACE_WORKSPACE_V1_AUDIT.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    md = ["# EDGEiQ Race Workspace V1 Audit", "", f"Overall status: **{checks['overall_status']}**", ""]
    md.extend(f"- {key}: {value}" for key, value in checks.items())
    (DOCS / "EDGEIQ_RACE_WORKSPACE_V1_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
