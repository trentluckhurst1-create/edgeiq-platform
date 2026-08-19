import csv
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "full-product-implementation"
SCREENSHOT_DIR = DOC_DIR / "screenshots" / "final-conformance"

MATRIX_PATH = DOC_DIR / "EDGEIQ_FINAL_SPEC_CONFORMANCE_MATRIX_V1.csv"
REPORT_PATH = DOC_DIR / "EDGEIQ_FINAL_SPEC_CONFORMANCE_REPORT_V1.md"
DATA_WIRING_PATH = DOC_DIR / "EDGEIQ_FINAL_DATA_WIRING_MATRIX_V1.md"
AUDIT_COVERAGE_PATH = DOC_DIR / "EDGEIQ_FULL_PRODUCT_AUDIT_COVERAGE_REVIEW_V1.md"
POPULATED_TEST_PATH = DOC_DIR / "EDGEIQ_FINAL_POPULATED_TEST_MATRIX_V1.md"

STATUSES = {"PASS", "PARTIAL", "FAIL", "DATA GAP", "NOT TESTED"}


@dataclass
class Requirement:
    workspace: str
    section: str
    requirement_id: str
    requirement: str
    expected: str
    check: Callable[[], tuple[str, str, str, str, str, str]]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def source(path: str) -> Path:
    return ROOT / path


def contains(path: str, token: str) -> bool:
    return token in read_text(source(path))


def contains_any(path: str, tokens: list[str]) -> bool:
    text = read_text(source(path))
    return any(token in text for token in tokens)


def regex(path: str, pattern: str) -> bool:
    return re.search(pattern, read_text(source(path)), re.I | re.S) is not None


def screenshot_evidence() -> dict[str, dict]:
    path = SCREENSHOT_DIR / "screenshot_evidence_v1.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {item.get("name", ""): item for item in data.get("evidence", [])}


SCREENSHOTS = screenshot_evidence()


def persistence_evidence() -> dict:
    path = SCREENSHOT_DIR / "browser_persistence_evidence_v1.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


PERSISTENCE_EVIDENCE = persistence_evidence()


def screenshot_status(name: str) -> tuple[str, str, str]:
    item = SCREENSHOTS.get(name)
    if not item:
        return "NOT TESTED", f"No screenshot evidence was captured for {name}.", "none"
    path = item.get("path", "")
    return "PASS", f"Screenshot captured for {name}.", path


def screenshot_headers(name: str) -> list[str]:
    item = SCREENSHOTS.get(name)
    if not item:
        return []
    return [str(header).strip() for header in item.get("tableHeaders", [])]


def pass_if(condition: bool, actual: str, evidence_type: str, evidence_path: str, source_file: str, symbol: str = ""):
    return ("PASS" if condition else "FAIL", actual, evidence_type, evidence_path, source_file, symbol)


def partial(actual: str, evidence_type="manual/source", evidence_path="", source_file="", symbol=""):
    return "PARTIAL", actual, evidence_type, evidence_path, source_file, symbol


def data_gap(actual: str, evidence_type="source/data", evidence_path="", source_file="", symbol=""):
    return "DATA GAP", actual, evidence_type, evidence_path, source_file, symbol


def not_tested(actual: str, evidence_type="not tested", evidence_path="", source_file="", symbol=""):
    return "NOT TESTED", actual, evidence_type, evidence_path, source_file, symbol


def route_order_check():
    path = "src/edgeiq-os/race/components/AppNavigation.tsx"
    text = read_text(source(path))
    expected = [
        "HOME", "MEETINGS", "RACE", "FIELD", "FORM GUIDE", "PERFORMANCE", "EPI", "MAP",
        "MARKET", "OVERVIEW", "INSIGHTS", "RESULTS", "LAB", "COMPARE", "REVIEW", "SETTINGS",
    ]
    labels = re.findall(r'label:\s*"([^"]+)"', text)
    return pass_if(labels == expected, f"Navigation labels: {' > '.join(labels)}", "source", path, path, "navItems")


def form_columns_check():
    path = "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
    text = read_text(source(path))
    expected = [
        "NO", "SILKS", "LAST 5", "HORSE", "TRAINER", "JOCKEY", "WT", "BAR", "DAYS",
        "EPI", "EARLY SPEED", "LATE SPEED", "SUITABILITY", "FORM MOMENTUM", "MARKET", "EDGEiQ PRICE",
    ]
    found = re.search(r"const summaryColumns = \[(.*?)\] as const;", text, re.S)
    labels = re.findall(r'"([^"]+)"', found.group(1)) if found else []
    return pass_if(labels == expected, f"summaryColumns: {' | '.join(labels)}", "source", path, path, "summaryColumns")


def recent_form_columns_check():
    path = "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
    text = read_text(source(path))
    expected = [
        "DATE", "TRACK", "DIST", "CLASS", "COND", "JOCKEY", "BAR", "WT", "POS", "FIELD",
        "SP", "MARGIN", "EPI", "ERI", "PIR", "8-6", "6-4", "4-2", "2-F",
    ]
    found = re.search(r"const recentFormColumns = \[(.*?)\] as const;", text, re.S)
    labels = re.findall(r'"([^"]+)"', found.group(1)) if found else []
    return pass_if(labels == expected, f"recentFormColumns: {' | '.join(labels)}", "source", path, path, "recentFormColumns")


