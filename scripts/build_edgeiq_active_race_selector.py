from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from audit_edgeiq_current_day_source_inventory_v1 import (
    DAY2,
    TODAY,
    TOMORROW,
    get_display_track,
    get_track_config,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_CANDIDATES = [
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv",
]

OUT = DATA / "edgeiq_active_race_selector.csv"
LOCAL_TZ = ZoneInfo("Australia/Sydney")

FIELDS = [
    "meeting_key",
    "race_key",
    "track",
    "race_no",
    "race_date",
    "race_time",
    "minutes_to_jump",
    "race_state",
    "is_live",
    "priority_rank",
    "default_ui_focus",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def norm_track(value: object) -> str:
    return " ".join(clean(value).upper().split())


def canonical_track(value: object) -> str:
    selected_track = get_display_track()
    aliases = {norm_track(alias) for alias in get_track_config(selected_track).get("aliases", set())}
    track = norm_track(value)
    return selected_track if track in aliases else track


def parse_race_dt(value: object):
    raw = clean(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ)
    except ValueError:
        return None


def race_state(minutes_to_jump: float | None, supplied: str) -> str:
    supplied_state = clean(supplied).upper()
    if supplied_state in {"SCRATCHED", "RESULTED", "CLOSED", "ACTIVE", "NEXT_UP", "STANDBY", "PREOPEN", "TIME_TBC"}:
        return supplied_state
    if minutes_to_jump is None:
        return "TIME_TBC"
    if minutes_to_jump > 90:
        return "PREOPEN"
    if minutes_to_jump > 25:
        return "STANDBY"
    if minutes_to_jump > 3:
        return "NEXT_UP"
    if minutes_to_jump > -5:
        return "ACTIVE"
    if minutes_to_jump > -25:
        return "CLOSED"
    return "RESULTED"


def load_source_rows() -> tuple[list[dict[str, str]], Path]:
    for path in SOURCE_CANDIDATES:
        if not path.exists():
            continue
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        if rows:
            return rows, path
    raise SystemExit(
        "Missing active selector source feed. Checked: "
        + ", ".join(str(path) for path in SOURCE_CANDIDATES)
    )


def write_rows(rows: list[dict[str, object]]) -> None:
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def determine_target_date(source_rows: list[dict[str, str]], selected_track: str) -> str:
    track_rows = [
        row for row in source_rows
        if canonical_track(row.get("track")) == selected_track and clean(row.get("race_date"))[:10]
    ]
    if not track_rows:
        return ""

    available_dates = {clean(row.get("race_date"))[:10] for row in track_rows if clean(row.get("race_date"))[:10]}
    for candidate in [TODAY, TOMORROW, DAY2]:
        if candidate in available_dates:
            return candidate

    return sorted(available_dates)[-1]


def build_selector() -> tuple[list[dict[str, object]], str, Path]:
    selected_track = get_display_track()
    source_rows, source_path = load_source_rows()
    target_date = determine_target_date(source_rows, selected_track)

    if not target_date:
        raise SystemExit(
            f"No rows found for selected track {selected_track or '<blank>'} in source {source_path}"
        )

    grouped: dict[str, dict[str, object]] = {}

    for row in source_rows:
        race_date = clean(row.get("race_date"))[:10]
        track = canonical_track(row.get("track"))
        if race_date != target_date or track != selected_track:
            continue

        race_no = clean(row.get("race_no"))
        if not race_no:
            continue

        race_key = clean(row.get("race_key")) or f"{race_date}_{selected_track}_R{race_no}"
        meeting_key = clean(row.get("meeting_key")) or f"{race_date}_{selected_track}"
        race_dt = parse_race_dt(row.get("race_time"))
        minutes = clean(row.get("minutes_to_jump"))
        try:
            minutes_value = float(minutes) if minutes else None
        except ValueError:
            minutes_value = None
        state = race_state(minutes_value, row.get("race_state", ""))

        candidate = {
            "meeting_key": meeting_key,
            "race_key": race_key,
            "track": selected_track,
            "race_no": race_no,
            "race_date": race_date,
            "race_time": row.get("race_time", ""),
            "minutes_to_jump": "" if minutes_value is None else f"{minutes_value:.1f}",
            "race_state": state,
            "is_live": "YES" if state in {"ACTIVE", "NEXT_UP"} else "NO",
            "_sort_time": race_dt or datetime.max.replace(tzinfo=LOCAL_TZ),
            "_sort_race_no": int("".join(ch for ch in race_no if ch.isdigit()) or "999"),
        }

        current = grouped.get(race_key)
        if current is None or (candidate["_sort_time"], candidate["_sort_race_no"]) < (current["_sort_time"], current["_sort_race_no"]):
            grouped[race_key] = candidate

    races = sorted(grouped.values(), key=lambda row: (row["_sort_time"], row["_sort_race_no"]))

    default_index = None
    for i, row in enumerate(races):
        try:
            minutes = float(row["minutes_to_jump"]) if row["minutes_to_jump"] != "" else None
        except ValueError:
            minutes = None
        if row["race_state"] in {"ACTIVE", "NEXT_UP", "STANDBY", "PREOPEN"} and (minutes is None or minutes >= -15):
            default_index = i
            break
    if default_index is None and races:
        default_index = len(races) - 1
    if default_index is None:
        default_index = 0

    output = []
    for idx, row in enumerate(races, start=1):
        output.append(
            {
                "meeting_key": row["meeting_key"],
                "race_key": row["race_key"],
                "track": row["track"],
                "race_no": row["race_no"],
                "race_date": row["race_date"],
                "race_time": row["race_time"],
                "minutes_to_jump": row["minutes_to_jump"],
                "race_state": row["race_state"],
                "is_live": row["is_live"],
                "priority_rank": idx,
                "default_ui_focus": "YES" if idx - 1 == default_index else "NO",
            }
        )

    return output, target_date, source_path


def main() -> None:
    selected_track = get_display_track()
    output, target_date, source_path = build_selector()
    write_rows(output)
    default_row = next((row for row in output if row["default_ui_focus"] == "YES"), {})

    print("=" * 90)
    print("EDGEIQ ACTIVE RACE SELECTOR")
    print("=" * 90)
    print(f"TARGET_DATE={target_date}")
    print(f"TRACK={selected_track}")
    print(f"SOURCE={source_path}")
    print(f"ROWS={len(output)}")
    print(f"DEFAULT={default_row}")
    print(f"OUT={OUT}")


if __name__ == "__main__":
    main()
