from __future__ import annotations

import json
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUTS = ROOT / "outputs"
SPORTSBET_DIR = OUTPUTS / "sportsbet_live_real"
AUDIT_DIR = OUTPUTS / "audits"

FAIR_PRICES = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
EXISTING_MARKET = DATA / "sportsbet_live_market_v1.csv"
RAW_EVENTS_SAMPLE = DATA / "sportsbet_live_market_raw_events_sample_v1.json"

FULL_DAY_EVENTS_OUT = SPORTSBET_DIR / "sportsbet_full_day_events_v5_2.json"
FULL_DAY_RACECARDS_OUT = SPORTSBET_DIR / "sportsbet_full_day_racecards_v5_2.json"
MARKET_OUT = DATA / "sportsbet_live_market_full_day_v5_2.csv"
AUDIT_TXT = AUDIT_DIR / "sportsbet_full_day_capture_v5_2_audit.txt"

NEXT_EVENTS_URL = (
    "https://www.sportsbet.com.au/apigw/sportsbook-racing/Sportsbook/Racing/NextEvents"
    "?racingFilters=HR_DOMESTIC,GH_DOMESTIC,HA_DOMESTIC&groupByFilters=true"
)
RACECARD_URL_TEMPLATE = (
    "https://www.sportsbet.com.au/apigw/sportsbook-racing/Sportsbook/Racing/Events/{event_id}/Racecard"
)

LOCAL_TZ = timezone(timedelta(hours=10), name="Australia/Sydney")
REQUEST_TIMEOUT_SECONDS = 20
INFERRED_EVENT_ID_RADIUS = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.sportsbet.com.au/racing",
    "Origin": "https://www.sportsbet.com.au",
}

MARKET_FIELDS = [
    "capture_timestamp_utc",
    "source",
    "source_status",
    "market_source",
    "market_captured_at",
    "event_id",
    "race_id",
    "track",
    "race_no",
    "race_time",
    "race_date",
    "date",
    "horse",
    "horse_key",
    "price_win",
    "sportsbet_price",
    "market_type",
    "market_name",
    "market_id",
    "selection_id",
    "meeting_name",
    "event_name",
    "state",
    "source_url",
    "bookmaker",
    "timestamp",
    "notes",
    "market_mover",
    "recent_odds_fluctuations",
    "is_scratched",
    "runner_status",
    "selection_status",
    "status_code",
    "match_confidence",
]


@dataclass
class FetchResult:
    ok: bool
    status: str
    url: str
    payload: Any | None
    raw_text: str
    notes: str
    http_status: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def clean_race_no(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def canon(value: object) -> str:
    text = norm(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=fields)
    for field in fields:
        if field not in frame.columns:
            frame[field] = ""
    frame.to_csv(path, index=False, columns=fields)


def request_json(url: str) -> FetchResult:
    request = Request(url, headers=HEADERS, method="GET")
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw_bytes = response.read()
            raw_text = raw_bytes.decode("utf-8", errors="replace")
            http_status = str(getattr(response, "status", ""))
    except HTTPError as exc:
        detail = f"HTTP {exc.code}"
        status = "BLOCKED" if exc.code in {401, 403, 429} else "FETCH_FAILED"
        try:
            raw_text = exc.read().decode("utf-8", errors="replace")[:4000]
        except Exception:
            raw_text = ""
        return FetchResult(False, status, url, None, raw_text, detail, str(exc.code))
    except URLError as exc:
        return FetchResult(False, "FETCH_FAILED", url, None, "", f"URL error: {exc.reason}")
    except socket.timeout:
        return FetchResult(False, "FETCH_FAILED", url, None, "", "socket timeout")
    except Exception as exc:
        return FetchResult(False, "FETCH_FAILED", url, None, "", f"unexpected fetch error: {exc}")

    lowered = raw_text.lower()
    if any(token in lowered for token in ["access denied", "forbidden", "captcha", "cloudflare", "bot challenge"]):
        return FetchResult(False, "BLOCKED", url, None, raw_text[:4000], "response indicates access blocked", http_status)

    try:
        payload = json.loads(raw_text)
    except JSONDecodeError:
        status = "BLOCKED" if lowered.startswith("<!doctype") or lowered.startswith("<html") else "SCHEMA_CHANGED"
        return FetchResult(False, status, url, None, raw_text[:4000], "response was not valid JSON", http_status)

    return FetchResult(True, "FRESH", url, payload, raw_text[:4000], "ok", http_status)


def iter_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from iter_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_dicts(value)


def first_non_empty(data: dict[str, Any] | None, names: list[str]) -> str:
    if not isinstance(data, dict):
        return ""
    lowered = {str(key).lower(): value for key, value in data.items()}
    for name in names:
        value = lowered.get(name.lower())
        text = clean(value)
        if text:
            return text
    return ""


def parse_race_time_value(value: object) -> datetime | None:
    if isinstance(value, (int, float)):
        if value > 1000000000:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone(LOCAL_TZ)
        return None

    text = clean(value)
    if not text:
        return None
    if text.isdigit() and len(text) >= 10:
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc).astimezone(LOCAL_TZ)
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
    except ValueError:
        return None


