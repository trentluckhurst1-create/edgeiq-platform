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
MARKET_FEED = DATA / "edgeiq_market_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_insights_terminal_feed_v1.csv"
SUMMARY = DATA / "edgeiq_insights_terminal_feed_summary_v1.csv"
TRACE = DATA / "edgeiq_insights_engineering_build_v1_trace.txt"

FIELDNAMES = [
    "workspace_id",
    "meeting_key",
    "race_key",
    "generated_at",
    "race_date",
    "track",
    "race_no",
    "row_kind",
    "card_type",
    "card_title",
    "card_value",
    "card_detail",
    "no",
    "horse",
    "key_insight",
    "edge",
    "confidence",
    "source",
    "source_timestamp",
    "source_confidence",
    "coverage",
    "supporting_evidence",
    "row_status",
]

CARD_TYPES = [
    "KEY INSIGHT",
    "BEST RATED RUNNER",
    "VALUE INSIGHT",
    "MARKET RISER",
    "RACE SETUP",
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


def market_index() -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = {}
    for row in read_csv_rows(MARKET_FEED):
        race_key = clean(row.get("race_key"))
        if race_key:
            index.setdefault(race_key, []).append(row)
    return index


def runner_no(runner: dict[str, Any], fallback: int) -> str:
    return number_text(runner.get("runnerNumber")) or str(fallback)


def runner_name(runner: dict[str, Any]) -> str:
    return clean(runner.get("runnerName"))


def source_time(runner: dict[str, Any]) -> str:
    for key in ["suitability", "formMomentum", "epi", "earlySpeed", "lateSpeed", "raceShape"]:
        value = runner.get(key)
        if isinstance(value, dict) and clean(value.get("asAt")):
            return clean(value.get("asAt"))
    return ""


def confidence_from_runner(runner: dict[str, Any]) -> str:
    coverages = []
    for key in ["suitability", "formMomentum", "earlySpeed", "lateSpeed"]:
        value = runner.get(key)
        if isinstance(value, dict):
            try:
                coverages.append(float(value.get("evidenceCoverage")))
            except (TypeError, ValueError):
                pass
    if not coverages:
        return ""
    return f"{sum(coverages) / len(coverages):.0f}% evidence"


def runner_source(runner: dict[str, Any]) -> str:
    sources = []
    for key in ["suitability", "formMomentum", "earlySpeed", "lateSpeed", "epi", "raceShape"]:
        value = runner.get(key)
        if isinstance(value, dict) and clean(value.get("source")):
            sources.append(clean(value.get("source")))
    return " | ".join(dict.fromkeys(sources))


def first_public_reason(runner: dict[str, Any]) -> str:
    for key in ["suitability", "formMomentum", "raceShape", "earlySpeed", "lateSpeed"]:
        value = runner.get(key)
        if isinstance(value, dict):
            reasons = value.get("publicReasons")
            if isinstance(reasons, list):
                for reason in reasons:
                    if clean(reason):
                        return clean(reason)
    return ""


def runner_edge(runner: dict[str, Any]) -> str:
    shape = runner.get("raceShape") if isinstance(runner.get("raceShape"), dict) else {}
    momentum = runner.get("formMomentum") if isinstance(runner.get("formMomentum"), dict) else {}
    suitability = runner.get("suitability") if isinstance(runner.get("suitability"), dict) else {}
    shape_band = clean(shape.get("band")).replace("_", " ").title()
    if clean(shape.get("band")).upper() == "AVOID_PRESSURE":
        shape_band = "Pressure Sensitive"
    parts = [
        f"Race shape {shape_band}" if shape_band else "",
        f"Suitability {metric_text(suitability.get('value'))}" if metric_text(suitability.get("value")) else "",
        f"Momentum {metric_text(momentum.get('value'))}" if metric_text(momentum.get("value")) else "",
    ]
    return "; ".join(part for part in parts if part)


def best_metric(summary: dict[str, Any], key: str) -> dict[str, Any]:
    values = summary.get(key)
    if isinstance(values, list) and values and isinstance(values[0], dict):
        return values[0]
    return {}


def card_row(
    meeting: dict[str, Any],
    race: dict[str, Any],
    generated_at: str,
    card_type: str,
    value: str,
    detail: str,
    source: str,
    status: str,
) -> dict[str, str]:
    return {
        "workspace_id": "BETA-012",
        "meeting_key": clean(meeting.get("meetingKey")),
        "race_key": clean(race.get("raceKey")),
        "generated_at": generated_at,
        "race_date": clean(meeting.get("date")),
        "track": clean(meeting.get("meeting")),
        "race_no": number_text(race.get("raceNumber")),
        "row_kind": "card",
        "card_type": card_type,
        "card_title": card_type,
        "card_value": value,
        "card_detail": detail,
        "no": "",
        "horse": "",
        "key_insight": "",
        "edge": "",
        "confidence": "Evidence quality" if value else "",
        "source": source,
        "source_timestamp": generated_at,
        "source_confidence": "governed" if value else "unavailable",
        "coverage": "",
        "supporting_evidence": detail,
        "row_status": status,
    }


def runner_row(
    meeting: dict[str, Any],
    race: dict[str, Any],
    generated_at: str,
    runner: dict[str, Any],
    fallback: int,
) -> dict[str, str]:
    insight = first_public_reason(runner)
    edge = runner_edge(runner)
    return {
        "workspace_id": "BETA-012",
        "meeting_key": clean(meeting.get("meetingKey")),
        "race_key": clean(race.get("raceKey")),
        "generated_at": generated_at,
        "race_date": clean(meeting.get("date")),
        "track": clean(meeting.get("meeting")),
        "race_no": number_text(race.get("raceNumber")),
        "row_kind": "runner",
        "card_type": "",
        "card_title": "",
        "card_value": "",
        "card_detail": "",
        "no": runner_no(runner, fallback),
        "horse": runner_name(runner),
        "key_insight": insight,
        "edge": edge,
        "confidence": confidence_from_runner(runner),
        "source": runner_source(runner),
        "source_timestamp": source_time(runner) or generated_at,
        "source_confidence": "governed" if insight or edge else "unavailable",
        "coverage": confidence_from_runner(runner),
        "supporting_evidence": " | ".join(
            part for part in [
                metric_text(runner.get("epi")),
                metric_text(runner.get("earlySpeed")),
                metric_text(runner.get("lateSpeed")),
                metric_text(runner.get("suitability")),
                metric_text(runner.get("formMomentum")),
            ] if part
        ),
        "row_status": "current" if insight or edge else "pending_insight",
    }


def build_cards(meeting: dict[str, Any], race: dict[str, Any], generated_at: str, intelligence: dict[str, Any] | None, market_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not intelligence:
        return [
            card_row(meeting, race, generated_at, card, "", "", "edgeiq_current_race_intelligence_v1.json", "pending_insight")
            for card in CARD_TYPES
        ]
    summary = intelligence.get("fieldSummary") if isinstance(intelligence.get("fieldSummary"), dict) else {}
    statements = intelligence.get("overview", {}).get("statements", []) if isinstance(intelligence.get("overview"), dict) else []
    key_statement = clean(statements[0].get("statement")) if statements and isinstance(statements[0], dict) else ""
    top_epi = best_metric(summary, "topEpi")
    top_value = f"{clean(top_epi.get('runnerName'))} {metric_text(top_epi.get('value'))}".strip()
    value_runner = ""
    for row in market_rows:
        if clean(row.get("edge")).startswith("+"):
            value_runner = f"{clean(row.get('horse'))} {clean(row.get('edge'))}".strip()
            break
    market_riser = ""
    for row in market_rows:
        move = clean(row.get("move"))
        if move.startswith("-"):
            market_riser = f"{clean(row.get('horse'))} {move}".strip()
            break
    race_setup = ""
    for statement in statements:
        text = clean(statement.get("statement") if isinstance(statement, dict) else statement)
        if "Projected map evidence" in text:
            race_setup = text
            break
    return [
        card_row(meeting, race, generated_at, "KEY INSIGHT", key_statement, key_statement, "edgeiq_current_race_intelligence_v1.json", "current" if key_statement else "pending_insight"),
        card_row(meeting, race, generated_at, "BEST RATED RUNNER", top_value, clean(top_epi.get("source")), "edgeiq_current_race_intelligence_v1.json", "current" if top_value else "pending_insight"),
        card_row(meeting, race, generated_at, "VALUE INSIGHT", value_runner, "Governed market versus EDGEiQ price context", "edgeiq_market_terminal_feed_v1.csv", "current" if value_runner else "pending_market"),
        card_row(meeting, race, generated_at, "MARKET RISER", market_riser, "Governed market movement context", "edgeiq_market_terminal_feed_v1.csv", "current" if market_riser else "pending_market"),
        card_row(meeting, race, generated_at, "RACE SETUP", race_setup, race_setup, "edgeiq_current_race_intelligence_v1.json", "current" if race_setup else "pending_insight"),
    ]


def main() -> None:
    if not CATALOG.exists():
        raise FileNotFoundError(CATALOG)
    catalog = read_json(CATALOG)
    intelligence_index = build_intelligence_index()
    markets = market_index()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    output_rows: list[dict[str, str]] = []
    races = 0
    matched_intelligence = 0
    runner_rows = 0

    for meeting in catalog.get("meetings", []) if isinstance(catalog, dict) else []:
        if not isinstance(meeting, dict):
            continue
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict):
                continue
            races += 1
            race_key = clean(race.get("raceKey"))
            intelligence = intelligence_index.get(race_match_key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber")))
            matched_intelligence += 1 if intelligence else 0
            output_rows.extend(build_cards(meeting, race, generated_at, intelligence, markets.get(race_key, [])))
            runners = intelligence.get("runners", []) if isinstance(intelligence, dict) else []
            if not runners:
                runners = [{"runnerNumber": index + 1, "runnerName": clean((runner.get("official") or {}).get("runner")) or clean((runner.get("source") or {}).get("horseName"))} for index, runner in enumerate(race.get("runners", []) or []) if isinstance(runner, dict)]
            for index, runner in enumerate(runners):
                if isinstance(runner, dict):
                    output_rows.append(runner_row(meeting, race, generated_at, runner, index + 1))
                    runner_rows += 1

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
                {"metric": "runner_rows", "value": runner_rows},
                {"metric": "matched_intelligence_races", "value": matched_intelligence},
                {"metric": "frontend_limit", "value": 10000},
                {"metric": "status", "value": "PASS" if len(output_rows) <= 10000 else "WARN_OVER_LIMIT"},
            ]
        )

    TRACE.write_text(
        "\n".join(
            [
                "EDGEIQ_INSIGHTS_TERMINAL_FEED_V1",
                f"generated_at={generated_at}",
                f"rows={len(output_rows)}",
                f"races={races}",
                f"runner_rows={runner_rows}",
                f"matched_intelligence_races={matched_intelligence}",
                f"source_catalog={CATALOG.name}",
                f"source_current_intelligence={CURRENT_INTELLIGENCE.name if CURRENT_INTELLIGENCE.exists() else 'missing'}",
                f"source_market={MARKET_FEED.name if MARKET_FEED.exists() else 'missing'}",
            ]
        ),
        encoding="utf-8",
    )

    if len(output_rows) > 10000:
        raise RuntimeError(f"edgeiq_insights_terminal_feed_v1 exceeds frontend limit: {len(output_rows)}")
    print(f"EDGEIQ_INSIGHTS_TERMINAL_FEED_V1 rows={len(output_rows)} races={races} runner_rows={runner_rows} matched_intelligence={matched_intelligence}")


if __name__ == "__main__":
    main()
