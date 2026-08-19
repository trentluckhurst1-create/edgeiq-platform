from edgeiq_meeting_workspace_audit_common_v1 import MEETING, read, run_audit

source = read(MEETING)
checks = {
    "summary_values_present": "Total Scratchings" in source and "Races Affected" in source and "Emergencies Promoted" in source,
    "grouped_by_race": "groupedByRace(rows)" in source and "Scratchings</strong>" in source,
    "runner_identity_columns": all(text in source for text in ["Horse</th>", "Trainer</th>", "Jockey</th>"]),
    "scratched_time_reason_source": all(text in source for text in ["Scratched At", "Reason", "Source"]),
    "missing_reason_not_fabricated": "scratchingReason" in source and "Vets Advice" not in source,
    "status_retained": "SCRATCHED" in source,
    "empty_state": "No official scratchings have been received for this meeting." in source,
}
run_audit("EDGEIQ_MEETING_SCRATCHINGS_TAB_V1", "EDGEIQ_MEETING_SCRATCHINGS_TAB_V1_AUDIT_PASS", checks, "edgeiq_meeting_scratchings_tab_v1_audit")
