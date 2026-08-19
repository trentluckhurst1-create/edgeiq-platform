from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"
MARKET_TAPE_PATH = DATA_DIR / "edgeiq_market_tape.csv"
MARKET_VELOCITY_PATH = DATA_DIR / "edgeiq_market_velocity_v1.csv"
SPORTSBET_LIVE_PATH = DATA_DIR / "sportsbet_live_market_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_market_intelligence_v1.csv"
AUDIT_PATH = DATA_DIR / "edgeiq_market_intelligence_v1_audit.csv"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "edgeiq_price",
    "market_price",
    "opening_price",
    "previous_price",
    "market_move_pct",
    "market_direction",
    "market_signal",
    "market_intelligence_note",
    "data_confidence",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def canonical_horse_key(value: str | None) -> str:
    raw = text(value).upper()
    pattern = "|".join(COUNTRY_SUFFIXES)
    raw = re.sub(rf"\s*\(({pattern})\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"[^A-Z0-9]+", "", raw)
    for suffix in COUNTRY_SUFFIXES:
        if raw.endswith(suffix) and len(raw) > len(suffix) + 3:
            return raw[: -len(suffix)]
    return raw


def normalise_track(value: str | None) -> str:
    raw = text(value).upper()
    raw = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", raw).strip()
    raw = re.sub(r"[^A-Z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def normalise_race_no(value: str | None) -> str:
    raw = text(value).upper()
    match = re.search(r"\d+", raw)
    return match.group(0) if match else raw


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        text(row.get("race_date") or row.get("date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        canonical_horse_key(row.get("horse_key") or row.get("horse")),
    )


def tape_runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        text(row.get("race_date") or row.get("date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        canonical_horse_key(row.get("horse_key") or row.get("horse")),
    )


def velocity_runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        "",
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        canonical_horse_key(row.get("horse_key") or row.get("horse")),
    )


def to_float(value: Any) -> float | None:
    raw = text(value)
    if not raw or raw.upper() in {"-", "NA", "N/A", "NULL", "NONE"}:
        return None
    cleaned = raw.replace("$", "").replace("%", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def first_number(row: dict[str, str], columns: list[str]) -> float | None:
    for column in columns:
        value = to_float(row.get(column))
        if value is not None and value > 0:
            return value
    return None


def price_text(value: float | None) -> str:
    if value is None or value <= 0:
        return ""
    return f"{value:.2f}"


def pct_text(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def dollar(value: float | None) -> str:
    if value is None or value <= 0:
        return "-"
    return f"${value:.2f}"


def latest_timestamp(row: dict[str, str]) -> str:
    return text(
        row.get("market_capture_timestamp")
        or row.get("market_captured_at")
        or row.get("sportsbet_timestamp")
        or row.get("timestamp")
        or row.get("snapshot_time")
        or row.get("built_at")
    )


def build_latest_lookup(rows: list[dict[str, str]], key_fn) -> dict[tuple[str, str, str, str], dict[str, str]]:
    lookup: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = key_fn(row)
        if not key[-1]:
            continue
        existing = lookup.get(key)
        if not existing or latest_timestamp(row) >= latest_timestamp(existing):
            lookup[key] = row
    return lookup


def movement_reference(live_row: dict[str, str], tape_row: dict[str, str] | None, velocity_row: dict[str, str] | None) -> tuple[float | None, float | None, str]:
    opening = first_number(live_row, ["open_price", "opening_price"])
    previous = first_number(live_row, ["previous_price", "prev_price", "mid_price", "close_price"])
    source = "live_feed"

    if tape_row:
        opening = opening or first_number(tape_row, ["open_price", "opening_price"])
        previous = previous or first_number(tape_row, ["previous_price", "prev_price"])
        if first_number(tape_row, ["open_price", "previous_price", "prev_price"]):
            source = "market_tape"

    if velocity_row:
        previous = previous or first_number(velocity_row, ["prev_price", "previous_price"])
        if first_number(velocity_row, ["prev_price", "previous_price"]):
            source = "market_velocity"

    return opening, previous, source


def current_market_price(live_row: dict[str, str], sportsbet_row: dict[str, str] | None, tape_row: dict[str, str] | None) -> float | None:
    live_price = first_number(live_row, ["sportsbet_price", "market_price", "live_price", "ui_price", "fixed_win"])
    if live_price is not None:
        return live_price
    if sportsbet_row:
        sportsbet_price = first_number(sportsbet_row, ["sportsbet_price", "price_win", "live_price"])
        if sportsbet_price is not None:
            return sportsbet_price
    if tape_row:
        return first_number(tape_row, ["sportsbet_price", "live_price"])
    return None


def edgeiq_price(live_row: dict[str, str]) -> float | None:
    return first_number(live_row, ["edgeiq_price", "rated_price", "ui_fair_price", "fair_price", "rated_price_v5_2_review"])


def move_pct(current: float | None, reference: float | None) -> float | None:
    if current is None or reference is None or current <= 0 or reference <= 0:
        return None
    return ((current / reference) - 1.0) * 100.0


def market_direction(current: float | None, reference: float | None, move: float | None) -> str:
    if current is None or reference is None or move is None:
        return "UNKNOWN"
    if abs(move) < 2.0:
        return "STABLE"
    return "FIRMING" if current < reference else "DRIFTING"


def market_signal(direction: str) -> str:
    if direction == "FIRMING":
        return "MARKET_SUPPORT"
    if direction == "DRIFTING":
        return "MARKET_DRIFT"
    if direction == "STABLE":
        return "STABLE_MARKET"
    return "NO_MARKET_HISTORY"


def market_note(direction: str, current: float | None, reference: float | None) -> str:
    if direction == "FIRMING":
        return f"Market has firmed from {dollar(reference)} to {dollar(current)}."
    if direction == "DRIFTING":
        return f"Market has drifted from {dollar(reference)} to {dollar(current)}."
    if direction == "STABLE":
        return "Current market is stable."
    return "No reliable market movement history available."


def confidence(current: float | None, opening: float | None, previous: float | None, source: str) -> str:
    if current is None:
        return "NO_MARKET"
    if previous is not None or opening is not None:
        return "HIGH" if source in {"market_tape", "market_velocity"} else "MEDIUM"
    return "LOW"


def build_market_intelligence() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    tape_rows = read_csv(MARKET_TAPE_PATH)
    velocity_rows = read_csv(MARKET_VELOCITY_PATH)
    sportsbet_rows = read_csv(SPORTSBET_LIVE_PATH)

    tape_lookup = build_latest_lookup(tape_rows, tape_runner_key)
    sportsbet_lookup = build_latest_lookup(sportsbet_rows, runner_key)
    velocity_lookup = build_latest_lookup(velocity_rows, velocity_runner_key)

    output_rows: list[dict[str, Any]] = []
    tape_matches = 0
    velocity_matches = 0
    sportsbet_matches = 0

    for live_row in live_rows:
        key = runner_key(live_row)
        if not key[-1]:
            continue

        tape_row = tape_lookup.get(key)
        velocity_key = ("", key[1], key[2], key[3])
        velocity_row = velocity_lookup.get(velocity_key)
        sportsbet_row = sportsbet_lookup.get(key)

        if tape_row:
            tape_matches += 1
        if velocity_row:
            velocity_matches += 1
        if sportsbet_row:
            sportsbet_matches += 1

        market = current_market_price(live_row, sportsbet_row, tape_row)
        opening, previous, movement_source = movement_reference(live_row, tape_row, velocity_row)
        reference = previous or opening
        move = move_pct(market, reference)
        direction = market_direction(market, reference, move)

        output_rows.append(
            {
                "race_date": key[0],
                "track": text(live_row.get("track")),
                "race_no": text(live_row.get("race_no")),
                "horse": text(live_row.get("horse")),
                "horse_key": key[3],
                "edgeiq_price": price_text(edgeiq_price(live_row)),
                "market_price": price_text(market),
                "opening_price": price_text(opening),
                "previous_price": price_text(previous),
                "market_move_pct": pct_text(move),
                "market_direction": direction,
                "market_signal": market_signal(direction),
                "market_intelligence_note": market_note(direction, market, reference),
                "data_confidence": confidence(market, opening, previous, movement_source),
            }
        )

    direction_counts = Counter(row["market_direction"] for row in output_rows)
    signal_counts = Counter(row["market_signal"] for row in output_rows)
    confidence_counts = Counter(row["data_confidence"] for row in output_rows)

    audit = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "live_feed_rows_loaded": len(live_rows),
        "market_tape_rows_loaded": len(tape_rows),
        "market_velocity_rows_loaded": len(velocity_rows),
        "sportsbet_live_rows_loaded": len(sportsbet_rows),
        "output_rows": len(output_rows),
        "rows_with_market_price": sum(1 for row in output_rows if row["market_price"]),
        "rows_with_edgeiq_price": sum(1 for row in output_rows if row["edgeiq_price"]),
        "rows_with_opening_price": sum(1 for row in output_rows if row["opening_price"]),
        "rows_with_previous_price": sum(1 for row in output_rows if row["previous_price"]),
        "market_tape_exact_matches": tape_matches,
        "market_velocity_matches": velocity_matches,
        "sportsbet_live_exact_matches": sportsbet_matches,
        "market_direction_counts": "; ".join(f"{name}:{count}" for name, count in sorted(direction_counts.items())),
        "market_signal_counts": "; ".join(f"{name}:{count}" for name, count in sorted(signal_counts.items())),
        "data_confidence_counts": "; ".join(f"{name}:{count}" for name, count in sorted(confidence_counts.items())),
        "movement_threshold": "STABLE if absolute move < 2%; FIRMING if current price shorter than previous/opening; DRIFTING if longer.",
        "diagnosis": "Current live feed and Sportsbet provide current prices. Current open/previous history is sparse; market_tape and velocity have no current exact runner matches.",
        "status": "MARKET_INTELLIGENCE_V1_BUILT",
    }

    return output_rows, audit


def main() -> None:
    output_rows, audit = build_market_intelligence()
    write_csv(OUTPUT_PATH, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT_PATH, [audit], list(audit.keys()))

    print(f"Market intelligence rows written: {len(output_rows)}")
    print(f"Audit written: {AUDIT_PATH}")
    print(f"Status: {audit['status']}")
    print(f"Rows with market price: {audit['rows_with_market_price']}")
    print(f"Rows with previous/opening: {audit['rows_with_previous_price']} / {audit['rows_with_opening_price']}")
    print(f"Direction counts: {audit['market_direction_counts']}")


if __name__ == "__main__":
    main()
