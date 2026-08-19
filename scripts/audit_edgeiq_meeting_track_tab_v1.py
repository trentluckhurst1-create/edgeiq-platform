from edgeiq_meeting_workspace_audit_common_v1 import MEETING, read, run_audit

source = read(MEETING)
checks = {
    "official_track_rating": "Official Rating" in source and "trackRatingFromRace" in source,
    "rail_correct": "Rail Position" in source and "railPosition" in source,
    "rainfall_irrigation_fields": all(text in source for text in ["Rainfall 24h", "Rainfall 7d", "Irrigation 24h", "Irrigation 7d"]),
    "track_map_present": "eiq-meeting-v1-track-map is-large" in source,
    "no_track_record": "Track Record" not in source,
    "no_class_record": "Class Record" not in source,
    "no_average_race_time": "Average Race Time" not in source,
    "no_average_winning_margin": "Average Winning Margin" not in source,
    "historical_lane_metrics": all(text in source for text in ["Inside Win %", "Middle Win %", "Wide Win %", "Leaders Win %", "Backmarker Win %"]),
    "pattern_title": "Track Pattern Analysis" in source,
}
run_audit("EDGEIQ_MEETING_TRACK_TAB_V1", "EDGEIQ_MEETING_TRACK_TAB_V1_AUDIT_PASS", checks, "edgeiq_meeting_track_tab_v1_audit")
