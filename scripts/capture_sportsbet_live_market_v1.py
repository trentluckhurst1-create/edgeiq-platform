from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from edgeiq_csv_utils import canon, clean, parse_datetime, race_no, read_csv
from edgeiq_memory_safe_io import write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SELECTOR = DATA / "edgeiq_active_race_selector.csv"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"

MARKET_OUT = DATA / "sportsbet_live_market_v1.csv"
STATUS_OUT = DATA / "sportsbet_live_market_status_v1.csv"
LOG_OUT = DATA / "sportsbet_live_market_capture_log_v1.csv"
RAW_SAMPLE_OUT = DATA / "sportsbet_live_market_raw_events_sample_v1.json"

NEXT_EVENTS_URL = (
    "https://www.sportsbet.com.au/apigw/sportsbook-racing/Sportsbook/Racing/NextEvents"
    "?racingFilters=HR_DOMESTIC,GH_DOMESTIC,HA_DOMESTIC&groupByFilters=true"
)
RACECARD_URL_TEMPLATE = (
    "https://www.sportsbet.com.au/apigw/sportsbook-racing/Sportsbook/Racing/Events/{event_id}/Racecard"
)

LOCAL_TZ = timezone(timedelta(hours=10), name="Australia/Sydney")
REQUEST_TIMEOUT_SECONDS = 20
MAX_EVENT_FETCH = 16

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

STATUS_FIELDS = [
    "capture_timestamp_utc",
    "source",
    "source_status",
    "events_seen",
    "events_selected",
    "racecards_requested",
    "racecards_succeeded",
    "racecards_failed",
    "rows_written",
    "tracks_captured",
    "races_captured",
    "prices_captured",
    "notes",
]

LOG_FIELDS = [
    "timestamp_utc",
    "step_order",
    "step_name",
    "status",
    "url",
    "items",
    "notes",
]

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


@dataclass
class FetchResult:
    ok: bool
    status: str
    url: str
    payload: Any | None
    raw_text: str
    notes: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_now() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


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


def iter_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from iter_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_dicts(value)


def iter_lists(node: Any):
    if isinstance(node, list):
        yield node
        for value in node:
            yield from iter_lists(value)
    elif isinstance(node, dict):
        for value in node.values():
            yield from iter_lists(value)


def normalize_state(value: str) -> str:
    text = clean(value).upper()
    if text in {"VIC", "VICTORIA"}:
        return "VIC"
    if text in {"NSW", "NEW SOUTH WALES"}:
        return "NSW"
    if text in {"QLD", "QUEENSLAND"}:
        return "QLD"
    if text in {"SA", "SOUTH AUSTRALIA"}:
        return "SA"
    if text in {"WA", "WESTERN AUSTRALIA"}:
        return "WA"
    if text in {"TAS", "TASMANIA"}:
        return "TAS"
    if text in {"ACT", "AUSTRALIAN CAPITAL TERRITORY"}:
        return "ACT"
    if text in {"NT", "NORTHERN TERRITORY"}:
        return "NT"
    return text


def extract_race_no(*values: object) -> str:
    for value in values:
        text = clean(value)
        if not text:
            continue
        parsed = race_no(text)
        if parsed:
            return parsed
        upper = text.upper().replace("-", " ")
        for marker in [" RACE ", " R ", "RACE ", "R "]:
            if marker in f" {upper} ":
                digits = "".join(ch for ch in upper.split(marker.strip(), 1)[-1] if ch.isdigit())
                if digits:
                    return str(int(digits))
    return ""


