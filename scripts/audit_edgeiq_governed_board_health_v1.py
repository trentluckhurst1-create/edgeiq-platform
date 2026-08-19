from __future__ import annotations

from collections import Counter

from edgeiq_results_common_v1 import DATA, first, now_iso, read_csv, race_key_for, parse_date, write_csv


OUT = DATA / "edgeiq_governed_board_health_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_governed_board_health_summary_v1.csv"


def load(name: str) -> list[dict[str, str]]:
    path = DATA / name
    return list(read_csv(path)) if path.exists() else []


def race_key(row: dict[str, str]) -> str:
    return first(row, ["race_key"]) or race_key_for(parse_date(first(row, ["race_date", "meeting_date"])), first(row, ["track"]), first(row, ["race_no"]))


def runner_key(row: dict[str, str]) -> str:
    return first(row, ["runner_key"]) or "|".join([race_key(row), first(row, ["horse", "runner", "runner_name"])])


def main() -> None:
    live = load("edgeiq_live_runner_board_v1.csv")
    governed = load("edgeiq_live_runner_board_governed_v1.csv")
    live_keys = {runner_key(row) for row in live if runner_key(row)}
    governed_keys = {runner_key(row) for row in governed if runner_key(row)}
    live_dates = {first(row, ["race_date"]) for row in live if first(row, ["race_date"])}
    governed_dates = {first(row, ["race_date"]) for row in governed if first(row, ["race_date"])}
    live_meetings = {first(row, ["meeting_key"]) for row in live if first(row, ["meeting_key"])}
    governed_meetings = {first(row, ["meeting_key"]) for row in governed if first(row, ["meeting_key"])}
    duplicate_counts = Counter(runner_key(row) for row in governed if runner_key(row))
    duplicate_rows = sum(count - 1 for count in duplicate_counts.values() if count > 1)

    checks = [
        {
            "check": "governed_rows_gte_live_rows",
            "live_value": len(live),
            "governed_value": len(governed),
            "missing_count": max(0, len(live) - len(governed)),
            "status": "OK" if len(governed) >= len(live) else "FAIL",
        },
        {
            "check": "governed_has_latest_race_date",
            "live_value": max(live_dates) if live_dates else "",
            "governed_value": max(governed_dates) if governed_dates else "",
            "missing_count": len(live_dates - governed_dates),
            "status": "OK" if live_dates.issubset(governed_dates) else "FAIL",
        },
        {
            "check": "governed_has_latest_meeting",
            "live_value": len(live_meetings),
            "governed_value": len(governed_meetings),
            "missing_count": len(live_meetings - governed_meetings),
            "status": "OK" if live_meetings.issubset(governed_meetings) else "FAIL",
        },
        {
            "check": "governed_runner_keys_match_live",
            "live_value": len(live_keys),
            "governed_value": len(governed_keys),
            "missing_count": len(live_keys - governed_keys),
            "status": "OK" if live_keys.issubset(governed_keys) else "FAIL",
        },
        {
            "check": "governed_duplicates",
            "live_value": "",
            "governed_value": duplicate_rows,
            "missing_count": duplicate_rows,
            "status": "OK" if duplicate_rows == 0 else "FAIL",
        },
    ]
    for row in checks:
        row["built_at"] = now_iso()
    fields = ["check", "live_value", "governed_value", "missing_count", "status", "built_at"]
    write_csv(OUT, checks, fields)
    summary = {
        "status": "READY" if all(row["status"] == "OK" for row in checks) else "FAIL",
        "live_rows": len(live),
        "governed_rows": len(governed),
        "missing_runner_keys": len(live_keys - governed_keys),
        "missing_dates": len(live_dates - governed_dates),
        "missing_meetings": len(live_meetings - governed_meetings),
        "duplicate_rows": duplicate_rows,
        "built_at": now_iso(),
    }
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(checks)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