def extract_race_no(*values: object) -> str:
    for value in values:
        text = clean(value)
        if not text:
            continue
        direct = re.fullmatch(r"\d+", text)
        if direct:
            return str(int(text))
        match = re.search(r"\bR(?:ACE)?\s*(\d{1,2})\b", text.upper())
        if match:
            return str(int(match.group(1)))
    return ""


def simplify_track_label(*values: object) -> str:
    raw = " ".join(clean(value) for value in values if clean(value))
    if not raw:
        return ""
    words = [word for word in raw.replace("/", " ").replace("-", " ").split() if word]
    blacklist = {"SPORTSBET", "BET365", "TAB", "NEDS", "RACES", "RACING", "CLUB", "THE"}
    filtered = [word for word in words if word.upper() not in blacklist]
    if filtered:
        raw = " ".join(filtered)
    return norm(raw)


def track_matches(candidate_track: str, target_track: str) -> bool:
    cand = norm(candidate_track).replace(" LAKESIDE", "")
    target = norm(target_track).replace(" LAKESIDE", "")
    return bool(cand and target and (cand in target or target in cand))


def target_races_from_fair(fair: pd.DataFrame) -> list[dict[str, object]]:
    races: list[dict[str, object]] = []
    grouped = fair.groupby(["race_date", "track", "race_no"], dropna=False)
    for (race_date, track, race_no), group in grouped:
        races.append(
            {
                "race_date": str(race_date),
                "track": str(track),
                "track_norm": norm(track),
                "race_no": clean_race_no(race_no),
                "race_time": str(group["race_time"].iloc[0]),
                "expected_runner_count": len(group),
                "expected_horse_keys": sorted(set(group["horse_key_match"])),
            }
        )
    races.sort(key=lambda row: int(row["race_no"]) if str(row["race_no"]).isdigit() else 999)
    return races


