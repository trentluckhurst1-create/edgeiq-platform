from __future__ import annotations

from pathlib import Path

from edgeiq_meeting_workspace_audit_common_v1 import CSS, MEETING, PUBLIC_DATA, read, run_audit


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingDetailFeed.ts"
TRACE = PUBLIC_DATA / "edgeiq_meeting_detail_engineering_build_v1_trace.txt"
WEATHER_AUDIT = PUBLIC_DATA / "edgeiq_weather_engineering_build_v1_audit.txt"


source = read(MEETING)
service = read(SERVICE)
trace = read(TRACE) if TRACE.exists() else ""
weather_audit = read(WEATHER_AUDIT) if WEATHER_AUDIT.exists() else ""
css = read(CSS)

checks = {
    "service_exists": SERVICE.exists(),
    "component_imports_service": "../services/meetingDetailFeed" in source,
    "service_exports_view_model": "export type MeetingDetailViewModel" in service
    and "buildMeetingDetailViewModel" in service,
    "service_owns_tabs": "MEETING_DETAIL_TAB_ORDER" in service
    and "MEETING_DETAIL_TAB_ORDER.map" in source,
    "service_owns_condition_strip": "buildMeetingConditionStripForRace" in service
    and "buildMeetingConditionStripForRace" in source,
    "service_owns_selected_race": "buildMeetingDetailSelectedRace" in service
    and "buildSelectedDetails" in service,
    "react_does_not_format_dates": "new Date(" not in source
    and "Intl.DateTimeFormat" not in source,
    "react_does_not_join_feed_fields": "function statusFromRace" not in source
    and "function trackRatingFromRace" not in source
    and "sourceValue(" not in source,
    "weather_workspace_mount_has_own_audit": "MeetingWeatherWorkspace" not in source
    or "EDGEIQ_WEATHER_ENGINEERING_BUILD_V1_AUDIT_PASS" in weather_audit,
    "trace_written": "Meeting Detail Engineering Build V1 Trace" in trace,
    "light_design_system_present": "#ffffff" in css and "#f4f6f9" in css,
}

run_audit(
    "EDGEIQ_MEETING_DETAIL_DATA_CONTRACT_V1",
    "EDGEIQ_MEETING_DETAIL_DATA_CONTRACT_V1_AUDIT_PASS",
    checks,
    "edgeiq_meeting_detail_data_contract_v1_audit",
)
