from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "public" / "data" / "edgeiq_epi_workspace_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_epi_context_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_epi_context_v1_audit.txt"

REQUIRED_CONTEXT = [
    "DATE",
    "TRACK",
    "MEETING / RACE",
    "DISTANCE",
    "CLASS",
    "CONDITION",
    "BARRIER",
    "WEIGHT",
    "JOCKEY",
    "TRAINER",
    "FINISH",
    "MARGIN",
    "SP",
    "EPI",
    "ERI",
    "8-6",
    "6-4",
    "4-2",
    "2-F",
    "SOURCE",
    "VERSION / TIMESTAMP",
]

rows = []
if FEED.exists():
    with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))

checked = 0
invalid = []
for row in rows:
    for index in range(10, 0, -1):
        value = row.get(f"start_{index}")
        context_text = row.get(f"start_{index}_context") or ""
        if not value:
            continue
        checked += 1
        try:
            context = json.loads(context_text)
        except json.JSONDecodeError:
            invalid.append({"row": row.get("horse"), "start": index, "reason": "invalid_json"})
            continue
        missing = [field for field in REQUIRED_CONTEXT if field not in context]
        if missing:
            invalid.append({"row": row.get("horse"), "start": index, "reason": "missing_fields", "fields": missing})
        if str(context.get("EPI", "")).strip() != str(value).strip():
            invalid.append({"row": row.get("horse"), "start": index, "reason": "epi_mismatch"})

checks = {
    "feed_exists": FEED.exists(),
    "populated_contexts_present": checked > 0,
    "all_populated_tiles_have_valid_context": not invalid,
}

payload = {
    "status": "EDGEIQ_EPI_CONTEXT_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_EPI_CONTEXT_V1_AUDIT_FAIL",
    "checks": checks,
    "contexts_checked": checked,
    "invalid": invalid[:20],
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], f"contexts_checked={checked}", "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
