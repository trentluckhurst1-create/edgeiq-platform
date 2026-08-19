from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from edgeiq_beta_intelligence_v1_common import (
    DATA,
    clean,
    identity,
    load_current_projection,
    normalise_date,
    now_utc,
    race_identity,
    race_no,
    to_float,
    write_csv,
    write_json,
)


ENRICHED = DATA / "edgeiq_form_guide_enriched_v2.json"
WEATHER = DATA / "edgeiq_race_weather_v1.json"
MAP = DATA / "edgeiq_current_map_v1.json"
OUT = DATA / "edgeiq_current_race_intelligence_v1.json"
OVERVIEW_AUDIT = DATA / "edgeiq_overview_v1_evidence_audit.csv"


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def metric_value(source_value: Any) -> Any:
    if isinstance(source_value, dict):
        return source_value.get("value")
    return source_value


def is_populated(value: Any) -> bool:
    return value not in (None, "", "-", "N/A")


def runner_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return identity(row.get("raceDate"), row.get("meeting"), row.get("raceNumber"), row.get("runnerName"))


def race_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return race_identity(row.get("raceDate"), row.get("meeting"), row.get("raceNumber"))


def weather_index() -> dict[tuple[str, str], dict[str, Any]]:
    payload = read_json(WEATHER)
    records = payload.get("records", []) if isinstance(payload, dict) else []
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in records:
        if isinstance(row, dict):
            out[(normalise_date(row.get("raceDate")), clean(row.get("meeting")).upper())] = row
    return out


def map_index() -> dict[tuple[str, str, str, str], dict[str, Any]]:
    payload = read_json(MAP)
    rows = payload.get("runners", []) if isinstance(payload, dict) else []
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            out[runner_key(row)] = row
    return out


def top_runners(rows: list[dict[str, Any]], field: str, limit: int = 3) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        value = to_float(metric_value(row.get(field)))
        if value is not None:
            ranked.append((value, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "runnerNumber": row.get("runnerNumber"),
            "runnerName": row.get("runnerName"),
            "value": round(value, 2),
            "source": (row.get(field) or {}).get("source") if isinstance(row.get(field), dict) else None,
        }
        for value, row in ranked[:limit]
    ]


