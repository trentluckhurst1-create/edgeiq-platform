# EDGEiQ Recent Script Status - 2026-07-15

Generated: 2026-07-15 12:25:56

This manifest records the current status of recent Meeting Workspace repair scripts so stale scripts are not reused accidentally.

| Script | Status | Safe to rerun | Purpose | Notes |
| --- | --- | --- | --- | --- |
| scripts/apply_edgeiq_meeting_races_cleanup_v1.py | SUPERSEDED | NO | Early Meeting Races cleanup attempt. | Superseded by compile, selected-state, and final-polish scripts. Do not rerun because it was written against an older MeetingWorkspace shape. |
| scripts/fix_edgeiq_meeting_races_compile_v1.py | SUPERSEDED | NO | Removed compile errors from the first Meeting Races cleanup. | This fixed stale race-number references but is superseded by the selected-state repair and final v2 polish. |
| scripts/fix_edgeiq_meeting_selected_state_v1.py | APPLIED | NO | Restored selected-race state through buildMeetingDetailSelectedRace. | Current MeetingWorkspace depends on this architecture. Preserve the outcome; do not rerun as a broad repair script. |
| scripts/apply_edgeiq_meeting_races_final_polish_v1.py | FAILED / SUPERSEDED | NO | First final-polish attempt for Meeting Races. | Validation assumptions were stale. Superseded by apply_edgeiq_meeting_races_final_polish_v2.py. |
| scripts/patch_meeting_condition_labels_v1.py | FAILED / SUPERSEDED | NO | Attempted condition label shortening. | Superseded by v2 render-only label mapping in MeetingWorkspace. |
| scripts/apply_edgeiq_meeting_races_final_polish_v2.py | APPLIED / ACTIVE | CONDITIONAL | Final locked Meeting Races polish: duplicate header removal, condition label cleanup, seven-column race table lock, CSS alignment. | Current canonical Meeting Races polish. Rerun only after inspecting current source and expecting either a safe refusal or identical output. |
| scripts/audit_edgeiq_meeting_races_final_polish_v2.py | PASS | YES | Static audit for the locked Meeting Races polish. | Expected pass marker: EDGEIQ_MEETING_RACES_FINAL_POLISH_V2_AUDIT_PASS. |
| scripts/apply_edgeiq_recent_workspace_regression_fixes_v1.py | APPLIED / ACTIVE | CONDITIONAL | Removed visible rejected Scratchings diagnostics, removed Track source column, and changed missing Results sectional cells to dash. | Current canonical regression fix. Rerun only after inspecting current source. |
| scripts/audit_edgeiq_recent_workspace_regression_v1.py | PASS | YES | Static regression audit for Scratchings, Gear, Track, Weather, Results, and Meeting selected-race state. | Expected pass marker: EDGEIQ_RECENT_WORKSPACE_REGRESSION_V1_AUDIT_PASS. |

## Current Canonical Path

- Meeting Races visual and state lock: `apply_edgeiq_meeting_races_final_polish_v2.py` plus `audit_edgeiq_meeting_races_final_polish_v2.py`.
- Cross-workspace regression lock: `apply_edgeiq_recent_workspace_regression_fixes_v1.py` plus `audit_edgeiq_recent_workspace_regression_v1.py`.
- Do not restore pre-weather checkpoints over `MeetingWeatherWorkspace.tsx` or `weatherFeed.ts`; live on-track weather v1.2 integration is preserved.
