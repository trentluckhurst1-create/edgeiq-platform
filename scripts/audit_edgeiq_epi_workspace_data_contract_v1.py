from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "public" / "data" / "edgeiq_epi_workspace_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_epi_workspace_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_epi_workspace_data_contract_v1_audit.txt"

EXPECTED_PREFIX = [
    "workspace_id",
    "meeting_key",
    "race_key",
    "generated_at",
    "race_date",
    "track",
    "race_no",
    "no",
    "horse",
    "current_epi",
    "rank",
    "field_avg",
    "diff",
    "start_10",
    "start_9",
    "start_8",
    "start_7",
    "start_6",
    "start_5",
    "start_4",
    "start_3",
    "start_2",
    "start_1",
]

rows = []
headers = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)

start_fields = [f"start_{index}" for index in range(10, 0, -1)]
start_class_fields = [f"{field}_class" for field in start_fields]
start_context_fields = [f"{field}_context" for field in start_fields]
populated_tiles = sum(1 for row in rows for field in start_fields if row.get(field))
zero_missing = all(row.get(field) != "0" for row in rows for field in start_fields if not row.get(field))

checks = {
    "feed_exists": FEED.exists(),
    "expected_prefix_present": headers[: len(EXPECTED_PREFIX)] == EXPECTED_PREFIX,
    "class_fields_present": all(field in headers for field in start_class_fields),
    "context_fields_present": all(field in headers for field in start_context_fields),
    "rows_under_frontend_limit": len(rows) <= 10000,
    "workspace_id_locked": bool(rows) and all(row.get("workspace_id") == "BETA-013" for row in rows),
    "runner_identity_present": bool(rows) and all(row.get("race_key") and row.get("horse") for row in rows),
    "missing_starts_never_zero": zero_missing,
    "historical_tiles_present": populated_tiles > 0,
}

payload = {
    "status": "EDGEIQ_EPI_WORKSPACE_DATA_CONTRACT_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_EPI_WORKSPACE_DATA_CONTRACT_V1_AUDIT_FAIL",
    "checks": checks,
    "rows": len(rows),
    "historical_tiles": populated_tiles,
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], f"rows={len(rows)}", f"historical_tiles={populated_tiles}", "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