def event_candidate_from_node(node: dict[str, Any]) -> dict[str, str] | None:
    event_id = first_non_empty(node, ["eventid", "event_id", "id"])
    race_no_value = extract_race_no(
        first_non_empty(node, ["raceno", "race_no", "racenumber", "race_number", "raceNumber"]),
        first_non_empty(node, ["eventname", "event_name", "name", "displayname", "display_name"]),
    )
    meeting_name = first_non_empty(
        node,
        ["meetingname", "meeting_name", "meeting", "trackname", "track_name", "competitionname", "competition_name"],
    )
    event_name = first_non_empty(node, ["eventname", "event_name", "name", "displayname", "display_name"])
    track = simplify_track_label(first_non_empty(node, ["trackname", "track_name", "track", "competitionname", "competition_name"]), meeting_name)
    race_time = parse_race_time_value(first_non_empty(node, ["racetime", "race_time", "starttime", "start_time", "startTime"]))
    class_name = first_non_empty(node, ["classname", "class_name", "class"])
    race_type = first_non_empty(node, ["type", "race_type", "category"])
    country = first_non_empty(node, ["country", "countryname", "country_name"])

    if not event_id or not race_no_value or not track:
        return None

    if country and norm(country) != "AUSTRALIA":
        return None
    if class_name and "HORSES" not in norm(class_name) and norm(race_type) != "HORSE":
        return None

    return {
        "event_id": str(event_id),
        "meeting_name": meeting_name or track,
        "event_name": event_name or meeting_name or track,
        "track": track,
        "race_no": race_no_value,
        "race_time": race_time.isoformat(timespec="minutes") if race_time else "",
        "race_date": race_time.date().isoformat() if race_time else "",
        "class_name": class_name,
        "race_type": race_type,
        "country": country,
        "source": "event_metadata",
    }


def extract_event_candidates(payload: Any) -> list[dict[str, str]]:
    candidates: dict[str, dict[str, str]] = {}
    for node in iter_dicts(payload):
        if not isinstance(node, dict):
            continue
        candidate = event_candidate_from_node(node)
        if not candidate:
            continue
        candidates[candidate["event_id"]] = candidate
    return list(candidates.values())


def load_raw_event_candidates() -> list[dict[str, str]]:
    payload = read_json(RAW_EVENTS_SAMPLE)
    if payload is None:
        return []
    events = extract_event_candidates(payload)
    if isinstance(payload, dict):
        raw_excerpt = payload.get("raw_excerpt")
        if isinstance(raw_excerpt, str) and raw_excerpt.strip().startswith("[") and raw_excerpt.strip().endswith("]"):
            try:
                events.extend(extract_event_candidates(json.loads(raw_excerpt)))
            except JSONDecodeError:
                pass
    dedup: dict[str, dict[str, str]] = {}
    for event in events:
        dedup[event["event_id"]] = event
    return list(dedup.values())


def known_market_events(existing_market: pd.DataFrame) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    if existing_market.empty:
        return events
    for (_, _, _, event_id), group in existing_market.groupby(["race_date", "track", "race_no", "event_id"], dropna=False):
        events.append(
            {
                "event_id": str(event_id),
                "meeting_name": clean(group["meeting_name"].iloc[0]) if "meeting_name" in group.columns else clean(group["track"].iloc[0]),
                "event_name": clean(group["event_name"].iloc[0]) if "event_name" in group.columns else "",
                "track": clean(group["track"].iloc[0]),
                "race_no": clean_race_no(group["race_no"].iloc[0]),
                "race_time": clean(group["race_time"].iloc[0]) if "race_time" in group.columns else "",
                "race_date": clean(group["race_date"].iloc[0]),
                "class_name": "Horses - Aus/NZ",
                "race_type": "horse",
                "country": "Australia",
                "source": "existing_sportsbet_live_market_v1",
            }
        )
    return events


def target_match_for_event(event: dict[str, str], targets: list[dict[str, object]]) -> dict[str, object] | None:
    for target in targets:
        if str(target["race_no"]) != clean_race_no(event.get("race_no")):
            continue
        if not track_matches(event.get("track", ""), str(target["track"])):
            continue
        if event.get("race_date") and event["race_date"] != target["race_date"]:
            continue
        return target
    return None