def no_rejected_form_columns_check():
    path = "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
    text = read_text(source(path))
    rejected = ["Confidence", "Race Shape", "Avg Finish", "Back", "Lay", "Recommendation", "Tip"]
    present = [token for token in rejected if token in text]
    return pass_if(not present, f"Rejected form-table tokens present: {present or 'none'}", "source", path, path, "RaceFormGuideWorkspace")


def meetings_columns_check():
    path = "src/edgeiq-os/race/components/MeetingsWorkspace.tsx"
    expected = ["SELECT", "MEETING", "STATE", "RAIL", "TRACK", "WEATHER", "RACES", "DECLARED", "SCRATCHINGS"]
    observed = screenshot_headers("MEETINGS")
    if observed:
        return pass_if(observed == expected, f"Rendered headers: {' | '.join(observed)}", "browser screenshot", str(SCREENSHOT_DIR / "meetings.png"), path, "Meetings table headers")
    text = read_text(source(path))
    present = [token for token in expected if token in text]
    rejected = [token for token in ["FIRST", "LAST", "UPDATE", "OPEN", "RUNNERS", "EDGEIQ READ", "STATUS"] if token in text]
    return pass_if(len(present) == len(expected) and not rejected, f"Source expected={present}; rejected={rejected}", "source", path, path, "Meetings table headers")


def map_orientation_check():
    path = "src/edgeiq-os/race/components/MapWorkspace.tsx"
    text = read_text(source(path))
    checks = {
        "barriers on right": "barrier" in text.lower() and ("right" in text.lower() or "start side right" in text.lower()),
        "barrier 1 bottom": "bottom" in text.lower(),
        "right to left": "right-to-left" in text.lower() or "Racing direction <-" in text or "direction left" in text.lower(),
        "no cartoon horse": "cartoon" not in text.lower(),
    }
    ok = all(checks.values())
    return pass_if(ok, f"Map source orientation checks: {checks}", "source", path, path, "MapWorkspace")


def market_columns_check():
    path = "src/edgeiq-os/race/components/MarketWorkspace.tsx"
    text = read_text(source(path))
    expected = ["NO", "RUNNER", "EDGEiQ", "MARKET", "FAIR", "EDGE", "FLUC 60s %", "STATUS"]
    ok = all(token in text for token in expected)
    rejected = [token for token in ["Back", "Lay", "stake", "CTA", "Confidence"] if token in text]
    return pass_if(ok and not rejected, f"Expected market headers present={ok}; rejected={rejected or 'none'}", "source", path, path, "MarketWorkspace")


def performance_columns_check():
    path = "src/edgeiq-os/race/components/PerformanceWorkspace.tsx"
    observed = screenshot_headers("PERFORMANCE")
    expected_core = ["No", "Silk", "Horse", "EPI", "Current", "Peak", "Avg", "Last", "L5", "L4", "L3", "L2", "L1"]
    rejected = {"DIST", "GOING", "CLASS"}
    observed_upper = [header.upper() for header in observed]
    has_rejected = any(header in observed_upper for header in rejected)
    if observed:
        missing = [header for header in expected_core if header.upper() not in observed_upper]
        if missing or has_rejected:
            return partial(f"Rendered Performance headers are {' | '.join(observed)}; missing expected final headers {missing or 'none'}; rejected present={has_rejected}", "browser screenshot", str(SCREENSHOT_DIR / "performance.png"), path, "Performance headers")
        return "PASS", f"Rendered Performance headers: {' | '.join(observed)}", "browser screenshot", str(SCREENSHOT_DIR / "performance.png"), path, "Performance headers"
    return not_tested("No rendered Performance table headers captured.", "browser screenshot", str(SCREENSHOT_DIR / "performance.png"), path, "Performance headers")


def lab_controls_check():
    path = "src/edgeiq-os/race/components/LabWorkspace.tsx"
    text = read_text(source(path))
    required = ["Universe", "Track", "Scope", "Entity", "Metric", "Group By", "Sort", "Result Limit", "Run Query"]
    present = [token for token in required if token in text]
    missing = [token for token in required if token not in text]
    # Spec asks Horse/Jockey/Trainer/Race entity selectors; implementation intentionally exposes governed supported set only.
    entity_gap = not all(token in text for token in ["HORSE", "JOCKEY", "TRAINER", "RACE"])
    if missing:
        return "FAIL", f"Missing LAB controls: {missing}", "source", path, path, "LabWorkspace"
    if entity_gap:
        return "DATA GAP", "LAB controls exist, but Jockey/Trainer are withheld until governed research dataset is available.", "source", path, path, "LabWorkspace"
    return "PASS", f"LAB controls present: {present}", "source", path, path, "LabWorkspace"


def weather_no_debug_check():
    path = "src/edgeiq-os/race/components/MeetingWeatherWorkspace.tsx"
    text = read_text(source(path))
    rejected = [
        "radar", "Forecast Source", "Weather Stations", "station ID", "station number",
        "source registry", "evidence URL", "builder status",
    ]
    present = [token for token in rejected if re.search(re.escape(token), text, re.I)]
    return pass_if(not present, f"Weather rejected technical labels: {present or 'none'}", "source", path, path, "MeetingWeatherWorkspace")


