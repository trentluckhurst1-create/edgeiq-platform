from pathlib import Path
import csv
import json
from datetime import datetime

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
RUNTIME_DIR = ROOT / "docs" / "full-product-implementation" / "screenshots" / "final-live-runtime"
RESOLUTION = ROOT / "docs" / "full-product-implementation" / "FINAL_LIVE_COMPONENT_RESOLUTION.csv"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "FINAL_LIVE_RUNTIME_COMPLETION_AUDIT_V1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "FINAL_LIVE_RUNTIME_COMPLETION_AUDIT_V1.md"

EXPECTED = {
    "01_HOME": ("HOME", "EdgeiqOsHome", ["EDGEIQ", "HOME", "MEETINGS"]),
    "02_MEETINGS": ("MEETINGS", "MeetingsWorkspace", ["MEETINGS", "OPEN MEETING", "RACES"]),
    "03_RACE_OVERVIEW": ("RACE", "RaceIntelligenceWorkspace", ["RACE SUMMARY", "RACE CONDITIONS", "MEETING INFORMATION"]),
    "04_FIELD": ("FIELD", "FieldWorkspace", ["FIELD", "RUNNER", "JOCKEY", "TRAINER"]),
    "05_FORM_GUIDE": ("FORM GUIDE", "RaceFormGuideWorkspace", ["FORM GUIDE", "LAST 5", "RUNNER"]),
    "06_PERFORMANCE": ("PERFORMANCE", "PerformanceWorkspace", ["PERFORMANCE MATRIX", "FIELD EPI MATRIX", "SECTIONALS"]),
    "07_MAP": ("MAP", "MapWorkspace", ["MAP", "BARRIER", "PACE"]),
    "08_EPI": ("EPI", "EpiWorkspaceWorkspace", ["EPI MATRIX", "CURRENT EPI", "RACE RANK"]),
    "09_MARKET": ("MARKET", "MarketWorkspace", ["MARKET", "EDGEIQ", "RUNNER"]),
    "10_OVERVIEW": ("OVERVIEW", "OverviewWorkspace", ["OVERVIEW", "RUNNER BOARD", "TEMPO PROFILE"]),
    "11_SCRATCHINGS": ("SCRATCHINGS", "MeetingScratchingsWorkspace", ["SCRATCHINGS", "FIELD"]),
    "12_GEAR_CHANGES": ("GEAR_CHANGES", "MeetingGearChangesWorkspace", ["GEAR", "RUNNER"]),
    "13_TRACK": ("TRACK", "MeetingTrackWorkspace", ["TRACK", "RAIL"]),
    "14_WEATHER": ("WEATHER", "MeetingWeatherWorkspace", ["WEATHER", "WIND"]),
    "15_RESULTS": ("RESULTS", "RaceResultsWorkspace", ["OFFICIAL FINISHING ORDER", "RUNNER PERFORMANCE SNAPSHOT", "REVIEW NOTES"]),
    "16_INSIGHTS": ("INSIGHTS", "InsightsWorkspace", ["INSIGHTS", "STABLE INTENT", "CAMPAIGN PROFILE"]),
    "17_LAB": ("LAB", "LabWorkspace", ["STATS ENGINE", "QUERY BUILDER", "RUN QUERY"]),
    "18_COMPARE": ("COMPARE", "CompareWorkspace", ["COMPARE", "LEFT", "RIGHT"]),
    "19_REVIEW": ("REVIEW", "ReviewWorkspace", ["SECTIONAL AND PERFORMANCE REVIEW", "REVIEW STRUCTURE", "STEWARDS"]),
}

FORBIDDEN_TEXT = [
    "Back/Lay",
    "Governed EPI workspace rows are not available for this race.",
    "Governed overview rows are not available for this race.",
    "Governed insight rows are not available for this race.",
    "Governed historical performance rows are not available for this race.",
    "Race review workspace",
    "Available product state",
    "Racing Research Laboratory",
    "Runner pending",
    "\ufffd",
    "â",
    "Â",
    "Ã",
]

rows = []
failures = []

def add_check(scope, check, expected, actual, status, detail=""):
    rows.append({
        "scope": scope,
        "check": check,
        "expected": str(expected),
        "actual": str(actual),
        "status": status,
        "detail": detail,
    })
    if status != "PASS":
        failures.append(f"{scope}::{check} {detail}".strip())

summary_path = RUNTIME_DIR / "EDGEIQ_FINAL_LIVE_RUNTIME_CAPTURE_V1_SUMMARY.json"
summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
add_check("capture", "status", "EDGEIQ_FINAL_LIVE_RUNTIME_CAPTURE_COMPLETE", summary.get("status"), "PASS" if summary.get("status") == "EDGEIQ_FINAL_LIVE_RUNTIME_CAPTURE_COMPLETE" else "FAIL")
add_check("capture", "workspace_count", 19, summary.get("workspace_count"), "PASS" if summary.get("workspace_count") == 19 else "FAIL")
add_check("capture", "capture_errors", 0, summary.get("capture_error_count"), "PASS" if summary.get("capture_error_count") == 0 else "FAIL")

