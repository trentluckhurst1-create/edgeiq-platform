from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUT = DATA / "edgeiq_gear_terminal_feed_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_gear_terminal_feed_summary_v1.csv"

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_key",
    "runner",
    "normalized_runner",
    "gear_current",
    "gear_changes",
    "gear_added",
    "gear_removed",
    "first_time_gear",
    "gear_change_flag",
    "source_confidence",
]

WARN_ROWS = 5000
FAIL_ROWS = 10000


def text(value: Any) -> str:
    return str(value or "").strip()


def normalized_runner(value: Any) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_catalog() -> dict[str, Any]:
    if not CATALOG.exists():
        return {}
    with CATALOG.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def classify_current_gear(gear: str) -> tuple[str, str, str, str]:
    raw = text(gear)
    if not raw:
        return "", "", "", "NO"
    upper = raw.upper()
    first_time = "YES" if "FIRST" in upper or "1ST" in upper else ""
    added = raw if any(token in upper for token in [" ON", "FIRST", "1ST", "VISOR", "BLINK", "WINK", "TONGUE", "LUGGING", "NOSE"]) else ""
    removed = raw if " OFF" in upper or "REMOVED" in upper else ""
    return added, removed, first_time, "YES" if added or removed or first_time else "NO"


def build_rows() -> list[dict[str, str]]:
    catalog = read_catalog()
    rows: list[dict[str, str]] = []
    for meeting in catalog.get("meetings", []):
        meeting_date = text(meeting.get("date"))
        track = text(meeting.get("meeting") or meeting.get("providerMeetingKey"))
        for race in meeting.get("races", []) or []:
            race_no = text(race.get("raceNumber"))
            race_key = text(race.get("raceKey")) or f"{meeting_date}|{track.upper()}|R{race_no}"
            for runner in race.get("runners", []) or []:
                official = runner.get("official") or {}
                runner_name = text(official.get("runner"))
                if not runner_name:
                    continue
                gear_current = text(official.get("currentGear"))
                added, removed, first_time, change_flag = classify_current_gear(gear_current)
                confidence = "catalog_current_gear" if gear_current else "current_gear_not_supplied"
                rows.append(
                    {
                        "race_date": meeting_date,
                        "track": track,
                        "race_no": race_no,
                        "race_key": race_key,
                        "runner": runner_name,
                        "normalized_runner": normalized_runner(runner_name),
                        "gear_current": gear_current,
                        "gear_changes": gear_current if change_flag == "YES" else "",
                        "gear_added": added,
                        "gear_removed": removed,
                        "first_time_gear": first_time,
                        "gear_change_flag": change_flag,
                        "source_confidence": confidence,
                    }
                )
    rows.sort(key=lambda row: (row["race_date"], row["track"], int(row["race_no"] or 0), int("".join(ch for ch in row.get("race_key", "") if ch.isdigit()) or 0), row["normalized_runner"]))
    return rows


def main() -> None:
    rows = build_rows()
    status = "OK"
    if len(rows) > FAIL_ROWS:
        status = "FAILED_OVER_10000"
    elif len(rows) > WARN_ROWS:
        status = "WARN_OVER_5000"
    write_csv(OUT, rows, FIELDS)
    summary = {
        "source_file": str(CATALOG.relative_to(ROOT)),
        "output_file": str(OUT.relative_to(ROOT)),
        "catalog_runners": len(rows),
        "current_gear_rows": sum(1 for row in rows if row["gear_current"]),
        "gear_change_rows": sum(1 for row in rows if row["gear_change_flag"] == "YES"),
        "terminal_rows": len(rows),
        "target_under_rows": WARN_ROWS,
        "hard_limit_rows": FAIL_ROWS,
        "status": status,
        "built_at": iso_now(),
        "notes": "Current-window feed. Gear fields are blank when the product catalogue does not supply current gear; no historical gear is projected into current race context.",
    }
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")
    print(f"Wrote {SUMMARY_OUT}")
    if len(rows) > FAIL_ROWS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
