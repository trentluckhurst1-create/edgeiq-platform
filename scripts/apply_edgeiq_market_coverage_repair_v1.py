from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
MARKET_TERMINAL = DATA / "edgeiq_market_terminal_feed_v1.csv"
SPORTSBET = DATA / "sportsbet_live_market_v1.csv"
TAB_MARKET = DATA / "edgeiq_tab_market_v1.csv"
FORM_ENRICHED = DATA / "edgeiq_form_guide_enriched_v2.json"
OUT_JSON = DATA / "edgeiq_market_coverage_repair_v1_apply.json"
OUT_TXT = DATA / "edgeiq_market_coverage_repair_v1_apply.txt"


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "null", "nan", "n/a", "na", "-", "missing"}:
        return ""
    return text


def normalise(value: Any) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def number_text(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        number = float(text.replace("$", "").replace(",", ""))
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return str(number)


def race_key(date: Any, track: Any, race_no: Any) -> str:
    return f"{clean(date)}|{normalise(track)}|{number_text(race_no)}"


def runner_name(runner: dict[str, Any]) -> str:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    return (
        clean(official.get("runner"))
        or clean(source.get("horseName"))
        or clean(source.get("runnerName"))
        or clean(source.get("horse"))
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def catalog_universe() -> tuple[list[dict[str, str]], set[str], set[tuple[str, str, str, str]]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    runners: list[dict[str, str]] = []
    race_keys: set[str] = set()
    runner_keys: set[tuple[str, str, str, str]] = set()
    for meeting in payload.get("meetings", []) if isinstance(payload, dict) else []:
        if not isinstance(meeting, dict):
            continue
        date = clean(meeting.get("date"))
        track = clean(meeting.get("meeting"))
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict):
                continue
            race_no = number_text(race.get("raceNumber"))
            key = race_key(date, track, race_no)
            race_keys.add(key)
            for runner in race.get("runners", []) or []:
                if not isinstance(runner, dict):
                    continue
                horse = runner_name(runner)
                runner_key = (date, normalise(track), race_no, normalise(horse))
                runner_keys.add(runner_key)
                runners.append(
                    {
                        "race_date": date,
                        "track": track,
                        "race_no": race_no,
                        "race_key": key,
                        "horse": horse,
                        "runner_key": "|".join(runner_key),
                    }
                )
    return runners, race_keys, runner_keys


def source_profile(path: Path, date_fields: list[str], track_fields: list[str], race_fields: list[str], horse_fields: list[str], runner_keys: set[tuple[str, str, str, str]]) -> dict[str, Any]:
    rows = read_csv(path)
    dates: set[str] = set()
    tracks: set[str] = set()
    keys: set[tuple[str, str, str, str]] = set()
    price_rows = 0
    for row in rows:
        date = next((clean(row.get(field)) for field in date_fields if clean(row.get(field))), "")
        track = next((clean(row.get(field)) for field in track_fields if clean(row.get(field))), "")
        race_no = next((number_text(row.get(field)) for field in race_fields if number_text(row.get(field))), "")
        horse = next((clean(row.get(field)) for field in horse_fields if clean(row.get(field))), "")
        if date:
            dates.add(date)
        if track:
            tracks.add(track)
        key = (date, normalise(track), race_no, normalise(horse))
        if all(key):
            keys.add(key)
        if any(clean(row.get(field)) for field in ["market", "sportsbet_price", "live_price", "tab_fixed_win", "tab_tote_win"]):
            price_rows += 1
    matches = len(keys & runner_keys)
    return {
        "exists": path.exists(),
        "rows": len(rows),
        "date_count": len(dates),
        "dates": sorted(dates),
        "track_count": len(tracks),
        "tracks_sample": sorted(tracks)[:12],
        "price_rows": price_rows,
        "runner_matches": matches,
        "current_source_rows": sum(1 for key in keys if key in runner_keys),
    }


def form_enriched_profile(runner_keys: set[tuple[str, str, str, str]]) -> dict[str, Any]:
    if not FORM_ENRICHED.exists():
        return {"exists": False, "races": 0, "runner_matches": 0, "dates": []}
    payload = json.loads(FORM_ENRICHED.read_text(encoding="utf-8"))
    keys: set[tuple[str, str, str, str]] = set()
    dates: set[str] = set()
    races = 0
    for race in payload.get("races", []) if isinstance(payload, dict) else []:
        if not isinstance(race, dict):
            continue
        races += 1
        date = clean(race.get("raceDate"))
        track = clean(race.get("meeting"))
        race_no = number_text(race.get("raceNumber"))
        if date:
            dates.add(date)
        for runner in race.get("runners", []) or []:
            if isinstance(runner, dict):
                keys.add((date, normalise(track), race_no, normalise(runner.get("runnerName"))))
    return {
        "exists": True,
        "races": races,
        "dates": sorted(dates),
        "runner_matches": len(keys & runner_keys),
    }


def main() -> None:
    if not CATALOG.exists():
        raise FileNotFoundError(CATALOG)
    if not MARKET_TERMINAL.exists():
        raise FileNotFoundError(MARKET_TERMINAL)

    catalog_runners, catalog_races, runner_keys = catalog_universe()
    terminal_rows = read_csv(MARKET_TERMINAL)
    status_counts = Counter(clean(row.get("row_status")) or "unknown" for row in terminal_rows)
    row_status_counts = Counter(clean(row.get("status")) or "unknown" for row in terminal_rows)
    market_rows = sum(1 for row in terminal_rows if clean(row.get("market")))
    open_rows = sum(1 for row in terminal_rows if clean(row.get("open")))
    move_rows = sum(1 for row in terminal_rows if clean(row.get("move")))
    edgeiq_price_rows = sum(1 for row in terminal_rows if clean(row.get("edgeiq_price")))
    edge_rows = sum(1 for row in terminal_rows if clean(row.get("edge")))
    source_counts = Counter(clean(row.get("source")) or "unknown" for row in terminal_rows)

    sportsbet_profile = source_profile(
        SPORTSBET,
        ["race_date", "meeting_date", "date"],
        ["track", "meeting"],
        ["race_no", "raceNumber"],
        ["horse", "runner"],
        runner_keys,
    )
    tab_profile = source_profile(
        TAB_MARKET,
        ["meeting_date", "race_date", "date"],
        ["track", "meeting"],
        ["race_no", "raceNumber"],
        ["horse", "runner"],
        runner_keys,
    )
    enriched_profile = form_enriched_profile(runner_keys)

    current_external_matches = (
        int(sportsbet_profile["runner_matches"])
        + int(tab_profile["runner_matches"])
        + int(enriched_profile["runner_matches"])
    )
    action = "NO_FEED_CHANGE"
    reason = "NO_CURRENT_EXTERNAL_MARKET_SOURCE_ROWS"
    if current_external_matches:
        action = "REVIEW_REQUIRED"
        reason = "CURRENT_EXTERNAL_MARKET_SOURCE_ROWS_EXIST"

    missing_market = len(terminal_rows) - market_rows
    missing_edgeiq_price = len(terminal_rows) - edgeiq_price_rows
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = {
        "marker": "EDGEIQ_MARKET_COVERAGE_REPAIR_V1_APPLY_COMPLETE",
        "generated_at": generated_at,
        "action": action,
        "reason": reason,
        "catalog_races": len(catalog_races),
        "catalog_runners": len(catalog_runners),
        "terminal_rows": len(terminal_rows),
        "market_rows": market_rows,
        "market_missing_rows": missing_market,
        "open_rows": open_rows,
        "move_rows": move_rows,
        "edgeiq_price_rows": edgeiq_price_rows,
        "edgeiq_price_missing_rows": missing_edgeiq_price,
        "edge_rows": edge_rows,
        "row_status_counts": dict(status_counts),
        "display_status_counts": dict(row_status_counts),
        "source_counts": dict(source_counts),
        "sportsbet_source": sportsbet_profile,
        "tab_source": tab_profile,
        "form_enriched_source": enriched_profile,
        "recovered_rows": 0,
        "before_market_rows": market_rows,
        "after_market_rows": market_rows,
        "before_edgeiq_price_rows": edgeiq_price_rows,
        "after_edgeiq_price_rows": edgeiq_price_rows,
        "unavailable_reasons": {
            "market_missing": "No current external market source rows beyond catalog-embedded odds.",
            "edgeiq_price_missing": "No current governed EDGEiQ price source matched the active catalogue.",
            "open_or_fluc_missing": "TAB/open/fluctuation source is stale and has no current active-catalogue runner matches.",
        },
    }

    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                "EDGEIQ_MARKET_COVERAGE_REPAIR_V1",
                f"generated_at={generated_at}",
                f"action={action}",
                f"reason={reason}",
                f"catalog_races={len(catalog_races)}",
                f"catalog_runners={len(catalog_runners)}",
                f"terminal_rows={len(terminal_rows)}",
                f"market_rows={market_rows}",
                f"edgeiq_price_rows={edgeiq_price_rows}",
                f"sportsbet_runner_matches={sportsbet_profile['runner_matches']}",
                f"tab_runner_matches={tab_profile['runner_matches']}",
                f"form_enriched_runner_matches={enriched_profile['runner_matches']}",
                "recovered_rows=0",
            ]
        ),
        encoding="utf-8",
    )
    print(f"EDGEIQ_MARKET_COVERAGE_REPAIR_V1 action={action} reason={reason} market_rows={market_rows}/{len(terminal_rows)} edgeiq_price_rows={edgeiq_price_rows}/{len(terminal_rows)}")


if __name__ == "__main__":
    main()
