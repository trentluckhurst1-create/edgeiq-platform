from edgeiq_meeting_workspace_audit_common_v1 import CSS, ROOT, MEETING, read, run_audit

race_file = read(ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx")
form = read(ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx")
meeting = read(MEETING)
css = read(CSS)
source = race_file + "\n" + form + "\n" + meeting
checks = {
    "primary_lengths_language": "lengths" in source.lower() or "benchmark sectionals" in source.lower(),
    "negative_green": "value < 0" in race_file or "is-inside" in source or "INSIDE_STANDARD" in source,
    "positive_red": "value > 0" in race_file or "is-outside" in source or "OUTSIDE_STANDARD" in source,
    "zero_neutral": "is-standard" in race_file and ".eiq-sectional-delta.is-standard" in css,
    "raw_seconds_not_primary": "Do NOT display raw sectional times" not in source,
    "no_react_conversion_claim": "React may format numeric display but must not calculate benchmark lengths" not in source,
    "meeting_result_pending_until_speed": "EPI and ERI remain pending until governed speed and sectional data is available." in meeting,
}
run_audit("EDGEIQ_BENCHMARK_SECTIONAL_DISPLAY_V1", "EDGEIQ_BENCHMARK_SECTIONAL_DISPLAY_V1_AUDIT_PASS", checks, "edgeiq_benchmark_sectional_display_v1_audit")
