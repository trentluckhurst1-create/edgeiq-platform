from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from edgeiq_results_common_v1 import (
    DATA,
    has_value,
    metro_priority,
    next_retry_at,
    read_csv,
    row_has_speed,
    write_csv,
)


MASTER = DATA / "edgeiq_results_master_v1.csv"
OUT = DATA / "edgeiq_sectionals_retry_queue_v1.csv"
SUMMARY = DATA / "edgeiq_sectionals_retry_queue_summary_v1.csv"

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_key",
    "meeting_key",
    "race_name",
    "distance",
    "class",
    "condition",
    "result_status",
    "sp_status",
    "sectional_status",
    "speed_available_rows",
    "runner_rows",
    "retry_priority",
    "priority_reason",
    "first_seen_at",
    "last_checked_at",
    "retry_count",
    "next_retry_at",
    "stop_reason",
]


def race_groups() -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not MASTER.exists():
        return groups
    for row in read_csv(MASTER):
        key = row.get("race_key", "")
        if key:
            groups[key].append(row)
    return groups


def build_queue() -> tuple[list[dict[str, object]], dict[str, object]]:
    checked_at = datetime.now().replace(microsecond=0).isoformat()
    rows: list[dict[str, object]] = []
    total_resulted = 0
    captured = 0
    speed_available_races = 0
    sp_missing = 0
    priority_counts = defaultdict(int)

    for race_key, race_rows in sorted(race_groups().items()):
        resulted = [r for r in race_rows if r.get("result_status") == "RESULTED"]
        if not resulted:
            continue
        total_resulted += 1
        has_speed = any(row_has_speed(r) or r.get("speed_available") == "YES" for r in race_rows)
        if has_speed:
            speed_available_races += 1
        if any(r.get("sectional_status") == "CAPTURED" for r in race_rows) or has_speed:
            captured += 1
            continue

        first = race_rows[0]
        sp_status = "SP_AVAILABLE" if any(has_value(r.get("sp", "")) or has_value(r.get("starting_price", "")) for r in race_rows) else "SP_MISSING"
        if sp_status == "SP_MISSING":
            sp_missing += 1
        priority, reason = metro_priority(first.get("track", ""), first.get("race_date", ""))
        priority_counts[priority] += 1
        rows.append(
            {
                "race_date": first.get("race_date", ""),
                "track": first.get("track", ""),
                "race_no": first.get("race_no", ""),
                "race_key": race_key,
                "meeting_key": first.get("meeting_key", ""),
                "race_name": first.get("race_name", ""),
                "distance": first.get("distance", ""),
                "class": first.get("class", ""),
                "condition": first.get("condition", ""),
                "result_status": "RESULTED",
                "sp_status": sp_status,
                "sectional_status": "MISSING",
                "speed_available_rows": 0,
                "runner_rows": len(race_rows),
                "retry_priority": priority,
                "priority_reason": reason,
                "first_seen_at": first.get("built_at", ""),
                "last_checked_at": checked_at,
                "retry_count": 0,
                "next_retry_at": next_retry_at(first.get("race_date", ""), 0),
                "stop_reason": "",
            }
        )

    summary = {
        "resulted_races": total_resulted,
        "sectional_captured_races": captured,
        "speed_available_races": speed_available_races,
        "retry_queue_races": len(rows),
        "sp_missing_queue_races": sp_missing,
        "high_priority": priority_counts["HIGH"],
        "medium_priority": priority_counts["MEDIUM"],
        "low_priority": priority_counts["LOW"],
        "built_at": checked_at,
    }
    return rows, summary


def main() -> None:
    rows, summary = build_queue()
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")
    print(f"Wrote {SUMMARY}")


if __name__ == "__main__":
    main()