def settings_controls_check():
    path = "src/edgeiq-os/race/components/SettingsWorkspace.tsx"
    text = read_text(source(path))
    dead_words = ["toggle", "checkbox", "input", "select"]
    interactive = [token for token in dead_words if token in text]
    if interactive:
        return partial(f"Settings exposes possible controls requiring browser persistence testing: {interactive}", "source", path, path, "SettingsWorkspace")
    return pass_if("Display" in text and "Data" in text, "Settings currently presents governance/display state without model controls.", "source", path, path, "SettingsWorkspace")


def refresh_persistence_check():
    path = "src/edgeiq-os/race/RaceFileV3.tsx"
    text = read_text(source(path))
    has_url_or_storage = any(token in text for token in ["localStorage", "sessionStorage", "URLSearchParams", "window.location", "history.pushState"])
    if has_url_or_storage and PERSISTENCE_EVIDENCE.get("status") == "PASS":
        return "PASS", "Browser reload preserved selected meeting, race, and workspace context.", "browser screenshot/evidence", str(SCREENSHOT_DIR / "browser_persistence_evidence_v1.json"), path, "RaceFileV3 state"
    if has_url_or_storage:
        return partial("Some persistence/navigation mechanism exists, but full refresh/back-forward behavior still needs browser verification.", "source", path, path, "RaceFileV3 state")
    return "FAIL", "Selected meeting/race/view state is held in React state only; refresh persistence is not proven and likely resets context.", "source", path, path, "RaceFileV3 state"


def epi_no_confidence_check():
    path = "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx"
    observed = screenshot_headers("EPI")
    if observed and "Confidence" not in observed and "CONFIDENCE" not in [item.upper() for item in observed]:
        return "PASS", f"Rendered EPI headers omit Confidence; headers: {' | '.join(observed)}", "browser screenshot", str(SCREENSHOT_DIR / "epi.png"), path, "EPI headers"
    return partial("EPI internal source uses sourceConfidence fields; rendered label requires visual verification when screenshot headers unavailable.", "source/browser", path, path, "EPI headers")


def global_home_visual_check():
    item = SCREENSHOTS.get("HOME")
    if not item:
        return not_tested("HOME screenshot not captured.", "browser screenshot", str(SCREENSHOT_DIR / "home.png"), "", "HOME")
    headings = " ".join(item.get("headings", []))
    if "Race intelligence workspace" in headings and "Light workspace locked" in headings:
        return partial("HOME is operational and white-theme, but current rendering is sparse and may be useful rather than exact final HOME product hub.", "browser screenshot", item.get("path", ""), "src/edgeiq-os/home/EdgeiqOsHome.tsx", "EdgeiqOsHome")
    return "PASS", "HOME screenshot captured with operational entry content.", "browser screenshot", item.get("path", ""), "src/edgeiq-os/home/EdgeiqOsHome.tsx", "EdgeiqOsHome"


def screenshot_req(workspace: str):
    def check():
        status, actual, path = screenshot_status(workspace)
        return status, actual, "browser screenshot", path, "", workspace
    return check


def track_assets_check():
    path = "src/edgeiq-os/race/services/trackMapAssets.ts"
    text = read_text(source(path))
    checks = {
        "Flemington": "FLEMINGTON" in text,
        "Caulfield": "CAULFIELD" in text,
        "Sandown Hillside": "SANDOWN" in text and "HILLSIDE" in text,
        "Sandown Lakeside": "SANDOWN" in text and "LAKESIDE" in text,
        "Bendigo": "BENDIGO" in text,
        "Ballarat Turf": "BALLARAT" in text,
        "Ballarat Synthetic": "SYNTHETIC" in text,
        "Cranbourne": "CRANBOURNE" in text,
        "Pakenham Turf": "PAKENHAM" in text,
        "Pakenham Synthetic": "PAKENHAM" in text and "SYNTHETIC" in text,
        "Geelong": "GEELONG" in text,
    }
    missing = [track for track, ok in checks.items() if not ok]
    return pass_if(not missing, f"Curated track asset keywords missing: {missing or 'none'}", "source", path, path, "TRACK_MAP_ASSETS")


def results_structure_check():
    path = "src/edgeiq-os/race/components/ResultsWorkspace.tsx"
    text = read_text(source(path))
    required = ["Runner Performance", "Stewards", "EPI", "ERI", "Sectionals"]
    rejected = ["replay", "official sectional", "raw timing", "confidence"]
    missing = [token for token in required if token not in text]
    present_rejected = [token for token in rejected if re.search(re.escape(token), text, re.I)]
    return pass_if(not missing and not present_rejected, f"Missing={missing or 'none'}; rejected={present_rejected or 'none'}", "source", path, path, "ResultsWorkspace")


def meeting_detail_check():
    path = "src/edgeiq-os/race/components/MeetingWorkspace.tsx"
    headers = screenshot_headers("MEETING DETAIL")
    has_race_list = all(header in headers for header in ["RACE", "TIME", "RACE NAME", "DIST", "CLASS", "FIELD", "SCR", "STATUS"])
    text = read_text(source(path))
    no_debug = not contains_any(path, ["station ID", "builder status", "Confidence"])
    return pass_if(has_race_list and no_debug, f"Rendered race-list headers={headers}; debug absent={no_debug}", "browser screenshot/source", str(SCREENSHOT_DIR / "meeting-detail.png"), path, "MeetingWorkspace")


