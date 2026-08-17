from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "trackFeed.ts"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingTrackWorkspace.tsx"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_track_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_track_data_contract_v1_audit.txt"

TERMINAL_FEEDS = [
    "edgeiq_vic_official_track_conditions_v1.json",
    "edgeiq_track_map_manifest_v1.csv",
    "edgeiq_current_true_track_feed_v1.csv",
    "edgeiq_track_profile_v2.csv",
    "edgeiq_track_intelligence_profile_v2.csv",
]

OFFICIAL_FIELDS = [
    "OFFICIAL RATING",
    "RAIL",
    "TRACK TYPE",
    "PENETROMETER AVERAGE",
    "GOING STICK",
    "RAIN 24H",
    "RAIN 7D",
    "IRRIGATION 24H",
    "IRRIGATION 7D",
]

DETAIL_FIELDS = [
    "SURFACE",
    "COURSE TYPE",
    "DIRECTION",
    "DISTANCES",
    "EDGEIQ TRUE TRACK",
    "SURFACE DELTA",
]

service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""

row_counts: dict[str, int | str] = {}
for feed in TERMINAL_FEEDS:
    path = ROOT / "public" / "data" / feed
    if not path.exists():
        row_counts[feed] = "missing"
        continue
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        row_counts[feed] = len(payload.get("records", [])) if isinstance(payload, dict) else len(payload)
    else:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            row_counts[feed] = max(sum(1 for _ in csv.reader(handle)) - 1, 0)

checks = {
    "service_exists": SERVICE.exists(),
    "component_exists": COMPONENT.exists(),
    "terminal_feeds_declared": all(feed in service for feed in TERMINAL_FEEDS),
    "frontend_row_guard_present": "> 10000" in service and "rejected oversized" in service,
    "official_fields_present": all(field in service for field in OFFICIAL_FIELDS),
    "track_details_present": all(field in service for field in DETAIL_FIELDS),
    "track_record_removed": "TRACK RECORD" not in component and "CLASS RECORD" not in component,
    "view_model_statuses_present": all(status in service for status in ["loading", "empty", "unavailable", "error", "current"]),
    "all_feeds_under_frontend_limit": all(isinstance(count, int) and count <= 10000 for count in row_counts.values()),
}

payload = {
    "status": "EDGEIQ_TRACK_DATA_CONTRACT_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_TRACK_DATA_CONTRACT_V1_AUDIT_FAIL",
    "checks": checks,
    "row_counts": row_counts,
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
            "Rows:",
            *[f"{key}: {value}" for key, value in row_counts.items()],
        ]
    ),
    encoding="utf-8",
)
print(payload["status"])