def format_price(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    write_csv_atomic(path, rows, fields)


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


def request_json(url: str) -> FetchResult:
    request = Request(url, headers=HEADERS, method="GET")
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw_bytes = response.read()
            raw_text = raw_bytes.decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = f"HTTP {exc.code}"
        if exc.code in {401, 403, 429}:
            return FetchResult(False, "BLOCKED", url, None, "", detail)
        return FetchResult(False, "FETCH_FAILED", url, None, "", detail)
    except URLError as exc:
        return FetchResult(False, "FETCH_FAILED", url, None, "", f"URL error: {exc.reason}")
    except socket.timeout:
        return FetchResult(False, "FETCH_FAILED", url, None, "", "socket timeout")
    except Exception as exc:  # pragma: no cover - safe fallback
        return FetchResult(False, "FETCH_FAILED", url, None, "", f"unexpected fetch error: {exc}")

    lowered = raw_text.lower()
    if any(token in lowered for token in ["access denied", "forbidden", "captcha", "cloudflare", "bot challenge"]):
        return FetchResult(False, "BLOCKED", url, None, raw_text[:4000], "response indicates access blocked")

    try:
        payload = json.loads(raw_text)
    except JSONDecodeError:
        status = "SCHEMA_CHANGED"
        if lowered.startswith("<!doctype") or lowered.startswith("<html"):
            status = "BLOCKED"
        return FetchResult(False, status, url, None, raw_text[:4000], "response was not valid JSON")

    return FetchResult(True, "FRESH", url, payload, raw_text[:4000], "ok")


def safe_dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except PermissionError:
        return


def selector_targets() -> list[dict[str, str]]:
    rows = read_csv(SELECTOR)
    if rows:
        return rows
    return read_csv(UNIVERSE)


def parse_race_time_value(value: object):
    if isinstance(value, (int, float)):
        if value > 1000000000:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone(LOCAL_TZ)
        return None
    text = clean(value)
    if text.isdigit() and len(text) >= 10:
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc).astimezone(LOCAL_TZ)
        except ValueError:
            return None
    return parse_datetime(value)


def match_selector(candidate: dict[str, str], selectors: list[dict[str, str]]) -> dict[str, str] | None:
    cand_race_no = clean(candidate.get("race_no"))
    cand_date = clean(candidate.get("race_date"))
    cand_track_key = canon(candidate.get("track") or candidate.get("meeting_name") or candidate.get("event_name"))
    for row in selectors:
        sel_race_no = clean(row.get("race_no"))
        if cand_race_no and sel_race_no and cand_race_no != sel_race_no:
            continue
        sel_date = clean(row.get("race_date") or row.get("date"))
        if cand_date and sel_date and cand_date != sel_date:
            continue
        sel_track_key = canon(row.get("track") or row.get("meeting_name"))
        if cand_track_key and sel_track_key and (sel_track_key in cand_track_key or cand_track_key in sel_track_key):
            return row
    return None


def simplify_track_label(*values: object) -> str:
    raw = " ".join(clean(value) for value in values if clean(value))
    if not raw:
        return ""
    words = [word for word in raw.replace("/", " ").replace("-", " ").split() if word]
    blacklist = {"SPORTSBET", "BET365", "TAB", "NEDS", "PICKLEBET", "RACES", "RACING", "CLUB", "THE"}
    filtered = [word for word in words if word.upper() not in blacklist]
    if filtered:
        raw = " ".join(filtered)
    return clean(raw.upper())


