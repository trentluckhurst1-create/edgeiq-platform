from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from build_edgeiq_vic_three_day_meeting_calendar_v1 import build_calendar_rows, normalise_track


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CALENDAR_PATH = DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv"
UNIVERSE_PATH = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
RUNNER_BOARD_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
OUT = DATA / "edgeiq_date_rollover_audit_v1.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")

FIELDS = [
    "run_timestamp",
    "today_date",
    "today_meeting",
    "tomorrow_meeting",
    "day2_meeting",
    "calendar_rows",
    "universe_rows",
    "runner_rows",
    "status",
]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def norm_track(value: object) -> str:
    return normalise_track(clean(value))


def today_local() -> date:
    return datetime.now(LOCAL_TZ).date()


def read_frame(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False).fillna("")
    except Exception:
        return pd.DataFrame()


def first_matching_column(columns: list[str], candidates: list[str]) -> str:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return ""


def calendar_rows_for(reference_date: date | None = None) -> list[dict[str, object]]:
    if reference_date is None:
        frame = read_frame(CALENDAR_PATH)
        if not frame.empty and {"race_date", "track", "day_bucket"}.issubset(frame.columns):
            return [
                {
                    "race_date": clean(row.get("race_date")),
                    "track": norm_track(row.get("track")),
                    "day_bucket": clean(row.get("day_bucket")).upper(),
                }
                for row in frame.to_dict("records")
            ]

    built = build_calendar_rows(today=reference_date)
    return [
        {
            "race_date": clean(row.get("race_date")),
            "track": norm_track(row.get("track")),
            "day_bucket": clean(row.get("day_bucket")).upper(),
        }
        for row in built
    ]


def meeting_for_bucket(rows: list[dict[str, object]], bucket: str) -> str:
    for row in rows:
        if clean(row.get("day_bucket")).upper() == bucket:
            return norm_track(row.get("track"))
    return ""


def count_rows_for_meeting(path: Path, meeting_date: str, meeting_track: str) -> int:
    if not meeting_date or not meeting_track:
        return 0

    frame = read_frame(path)
    if frame.empty:
        return 0

    date_col = first_matching_column(list(frame.columns), ["race_date", "meeting_date", "date"])
    track_col = first_matching_column(list(frame.columns), ["track", "meeting_name", "meeting", "location", "track_name"])
    if not date_col or not track_col:
        return 0

    date_keys = frame[date_col].map(clean).str[:10]
    track_keys = frame[track_col].map(norm_track)
    return int(((date_keys == meeting_date) & (track_keys == meeting_track)).sum())


def build_status(today_meeting: str, universe_rows: int, runner_rows: int) -> str:
    if not today_meeting:
        return "FAIL_NO_TODAY_MEETING"
    if universe_rows > 0 and runner_rows > 0:
        return "PASS_PROMOTED_WITH_RUNNERS"
    if universe_rows > 0 and runner_rows == 0:
        return "PASS_PROMOTED_PENDING_RUNNERS"
    return "PASS_PROMOTED_PENDING_FIELDS"


def append_row(path: Path, row: dict[str, object]) -> None:
    existing_rows: list[dict[str, object]] = []
    if path.exists() and path.stat().st_size > 0:
        try:
            with path.open("r", newline="", encoding="utf-8-sig") as handle:
                existing_rows = list(csv.DictReader(handle))
        except Exception:
            existing_rows = []

    existing_rows.append({field: row.get(field, "") for field in FIELDS})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing_rows)


def build_actual_row() -> dict[str, object]:
    current_date = today_local()
    calendar = calendar_rows_for()
    today_meeting = meeting_for_bucket(calendar, "TODAY")
    tomorrow_meeting = meeting_for_bucket(calendar, "TOMORROW")
    day2_meeting = meeting_for_bucket(calendar, "DAY+2")

    universe_rows = count_rows_for_meeting(UNIVERSE_PATH, current_date.isoformat(), today_meeting)
    runner_rows = count_rows_for_meeting(RUNNER_BOARD_PATH, current_date.isoformat(), today_meeting)

    return {
        "run_timestamp": datetime.now(LOCAL_TZ).isoformat(timespec="seconds"),
        "today_date": current_date.isoformat(),
        "today_meeting": today_meeting,
        "tomorrow_meeting": tomorrow_meeting,
        "day2_meeting": day2_meeting,
        "calendar_rows": len(calendar),
        "universe_rows": universe_rows,
        "runner_rows": runner_rows,
        "status": build_status(today_meeting, universe_rows, runner_rows),
    }


def simulate_rollover(from_date: date, to_date: date) -> list[dict[str, object]]:
    simulation_rows: list[dict[str, object]] = []
    for reference_date in [from_date, to_date]:
        calendar = calendar_rows_for(reference_date)
        simulation_rows.append(
            {
                "today_date": reference_date.isoformat(),
                "today_meeting": meeting_for_bucket(calendar, "TODAY"),
                "tomorrow_meeting": meeting_for_bucket(calendar, "TOMORROW"),
                "day2_meeting": meeting_for_bucket(calendar, "DAY+2"),
                "calendar_rows": len(calendar),
            }
        )
    return simulation_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate-from", default="")
    parser.add_argument("--simulate-to", default="")
    return parser.parse_args()


def parse_iso_date(value: str) -> date | None:
    text = clean(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def main() -> None:
    args = parse_args()
    actual_row = build_actual_row()
    append_row(OUT, actual_row)

    print("[EDGEIQ_DATE_ROLLOVER_AUDIT_V1] COMPLETE")
    print(f"today_date={actual_row['today_date']}")
    print(f"today_meeting={actual_row['today_meeting']}")
    print(f"tomorrow_meeting={actual_row['tomorrow_meeting']}")
    print(f"day2_meeting={actual_row['day2_meeting']}")
    print(f"calendar_rows={actual_row['calendar_rows']}")
    print(f"universe_rows={actual_row['universe_rows']}")
    print(f"runner_rows={actual_row['runner_rows']}")
    print(f"status={actual_row['status']}")
    print(f"wrote={OUT}")

    simulate_from = parse_iso_date(args.simulate_from)
    simulate_to = parse_iso_date(args.simulate_to)
    if simulate_from and simulate_to:
        print("[EDGEIQ_DATE_ROLLOVER_AUDIT_V1] SIMULATION")
        for row in simulate_rollover(simulate_from, simulate_to):
            print(
                f"{row['today_date']} TODAY={row['today_meeting']} "
                f"TOMORROW={row['tomorrow_meeting']} DAY2={row['day2_meeting']} "
                f"calendar_rows={row['calendar_rows']}"
            )


if __name__ == "__main__":
    main()
