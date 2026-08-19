from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "public" / "data" / "edgeiq_insights_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_insights_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_insights_data_contract_v1_audit.txt"

EXPECTED_PREFIX = [
    "workspace_id",
    "meeting_key",
    "race_key",
    "generated_at",
    "race_date",
    "track",
    "race_no",
    "row_kind",
    "card_type",
    "card_title",
    "card_value",
    "card_detail",
    "no",
    "horse",
    "key_insight",
    "edge",
    "confidence",
]
LOCKED_RUNNER_FIELDS = ["no", "horse", "key_insight", "edge", "confidence"]
CARD_TYPES = {"KEY INSIGHT", "BEST RATED RUNNER", "VALUE INSIGHT", "MARKET RISER", "RACE SETUP"}

rows = []
headers = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)

runner_rows = [row for row in rows if row.get("row_kind") == "runner"]
card_rows = [row for row in rows if row.get("row_kind") == "card"]
cards_by_race: dict[str, set[str]] = {}
for row in card_rows:
    cards_by_race.setdefault(row.get("race_key", ""), set()).add(row.get("card_type", ""))

checks = {
    "feed_exists": FEED.exists(),
    "expected_prefix_present": headers[: len(EXPECTED_PREFIX)] == EXPECTED_PREFIX,
    "locked_runner_fields_present": all(field in headers for field in LOCKED_RUNNER_FIELDS),
    "rows_under_frontend_limit": len(rows) <= 10000,
    "workspace_id_locked": all(row.get("workspace_id") == "BETA-012" for row in rows),
    "runner_identity_present": all(row.get("race_key") and row.get("horse") for row in runner_rows),
    "card_types_present_per_race": bool(cards_by_race) and all(cards == CARD_TYPES for cards in cards_by_race.values()),
}

payload = {
    "status": "EDGEIQ_INSIGHTS_DATA_CONTRACT_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_INSIGHTS_DATA_CONTRACT_V1_AUDIT_FAIL",
    "checks": checks,
    "rows": len(rows),
    "runner_rows": len(runner_rows),
    "card_rows": len(card_rows),
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], f"rows={len(rows)}", f"runner_rows={len(runner_rows)}", f"card_rows={len(card_rows)}", "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