def event_candidate(node: dict[str, Any], selectors: list[dict[str, str]]) -> dict[str, str] | None:
    event_id = first_non_empty(node, ["eventid", "event_id"])
    if not event_id:
        fallback_id = first_non_empty(node, ["id"])
        if fallback_id and any(clean(node.get(name)) for name in ["eventName", "event_name", "meetingName", "trackName", "raceNo", "raceNumber"]):
            event_id = fallback_id
    if not event_id:
        return None

    meeting_name = first_non_empty(
        node,
        [
            "meetingname",
            "meeting_name",
            "meeting",
            "trackname",
            "track_name",
            "venuename",
            "venue_name",
            "venue",
            "competitionname",
            "competition_name",
        ],
    )
    event_name = first_non_empty(node, ["eventname", "event_name", "name", "displayname", "display_name", "racename", "race_name", "title"])
    race_time_raw = first_non_empty(node, ["racetime", "race_time", "starttime", "start_time", "eventstarttime", "advertisedstarttime", "scheduledstarttime", "startdate"])
    if not race_time_raw and "startTime" in node:
        race_time = parse_race_time_value(node.get("startTime"))
    else:
        race_time = parse_race_time_value(race_time_raw)
    race_no_value = extract_race_no(
        first_non_empty(node, ["raceno", "race_no", "racenumber", "race_number", "eventnumber", "event_number"]),
        event_name,
        meeting_name,
    )
    state = normalize_state(first_non_empty(node, ["state", "stateabbr", "venue_state", "trackstate", "region"]))
    country = first_non_empty(node, ["country", "countryname", "country_name"])
    class_name = first_non_empty(node, ["classname", "class_name", "class"])
    race_type = first_non_empty(node, ["type", "race_type", "category"])
    track = simplify_track_label(first_non_empty(node, ["trackname", "track_name", "track", "meetingname", "meeting_name", "meeting"]), meeting_name)

    if not race_time or not race_no_value or not (meeting_name or track or event_name):
        return None

    candidate = {
        "event_id": event_id,
        "meeting_name": meeting_name or track or event_name,
        "event_name": event_name or meeting_name,
        "track": track or simplify_track_label(meeting_name or event_name),
        "race_no": race_no_value,
        "race_time": race_time.astimezone(LOCAL_TZ).isoformat(timespec="minutes"),
        "race_date": race_time.astimezone(LOCAL_TZ).date().isoformat(),
        "state": state,
        "country": country,
        "class_name": class_name,
        "race_type": race_type,
        "notes": "",
    }
    country_upper = clean(candidate.get("country")).upper()
    class_upper = clean(candidate.get("class_name")).upper()
    type_upper = clean(candidate.get("race_type")).upper()
    track_upper = clean(candidate.get("track")).upper()

    if country_upper != "AUSTRALIA":
        return None

    if "HORSES" not in class_upper and type_upper != "HORSE":
        return None

    # EDGEiQ Racing is VIC-only while model is being perfected.
    # Sportsbet NextEvents often does not expose a reliable state field, so we use an explicit VIC thoroughbred track allowlist.
    vic_tracks = {
        "MOE", "PAKENHAM", "SALE", "SANDOWN", "CAULFIELD", "FLEMINGTON", "BALLARAT",
        "BENDIGO", "GEELONG", "WARRNAMBOOL", "WANGARATTA", "WODONGA", "SEYMOUR",
        "CRANBOURNE", "KYNETON", "HAMILTON", "MORNINGTON", "TERANG", "ARARAT",
        "STAWELL", "COLAC", "CAMPERDOWN", "ECHUCA", "MILDURA", "SWAN HILL",
        "BENALLA", "BAIRNSDALE", "CASTERTON", "HANGING ROCK", "YARRA VALLEY"
    }

    if track_upper not in vic_tracks:
        return None

    selector_match = match_selector(candidate, selectors)
    if selector_match:
        selector_track = clean(selector_match.get("track"))
        selector_race_date = clean(selector_match.get("race_date") or selector_match.get("date"))
        selector_race_no = clean(selector_match.get("race_no"))
        if selector_track:
            candidate["track"] = selector_track
        if selector_race_date:
            candidate["race_date"] = selector_race_date
        if selector_race_no:
            candidate["race_no"] = selector_race_no
        candidate["race_id"] = clean(selector_match.get("race_key")) or f"{candidate["race_date"]}_{candidate["track"]}_R{candidate["race_no"]}"
        candidate["meeting_key"] = clean(selector_match.get("meeting_key")) or f"{candidate["race_date"]}_{candidate["track"]}"
        candidate["selector_match"] = "YES"
        candidate["match_confidence"] = "HIGH"
    else:
        candidate["race_id"] = f"{candidate["race_date"]}_{candidate["track"]}_R{candidate["race_no"]}"
        candidate["meeting_key"] = f"{candidate["race_date"]}_{candidate["track"]}"
        candidate["selector_match"] = "NO"
        candidate["match_confidence"] = "MEDIUM"

    candidate["state"] = "VIC"
    return candidate


