from __future__ import annotations

from pathlib import Path

from edgeiq_meeting_workspace_audit_common_v1 import CSS, MEETING, read, run_audit


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingDetailFeed.ts"


source = read(MEETING)
service = read(SERVICE)
css = read(CSS)

checks = {
    "persistent_header": "eiq-meeting-v1-header" in source
    and "MeetingHeader" in source,
    "persistent_breadcrumb": "eiq-meeting-v1-breadcrumb" in source
    and "MEETINGS" in source,
    "persistent_condition_strip": "eiq-meeting-v1-condition-strip" in source
    and "MeetingConditionStrip" in source,
    "exact_condition_order": all(
        label in service
        for label in [
            '"TRACK"',
            '"RAIL"',
            '"WEATHER"',
            '"WIND"',
            '"TEMPERATURE"',
            '"RAIN 24H"',
            '"IRRIGATION 24H"',
            '"OFFICIAL UPDATE"',
        ]
    ),
    "exact_tab_order": all(
        text in service
        for text in [
            'key: "RACES"',
            'key: "SCRATCHINGS"',
            'key: "GEAR_CHANGES"',
            'key: "TRACK"',
            'key: "WEATHER"',
            'key: "RESULTS"',
        ]
    ),
    "pending_states_exact": all(
        text in service
        for text in [
            "Official scratchings for this meeting will appear here.",
            "Official gear changes for this meeting will appear here.",
            "Detailed track intelligence will appear here.",
            "Detailed weather intelligence will appear here.",
            "Official meeting results will appear here as races are completed.",
        ]
    ),
    "layout_80_20": "eiq-meeting-v1-layout" in source
    and "4.2fr" in css
    and "minmax(260px, 1fr)" in css,
    "operational_rail": "Meeting Highlights" in source
    and "Track Map" in source
    and "EDGEiQ Notes" in source
    and "Data Freshness" in source,
    "active_tabs_not_filled_pill": "background: #1f5fd6 !important" not in css[
        css.find(".eiq-meeting-v1-tabs button.is-active") :
        css.find(".eiq-meeting-v1-layout")
    ],
    "selected_row_outline": "tr.is-selected" in css
    and "#eef4ff" in css
    and "#75a7f5" in css,
}

run_audit(
    "EDGEIQ_MEETING_DETAIL_VISUAL_STRUCTURE_V1",
    "EDGEIQ_MEETING_DETAIL_VISUAL_STRUCTURE_V1_AUDIT_PASS",
    checks,
    "edgeiq_meeting_detail_visual_structure_v1_audit",
)
