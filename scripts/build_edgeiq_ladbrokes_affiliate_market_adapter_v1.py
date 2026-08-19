from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "market-intelligence" / "ladbrokes"
PRIVATE_DATA = ROOT / "data" / "market" / "ladbrokes"
RAW_DIR = PRIVATE_DATA / "raw"
HISTORY = PRIVATE_DATA / "edgeiq_ladbrokes_market_observation_history_v1.csv"

CATALOG = PUBLIC_DATA / "edgeiq_three_day_product_catalog_v1.json"
WINDOW = PUBLIC_DATA / "edgeiq_three_day_window_v1.json"

RUNTIME_CSV = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_runtime_v1.csv"
RUNTIME_JSON = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_runtime_v1.json"
SUMMARY_CSV = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_adapter_v1_summary.csv"
AUDIT_CSV = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_adapter_v1_audit.csv"
PROOF_CSV = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_current_match_proof_v1.csv"

REFERENCE_JSON = DOCS / "edgeiq_ladbrokes_reference_inspection_v1.json"
REFERENCE_MD = DOCS / "edgeiq_ladbrokes_reference_inspection_v1.md"
TERMS_JSON = DOCS / "edgeiq_ladbrokes_api_terms_assessment_v1.json"
TERMS_MD = DOCS / "edgeiq_ladbrokes_api_terms_assessment_v1.md"
ADAPTER_AUDIT_JSON = DOCS / "edgeiq_ladbrokes_adapter_v1_audit.json"
ADAPTER_AUDIT_MD = DOCS / "edgeiq_ladbrokes_adapter_v1_audit.md"
SCHEMA_CSV = DOCS / "edgeiq_ladbrokes_provider_schema_v1.csv"
PROOF_JSON = DOCS / "edgeiq_ladbrokes_current_match_proof_v1.json"
PROOF_MD = DOCS / "edgeiq_ladbrokes_current_match_proof_v1.md"

BASE_URL = "https://api-affiliates.ladbrokes.com.au/affiliates/v1/racing"
OFFICIAL_DOCS_URL = "https://nedscode.github.io/affiliate-feeds/"
REFERENCE_REPO_URL = "https://github.com/Josh9456/Racing-Form-"
PREFERRED_ENV = ["EDGEIQ_LADBROKES_FROM", "EDGEIQ_LADBROKES_X_PARTNER"]
LEGACY_ENV = ["EDGEIQ_LADBROKES_EMAIL", "EDGEIQ_LADBROKES_PARTNER_NAME"]
REQUIRED_ENV = PREFERRED_ENV + LEGACY_ENV

RUNTIME_FIELDS = [
    "generated_at",
    "mode",
    "race_date",
    "canonical_meeting_key",
    "canonical_race_key",
    "canonical_runner_key",
    "track",
    "race_no",
    "horse",
    "runner_number",
    "provider_meeting_id",
    "provider_race_id",
    "provider_runner_id",
    "provider_horse",
    "provider_runner_number",
    "fixed_win",
    "fixed_place",
    "opening_price",
    "high_price",
    "low_price",
    "recent_price",
    "price_timestamp",
    "edgeiq_observed_at",
    "flucs_with_timestamp",
    "flucs_untimestamped",
    "fluctuation_status",
    "price_movement",
    "price_movement_status",
    "is_scratched",
    "scratch_time",
    "market_status",
    "race_status",
    "advertised_start",
    "actual_start",
    "market_availability_status",
    "market_freshness_status",
    "source_priority_rank",
    "source_confidence",
    "join_status",
    "runner_match_method",
    "raw_publication_status",
]

