from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
ENRICHED_FORM = DATA / "edgeiq_form_guide_enriched_v2.json"
CURRENT_MAP = DATA / "edgeiq_current_map_v1.json"
MARKET_FEED = DATA / "edgeiq_market_terminal_feed_v1.csv"
RACE_DIR = DATA / "races"
RUNNER_DIR = DATA / "runners"
RACE_INDEX = RACE_DIR / "index.json"
RUNNER_INDEX = RUNNER_DIR / "index.json"


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def slug(value: Any) -> str:
    raw = text(value).lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or "item"


def norm_track(value: Any) -> str:
    raw = text(value).upper()
    raw = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", raw)
    raw = re.sub(r"\b(RACECOURSE|RACING|TRACK)\b", " ", raw)
    return re.sub(r"[^A-Z0-9]+", "", raw)


def norm_runner(value: Any) -> str:
    raw = text(value).upper()
    raw = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", raw)
    raw = raw.replace("'", "").replace("’", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", raw)


def race_no(value: Any) -> str:
    match = re.search(r"\d+", text(value).upper().replace("R", ""))
    return str(int(match.group(0))) if match else ""


def identity(date_value: Any, meeting: Any, race_number: Any, runner_name: Any) -> tuple[str, str, str, str]:
    return (text(date_value)[:10], norm_track(meeting), race_no(race_number), norm_runner(runner_name))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def build_enriched_index() -> dict[tuple[str, str, str, str], dict[str, Any]]:
    payload = read_json(ENRICHED_FORM)
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for race in payload.get("races", []) if isinstance(payload.get("races"), list) else []:
        if not isinstance(race, dict):
            continue
        date_value = race.get("raceDate")
        meeting = race.get("meeting")
        number = race.get("raceNumber")
        for runner in race.get("runners", []) if isinstance(race.get("runners"), list) else []:
            if not isinstance(runner, dict):
                continue
            key = identity(date_value, meeting, number, runner.get("runnerName") or runner.get("horse"))
            if all(key):
                out[key] = runner
    return out


def build_map_index() -> dict[tuple[str, str, str, str], dict[str, Any]]:
    payload = read_json(CURRENT_MAP)
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in payload.get("runners", []) if isinstance(payload.get("runners"), list) else []:
        if not isinstance(row, dict):
            continue
        key = identity(row.get("raceDate"), row.get("meeting"), row.get("raceNumber"), row.get("runnerName"))
        if all(key):
            out[key] = row
    return out


def build_market_index() -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in read_csv(MARKET_FEED):
        key = identity(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("horse"))
        if all(key):
            out[key] = row
    return out


def scalar(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("value")
    return value


def enrich_runner(runner: dict[str, Any], enriched: dict[str, Any] | None, map_row: dict[str, Any] | None, market_row: dict[str, str] | None) -> dict[str, Any]:
    full = dict(runner)
    official = dict(runner.get("official")) if isinstance(runner.get("official"), dict) else {}
    source = dict(runner.get("source")) if isinstance(runner.get("source"), dict) else {}

    if enriched:
        for key in (
            "rating", "epi", "edgeiqPrice", "marketPrice", "earlySpeed", "lateSpeed",
            "suitability", "raceShape", "formMomentum", "careerRecord", "trackRecord",
            "distanceRecord", "trackDistanceRecord", "conditionProfile", "preparationProfile",
        ):
            if key in enriched and enriched.get(key) not in (None, "", [], {}):
                source[key] = enriched.get(key)
        full_form = enriched.get("fullForm")
        if isinstance(full_form, list) and full_form:
            full["historicalRuns"] = full_form
        evidence = enriched.get("evidenceRuns")
        if isinstance(evidence, list) and evidence:
            full["evidenceRuns"] = evidence

    if map_row:
        for key in ("projectedZone", "projectedRank", "earlySpeed", "runStyle", "raceShape", "evidenceCoverage"):
            value = map_row.get(key)
            if value not in (None, ""):
                source[key] = value

    if market_row:
        field_map = {
            "market": "market",
            "open": "marketOpen",
            "high": "marketHigh",
            "low": "marketLow",
            "move": "marketMove",
            "edgeiq_price": "edgeiqPriceCurrent",
            "edge": "edge",
            "market_availability_status": "marketAvailabilityStatus",
            "market_freshness_status": "marketFreshnessStatus",
            "market_observed_at": "marketObservedAt",
            "market_is_live": "marketIsLive",
        }
        for source_key, target_key in field_map.items():
            value = text(market_row.get(source_key))
            if value:
                source[target_key] = value
        current_market = text(market_row.get("market"))
        if current_market:
            try:
                official["market"] = f"${float(current_market):.2f}"
            except ValueError:
                official["market"] = current_market
        current_fair = text(market_row.get("edgeiq_price"))
        if current_fair:
            source["edgeiqPrice"] = current_fair

    full["official"] = official
    full["source"] = source
    full.setdefault("historicalRuns", [])
    full.setdefault("evidenceRuns", [])
    return full


def lightweight_runner(runner: dict[str, Any], detail_path: str) -> dict[str, Any]:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    summary_source = {
        key: value
        for key, value in source.items()
        if key in {
            "scratched", "is_scratched", "runner_status", "status", "gear", "gear_changes",
            "market", "price", "barrier", "weight", "jockey", "trainer", "runner_number",
            "number", "silks", "form", "last_five", "marketAvailabilityStatus", "marketFreshnessStatus",
        }
    }
    summary_source["runnerDetailPath"] = detail_path
    summary_source["lightweightRunner"] = True
    return {
        "official": official,
        "source": summary_source,
        "historicalRuns": [],
        "evidenceRuns": [],
    }


def main() -> int:
    if not CATALOG.exists():
        print("EDGEIQ_RACE_DETAIL_SHARDS_V3 FAIL catalog_missing")
        return 1

    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    meetings = [m for m in payload.get("meetings", []) if isinstance(m, dict)]
    enriched_index = build_enriched_index()
    map_index = build_map_index()
    market_index = build_market_index()

    for directory in (RACE_DIR, RUNNER_DIR):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    race_records: list[dict[str, Any]] = []
    runner_records: list[dict[str, Any]] = []
    race_total_bytes = 0
    runner_total_bytes = 0
    enriched_matches = 0
    map_matches = 0
    market_matches = 0

    for meeting in meetings:
        date_value = text(meeting.get("date"))[:10]
        meeting_key = text(meeting.get("meetingKey"))
        meeting_name = text(meeting.get("meeting"))
        races = meeting.get("races", []) if isinstance(meeting.get("races"), list) else []
        for race in races:
            if not isinstance(race, dict):
                continue
            race_key = text(race.get("raceKey"))
            race_number = race.get("raceNumber")
            race_copy = dict(race)
            full_runners = race.get("runners", []) if isinstance(race.get("runners"), list) else []
            summary_runners: list[dict[str, Any]] = []

            for runner_index, runner in enumerate(full_runners):
                if not isinstance(runner, dict):
                    continue
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                runner_number = text(official.get("number") or official.get("no")) or str(runner_index + 1)
                runner_name = text(official.get("runner"))
                key = identity(date_value, meeting_name, race_number, runner_name)
                enriched = enriched_index.get(key)
                map_row = map_index.get(key)
                market_row = market_index.get(key)
                enriched_matches += 1 if enriched else 0
                map_matches += 1 if map_row else 0
                market_matches += 1 if market_row else 0
                full_runner = enrich_runner(runner, enriched, map_row, market_row)

                runner_filename = f"{date_value}_{slug(meeting_key)}_{slug(race_key)}_{runner_index + 1:02d}.json"
                runner_path = RUNNER_DIR / runner_filename
                public_runner_path = f"/data/runners/{runner_filename}"
                runner_detail = {
                    "schemaVersion": "edgeiq_runner_detail_v2",
                    "generatedAt": payload.get("generatedAt"),
                    "date": date_value,
                    "meetingKey": meeting_key,
                    "raceKey": race_key,
                    "runnerIndex": runner_index,
                    "runnerNumber": runner_number,
                    "runnerName": runner_name,
                    "runner": full_runner,
                }
                runner_path.write_text(json.dumps(runner_detail, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
                runner_size = runner_path.stat().st_size
                runner_total_bytes += runner_size
                runner_records.append({
                    "date": date_value,
                    "meetingKey": meeting_key,
                    "raceKey": race_key,
                    "runnerIndex": runner_index,
                    "runnerNumber": runner_number,
                    "runnerName": runner_name,
                    "path": public_runner_path,
                    "bytes": runner_size,
                    "enrichedForm": bool(enriched),
                    "map": bool(map_row),
                    "market": bool(market_row),
                })
                summary_runners.append(lightweight_runner(full_runner, public_runner_path))

            race_copy["runners"] = summary_runners
            race_filename = f"{date_value}_{slug(meeting_key)}_{slug(race_key)}.json"
            race_path = RACE_DIR / race_filename
            race_detail = {
                "schemaVersion": "edgeiq_race_detail_v3",
                "generatedAt": payload.get("generatedAt"),
                "date": date_value,
                "meetingKey": meeting_key,
                "raceKey": race_key,
                "race": race_copy,
            }
            race_path.write_text(json.dumps(race_detail, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
            race_size = race_path.stat().st_size
            race_total_bytes += race_size
            race_records.append({
                "date": date_value,
                "meetingKey": meeting_key,
                "raceKey": race_key,
                "raceNumber": race.get("raceNumber"),
                "path": f"/data/races/{race_filename}",
                "bytes": race_size,
                "runners": len(summary_runners),
            })

    RACE_INDEX.write_text(json.dumps({
        "schemaVersion": "edgeiq_race_detail_index_v3",
        "generatedAt": payload.get("generatedAt"),
        "sourceCatalog": CATALOG.name,
        "races": race_records,
        "totalBytes": race_total_bytes,
    }, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    RUNNER_INDEX.write_text(json.dumps({
        "schemaVersion": "edgeiq_runner_detail_index_v2",
        "generatedAt": payload.get("generatedAt"),
        "sourceCatalog": CATALOG.name,
        "runners": runner_records,
        "totalBytes": runner_total_bytes,
        "enrichedFormMatches": enriched_matches,
        "mapMatches": map_matches,
        "marketMatches": market_matches,
    }, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    print("EDGEIQ_RACE_DETAIL_SHARDS_V3 PASS")
    print(f"RACES={len(race_records)}")
    print(f"RUNNERS={len(runner_records)}")
    print(f"ENRICHED_FORM_MATCHES={enriched_matches}")
    print(f"MAP_MATCHES={map_matches}")
    print(f"MARKET_MATCHES={market_matches}")
    print(f"RACE_TOTAL_BYTES={race_total_bytes}")
    print(f"RUNNER_TOTAL_BYTES={runner_total_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
