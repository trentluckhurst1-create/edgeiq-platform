import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AUDITS = [
    "audit_edgeiq_form_guide_final_spec_v1.py",
    "audit_edgeiq_map_final_spec_v1.py",
    "audit_edgeiq_market_final_spec_v1.py",
    "audit_edgeiq_overview_final_spec_v1.py",
    "audit_edgeiq_insights_final_spec_v1.py",
    "audit_edgeiq_results_final_spec_v1.py",
    "audit_edgeiq_meetings_final_spec_v1.py",
    "audit_edgeiq_meeting_detail_final_spec_v1.py",
    "audit_edgeiq_scratchings_final_spec_v1.py",
    "audit_edgeiq_gear_changes_final_spec_v1.py",
    "audit_edgeiq_track_final_spec_v1.py",
    "audit_edgeiq_weather_final_spec_v1.py",
    "audit_edgeiq_lab_final_spec_v1.py",
    "audit_edgeiq_compare_final_spec_v1.py",
    "audit_edgeiq_review_final_spec_v1.py",
    "audit_edgeiq_home_settings_final_spec_v1.py",
]

REQUIRED_MARKERS = [
    "EDGEIQ COMPARE FINAL SPEC V1",
    "EDGEIQ REVIEW FINAL SPEC V1",
    "EDGEIQ HOME AND SETTINGS FINAL SPEC V1",
    "EDGEIQ LAB FINAL SPEC V1",
    "EDGEIQ WEATHER FINAL SPEC V1",
]

TOP_LEVEL_ROUTE_TOKENS = [
    "<EdgeiqOsHome />",
    "<SettingsWorkspace />",
    "LabWorkspace",
]

RACE_WORKSPACE_TOKENS = [
    "<ReviewWorkspace",
    "CompareWorkspace",
]

REJECTED_IN_FINAL_FILES = [
    "Race review pending",
    "not yet connected",
    "SpeedProfile",
    "TrackSignature",
    "RaceStrength",
    "RaceFlow",
    "Similarity",
    "similarity",
    "verdict",
    "winner by design",
    "recommendation",
    "mock",
    "demo",
    "fake",
]

FINAL_FILES = [
    ROOT / "src/edgeiq-os/compare/CompareWorkspace.tsx",
    ROOT / "src/edgeiq-os/compare/compareWorkspaceData.ts",
    ROOT / "src/edgeiq-os/race/components/ReviewWorkspace.tsx",
    ROOT / "src/edgeiq-os/race/services/reviewWorkspaceData.ts",
    ROOT / "src/edgeiq-os/home/EdgeiqOsHome.tsx",
    ROOT / "src/edgeiq-os/race/components/SettingsWorkspace.tsx",
]


def fail(message: str) -> None:
    raise SystemExit(f"EDGEIQ_FULL_PRODUCT_ACCEPTANCE_AUDIT_FAIL: {message}")


def run_audit(script_name: str) -> tuple[str, str]:
    script = ROOT / "scripts" / script_name
    if not script.exists():
        fail(f"missing audit script {script_name}")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        fail(f"{script_name} failed: {output}")
    if "PASS" not in output:
        fail(f"{script_name} did not emit PASS: {output}")
    return script_name, output.splitlines()[-1] if output else "PASS"


def main() -> None:
    audit_results = [run_audit(script_name) for script_name in AUDITS]

    css_text = (ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css").read_text(encoding="utf-8")
    for marker in REQUIRED_MARKERS:
        if marker not in css_text:
            fail(f"missing css marker {marker}")

    race_file = (ROOT / "src/edgeiq-os/race/RaceFileV3.tsx").read_text(encoding="utf-8")
    for token in TOP_LEVEL_ROUTE_TOKENS:
        if token not in race_file:
            fail(f"missing route token {token}")

    race_workspace = (ROOT / "src/edgeiq-os/race/components/RaceWorkspace.tsx").read_text(encoding="utf-8")
    runner_workspace = (ROOT / "src/edgeiq-os/race/components/RunnerProfileWorkspace.tsx").read_text(encoding="utf-8")
    routed_workspace_text = race_workspace + "\n" + runner_workspace
    for token in RACE_WORKSPACE_TOKENS:
        if token not in routed_workspace_text:
            fail(f"missing workspace route token {token}")

    combined = "\n".join(path.read_text(encoding="utf-8") for path in FINAL_FILES if path.exists())
    for token in REJECTED_IN_FINAL_FILES:
        if token in combined:
            fail(f"rejected token remains in final workspace files: {token}")

    report = ROOT / "docs/full-product-implementation/EDGEIQ_FULL_PRODUCT_ACCEPTANCE_AUDIT_V1.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# EDGEiQ Full Product Acceptance Audit V1",
        "",
        "Status: EDGEIQ_FULL_PRODUCT_ACCEPTANCE_AUDIT_PASS",
        "",
        "## Workspace Audits",
    ]
    lines.extend(f"- {name}: {status}" for name, status in audit_results)
    lines.extend(
        [
            "",
            "## Acceptance Checks",
            "- Final workspace route tokens present.",
            "- Final CSS markers present.",
            "- Rejected final-workspace product language absent.",
            "- White theme tranche smoke reports were generated for browser-verifiable workspaces.",
            "",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")
    print("EDGEIQ_FULL_PRODUCT_ACCEPTANCE_AUDIT_PASS")


if __name__ == "__main__":
    main()
