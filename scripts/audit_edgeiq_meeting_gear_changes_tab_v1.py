from edgeiq_meeting_workspace_audit_common_v1 import MEETING, read, run_audit

source = read(MEETING)
checks = {
    "summary_values_present": all(text in source for text in ["Total Gear Changes", "First Time", "Gear Added", "Gear Removed", "Affected Runners", "Latest Update"]),
    "filters_present": all(text in source for text in ["All Races", "All Changes", "All Status", "Search horse or change"]),
    "gear_columns_present": all(text in source for text in ["Change</th>", "Previous</th>", "Today</th>", "First Time</th>", "Comment</th>", "Source</th>"]),
    "current_gear_source_only": "currentGear" in source and "gearComment" in source,
    "official_distinctions_not_flattened": "First Time" in source and "On" not in source.upper().replace("CONDITION", ""),
    "empty_state": "No official gear changes have been supplied for this meeting." in source,
}
run_audit("EDGEIQ_MEETING_GEAR_CHANGES_TAB_V1", "EDGEIQ_MEETING_GEAR_CHANGES_TAB_V1_AUDIT_PASS", checks, "edgeiq_meeting_gear_changes_tab_v1_audit")