def infer_event_ids(known_events: list[dict[str, str]], targets: list[dict[str, object]]) -> list[dict[str, str]]:
    inferred: dict[str, dict[str, str]] = {}
    for known in known_events:
        event_id_text = str(known.get("event_id", "")).strip()
        known_race_no_text = clean_race_no(known.get("race_no", ""))
        if not event_id_text.isdigit() or not known_race_no_text.isdigit():
            continue
        base_event_id = int(event_id_text)
        base_race_no = int(known_race_no_text)
        for target in targets:
            target_race_no = int(target["race_no"])
            base_guess = base_event_id + (target_race_no - base_race_no)
            for delta in range(-INFERRED_EVENT_ID_RADIUS, INFERRED_EVENT_ID_RADIUS + 1):
                event_id_value = str(base_guess + delta)
                inferred[event_id_value] = {
                    "event_id": event_id_value,
                    "meeting_name": str(target["track"]),
                    "event_name": f"R{target['race_no']} inferred racecard probe",
                    "track": str(target["track"]),
                    "race_no": str(target["race_no"]),
                    "race_time": str(target["race_time"]),
                    "race_date": str(target["race_date"]),
                    "class_name": "Horses - Aus/NZ",
                    "race_type": "horse",
                    "country": "Australia",
                    "source": f"inferred_from_event_{event_id_text}_r{known_race_no_text}_delta_{delta}",
                }
    return list(inferred.values())


def event_from_racecard(payload: Any, fallback: dict[str, str]) -> dict[str, str]:
    if not isinstance(payload, dict):
        return fallback
    event = event_candidate_from_node(payload) or {}
    if not event:
        event = fallback.copy()
        event["event_name"] = first_non_empty(payload, ["name", "displayName"]) or event.get("event_name", "")
        event["race_no"] = extract_race_no(payload.get("raceNumber"), event.get("event_name")) or event.get("race_no", "")
        event["track"] = simplify_track_label(payload.get("competitionName"), payload.get("track")) or event.get("track", "")
        event["race_date"] = event.get("race_date", fallback.get("race_date", ""))
        event["race_time"] = event.get("race_time", fallback.get("race_time", ""))
        event["event_id"] = str(payload.get("id") or fallback.get("event_id", ""))
    event["source"] = fallback.get("source", event.get("source", "racecard"))
    return event


def to_float(value: object) -> float | None:
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if parsed <= 1.0 or parsed > 1000:
        return None
    return parsed


