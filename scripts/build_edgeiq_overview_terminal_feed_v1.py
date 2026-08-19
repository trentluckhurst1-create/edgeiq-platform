from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
CURRENT_INTELLIGENCE = DATA / "edgeiq_current_race_intelligence_v1.json"
MAP_FEED = DATA / "edgeiq_map_terminal_feed_v1.csv"
MARKET_FEED = DATA / "edgeiq_market_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_overview_terminal_feed_v1.csv"
SUMMARY = DATA / "edgeiq_overview_terminal_feed_summary_v1.csv"
TRACE = DATA / "edgeiq_overview_engineering_build_v1_trace.txt"

FIELDNAMES = [
    "workspace_id",
    "meeting_key",
    "race_key",
    "generated_at",
    "race_date",
    "track",
    "race_no",
    "section",
    "evidence",
    "source",
    "status",
    "open",
    "source_timestamp",
    "source_confidence",
    "row_status",
]

LOCKED_SECTIONS = [
    "Race Environment",
    "MAP / Race Shape",
    "Field Intelligence",
    "EDGEiQ Race Read",
    "Key Race Questions",
    "Operational / Data State",
]


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
        return "".join(ch for ch in text if ch.isdigit()) or text
    if number.is_integer():
        return str(int(number))
    return str(number)


def metric_text(value: Any, places: int = 1) -> str:
    if isinstance(value, dict):
        value = value.get("value") or value.get("top") or value.get("average")
    text = clean(value)
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return f"{number:.{places}f}"


def race_match_key(date: Any, track: Any, race_no: Any) -> tuple[str, str, str]:
    return (clean(date), normalise(track), number_text(race_no))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def build_intelligence_index() -> dict[tuple[str, str, str], dict[str, Any]]:
    payload = read_json(CURRENT_INTELLIGENCE)
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for race in payload.get("races", []) if isinstance(payload, dict) else []:
        if not isinstance(race, dict):
            continue
        key = race_match_key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber"))
        if all(key):
            index[key] = race
    return index


