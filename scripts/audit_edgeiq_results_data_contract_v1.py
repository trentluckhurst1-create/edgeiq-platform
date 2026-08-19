from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
FEED = DATA / "edgeiq_meeting_results_terminal_feed_v1.csv"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "resultsFeed.ts"
OUT_JSON = DATA / "edgeiq_results_data_contract_v1_audit.json"
OUT_TXT = DATA / "edgeiq_results_data_contract_v1_audit.txt"

EXPECTED = [
    "meeting_key",
    "race_key",
    "race_date",
    "track",
    "race_no",
    "time",
    "winner",
    "jockey",
    "trainer",
    "sp_tab",
    "margin",
    "official_time",
    "track_condition",
    "status",
    "open",
    "source",
    "source_timestamp",
    "source_confidence",
]


def read_rows() -> tuple[list[str], list[dict[str, str]]]:
    if not FEED.exists():
        return [], []
    with FEED.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def main() -> None:
    headers, rows = read_rows()
    service = SERVICE.read_text(encoding="utf-8", errors="replace") if SERVICE.exists() else ""
    checks = {
        "feed_exists": FEED.exists(),
        "headers_exact": headers == EXPECTED,
        "row_budget_ok": len(rows) <= 10000,
        "has_current_rows": len(rows) > 0,
        "status_values_governed": all((row.get("status") or "") in {"OFFICIAL", "UNOFFICIAL", "ABANDONED", "PENDING", "UPCOMING"} for row in rows),
        "frontend_loads_small_feed": "edgeiq_meeting_results_terminal_feed_v1.csv" in service,
        "frontend_does_not_load_warehouse": "edgeiq_results_terminal_feed_v1.csv" not in service
        and "edgeiq_results_master_v1.csv" not in service,
        "frontend_row_guard": "rows.length > 10000" in service and "rejected oversized results feed" in service,
    }
    status = "EDGEIQ_RESULTS_DATA_CONTRACT_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_RESULTS_DATA_CONTRACT_V1_AUDIT_FAIL"
    payload = {"status": status, "checks": checks, "row_count": len(rows), "headers": headers}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text("\n".join([status, "", *[f"{key}: {value}" for key, value in checks.items()]]) + "\n", encoding="utf-8")
    print(status)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