def format_price(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def extract_price(node: Any) -> float | None:
    if isinstance(node, dict):
        direct_order = [
            "price",
            "displayprice",
            "winprice",
            "currentprice",
            "fixedodds",
            "fixedwin",
            "returnwin",
            "decimalodds",
            "odds",
            "sPrice",
            "lPrice",
            "winPrice",
        ]
        for key in direct_order:
            value = first_non_empty(node, [key])
            parsed = to_float(value)
            if parsed is not None:
                return parsed
        for key, value in node.items():
            lowered = str(key).lower()
            if isinstance(value, dict) and lowered in {"price", "prices", "odds", "fixedodds", "fixed", "win", "winprice", "betoffer", "offer", "powerplaypricing"}:
                parsed = extract_price(value)
                if parsed is not None:
                    return parsed
            if isinstance(value, list) and lowered in {"prices", "offers"}:
                parsed = extract_price(value)
                if parsed is not None:
                    return parsed
            if lowered.endswith("price") or lowered.endswith("odds"):
                parsed = to_float(value)
                if parsed is not None:
                    return parsed
    elif isinstance(node, list):
        for item in node:
            parsed = extract_price(item)
            if parsed is not None:
                return parsed
    return None


def looks_scratched(item: dict[str, Any]) -> bool:
    flags = [
        first_non_empty(item, ["isscratched", "is_scratched", "scratched", "isout", "isOut"]),
        first_non_empty(item, ["status", "selectionstatus", "runnerstatus", "statuscode", "statusCode"]),
    ]
    blob = " ".join(flag.upper() for flag in flags if flag)
    return any(token in blob for token in ["TRUE", "SCR", "SCRATCH", "WITHDRAWN", "REMOVED"])


def market_priority(market_name: str) -> int:
    name = clean(market_name).lower()
    if name in {"win", "winner", "fixed odds win"} or name.startswith("win "):
        return 1
    if "win or place" in name:
        return 2
    if name in {"top 2", "top2", "top two"}:
        return 3
    if name in {"top 3", "top3", "top three"}:
        return 4
    return 99


def market_has_selection_list(node: dict[str, Any]) -> bool:
    return any(isinstance(node.get(key), list) for key in ["selections", "runners", "outcomes", "participants", "competitors"])


def selection_row(item: dict[str, Any], event: dict[str, str], market_id: str, market_name: str, captured_at: str) -> dict[str, object] | None:
    horse = first_non_empty(item, ["horse", "runnername", "runner_name", "selectionname", "selection_name", "competitorname", "horse_name", "name", "displayname"])
    if not horse:
        return None
    is_scratched = looks_scratched(item)
    status_text = first_non_empty(item, ["status", "selectionstatus", "runnerstatus", "statuscode", "statusCode", "bettingstatus", "pricecode"])
    price = extract_price(item)
    if price is None and not is_scratched:
        return None

    event_id_value = clean(event.get("event_id"))
    race_date = clean(event.get("race_date"))
    track = clean(event.get("track"))
    race_no_value = clean(event.get("race_no"))
    race_id = f"{race_date}_{track}_R{race_no_value}" if race_date and track and race_no_value else event_id_value
    selection_id = first_non_empty(item, ["selectionid", "selection_id", "outcomeid", "outcome_id", "runnerid", "runner_id", "competitorid", "id"])
    price_text = format_price(price)

    return {
        "capture_timestamp_utc": captured_at,
        "source": "Sportsbet",
        "source_status": "FRESH",
        "market_source": "Sportsbet Full Day Racecard V5.2",
        "market_captured_at": captured_at,
        "event_id": event_id_value,
        "race_id": race_id,
        "track": track,
        "race_no": race_no_value,
        "race_time": clean(event.get("race_time")),
        "race_date": race_date,
        "date": race_date,
        "horse": clean(horse),
        "horse_key": canon(horse),
        "price_win": price_text,
        "sportsbet_price": price_text,
        "market_type": market_name or "Win",
        "market_name": market_name or "Win",
        "market_id": market_id,
        "selection_id": selection_id,
        "meeting_name": clean(event.get("meeting_name")) or track,
        "event_name": clean(event.get("event_name")),
        "state": "VIC",
        "source_url": RACECARD_URL_TEMPLATE.format(event_id=event_id_value),
        "bookmaker": "Sportsbet",
        "timestamp": captured_at,
        "notes": clean(event.get("source")),
        "market_mover": "",
        "recent_odds_fluctuations": "",
        "is_scratched": "TRUE" if is_scratched else "FALSE",
        "runner_status": "SCRATCHED" if is_scratched else "ACTIVE",
        "selection_status": status_text,
        "status_code": status_text,
        "match_confidence": "HIGH",
    }


def rows_from_market_node(market_node: dict[str, Any], event: dict[str, str], captured_at: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    market_name = first_non_empty(market_node, ["marketname", "market_name", "name", "displayname", "title", "bettype"]) or "Win"
    market_id = first_non_empty(market_node, ["marketid", "market_id", "id"])
    for key in ["selections", "runners", "outcomes", "participants", "competitors"]:
        items = market_node.get(key) or market_node.get(key.title()) or market_node.get(key.upper())
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                row = selection_row(item, event, market_id, market_name, captured_at)
                if row:
                    rows.append(row)
    return rows


def extract_racecard_rows(payload: Any, event: dict[str, str], captured_at: str) -> list[dict[str, object]]:
    market_nodes: list[dict[str, Any]] = []
    for node in iter_dicts(payload):
        if not isinstance(node, dict):
            continue
        market_name = first_non_empty(node, ["marketname", "market_name", "name", "displayname", "title", "bettype"])
        if not market_name or not market_has_selection_list(node):
            continue
        if market_priority(market_name) <= 4:
            market_nodes.append(node)

    market_nodes.sort(
        key=lambda node: (
            market_priority(first_non_empty(node, ["marketname", "market_name", "name", "displayname", "title", "bettype"])),
            clean(first_non_empty(node, ["id", "marketid", "market_id"])),
        )
    )

    rows: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str]] = set()
    for market in market_nodes:
        market_name = first_non_empty(market, ["marketname", "market_name", "name", "displayname", "title", "bettype"]) or "Unknown"
        for row in rows_from_market_node(market, event, captured_at):
            key = (clean(str(row.get("event_id"))), clean(str(row.get("horse_key"))))
            if key in seen_keys:
                continue
            row["market_type"] = market_name
            row["market_name"] = market_name
            seen_keys.add(key)
            rows.append(row)
    return rows