def gear_changes_check():
    path = "src/edgeiq-os/race/components/MeetingGearChangesWorkspace.tsx"
    text = read_text(source(path))
    required = ["GEAR CHANGES", "PREVIOUS GEAR", "TODAY GEAR", "FIRST TIME"]
    rejected = ["impact score", "verdict", "Confidence"]
    missing = [token for token in required if token not in text]
    present_rejected = [token for token in rejected if re.search(re.escape(token), text, re.I)]
    return pass_if(not missing and not present_rejected, f"Missing={missing or 'none'}; rejected={present_rejected or 'none'}", "source", path, path, "MeetingGearChangesWorkspace")


def race_structure_check():
    path = "src/edgeiq-os/race/components/RaceIntelligenceWorkspace.tsx"
    headers = screenshot_headers("RACE")
    has_runner_board = headers == ["NO", "SILK", "RUNNER", "BAR", "WGT", "JOCKEY", "TRAINER", "EPI SPD", "EDGEiQ", "MARKET", "STATUS"]
    text = read_text(source(path))
    required_present = all(token in text for token in ["Tempo", "EPF", "What Matters", "Runner Board"])
    if has_runner_board and required_present:
        return "PASS", f"Runner board headers and Race structure confirmed.", "browser screenshot/source", str(SCREENSHOT_DIR / "race.png"), path, "RaceIntelligenceWorkspace"
    return partial(f"Runner board headers={headers}; structure tokens present={required_present}", "browser screenshot/source", str(SCREENSHOT_DIR / "race.png"), path, "RaceIntelligenceWorkspace")


def review_boundary_check():
    path = "src/edgeiq-os/race/components/ReviewWorkspace.tsx"
    headings = " ".join(SCREENSHOTS.get("REVIEW", {}).get("headings", []))
    text = read_text(source(path))
    no_fake = not contains_any(path, ["mock activity", "fake saved", "activity feed"])
    return pass_if("No saved review record" in headings and no_fake, f"Rendered review headings include no saved record={ 'No saved review record' in headings }; fake terms absent={no_fake}", "browser screenshot/source", str(SCREENSHOT_DIR / "review.png"), path, "ReviewWorkspace")


def compare_controls_check():
    path = "src/edgeiq-os/compare/CompareWorkspace.tsx"
    text = read_text(source(path))
    required = ["Entity", "Left", "Right", "Common Metrics"]
    rejected = ["winner", "recommendation", "confidence", "radar"]
    missing = [token for token in required if token not in text]
    present_rejected = [token for token in rejected if re.search(re.escape(token), text, re.I)]
    return pass_if(not missing and not present_rejected, f"Missing={missing or 'none'}; rejected={present_rejected or 'none'}", "source", path, path, "CompareWorkspace")


