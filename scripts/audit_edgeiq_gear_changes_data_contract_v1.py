from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "gearChangesFeed.ts"
FEED = ROOT / "public" / "data" / "edgeiq_gear_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_gear_changes_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_gear_changes_data_contract_v1_audit.txt"

text = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
feed_headers: list[str] = []
row_count = 0
if FEED.exists():
    with FEED.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        feed_headers = list(reader.fieldnames or [])
        row_count = sum(1 for _ in reader)

required_exports = [
    "GearChangeRecordViewModel",
    "GearChangeHistoryRecord",
    "GearChangesRaceGroupViewModel",
    "MeetingGearChangesViewModel",
    "GearTerminalRow",
    "loadGearTerminalFeed",
    "buildMeetingGearChangesViewModel",
]
required_record_fields = [
    "eventKey",
    "meetingKey",
    "raceKey",
    "raceNumber",
    "runnerKey",
    "no",
    "silk",
    "horse",
    "change",
    "previous",
    "today",
    "firstTime",
    "comment",
    "source",
    "status",
    "sourceTimestamp",
    "historical",
]
required_summary_fields = [
    "totalGearChanges",
    "firstTime",
    "gearAdded",
    "gearRemoved",
    "affectedRunners",
    "latestUpdate",
]
required_feed_headers = [
    "race_date",
    "track",
    "race_no",
    "race_key",
    "runner",
    "normalized_runner",
    "gear_current",
    "gear_changes",
    "gear_added",
    "gear_removed",
    "first_time_gear",
    "gear_change_flag",
    "source_confidence",
]

checks = {
    "service_exists": SERVICE.exists(),
    "required_exports_present": all(item in text for item in required_exports),
    "required_record_fields_present": all(re.search(rf"\b{field}\b", text) for field in required_record_fields),
    "summary_contract_present": all(item in text for item in required_summary_fields),
    "statuses_present": all(item in text for item in ["CURRENT", "STALE", "UNAVAILABLE"]),
    "terminal_feed_exists": FEED.exists(),
    "terminal_feed_under_10000_rows": row_count <= 10000,
    "terminal_feed_headers_present": all(header in feed_headers for header in required_feed_headers),
    "large_warehouse_not_loaded": "edgeiq_gear_profile_feed_v1.csv" not in text,
    "safe_load_guard_present": "rows.length > 10000" in text and "console.warn" in text,
}

payload = {
    "status": "EDGEIQ_GEAR_CHANGES_DATA_CONTRACT_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_GEAR_CHANGES_DATA_CONTRACT_V1_AUDIT_FAIL",
    "checks": checks,
    "feed": {
        "path": str(FEED),
        "row_count": row_count,
        "headers": feed_headers,
    },
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join(
        [
            payload["status"],
            "",
            "Checks:",
            *[f"{key}: {value}" for key, value in checks.items()],
            "",
            f"terminal_feed_rows: {row_count}",
        ]
    ),
    encoding="utf-8",
)
print(payload["status"])
