from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
CALENDAR = DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv"
OUT = DATA / "edgeiq_meetings_race_list_fallback_audit_v1.csv"

EXPECTED = {
    ("2026-07-01", "SANDOWN LAKESIDE"): 8,
    ("2026-07-02", "BALLARAT SYNTHETIC"): 8,
    ("2026-07-03", "MOE"): 8,
}


def clean_track(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    rows = read_csv(RACE_LIST)
    calendar_rows = read_csv(CALENDAR)
    calendar_keys = {
        f"{row.get('race_date') or row.get('meeting_date')}_{clean_track(row.get('track', ''))}"
        for row in calendar_rows
        if (row.get("race_date") or row.get("meeting_date")) and row.get("track")
    }

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        race_date = row.get("race_date", "").strip()
        track = (row.get("normalised_track") or row.get("track") or "").strip()
        if race_date and track:
            grouped[(race_date, track)].append(row)

    output: list[dict[str, object]] = []
    if not RACE_LIST.exists():
        output.append({
            "check_type": "FILE_EXISTS",
            "race_date": "",
            "track": "",
            "frontend_meeting_key": "",
            "race_count": 0,
            "expected_count": "",
            "calendar_key_match": "",
            "status": "FAIL",
            "details": f"Missing {RACE_LIST}",
        })
    else:
        output.append({
            "check_type": "FILE_EXISTS",
            "race_date": "",
            "track": "",
            "frontend_meeting_key": "",
            "race_count": len(rows),
            "expected_count": ">0",
            "calendar_key_match": "",
            "status": "PASS" if rows else "FAIL",
            "details": "Race-list file exists and has rows" if rows else "Race-list file exists but is empty",
        })

    for (race_date, track), meeting_rows in sorted(grouped.items()):
        frontend_key = f"{race_date}_{clean_track(track)}"
        expected = EXPECTED.get((race_date, track), "")
        race_numbers = sorted({row.get("race_no", "").strip() for row in meeting_rows if row.get("race_no", "").strip()}, key=lambda x: int(x) if x.isdigit() else 999)
        status = "PASS"
        details = "Frontend fallback key generated from race_date + cleanTrack(normalised_track)"
        if expected != "" and len(race_numbers) != expected:
            status = "FAIL"
            details = f"Expected {expected} races but found {len(race_numbers)}"
        output.append({
            "check_type": "MEETING_COUNT",
            "race_date": race_date,
            "track": track,
            "frontend_meeting_key": frontend_key,
            "race_count": len(race_numbers),
            "expected_count": expected,
            "calendar_key_match": "YES" if frontend_key in calendar_keys else "NO",
            "status": status,
            "details": details,
        })

    for expected_key, expected_count in EXPECTED.items():
        if expected_key not in grouped:
            race_date, track = expected_key
            output.append({
                "check_type": "EXPECTED_MEETING_PRESENT",
                "race_date": race_date,
                "track": track,
                "frontend_meeting_key": f"{race_date}_{clean_track(track)}",
                "race_count": 0,
                "expected_count": expected_count,
                "calendar_key_match": "YES" if f"{race_date}_{clean_track(track)}" in calendar_keys else "NO",
                "status": "FAIL",
                "details": "Expected meeting missing from Racing.com race-list fallback",
            })

    status_counts = Counter(row["status"] for row in output)
    output.append({
        "check_type": "SUMMARY",
        "race_date": "",
        "track": "",
        "frontend_meeting_key": "",
        "race_count": len(rows),
        "expected_count": "",
        "calendar_key_match": "",
        "status": "PASS" if status_counts.get("FAIL", 0) == 0 else "FAIL",
        "details": f"meetings={len(grouped)} races={len(rows)} pass={status_counts.get('PASS', 0)} fail={status_counts.get('FAIL', 0)}",
    })

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "check_type",
            "race_date",
            "track",
            "frontend_meeting_key",
            "race_count",
            "expected_count",
            "calendar_key_match",
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
