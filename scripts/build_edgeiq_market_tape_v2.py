from __future__ import annotations

import csv
import hashlib
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SPORTSBET_IN = DATA / "sportsbet_live_market_v1.csv"
LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_market_tape_v2.csv"
AUDIT = DATA / "edgeiq_market_tape_v2_audit.csv"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

FIELDS = [
    "snapshot_timestamp",
    "capture_timestamp_utc",
    "market_captured_at",
    "source_file",
    "source",
    "source_status",
    "market_source",
    "race_date",
    "track",
    "race_no",
    "race_time",
    "race_id",
    "horse",
    "horse_key",
    "sportsbet_price",
    "price_win",
    "sportsbet_event_id",
    "sportsbet_market_id",
    "selection_id",
    "event_id",
    "market_id",
    "market_type",
    "market_name",
    "event_name",
    "meeting_name",
    "state",
    "bookmaker",
    "source_url",
    "market_mover",
    "recent_odds_fluctuations",
    "is_scratched",
    "runner_status",
    "selection_status",
    "status_code",
    "match_confidence",
    "append_key",
    "source_row_hash",
]

AUDIT_FIELDS = [
    "metric",
    "value",
    "notes",
]


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


def parse_price(value: Any) -> float:
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


def price_text(value: Any) -> str:
    number = parse_price(value)
    if math.isnan(number) or number <= 0:
        return ""
    return f"{number:.2f}"


def first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def snapshot_timestamp(row: dict[str, str]) -> str:
    return first(row, ["market_captured_at", "capture_timestamp_utc", "timestamp"]) or datetime.now(timezone.utc).isoformat(timespec="seconds")


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("race_date") or row.get("date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        canonical_horse(row.get("horse_key") or row.get("horse")),
    )


def live_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("race_date") or row.get("date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        canonical_horse(row.get("horse_key") or row.get("horse")),
    )


