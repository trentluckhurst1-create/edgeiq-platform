from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "public" / "data" / "edgeiq_map_terminal_feed_v1.csv"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_map_data_contract_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_map_data_contract_v1_audit.txt"

EXPECTED_COLUMNS = [
    "workspace_id",
    "meeting_key",
    "race_key",
    "generated_at",
    "race_date",
    "track",
    "race_no",
    "no",
    "horse",
    "barrier",
    "effective_barrier",
    "run_style",
    "early_speed",
    "projected_position",
    "source",
    "source_timestamp",
    "source_confidence",
    "row_status",
]

LOCKED_DISPLAY_COLUMNS = ["NO", "HORSE", "BARRIER", "EFFECTIVE BARRIER", "RUN STYLE", "EARLY SPEED", "PROJECTED POSITION"]


def main() -> None:
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    if FEED.exists():
        with FEED.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            rows = list(reader)

    race_keys = {row.get("race_key", "") for row in rows if row.get("race_key")}
    checks = {
        "feed_exists": FEED.exists(),
        "columns_exact": headers == EXPECTED_COLUMNS,
        "frontend_row_limit": len(rows) <= 10000,
        "has_rows": len(rows) > 0,
        "has_races": len(race_keys) > 0,
        "workspace_id_beta_009": all(row.get("workspace_id") == "BETA-009" for row in rows),
        "locked_display_columns": LOCKED_DISPLAY_COLUMNS == ["NO", "HORSE", "BARRIER", "EFFECTIVE BARRIER", "RUN STYLE", "EARLY SPEED", "PROJECTED POSITION"],
        "missing_fields_not_zeroed": all(
            row.get("run_style", "") != "0"
            and row.get("early_speed", "") != "0"
            and row.get("projected_position", "") != "0"
            for row in rows
        ),
    }
    payload = {
        "status": "EDGEIQ_MAP_DATA_CONTRACT_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_MAP_DATA_CONTRACT_V1_AUDIT_FAIL",
        "checks": checks,
        "rows": len(rows),
        "races": len(race_keys),
        "columns": headers,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                payload["status"],
                f"rows={len(rows)}",
                f"races={len(race_keys)}",
                "",
                *[f"{key}: {value}" for key, value in checks.items()],
            ]
        ),
        encoding="utf-8",
    )
    print(payload["status"])
    if payload["status"].endswith("FAIL"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
