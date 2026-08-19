from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, first, now_iso, read_csv, write_csv


OUT = DATA / "edgeiq_speed_retry_engine_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_speed_retry_engine_summary_v1.csv"
RETRY_WINDOWS = ["+15m", "+1h", "+3h", "+6h", "+12h", "+24h", "+48h", "+72h"]


def main() -> None:
    source = DATA / "edgeiq_results_master_v1.csv"
    grouped: dict[str, dict[str, object]] = defaultdict(lambda: {"race_key": "", "race_date": "", "track": "", "race_no": "", "runner_rows": 0, "speed_rows": 0})
    for row in read_csv(source) if source.exists() else []:
        key = first(row, ["race_key"])
        if not key:
            continue
        bucket = grouped[key]
        bucket["race_key"] = key
        bucket["race_date"] = first(row, ["race_date"])
        bucket["track"] = first(row, ["track"])
        bucket["race_no"] = first(row, ["race_no"])
        bucket["runner_rows"] += 1
        if first(row, ["speed_available"]) == "YES":
            bucket["speed_rows"] += 1
    rows = []
    for bucket in grouped.values():
        runner_rows = int(bucket["runner_rows"])
        speed_rows = int(bucket["speed_rows"])
        status = "SPEED_CAPTURED" if runner_rows and speed_rows >= runner_rows else "RETRY_PENDING"
        if speed_rows == 0:
            next_retry = RETRY_WINDOWS[0]
        else:
            next_retry = "+15m"
        rows.append({**bucket, "missing_speed_rows": runner_rows - speed_rows, "next_retry_window": next_retry, "retry_schedule": "|".join(RETRY_WINDOWS), "final_status_after_retries": "SPEED_UNAVAILABLE", "status": status, "built_at": now_iso()})
    fields = ["race_key", "race_date", "track", "race_no", "runner_rows", "speed_rows", "missing_speed_rows", "next_retry_window", "retry_schedule", "final_status_after_retries", "status", "built_at"]
    write_csv(OUT, rows, fields)
    summary = {"races": len(rows), "retry_pending": sum(1 for row in rows if row["status"] == "RETRY_PENDING"), "speed_captured": sum(1 for row in rows if row["status"] == "SPEED_CAPTURED"), "built_at": now_iso()}
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
