from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
CALENDAR = DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv"
OUT = DATA / "edgeiq_frontend_race_list_key_join_audit_v1.csv"

EXPECTED_COUNTS = {
    "2026-07-01_SANDOWNLAKESIDE": 8,
    "2026-07-02_BALLARATSYNTHETIC": 8,
    "2026-07-03_MOE": 8,
}


def clean_track(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def frontend_key(date_value: str, track_value: str) -> str:
    return f"{date_value}_{clean_track(track_value)}"


def main() -> None:
    race_rows = read_csv(RACE_LIST)
    calendar_rows = read_csv(CALENDAR)

    race_counts: Counter[str] = Counter()
    race_examples: dict[str, str] = {}
    for row in race_rows:
        race_date = (row.get("race_date") or "").strip()
        track = (row.get("normalised_track") or row.get("track") or "").strip()
        race_no = (row.get("race_no") or "").strip()
        if not race_date or not track or not race_no:
            continue
        key = frontend_key(race_date, track)
        race_counts[key] += 1
        race_examples.setdefault(key, f"{race_date} / {track}")

    calendar_keys = set()
    for row in calendar_rows:
        race_date = (row.get("race_date") or row.get("meeting_date") or "").strip()
        track = (row.get("track") or "").strip()
        if race_date and track:
            calendar_keys.add(frontend_key(race_date, track))

    output: list[dict[str, object]] = []
    output.append({
        "check_type": "RACE_LIST_ROWS",
        "frontend_meeting_key": "",
        "race_count": len(race_rows),
        "expected_count": ">0",
        "calendar_key_exists": "",
        "status": "PASS" if len(race_rows) > 0 else "FAIL",
        "details": f"race_list_rows={len(race_rows)}",
    })

    for key, expected in EXPECTED_COUNTS.items():
        actual = race_counts.get(key, 0)
        calendar_match = key in calendar_keys
        status = "PASS" if actual == expected and calendar_match else "FAIL"
        details = "frontend race-list key matches calendar key"
        if actual != expected:
            details = f"expected {expected} races but found {actual}"
        elif not calendar_match:
            details = "race-list key not present in calendar generated keys"
        output.append({
            "check_type": "EXPECTED_KEY_JOIN",
            "frontend_meeting_key": key,
            "race_count": actual,
            "expected_count": expected,
            "calendar_key_exists": "YES" if calendar_match else "NO",
            "status": status,
            "details": details,
        })

    for key, count in sorted(race_counts.items()):
        output.append({
            "check_type": "RACE_LIST_KEY_COUNT",
            "frontend_meeting_key": key,
            "race_count": count,
            "expected_count": EXPECTED_COUNTS.get(key, ""),
            "calendar_key_exists": "YES" if key in calendar_keys else "NO",
            "status": "PASS",
            "details": race_examples.get(key, ""),
        })

    fail_count = sum(1 for row in output if row["status"] != "PASS")
    output.append({
        "check_type": "SUMMARY",
        "frontend_meeting_key": "",
        "race_count": sum(race_counts.values()),
        "expected_count": "",
        "calendar_key_exists": "",
        "status": "PASS" if fail_count == 0 else "FAIL",
        "details": f"keys={len(race_counts)} races={sum(race_counts.values())} failures={fail_count}",
    })

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "check_type",
            "frontend_meeting_key",
            "race_count",
            "expected_count",
            "calendar_key_exists",
            "status",
            "details",
        ])
        writer.writeheader()
        writer.writerows(output)

    print(f"Wrote {OUT}")
    print(output[-1]["details"])
    if output[-1]["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
