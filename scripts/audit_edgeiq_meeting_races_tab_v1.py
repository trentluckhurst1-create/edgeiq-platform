from __future__ import annotations

import re

from edgeiq_meeting_workspace_audit_common_v1 import CSS, MEETING, read, run_audit


source = read(MEETING)
css = read(CSS)


def has_th(label: str) -> bool:
    return re.search(rf"<th[^>]*>\s*{re.escape(label)}\s*</th>", source) is not None


checks = {
    "races_tab_full_mount": "function RacesTab" in source
    and "RacesTable" in source
    and "SelectedRacePanel" in source,
    "race_table_exact_columns": all(
        has_th(label)
        for label in [
            "RACE",
            "TIME",
            "RACE NAME",
            "DIST",
            "CLASS",
            "FIELD",
            "SCR",
            "TRACK",
            "STATUS",
            "OPEN",
        ]
    ),
    "row_selection_not_navigation": "onSelectRace(row.raceKey)" in source
    and "event.stopPropagation()" in source
    and "onOpenRace(row.race, row.raceIndex)" in source,
    "selected_row_visible": "selectedRaceKey === row.raceKey" in source
    and "is-selected" in source
    and "tr.is-selected" in css,
    "selected_detail_supported": "Selected Race Details" in source
    and "selected.details" in source
    and "selected.intelligence" in source,
    "market_status_pending_supported": "Market Status" in read(
        MEETING.parents[1] / "services" / "meetingDetailFeed.ts"
    )
    and "Pending Market" in read(MEETING.parents[1] / "services" / "meetingDetailFeed.ts"),
    "no_vertical_table_dividers": "border-left" not in css[
        css.find(".eiq-meeting-v1-table") :
        css.find(".eiq-meeting-v1-detail-grid")
    ],
}

run_audit(
    "EDGEIQ_MEETING_RACES_TAB_V1",
    "EDGEIQ_MEETING_RACES_TAB_V1_AUDIT_PASS",
    checks,
    "edgeiq_meeting_races_tab_v1_audit",
)
