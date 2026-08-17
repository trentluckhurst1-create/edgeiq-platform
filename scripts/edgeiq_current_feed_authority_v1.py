from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from edgeiq_three_day_window_v1_common import get_operational_today

csv.field_size_limit(1024 * 1024 * 128)


DATE_FIELDS = (
    "raceDate",
    "race_date",
    "meetingDate",
    "meeting_date",
    "date",
    "asOfDate",
    "operating_date",
    "operational_today",
    "today",
)

RUNNER_FIELDS = (
    "runnerName",
    "runner_name",
    "horse_name",
    "horse",
    "normalisedRunnerName",
    "normalizedRunnerName",
    "normalised_horse_name",
    "normalizedRunner",
)

RACE_FIELDS = (
    "raceKey",
    "race_key",
    "canonical_race_key",
    "raceNumber",
    "race_number",
    "race_no",
)

GENERATED_FIELDS = {
    "generatedAt",
    "generated_at",
    "built_at",
    "built_at_epr_market_v1",
    "asAt",
    "edgeiq_observed_at",
    "price_timestamp",
}

FEED_CONTRACTS: dict[str, dict[str, Any]] = {
    "edgeiq_epi_current_rating_v1": {
        "model": "MODEL_A_SINGLE_CANONICAL_SOURCE",
        "authority_format": "json",
        "critical": True,
        "date_requirement": "TODAY",
        "reason": "JSON is the governed current EPI publication; CSV is a derived/publication representation and may lag.",
    },
    "edgeiq_current_early_speed_v1": {
        "model": "MODEL_A_SINGLE_CANONICAL_SOURCE",
        "authority_format": "json",
        "critical": True,
        "date_requirement": "TODAY",
        "reason": "Form Guide consumes the JSON projection publication.",
    },
    "edgeiq_current_late_speed_v1": {
        "model": "MODEL_A_SINGLE_CANONICAL_SOURCE",
        "authority_format": "json",
        "critical": True,
        "date_requirement": "TODAY",
        "reason": "Form Guide consumes the JSON projection publication.",
    },
    "edgeiq_current_suitability_v1": {
        "model": "MODEL_A_SINGLE_CANONICAL_SOURCE",
        "authority_format": "json",
        "critical": True,
        "date_requirement": "TODAY",
        "reason": "Form Guide consumes the JSON projection publication.",
    },
    "edgeiq_current_form_momentum_v1": {
        "model": "MODEL_A_SINGLE_CANONICAL_SOURCE",
        "authority_format": "json",
        "critical": True,
        "date_requirement": "TODAY",
        "reason": "Form Guide consumes the JSON projection publication.",
    },
    "edgeiq_current_race_shape_v2": {
        "model": "MODEL_A_SINGLE_CANONICAL_SOURCE",
        "authority_format": "json",
        "critical": True,
        "date_requirement": "TODAY",
        "reason": "Form Guide consumes the JSON race-shape publication.",
    },
    "edgeiq_current_market_v1": {
        "model": "MODEL_A_SINGLE_CANONICAL_SOURCE",
        "authority_format": "csv",
        "critical": True,
        "date_requirement": "TODAY",
        "reason": "CSV is the production market input consumed by Form Guide and Market terminal builders.",
    },
    "edgeiq_form_guide_enriched_v2": {
        "model": "MODEL_A_SINGLE_CANONICAL_SOURCE",
        "authority_format": "json",
        "critical": True,
        "date_requirement": "TODAY",
        "reason": "React consumes JSON; CSV is a compact diagnostic/export representation.",
    },
}


@dataclass(frozen=True)
class FeedInspection:
    logical_feed: str
    path: Path
    format: str
    exists: bool
    embedded_date: str
    mtime: str
    rows: int
    races: int
    runners: int
    operational_today: str
    freshness_status: str
    content_hash: str
    records: tuple[dict[str, Any], ...]


def get_operational_date(override_date: date | None = None) -> date:
    return get_operational_today(override_date=override_date)[0]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple, set)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "none", "null", "nan", "n/a", "na", "-"} else text


