from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "ladbrokes_market_api_probe_v1.csv"
SUMMARY = DATA / "ladbrokes_market_api_probe_v1_summary.csv"
RAW = DATA / "ladbrokes_market_probe_raw"

BASE = "https://api-affiliates.ladbrokes.com.au/affiliates/v1/racing/meetings"
HEADERS = {
    "User-Agent": "EDGEiQ market API probe/1.0",
    "Accept": "application/json,text/plain,*/*",
}


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


def count_meetings(payload: Any) -> tuple[list[str], int, int]:
    names: set[str] = set()
    race_ids: set[str] = set()
    runners = 0
    for node in walk(payload):
        name = text(node.get("name") or node.get("meeting_name") or node.get("venue") or node.get("track"))
        if name and any(k in node for k in ("races", "events", "meeting_id", "venue", "track")):
            names.add(name)
        event_id = text(node.get("event_id") or node.get("id"))
        if event_id and any(k in node for k in ("runners", "entrants", "markets", "race_number", "race_no")):
            race_ids.add(event_id)
        runner_name = text(node.get("runner_name") or node.get("name") or node.get("entrant_name") or node.get("horse"))
        if runner_name and any(k in node for k in ("fixed_win", "price", "odds", "runner_number", "barrier")):
            runners += 1
    return sorted(names)[:20], len(race_ids), runners


def payload_flags(raw: bytes, payload: Any | None) -> tuple[bool, bool, bool]:
    blob = raw[:250000].decode("utf-8", errors="ignore").lower()
    contains_racing = any(token in blob for token in ("racing", "thoroughbred", "horse", "meeting", "race"))
    contains_prices = any(token in blob for token in ("fixed_win", "price", "odds", "dividend"))
    contains_runner_names = False
    if payload is not None:
        for node in walk(payload):
            if any(text(node.get(k)) for k in ("runner_name", "entrant_name", "horse")):
                contains_runner_names = True
                break
    if not contains_runner_names:
        contains_runner_names = bool(re.search(r'"(?:runner_name|entrant_name|horse|name)"\s*:', blob))
    return contains_racing, contains_runner_names, contains_prices


def fetch(url: str) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return int(response.status), response.read(), ""
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read(), f"HTTPError: {exc.reason}"
    except Exception as exc:
        return 0, b"", f"{type(exc).__name__}: {exc}"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    today = date.today()
    rows: list[dict[str, Any]] = []
    json_hits = 0
    price_hits = 0
    coverage: list[str] = []

    for offset, label in [(0, "TODAY"), (1, "TOMORROW"), (2, "DAY+2")]:
        target = today + timedelta(days=offset)
        params = {
            "enc": "json",
            "category": "T",
            "country": "AUS",
            "date_from": target.isoformat(),
            "date_to": target.isoformat(),
            "limit": "200",
        }
        url = f"{BASE}?{urllib.parse.urlencode(params)}"
        status, raw, note = fetch(url)
        payload = None
        raw_path = ""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else None
        except Exception as exc:
            note = (note + f"; JSON parse failed: {exc}").strip("; ")
        if payload is not None:
            json_hits += 1
            raw_path = str(RAW / f"ladbrokes_meetings_{label.lower().replace('+', 'plus')}_{target.isoformat()}.json")
            Path(raw_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        contains_racing, contains_runner_names, contains_prices = payload_flags(raw, payload)
        meeting_names, race_count, runner_count = count_meetings(payload) if payload is not None else ([], 0, 0)
        if contains_prices:
            price_hits += 1
        if status == 200 and contains_racing:
            coverage.append(label)
        rows.append(
            {
                "url": url,
                "status": status,
                "response_length": len(raw),
                "contains_racing": "YES" if contains_racing else "NO",
                "contains_runner_names": "YES" if contains_runner_names else "NO",
                "contains_prices": "YES" if contains_prices else "NO",
                "date_coverage": label,
                "meeting_names": " | ".join(meeting_names),
                "race_count": race_count,
                "runner_count": runner_count,
                "notes": note or ("raw_json_saved=" + raw_path if raw_path else "response captured"),
            }
        )

    write_csv(
        OUT,
        rows,
        ["url", "status", "response_length", "contains_racing", "contains_runner_names", "contains_prices", "date_coverage", "meeting_names", "race_count", "runner_count", "notes"],
    )
    write_csv(
        SUMMARY,
        [
            {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
            {"metric": "documented_endpoint", "value": BASE},
            {"metric": "json_responses", "value": json_hits},
            {"metric": "price_response_hits", "value": price_hits},
            {"metric": "date_coverage_found", "value": " | ".join(coverage) if coverage else "NONE"},
            {"metric": "endpoint_found", "value": "YES" if json_hits else "NO"},
            {"metric": "notes", "value": "Affiliate endpoint may require identification headers if responses are 401/403."},
        ],
        ["metric", "value"],
    )
    print(f"Ladbrokes probe complete: json_responses={json_hits}, price_hits={price_hits}, coverage={'|'.join(coverage) if coverage else 'NONE'}")


if __name__ == "__main__":
    main()
