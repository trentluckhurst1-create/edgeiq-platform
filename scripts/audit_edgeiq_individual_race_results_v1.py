from edgeiq_meeting_workspace_audit_common_v1 import MEETING, ROOT, read, run_audit

RESULTS = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "resultsFeed.ts"
source = read(MEETING) + "\n" + (read(RESULTS) if RESULTS.exists() else "") + "\n" + (read(SERVICE) if SERVICE.exists() else "")
checks = {
    "individual_view_present": "function IndividualRaceResult" in source,
    "back_to_results": "Back to Results" in source,
    "race_snapshot_fields": all(text in source for text in ["Official Race Time", "Penetrometer Average", "Prize Money"]),
    "finishing_order_columns": all(text in source for text in ["Pos</th>", "No</th>", "Horse</th>", "Jockey</th>", "Trainer</th>", "SP (TAB)</th>", "Margin</th>"]),
    "runner_performance_dominant": "Runner Performance" in source and "Benchmark sectionals" in source,
    "epi_pending": "EPI and ERI remain pending until governed speed and sectional data is available." in source,
    "stewards_pending": "Stewards comments will display only when the official report is published." in source,
    "no_replay": "replay" not in source.lower(),
    "no_epi_vs_sp": "EPI vs SP" not in source and "EPI versus SP" not in source,
    "no_race_tempo_visual": "race-tempo" not in source.lower(),
}
run_audit("EDGEIQ_INDIVIDUAL_RACE_RESULTS_V1", "EDGEIQ_INDIVIDUAL_RACE_RESULTS_V1_AUDIT_PASS", checks, "edgeiq_individual_race_results_v1_audit")
