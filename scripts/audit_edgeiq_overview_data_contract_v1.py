from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "public" / "data" / "edgeiq_overview_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_overview_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_overview_data_contract_v1_audit.txt"

EXPECTED = [
    "workspace_id",
    "meeting_key",
    "race_key",
    "generated_at",
    "race_date",
    "track",
    "race_no",
    "section",
    "evidence",
    "source",
    "status",
    "open",
    "source_timestamp",
    "source_confidence",
    "row_status",
]

LOCKED_SECTIONS = {
    "Race Environment",
    "MAP / Race Shape",
    "Field Intelligence",
    "EDGEiQ Race Read",
    "Key Race Questions",
    "Operational / Data State",
}

rows = []
headers = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)

race_sections: dict[str, set[str]] = {}
for row in rows:
    race_key = row.get("race_key", "")
    race_sections.setdefault(race_key, set()).add(row.get("section", ""))

checks = {
    "feed_exists": FEED.exists(),
    "locked_columns_exact": headers == EXPECTED,
    "rows_under_frontend_limit": len(rows) <= 10000,
    "workspace_id_locked": all(row.get("workspace_id") == "BETA-011" for row in rows),
    "identity_present": all(row.get("meeting_key") and row.get("race_key") and row.get("section") for row in rows),
    "locked_sections_present_per_race": bool(race_sections) and all(sections == LOCKED_SECTIONS for sections in race_sections.values()),
    "locked_display_columns_present": all(field in headers for field in ["section", "evidence", "source", "status", "open"]),
}

payload = {
    "status": "EDGEIQ_OVERVIEW_DATA_CONTRACT_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_OVERVIEW_DATA_CONTRACT_V1_AUDIT_FAIL",
    "checks": checks,
    "rows": len(rows),
    "races": len(race_sections),
    "headers": headers,
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], f"rows={len(rows)}", f"races={len(race_sections)}", "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