for suffix, expected_count in [
    ("_LIVE_RENDERED.png", 19),
    ("_APPROVED.png", 19),
    ("_OVERLAY.png", 19),
    ("_DIFF.png", 19),
    ("_SIDE_BY_SIDE.png", 19),
    ("_MATERIAL_REGIONS.png", 19),
    ("_LIVE_RUNTIME.json", 19),
    ("_COMPARISON.json", 19),
]:
    count = len(list(RUNTIME_DIR.glob(f"*{suffix}")))
    add_check("artifacts", suffix, expected_count, count, "PASS" if count == expected_count else "FAIL")

if RESOLUTION.exists():
    with RESOLUTION.open("r", encoding="utf-8-sig", newline="") as f:
        resolution_rows = list(csv.DictReader(f))
    add_check("resolution", "rows", 19, len(resolution_rows), "PASS" if len(resolution_rows) == 19 else "FAIL")
    bad = [r for r in resolution_rows if r.get("Match") != "PASS"]
    add_check("resolution", "all_pass", 0, len(bad), "PASS" if not bad else "FAIL")
else:
    add_check("resolution", "exists", True, False, "FAIL")

for workspace, (expected_key, expected_component, required_tokens) in EXPECTED.items():
    runtime_path = RUNTIME_DIR / f"{workspace}_LIVE_RUNTIME.json"
    if not runtime_path.exists():
        add_check(workspace, "runtime_json_exists", True, False, "FAIL")
        continue
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    body = str(runtime.get("bodySample") or "")
    body_upper = body.upper()
    add_check(workspace, "mounted_component", expected_component, runtime.get("mountedComponent"), "PASS" if runtime.get("mountedComponent") == expected_component else "FAIL")
    add_check(workspace, "mounted_key", expected_key, runtime.get("mountedKey"), "PASS" if runtime.get("mountedKey") == expected_key else "FAIL")
    add_check(workspace, "capture_errors", 0, len(runtime.get("captureErrors") or []), "PASS" if not runtime.get("captureErrors") else "FAIL")
    add_check(workspace, "body_sample_present", ">=800 chars", len(body), "PASS" if len(body) >= 800 else "FAIL")
    for token in required_tokens:
        add_check(workspace, f"required_token:{token}", "present", token in body_upper, "PASS" if token in body_upper else "FAIL")
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in body:
            add_check(workspace, f"forbidden_text:{forbidden}", "absent", "present", "FAIL")

# Source-level guard for the specific miswires from this task.
race_file = (ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx").read_text(encoding="utf-8")
add_check("source", "compare_component_import", "CompareWorkspace import", "CompareWorkspace" in race_file, "PASS" if "CompareWorkspace" in race_file else "FAIL")
add_check("source", "results_race_tab_mapping", "results: RESULTS", 'results: "RESULTS"' in race_file, "PASS" if 'results: "RESULTS"' in race_file else "FAIL")
runner_section = race_file.split("const runnerModeBySection", 1)[1].split("};", 1)[0].lower() if "const runnerModeBySection" in race_file else ""
runner_compare_ok = "const runnerModeBySection" in race_file and "compare" not in runner_section
add_check("source", "no_runner_compare_reroute", "runnerModeBySection has no compare route", runner_compare_ok, "PASS" if runner_compare_ok else "FAIL")

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["scope", "check", "expected", "actual", "status", "detail"])
    writer.writeheader()
    writer.writerows(rows)

status = "EDGEIQ_FINAL_LIVE_RUNTIME_COMPLETION_PASS" if not failures else "EDGEIQ_FINAL_LIVE_RUNTIME_COMPLETION_FAIL"
lines = [
    f"# EDGEiQ Final Live Runtime Completion Audit V1",
    "",
    f"Generated: {datetime.now().isoformat(timespec='seconds')}",
    f"Status: {status}",
    f"Checks: {len(rows)}",
    f"Failures: {len(failures)}",
    "",
]
if failures:
    lines.append("## Failures")
    lines.extend(f"- {failure}" for failure in failures[:80])
else:
    lines.extend([
        "## Result",
        "All 19 approved workspaces resolve to the expected live mounted component.",
        "Live-rendered, approved, overlay, diff, side-by-side, material-region, runtime JSON and comparison artifacts are present for every workspace.",
        "The previously ambiguous COMPARE and RESULTS routes are resolved.",
        "Sparse one-line EPI, Performance, Overview and Insights fallback screens are replaced by structured product workspaces using existing field context only.",
    ])
OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(status)
print(f"checks={len(rows)} failures={len(failures)}")
print(f"csv={OUT_CSV}")
print(f"report={OUT_MD}")
if failures:
    raise SystemExit(1)