def csv_count_by_race(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        race_key = clean(row.get("race_key"))
        if race_key:
            counts[race_key] = counts.get(race_key, 0) + 1
    return counts


def first_leader(items: Any, label: str) -> str:
    if not isinstance(items, list) or not items:
        return ""
    first = items[0] if isinstance(items[0], dict) else {}
    runner = clean(first.get("runnerName"))
    value = metric_text(first.get("value"))
    if runner and value:
        return f"{label}: {runner} {value}"
    if runner:
        return f"{label}: {runner}"
    return ""


def race_environment(race: dict[str, Any], meeting: dict[str, Any]) -> tuple[str, str, str]:
    fields = [
        clean(meeting.get("meeting")),
        f"R{number_text(race.get('raceNumber'))}" if number_text(race.get("raceNumber")) else "",
        clean(race.get("distance")),
        clean(race.get("raceClass")),
        clean(race.get("trackCondition")) or clean(meeting.get("trackCondition")),
        f"Rail {clean(race.get('rail') or meeting.get('rail'))}" if clean(race.get("rail") or meeting.get("rail")) else "",
    ]
    evidence = " | ".join(part for part in fields if part)
    return evidence, "THREE_DAY_PRODUCT_CATALOG_V1", "Available" if evidence else "Pending"


def map_shape(race: dict[str, Any], intelligence: dict[str, Any] | None, map_rows: int) -> tuple[str, str, str]:
    if intelligence:
        tempo = clean(intelligence.get("tempo"))
        pressure = clean(intelligence.get("pressure"))
        projected = ""
        for statement in intelligence.get("overview", {}).get("statements", []) or []:
            text = clean(statement.get("statement") if isinstance(statement, dict) else statement)
            if "Projected map evidence" in text:
                projected = text
                break
        parts = [
            f"Tempo {tempo}" if tempo else "",
            f"Pressure {pressure}" if pressure else "",
            projected,
            f"Map rows {map_rows}" if map_rows else "",
        ]
        evidence = "; ".join(part for part in parts if part)
        if evidence:
            return evidence, "edgeiq_current_race_intelligence_v1.json | edgeiq_map_terminal_feed_v1.csv", "Available"
    if map_rows:
        return f"Map feed rows {map_rows}; race-shape summary pending", "edgeiq_map_terminal_feed_v1.csv", "Partial"
    return "", "edgeiq_map_terminal_feed_v1.csv", "Pending"


def field_intelligence(intelligence: dict[str, Any] | None) -> tuple[str, str, str]:
    if not intelligence:
        return "", "edgeiq_current_race_intelligence_v1.json", "Pending"
    summary = intelligence.get("fieldSummary") if isinstance(intelligence.get("fieldSummary"), dict) else {}
    epi = summary.get("epi") if isinstance(summary.get("epi"), dict) else {}
    parts = [
        first_leader(summary.get("topEpi"), "Top EPI"),
        f"Average EPI {metric_text(epi.get('average'))}" if metric_text(epi.get("average")) else "",
        first_leader(summary.get("topEarlySpeed"), "Early Speed"),
        first_leader(summary.get("topLateSpeed"), "Late Speed"),
        first_leader(summary.get("topSuitability"), "Suitability"),
        first_leader(summary.get("topFormMomentum"), "Form Momentum"),
    ]
    evidence = "; ".join(part for part in parts if part)
    return evidence, "edgeiq_current_race_intelligence_v1.json", "Available" if evidence else "Pending"


def overview_items(intelligence: dict[str, Any] | None, key: str, limit: int = 3) -> tuple[str, str, str]:
    if not intelligence:
        return "", "edgeiq_current_race_intelligence_v1.json", "Pending"
    items = intelligence.get("overview", {}).get(key, []) if isinstance(intelligence.get("overview"), dict) else []
    field_name = "statement" if key == "statements" else "question"
    values = [
        clean(item.get(field_name) if isinstance(item, dict) else item)
        for item in items[:limit]
    ]
    evidence = " ".join(value for value in values if value)
    return evidence, "edgeiq_current_race_intelligence_v1.json", "Available" if evidence else "Pending"


def operational_state(race: dict[str, Any], map_rows: int, market_rows: int) -> tuple[str, str, str]:
    runner_count = len(race.get("runners", []) or [])
    parts = [
        f"Runners {runner_count}" if runner_count else "",
        f"Map rows {map_rows}" if map_rows else "Map feed pending",
        f"Market rows {market_rows}" if market_rows else "Market feed pending",
    ]
    evidence = "; ".join(part for part in parts if part)
    status = "Available" if runner_count and (map_rows or market_rows) else "Partial" if runner_count else "Pending"
    return evidence, "terminal feeds", status


def row(
    meeting: dict[str, Any],
    race: dict[str, Any],
    generated_at: str,
    section: str,
    evidence: str,
    source: str,
    status: str,
    open_target: str,
) -> dict[str, str]:
    return {
        "workspace_id": "BETA-011",
        "meeting_key": clean(meeting.get("meetingKey")),
        "race_key": clean(race.get("raceKey")),
        "generated_at": generated_at,
        "race_date": clean(meeting.get("date")),
        "track": clean(meeting.get("meeting")),
        "race_no": number_text(race.get("raceNumber")),
        "section": section,
        "evidence": evidence,
        "source": source,
        "status": status,
        "open": open_target,
        "source_timestamp": generated_at,
        "source_confidence": "governed" if evidence else "unavailable",
        "row_status": "current" if evidence else "pending_evidence",
    }


def main() -> None:
    if not CATALOG.exists():
        raise FileNotFoundError(CATALOG)

    catalog = read_json(CATALOG)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    intelligence_index = build_intelligence_index()
    map_counts = csv_count_by_race(read_csv_rows(MAP_FEED))
    market_counts = csv_count_by_race(read_csv_rows(MARKET_FEED))

    output_rows: list[dict[str, str]] = []
    races = 0
    matched_intelligence = 0

    for meeting in catalog.get("meetings", []) if isinstance(catalog, dict) else []:
        if not isinstance(meeting, dict):
            continue
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict):
                continue
            races += 1
            selected_race_key = clean(race.get("raceKey"))
            intelligence = intelligence_index.get(race_match_key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber")))
            matched_intelligence += 1 if intelligence else 0
            map_rows = map_counts.get(selected_race_key, 0)
            market_rows = market_counts.get(selected_race_key, 0)

            evidence, source, status = race_environment(race, meeting)
            output_rows.append(row(meeting, race, generated_at, "Race Environment", evidence, source, status, "FORM"))

            evidence, source, status = map_shape(race, intelligence, map_rows)
            output_rows.append(row(meeting, race, generated_at, "MAP / Race Shape", evidence, source, status, "MAP"))

            evidence, source, status = field_intelligence(intelligence)
            output_rows.append(row(meeting, race, generated_at, "Field Intelligence", evidence, source, status, "FORM"))

            evidence, source, status = overview_items(intelligence, "statements")
            output_rows.append(row(meeting, race, generated_at, "EDGEiQ Race Read", evidence, source, status, "OVERVIEW"))

            evidence, source, status = overview_items(intelligence, "questions")
            output_rows.append(row(meeting, race, generated_at, "Key Race Questions", evidence, source, status, "OVERVIEW"))

            evidence, source, status = operational_state(race, map_rows, market_rows)
            output_rows.append(row(meeting, race, generated_at, "Operational / Data State", evidence, source, status, "MARKET"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(output_rows)

    with SUMMARY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(
            [
                {"metric": "rows", "value": len(output_rows)},
                {"metric": "races", "value": races},
                {"metric": "matched_intelligence_races", "value": matched_intelligence},
                {"metric": "frontend_limit", "value": 10000},
                {"metric": "status", "value": "PASS" if len(output_rows) <= 10000 else "WARN_OVER_LIMIT"},
            ]
        )

    TRACE.write_text(
        "\n".join(
            [
                "EDGEIQ_OVERVIEW_TERMINAL_FEED_V1",
                f"generated_at={generated_at}",
                f"rows={len(output_rows)}",
                f"races={races}",
                f"matched_intelligence_races={matched_intelligence}",
                f"source_catalog={CATALOG.name}",
                f"source_current_intelligence={CURRENT_INTELLIGENCE.name if CURRENT_INTELLIGENCE.exists() else 'missing'}",
                f"source_map={MAP_FEED.name if MAP_FEED.exists() else 'missing'}",
                f"source_market={MARKET_FEED.name if MARKET_FEED.exists() else 'missing'}",
            ]
        ),
        encoding="utf-8",
    )

    if len(output_rows) > 10000:
        raise RuntimeError(f"edgeiq_overview_terminal_feed_v1 exceeds frontend limit: {len(output_rows)}")
    print(
        "EDGEIQ_OVERVIEW_TERMINAL_FEED_V1 "
        f"rows={len(output_rows)} races={races} matched_intelligence={matched_intelligence}"
    )


if __name__ == "__main__":
    main()
