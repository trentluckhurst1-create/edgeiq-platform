from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

from edgeiq_three_day_window_v1_common import build_three_day_window
from pathlib import Path
from typing import Any, Iterable

csv.field_size_limit(1024 * 1024 * 64)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RAW_JSON = DATA / "edgeiq_racingcom_three_day_raw_meetings_v1.json"
RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"

CSV_SOURCES = [
    DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv",
    RACE_LIST,
    DATA / "race_fields.csv",
    DATA / "edgeiq_vic_three_day_race_fields.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_tab_calendar_racecards_vic_v1.csv",
]

OUTPUT = DATA / "edgeiq_three_day_product_catalog_v1.json"
SUMMARY = DATA / "edgeiq_three_day_product_catalog_v1_summary.txt"
AUDIT = DATA / "edgeiq_three_day_product_catalog_v1_audit.txt"

THREE_DAY_WINDOW = build_three_day_window()
TODAY = date.fromisoformat(THREE_DAY_WINDOW.today)
TARGET_DATES = [
    date.fromisoformat(THREE_DAY_WINDOW.today),
    date.fromisoformat(THREE_DAY_WINDOW.tomorrow),
    date.fromisoformat(THREE_DAY_WINDOW.dayPlus2),
]
TARGET_DATE_SET = {item.isoformat() for item in TARGET_DATES}

VICTORIAN_VENUES = {
    "ARARAT",
    "BAIRNSDALE",
    "BALLARAT",
    "BALNARRING",
    "BENALLA",
    "BENDIGO",
    "CAULFIELD",
    "CAULFIELD HEATH",
    "COLAC",
    "COLERAINE",
    "CRANBOURNE",
    "DONALD",
    "ECHUCA",
    "FLEMINGTON",
    "GEELONG",
    "HAMILTON",
    "HORSHAM",
    "KERANG",
    "KILMORE",
    "KYNETON",
    "MANSFIELD",
    "MOE",
    "MOONEE VALLEY",
    "MORNINGTON",
    "MURTOA",
    "PAKENHAM",
    "SALE",
    "SANDOWN",
    "SANDOWN HILLSIDE",
    "SANDOWN LAKESIDE",
    "SEYMOUR",
    "ST ARNAUD",
    "STAWELL",
    "SWAN HILL",
    "TERANG",
    "TOWONG",
    "WANGARATTA",
    "WARRACKNABEAL",
    "WARRNAMBOOL",
    "WERRIBEE",
    "WODONGA",
    "YARRA VALLEY",
    "YEA",
}

DATE_KEYS = (
    "date",
    "raceDate",
    "race_date",
    "meetingDate",
    "meeting_date",
    "startDate",
    "start_date",
    "meetingDateLocal",
)

MEETING_KEYS = (
    "meeting",
    "meetingName",
    "meeting_name",
    "venue",
    "venueName",
    "venue_name",
    "track",
    "trackName",
    "track_name",
    "racecourse",
    "courseName",
)

RACE_NUMBER_KEYS = (
    "raceNumber",
    "race_number",
    "number",
    "raceNo",
    "race_no",
    "raceNum",
)

RACE_NAME_KEYS = (
    "raceName",
    "race_name",
    "name",
    "title",
    "eventName",
    "event_name",
)

RACE_TIME_KEYS = (
    "raceTime",
    "race_time",
    "startTime",
    "start_time",
    "advertisedStart",
    "advertised_start",
    "jumpTime",
    "jump_time",
)

DISTANCE_KEYS = (
    "distance",
    "distanceMetres",
    "distance_metres",
    "metres",
    "meters",
)

RUNNER_NAME_KEYS = (
    "runner",
    "runnerName",
    "runner_name",
    "horseName",
    "horse_name",
    "horse",
    "name",
)

RUNNER_NUMBER_KEYS = (
    "raceEntryNumber",
    "race_entry_number",
    "runnerNumber",
    "runner_number",
    "saddlecloth",
    "saddleclothNumber",
    "saddlecloth_number",
    "tabNumber",
    "tab_number",
    "number",
)

BARRIER_KEYS = (
    "barrier",
    "barrierNumber",
    "barrier_number",
    "draw",
)

JOCKEY_KEYS = (
    "jockey",
    "jockeyName",
    "jockey_name",
)

TRAINER_KEYS = (
    "trainer",
    "trainerName",
    "trainer_name",
)

WEIGHT_KEYS = (
    "weight",
    "allocatedWeight",
    "allocated_weight",
)

MARKET_KEYS = (
    "market",
    "price",
    "odds",
    "fixedWin",
    "fixed_win",
)

RUNNER_CONTAINER_KEYS = (
    "runners",
    "field",
    "fields",
    "entries",
    "acceptances",
    "horses",
    "competitors",
)

RACE_CONTAINER_KEYS = (
    "races",
    "raceList",
    "race_list",
    "events",
    "raceEvents",
    "race_events",
)


