from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edgeiq_csv_utils import build_lookup, clean, first, num, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
TRUTH = DATA / "edgeiq_market_truth_engine_v3.csv"
SUPPRESSION = DATA / "edgeiq_execution_suppression_v2.csv"
CLOCK = DATA / "edgeiq_race_clock_engine.csv"
MEMORY_OUT = DATA / "edgeiq_market_tape_memory.csv"
SUMMARY_OUT = DATA / "edgeiq_market_tape_summary.csv"

MEMORY_FIELDS = [
    "timestamp", "race_date", "track", "race_no", "horse", "horse_key", "live_price",
    "fair_price", "edge_pct", "suppression_action", "truth_grade", "lifecycle_state",
]

SUMMARY_FIELDS = [
    "race_date", "track", "race_no", "horse", "horse_key", "open_price", "last_price",
    "low_price", "high_price", "move_pct", "steam_drift", "snapshots", "first_seen",
    "last_seen", "market_volatility", "late_move_flag",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_timestamp(value: object) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone()
    except ValueError:
        return None


def race_key(row: dict[str, str]) -> str:
    return "|".join(runner_key(row).split("|")[:2])


def race_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        key = race_key(row)
        if key and key not in out:
            out[key] = row
    return out


def valid_date(row: dict[str, str]) -> bool:
    raw = clean(row.get("race_date"))
    if not raw:
        return True
    try:
        race_date = datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return True
    today = datetime.now().astimezone().date()
    return today <= race_date <= today + timedelta(days=2)


def price_from(row: dict[str, str]) -> str:
    value = first(row, ["live_price", "ui_price", "sportsbet_price", "market_price", "fixed_win", "current_price"])
    parsed = num(value)
    return "" if math.isnan(parsed) or parsed <= 0 else f"{parsed:.2f}"


def fair_from(row: dict[str, str]) -> str:
    value = first(row, ["fair_price", "ui_fair_price", "rated_price", "model_price", "execution_fair"])
    parsed = num(value)
    return "" if math.isnan(parsed) or parsed <= 0 else f"{parsed:.2f}"


def edge_from(row: dict[str, str]) -> str:
    value = first(row, ["edge_pct", "ui_edge_pct", "overlay_pct", "v3_edge_pct", "calibrated_edge_pct"])
    parsed = num(value)
    return "" if math.isnan(parsed) else f"{parsed:.2f}"


def merge_row(row: dict[str, str], maps: list[dict[str, dict[str, str]]], race_maps: list[dict[str, dict[str, str]]]) -> dict[str, str]:
    merged = dict(row)
    key = runner_key(row)
    rkey = race_key(row)
    for mapping in maps:
        extra = mapping.get(key)
        if extra:
            for col, value in extra.items():
                if clean(value) and not clean(merged.get(col)):
                    merged[col] = value
    for mapping in race_maps:
        extra = mapping.get(rkey)
        if extra:
            for col, value in extra.items():
                if clean(value) and not clean(merged.get(col)):
                    merged[col] = value
    return merged


def dedupe(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        key = (clean(row.get("timestamp")), runner_key(row))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def summarise(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(runner_key(row), []).append(row)

    out: list[dict[str, object]] = []
    for key, items in grouped.items():
        items.sort(key=lambda item: parse_timestamp(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc))
        priced = [(item, num(item.get("live_price"))) for item in items if not math.isnan(num(item.get("live_price"))) and num(item.get("live_price")) > 0]
        first_item = items[0]
        last_item = items[-1]
        if priced:
            open_price = priced[0][1]
            last_price = priced[-1][1]
            low_price = min(value for _, value in priced)
            high_price = max(value for _, value in priced)
            move_pct = ((last_price - open_price) / open_price) * 100 if open_price > 0 else math.nan
            volatility = ((high_price - low_price) / open_price) * 100 if open_price > 0 else math.nan
            if abs(move_pct) < 0.5:
                steam_drift = "FLAT"
            else:
                steam_drift = "STEAM" if move_pct < 0 else "DRIFT"
        else:
            open_price = last_price = low_price = high_price = move_pct = volatility = math.nan
            steam_drift = "NO_PRICE"

        lifecycle = clean(last_item.get("lifecycle_state")).upper()
        late = "YES" if (not math.isnan(move_pct) and abs(move_pct) >= 8 and lifecycle in {"NEXT_UP", "JUMPING", "INPLAY", "PHOTO"}) else "NO"
        out.append({
            "race_date": clean(last_item.get("race_date") or first_item.get("race_date")),
            "track": clean(last_item.get("track") or first_item.get("track")),
            "race_no": clean(last_item.get("race_no") or first_item.get("race_no")),
            "horse": clean(last_item.get("horse") or first_item.get("horse")),
            "horse_key": clean(last_item.get("horse_key") or first_item.get("horse_key")) or key.split("|")[-1],
            "open_price": "" if math.isnan(open_price) else f"{open_price:.2f}",
            "last_price": "" if math.isnan(last_price) else f"{last_price:.2f}",
            "low_price": "" if math.isnan(low_price) else f"{low_price:.2f}",
            "high_price": "" if math.isnan(high_price) else f"{high_price:.2f}",
            "move_pct": "" if math.isnan(move_pct) else f"{move_pct:.2f}",
            "steam_drift": steam_drift,
            "snapshots": len(items),
            "first_seen": clean(first_item.get("timestamp")),
            "last_seen": clean(last_item.get("timestamp")),
            "market_volatility": "" if math.isnan(volatility) else f"{volatility:.2f}",
            "late_move_flag": late,
        })
    return sorted(out, key=lambda row: (clean(row.get("race_date")), clean(row.get("track")), int(clean(row.get("race_no")) or 0), clean(row.get("horse"))))


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    universe = [row for row in read_csv(UNIVERSE) if valid_date(row)]
    live_map = build_lookup(read_csv(LIVE))
    truth_map = build_lookup(read_csv(TRUTH))
    suppression_map = build_lookup(read_csv(SUPPRESSION))
    clock_map = race_lookup(read_csv(CLOCK))
    existing = read_csv(MEMORY_OUT)
    stamp = now_iso()

    snapshots: list[dict[str, str]] = []
    for base in universe:
        merged = merge_row(base, [live_map, truth_map, suppression_map], [clock_map])
        snapshots.append({
            "timestamp": stamp,
            "race_date": first(merged, ["race_date", "date"]),
            "track": first(merged, ["track", "meeting"]),
            "race_no": first(merged, ["race_no", "race_number"]),
            "horse": first(merged, ["horse", "runner", "horse_name", "runner_name"]),
            "horse_key": first(merged, ["horse_key"]) or runner_key(merged).split("|")[-1],
            "live_price": price_from(merged),
            "fair_price": fair_from(merged),
            "edge_pct": edge_from(merged),
            "suppression_action": first(merged, ["suppression_action"]),
            "truth_grade": first(merged, ["truth_grade"]),
            "lifecycle_state": first(merged, ["lifecycle_state", "race_state"]),
        })

    memory = dedupe(existing + snapshots)
    write_csv(MEMORY_OUT, memory, MEMORY_FIELDS)
    summary = summarise(memory)
    write_csv(SUMMARY_OUT, summary, SUMMARY_FIELDS)

    print("=" * 90)
    print("EDGEIQ MARKET TAPE MEMORY")
    print("=" * 90)
    print("SNAPSHOTS ADDED:", len(snapshots))
    print("MEMORY ROWS:", len(memory))
    print("SUMMARY ROWS:", len(summary))
    print("OUT:", MEMORY_OUT)
    print("SUMMARY:", SUMMARY_OUT)


if __name__ == "__main__":
    main()
