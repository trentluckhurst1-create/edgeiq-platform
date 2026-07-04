from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from edgeiq_csv_utils import clean, file_age_seconds, first, race_no, read_csv, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_race_state_engine.csv"
LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
SELECTOR = DATA / "edgeiq_active_race_selector.csv"

FIELDS = ["built_at", "track", "race_no", "race_time", "minutes_to_jump", "race_state", "state_reason", "price_age_seconds"]

try:
    LOCAL_TZ = ZoneInfo("Australia/Sydney")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=10), name="Australia/Sydney")


def parse_time_value(value: object, now: datetime) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ)
    except ValueError:
        pass
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M%p", "%I:%M %p"):
        try:
            parsed_time = datetime.strptime(text.upper(), fmt).time().replace(second=0, microsecond=0)
            return datetime.combine(now.date(), parsed_time, tzinfo=LOCAL_TZ)
        except ValueError:
            pass
    return None


def to_float(value: object) -> float | None:
    text = clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def state(minutes: float | None, price_age: float | None, has_prices: bool) -> tuple[str, str]:
    if minutes is None:
        return ("OPEN" if has_prices else "STANDBY", "missing_time_price_based")
    if minutes > 90:
        return "PREOPEN", "more_than_90_minutes"
    if minutes > 25:
        return "STANDBY", "future_race_standby"
    if minutes > 3:
        return "NEXT_UP", "next_race_window"
    if minutes > -1:
        return "JUMPING", "jump_window"
    if minutes > -5:
        return "ACTIVE", "late_market_or_jump_hold"
    if minutes > -25:
        return "CLOSED", "recently_closed"
    if price_age is not None and price_age < 300 and has_prices and minutes > -45:
        return "CLOSED", "recent_prices_after_jump"
    return "RESULTED", "rollover_complete"


def live_price_lookup(live_rows: list[dict[str, str]]) -> dict[tuple[str, str], bool]:
    lookup: dict[tuple[str, str], bool] = {}
    for row in live_rows:
        track = first(row, ["track", "meeting", "track_name"])
        rn = race_no(first(row, ["race_no", "race_number", "race"]))
        if not track or not rn:
            continue
        has_price = bool(first(row, ["ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win"]))
        key = (track, rn)
        lookup[key] = lookup.get(key, False) or has_price
    return lookup


def race_sources(selector: list[dict[str, str]], live: list[dict[str, str]]) -> list[dict[str, str]]:
    selector_lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in selector:
        track = first(row, ["track", "meeting", "track_name"])
        rn = race_no(first(row, ["race_no", "race_number", "race"]))
        if track and rn:
            selector_lookup[(track, rn)] = row
    if live:
        grouped: dict[tuple[str, str], dict[str, str]] = {}
        for row in live:
            track = first(row, ["track", "meeting", "track_name"])
            rn = race_no(first(row, ["race_no", "race_number", "race"]))
            if track and rn and (track, rn) not in grouped:
                selector_row = selector_lookup.get((track, rn), {})
                grouped[(track, rn)] = {
                    **selector_row,
                    **row,
                    "race_time": first(row, ["race_time", "jump_time", "start_time", "time"]) or first(selector_row, ["race_time", "jump_time", "start_time", "time"]),
                    "minutes_to_jump": first(row, ["minutes_to_jump"]) or first(selector_row, ["minutes_to_jump"]),
                }
        return list(grouped.values())
    if selector:
        return selector
    grouped: dict[tuple[str, str], dict[str, str]] = {}
    for row in live:
        track = first(row, ["track", "meeting", "track_name"])
        rn = race_no(first(row, ["race_no", "race_number", "race"]))
        if track and rn and (track, rn) not in grouped:
            grouped[(track, rn)] = row
    return list(grouped.values())


def minutes_to_jump(row: dict[str, str], now: datetime) -> float | None:
    supplied = to_float(first(row, ["minutes_to_jump"]))
    if supplied is not None:
        return round(supplied, 1)
    dt = parse_time_value(first(row, ["race_time", "jump_time", "start_time", "time"]), now)
    if not dt:
        return None
    return round((dt - now).total_seconds() / 60, 1)


def main() -> None:
    now = datetime.now(LOCAL_TZ)
    built_at = now.isoformat(timespec="seconds")
    selector = read_csv(SELECTOR)
    live = read_csv(LIVE)
    price_age = file_age_seconds(LIVE)
    has_prices_by_race = live_price_lookup(live)

    rows = []
    seen: set[tuple[str, str]] = set()
    for row in race_sources(selector, live):
        track = first(row, ["track", "meeting", "track_name"])
        rn = race_no(first(row, ["race_no", "race_number", "race"]))
        if not track or not rn or (track, rn) in seen:
            continue
        seen.add((track, rn))
        minutes = minutes_to_jump(row, now)
        race_time = first(row, ["race_time", "jump_time", "start_time", "time"])
        race_state, reason = state(minutes, price_age, has_prices_by_race.get((track, rn), False))
        rows.append({
            "built_at": built_at,
            "track": track,
            "race_no": rn,
            "race_time": race_time,
            "minutes_to_jump": "" if minutes is None else round(minutes, 1),
            "race_state": race_state,
            "state_reason": reason,
            "price_age_seconds": "" if price_age is None else price_age,
        })

    rows.sort(key=lambda row: (
        0 if row["race_state"] in {"NEXT_UP", "JUMPING", "ACTIVE"} else 1 if row["race_state"] in {"STANDBY", "PREOPEN"} else 2,
        abs(to_float(row["minutes_to_jump"]) or 9999),
        clean(row["track"]),
        race_no(row["race_no"]),
    ))
    write_csv(OUT, rows, FIELDS)
    print("=" * 100)
    print("EDGEIQ RACE STATE ENGINE")
    print("=" * 100)
    print("ROWS:", len(rows))
    print("OUT:", OUT)
    for row in rows[:12]:
        print(row)


if __name__ == "__main__":
    main()
