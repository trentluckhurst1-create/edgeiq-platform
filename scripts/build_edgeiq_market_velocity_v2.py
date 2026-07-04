from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TAPE_IN = DATA / "edgeiq_market_tape_v2.csv"
LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_market_velocity_v2.csv"
AUDIT = DATA / "edgeiq_market_velocity_v2_audit.csv"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

FIELDS = [
    "snapshot_timestamp",
    "previous_snapshot_timestamp",
    "race_date",
    "track",
    "race_no",
    "race_time",
    "horse",
    "horse_key",
    "sportsbet_price",
    "previous_price",
    "open_price",
    "low_price",
    "high_price",
    "price_delta",
    "pct_move",
    "seconds_since_previous",
    "snapshots",
    "velocity_state",
    "pressure_rating",
    "sportsbet_event_id",
    "sportsbet_market_id",
    "selection_id",
    "runner_status",
    "selection_status",
    "market_source",
    "source_status",
    "append_key",
]

AUDIT_FIELDS = ["metric", "value", "notes"]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "n/a", "-"} else text


def canonical_horse(value: Any) -> str:
    text = clean(value).upper()
    suffix_pattern = "|".join(COUNTRY_SUFFIXES)
    text = re.sub(rf"\s*\(({suffix_pattern})\)\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Z0-9]", "", text)
    for suffix in COUNTRY_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix) + 3:
            return text[: -len(suffix)]
    return text


def normalise_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("race_date") or row.get("date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        canonical_horse(row.get("horse_key") or row.get("horse")),
    )


def parse_price(value: Any) -> float:
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


def price_text(value: float) -> str:
    if math.isnan(value) or value <= 0:
        return ""
    return f"{value:.2f}"


def number_text(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:.2f}"


def parse_time(value: Any) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def latest_time(row: dict[str, str]) -> datetime:
    return parse_time(row.get("snapshot_timestamp")) or datetime.min.replace(tzinfo=timezone.utc)


def movement_state(current: float, previous: float, pct: float) -> str:
    if math.isnan(current) or math.isnan(previous):
        return "NO_HISTORY"
    if abs(pct) < 2:
        return "STABLE"
    if current < previous:
        return "FIRMING"
    return "DRIFTING"


def pressure_rating(state: str, pct: float) -> str:
    if state == "NO_HISTORY":
        return "NO_HISTORY"
    if math.isnan(pct):
        return "UNKNOWN"
    magnitude = abs(pct)
    if magnitude >= 25:
        return "EXTREME"
    if magnitude >= 10:
        return "HIGH"
    if magnitude >= 4:
        return "MODERATE"
    return "LOW"