def racecard_closed_or_suspended(payload: Any, fetch: FetchResult) -> str:
    if not fetch.ok:
        if fetch.status in {"BLOCKED", "FETCH_FAILED", "SCHEMA_CHANGED"}:
            return fetch.status
        return "UNKNOWN"
    if not isinstance(payload, dict):
        return "UNKNOWN"
    status_bits = [
        first_non_empty(payload, ["statusCode", "status", "bettingStatus"]),
        str(payload.get("livePriceSettled", "")),
        str(payload.get("nonLivePriceSettled", "")),
        str(payload.get("livePriceResultConfirmed", "")),
    ]
    blob = " ".join(bit.upper() for bit in status_bits if bit)
    if any(token in blob for token in ["CLOSED", "SUSP", "SETTLED", "RESULT", "FINAL", "TRUE"]):
        return "YES"
    return "NO"


def compile_event_candidates(targets: list[dict[str, object]], existing_market: pd.DataFrame, next_payload: Any, endpoint_log: list[dict[str, object]]) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    raw_events = load_raw_event_candidates()
    next_events = extract_event_candidates(next_payload) if next_payload is not None else []
    existing_events = known_market_events(existing_market)

    all_known = [*raw_events, *next_events, *existing_events]
    matched_known: dict[str, dict[str, str]] = {}
    for event in all_known:
        target = target_match_for_event(event, targets)
        if target:
            event["race_date"] = str(target["race_date"])
            event["track"] = str(target["track"])
            event["race_no"] = str(target["race_no"])
            event["race_time"] = event.get("race_time") or str(target["race_time"])
            matched_known[event["event_id"]] = event

    inferred = infer_event_ids(list(matched_known.values()), targets)
    event_candidates: dict[str, dict[str, str]] = {}
    for event in [*matched_known.values(), *inferred]:
        event_candidates[event["event_id"]] = event

    endpoint_log.append(
        {
            "endpoint": "candidate_compilation",
            "status": "PASS",
            "events_seen": len(all_known),
            "events_matched_to_target": len(matched_known),
            "events_inferred": len(inferred),
            "notes": "compiled from NextEvents, raw sample, existing market, and inferred adjacent event ids",
        }
    )
    return list(event_candidates.values()), endpoint_log