def extract_event_candidates(payload: Any, selectors: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    candidates: list[dict[str, str]] = []
    for node in iter_dicts(payload):
        candidate = event_candidate(node, selectors)
        if not candidate:
            continue
        event_id = clean(candidate.get("event_id"))
        if event_id in seen:
            continue
        seen.add(event_id)
        candidates.append(candidate)

    selector_matches = [row for row in candidates if clean(row.get("selector_match")) == "YES"]
    selected = selector_matches if selector_matches else candidates
    selected.sort(key=lambda row: (clean(row.get("selector_match")) != "YES", clean(row.get("race_time")), clean(row.get("track")), clean(row.get("race_no"))))
    return selected[:MAX_EVENT_FETCH]


def looks_scratched(item: dict[str, Any]) -> bool:
    flags = [
        first_non_empty(item, ["isscratched", "is_scratched", "scratched"]),
        first_non_empty(item, ["status", "selectionstatus", "runnerstatus", "statuscode"]),
    ]
    blob = " ".join(flag.upper() for flag in flags if flag)
    return any(token in blob for token in ["SCR", "SCRATCH", "WITHDRAWN", "REMOVED"])


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
        ]
        for key in direct_order:
            value = first_non_empty(node, [key])
            parsed = to_float(value)
            if parsed is not None:
                return parsed
        for key, value in node.items():
            lowered = str(key).lower()
            if isinstance(value, dict) and lowered in {"price", "prices", "odds", "fixedodds", "fixed", "win", "winprice", "betoffer", "offer"}:
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


