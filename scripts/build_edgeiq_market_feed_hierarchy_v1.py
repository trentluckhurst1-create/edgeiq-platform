from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
LADBROKES = DATA / "edgeiq_ladbrokes_market_feed_v1.csv"
GENERIC = DATA / "edgeiq_market_feed_current_v1.csv"
LIVE_GOVERNED = DATA / "edgeiq_live_runner_board_governed_v1.csv"
LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
OUT = DATA / "edgeiq_market_feed_hierarchy_v1.csv"
SUMMARY = DATA / "edgeiq_market_feed_hierarchy_v1_summary.csv"

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "runner_name",
    "runner_number",
    "market_price",
    "market_status",
    "market_source",
    "market_source_rank",
    "source_url",
    "captured_at",
    "fallback_reason",
]


def text(value: Any) -> str:
    return str(value or "").strip()


def key_text(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def price(value: Any) -> str:
    raw = text(value).replace("$", "").replace(",", "")
    if not raw:
        return ""
    try:
        val = float(raw)
    except ValueError:
        return ""
    return f"{val:.2f}" if val > 0 else ""


def market_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        text(row.get("race_date")),
        key_text(row.get("track")),
        text(row.get("race_no")).replace("R", "").replace("r", ""),
        key_text(row.get("runner_name") or row.get("horse")),
    )


def choose_existing(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = market_key(row)
        if not key[3] or not price(row.get("market_price") or row.get("fixed_win")):
            continue
        source = text(row.get("source")).upper()
        rank = 1 if "API" in source and "ARCHIVE" not in source else 2
        current = out.get(key)
        if current is None or rank < int(current["market_source_rank"]):
            out[key] = {
                "race_date": text(row.get("race_date")),
                "track": text(row.get("track")),
                "race_no": text(row.get("race_no")),
                "runner_name": text(row.get("runner_name") or row.get("horse")),
                "runner_number": text(row.get("runner_number")),
                "market_price": price(row.get("market_price") or row.get("fixed_win")),
                "market_status": text(row.get("market_status")) or "Market Available",
                "market_source": "LADBROKES" if rank == 1 else "ARCHIVED",
                "market_source_rank": str(rank),
                "source_url": text(row.get("source_url")),
                "captured_at": text(row.get("captured_at")),
                "fallback_reason": "Primary Ladbrokes API price" if rank == 1 else "Archived Ladbrokes market price",
            }
    return out


def live_last_known(row: dict[str, str]) -> dict[str, str] | None:
    market_price = price(
        row.get("market_price")
        or row.get("display_market_price")
        or row.get("display_live_price")
        or row.get("live_price")
        or row.get("fixed_win")
        or row.get("tab_fixed_win")
    )
    if not market_price:
        return None
    return {
        "race_date": text(row.get("race_date")),
        "track": text(row.get("track")),
        "race_no": text(row.get("race_no")),
        "runner_name": text(row.get("runner_name") or row.get("horse")),
        "runner_number": text(row.get("runner_number") or row.get("horse_no") or row.get("saddlecloth")),
        "market_price": market_price,
        "market_status": "Market Available",
        "market_source": "LAST_KNOWN",
        "market_source_rank": "3",
        "source_url": str(LIVE_GOVERNED if LIVE_GOVERNED.exists() else LIVE_BOARD),
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "fallback_reason": "Last known live board market price",
    }


def pending_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "race_date": text(row.get("race_date")),
        "track": text(row.get("track")),
        "race_no": text(row.get("race_no")),
        "runner_name": text(row.get("runner_name") or row.get("horse")),
        "runner_number": text(row.get("runner_number") or row.get("horse_no") or row.get("saddlecloth")),
        "market_price": "",
        "market_status": "Market Pending",
        "market_source": "MARKET_PENDING",
        "market_source_rank": "4",
        "source_url": "",
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "fallback_reason": "No Ladbrokes, archived, or last-known market price available",
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ladbrokes_rows = read_rows(LADBROKES)
    generic_rows = read_rows(GENERIC)
    live_rows = read_rows(LIVE_GOVERNED) or read_rows(LIVE_BOARD)
    feed_index = choose_existing(ladbrokes_rows + generic_rows)

    output: list[dict[str, str]] = []
    used_keys: set[tuple[str, str, str, str]] = set()
    for live in live_rows:
        key = (
            text(live.get("race_date")),
            key_text(live.get("track")),
            text(live.get("race_no")).replace("R", "").replace("r", ""),
            key_text(live.get("runner_name") or live.get("horse")),
        )
        chosen = feed_index.get(key) or live_last_known(live) or pending_row(live)
        if not chosen.get("runner_number"):
            chosen["runner_number"] = text(live.get("horse_no") or live.get("saddlecloth"))
        output.append(chosen)
        used_keys.add(key)

    for key, row in feed_index.items():
        if key not in used_keys:
            output.append(row)

    source_counts: dict[str, int] = {}
    for row in output:
        source_counts[row["market_source"]] = source_counts.get(row["market_source"], 0) + 1

    summary_rows = [
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "rows", "value": len(output)},
        {"metric": "live_runner_rows", "value": len(live_rows)},
        {"metric": "ladbrokes_feed_rows", "value": len(ladbrokes_rows)},
        {"metric": "generic_feed_rows", "value": len(generic_rows)},
    ] + [{"metric": f"market_source_{source}", "value": count} for source, count in sorted(source_counts.items())]

    write_csv(OUT, output, FIELDS)
    write_csv(SUMMARY, summary_rows, ["metric", "value"])
    print(f"Market feed hierarchy built: rows={len(output)} sources={source_counts}")


if __name__ == "__main__":
    main()