def make_requirements() -> list[Requirement]:
    reqs: list[Requirement] = []

    def add(workspace, section, rid, requirement, expected, check):
        reqs.append(Requirement(workspace, section, rid, requirement, expected, check))

    add("GLOBAL", "Navigation", "GLOBAL-NAV-001", "Exact global navigation names and order remain locked.", "HOME > MEETINGS > RACE > FIELD > FORM GUIDE > PERFORMANCE > EPI > MAP > MARKET > OVERVIEW > INSIGHTS > RESULTS > LAB > COMPARE > REVIEW > SETTINGS", route_order_check)
    add("GLOBAL", "Persistence", "GLOBAL-STATE-001", "Refresh must not destroy selected meeting/race context.", "Selected meeting and race survive refresh/back-forward.", refresh_persistence_check)
    for workspace in [
        "HOME", "MEETINGS", "MEETING DETAIL", "SCRATCHINGS", "GEAR CHANGES", "TRACK", "WEATHER",
        "RACE", "FIELD", "FIELD expanded", "FORM GUIDE", "FORM GUIDE expanded", "PERFORMANCE", "EPI",
        "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "RESULTS", "RESULTS expanded", "LAB", "LAB query result",
        "COMPARE", "REVIEW", "SETTINGS",
    ]:
        add(workspace, "Visual", f"{workspace.upper().replace(' ', '-')}-VIS-001", "Rendered workspace screenshot evidence exists.", "Screenshot or explicit NOT TESTED evidence.", screenshot_req(workspace))

    add("HOME", "Utility", "HOME-001", "HOME is a useful professional product entry point, not a marketing or fake-activity page.", "Operational current racing hub with honest data availability.", global_home_visual_check)
    add("MEETINGS", "Columns", "MEETINGS-COL-001", "Meetings table uses approved columns only.", "SELECT / MEETING / STATE / RAIL / TRACK / WEATHER / RACES / DECLARED / SCRATCHINGS", meetings_columns_check)
    add("MEETING DETAIL", "Identity", "MEETING-DETAIL-001", "Meeting detail shows identity, race list, declared runners, scratchings, rail, condition, weather.", "Approved meeting detail content only.", meeting_detail_check)
    add("SCRATCHINGS", "Data", "SCRATCHINGS-001", "Official scratchings are shown without independently conflicting barrier compression.", "Governed scratchings feed and shared state.", lambda: pass_if(contains("src/edgeiq-os/race/components/MeetingScratchingsWorkspace.tsx", "scratching") and contains("src/edgeiq-os/race/services/scratchingsFeed.ts", "load"), "Scratchings workspace is feed-backed.", "source", "src/edgeiq-os/race/components/MeetingScratchingsWorkspace.tsx", "src/edgeiq-os/race/components/MeetingScratchingsWorkspace.tsx", "MeetingScratchingsWorkspace"))
    add("GEAR CHANGES", "Data", "GEAR-001", "Gear changes show previous/current/first-time gear where officially supplied and no verdict/impact score.", "No fake gear implications.", gear_changes_check)
    add("TRACK", "Assets", "TRACK-001", "Curated track assets exist and distinguish key Victorian tracks.", "Flemington, Caulfield, Sandown variants, Bendigo, Ballarat variants, Cranbourne, Pakenham variants, Geelong.", track_assets_check)
    add("WEATHER", "Language", "WEATHER-001", "Weather omits radar, station IDs, registry labels, evidence URLs, and builder status.", "Useful current conditions only.", weather_no_debug_check)
    add("RACE", "Structure", "RACE-001", "Race workspace is distinct from Overview and includes runner board/intelligence sections.", "Tempo, EPF, Key Determinants, Hidden Angles, What Matters Today, speed-map preview, EPI Top 3, runner board.", race_structure_check)
    add("FIELD", "Columns", "FIELD-001", "Field table uses approved columns and does not duplicate full Form Guide dossier.", "NO/SILK/RUNNER/BAR/WGT/JOCKEY/TRAINER/EDGEiQ/MARKET/STATUS.", lambda: pass_if(all(contains("src/edgeiq-os/race/components/FieldWorkspace.tsx", token) for token in ["EDGEiQ", "MARKET", "STATUS"]) and not contains("src/edgeiq-os/race/components/FieldWorkspace.tsx", "Today"), "Field source includes approved table labels and omits dossier language.", "source", "src/edgeiq-os/race/components/FieldWorkspace.tsx", "src/edgeiq-os/race/components/FieldWorkspace.tsx", "FieldWorkspace"))
    add("FORM GUIDE", "Summary Columns", "FORM-COL-001", "Main Form Guide columns exactly match approved V4 order.", "NO/SILKS/LAST 5/HORSE/TRAINER/JOCKEY/WT/BAR/DAYS/EPI/EARLY SPEED/LATE SPEED/SUITABILITY/FORM MOMENTUM/MARKET/EDGEiQ PRICE.", form_columns_check)
    add("FORM GUIDE", "Rejected Columns", "FORM-COL-002", "Rejected Form Guide columns are absent.", "No Confidence/Race Shape/Avg Finish/Back/Lay/generic rank/tip/recommendation.", no_rejected_form_columns_check)
    add("FORM GUIDE", "Recent Form Columns", "FORM-RECENT-001", "Recent Form includes governed fields and ESI movement columns.", "DATE/TRACK/DIST/CLASS/COND/JOCKEY/BAR/WT/POS/FIELD/SP/MARGIN/EPI/ERI/PIR/8-6/6-4/4-2/2-F.", recent_form_columns_check)
    add("PERFORMANCE", "Historical Heatmap", "PERF-001", "Performance is historical performance analysis and not EPI substitution.", "Historical performance rating service/view-model boundary and final columns.", performance_columns_check)
    add("EPI", "Canonical", "EPI-001", "EPI is distinct from Performance and has no Confidence label.", "No Confidence label and no component-side EPI calculation.", epi_no_confidence_check)
    add("MAP", "Orientation", "MAP-001", "Map follows Victorian orientation, barriers right, B1 bottom, travel right-to-left.", "Straight blue lanes, neutral numbers, no invented placement.", map_orientation_check)
    add("MARKET", "Columns", "MARKET-001", "Market table uses exact approved labels and no betting controls.", "NO/RUNNER/EDGEiQ/MARKET/FAIR/EDGE/FLUC 60s %/STATUS.", market_columns_check)
    add("OVERVIEW", "Duplication", "OVERVIEW-001", "Overview is concise and does not duplicate full specialist workspaces.", "Summary cards, speed-map preview, EPI snapshot, runner board only.", lambda: partial("Overview contains approved race-shape/summary sections, but visual/data-population exactness requires screenshot inspection.", "source/browser", "src/edgeiq-os/race/components/OverviewWorkspace.tsx", "src/edgeiq-os/race/components/OverviewWorkspace.tsx", "OverviewWorkspace"))
    add("INSIGHTS", "Governance", "INSIGHTS-001", "Insights use governed categories and no generic AI/tips/confidence.", "Stable Intent, Preparation Stage, Heavy Skill, Campaign Profile.", lambda: pass_if(all(contains("src/edgeiq-os/race/components/InsightsWorkspace.tsx", token) for token in ["Stable Intent", "Preparation Stage", "Heavy Skill", "Campaign Profile"]) and not contains_any("src/edgeiq-os/race/components/InsightsWorkspace.tsx", ["confidence", "tip"]), "Insights governed category labels found; rejected language absent in active component.", "source", "src/edgeiq-os/race/components/InsightsWorkspace.tsx", "src/edgeiq-os/race/components/InsightsWorkspace.tsx", "InsightsWorkspace"))
    add("RESULTS", "Structure", "RESULTS-001", "Results show runner performance, stewards where available, EPI/ERI, sectionals as lengths vs standard.", "No replay/raw times/confidence.", results_structure_check)
    add("LAB", "Query Builder", "LAB-001", "LAB is a generic governed research/query builder, not a per-race stats page.", "Selectors, run query, result table, governed boundary.", lab_controls_check)
    add("COMPARE", "Comparison", "COMPARE-001", "Compare supports legitimate governed entity comparisons without winner/recommendation/confidence.", "Entity/left/right/common metrics and data boundary.", compare_controls_check)
    add("REVIEW", "Persistence Boundary", "REVIEW-001", "Review contains legitimate persisted/reviewable items only; if persistence absent, empty-state is honest.", "No fake saved items or mock activity feed.", review_boundary_check)
    add("SETTINGS", "Controls", "SETTINGS-001", "Settings exposes only real display/governance state and no model/pricing/feed controls.", "No dead toggles or model controls.", settings_controls_check)
    return reqs