def selection_row(item: dict[str, Any], event: dict[str, str], market_id: str, market_name: str, captured_at: str) -> dict[str, object] | None:
    horse = first_non_empty(item, ["horse", "runnername", "runner_name", "selectionname", "selection_name", "competitorname", "horse_name", "name", "displayname"])
    if not horse:
        return None
    is_scratched = looks_scratched(item)
    status_text = first_non_empty(item, ["status", "selectionstatus", "runnerstatus", "statuscode", "bettingstatus", "pricecode"])

    price = extract_price(item)
    if price is None and not is_scratched:
        return None

    selection_id = first_non_empty(item, ["selectionid", "selection_id", "outcomeid", "outcome_id", "runnerid", "runner_id", "competitorid", "id"])
    horse_key = canon(horse)
    race_id = clean(event.get("race_id"))
    if not race_id:
        race_date = clean(event.get("race_date"))
        track = clean(event.get("track"))
        race_no_value = clean(event.get("race_no"))
        race_id = f"{race_date}_{track}_R{race_no_value}" if race_date and track and race_no_value else clean(event.get("event_id"))

    price_text = format_price(price) if price is not None else ""
    return {
        "capture_timestamp_utc": captured_at,
        "source": "Sportsbet",
        "source_status": "FRESH",
        "market_source": "Sportsbet Racecard",
        "market_captured_at": captured_at,
        "event_id": clean(event.get("event_id")),
        "race_id": race_id,
        "track": clean(event.get("track")),
        "race_no": clean(event.get("race_no")),
        "race_time": clean(event.get("race_time")),
        "race_date": clean(event.get("race_date")),
        "date": clean(event.get("race_date")),
        "horse": clean(horse),
        "horse_key": horse_key,
        "price_win": price_text,
        "sportsbet_price": price_text,
        "market_type": "Win",
        "market_name": market_name or "Win",
        "market_id": market_id,
        "selection_id": selection_id,
        "meeting_name": clean(event.get("meeting_name")),
        "event_name": clean(event.get("event_name")),
        "state": clean(event.get("state")) or "VIC",
        "source_url": RACECARD_URL_TEMPLATE.format(event_id=clean(event.get("event_id"))),
        "bookmaker": "Sportsbet",
        "timestamp": captured_at,
        "notes": "selector_match" if clean(event.get("selector_match")) == "YES" else "",
        "market_mover": "",
        "recent_odds_fluctuations": "",
        "is_scratched": "TRUE" if is_scratched else "FALSE",
        "runner_status": "SCRATCHED" if is_scratched else "ACTIVE",
        "selection_status": status_text,
        "status_code": status_text,
        "match_confidence": clean(event.get("match_confidence")) or ("HIGH" if clean(event.get("selector_match")) == "YES" else "MEDIUM"),
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
            if not isinstance(item, dict):
                continue
            row = selection_row(item, event, market_id, market_name, captured_at)
            if row:
                rows.append(row)
    return rows


def market_priority(market_name: str) -> int:
    name = clean(market_name).lower()
    if name in {"win", "winner", "fixed odds win"} or name.startswith("win "):
        return 1
    if name in {"top 2", "top2", "top two"}:
        return 2
    if name in {"top 3", "top3", "top three"}:
        return 3
    if name in {"top 4", "top4", "top four"}:
        return 4
    return 99


def market_has_selection_list(node: dict[str, Any]) -> bool:
    return any(isinstance(node.get(key), list) for key in ["selections", "runners", "outcomes", "participants", "competitors"])


def extract_racecard_rows(payload: Any, event: dict[str, str], captured_at: str) -> list[dict[str, object]]:
    market_nodes: list[dict[str, Any]] = []

    for node in iter_dicts(payload):
        if not isinstance(node, dict):
            continue

        market_name = first_non_empty(
            node,
            ["marketname", "market_name", "name", "displayname", "title", "bettype"],
        )

        if not market_name or not market_has_selection_list(node):
            continue

        priority = market_priority(market_name)

        if priority <= 4:
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
        market_name = first_non_empty(
            market,
            ["marketname", "market_name", "name", "displayname", "title", "bettype"],
        ) or "Unknown"

        for row in rows_from_market_node(market, event, captured_at):
            key = (clean(str(row.get("event_id"))), clean(str(row.get("horse_key"))))
            if key in seen_keys:
                continue

            row["market_type"] = market_name
            row["market_name"] = market_name
            row["notes"] = (
                clean(str(row.get("notes"))) + f"; market_fallback={market_name}"
            ).strip("; ")

            seen_keys.add(key)
            rows.append(row)

    if rows:
        return rows

    for node in iter_dicts(payload):
        if not isinstance(node, dict):
            continue

        row = selection_row(node, event, "", "Fallback", captured_at)
        if not row:
            continue

        key = (clean(str(row.get("event_id"))), clean(str(row.get("horse_key"))))
        if key in seen_keys:
            continue

        row["notes"] = (
            clean(str(row.get("notes"))) + "; generic_fallback"
        ).strip("; ")

        seen_keys.add(key)
        rows.append(row)

    return rows


def main() -> None:
    captured_at = utc_now()
    log_rows: list[dict[str, object]] = []
    selectors = selector_targets()

    next_events = request_json(NEXT_EVENTS_URL)
    log_rows.append({
        "timestamp_utc": captured_at,
        "step_order": 1,
        "step_name": "fetch_next_events",
        "status": next_events.status,
        "url": NEXT_EVENTS_URL,
        "items": 0,
        "notes": next_events.notes,
    })

    selected_events: list[dict[str, str]] = []
    market_rows: list[dict[str, object]] = []
    racecards_requested = 0
    racecards_succeeded = 0
    racecards_failed = 0
    source_status = "FETCH_FAILED"
    notes = next_events.notes

    sample_payload: dict[str, Any] = {
        "captured_at": captured_at,
        "next_events_status": next_events.status,
        "selected_events": [],
        "raw_excerpt": next_events.raw_text[:4000],
    }

    if next_events.ok and next_events.payload is not None:
        selected_events = extract_event_candidates(next_events.payload, selectors)
        sample_payload["selected_events"] = selected_events[:20]
        log_rows.append({
            "timestamp_utc": captured_at,
            "step_order": 2,
            "step_name": "select_vic_events",
            "status": "PASS" if selected_events else "EMPTY",
            "url": NEXT_EVENTS_URL,
            "items": len(selected_events),
            "notes": "matched active selector" if any(clean(row.get("selector_match")) == "YES" for row in selected_events) else "no active selector match; VIC fallback applied",
        })

        for index, event in enumerate(selected_events, start=1):
            racecard_url = RACECARD_URL_TEMPLATE.format(event_id=clean(event.get("event_id")))
            racecards_requested += 1
            racecard = request_json(racecard_url)
            if racecard.ok and racecard.payload is not None:
                rows = extract_racecard_rows(racecard.payload, event, captured_at)
                if rows:
                    market_rows.extend(rows)
                    racecards_succeeded += 1
                    status = "PASS"
                    note = f"{clean(event.get('track'))} R{clean(event.get('race_no'))}: {len(rows)} prices"
                else:
                    racecards_failed += 1
                    status = "SCHEMA_CHANGED"
                    note = f"{clean(event.get('track'))} R{clean(event.get('race_no'))}: no runner prices extracted"
                if index <= 3:
                    sample_payload[f"racecard_sample_{index}"] = {
                        "event": event,
                        "raw_excerpt": racecard.raw_text[:4000],
                    }
            else:
                racecards_failed += 1
                status = racecard.status
                note = f"{clean(event.get('track'))} R{clean(event.get('race_no'))}: {racecard.notes}"

            log_rows.append({
                "timestamp_utc": captured_at,
                "step_order": 2 + index,
                "step_name": "fetch_racecard",
                "status": status,
                "url": racecard_url,
                "items": len(market_rows),
                "notes": note,
            })

        if market_rows:
            source_status = "FRESH"
            notes = f"captured {len(market_rows)} prices across {len({clean(str(row.get('event_id'))) for row in market_rows})} races"
        elif selected_events:
            source_status = "SCHEMA_CHANGED" if racecards_succeeded == 0 else "EMPTY"
            notes = "events were found but no priced runners were extracted"
        else:
            source_status = "EMPTY"
            notes = "no matching VIC thoroughbred events selected from NextEvents"
    else:
        source_status = next_events.status
        notes = next_events.notes

    market_rows.sort(key=lambda row: (clean(str(row.get("race_time"))), clean(str(row.get("track"))), clean(str(row.get("race_no"))), clean(str(row.get("horse")))))

    if market_rows:
        write_csv(MARKET_OUT, market_rows, MARKET_FIELDS)
    else:
        notes = notes + "; protected previous sportsbet_live_market_v1.csv because current capture returned zero rows"
    write_csv(
        STATUS_OUT,
        [{
            "capture_timestamp_utc": captured_at,
            "source": "Sportsbet",
            "source_status": source_status,
            "events_seen": len(selected_events) if next_events.ok else 0,
            "events_selected": len(selected_events),
            "racecards_requested": racecards_requested,
            "racecards_succeeded": racecards_succeeded,
            "racecards_failed": racecards_failed,
            "rows_written": len(market_rows),
            "tracks_captured": len({clean(str(row.get("track"))) for row in market_rows if clean(str(row.get("track")))}),
            "races_captured": len({clean(str(row.get("event_id"))) for row in market_rows if clean(str(row.get("event_id")))}),
            "prices_captured": len([row for row in market_rows if clean(str(row.get("price_win")))]),
            "notes": notes,
        }],
        STATUS_FIELDS,
    )
    write_csv(LOG_OUT, log_rows, LOG_FIELDS)
    safe_dump_json(RAW_SAMPLE_OUT, sample_payload)

    print("=" * 90)
    print("SPORTSBET LIVE MARKET CAPTURE V1")
    print("=" * 90)
    print("SOURCE STATUS:", source_status)
    print("EVENTS SELECTED:", len(selected_events))
    print("RACECARDS REQUESTED:", racecards_requested)
    print("RACECARDS SUCCEEDED:", racecards_succeeded)
    print("ROWS WRITTEN:", len(market_rows))
    print("TRACKS:", len({clean(str(row.get('track'))) for row in market_rows if clean(str(row.get('track'))) }))
    print("RACES:", len({clean(str(row.get('event_id'))) for row in market_rows if clean(str(row.get('event_id'))) }))
    print("OUT:", MARKET_OUT)
    print("STATUS:", STATUS_OUT)
    print("LOG:", LOG_OUT)
    print("RAW SAMPLE:", RAW_SAMPLE_OUT)


if __name__ == "__main__":
    main()