def main() -> None:
    print("=" * 90)
    print("EDGEIQ SPORTSBET FULL-DAY RACECARD CAPTURE V5.2")
    print("=" * 90)

    SPORTSBET_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    if not FAIR_PRICES.exists():
        raise FileNotFoundError(f"Missing input: {FAIR_PRICES}")

    captured_at = utc_now()
    fair = pd.read_csv(FAIR_PRICES, dtype=str, keep_default_na=False, low_memory=False)
    fair["race_no"] = fair["race_no"].map(clean_race_no)
    fair["horse_key_match"] = fair.apply(lambda row: canon(row.get("horse_key", "")) or canon(row.get("horse", "")), axis=1)
    targets = target_races_from_fair(fair)
    target_track = targets[0]["track"] if targets else ""

    existing_market = pd.read_csv(EXISTING_MARKET, dtype=str, keep_default_na=False, low_memory=False) if EXISTING_MARKET.exists() else pd.DataFrame()
    if not existing_market.empty:
        existing_market["race_no"] = existing_market["race_no"].map(clean_race_no)

    endpoints_tested: list[dict[str, object]] = []
    next_events = request_json(NEXT_EVENTS_URL)
    endpoints_tested.append(
        {
            "endpoint": NEXT_EVENTS_URL,
            "status": next_events.status,
            "http_status": next_events.http_status,
            "notes": next_events.notes,
            "events_seen": 0,
        }
    )

    event_candidates, endpoints_tested = compile_event_candidates(
        targets,
        existing_market,
        next_events.payload if next_events.ok else None,
        endpoints_tested,
    )

    racecards_requested = 0
    racecards_succeeded = 0
    racecards_failed = 0
    racecard_results: list[dict[str, Any]] = []
    market_rows: list[dict[str, object]] = []
    accepted_event_by_race: dict[str, dict[str, Any]] = {}
    race_missing_reasons: dict[str, str] = {str(target["race_no"]): "CLOSED_OR_NOT_AVAILABLE_FROM_CURRENT_SPORTSBET_ENDPOINT" for target in targets}

    for candidate in sorted(event_candidates, key=lambda row: int(row["event_id"]) if row["event_id"].isdigit() else 0):
        url = RACECARD_URL_TEMPLATE.format(event_id=candidate["event_id"])
        racecards_requested += 1
        fetch = request_json(url)
        closed_or_suspended = racecard_closed_or_suspended(fetch.payload, fetch)
        result: dict[str, Any] = {
            "event_id": candidate["event_id"],
            "candidate_race_no": candidate["race_no"],
            "candidate_track": candidate["track"],
            "candidate_source": candidate.get("source", ""),
            "url": url,
            "fetch_status": fetch.status,
            "http_status": fetch.http_status,
            "fetch_notes": fetch.notes,
            "closed_or_suspended": closed_or_suspended,
            "accepted_target_race": "",
            "rows_extracted": 0,
            "prices_extracted": 0,
            "scratched_extracted": 0,
            "event_summary": {},
        }

        if fetch.ok and fetch.payload is not None:
            event = event_from_racecard(fetch.payload, candidate)
            target = target_match_for_event(event, targets)
            result["event_summary"] = event
            if target:
                event["race_date"] = str(target["race_date"])
                event["track"] = str(target["track"])
                event["race_no"] = str(target["race_no"])
                event["race_time"] = event.get("race_time") or str(target["race_time"])
                rows = extract_racecard_rows(fetch.payload, event, captured_at)
                result["accepted_target_race"] = str(target["race_no"])
                result["rows_extracted"] = len(rows)
                result["prices_extracted"] = len([row for row in rows if clean(row.get("sportsbet_price"))])
                result["scratched_extracted"] = len([row for row in rows if clean(row.get("is_scratched")) == "TRUE"])
                if rows:
                    race_no_value = str(target["race_no"])
                    previous = accepted_event_by_race.get(race_no_value)
                    if previous is None or len(rows) > int(previous["rows_extracted"]):
                        accepted_event_by_race[race_no_value] = {
                            "candidate": candidate,
                            "event": event,
                            "rows": rows,
                            "rows_extracted": len(rows),
                            "result": result,
                        }
                    race_missing_reasons[race_no_value] = "covered"
                else:
                    race_missing_reasons[str(target["race_no"])] = "RACECARD_AVAILABLE_BUT_NO_PRICES_EXTRACTED"
            racecards_succeeded += 1
        else:
            racecards_failed += 1

        endpoints_tested.append(
            {
                "endpoint": url,
                "status": fetch.status,
                "http_status": fetch.http_status,
                "event_id": candidate["event_id"],
                "candidate_race_no": candidate["race_no"],
                "candidate_source": candidate.get("source", ""),
                "notes": fetch.notes,
            }
        )
        racecard_results.append(result)

    for bundle in accepted_event_by_race.values():
        market_rows.extend(bundle["rows"])

    market_rows.sort(key=lambda row: (clean(row.get("race_no")), clean(row.get("horse"))))
    write_csv(MARKET_OUT, market_rows, MARKET_FIELDS)

    full_day_events_payload = {
        "captured_at": captured_at,
        "target_track": target_track,
        "target_races": targets,
        "endpoints_tested": endpoints_tested,
        "event_candidates": event_candidates,
        "accepted_event_ids_by_race": {
            race_no: {
                "event_id": bundle["event"].get("event_id", ""),
                "event_name": bundle["event"].get("event_name", ""),
                "source": bundle["candidate"].get("source", ""),
                "rows_extracted": bundle["rows_extracted"],
            }
            for race_no, bundle in sorted(accepted_event_by_race.items(), key=lambda item: int(item[0]))
        },
    }
    write_json(FULL_DAY_EVENTS_OUT, full_day_events_payload)

    write_json(
        FULL_DAY_RACECARDS_OUT,
        {
            "captured_at": captured_at,
            "racecards_requested": racecards_requested,
            "racecards_succeeded": racecards_succeeded,
            "racecards_failed": racecards_failed,
            "racecards": racecard_results,
        },
    )

    race_lines: list[str] = []
    covered_races = 0
    for target in targets:
        race_no_value = str(target["race_no"])
        rows_for_race = [row for row in market_rows if clean(row.get("race_no")) == race_no_value]
        if rows_for_race:
            covered_races += 1
        event_id_values = sorted({clean(row.get("event_id")) for row in rows_for_race if clean(row.get("event_id"))})
        price_count = len([row for row in rows_for_race if clean(row.get("sportsbet_price"))])
        scratched_count = len([row for row in rows_for_race if clean(row.get("is_scratched")) == "TRUE"])
        closed_detected = "YES" if any(result.get("accepted_target_race") == race_no_value and result.get("closed_or_suspended") == "YES" for result in racecard_results) else "NO"
        reason = race_missing_reasons.get(race_no_value, "CLOSED_OR_NOT_AVAILABLE_FROM_CURRENT_SPORTSBET_ENDPOINT")
        race_lines.append(
            (
                f"R{race_no_value}: expected={target['expected_runner_count']}; rows={len(rows_for_race)}; "
                f"prices={price_count}; scratched={scratched_count}; event_ids={','.join(event_id_values) or '-'}; "
                f"closed_or_suspended={closed_detected}; reason={reason}"
            )
        )

    missing_races = len(targets) - covered_races
    audit_lines = [
        "EDGEIQ SPORTSBET FULL-DAY RACECARD CAPTURE V5.2",
        "=" * 90,
        f"captured_at={captured_at}",
        f"local_time={datetime.now(LOCAL_TZ).isoformat(timespec='seconds')}",
        f"target_track={target_track}",
        f"target_races={','.join(str(target['race_no']) for target in targets)}",
        f"target_runner_count={len(fair)}",
        f"sportsbet_endpoints_tested={len(endpoints_tested)}",
        f"events_seen={len(event_candidates)}",
        f"events_matched_to_target_races={len(accepted_event_by_race)}",
        f"racecards_requested={racecards_requested}",
        f"racecards_succeeded={racecards_succeeded}",
        f"racecards_failed={racecards_failed}",
        f"runner_rows_written={len(market_rows)}",
        f"races_covered={covered_races}",
        f"races_missing={missing_races}",
        "",
        "ENDPOINTS TESTED",
    ]
    for endpoint in endpoints_tested:
        audit_lines.append("; ".join(f"{key}={value}" for key, value in endpoint.items()))
    audit_lines.extend(["", "PRICE COUNT BY RACE"])
    audit_lines.extend(race_lines)

    AUDIT_TXT.write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

    print(f"wrote: {FULL_DAY_EVENTS_OUT}")
    print(f"wrote: {FULL_DAY_RACECARDS_OUT}")
    print(f"wrote: {MARKET_OUT}")
    print(f"wrote: {AUDIT_TXT}")
    print()
    print("\n".join(audit_lines[:20]))
    print()
    print("\n".join(race_lines))
    print("=" * 90)


if __name__ == "__main__":
    main()