HISTORY_FIELDS = [
    "observation_id",
    "observed_at",
    "mode",
    "race_date",
    "track",
    "race_no",
    "horse",
    "runner_number",
    "provider_meeting_id",
    "provider_race_id",
    "provider_runner_id",
    "fixed_win",
    "fixed_place",
    "race_status",
    "is_scratched",
    "payload_hash",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def text(value: Any) -> str:
    if value is None:
        return ""
    result = str(value).strip()
    if result.lower() in {"none", "null", "nan", "n/a", "na"}:
        return ""
    return result


def number_text(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""
    try:
        number = float(raw.replace("$", "").replace(",", ""))
    except ValueError:
        return raw
    if number.is_integer():
        return str(int(number))
    return str(number)


def money_text(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""
    try:
        number = float(raw.replace("$", "").replace(",", ""))
    except ValueError:
        return ""
    if number <= 0:
        return ""
    return f"{number:.2f}"


def normalise(value: Any) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def bool_text(value: Any) -> str:
    raw = text(value).lower()
    return "true" if raw in {"true", "1", "yes", "scratched", "scr"} else "false"


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            write_csv(path, [], fieldnames)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def current_window_dates() -> list[str]:
    payload = read_json(WINDOW)
    dates = payload.get("dates") if isinstance(payload, dict) else []
    if isinstance(dates, list):
        result: list[str] = []
        for item in dates:
            if isinstance(item, dict):
                value = text(item.get("date"))
            else:
                value = text(item)
            if value:
                result.append(value[:10])
        if result:
            return result
    today = datetime.now().date().isoformat()
    return [today]


@dataclass
class CatalogRunner:
    race_date: str
    track: str
    race_no: str
    horse: str
    runner_number: str
    canonical_meeting_key: str
    canonical_race_key: str
    canonical_runner_key: str
    scratched: str


def catalog_runners() -> list[CatalogRunner]:
    payload = read_json(CATALOG)
    meetings = payload.get("meetings", []) if isinstance(payload, dict) else []
    rows: list[CatalogRunner] = []
    for meeting in meetings:
        if not isinstance(meeting, dict):
            continue
        race_date = text(meeting.get("date"))
        track = text(meeting.get("meeting") or meeting.get("track"))
        meeting_key = text(meeting.get("meetingKey")) or f"{race_date}|{normalise(track)}"
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict):
                continue
            race_no = number_text(race.get("raceNumber") or race.get("race_no"))
            race_key = text(race.get("raceKey")) or f"{meeting_key}|R{race_no}"
            for index, runner in enumerate(race.get("runners", []) or []):
                if not isinstance(runner, dict):
                    continue
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                horse = text(official.get("runner") or source.get("horseName") or source.get("runnerName") or source.get("horse"))
                runner_number = number_text(
                    official.get("no")
                    or official.get("number")
                    or source.get("runnerNumber")
                    or source.get("runner_number")
                    or source.get("saddlecloth")
                )
                canonical_runner_key = f"{race_key}|{runner_number or normalise(horse) or index + 1}"
                rows.append(
                    CatalogRunner(
                        race_date=race_date,
                        track=track,
                        race_no=race_no,
                        horse=horse,
                        runner_number=runner_number,
                        canonical_meeting_key=meeting_key,
                        canonical_race_key=race_key,
                        canonical_runner_key=canonical_runner_key,
                        scratched=bool_text(official.get("scratched") or source.get("scratched") or source.get("is_scratched")),
                    )
                )
    return rows


def catalog_index(rows: list[CatalogRunner]) -> tuple[dict[tuple[str, str, str, str], CatalogRunner], dict[tuple[str, str, str, str], CatalogRunner]]:
    by_number: dict[tuple[str, str, str, str], CatalogRunner] = {}
    by_horse: dict[tuple[str, str, str, str], CatalogRunner] = {}
    for row in rows:
        base = (row.race_date, normalise(row.track), row.race_no)
        if row.runner_number:
            by_number[(*base, row.runner_number)] = row
        if row.horse:
            by_horse[(*base, normalise(row.horse))] = row
    return by_number, by_horse


def extract_payload_records(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    generated = ""
    if isinstance(payload.get("header"), dict):
        generated = text(payload["header"].get("generated_time"))
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    race = data.get("race") if isinstance(data.get("race"), dict) else data
    runners = data.get("runners") if isinstance(data.get("runners"), list) else []
    provider_race_id = text(race.get("event_id") or race.get("id"))
    provider_meeting_id = text(race.get("meeting_id"))
    meeting_name = text(race.get("meeting_name") or race.get("meeting") or race.get("name"))
    race_no = number_text(race.get("race_number"))
    advertised_start = text(race.get("advertised_start_string") or race.get("advertised_start"))
    actual_start = text(race.get("actual_start_string") or race.get("actual_start"))
    race_status = text(race.get("status"))
    records: list[dict[str, Any]] = []
    for runner in runners:
        if not isinstance(runner, dict):
            continue
        odds = runner.get("odds") if isinstance(runner.get("odds"), dict) else {}
        flucs = runner.get("flucs") if isinstance(runner.get("flucs"), list) else []
        timestamped = runner.get("flucs_with_timestamp") if isinstance(runner.get("flucs_with_timestamp"), list) else []
        numeric_flucs = [float(x) for x in flucs if isinstance(x, (int, float))]
        record = {
            "provider_meeting_id": provider_meeting_id,
            "provider_race_id": provider_race_id,
            "provider_runner_id": text(runner.get("entrant_id") or runner.get("competitor_id")),
            "provider_horse": text(runner.get("name")),
            "provider_runner_number": number_text(runner.get("runner_number")),
            "track": meeting_name,
            "race_no": race_no,
            "fixed_win": money_text(odds.get("fixed_win")),
            "fixed_place": money_text(odds.get("fixed_place")),
            "opening_price": f"{numeric_flucs[0]:.2f}" if numeric_flucs else "",
            "high_price": f"{max(numeric_flucs):.2f}" if numeric_flucs else "",
            "low_price": f"{min(numeric_flucs):.2f}" if numeric_flucs else "",
            "recent_price": f"{numeric_flucs[-1]:.2f}" if numeric_flucs else money_text(odds.get("fixed_win")),
            "price_timestamp": generated,
            "flucs_with_timestamp": json.dumps(timestamped, ensure_ascii=False) if timestamped else "",
            "flucs_untimestamped": json.dumps(numeric_flucs, ensure_ascii=False) if numeric_flucs else "",
            "fluctuation_status": "TIMESTAMPED_FLUCTUATIONS_AVAILABLE" if timestamped else ("PROVIDER_FLUCS_UNTIMESTAMPED" if numeric_flucs else "FLUCTUATION_UNAVAILABLE"),
            "is_scratched": bool_text(runner.get("is_scratched")),
            "scratch_time": text(runner.get("scr_time") or runner.get("scratch_time")),
            "market_status": "SCRATCHED" if bool_text(runner.get("is_scratched")) == "true" else ("LIVE_MARKET" if money_text(odds.get("fixed_win")) else "MARKET_UNAVAILABLE"),
            "race_status": race_status,
            "advertised_start": advertised_start,
            "actual_start": actual_start,
            "jockey": text(runner.get("jockey")),
            "trainer_name": text(runner.get("trainer_name")),
            "barrier": number_text(runner.get("barrier")),
        }
        records.append(record)
    return generated, records


def request_json(url: str, headers: dict[str, str], params: dict[str, Any], timeout: int = 30, retries: int = 2) -> tuple[int, dict[str, Any], str]:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if text(v)})
    full_url = f"{url}?{query}" if query else url
    last_error = ""
    for attempt in range(retries + 1):
        req = urllib.request.Request(full_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return response.status, json.loads(body), full_url
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP_{exc.code}"
            if exc.code in {429, 500, 503} and attempt < retries:
                time.sleep(2**attempt)
                continue
            return exc.code, {"error": last_error, "body": exc.read().decode("utf-8", errors="replace")[:2000]}, full_url
        except Exception as exc:
            last_error = type(exc).__name__
            if attempt < retries:
                time.sleep(2**attempt)
                continue
            return 0, {"error": last_error, "message": text(exc)}, full_url
    return 0, {"error": last_error}, full_url


def fetch_ladbrokes(mode: str, dates: list[str], email: str, partner: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    headers = {"From": email, "X-Partner": partner, "User-Agent": "EDGEiQ-Ladbrokes-Affiliate-Adapter/1.0"}
    all_records: list[dict[str, Any]] = []
    request_audit: list[dict[str, Any]] = []
    raw_refs: list[dict[str, Any]] = []
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for race_date in dates:
        offset = 0
        while True:
            params = {
                "enc": "json",
                "date_from": race_date,
                "date_to": race_date,
                "category": "T",
                "country": "AUS",
                "limit": 200,
                "offset": offset,
            }
            status, payload, url = request_json(f"{BASE_URL}/meetings", headers, params)
            request_audit.append({"request_type": "meetings", "race_date": race_date, "url": url, "status_code": status, "error": text(payload.get("error"))})
            raw_path = RAW_DIR / race_date / f"meetings_offset_{offset}.json"
            write_json(raw_path, payload)
            raw_refs.append({"path": str(raw_path), "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest()})
            if status != 200:
                break
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            meetings = data.get("meetings") if isinstance(data.get("meetings"), list) else []
            vic_meetings = [m for m in meetings if isinstance(m, dict) and text(m.get("state")).upper() == "VIC" and text(m.get("category")).upper() == "T"]
            for meeting in vic_meetings:
                for race in meeting.get("races", []) or []:
                    if not isinstance(race, dict):
                        continue
                    race_id = text(race.get("id") or race.get("event_id"))
                    if not race_id:
                        continue
                    status_e, event_payload, event_url = request_json(f"{BASE_URL}/events/{race_id}", headers, {"enc": "json"})
                    request_audit.append({"request_type": "event", "race_date": race_date, "url": event_url, "status_code": status_e, "error": text(event_payload.get("error"))})
                    event_raw_path = RAW_DIR / race_date / f"event_{race_id}.json"
                    write_json(event_raw_path, event_payload)
                    raw_refs.append({"path": str(event_raw_path), "sha256": hashlib.sha256(event_raw_path.read_bytes()).hexdigest()})
                    if status_e != 200:
                        continue
                    generated, records = extract_payload_records(event_payload)
                    for record in records:
                        record["race_date"] = race_date
                        record["price_timestamp"] = record.get("price_timestamp") or generated
                        record["edgeiq_observed_at"] = now_utc()
                    all_records.extend(records)
                    if mode == "ACTIVE_MARKET_REFRESH":
                        time.sleep(0.8)
            if len(meetings) < 200:
                break
            offset += 200
    return all_records, request_audit, raw_refs


def match_records(records: list[dict[str, Any]], catalog: list[CatalogRunner], generated_at: str, mode: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_number, by_horse = catalog_index(catalog)
    runtime_rows: list[dict[str, Any]] = []
    proof_rows: list[dict[str, Any]] = []
    for record in records:
        base = (text(record.get("race_date")), normalise(record.get("track")), number_text(record.get("race_no")))
        runner_number = number_text(record.get("provider_runner_number"))
        horse_key = normalise(record.get("provider_horse"))
        matched = by_number.get((*base, runner_number)) if runner_number else None
        match_method = "RUNNER_NUMBER"
        if not matched and horse_key:
            matched = by_horse.get((*base, horse_key))
            match_method = "HORSE_NAME"
        join_status = "MATCHED" if matched else "UNMATCHED"
        canonical = matched or CatalogRunner(
            race_date=text(record.get("race_date")),
            track=text(record.get("track")),
            race_no=number_text(record.get("race_no")),
            horse=text(record.get("provider_horse")),
            runner_number=runner_number,
            canonical_meeting_key="",
            canonical_race_key="",
            canonical_runner_key="",
            scratched="false",
        )
        source_confidence = "HIGH" if join_status == "MATCHED" and text(record.get("fixed_win")) else ("MEDIUM" if join_status == "MATCHED" else "LOW")
        market_availability = "SCRATCHED" if text(record.get("is_scratched")) == "true" else ("LIVE_MARKET" if text(record.get("fixed_win")) else "MARKET_UNAVAILABLE")
        row = {
            "generated_at": generated_at,
            "mode": mode,
            "race_date": canonical.race_date,
            "canonical_meeting_key": canonical.canonical_meeting_key,
            "canonical_race_key": canonical.canonical_race_key,
            "canonical_runner_key": canonical.canonical_runner_key,
            "track": canonical.track,
            "race_no": canonical.race_no,
            "horse": canonical.horse,
            "runner_number": canonical.runner_number,
            "provider_meeting_id": text(record.get("provider_meeting_id")),
            "provider_race_id": text(record.get("provider_race_id")),
            "provider_runner_id": text(record.get("provider_runner_id")),
            "provider_horse": text(record.get("provider_horse")),
            "provider_runner_number": runner_number,
            "fixed_win": text(record.get("fixed_win")),
            "fixed_place": text(record.get("fixed_place")),
            "opening_price": text(record.get("opening_price")),
            "high_price": text(record.get("high_price")),
            "low_price": text(record.get("low_price")),
            "recent_price": text(record.get("recent_price")),
            "price_timestamp": text(record.get("price_timestamp")),
            "edgeiq_observed_at": text(record.get("edgeiq_observed_at")) or generated_at,
            "flucs_with_timestamp": text(record.get("flucs_with_timestamp")),
            "flucs_untimestamped": text(record.get("flucs_untimestamped")),
            "fluctuation_status": text(record.get("fluctuation_status")),
            "price_movement": "",
            "price_movement_status": "INSUFFICIENT_EDGEIQ_OBSERVATIONS",
            "is_scratched": text(record.get("is_scratched")),
            "scratch_time": text(record.get("scratch_time")),
            "market_status": text(record.get("market_status")),
            "race_status": text(record.get("race_status")),
            "advertised_start": text(record.get("advertised_start")),
            "actual_start": text(record.get("actual_start")),
            "market_availability_status": market_availability,
            "market_freshness_status": "CURRENT_PROVIDER_OBSERVATION",
            "source_priority_rank": "1",
            "source_confidence": source_confidence,
            "join_status": join_status,
            "runner_match_method": match_method if join_status == "MATCHED" else "NO_MATCH",
            "raw_publication_status": "NOT_RAW_REPUBLISHED",
        }
        runtime_rows.append(row)
        proof_rows.append(
            {
                "race_date": row["race_date"],
                "track": row["track"],
                "race_no": row["race_no"],
                "horse": row["horse"],
                "provider_horse": row["provider_horse"],
                "runner_number": row["runner_number"],
                "provider_runner_number": row["provider_runner_number"],
                "canonical_race_key": row["canonical_race_key"],
                "provider_race_id": row["provider_race_id"],
                "join_status": row["join_status"],
                "runner_match_method": row["runner_match_method"],
                "fixed_win_retrieved": "YES" if row["fixed_win"] else "NO",
                "scratching_status_compared": "YES" if matched else "NO",
                "catalog_scratched": canonical.scratched,
                "provider_scratched": row["is_scratched"],
                "source_timestamp_retained": "YES" if row["price_timestamp"] or row["edgeiq_observed_at"] else "NO",
            }
        )
    return runtime_rows, proof_rows


def apply_price_movement(runtime_rows: list[dict[str, Any]]) -> None:
    history = read_csv(HISTORY)
    latest_by_runner: dict[str, dict[str, str]] = {}
    for row in history:
        runner_id = text(row.get("provider_runner_id"))
        if runner_id:
            latest_by_runner[runner_id] = row
    for row in runtime_rows:
        runner_id = text(row.get("provider_runner_id"))
        previous = latest_by_runner.get(runner_id)
        if not previous:
            continue
        current = money_text(row.get("fixed_win"))
        prior = money_text(previous.get("fixed_win"))
        if not current or not prior:
            continue
        movement = float(current) - float(prior)
        row["price_movement"] = f"{movement:+.2f}"
        row["price_movement_status"] = "DERIVED_FROM_EDGEIQ_OBSERVATION_HISTORY"


def history_rows(runtime_rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in runtime_rows:
        if not row.get("fixed_win") and not row.get("is_scratched"):
            continue
        payload = "|".join(text(row.get(field)) for field in ["provider_runner_id", "fixed_win", "fixed_place", "is_scratched", "race_status"])
        observed = text(row.get("edgeiq_observed_at")) or now_utc()
        rows.append(
            {
                "observation_id": hashlib.sha256(f"{observed}|{payload}".encode("utf-8")).hexdigest()[:24],
                "observed_at": observed,
                "mode": mode,
                "race_date": text(row.get("race_date")),
                "track": text(row.get("track")),
                "race_no": text(row.get("race_no")),
                "horse": text(row.get("horse")),
                "runner_number": text(row.get("runner_number")),
                "provider_meeting_id": text(row.get("provider_meeting_id")),
                "provider_race_id": text(row.get("provider_race_id")),
                "provider_runner_id": text(row.get("provider_runner_id")),
                "fixed_win": text(row.get("fixed_win")),
                "fixed_place": text(row.get("fixed_place")),
                "race_status": text(row.get("race_status")),
                "is_scratched": text(row.get("is_scratched")),
                "payload_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            }
        )
    return rows


def reference_assessment() -> dict[str, Any]:
    return {
        "reference_repository": REFERENCE_REPO_URL,
        "files_inspected": [
            "ladbrokes_racing_scraper.py",
            "run_scraper.py",
            "README.md",
            "requirements.txt",
            ".github/workflows/All_form_updater.yml",
        ],
        "reference_endpoint_usage": {
            "base_url": "https://api-affiliates.ladbrokes.com.au/affiliates/v1/racing",
            "meetings_endpoint": "/meetings",
            "event_endpoint": "/events/{race_id}",
            "additional_reference_endpoints": ["/events/{race_id}/form", "/runners/{runner_id}"],
        },
        "reference_auth_contract": {
            "headers": ["From", "X-Partner"],
            "reference_runtime_env": ["SCRAPER_EMAIL", "SCRAPER_PARTNER"],
            "edgeiq_runtime_env": REQUIRED_ENV,
            "api_key_required_by_verified_docs": False,
        },
        "official_docs_confirmation": {
            "docs_url": OFFICIAL_DOCS_URL,
            "base_url_in_intro": "https://api.ladbrokes.com.au/affiliates/v1",
            "racing_examples_base_url": "https://api-affiliates.ladbrokes.com.au/affiliates/v1/racing",
            "supported_racing_endpoints": ["/racing/meetings", "/racing/meetings/{MEETING_ID}", "/racing/events/{EVENT_ID}"],
            "sports_api_available_via_affiliates": False,
            "meetings_params": ["enc", "id", "date_from", "date_to", "category", "country", "limit", "offset"],
            "event_params": ["enc", "id"],
        },
        "edgeiq_decision": "BUILD_GOVERNED_ADAPTER_DO_NOT_COPY_REFERENCE_SUBSYSTEM",
        "folder_per_race_json_adopted_as_canonical": False,
    }


def terms_assessment(auth_present: bool) -> dict[str, Any]:
    return {
        "API_ACCESS_AUTHORISED": "ENV_CONFIGURED_PENDING_PROVIDER_ACCEPTANCE" if auth_present else "NO_ENV_CREDENTIALS_CONFIGURED",
        "LOCAL_PERSONAL_USE_ALLOWED": "CONDITIONAL_ON_AUTHORISED_AFFILIATE_ACCESS",
        "PUBLIC_REPUBLICATION_ALLOWED": "NO_WITHOUT_WRITTEN_PERMISSION",
        "COMMERCIAL_USE_ALLOWED": "NO_UNLESS_WRITTEN_PERMISSION_OR_CONTRACT",
        "WRITTEN_PERMISSION_REQUIRED": "YES_FOR_RAW_DATA_REPUBLICATION_OR_COMMERCIAL_REUSE",
        "TERMS_UNCLEAR": "PARTIAL_PUBLIC_DOCS_DO_NOT_REPLACE_LADBROKES_CONTRACT",
        "credential_values_written_to_outputs": "NO",
        "raw_payload_publication": "NO_RAW_PAYLOADS_WRITTEN_TO_PUBLIC_DATA",
    }


def write_reference_docs() -> None:
    payload = reference_assessment()
    write_json(REFERENCE_JSON, payload)
    lines = [
        "# EDGEiQ Ladbrokes Reference Inspection V1",
        "",
        f"Reference repository: {REFERENCE_REPO_URL}",
        f"Official API docs: {OFFICIAL_DOCS_URL}",
        "",
        "## Confirmed Contract",
        "",
        "- Racing API examples use `https://api-affiliates.ladbrokes.com.au/affiliates/v1/racing`.",
        "- Identification uses `From` and `X-Partner` headers.",
        "- Documented racing endpoints are meetings, meeting-by-id, and event-by-id.",
        "- Sports API is not available via the affiliates API.",
        "- Race runners expose `odds.fixed_win`, `odds.fixed_place`, `is_scratched`, `scratch_time`, weights, barrier, jockey, trainer, runner number, and ordered `flucs`.",
        "- Official docs describe `flucs` as ordered prices, not timestamped prices.",
        "",
        "## EDGEiQ Decision",
        "",
        "The public repository is treated as endpoint evidence only. EDGEiQ keeps its canonical IDs, market observation history, freshness contract, last-known-good protection, and public runtime feed.",
    ]
    REFERENCE_MD.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_terms_docs(auth_present: bool) -> dict[str, Any]:
    payload = terms_assessment(auth_present)
    write_json(TERMS_JSON, payload)
    lines = [
        "# EDGEiQ Ladbrokes API Terms Assessment V1",
        "",
        "| Classification | Status |",
        "| --- | --- |",
    ]
    for key, value in payload.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "Raw Ladbrokes payloads are retained only in local private `data/market/ladbrokes/raw` when authorised credentials are supplied. The public runtime feed is flattened and source-labelled.",
        ]
    )
    TERMS_MD.parent.mkdir(parents=True, exist_ok=True)
    TERMS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_schema() -> None:
    rows = [
        {"field": "fixed_win", "provider_path": "runner.odds.fixed_win", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "fixed_place", "provider_path": "runner.odds.fixed_place", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "price_timestamp", "provider_path": "response.header.generated_time / edgeiq_observed_at", "edgeiq_status": "RETAINED"},
        {"field": "opening_price", "provider_path": "runner.flucs[0]", "edgeiq_status": "UNTIMESTAMPED_PROVIDER_FLUC"},
        {"field": "high_price", "provider_path": "max(runner.flucs)", "edgeiq_status": "UNTIMESTAMPED_PROVIDER_FLUC"},
        {"field": "low_price", "provider_path": "min(runner.flucs)", "edgeiq_status": "UNTIMESTAMPED_PROVIDER_FLUC"},
        {"field": "recent_price", "provider_path": "runner.flucs[-1] or runner.odds.fixed_win", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "flucs_with_timestamp", "provider_path": "runner.flucs_with_timestamp", "edgeiq_status": "ONLY_IF_EXPLICITLY_SUPPLIED"},
        {"field": "is_scratched", "provider_path": "runner.is_scratched", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "market_status", "provider_path": "derived from odds/scratching", "edgeiq_status": "GOVERNED_DERIVATION"},
        {"field": "race_status", "provider_path": "race.status", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "advertised_start", "provider_path": "race.advertised_start_string / advertised_start", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "actual_start", "provider_path": "race.actual_start_string / actual_start", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "provider_runner_id", "provider_path": "runner.entrant_id", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "provider_race_id", "provider_path": "race.event_id", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
        {"field": "provider_meeting_id", "provider_path": "race.meeting_id", "edgeiq_status": "CAPTURE_IF_SUPPLIED"},
    ]
    write_csv(SCHEMA_CSV, rows, ["field", "provider_path", "edgeiq_status"])


def fallback_runtime(catalog: list[CatalogRunner], generated_at: str, mode: str, status: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for runner in catalog:
        row = {field: "" for field in RUNTIME_FIELDS}
        row.update(
            {
                "generated_at": generated_at,
                "mode": mode,
                "race_date": runner.race_date,
                "canonical_meeting_key": runner.canonical_meeting_key,
                "canonical_race_key": runner.canonical_race_key,
                "canonical_runner_key": runner.canonical_runner_key,
                "track": runner.track,
                "race_no": runner.race_no,
                "horse": runner.horse,
                "runner_number": runner.runner_number,
                "market_availability_status": status,
                "market_freshness_status": status,
                "source_priority_rank": "4",
                "source_confidence": "NONE",
                "join_status": "CATALOG_ONLY",
                "runner_match_method": "NOT_APPLICABLE",
                "raw_publication_status": "NO_PROVIDER_DATA_FETCHED",
                "fluctuation_status": "FLUCTUATION_UNAVAILABLE",
                "price_movement_status": "NO_PROVIDER_OBSERVATION",
            }
        )
        rows.append(row)
    return rows


def summary_rows(runtime_rows: list[dict[str, Any]], proof_rows: list[dict[str, Any]], request_audit: list[dict[str, Any]], auth_present: bool, mode: str, status: str) -> list[dict[str, Any]]:
    matched = sum(1 for row in runtime_rows if row.get("join_status") == "MATCHED")
    live_prices = sum(1 for row in runtime_rows if text(row.get("fixed_win")))
    timestamped_flucs = sum(1 for row in runtime_rows if text(row.get("flucs_with_timestamp")))
    movement = sum(1 for row in runtime_rows if row.get("price_movement_status") == "DERIVED_FROM_EDGEIQ_OBSERVATION_HISTORY")
    return [
        {"metric": "adapter_status", "value": status},
        {"metric": "mode", "value": mode},
        {"metric": "auth_headers_configured", "value": "YES" if auth_present else "NO"},
        {"metric": "runtime_rows", "value": len(runtime_rows)},
        {"metric": "matched_rows", "value": matched},
        {"metric": "live_fixed_win_rows", "value": live_prices},
        {"metric": "timestamped_fluc_rows", "value": timestamped_flucs},
        {"metric": "movement_rows_from_edgeiq_history", "value": movement},
        {"metric": "request_count", "value": len(request_audit)},
        {"metric": "proof_rows", "value": len(proof_rows)},
        {"metric": "production_pricing_changed", "value": "NO"},
        {"metric": "market_workspace_wired", "value": "NO"},
    ]


def write_audit_docs(runtime_rows: list[dict[str, Any]], proof_rows: list[dict[str, Any]], request_audit: list[dict[str, Any]], raw_refs: list[dict[str, Any]], terms: dict[str, Any], status: str, mode: str) -> None:
    audit = {
        "adapter_status": status,
        "mode": mode,
        "runtime_rows": len(runtime_rows),
        "matched_rows": sum(1 for row in runtime_rows if row.get("join_status") == "MATCHED"),
        "live_fixed_win_rows": sum(1 for row in runtime_rows if text(row.get("fixed_win"))),
        "request_audit": request_audit,
        "raw_local_files": raw_refs,
        "terms": terms,
        "market_workspace_wired": False,
        "production_pricing_changed": False,
    }
    write_json(ADAPTER_AUDIT_JSON, audit)
    write_json(PROOF_JSON, {"status": status, "rows": proof_rows[:500], "row_count": len(proof_rows)})
    ADAPTER_AUDIT_MD.parent.mkdir(parents=True, exist_ok=True)
    ADAPTER_AUDIT_MD.write_text(
        "\n".join(
            [
                "# EDGEiQ Ladbrokes Adapter V1 Audit",
                "",
                f"Adapter status: {status}",
                f"Mode: {mode}",
                f"Runtime rows: {len(runtime_rows)}",
                f"Matched rows: {audit['matched_rows']}",
                f"Live fixed-win rows: {audit['live_fixed_win_rows']}",
                "",
                "MARKET workspace wiring: NO. Required current-meeting proof has not been satisfied unless live credentials produce matched prices and repeated observations.",
                "",
                "Production pricing changed: NO.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    PROOF_MD.write_text(
        "\n".join(
            [
                "# EDGEiQ Ladbrokes Current Match Proof V1",
                "",
                f"Status: {status}",
                f"Rows: {len(proof_rows)}",
                "",
                "Proof gates require matched meetings, races, runners, current fixed-win prices, retained timestamps, multiple retained observations, movement derived only from real observations, race switching validation, and no exposed credentials.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build governed EDGEiQ Ladbrokes Affiliate market adapter feed.")
    parser.add_argument("--mode", choices=["DAILY_DISCOVERY", "ACTIVE_MARKET_REFRESH"], default="DAILY_DISCOVERY")
    parser.add_argument("--date", default="", help="Optional race date YYYY-MM-DD. Defaults to EDGEiQ three-day window.")
    args = parser.parse_args()

    generated_at = now_utc()
    email = os.environ.get("EDGEIQ_LADBROKES_FROM", "").strip() or os.environ.get("EDGEIQ_LADBROKES_EMAIL", "").strip()
    partner = os.environ.get("EDGEIQ_LADBROKES_X_PARTNER", "").strip() or os.environ.get("EDGEIQ_LADBROKES_PARTNER_NAME", "").strip()
    auth_present = bool(email and partner)
    status = "AUTH_REQUIRED"
    dates = [args.date] if args.date else current_window_dates()

    write_reference_docs()
    terms = write_terms_docs(auth_present)
    write_schema()

    catalog = catalog_runners()
    request_audit: list[dict[str, Any]] = []
    raw_refs: list[dict[str, Any]] = []
    proof_rows: list[dict[str, Any]] = []

    if auth_present:
        records, request_audit, raw_refs = fetch_ladbrokes(args.mode, dates, email, partner)
        runtime_rows, proof_rows = match_records(records, catalog, generated_at, args.mode)
        apply_price_movement(runtime_rows)
        append_csv(HISTORY, history_rows(runtime_rows, args.mode), HISTORY_FIELDS)
        status = "LADBROKES_OBSERVATION_BUILT" if runtime_rows else "NO_PROVIDER_ROWS_RETURNED"
    else:
        runtime_rows = fallback_runtime(catalog, generated_at, args.mode, "AUTH_REQUIRED")
        append_csv(HISTORY, [], HISTORY_FIELDS)

    write_csv(RUNTIME_CSV, runtime_rows, RUNTIME_FIELDS)
    write_json(
        RUNTIME_JSON,
        {
            "schemaVersion": "edgeiq_ladbrokes_affiliate_market_runtime_v1",
            "generatedAt": generated_at,
            "mode": args.mode,
            "adapterStatus": status,
            "marketWorkspaceWired": False,
            "productionPricingChanged": False,
            "records": runtime_rows,
        },
    )
    write_csv(PROOF_CSV, proof_rows, list(proof_rows[0].keys()) if proof_rows else ["status"])
    write_csv(SUMMARY_CSV, summary_rows(runtime_rows, proof_rows, request_audit, auth_present, args.mode, status), ["metric", "value"])
    audit_rows = request_audit or [{"request_type": "auth_gate", "race_date": ",".join(dates), "url": "", "status_code": "", "error": "AUTH_REQUIRED"}]
    write_csv(AUDIT_CSV, audit_rows, ["request_type", "race_date", "url", "status_code", "error"])
    write_audit_docs(runtime_rows, proof_rows, request_audit, raw_refs, terms, status, args.mode)

    print(json.dumps({"adapter_status": status, "runtime_rows": len(runtime_rows), "auth_headers_configured": auth_present}, indent=2))


if __name__ == "__main__":
    main()