def normalise_key(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def clean_race_number(value: Any) -> str:
    match = re.search(r"\d+", clean_text(value).upper().replace("R", ""))
    return match.group(0) if match else ""


def parse_date_text(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]):
        return text[:10]
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _json_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("runners", "records", "rows", "data"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    races = payload.get("races")
    if isinstance(races, list):
        flattened: list[dict[str, Any]] = []
        for race in races:
            if not isinstance(race, dict):
                continue
            runners = race.get("runners")
            if isinstance(runners, list):
                for runner in runners:
                    if isinstance(runner, dict):
                        row = dict(runner)
                        for field in ("raceDate", "meeting", "raceNumber", "raceKey"):
                            row.setdefault(field, race.get(field))
                        flattened.append(row)
            else:
                flattened.append(race)
        return flattened
    meetings = payload.get("meetings")
    if isinstance(meetings, list):
        flattened = []
        for meeting in meetings:
            if not isinstance(meeting, dict):
                continue
            for race in meeting.get("races", []) or []:
                if not isinstance(race, dict):
                    continue
                runners = race.get("runners")
                if isinstance(runners, list):
                    for runner in runners:
                        if isinstance(runner, dict):
                            row = dict(runner.get("official") or runner.get("source") or runner)
                            row.setdefault("raceDate", meeting.get("date"))
                            row.setdefault("meeting", meeting.get("meeting"))
                            row.setdefault("raceNumber", race.get("raceNumber"))
                            flattened.append(row)
                else:
                    flattened.append(
                        {
                            "raceDate": meeting.get("date"),
                            "meeting": meeting.get("meeting"),
                            "raceNumber": race.get("raceNumber"),
                        }
                    )
        return flattened
    return [payload]


def load_feed_records(path: Path) -> tuple[dict[str, Any] | list[Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, []
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
            return None, [dict(row) for row in csv.DictReader(handle)]
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload, _json_rows(payload)
    return None, []


def _collect_payload_dates(payload: Any) -> set[str]:
    dates: set[str] = set()
    if isinstance(payload, dict):
        for field in ("today", "tomorrow", "dayPlus2", "operational_today", "operating_date"):
            parsed = parse_date_text(payload.get(field))
            if parsed:
                dates.add(parsed)
        raw_dates = payload.get("dates")
        if isinstance(raw_dates, list):
            for item in raw_dates:
                if isinstance(item, dict):
                    parsed = parse_date_text(item.get("date"))
                else:
                    parsed = parse_date_text(item)
                if parsed:
                    dates.add(parsed)
    return dates


def collect_embedded_dates(payload: Any, records: Iterable[dict[str, Any]]) -> list[str]:
    dates = _collect_payload_dates(payload)
    for row in records:
        for field in DATE_FIELDS:
            parsed = parse_date_text(row.get(field))
            if parsed:
                dates.add(parsed)
    return sorted(dates)


def race_identity(row: dict[str, Any]) -> str:
    date_value = first_present(row, DATE_FIELDS)
    meeting = first_present(row, ("meeting", "track", "canonical_track", "canonical_meeting_name"))
    race = first_present(row, RACE_FIELDS)
    race_number = clean_race_number(race)
    if clean_text(race).count("|") >= 2 and not race_number:
        return clean_text(race).upper()
    return "|".join([parse_date_text(date_value), normalise_key(meeting), race_number])


def runner_identity(row: dict[str, Any]) -> str:
    runner = first_present(row, RUNNER_FIELDS)
    number = first_present(row, ("runnerNumber", "runner_number", "runner_no", "runner", "saddlecloth"))
    return "|".join([race_identity(row), clean_race_number(number), normalise_key(runner)])


def first_present(row: dict[str, Any], fields: Iterable[str]) -> Any:
    for field in fields:
        value = row.get(field)
        if clean_text(value):
            return value
    return ""


def normalise_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{float(value):.8g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    text = clean_text(value)
    try:
        return f"{float(text):.8g}"
    except ValueError:
        return text


def comparable_row(row: dict[str, Any]) -> dict[str, str]:
    comparable: dict[str, str] = {}
    for key, value in row.items():
        if key in GENERATED_FIELDS or key.startswith("_"):
            continue
        comparable[key] = normalise_scalar(value)
    return comparable


def content_hash(records: Iterable[dict[str, Any]]) -> str:
    payload = []
    for row in records:
        key = runner_identity(row) or race_identity(row)
        payload.append((key, comparable_row(row)))
    payload.sort(key=lambda item: item[0])
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def freshness_status(
    embedded_dates: list[str],
    operational_today: date,
    *,
    date_requirement: str = "TODAY",
) -> str:
    if date_requirement == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if not embedded_dates:
        return "DATE_NOT_PRESENT"
    today = operational_today.isoformat()
    day_plus_2 = (operational_today.replace()).toordinal() + 2
    if any(date.fromisoformat(item).toordinal() > day_plus_2 for item in embedded_dates):
        return "FUTURE_DATE_INVALID"
    if date_requirement == "WINDOW":
        required = {
            operational_today.toordinal(),
            operational_today.toordinal() + 1,
            operational_today.toordinal() + 2,
        }
        observed = {date.fromisoformat(item).toordinal() for item in embedded_dates}
        return "CURRENT" if required.issubset(observed) else "STALE"
    return "CURRENT" if today in embedded_dates else "STALE"


def inspect_feed_freshness(
    path: Path | str,
    logical_feed: str,
    *,
    operational_today: date | None = None,
    date_requirement: str | None = None,
) -> FeedInspection:
    physical_path = Path(path)
    today = operational_today or get_operational_date()
    contract = FEED_CONTRACTS.get(logical_feed, {})
    requirement = date_requirement or contract.get("date_requirement") or "TODAY"
    payload, records = load_feed_records(physical_path)
    embedded_dates = collect_embedded_dates(payload, records)
    races = {race_identity(row) for row in records if race_identity(row).strip("|")}
    runners = {runner_identity(row) for row in records if runner_identity(row).strip("|")}
    if physical_path.exists():
        mtime = datetime.fromtimestamp(physical_path.stat().st_mtime, timezone.utc).isoformat()
    else:
        mtime = ""
    return FeedInspection(
        logical_feed=logical_feed,
        path=physical_path,
        format=physical_path.suffix.lower().lstrip("."),
        exists=physical_path.exists(),
        embedded_date="|".join(embedded_dates),
        mtime=mtime,
        rows=len(records),
        races=len(races),
        runners=len(runners),
        operational_today=today.isoformat(),
        freshness_status=freshness_status(embedded_dates, today, date_requirement=requirement),
        content_hash=content_hash(records) if records else "",
        records=tuple(records),
    )


def equivalence_status(inspections: Iterable[FeedInspection]) -> str:
    present = [item for item in inspections if item.exists]
    if len(present) <= 1:
        return "SINGLE_REPRESENTATION"
    current = [item for item in present if item.freshness_status == "CURRENT"]
    if len(current) <= 1:
        return "NOT_COMPARABLE"
    comparable_hashes = {item.content_hash for item in current if item.content_hash}
    return "EQUIVALENT" if len(comparable_hashes) == 1 else "DIVERGENT"


def assert_equivalent_current_representations(
    inspections: Iterable[FeedInspection],
    logical_feed: str,
) -> None:
    status = equivalence_status(inspections)
    if status == "DIVERGENT":
        raise RuntimeError(f"DIVERGENT_CURRENT_REPRESENTATIONS: {logical_feed}")


def choose_current_feed_authority(
    candidates: Iterable[Path | str],
    logical_feed: str,
    *,
    operational_today: date | None = None,
    critical: bool | None = None,
    date_requirement: str | None = None,
) -> tuple[Path, FeedInspection, list[FeedInspection], str]:
    inspections = [
        inspect_feed_freshness(
            Path(candidate),
            logical_feed,
            operational_today=operational_today,
            date_requirement=date_requirement,
        )
        for candidate in candidates
    ]
    present = [item for item in inspections if item.exists and item.rows > 0]
    if not present:
        raise FileNotFoundError(f"NO_FEED_REPRESENTATION_FOUND: {logical_feed}")

    contract = FEED_CONTRACTS.get(logical_feed, {})
    is_critical = bool(contract.get("critical")) if critical is None else critical
    current = [item for item in present if item.freshness_status == "CURRENT"]
    if not current:
        if is_critical:
            statuses = ", ".join(f"{item.path.name}:{item.freshness_status}" for item in present)
            raise RuntimeError(f"NO_CURRENT_FEED_REPRESENTATION: {logical_feed}: {statuses}")
        current = present

    authority_format = clean_text(contract.get("authority_format")).lower()
    if authority_format:
        selected = next((item for item in current if item.format == authority_format), None)
        if selected is None and is_critical:
            statuses = ", ".join(f"{item.path.name}:{item.freshness_status}" for item in present)
            raise RuntimeError(f"GOVERNED_AUTHORITY_NOT_CURRENT: {logical_feed}: {statuses}")
        if selected is not None:
            return selected.path, selected, inspections, clean_text(contract.get("reason"))

    if is_critical:
        assert_equivalent_current_representations(inspections, logical_feed)

    dated_current = [item for item in current if item.embedded_date]
    pool = dated_current or current
    pool.sort(key=lambda item: (item.mtime, item.path.name), reverse=True)
    selected = pool[0]
    reason = "Freshest current dated representation selected by governed authority utility."
    return selected.path, selected, inspections, reason


def assert_current_feed(
    path: Path | str,
    logical_feed: str,
    *,
    operational_today: date | None = None,
    date_requirement: str | None = None,
) -> FeedInspection:
    inspection = inspect_feed_freshness(
        Path(path),
        logical_feed,
        operational_today=operational_today,
        date_requirement=date_requirement,
    )
    if inspection.freshness_status != "CURRENT":
        raise RuntimeError(
            f"FEED_NOT_CURRENT: {logical_feed}: {inspection.path.name}: {inspection.freshness_status}"
        )
    return inspection
