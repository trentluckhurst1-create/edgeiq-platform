from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "public" / "data" / "edgeiq_market_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_market_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_market_data_contract_v1_audit.txt"

EXPECTED = [
    "workspace_id",
    "meeting_key",
    "race_key",
    "generated_at",
    "race_date",
    "track",
    "race_no",
    "no",
    "horse",
    "epi",
    "market",
    "open",
    "high",
    "low",
    "move",
    "edgeiq_price",
    "edge",
    "status",
    "source",
    "source_timestamp",
    "source_confidence",
    "row_status",
]

rows = []
headers = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)

checks = {
    "feed_exists": FEED.exists(),
    "locked_columns_exact": headers == EXPECTED,
    "rows_under_frontend_limit": len(rows) <= 10000,
    "workspace_id_locked": all(row.get("workspace_id") == "BETA-010" for row in rows),
    "identity_present": all(row.get("race_key") and row.get("horse") for row in rows),
}

payload = {
    "status": "EDGEIQ_MARKET_DATA_CONTRACT_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_MARKET_DATA_CONTRACT_V1_AUDIT_FAIL",
    "checks": checks,
    "rows": len(rows),
    "headers": headers,
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], f"rows={len(rows)}", "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
