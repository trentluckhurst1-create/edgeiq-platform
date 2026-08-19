from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
VISUALS = DATA / "visual_audits"
OUT_JSON = DATA / "edgeiq_remaining_beta_autonomous_completion_v1_audit.json"
OUT_TXT = DATA / "edgeiq_remaining_beta_autonomous_completion_v1_audit.txt"
OUT_INV = DATA / "edgeiq_remaining_beta_autonomous_completion_v1_inventory.csv"

WORKSPACES = {
    "Gear Changes": "edgeiq_gear_changes_engineering_build_v1_audit.txt",
    "Track": "edgeiq_track_engineering_build_v1_audit.txt",
    "Weather": "edgeiq_weather_engineering_build_v1_audit.txt",
    "Results": "edgeiq_results_engineering_build_v1_audit.txt",
    "MAP": "edgeiq_map_engineering_build_v1_audit.txt",
    "Market": "edgeiq_market_engineering_build_v1_audit.txt",
    "Overview": "edgeiq_overview_engineering_build_v1_audit.txt",
    "Insights": "edgeiq_insights_engineering_build_v1_audit.txt",
    "EPI Workspace": "edgeiq_epi_workspace_engineering_build_v1_audit.txt",
}

SCREENSHOT_PREFIXES = {
    "Gear Changes": "edgeiq_gear_changes_engineering_v1_",
    "Track": "edgeiq_track_engineering_v1_",
    "Weather": "edgeiq_weather_engineering_v1_",
    "Results": "edgeiq_results_engineering_v1_",
    "MAP": "edgeiq_map_engineering_v1_",
    "Market": "edgeiq_market_engineering_v1_",
    "Overview": "edgeiq_overview_engineering_v1_",
    "Insights": "edgeiq_insights_engineering_v1_",
    "EPI Workspace": "edgeiq_epi_workspace_engineering_v1_",
}

BASELINE_AUDITS = {
    "Specification Library": "edgeiq_engineering_specification_library_v1_audit.txt",
    "Form Guide": "edgeiq_form_guide_engineering_build_v1_audit.txt",
    "Meetings": "edgeiq_meetings_engineering_build_v1_audit.txt",
    "Meeting Detail": "edgeiq_meeting_detail_engineering_build_v1_audit.txt",
    "Scratchings": "edgeiq_scratchings_engineering_build_v1_audit.txt",
    "Current Intelligence": "edgeiq_current_intelligence_v1_1_audit.txt",
    "Speed Projection": "edgeiq_current_speed_projection_v1_audit.txt",
    "Beta Intelligence": "edgeiq_beta_intelligence_completion_v1_audit.txt",
    "Light Design System": "edgeiq_light_design_system_v3_audit_summary.csv",
}


def audit_status(path: Path, expected: str) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    return expected in text, text.splitlines()[0] if text.splitlines() else ""


inventory_rows: list[dict[str, str]] = []
workspace_results: dict[str, dict[str, object]] = {}
for workspace, audit_file in WORKSPACES.items():
    expected = f"EDGEIQ_{workspace.upper().replace(' ', '_')}_ENGINEERING_BUILD_V1_AUDIT_PASS"
    if workspace == "MAP":
        expected = "EDGEIQ_MAP_ENGINEERING_BUILD_V1_AUDIT_PASS"
    if workspace == "EPI Workspace":
        expected = "EDGEIQ_EPI_WORKSPACE_ENGINEERING_BUILD_V1_AUDIT_PASS"
    audit_path = DATA / audit_file
    audit_pass, first_line = audit_status(audit_path, expected)
    screenshots = sorted(path.name for path in VISUALS.glob(f"{SCREENSHOT_PREFIXES[workspace]}*.png")) if VISUALS.exists() else []
    workspace_results[workspace] = {
        "audit_file": str(audit_path),
        "audit_pass": audit_pass,
        "audit_status": first_line,
        "screenshots": screenshots,
        "screenshots_present": bool(screenshots),
    }
    inventory_rows.append(
        {
            "workspace": workspace,
            "audit": str(audit_path),
            "audit_pass": str(audit_pass),
            "screenshots": str(len(screenshots)),
            "status": "PASS" if audit_pass and screenshots else "FAIL",
        }
    )

baseline_results: dict[str, dict[str, object]] = {}
for name, audit_file in BASELINE_AUDITS.items():
    path = DATA / audit_file
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if name == "Light Design System" and path.exists():
        pass_detected = "PASS" in text
        first_line = "EDGEIQ_LIGHT_DESIGN_SYSTEM_V3_AUDIT_PASS" if pass_detected else text.splitlines()[0] if text.splitlines() else ""
    else:
        pass_detected = "PASS" in text
        first_line = text.splitlines()[0] if text.splitlines() else ""
    baseline_results[name] = {
        "audit_file": str(path),
        "exists": path.exists(),
        "pass_detected": pass_detected,
        "first_line": first_line,
    }

all_workspace_pass = all(result["audit_pass"] and result["screenshots_present"] for result in workspace_results.values())
all_baseline_pass = all(result["exists"] and result["pass_detected"] for result in baseline_results.values())
status = "EDGEIQ_REMAINING_BETA_AUTONOMOUS_COMPLETION_V1_PASS" if all_workspace_pass and all_baseline_pass else "EDGEIQ_REMAINING_BETA_AUTONOMOUS_COMPLETION_V1_PARTIAL_PASS"

payload = {
    "status": status,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "workspace_results": workspace_results,
    "baseline_results": baseline_results,
    "checks": {
        "all_workspace_audits_and_screenshots_pass": all_workspace_pass,
        "all_baseline_audits_pass": all_baseline_pass,
    },
}

OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join(
        [
            status,
            "",
            "Workspace Status:",
            *[
                f"{name}: audit={result['audit_pass']} screenshots={len(result['screenshots'])}"
                for name, result in workspace_results.items()
            ],
            "",
            "Baseline Status:",
            *[
                f"{name}: pass={result['pass_detected']}"
                for name, result in baseline_results.items()
            ],
        ]
    ),
    encoding="utf-8",
)
with OUT_INV.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["workspace", "audit", "audit_pass", "screenshots", "status"])
    writer.writeheader()
    writer.writerows(inventory_rows)

print(status)
if status.endswith("PARTIAL_PASS"):
    raise SystemExit(1)
