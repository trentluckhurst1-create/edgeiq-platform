from __future__ import annotations

from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs" / "engineering"
OUTPUT = DOCS / "EDGEIQ_RECENT_SCRIPT_STATUS_20260715.md"


SCRIPT_ROWS = [
    {
        "script": "scripts/apply_edgeiq_meeting_races_cleanup_v1.py",
        "status": "SUPERSEDED",
        "safe": "NO",
        "purpose": "Early Meeting Races cleanup attempt.",
        "notes": "Superseded by compile, selected-state, and final-polish scripts. Do not rerun because it was written against an older MeetingWorkspace shape.",
    },
    {
        "script": "scripts/fix_edgeiq_meeting_races_compile_v1.py",
        "status": "SUPERSEDED",
        "safe": "NO",
        "purpose": "Removed compile errors from the first Meeting Races cleanup.",
        "notes": "This fixed stale race-number references but is superseded by the selected-state repair and final v2 polish.",
    },
    {
        "script": "scripts/fix_edgeiq_meeting_selected_state_v1.py",
        "status": "APPLIED",
        "safe": "NO",
        "purpose": "Restored selected-race state through buildMeetingDetailSelectedRace.",
        "notes": "Current MeetingWorkspace depends on this architecture. Preserve the outcome; do not rerun as a broad repair script.",
    },
    {
        "script": "scripts/apply_edgeiq_meeting_races_final_polish_v1.py",
        "status": "FAILED / SUPERSEDED",
        "safe": "NO",
        "purpose": "First final-polish attempt for Meeting Races.",
        "notes": "Validation assumptions were stale. Superseded by apply_edgeiq_meeting_races_final_polish_v2.py.",
    },
    {
        "script": "scripts/patch_meeting_condition_labels_v1.py",
        "status": "FAILED / SUPERSEDED",
        "safe": "NO",
        "purpose": "Attempted condition label shortening.",
        "notes": "Superseded by v2 render-only label mapping in MeetingWorkspace.",
    },
    {
        "script": "scripts/apply_edgeiq_meeting_races_final_polish_v2.py",
        "status": "APPLIED / ACTIVE",
        "safe": "CONDITIONAL",
        "purpose": "Final locked Meeting Races polish: duplicate header removal, condition label cleanup, seven-column race table lock, CSS alignment.",
        "notes": "Current canonical Meeting Races polish. Rerun only after inspecting current source and expecting either a safe refusal or identical output.",
    },
    {
        "script": "scripts/audit_edgeiq_meeting_races_final_polish_v2.py",
        "status": "PASS",
        "safe": "YES",
        "purpose": "Static audit for the locked Meeting Races polish.",
        "notes": "Expected pass marker: EDGEIQ_MEETING_RACES_FINAL_POLISH_V2_AUDIT_PASS.",
    },
    {
        "script": "scripts/apply_edgeiq_recent_workspace_regression_fixes_v1.py",
        "status": "APPLIED / ACTIVE",
        "safe": "CONDITIONAL",
        "purpose": "Removed visible rejected Scratchings diagnostics, removed Track source column, and changed missing Results sectional cells to dash.",
        "notes": "Current canonical regression fix. Rerun only after inspecting current source.",
    },
    {
        "script": "scripts/audit_edgeiq_recent_workspace_regression_v1.py",
        "status": "PASS",
        "safe": "YES",
        "purpose": "Static regression audit for Scratchings, Gear, Track, Weather, Results, and Meeting selected-race state.",
        "notes": "Expected pass marker: EDGEIQ_RECENT_WORKSPACE_REGRESSION_V1_AUDIT_PASS.",
    },
]


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# EDGEiQ Recent Script Status - 2026-07-15",
        "",
        f"Generated: {generated}",
        "",
        "This manifest records the current status of recent Meeting Workspace repair scripts so stale scripts are not reused accidentally.",
        "",
        "| Script | Status | Safe to rerun | Purpose | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]

    for row in SCRIPT_ROWS:
        lines.append(
            "| {script} | {status} | {safe} | {purpose} | {notes} |".format(
                script=row["script"],
                status=row["status"],
                safe=row["safe"],
                purpose=row["purpose"],
                notes=row["notes"],
            )
        )

    lines.extend(
        [
            "",
            "## Current Canonical Path",
            "",
            "- Meeting Races visual and state lock: `apply_edgeiq_meeting_races_final_polish_v2.py` plus `audit_edgeiq_meeting_races_final_polish_v2.py`.",
            "- Cross-workspace regression lock: `apply_edgeiq_recent_workspace_regression_fixes_v1.py` plus `audit_edgeiq_recent_workspace_regression_v1.py`.",
            "- Do not restore pre-weather checkpoints over `MeetingWeatherWorkspace.tsx` or `weatherFeed.ts`; live on-track weather v1.2 integration is preserved.",
            "",
        ]
    )

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote={OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