def build_velocity(tape_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in tape_rows:
        key = runner_key(row)
        if not all(key):
            continue
        grouped.setdefault(key, []).append(row)

    out: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        rows.sort(key=latest_time)
        latest = rows[-1]
        previous_rows = [row for row in rows[:-1] if parse_price(row.get("sportsbet_price")) > 0]
        previous = previous_rows[-1] if previous_rows else None
        current_price = parse_price(latest.get("sportsbet_price"))
        previous_price = parse_price(previous.get("sportsbet_price")) if previous else math.nan

        priced = [parse_price(row.get("sportsbet_price")) for row in rows if parse_price(row.get("sportsbet_price")) > 0]
        open_price = priced[0] if priced else math.nan
        low_price = min(priced) if priced else math.nan
        high_price = max(priced) if priced else math.nan

        if not math.isnan(current_price) and not math.isnan(previous_price) and previous_price > 0:
            delta = current_price - previous_price
            pct = (delta / previous_price) * 100.0
        else:
            delta = math.nan
            pct = math.nan

        latest_dt = parse_time(latest.get("snapshot_timestamp"))
        previous_dt = parse_time(previous.get("snapshot_timestamp")) if previous else None
        seconds = ""
        if latest_dt and previous_dt:
            seconds = str(max(0, int((latest_dt - previous_dt).total_seconds())))

        state = movement_state(current_price, previous_price, pct)
        out.append(
            {
                "snapshot_timestamp": clean(latest.get("snapshot_timestamp")),
                "previous_snapshot_timestamp": clean(previous.get("snapshot_timestamp")) if previous else "",
                "race_date": key[0],
                "track": clean(latest.get("track")),
                "race_no": key[2],
                "race_time": clean(latest.get("race_time")),
                "horse": clean(latest.get("horse")),
                "horse_key": key[3],
                "sportsbet_price": price_text(current_price),
                "previous_price": price_text(previous_price),
                "open_price": price_text(open_price),
                "low_price": price_text(low_price),
                "high_price": price_text(high_price),
                "price_delta": number_text(delta),
                "pct_move": number_text(pct),
                "seconds_since_previous": seconds,
                "snapshots": str(len(rows)),
                "velocity_state": state,
                "pressure_rating": pressure_rating(state, pct),
                "sportsbet_event_id": clean(latest.get("sportsbet_event_id") or latest.get("event_id")),
                "sportsbet_market_id": clean(latest.get("sportsbet_market_id") or latest.get("market_id")),
                "selection_id": clean(latest.get("selection_id")),
                "runner_status": clean(latest.get("runner_status")),
                "selection_status": clean(latest.get("selection_status")),
                "market_source": clean(latest.get("market_source")),
                "source_status": clean(latest.get("source_status")),
                "append_key": clean(latest.get("append_key")),
            }
        )

    out.sort(key=lambda row: (clean(row.get("race_date")), normalise_track(row.get("track")), int(normalise_race_no(row.get("race_no")) or 0), clean(row.get("horse_key"))))
    return out


def audit_rows(tape_rows: list[dict[str, str]], velocity_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    live_rows = read_csv(LIVE_FEED)
    live_keys = {runner_key(row) for row in live_rows if all(runner_key(row))}
    velocity_keys = {runner_key(row) for row in velocity_rows if all(runner_key(row))}
    state_counts = Counter(clean(row.get("velocity_state")) or "UNKNOWN" for row in velocity_rows)
    pressure_counts = Counter(clean(row.get("pressure_rating")) or "UNKNOWN" for row in velocity_rows)
    snapshot_counts = Counter(clean(row.get("snapshot_timestamp")) for row in velocity_rows)
    race_contexts = {(row.get("race_date", ""), normalise_track(row.get("track")), row.get("race_no", "")) for row in velocity_rows}

    rows = [
        {"metric": "source_file", "value": str(TAPE_IN), "notes": ""},
        {"metric": "tape_rows_loaded", "value": str(len(tape_rows)), "notes": ""},
        {"metric": "velocity_rows_written", "value": str(len(velocity_rows)), "notes": "One latest row per race_date + track + race_no + horse_key."},
        {"metric": "race_contexts", "value": str(len(race_contexts)), "notes": ""},
        {"metric": "live_terminal_rows_loaded_for_key_check", "value": str(len(live_rows)), "notes": ""},
        {"metric": "velocity_runner_keys_matching_live_terminal", "value": str(len(velocity_keys & live_keys)), "notes": "Exact date + track + race_no + horse_key keys."},
        {"metric": "sportsbet_event_id_nonblank", "value": str(sum(1 for row in velocity_rows if clean(row.get("sportsbet_event_id")))), "notes": ""},
        {"metric": "sportsbet_market_id_nonblank", "value": str(sum(1 for row in velocity_rows if clean(row.get("sportsbet_market_id")))), "notes": ""},
        {"metric": "selection_id_nonblank", "value": str(sum(1 for row in velocity_rows if clean(row.get("selection_id")))), "notes": ""},
        {"metric": "velocity_state_counts", "value": "; ".join(f"{key}:{value}" for key, value in sorted(state_counts.items())), "notes": ""},
        {"metric": "pressure_rating_counts", "value": "; ".join(f"{key}:{value}" for key, value in sorted(pressure_counts.items())), "notes": ""},
        {"metric": "latest_snapshot_counts", "value": "; ".join(f"{key}:{value}" for key, value in sorted(snapshot_counts.items())[:10]), "notes": ""},
        {"metric": "status", "value": "MARKET_VELOCITY_V2_BUILT", "notes": "Built from V2 tape with full race_date + track + race_no + horse_key keys."},
    ]
    return rows


def main() -> None:
    tape_rows = read_csv(TAPE_IN)
    velocity_rows = build_velocity(tape_rows)
    write_csv(OUT, velocity_rows, FIELDS)
    audit = audit_rows(tape_rows, velocity_rows)
    write_csv(AUDIT, audit, AUDIT_FIELDS)

    print("EDGEiQ Market Velocity V2")
    print(f"tape rows loaded: {len(tape_rows)}")
    print(f"velocity rows written: {len(velocity_rows)}")
    print(f"output: {OUT}")
    print(f"audit: {AUDIT}")


if __name__ == "__main__":
    main()