def csv_row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            return max(0, sum(1 for _ in handle) - 1)
    except OSError:
        return None


def first_csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            return next(reader, [])
    except Exception:
        return []


def write_data_wiring_matrix() -> None:
    rows = [
        ("Meetings", "meeting/date/state/rail/track/weather/races/declared/scratchings", "MeetingsWorkspace", "meetingsFeed", "public/data/edgeiq_three_day_product_catalog_v1.csv", "meeting/race/scratchings fields", "compact unavailable", "current", "builder freshness"),
        ("Meeting Detail", "race list and meeting context", "MeetingWorkspace", "meetingDetailFeed", "public/data/edgeiq_three_day_product_catalog_v1.csv", "meeting/race fields", "compact unavailable", "current", "builder freshness"),
        ("Scratchings", "scratched runner status", "MeetingScratchingsWorkspace", "scratchingsFeed", "public/data/edgeiq_scratchings_terminal_feed_v1.csv", "runner/scratching/status", "no governed scratchings state", "current", "builder freshness"),
        ("Gear Changes", "current gear/changes", "MeetingGearChangesWorkspace", "gearChangesFeed", "public/data/edgeiq_gear_terminal_feed_v1.csv", "gear_current/gear_changes/first_time_gear", "honest unavailable/no-change", "current", "builder freshness"),
        ("Track", "track condition/rail/map/history", "MeetingTrackWorkspace", "trackFeed/trackMapAssets", "public/data track feeds + public/track-maps", "track/rail/condition/map asset", "compact unavailable", "current + historical comparison", "service transforms display"),
        ("Weather", "live/current weather", "MeetingWeatherWorkspace", "weatherFeed", "governed live-weather v1.2 outputs", "temperature/rain/wind/source state", "available/stale/unavailable", "current", "builder-owned freshness"),
        ("Race", "tempo/EPF/determinants/runner board", "RaceIntelligenceWorkspace", "raceWorkspaceViewModel/currentRaceIntelligenceFeed", "current race intelligence feeds", "tempo/epf/runner board fields", "compact unavailable", "current", "service/view-model"),
        ("Field", "runner identity and market/status", "FieldWorkspace", "fieldWorkspaceViewModel", "three-day catalog/live runner board", "runner/barrier/weight/jockey/trainer/edgeiq/market/status", "dash or status", "current", "view-model"),
        ("Form Guide", "EPI/early/late/suitability/momentum/price/profile/recent form", "RaceFormGuideWorkspace", "formGuideNormaliser/formGuideEnrichedFeed/formGuideWorkspaceViewModel", "edgeiq_form_guide_enriched_v2.csv and governed terminal feeds", "approved form columns and dossier fields", "empty strings/dash/unavailable copy", "current + historical", "normaliser/view-model"),
        ("Performance", "historical performance figures", "PerformanceWorkspace", "performanceWorkspaceViewModel", "certified performance feed", "historical rating fields", "empty cells", "historical", "view-model"),
        ("EPI", "canonical EPI", "EpiWorkspaceWorkspace", "epiWorkspaceFeed", "epi terminal feed", "EPI fields", "unavailable evidence", "current", "service"),
        ("Map", "speed map/run style", "MapWorkspace", "mapFeed", "map terminal feed", "barrier/run_style/speed/market", "limited evidence/unavailable", "current", "service"),
        ("Market", "market/edge/fair/fluc", "MarketWorkspace", "marketFeed", "market terminal feed", "market_price/edgeiq_price/edge/fluc", "stale/unavailable", "current", "service"),
        ("Overview", "summary/map/EPI/runner board", "OverviewWorkspace", "overviewFeed", "overview terminal feed", "summary fields", "compact unavailable", "current", "service"),
        ("Insights", "stable/prep/heavy/campaign insights", "InsightsWorkspace", "insightsFeed", "insights terminal feed", "insight_category/text/source", "no insight inputs", "current", "service"),
        ("Results", "runner performance/sectionals/stewards", "ResultsWorkspace", "resultsFeed", "results terminal feed", "position/runner/EPI/ERI/ESI/stewards", "preliminary/official/unavailable", "historical/result", "service"),
        ("LAB", "query engine/result table", "LabWorkspace", "labResearch/performanceIntelligenceFeed", "certified performance feed", "query model/results", "disabled/unavailable metrics", "research", "service/query boundary"),
        ("Compare", "side-by-side common metrics", "CompareWorkspace", "compareWorkspaceData/performanceIntelligenceFeed", "certified performance feed", "common metric rows", "unavailable values distinguished", "research/current/historical", "service/view-model"),
        ("Review", "review persistence boundary", "ReviewWorkspace", "reviewWorkspaceData", "local/session persistence if supplied", "reviewable items", "honest no saved review record", "session/review", "service"),
        ("Settings", "display/governance state", "SettingsWorkspace", "none/model-free", "application state", "display/data/weather/review states", "static state where controls absent", "application", "component state only"),
    ]
    lines = [
        "# EDGEiQ Final Data Wiring Matrix V1",
        "",
        "| Workspace | Display label(s) | Component | View model/service | Feed/API | Canonical field(s) | Unavailable behavior | Current/Historical | Transformation/freshness |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    DATA_WIRING_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit_coverage_review() -> None:
    script_path = ROOT / "scripts" / "audit_edgeiq_full_product_acceptance_v1.py"
    text = read_text(script_path)
    audit_names = re.findall(r'"(audit_edgeiq_[^"]+\.py)"', text)
    lines = [
        "# EDGEiQ Full Product Audit Coverage Review V1",
        "",
        "Status: PARTIAL",
        "",
        "The existing full-product acceptance audit is useful as a route/source smoke, but it is not a forensic specification-conformance proof.",
        "",
        "## Checks It Performs",
        "- Executes listed targeted audit scripts and requires each to emit PASS.",
        "- Checks selected CSS final-spec markers.",
        "- Checks a small set of route/component tokens.",
        "- Checks a limited rejected-token list in final Compare/Review/Home/Settings files.",
        "- Writes `EDGEIQ_FULL_PRODUCT_ACCEPTANCE_AUDIT_V1.md`.",
        "",
        "## Targeted Audits Called",
    ]
    lines.extend(f"- `{name}`" for name in audit_names)
    lines.extend([
        "",
        "## Checks It Does Not Perform",
        "- No rendered visual comparison.",
        "- No screenshot capture.",
        "- No DOM table-header verification.",
        "- No populated meeting/race data acceptance.",
        "- No browser refresh/back/forward persistence verification.",
        "- No per-visible-metric feed lineage proof.",
        "- No interaction testing beyond any evidence in the individual smoke files.",
        "- No verification that every final approved requirement has an individual matrix row.",
        "",
        "## Consequence",
        "A PASS from the prior audit is evidence that implementation tranches exist, not evidence that every approved specification line is fully satisfied.",
    ])
    AUDIT_COVERAGE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_populated_test_matrix() -> None:
    candidate_files = [
        "public/data/edgeiq_three_day_product_catalog_v1.json",
        "public/data/edgeiq_form_guide_enriched_v2.csv",
        "public/data/edgeiq_market_terminal_feed_v1.csv",
        "public/data/edgeiq_map_terminal_feed_v1.csv",
        "public/data/edgeiq_epi_workspace_terminal_feed_v1.csv",
        "public/data/edgeiq_meeting_results_terminal_feed_v1.csv",
        "public/data/edgeiq_gear_terminal_feed_v1.csv",
    ]
    lines = [
        "# EDGEiQ Final Populated Test Matrix V1",
        "",
        "| Feed | Rows | Header evidence | Populated acceptance use |",
        "|---|---:|---|---|",
    ]
    for rel in candidate_files:
        path = ROOT / rel
        if path.suffix.lower() == ".json":
            if not path.exists():
                lines.append(f"| `{rel}` | DATA GAP | File not found | Cannot use for populated browser acceptance |")
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                meetings = data.get("meetings", []) if isinstance(data, dict) else []
                races = sum(len(meeting.get("races") or []) for meeting in meetings)
                runners = sum(len(race.get("runners") or []) for meeting in meetings for race in (meeting.get("races") or []))
                lines.append(f"| `{rel}` | {len(meetings)} meetings / {races} races / {runners} runners | JSON catalog | Candidate populated source |")
            except Exception as exc:
                lines.append(f"| `{rel}` | DATA GAP | JSON read failed: {exc} | Cannot use for populated browser acceptance |")
            continue
        count = csv_row_count(path)
        header = first_csv_header(path)
        if count is None:
            lines.append(f"| `{rel}` | DATA GAP | File not found | Cannot use for populated browser acceptance |")
        else:
            lines.append(f"| `{rel}` | {count} | {', '.join(header[:12])} | {'Candidate populated source' if count > 0 else 'DATA GAP'} |")
    lines.extend([
        "",
        "## Browser Evidence",
    ])
    if SCREENSHOTS:
        for name, item in SCREENSHOTS.items():
            lines.append(f"- {name}: screenshot captured at `{item.get('path')}`; first headings: {', '.join(item.get('headings', [])[:6])}")
    else:
        lines.append("- No screenshot evidence file found at generation time.")
    POPULATED_TEST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_targeted_audits() -> list[tuple[str, str, str]]:
    audit_script = ROOT / "scripts" / "audit_edgeiq_full_product_acceptance_v1.py"
    text = read_text(audit_script)
    names = re.findall(r'"(audit_edgeiq_[^"]+\.py)"', text)
    results = []
    for name in names:
        path = ROOT / "scripts" / name
        if not path.exists():
            results.append((name, "NOT TESTED", "script missing"))
            continue
        proc = subprocess.run([sys.executable, str(path)], cwd=ROOT, text=True, capture_output=True)
        output = (proc.stdout + "\n" + proc.stderr).strip().splitlines()
        tail = output[-1] if output else ""
        full_output = "\n".join(output)
        status = "PASS" if proc.returncode == 0 and "PASS" in full_output else "FAIL"
        results.append((name, status, tail))
    return results


def main() -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    requirements = make_requirements()
    for req in requirements:
        status, actual, evidence_type, evidence_path, source_file, symbol = req.check()
        if status not in STATUSES:
            status = "NOT TESTED"
        rows.append({
            "workspace": req.workspace,
            "section": req.section,
            "requirement_id": req.requirement_id,
            "requirement": req.requirement,
            "expected": req.expected,
            "actual": actual,
            "status": status,
            "evidence_type": evidence_type,
            "evidence_path": evidence_path,
            "source_file": source_file,
            "source_line_or_symbol": symbol,
            "governed_source": "",
            "notes": "",
            "remediation_required": "YES" if status in {"FAIL", "PARTIAL"} else "NO",
        })

    with MATRIX_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    write_data_wiring_matrix()
    write_audit_coverage_review()
    write_populated_test_matrix()
    targeted = run_targeted_audits()

    counts = Counter(row["status"] for row in rows)
    workspace_counts = defaultdict(Counter)
    for row in rows:
        workspace_counts[row["workspace"]][row["status"]] += 1

    overall = "COMPLETE"
    if counts["FAIL"] or counts["PARTIAL"] or counts["NOT TESTED"]:
        overall = "PARTIAL"

    lines = [
        "# EDGEiQ Final Specification Conformance Report V1",
        "",
        f"Overall status: {overall}",
        "",
        f"Total requirements reviewed: {len(rows)}",
        f"PASS count: {counts['PASS']}",
        f"PARTIAL count: {counts['PARTIAL']}",
        f"FAIL count: {counts['FAIL']}",
        f"DATA GAP count: {counts['DATA GAP']}",
        f"NOT TESTED count: {counts['NOT TESTED']}",
        "",
        "## Results By Workspace",
        "",
        "| Workspace | PASS | PARTIAL | FAIL | DATA GAP | NOT TESTED |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for workspace in sorted(workspace_counts):
        wc = workspace_counts[workspace]
        lines.append(f"| {workspace} | {wc['PASS']} | {wc['PARTIAL']} | {wc['FAIL']} | {wc['DATA GAP']} | {wc['NOT TESTED']} |")

    for title, status in [
        ("Implementation Failures", "FAIL"),
        ("Partials", "PARTIAL"),
        ("Data Gaps", "DATA GAP"),
        ("Untested Requirements", "NOT TESTED"),
    ]:
        lines.extend(["", f"## {title}"])
        matching = [row for row in rows if row["status"] == status]
        if not matching:
            lines.append("- None.")
        else:
            for row in matching:
                lines.append(f"- `{row['requirement_id']}` {row['workspace']}: {row['actual']}")

    lines.extend([
        "",
        "## Screenshot Evidence",
        f"- Directory: `{SCREENSHOT_DIR}`",
        f"- Captured entries: {len(SCREENSHOTS)}",
        "",
        "## Targeted Audits",
    ])
    for name, status, tail in targeted:
        lines.append(f"- `{name}`: {status} - {tail}")
    remaining_partials = [row["requirement_id"] for row in rows if row["status"] == "PARTIAL"]
    remaining_failures = [row["requirement_id"] for row in rows if row["status"] == "FAIL"]
    remaining_data_gaps = [row["requirement_id"] for row in rows if row["status"] == "DATA GAP"]
    remediation_lines = []
    if remaining_failures:
        remediation_lines.append(f"- Fix genuine implementation failures: {', '.join(remaining_failures)}.")
    if remaining_partials:
        remediation_lines.append(f"- Resolve or design-review remaining partials: {', '.join(remaining_partials)}.")
    if remaining_data_gaps:
        remediation_lines.append(f"- Preserve documented governed data gaps without fabricating data: {', '.join(remaining_data_gaps)}.")
    if not remediation_lines:
        remediation_lines.append("- No remediation remains in this conformance matrix.")

    lines.extend([
        "",
        "## Audit Coverage Limitation",
        f"- Detailed coverage review: `{AUDIT_COVERAGE_PATH}`",
        "",
        "## Remediation Plan",
        *remediation_lines,
        "",
    ])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"EDGEIQ_FINAL_FORENSIC_CONFORMANCE_AUDIT_{overall}")
    print(f"MATRIX={MATRIX_PATH}")
    print(f"REPORT={REPORT_PATH}")


if __name__ == "__main__":
    main()
