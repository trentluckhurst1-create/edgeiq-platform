from pathlib import Path

from edgeiq_meeting_workspace_audit_common_v1 import MEETING, ROOT, read, run_audit

RESULTS = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "resultsFeed.ts"
source = read(MEETING) + "\n" + (read(RESULTS) if RESULTS.exists() else "") + "\n" + (read(SERVICE) if SERVICE.exists() else "")
checks = {
    "results_columns_present": all(text in source for text in ["Winner</th>", "SP (TAB)</th>", "Margin</th>", "Status</th>", "Open</th>"]),
    "statuses_present": all(text in source for text in ["OFFICIAL", "UNOFFICIAL", "UPCOMING", "ABANDONED"]),
    "pending_state": "Results become available after official race results are received." in source,
    "open_result_route": "Open Race Result" in source and "setResultRaceKey" in source,
    "no_winner_decoration": "medal" not in source.lower() and "gold" not in source.lower(),
    "meeting_summary": all(text in source for text in ["Races Completed", "Upcoming Races", "Average Field Size"]),
}
run_audit("EDGEIQ_MEETING_RESULTS_TAB_V1", "EDGEIQ_MEETING_RESULTS_TAB_V1_AUDIT_PASS", checks, "edgeiq_meeting_results_tab_v1_audit")