def row_hash(row: dict[str, str]) -> str:
    material = "|".join(
        clean(row.get(name))
        for name in [
            "capture_timestamp_utc",
            "market_captured_at",
            "event_id",
            "market_id",
            "selection_id",
            "race_date",
            "track",
            "race_no",
            "horse_key",
            "sportsbet_price",
            "price_win",
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def append_key(row: dict[str, str]) -> str:
    selection = clean(row.get("selection_id")) or clean(row.get("horse_key"))
    return "|".join(
        [
            clean(row.get("snapshot_timestamp")),
            clean(row.get("race_date")),
            normalise_track(row.get("track")),
            normalise_race_no(row.get("race_no")),
            canonical_horse(row.get("horse_key") or row.get("horse")),
            selection,
        ]
    )


def build_snapshot_rows(sportsbet_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in sportsbet_rows:
        price = price_text(first(row, ["sportsbet_price", "price_win", "live_price", "market_price"]))
        race_date, track, race_no, horse_key = runner_key(row)
        mapped = {
            "snapshot_timestamp": snapshot_timestamp(row),
            "capture_timestamp_utc": clean(row.get("capture_timestamp_utc")),
            "market_captured_at": clean(row.get("market_captured_at")),
            "source_file": SPORTSBET_IN.name,
            "source": first(row, ["source"]) or "Sportsbet",
            "source_status": clean(row.get("source_status")),
            "market_source": clean(row.get("market_source")),
            "race_date": race_date,
            "track": clean(row.get("track")),
            "race_no": race_no,
            "race_time": clean(row.get("race_time")),
            "race_id": clean(row.get("race_id")),
            "horse": clean(row.get("horse")),
            "horse_key": horse_key,
            "sportsbet_price": price,
            "price_win": price_text(row.get("price_win")),
            "sportsbet_event_id": clean(row.get("event_id") or row.get("sportsbet_event_id")),
            "sportsbet_market_id": clean(row.get("market_id") or row.get("sportsbet_market_id")),
            "selection_id": clean(row.get("selection_id")),
            "event_id": clean(row.get("event_id") or row.get("sportsbet_event_id")),
            "market_id": clean(row.get("market_id") or row.get("sportsbet_market_id")),
            "market_type": clean(row.get("market_type")),
            "market_name": clean(row.get("market_name")),
            "event_name": clean(row.get("event_name")),
            "meeting_name": clean(row.get("meeting_name")),
            "state": clean(row.get("state")),
            "bookmaker": first(row, ["bookmaker"]) or "Sportsbet",
            "source_url": clean(row.get("source_url")),
            "market_mover": clean(row.get("market_mover")),
            "recent_odds_fluctuations": clean(row.get("recent_odds_fluctuations")),
            "is_scratched": clean(row.get("is_scratched")),
            "runner_status": clean(row.get("runner_status")),
            "selection_status": clean(row.get("selection_status")),
            "status_code": clean(row.get("status_code")),
            "match_confidence": clean(row.get("match_confidence")),
        }
        mapped["append_key"] = append_key(mapped)
        mapped["source_row_hash"] = row_hash(row)
        out.append(mapped)
    return out


def dedupe_append(existing: list[dict[str, str]], snapshots: list[dict[str, str]]) -> tuple[list[dict[str, str]], int, int]:
    seen: set[str] = set()
    merged: list[dict[str, str]] = []
    existing_duplicates = 0
    skipped_new = 0

    for row in existing:
        key = clean(row.get("append_key")) or append_key(row)
        normalised = {field: clean(row.get(field)) for field in FIELDS}
        normalised["append_key"] = key
        if key in seen:
            existing_duplicates += 1
            continue
        seen.add(key)
        merged.append(normalised)

    for row in snapshots:
        key = clean(row.get("append_key")) or append_key(row)
        if key in seen:
            skipped_new += 1
            continue
        seen.add(key)
        merged.append(row)

    merged.sort(key=lambda item: (clean(item.get("snapshot_timestamp")), clean(item.get("race_date")), normalise_track(item.get("track")), int(normalise_race_no(item.get("race_no")) or 0), clean(item.get("horse_key"))))
    return merged, existing_duplicates, skipped_new


def audit_rows(
    sportsbet_rows: list[dict[str, str]],
    snapshots: list[dict[str, str]],
    existing_rows: list[dict[str, str]],
    merged_rows: list[dict[str, str]],
    existing_duplicates: int,
    skipped_new: int,
) -> list[dict[str, str]]:
    live_rows = read_csv(LIVE_FEED)
    live_keys = {live_key(row) for row in live_rows if all(live_key(row))}
    tape_keys = {runner_key(row) for row in merged_rows if all(runner_key(row))}
    snapshot_keys = {runner_key(row) for row in snapshots if all(runner_key(row))}
    race_contexts = {(row.get("race_date", ""), normalise_track(row.get("track")), row.get("race_no", "")) for row in snapshots}
    snapshot_times = {clean(row.get("snapshot_timestamp")) for row in snapshots if clean(row.get("snapshot_timestamp"))}

    id_counts = {
        "sportsbet_event_id_nonblank": sum(1 for row in snapshots if clean(row.get("sportsbet_event_id"))),
        "sportsbet_market_id_nonblank": sum(1 for row in snapshots if clean(row.get("sportsbet_market_id"))),
        "selection_id_nonblank": sum(1 for row in snapshots if clean(row.get("selection_id"))),
        "sportsbet_price_nonblank": sum(1 for row in snapshots if clean(row.get("sportsbet_price"))),
    }
    source_status_counts = Counter(clean(row.get("source_status")) or "UNKNOWN" for row in sportsbet_rows)

    rows = [
        {"metric": "source_file", "value": str(SPORTSBET_IN), "notes": ""},
        {"metric": "source_rows_loaded", "value": str(len(sportsbet_rows)), "notes": ""},
        {"metric": "existing_v2_rows_loaded", "value": str(len(existing_rows)), "notes": ""},
        {"metric": "snapshot_candidate_rows", "value": str(len(snapshots)), "notes": ""},
        {"metric": "rows_added_this_run", "value": str(len(snapshots) - skipped_new), "notes": ""},
        {"metric": "duplicate_snapshot_rows_skipped", "value": str(skipped_new), "notes": "Append key is snapshot_timestamp + race_date + track + race_no + horse_key + selection_id/horse_key."},
        {"metric": "existing_duplicate_rows_removed", "value": str(existing_duplicates), "notes": ""},
        {"metric": "total_v2_rows", "value": str(len(merged_rows)), "notes": ""},
        {"metric": "snapshot_timestamps", "value": str(len(snapshot_times)), "notes": "; ".join(sorted(snapshot_times)[:5])},
        {"metric": "race_contexts_in_snapshot", "value": str(len(race_contexts)), "notes": ""},
        {"metric": "live_terminal_rows_loaded_for_key_check", "value": str(len(live_rows)), "notes": ""},
        {"metric": "snapshot_runner_keys_matching_live_terminal", "value": str(len(snapshot_keys & live_keys)), "notes": "Exact date + track + race_no + horse_key keys."},
        {"metric": "total_tape_runner_keys_matching_live_terminal", "value": str(len(tape_keys & live_keys)), "notes": "Exact date + track + race_no + horse_key keys."},
        {"metric": "source_status_counts", "value": "; ".join(f"{key}:{value}" for key, value in sorted(source_status_counts.items())), "notes": ""},
    ]
    for metric, value in id_counts.items():
        rows.append({"metric": metric, "value": str(value), "notes": "Snapshot rows only."})
    rows.append({"metric": "status", "value": "MARKET_TAPE_V2_BUILT", "notes": "Read from current Sportsbet snapshot and appended safely."})
    return rows


def main() -> None:
    sportsbet_rows = read_csv(SPORTSBET_IN)
    existing_rows = read_csv(OUT)
    snapshots = build_snapshot_rows(sportsbet_rows)
    merged, existing_duplicates, skipped_new = dedupe_append(existing_rows, snapshots)
    write_csv(OUT, merged, FIELDS)
    audit = audit_rows(sportsbet_rows, snapshots, existing_rows, merged, existing_duplicates, skipped_new)
    write_csv(AUDIT, audit, AUDIT_FIELDS)

    print("EDGEiQ Market Tape V2")
    print(f"source rows loaded: {len(sportsbet_rows)}")
    print(f"existing v2 rows: {len(existing_rows)}")
    print(f"snapshot candidates: {len(snapshots)}")
    print(f"rows added this run: {len(snapshots) - skipped_new}")
    print(f"duplicate snapshot rows skipped: {skipped_new}")
    print(f"total v2 rows: {len(merged)}")
    print(f"output: {OUT}")
    print(f"audit: {AUDIT}")


if __name__ == "__main__":
    main()
