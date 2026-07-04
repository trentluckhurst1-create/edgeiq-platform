from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
SELECTOR = DATA / "edgeiq_active_race_selector.csv"
RACE_STATE = DATA / "edgeiq_race_state_engine.csv"
SETTLEMENT = DATA / "edgeiq_results_auto_settlement.csv"
OUT = DATA / "edgeiq_race_clock_engine.csv"

try:
    LOCAL_TZ = ZoneInfo("Australia/Sydney")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=10), name="Australia/Sydney")

FIELDS = [
    "meeting_key",
    "race_key",
    "race_date",
    "track",
    "race_no",
    "race_time",
    "minutes_to_jump",
    "clock_display",
    "lifecycle_state",
    "clock_confidence",
    "rollover_priority",
    "should_show_in_selector",
    "should_default_focus",
    "is_today",
    "is_tomorrow",
    "is_next_day",
    "reason",
]


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def race_no(value: object) -> int:
    digits = "".join(ch for ch in clean(value) if ch.isdigit())
    return int(digits) if digits else 0


def clean_track(value: object) -> str:
    return " ".join(clean(value).upper().replace("|", " ").replace("_", " ").split())


def meeting_key(race_date: object, track: object) -> str:
    return f"{clean(race_date)}_{clean_track(track)}"


def canonical_race_key(race_date: object, track: object, race_no_value: object) -> str:
    return f"{meeting_key(race_date, track)}_R{race_no(race_no_value)}"


def parse_date(value: object):
    text = clean(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def parse_minutes(value: object):
    text = clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_time_value(value: object, race_date) -> tuple[str, float | None]:
    text = clean(value)
    if not text:
        return "", None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        parsed = parsed.astimezone(LOCAL_TZ)
        return parsed.isoformat(timespec="minutes"), round((parsed - now_local()).total_seconds() / 60, 1)
    except ValueError:
        pass
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M%p", "%I:%M %p"):
        try:
            parsed_time = datetime.strptime(text.upper(), fmt).time().replace(second=0, microsecond=0)
            parsed = datetime.combine(race_date, parsed_time, tzinfo=LOCAL_TZ)
            return parsed.isoformat(timespec="minutes"), round((parsed - now_local()).total_seconds() / 60, 1)
        except ValueError:
            pass
    return text, None


def time_label(race_time: object) -> str:
    text = clean(race_time)
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ).strftime("%H:%M")
    except ValueError:
        pass
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M%p", "%I:%M %p"):
        try:
            return datetime.strptime(text.upper(), fmt).strftime("%H:%M")
        except ValueError:
            pass
    return text if ":" in text else ""