def market_vs_price(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        market = to_float(row.get("marketPrice"))
        edgeiq = to_float(metric_value(row.get("edgeiqPrice")))
        if market is None or edgeiq is None or market <= 0 or edgeiq <= 0:
            continue
        diff_pct = round(((market - edgeiq) / edgeiq) * 100, 1)
        out.append({
            "runnerNumber": row.get("runnerNumber"),
            "runnerName": row.get("runnerName"),
            "market": market,
            "edgeiqPrice": edgeiq,
            "edgePct": diff_pct,
        })
    out.sort(key=lambda item: item["edgePct"], reverse=True)
    return out[:5]


def race_stat(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [to_float(metric_value(row.get(field))) for row in rows]
    values = [value for value in values if value is not None]
    return {
        "count": len(values),
        "average": round(sum(values) / len(values), 2) if values else None,
        "top": round(max(values), 2) if values else None,
    }


def deterministic_overview(race: dict[str, Any], rows: list[dict[str, Any]], weather: dict[str, Any] | None, map_rows: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    statements: list[dict[str, str]] = []
    questions: list[dict[str, str]] = []

    early = top_runners(rows, "earlySpeed", 1)
    late = top_runners(rows, "lateSpeed", 1)
    suitability = top_runners(rows, "suitability", 1)
    momentum = top_runners(rows, "formMomentum", 1)
    map_counts = Counter(clean(row.get("projectedZone")).upper() or "UNRESOLVED" for row in map_rows)
    coverage_values = [to_float(row.get("evidenceCoverage")) for row in map_rows]
    coverage_values = [value for value in coverage_values if value is not None]
    map_coverage = round(sum(coverage_values) / len(coverage_values), 1) if coverage_values else None

    if early:
        statements.append({"statement": f"{early[0]['runnerName']} owns the strongest current Early Speed.", "source": "edgeiq_current_early_speed_v1"})
        questions.append({"question": "Can the strongest early-speed runner use that advantage without overworking?", "source": "edgeiq_current_early_speed_v1"})
    if late:
        statements.append({"statement": f"{late[0]['runnerName']} owns the strongest current Late Speed.", "source": "edgeiq_current_late_speed_v1"})
        questions.append({"question": "If tempo is genuine, does the strongest late-speed profile become more relevant late?", "source": "edgeiq_current_late_speed_v1"})
    if suitability:
        statements.append({"statement": f"{suitability[0]['runnerName']} ranks highest on Suitability for today's setup.", "source": "edgeiq_current_suitability_v1"})
        questions.append({"question": "Does the top Suitability profile line up with the current market?", "source": "edgeiq_current_suitability_v1"})
    if momentum:
        statements.append({"statement": f"{momentum[0]['runnerName']} shows the strongest Form Momentum among populated runners.", "source": "edgeiq_current_form_momentum_v1"})
    if map_counts:
        statements.append({"statement": f"Projected map evidence: {map_counts.get('LEAD', 0)} lead, {map_counts.get('ON PACE', 0)} on pace, {map_counts.get('MIDFIELD', 0)} midfield, {map_counts.get('BACK', 0)} back, {map_counts.get('UNRESOLVED', 0)} unresolved.", "source": "edgeiq_current_map_v1"})
    if map_coverage is not None:
        statements.append({"statement": f"Map evidence coverage averages {map_coverage:.1f}% for this race.", "source": "edgeiq_current_map_v1"})
    if weather and not weather.get("stale") and clean(weather.get("windDirection")):
        statements.append({"statement": f"Weather context is available: wind {clean(weather.get('windDirection'))} {weather.get('windSpeedKmh') or ''} km/h.", "source": "edgeiq_race_weather_v1"})
    elif weather and weather.get("gapReason"):
        statements.append({"statement": f"Weather evidence is incomplete for this meeting: {weather.get('gapReason')}.", "source": "edgeiq_race_weather_v1"})

    if map_counts.get("UNRESOLVED", 0):
        questions.append({"question": "How much confidence should be placed in the map while some runners remain unresolved?", "source": "edgeiq_current_map_v1"})
    if market_vs_price(rows):
        questions.append({"question": "Which current market prices differ most from EDGEiQ assessed price?", "source": "edgeiq_form_guide_enriched_v2"})

    return statements[:5], questions[:5]


def main() -> None:
    enriched = read_json(ENRICHED)
    races = enriched.get("races", []) if isinstance(enriched, dict) else []
    weather_by_meeting = weather_index()
    map_by_runner = map_index()
    generated_at = now_utc()
    out_races: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for race in races:
        race_rows = race.get("runners", []) if isinstance(race, dict) else []
        race_id = race_identity(race.get("raceDate"), race.get("meeting"), race.get("raceNumber"))
        weather = weather_by_meeting.get((normalise_date(race.get("raceDate")), clean(race.get("meeting")).upper()))
        enriched_map_rows = []
        out_runners = []
        for runner in race_rows:
            key = runner_key(runner)
            map_row = map_by_runner.get(key, {})
            enriched_map_rows.append(map_row)
            out_runners.append({
                "runnerId": runner.get("runnerId"),
                "runnerNumber": runner.get("runnerNumber"),
                "runnerName": runner.get("runnerName"),
                "scratched": runner.get("scratched"),
                "barrier": map_row.get("barrier"),
                "market": runner.get("marketPrice"),
                "edgeiqPrice": runner.get("edgeiqPrice"),
                "epi": runner.get("epi"),
                "earlySpeed": runner.get("earlySpeed"),
                "lateSpeed": runner.get("lateSpeed"),
                "raceShape": runner.get("raceShape"),
                "suitability": runner.get("suitability"),
                "formMomentum": runner.get("formMomentum"),
                "projectedMapZone": map_row.get("projectedZone") or "UNRESOLVED",
                "publicReasons": {
                    "suitability": runner.get("suitability", {}).get("publicReasons", []) if isinstance(runner.get("suitability"), dict) else [],
                    "formMomentum": runner.get("formMomentum", {}).get("publicReasons", []) if isinstance(runner.get("formMomentum"), dict) else [],
                },
            })

        statements, questions = deterministic_overview(race, race_rows, weather, enriched_map_rows)
        for item in statements:
            audit_rows.append({
                "race_date": race.get("raceDate"),
                "meeting": race.get("meeting"),
                "race_number": race.get("raceNumber"),
                "item_type": "STATEMENT",
                "text": item["statement"],
                "source": item["source"],
                "deterministic_rule": "top_metric_or_coverage_statement",
                "tipping_language": "NO",
            })
        for item in questions:
            audit_rows.append({
                "race_date": race.get("raceDate"),
                "meeting": race.get("meeting"),
                "race_number": race.get("raceNumber"),
                "item_type": "QUESTION",
                "text": item["question"],
                "source": item["source"],
                "deterministic_rule": "evidence_presence_question",
                "tipping_language": "NO",
            })

        out_races.append({
            "raceDate": race.get("raceDate"),
            "meeting": race.get("meeting"),
            "raceNumber": race.get("raceNumber"),
            "raceKey": "|".join(race_id),
            "raceName": race.get("raceName"),
            "distance": race.get("distance"),
            "class": race.get("class") or race.get("raceClass"),
            "trackCondition": race.get("trackCondition"),
            "rail": race.get("rail"),
            "weather": weather,
            "tempo": race.get("tempo"),
            "pressure": race.get("pressure"),
            "mapCoverage": race_stat(enriched_map_rows, "evidenceCoverage"),
            "fieldSummary": {
                "epi": race_stat(race_rows, "epi"),
                "earlySpeed": race_stat(race_rows, "earlySpeed"),
                "lateSpeed": race_stat(race_rows, "lateSpeed"),
                "suitability": race_stat(race_rows, "suitability"),
                "formMomentum": race_stat(race_rows, "formMomentum"),
                "marketVsEdgeiqPrice": market_vs_price(race_rows),
                "topEpi": top_runners(race_rows, "epi"),
                "topEarlySpeed": top_runners(race_rows, "earlySpeed"),
                "topLateSpeed": top_runners(race_rows, "lateSpeed"),
                "topSuitability": top_runners(race_rows, "suitability"),
                "topFormMomentum": top_runners(race_rows, "formMomentum"),
            },
            "overview": {
                "statements": statements,
                "questions": questions,
            },
            "runners": out_runners,
        })

    write_json(OUT, {
        "schemaVersion": "edgeiq_current_race_intelligence_v1",
        "generatedAt": generated_at,
        "sourceContract": {
            "formGuide": ENRICHED.name,
            "weather": WEATHER.name,
            "map": MAP.name,
            "provenance": "Overview statements are deterministic and source-tagged; no tipping language or AI filler.",
        },
        "races": out_races,
    })
    write_csv(OVERVIEW_AUDIT, audit_rows, ["race_date", "meeting", "race_number", "item_type", "text", "source", "deterministic_rule", "tipping_language"])
    print(f"CURRENT_RACE_INTELLIGENCE_V1 races={len(out_races)} overview_items={len(audit_rows)}")


if __name__ == "__main__":
    main()