def first(mapping: dict[str, Any], keys: Iterable[str]) -> Any:
    lowered = {str(key).lower(): key for key in mapping.keys()}

    for key in keys:
        actual = key if key in mapping else lowered.get(key.lower())

        if actual is None:
            continue

        value = mapping.get(actual)

        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        return value

    return None


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, (dict, list, tuple)):
        return None

    text = re.sub(r"\s+", " ", str(value)).strip()

    if not text or text.lower() in {
        "none",
        "null",
        "n/a",
        "na",
        "-",
    }:
        return None

    return text


def parse_structured(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value

    if not isinstance(value, str):
        return value

    text = value.strip()

    if not text or text[0] not in "[{":
        return value

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return value


def structured_first(value: Any, keys: Iterable[str]) -> Any:
    parsed = parse_structured(value)

    if not isinstance(parsed, dict):
        return None

    return first(parsed, keys)


def text_from_value(value: Any, keys: Iterable[str] = ()) -> str | None:
    parsed = parse_structured(value)

    if isinstance(parsed, dict):
        nested = structured_first(parsed, keys or RUNNER_NAME_KEYS)

        if nested is not None and nested is not parsed:
            return text_from_value(nested, keys)

        return None

    if isinstance(parsed, list):
        return None

    return clean_text(parsed)


def runner_name_from(row: dict[str, Any]) -> str | None:
    for key in (
        "horseName",
        "horse_name",
        "runnerName",
        "runner_name",
        "runner",
        "name",
    ):
        value = first(row, (key,))
        text = text_from_value(value)

        if text:
            return text

    horse = first(row, ("horse",))
    return text_from_value(
        horse,
        (
            "horseName",
            "horse_name",
            "runnerName",
            "runner_name",
            "name",
            "fullName",
            "full_name",
        ),
    )


def runner_silk_from(row: dict[str, Any]) -> str | None:
    return text_from_value(
        first(row, ("silkUrl", "silk_url", "silk")),
    ) or text_from_value(
        structured_first(
            first(row, ("horse",)),
            ("silkUrl", "silk_url", "silk"),
        ),
    )


def runner_last_five_from(row: dict[str, Any]) -> list[str]:
    value = first(
        row,
        (
            "lastFive",
            "last5",
            "last_five",
            "recentForm",
            "recent_form",
            "form",
        ),
    )

    if value is None:
        value = structured_first(
            first(row, ("horse",)),
            (
                "lastFive",
                "last5",
                "last_five",
                "recentForm",
                "recent_form",
                "form",
            ),
        )

    parsed = parse_structured(value)

    if isinstance(parsed, str):
        tokens = re.split(r"[\s,]+", parsed)
    elif isinstance(parsed, list):
        tokens = parsed
    else:
        tokens = []

    allowed_codes = {"DNF", "F", "UR", "PU", "L", "BD"}
    last_five: list[str] = []

    for token in tokens:
        text = clean_text(token)

        if not text:
            continue

        text = text.upper()

        if text in {"-", "X"}:
            continue

        if text in allowed_codes or re.fullmatch(r"\d{1,2}", text):
            last_five.append(text)

        if len(last_five) >= 5:
            break

    return last_five


def parse_date(value: Any) -> str | None:
    text = clean_text(value)

    if not text:
        return None

    iso_match = re.search(
        r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b",
        text,
    )

    if iso_match:
        return (
            f"{int(iso_match.group(1)):04d}-"
            f"{int(iso_match.group(2)):02d}-"
            f"{int(iso_match.group(3)):02d}"
        )

    for pattern in (
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            return datetime.strptime(
                text[:19],
                pattern,
            ).date().isoformat()
        except ValueError:
            pass

    return None


def meeting_display_name(value: Any) -> str:
    text = clean_text(value) or ""

    text = re.sub(
        r"^(SPORTSBET|LADBROKES|BET365|PICKLEBET PARK)[-\s]+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"SYNTHETIC(?:THETIC)+",
        "SYNTHETIC",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^SOUTHSIDE\s+PAKENHAM\s+SYNTHETIC$",
        "PAKENHAM SYNTHETIC",
        text,
        flags=re.IGNORECASE,
    )

    return re.sub(r"\s+", " ", text).strip()


def meeting_key(value: Any) -> str:
    text = meeting_display_name(value).upper()

    aliases = {
        "CAULFIELD HEATH": "CAULFIELD",
        "CAULFIELD": "CAULFIELD",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
        "LADBROKES PARK": "SANDOWN",
        "LADBROKES PARK HILLSIDE": "SANDOWN",
        "LADBROKES PARK LAKESIDE": "SANDOWN",
        "BALLARAT SYNTHETIC": "BALLARAT",
        "GEELONG SYNTHETIC": "GEELONG",
        "PAKENHAM SYNTHETIC": "PAKENHAM",
        "PICKLEBET PARK WODONGA": "WODONGA",
        "WODONGA": "WODONGA",
    }

    return aliases.get(text, text)


def is_victorian_meeting(value: Any) -> bool:
    display = meeting_display_name(value).upper()
    key = meeting_key(value)

    return display in VICTORIAN_VENUES or key in VICTORIAN_VENUES


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    text = clean_text(value)

    return text is not None and text.upper() in {
        "TRUE",
        "YES",
        "Y",
        "1",
    }


def excluded_event(row: dict[str, Any]) -> bool:
    text = " ".join(
        clean_text(value) or ""
        for value in (
            row.get("UrlSegment"),
            row.get("url_segment"),
            row.get("EventType"),
            row.get("event_type"),
            row.get("FullStatus"),
            row.get("full_status"),
            row.get("MeetStatus"),
            row.get("meet_status"),
        )
    ).upper()

    sub_types = row.get("SubTypes") or row.get("sub_types") or []

    if isinstance(sub_types, list):
        text = f"{text} {' '.join(str(item).upper() for item in sub_types)}"

    return (
        truthy(row.get("IsTrial"))
        or truthy(row.get("is_trial"))
        or truthy(row.get("IsJumpout"))
        or truthy(row.get("is_jumpout"))
        or "JUMPOUT" in text
        or "JUMP OUT" in text
        or "TRIAL" in text
    )


def race_list_has_target_races() -> bool:
    if not RACE_LIST.exists():
        return False

    try:
        with RACE_LIST.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
    except Exception:
        return False

    dates_with_races = {
        parse_date(first(row, DATE_KEYS))
        for row in rows
        if integer(first(row, RACE_NUMBER_KEYS)) is not None
    }

    return TARGET_DATE_SET.issubset(dates_with_races)


def ensure_race_list_source() -> None:
    if race_list_has_target_races():
        return

    builder = ROOT / "scripts" / "build_edgeiq_racingcom_three_day_race_list_v1.py"

    if not builder.exists():
        return

    subprocess.run(
        [sys.executable, str(builder)],
        cwd=ROOT,
        check=True,
    )

    if not race_list_has_target_races():
        raise RuntimeError(
            "Racing.com three-day race list did not produce races for "
            f"all target dates: {sorted(TARGET_DATE_SET)}"
        )


def integer(value: Any) -> int | None:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def list_from(mapping: dict[str, Any], keys: Iterable[str]) -> list[Any]:
    value = first(mapping, keys)
    return value if isinstance(value, list) else []


def looks_like_race(mapping: dict[str, Any]) -> bool:
    race_number = integer(first(mapping, RACE_NUMBER_KEYS))

    if race_number is None or not 1 <= race_number <= 20:
        return False

    has_race_detail = any(
        first(mapping, keys) is not None
        for keys in (
            RACE_NAME_KEYS,
            RACE_TIME_KEYS,
            DISTANCE_KEYS,
        )
    )

    return has_race_detail


def looks_like_runner(mapping: dict[str, Any]) -> bool:
    name = runner_name_from(mapping)

    if not name:
        return False

    return any(
        first(mapping, keys) is not None
        for keys in (
            RUNNER_NUMBER_KEYS,
            BARRIER_KEYS,
            JOCKEY_KEYS,
            TRAINER_KEYS,
            WEIGHT_KEYS,
        )
    )


def runner_historical_runs_from(
    row: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Promote only the genuine previous-race summary supplied by the
    authoritative current Racing.com runner payload.

    This is source evidence, not a calculated performance record.
    Unknown values remain absent and no rating, time, margin,
    sectional, class or benchmark data is fabricated.
    """
    horse = first(row, ("horse",))

    last_item = first(
        row,
        (
            "lastProfessionalRaceEntryItem",
            "last_professional_race_entry_item",
        ),
    )

    if not isinstance(last_item, dict):
        last_item = structured_first(
            horse,
            (
                "lastProfessionalRaceEntryItem",
                "last_professional_race_entry_item",
            ),
        )

    if not isinstance(last_item, dict):
        return []

    race = first(last_item, ("race",))

    if not isinstance(race, dict):
        race = {}

    race_code = clean_text(
        first(
            last_item,
            (
                "raceCode",
                "race_code",
            ),
        )
    )

    race_date = parse_date(
        first(
            race,
            (
                "date",
                "raceDate",
                "race_date",
            ),
        )
    )

    position = integer(
        first(
            last_item,
            (
                "position",
                "finish",
                "finishPosition",
                "finish_position",
            ),
        )
    )

    position_abbreviation = clean_text(
        first(
            last_item,
            (
                "positionAbbreviation",
                "position_abbreviation",
                "finishAbv",
                "finish_abv",
            ),
        )
    )

    track = clean_text(
        first(
            race,
            (
                "venueAbbr",
                "venue",
                "track",
                "meeting",
            ),
        )
    )

    distance = clean_text(
        first(
            race,
            (
                "distance",
                "distanceMetres",
                "distance_m",
            ),
        )
    )

    field_size = integer(
        first(
            race,
            (
                "runnersCount",
                "runnerCount",
                "fieldSize",
                "field_size",
            ),
        )
    )

    horse_code = clean_text(
        first(
            row,
            (
                "horseCode",
                "horse_code",
            ),
        )
    ) or clean_text(
        structured_first(
            horse,
            (
                "id",
                "horseCode",
                "horse_code",
            ),
        )
    )

    # A usable source-history record requires an actual race identity
    # plus a date. A summary without those fields is not promoted.
    if not race_code or not race_date:
        return []

    historical_run: dict[str, Any] = {
        "raceCode": race_code,
        "date": race_date,
        "track": track,
        "distance": distance,
        "finishPosition": position,
        "finish": position_abbreviation or (
            str(position)
            if position is not None
            else None
        ),
        "fieldSize": field_size,
        "horseCode": horse_code,
        "source": (
            "RACING_COM_CURRENT_CATALOG_"
            "LAST_PROFESSIONAL_RACE_ENTRY"
        ),
        "sourceEvidenceLevel": (
            "AUTHORITATIVE_PREVIOUS_RACE_SUMMARY"
        ),
        "performanceRatingAvailable": False,
        "sectionalEvidenceAvailable": False,
        "benchmarkEvidenceAvailable": False,
    }

    return [
        {
            key: value
            for key, value in historical_run.items()
            if value is not None and value != ""
        }
    ]


def normalise_runner(
    row: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    number = first(row, RUNNER_NUMBER_KEYS)
    odds = first(row, ("odds",))

    if isinstance(odds, list):
        for quote in odds:
            if not isinstance(quote, dict):
                continue

            price = first(
                quote,
                (
                    "oddsWin",
                    "winOdds",
                    "fixedWin",
                    "price",
                ),
            )

            if price is not None:
                break
        else:
            price = first(row, MARKET_KEYS)
    else:
        price = first(row, MARKET_KEYS)

    historical_runs = runner_historical_runs_from(row)

    return {
        "official": {
            "no": number,
            "number": number,
            "runner": runner_name_from(row),
            "barrier": first(row, BARRIER_KEYS),
            "jockey": clean_text(first(row, JOCKEY_KEYS)),
            "trainer": clean_text(first(row, TRAINER_KEYS)),
            "weight": clean_text(first(row, WEIGHT_KEYS)),
            "market": price,
            "silkUrl": runner_silk_from(row),
            "lastFive": runner_last_five_from(row),
            "scratched": truthy(first(row, ("scratched", "isScratched", "scratchedFlag"))),
            "horseCountry": clean_text(first(row, ("horseCountry", "horse_country", "country"))),
            "apprenticeClaim": clean_text(first(row, ("apprenticeAllowedClaim", "claim", "claimKg"))),
            "currentGear": clean_text(
                first(row, ("currentGear", "gear", "gearChanges"))
            )
            or clean_text(
                structured_first(
                    first(row, ("horse",)),
                    ("currentGear", "gear", "gearChanges"),
                )
            ),
        },
        "historicalRuns": historical_runs,
        "evidenceRuns": list(historical_runs),
        "source": row,
    }


def find_runner_rows(race: dict[str, Any]) -> list[dict[str, Any]]:
    direct = [
        row
        for row in list_from(race, RUNNER_CONTAINER_KEYS)
        if isinstance(row, dict)
    ]

    form_entries = clean_text(race.get("form_entries_json"))
    entries: list[dict[str, Any]] = []

    if form_entries:
        try:
            parsed_entries = json.loads(form_entries)
        except json.JSONDecodeError:
            parsed_entries = []

        if isinstance(parsed_entries, list):
            entries = [
                row
                for row in parsed_entries
                if isinstance(row, dict)
                and runner_name_from(row)
            ]

    # Direct field data remains authoritative, but Racing.com form entries
    # enrich matching runners with stable source identity such as id/horseCode.
    if direct and entries:
        def identity(row: dict[str, Any]) -> str:
            number = str(first(row, RUNNER_NUMBER_KEYS) or "")
            name = runner_name_from(row) or ""
            normalised_name = re.sub(
                r"[^A-Z0-9]+",
                "",
                name.upper(),
            )
            return f"{number}|{normalised_name}"

        entry_by_identity = {
            identity(row): row
            for row in entries
            if identity(row)
        }

        enriched: list[dict[str, Any]] = []

        for row in direct:
            supplemental = entry_by_identity.get(identity(row))

            if supplemental:
                enriched.append(
                    merge_missing_values(row, supplemental)
                )
            else:
                enriched.append(row)

        return enriched

    if direct:
        return direct

    if entries:
        return entries

    candidates: list[dict[str, Any]] = []

    def walk(value: Any, depth: int = 0) -> None:
        if depth > 5:
            return

        if isinstance(value, dict):
            if looks_like_runner(value):
                candidates.append(value)
                return

            for child in value.values():
                walk(child, depth + 1)

        elif isinstance(value, list):
            for child in value:
                walk(child, depth + 1)

    walk(race)

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in candidates:
        name = (runner_name_from(row) or "").upper()

        number = str(first(row, RUNNER_NUMBER_KEYS) or "")
        identity = f"{number}|{name}"

        if not name or identity in seen:
            continue

        seen.add(identity)
        deduped.append(row)

    return deduped


def value_present(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {
            "none",
            "null",
            "n/a",
            "na",
            "-",
        }

    if isinstance(value, (list, tuple, dict)):
        return bool(value)

    return True


def runner_identity(runner: dict[str, Any]) -> str:
    official = runner.get("official") or {}
    source = runner.get("source") or {}

    number = (
        official.get("no")
        or official.get("number")
        or first(source, RUNNER_NUMBER_KEYS)
        or ""
    )

    name = (
        clean_text(official.get("runner"))
        or runner_name_from(source)
        or ""
    )

    normalised_name = re.sub(
        r"[^A-Z0-9]+",
        "",
        name.upper(),
    )

    return f"{number}|{normalised_name}"


def merge_missing_values(
    primary: dict[str, Any],
    supplemental: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(primary)

    for key, value in supplemental.items():
        current = merged.get(key)

        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = merge_missing_values(current, value)
            continue

        if not value_present(current) and value_present(value):
            merged[key] = value

    return merged


def merge_runner_records(
    primary: dict[str, Any],
    supplemental: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(primary)

    primary_official = primary.get("official") or {}
    supplemental_official = supplemental.get("official") or {}

    merged["official"] = merge_missing_values(
        primary_official,
        supplemental_official,
    )

    primary_source = primary.get("source") or {}
    supplemental_source = supplemental.get("source") or {}

    merged["source"] = merge_missing_values(
        primary_source,
        supplemental_source,
    )

    for collection_key in ("historicalRuns", "evidenceRuns"):
        primary_rows = primary.get(collection_key)
        supplemental_rows = supplemental.get(collection_key)

        if not primary_rows and supplemental_rows:
            merged[collection_key] = supplemental_rows

    return merged


def merge_race_records(
    primary: dict[str, Any],
    supplemental: dict[str, Any],
) -> dict[str, Any]:
    merged = merge_missing_values(primary, supplemental)

    primary_runners = [
        runner
        for runner in primary.get("runners", [])
        if isinstance(runner, dict)
    ]
    supplemental_runners = [
        runner
        for runner in supplemental.get("runners", [])
        if isinstance(runner, dict)
    ]

    merged_runners = list(primary_runners)
    runner_indexes = {
        runner_identity(runner): index
        for index, runner in enumerate(merged_runners)
        if runner_identity(runner)
    }

    for supplemental_runner in supplemental_runners:
        identity = runner_identity(supplemental_runner)

        if identity and identity in runner_indexes:
            index = runner_indexes[identity]
            merged_runners[index] = merge_runner_records(
                merged_runners[index],
                supplemental_runner,
            )
            continue

        runner_indexes[identity] = len(merged_runners)
        merged_runners.append(supplemental_runner)

    merged["runners"] = merged_runners
    return merged


def normalise_race(
    row: dict[str, Any],
    meeting_name: str,
    meeting_date: str,
) -> dict[str, Any]:
    number = integer(first(row, RACE_NUMBER_KEYS))

    if number is None:
        raise ValueError("Race number missing")

    runners_raw = find_runner_rows(row)

    return {
        "raceKey": (
            f"{meeting_date}|{meeting_key(meeting_name)}|R{number}"
        ),
        "raceNumber": number,
        "raceName": clean_text(
            first(row, RACE_NAME_KEYS)
        ) or f"Race {number}",
        "distance": clean_text(first(row, DISTANCE_KEYS)),
        "raceClass": clean_text(
            first(
                row,
                (
                    "raceClass",
                    "race_class",
                    "class",
                    "grade",
                    "conditions",
                ),
            )
        ),
        "raceTime": clean_text(first(row, RACE_TIME_KEYS)),
        "trackCondition": clean_text(
            first(
                row,
                (
                    "trackCondition",
                    "track_condition",
                    "condition",
                ),
            )
        ),
        "rail": clean_text(
            first(
                row,
                (
                    "rail",
                    "railPosition",
                    "rail_position",
                ),
            )
        ),
        "runners": [
            normalise_runner(runner, index)
            for index, runner in enumerate(runners_raw)
        ],
        "source": row,
    }


meetings: dict[tuple[str, str], dict[str, Any]] = {}
race_nodes_seen = 0
runner_nodes_seen = 0


def ensure_meeting(
    name: str,
    meeting_date: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    key = meeting_key(name)
    identity = (meeting_date, key)

    meeting = meetings.get(identity)

    if meeting is None:
        meeting = {
            "meetingKey": f"{meeting_date}|{key}",
            "meeting": meeting_display_name(name),
            "providerMeetingKey": key,
            "date": meeting_date,
            "trackCondition": clean_text(
                first(
                    source,
                    (
                        "trackCondition",
                        "track_condition",
                        "condition",
                    ),
                )
            ),
            "rail": clean_text(
                first(
                    source,
                    (
                        "rail",
                        "railPosition",
                        "rail_position",
                    ),
                )
            ),
            "raceCount": 0,
            "races": [],
            "source": source,
        }

        meetings[identity] = meeting

    return meeting


def walk_json(
    value: Any,
    inherited_meeting: str | None = None,
    inherited_date: str | None = None,
    depth: int = 0,
) -> None:
    global race_nodes_seen, runner_nodes_seen

    if depth > 30:
        return

    if isinstance(value, dict):
        own_meeting = clean_text(first(value, MEETING_KEYS))
        own_date = parse_date(first(value, DATE_KEYS))

        current_meeting = own_meeting or inherited_meeting
        current_date = own_date or inherited_date

        if (
            current_meeting
            and current_date in TARGET_DATE_SET
            and is_victorian_meeting(current_meeting)
            and not excluded_event(value)
        ):
            ensure_meeting(
                current_meeting,
                current_date,
                value,
            )

        if (
            current_meeting
            and current_date in TARGET_DATE_SET
            and is_victorian_meeting(current_meeting)
            and not excluded_event(value)
            and looks_like_race(value)
        ):
            race_nodes_seen += 1

            meeting = ensure_meeting(
                current_meeting,
                current_date,
                value,
            )

            try:
                race = normalise_race(
                    value,
                    current_meeting,
                    current_date,
                )
            except ValueError:
                race = None

            if race:
                runner_nodes_seen += len(race["runners"])

                existing_index = next(
                    (
                        index
                        for index, item in enumerate(meeting["races"])
                        if item["raceNumber"] == race["raceNumber"]
                    ),
                    None,
                )

                if existing_index is None:
                    meeting["races"].append(race)
                else:
                    existing = meeting["races"][existing_index]

                    existing_score = (
                        len(existing["runners"])
                        + sum(
                            bool(existing.get(field))
                            for field in (
                                "raceName",
                                "distance",
                                "raceTime",
                            )
                        )
                    )

                    new_score = (
                        len(race["runners"])
                        + sum(
                            bool(race.get(field))
                            for field in (
                                "raceName",
                                "distance",
                                "raceTime",
                            )
                        )
                    )

                    if new_score > existing_score:
                        meeting["races"][existing_index] = race

        for child in value.values():
            walk_json(
                child,
                current_meeting,
                current_date,
                depth + 1,
            )

    elif isinstance(value, list):
        for child in value:
            walk_json(
                child,
                inherited_meeting,
                inherited_date,
                depth + 1,
            )


ensure_race_list_source()


if RAW_JSON.exists():
    raw = json.loads(
        RAW_JSON.read_text(
            encoding="utf-8-sig",
        )
    )

    walk_json(raw)


def current_csv_meeting_identities() -> set[tuple[str, str]]:
    identities: set[tuple[str, str]] = set()

    for path in CSV_SOURCES:
        if not path.exists():
            continue

        try:
            with path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
        except Exception:
            continue

        for row in rows:
            date_value = parse_date(first(row, DATE_KEYS))
            name_value = clean_text(first(row, MEETING_KEYS))
            if date_value in TARGET_DATE_SET and name_value and is_victorian_meeting(name_value) and not excluded_event(row):
                identities.add((date_value, meeting_key(name_value)))

    return identities


def add_csv_sources() -> None:
    for path in CSV_SOURCES:
        if not path.exists():
            continue

        try:
            with path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
        except Exception:
            continue

        grouped: dict[
            tuple[str, str, int],
            list[dict[str, str]],
        ] = defaultdict(list)

        for row in rows:
            date_value = parse_date(first(row, DATE_KEYS))
            name_value = clean_text(first(row, MEETING_KEYS))
            race_number = integer(first(row, RACE_NUMBER_KEYS))

            if (
                date_value not in TARGET_DATE_SET
                or not name_value
                or not is_victorian_meeting(name_value)
                or excluded_event(row)
            ):
                continue

            ensure_meeting(name_value, date_value, row)

            if race_number is None:
                continue

            grouped[
                (
                    date_value,
                    meeting_key(name_value),
                    race_number,
                )
            ].append(row)

        for (
            meeting_date,
            key,
            race_number,
        ), race_rows in grouped.items():
            display_name = clean_text(
                first(race_rows[0], MEETING_KEYS)
            ) or key.title()

            meeting = ensure_meeting(
                display_name,
                meeting_date,
                race_rows[0],
            )

            candidate = normalise_race(
                race_rows[0],
                display_name,
                meeting_date,
            )

            candidate["raceNumber"] = race_number
            candidate["raceKey"] = (
                f"{meeting_date}|{key}|R{race_number}"
            )

            runner_rows = [
                row
                for row in race_rows
                if looks_like_runner(row)
            ]

            if runner_rows:
                candidate["runners"] = [
                    normalise_runner(row, index)
                    for index, row in enumerate(runner_rows)
                ]

            existing_index = next(
                (
                    index
                    for index, race in enumerate(meeting["races"])
                    if race["raceNumber"] == race_number
                ),
                None,
            )

            if existing_index is None:
                meeting["races"].append(candidate)
            else:
                meeting["races"][existing_index] = merge_race_records(
                    meeting["races"][existing_index],
                    candidate,
                )


add_csv_sources()

valid_csv_identities = current_csv_meeting_identities()
if valid_csv_identities:
    meetings = {
        identity: meeting
        for identity, meeting in meetings.items()
        if identity in valid_csv_identities
    }

meeting_rows = list(meetings.values())


# ==============================================================================
# EDGEIQ_RUNNER_AUTHORITY_DEDUP_V1
#
# Multiple source representations of one race may contain the same runner.
# Publish each horse once per race and retain the representation with the
# strongest official current-field authority.
#
# No values are fabricated.
# Unique runners are never removed.
# ==============================================================================

def _edgeiq_catalog_runner_identity(runner):
    if not isinstance(runner, dict):
        return ""

    official = runner.get("official") or {}
    source = runner.get("source") or {}

    name = (
        official.get("runner")
        or source.get("horseName")
        or source.get("runnerName")
        or source.get("runner")
        or source.get("horse")
        or source.get("horse_name")
        or ""
    )

    name = str(name).strip().upper()

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        name,
    )


def _edgeiq_catalog_value_present(value):
    if value is None:
        return False

    text = str(value).strip()

    return text.lower() not in {
        "",
        "-",
        "none",
        "null",
        "undefined",
        "n/a",
        "na",
    }


def _edgeiq_catalog_runner_authority_score(runner):
    if not isinstance(runner, dict):
        return (0, 0, 0)

    official = runner.get("official") or {}

    number = (
        official.get("no")
        if _edgeiq_catalog_value_present(
            official.get("no")
        )
        else official.get("number")
    )

    critical_values = (
        number,
        official.get("barrier"),
        official.get("trainer"),
        official.get("weight"),
    )

    critical = sum(
        1
        for value in critical_values
        if _edgeiq_catalog_value_present(value)
    )

    jockey = (
        1
        if _edgeiq_catalog_value_present(
            official.get("jockey")
        )
        else 0
    )

    market = (
        1
        if _edgeiq_catalog_value_present(
            official.get("market")
        )
        else 0
    )

    return (
        critical,
        jockey,
        market,
    )


_edgeiq_catalog_duplicates_removed = 0
_edgeiq_catalog_duplicate_replacements = 0

for _meeting in meeting_rows:

    for _race in _meeting.get("races", []):

        _runners = list(
            _race.get("runners") or []
        )

        _deduped = []
        _index_by_identity = {}

        for _runner in _runners:

            _identity = (
                _edgeiq_catalog_runner_identity(
                    _runner
                )
            )

            # A genuinely unidentified row cannot safely be collapsed.
            if not _identity:
                _deduped.append(_runner)
                continue

            if _identity not in _index_by_identity:

                _index_by_identity[
                    _identity
                ] = len(_deduped)

                _deduped.append(
                    _runner
                )

                continue

            _edgeiq_catalog_duplicates_removed += 1

            _existing_index = (
                _index_by_identity[
                    _identity
                ]
            )

            _existing = (
                _deduped[
                    _existing_index
                ]
            )

            if (
                _edgeiq_catalog_runner_authority_score(
                    _runner
                )
                >
                _edgeiq_catalog_runner_authority_score(
                    _existing
                )
            ):

                _deduped[
                    _existing_index
                ] = _runner

                _edgeiq_catalog_duplicate_replacements += 1

        _race["runners"] = _deduped


print(
    "EDGEIQ_CATALOG_DUPLICATES_REMOVED="
    f"{_edgeiq_catalog_duplicates_removed}"
)

print(
    "EDGEIQ_CATALOG_DUPLICATE_AUTHORITY_REPLACEMENTS="
    f"{_edgeiq_catalog_duplicate_replacements}"
)


for meeting in meeting_rows:
    meeting["races"].sort(
        key=lambda race: race["raceNumber"]
    )

    meeting["raceCount"] = len(meeting["races"])

meeting_rows = [
    meeting
    for meeting in meeting_rows
    if meeting["date"] in TARGET_DATE_SET
    and is_victorian_meeting(meeting["meeting"])
]

meeting_rows.sort(
    key=lambda meeting: (
        meeting["date"],
        meeting["meeting"],
    )
)


# ---------------------------------------------------------------------------
# GOVERNED FINAL RUNNER RECONCILIATION
#
# CSV_SOURCES can contain overlapping representations of the same declared
# field. Source-local runner identity is useful during enrichment, but the
# final product catalogue must publish one logical runner once per race.
#
# This reconciliation is deliberately performed at the race boundary after
# all source ingestion has completed. Duplicate logical runners are merged
# with merge_runner_records() so supplemental evidence is retained.
# ---------------------------------------------------------------------------

def final_runner_identity(runner: dict[str, Any]) -> str:
    if not isinstance(runner, dict):
        return ""

    official = runner.get("official")
    if not isinstance(official, dict):
        official = {}

    source = runner.get("source")
    if not isinstance(source, dict):
        source = {}

    number = (
        official.get("no")
        or official.get("number")
        or first(source, RUNNER_NUMBER_KEYS)
    )

    name = (
        clean_text(official.get("runner"))
        or runner_name_from(source)
        or ""
    )

    normalised_name = re.sub(
        r"[^A-Z0-9]+",
        "",
        str(name).upper(),
    )

    number_text = clean_text(number) or ""

    if normalised_name and number_text:
        return f"NUMBER_NAME|{number_text}|{normalised_name}"

    if normalised_name:
        return f"NAME|{normalised_name}"

    return ""


def reconcile_final_race_runners(
    runners: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reconciled: list[dict[str, Any]] = []
    indexes: dict[str, int] = {}

    for runner in runners:
        if not isinstance(runner, dict):
            continue

        identity = final_runner_identity(runner)

        # Do not silently collapse records for which no defensible identity
        # can be established.
        if not identity:
            reconciled.append(runner)
            continue

        existing_index = indexes.get(identity)

        if existing_index is None:
            indexes[identity] = len(reconciled)
            reconciled.append(runner)
            continue

        reconciled[existing_index] = merge_runner_records(
            reconciled[existing_index],
            runner,
        )

    return reconciled


final_runner_reconciliation = {
    "before": 0,
    "after": 0,
    "removed": 0,
    "races_changed": 0,
}

for meeting in meeting_rows:
    for race in meeting.get("races", []):
        runners_before = [
            runner
            for runner in race.get("runners", [])
            if isinstance(runner, dict)
        ]

        runners_after = reconcile_final_race_runners(runners_before)

        final_runner_reconciliation["before"] += len(runners_before)
        final_runner_reconciliation["after"] += len(runners_after)

        removed = len(runners_before) - len(runners_after)

        if removed:
            final_runner_reconciliation["removed"] += removed
            final_runner_reconciliation["races_changed"] += 1

        race["runners"] = runners_after


day_labels = {
    TARGET_DATES[0].isoformat(): "TODAY",
    TARGET_DATES[1].isoformat(): "TOMORROW",
    TARGET_DATES[2].isoformat(): TARGET_DATES[2].strftime(
        "%A"
    ).upper(),
}

output = {
    "schemaVersion": "edgeiq_three_day_product_catalog_v1",
    "generatedAt": datetime.now().isoformat(),
    "dates": [
        item.isoformat()
        for item in TARGET_DATES
    ],
    "dayLabels": day_labels,
    "meetings": meeting_rows,
}

OUTPUT.write_text(
    json.dumps(
        output,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

total_races = sum(
    len(meeting["races"])
    for meeting in meeting_rows
)

total_runners = sum(
    len(race["runners"])
    for meeting in meeting_rows
    for race in meeting["races"]
)

summary_lines = [
    "EDGEIQ THREE-DAY PRODUCT CATALOGUE V1",
    "=" * 45,
    "",
    f"Generated: {output['generatedAt']}",
    f"Dates: {', '.join(output['dates'])}",
    f"Meetings: {len(meeting_rows)}",
    f"Races: {total_races}",
    f"Runners: {total_runners}",
    "",
]

for meeting in meeting_rows:
    summary_lines.append(
        f"{meeting['date']} | "
        f"{meeting['meeting']} | "
        f"{len(meeting['races'])} races | "
        f"{sum(len(race['runners']) for race in meeting['races'])} runners"
    )

SUMMARY.write_text(
    "\n".join(summary_lines),
    encoding="utf-8",
)

audit_lines = [
    "EDGEIQ THREE-DAY CATALOGUE AUDIT",
    "=" * 40,
    "",
    f"Raw race-like nodes found: {race_nodes_seen}",
    f"Raw nested runners found: {runner_nodes_seen}",
    f"Final meetings: {len(meeting_rows)}",
    f"Final races: {total_races}",
    f"Final runners: {total_runners}",
    "",
]

for meeting in meeting_rows:
    audit_lines.append(
        f"{meeting['date']} | "
        f"{meeting['meeting']} | "
        f"provider={meeting['providerMeetingKey']} | "
        f"races={len(meeting['races'])}"
    )

    for race in meeting["races"]:
        audit_lines.append(
            f"  R{race['raceNumber']} | "
            f"{race['raceName']} | "
            f"{race['distance']} | "
            f"time={race['raceTime']} | "
            f"runners={len(race['runners'])}"
        )

AUDIT.write_text(
    "\n".join(audit_lines),
    encoding="utf-8",
)

print("[EDGEIQ] Three-day catalogue rebuilt")
print(f"[EDGEIQ] Meetings: {len(meeting_rows)}")
print(f"[EDGEIQ] Races: {total_races}")
print(f"[EDGEIQ] Runners: {total_runners}")
print(f"[EDGEIQ] Raw race nodes: {race_nodes_seen}")
