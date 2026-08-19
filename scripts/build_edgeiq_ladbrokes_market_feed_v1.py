from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RAW = DATA / "ladbrokes_market_probe_raw"
LEGACY = DATA / "ladbrokes_affiliate_market_odds.csv"
OUT = DATA / "edgeiq_ladbrokes_market_feed_v1.csv"
GENERIC = DATA / "edgeiq_market_feed_current_v1.csv"

FIELDS = ["race_date", "track", "race_no", "race_name", "runner_name", "runner_number", "market_price", "market_status", "source", "source_url", "captured_at"]


def text(value: Any) -> str:
    return str(value or "").strip()


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def rows_from_raw() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not RAW.exists():
        return rows
    captured_at = datetime.now().isoformat(timespec="seconds")
    for path in RAW.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in walk(payload):
            runner = text(node.get("runner_name") or node.get("entrant_name") or node.get("horse"))
            price = text(node.get("fixed_win") or node.get("market_price") or node.get("price") or node.get("odds"))
            if not runner or not price:
                continue
            rows.append(
                {
                    "race_date": text(node.get("race_date") or node.get("date")),
                    "track": text(node.get("track") or node.get("meeting_name") or node.get("venue")),
                    "race_no": text(node.get("race_no") or node.get("race_number")),
                    "race_name": text(node.get("race_name") or node.get("name")),
                    "runner_name": runner,
                    "runner_number": text(node.get("runner_number") or node.get("number")),
                    "market_price": price,
                    "market_status": text(node.get("market_status") or node.get("status")) or "Market Available",
                    "source": "LADBROKES_AFFILIATE_API",
                    "source_url": str(path),
                    "captured_at": captured_at,
                }
            )
    return rows


def rows_from_legacy() -> list[dict[str, Any]]:
    if not LEGACY.exists():
        return []
    rows: list[dict[str, Any]] = []
    with LEGACY.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "race_date": text(row.get("race_date")),
                    "track": text(row.get("track") or row.get("meeting_name")),
                    "race_no": text(row.get("race_no")),
                    "race_name": text(row.get("race_name")),
                    "runner_name": text(row.get("horse")),
                    "runner_number": text(row.get("runner_number")),
                    "market_price": text(row.get("fixed_win")),
                    "market_status": "Scratched" if text(row.get("is_scratched")).upper() == "TRUE" else ("Market Available" if text(row.get("fixed_win")) else "Pending"),
                    "source": "LADBROKES_AFFILIATE_ARCHIVE",
                    "source_url": str(LEGACY),
                    "captured_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
    return rows


def write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = rows_from_raw()
    if not rows:
        rows = rows_from_legacy()
    write(OUT, rows)
    write(GENERIC, rows)
    print(f"Ladbrokes market feed rows={len(rows)}")


if __name__ == "__main__":
    main()