def clock_display(lifecycle: str, minutes: float | None, race_date, race_time: object) -> str:
    today = now_local().date()
    state = clean(lifecycle).upper()
    time_text = time_label(race_time)
    if state == "JUMPING":
        return "Jumping"
    if state in {"INPLAY", "PHOTO"}:
        return "Recently jumped"
    if state in {"RESULTED", "CLOSED"}:
        return "Closed"
    if minutes is None:
        return "Time TBC"
    if race_date > today:
        prefix = "Tomorrow" if race_date == today + timedelta(days=1) else race_date.strftime("%a")
        return f"{prefix} {time_text}".strip() if time_text else f"{prefix} time TBC"
    if minutes <= 0 and minutes > -5:
        return "Jumping"
    if minutes < 0 and minutes > -20:
        return "Recently jumped"
    if minutes < 0:
        return "Closed"
    if minutes < 60:
        return f"Jumps in {max(1, math.ceil(minutes))}m"
    hours = int(minutes // 60)
    mins = int(round(minutes % 60))
    return f"Jumps in {hours}h {mins:02d}m" if mins else f"Jumps in {hours}h"


def key(row: dict[str, str]) -> tuple[str, str, int]:
    return clean(row.get("race_date") or row.get("date")), clean(row.get("track")), race_no(row.get("race_no") or row.get("race_number"))


def race_key(track: object, race_no_value: object, race_date: object = "") -> tuple[str, str, int]:
    return clean(race_date), clean(track), race_no(race_no_value)


def by_race(rows: list[dict[str, str]]) -> dict[tuple[str, str, int], dict[str, str]]:
    out: dict[tuple[str, str, int], dict[str, str]] = {}
    for row in rows:
        candidates = [key(row), race_key(row.get("track"), row.get("race_no") or row.get("race_number"))]
        for item in candidates:
            if item[1] and item[2] and item not in out:
                out[item] = row
    return out


def result_lookup(rows: list[dict[str, str]]) -> set[tuple[str, str, int]]:
    resulted: set[tuple[str, str, int]] = set()
    for row in rows:
        status = clean(row.get("result_status") or row.get("result") or row.get("settlement_status")).upper()
        if status in {"SETTLED", "RESULTED", "FINAL", "OFFICIAL"}:
            resulted.add(key(row))
            resulted.add(race_key(row.get("track"), row.get("race_no") or row.get("race_number")))
    return resulted


def state_from(minutes: float | None, race_date, resulted: bool) -> tuple[str, str, str]:
    today = now_local().date()
    if resulted:
        return "RESULTED", "HIGH", "result_settlement_detected"
    if race_date < today:
        return "CLOSED", "HIGH", "stale_date_closed"
    if minutes is None:
        return "STANDBY", "LOW", "missing_race_time"
    if race_date > today:
        return "PREOPEN", "HIGH", "future_three_day_race"
    if minutes > 90:
        return "PREOPEN", "HIGH", "more_than_90_minutes"
    if minutes > 25:
        return "OPEN", "HIGH", "today_market_open"
    if minutes > 3:
        return "NEXT_UP", "HIGH", "next_to_jump_window"
    if minutes > -1:
        return "JUMPING", "HIGH", "jump_window"
    if minutes > -8:
        return "INPLAY", "MEDIUM", "post_jump_inplay_window"
    if minutes > -18:
        return "PHOTO", "MEDIUM", "recently_jumped_review_window"
    if minutes > -90:
        return "CLOSED", "HIGH", "closed_but_visible_for_review"
    return "RESULTED", "MEDIUM", "rollover_result_expected"


def day_flags(race_date) -> tuple[str, str, str]:
    today = now_local().date()
    return (
        "YES" if race_date == today else "NO",
        "YES" if race_date == today + timedelta(days=1) else "NO",
        "YES" if race_date == today + timedelta(days=2) else "NO",
    )


def priority(row: dict[str, object]) -> tuple[int, int, float, str, int]:
    today_rank = 0 if row["is_today"] == "YES" else 1 if row["is_tomorrow"] == "YES" else 2
    state = str(row["lifecycle_state"])
    state_rank = {
        "JUMPING": 0,
        "NEXT_UP": 1,
        "OPEN": 2,
        "PREOPEN": 3,
        "INPLAY": 4,
        "PHOTO": 5,
        "CLOSED": 6,
        "RESULTED": 7,
        "STANDBY": 8,
    }.get(state, 9)
    minutes = parse_minutes(row["minutes_to_jump"]) if row["minutes_to_jump"] != "" else None
    minute_rank = abs(minutes) if minutes is not None and minutes < 0 else minutes if minutes is not None else 99999.0
    if today_rank == 0 and state in {"CLOSED", "RESULTED"}:
        minute_rank = 1000.0 + abs(minutes or 0)
    return today_rank, state_rank, minute_rank, str(row["track"]), int(row["race_no"] or 0)


def main() -> None:
    universe = read_csv(UNIVERSE)
    selector_map = by_race(read_csv(SELECTOR))
    state_map = by_race(read_csv(RACE_STATE))
    resulted = result_lookup(read_csv(SETTLEMENT))
    today = now_local().date()
    max_date = today + timedelta(days=2)

    grouped: dict[tuple[str, str, int], dict[str, str]] = {}
    for row in universe:
        race_date = parse_date(row.get("race_date"))
        if race_date is None or race_date < today or race_date > max_date:
            continue
        race = key(row)
        if not race[1] or not race[2]:
            continue
        grouped.setdefault(race, row)

    rows: list[dict[str, object]] = []
    for race, row in grouped.items():
        race_date = parse_date(race[0]) or today
        selector = selector_map.get(race) or selector_map.get(("", race[1], race[2]), {})
        state_row = state_map.get(race) or state_map.get(("", race[1], race[2]), {})
        race_time, minutes = parse_time_value(clean(row.get("race_time")) or clean(selector.get("race_time")) or clean(state_row.get("race_time")), race_date)
        if minutes is None:
            minutes = parse_minutes(row.get("minutes_to_jump")) or parse_minutes(selector.get("minutes_to_jump")) or parse_minutes(state_row.get("minutes_to_jump"))
        lifecycle, confidence, reason = state_from(minutes, race_date, race in resulted or ("", race[1], race[2]) in resulted)
        state_override = clean(state_row.get("race_state") or state_row.get("lifecycle_state")).upper()
        if state_override in {"RESULTED", "CLOSED"} and lifecycle in {"STANDBY", "PREOPEN"}:
            lifecycle = state_override
            reason = "race_state_engine_override"
        is_today, is_tomorrow, is_next_day = day_flags(race_date)
        show = "YES" if lifecycle in {"PREOPEN", "OPEN", "NEXT_UP", "JUMPING", "INPLAY", "PHOTO", "CLOSED", "STANDBY"} else "NO"
        rows.append({
            "meeting_key": meeting_key(race[0], race[1]),
            "race_key": canonical_race_key(race[0], race[1], race[2]),
            "race_date": race[0],
            "track": race[1],
            "race_no": race[2],
            "race_time": race_time,
            "minutes_to_jump": "" if minutes is None else round(minutes, 1),
            "clock_display": clock_display(lifecycle, minutes, race_date, race_time),
            "lifecycle_state": lifecycle,
            "clock_confidence": confidence,
            "rollover_priority": 0,
            "should_show_in_selector": show,
            "should_default_focus": "NO",
            "is_today": is_today,
            "is_tomorrow": is_tomorrow,
            "is_next_day": is_next_day,
            "reason": reason,
        })

    rows.sort(key=priority)
    visible = [row for row in rows if row["should_show_in_selector"] == "YES"]
    focus_pool = [row for row in visible if row["is_today"] == "YES" and row["lifecycle_state"] in {"OPEN", "NEXT_UP", "JUMPING", "INPLAY", "PHOTO"}]
    if not focus_pool:
        focus_pool = [row for row in visible if row["is_today"] == "YES"]
    if not focus_pool:
        focus_pool = visible
    focus = focus_pool[0] if focus_pool else None
    for index, row in enumerate(rows, start=1):
        row["rollover_priority"] = index
        row["should_default_focus"] = "YES" if focus and row is focus else "NO"

    write_csv(OUT, rows, FIELDS)
    print("=" * 90)
    print("EDGEIQ RACE CLOCK ENGINE")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("DEFAULT:", focus or {})
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
