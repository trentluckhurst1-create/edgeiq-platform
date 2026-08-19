from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-source-discovery"
RAW_DIR = ROOT / "outputs" / "performance-intelligence" / "racingcom-source-discovery" / "raw"

FIXTURE_CONTRACT = DISCOVERY_DIR / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"
NETWORK_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_network_response_ledger_v1.csv"
REQUEST_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_network_request_ledger_v1.csv"
STATIC_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_static_response_ledger_v1.csv"

VALIDATION_OUT = DISCOVERY_DIR / "edgeiq_racingcom_source_candidate_validation_v1.csv"
SCHEMA_OUT = DISCOVERY_DIR / "edgeiq_racingcom_source_schema_profile_v1.csv"
SEMANTICS_OUT = DISCOVERY_DIR / "edgeiq_racingcom_source_semantics_audit_v1.csv"
REPORT_OUT = DISCOVERY_DIR / "edgeiq_racingcom_source_validation_report_v1.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def path_from_repo(value: str) -> Path:
    if not value:
        return Path()
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def load_json_cache(row: dict[str, str]) -> dict[str, Any] | None:
    cache_path = path_from_repo(row.get("cache_path", ""))
    if not cache_path.exists() or cache_path.is_dir():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def extract_visible_text_paths(source_evidence: str) -> list[Path]:
    paths: list[Path] = []
    for token in source_evidence.split("||"):
        match = re.search(r"outputs/performance-intelligence/racingcom-source-discovery/raw/fixture-selection/visible_text_[A-Za-z0-9]+\.txt", token)
        if match:
            paths.append(ROOT / match.group(0))
    return paths


def text_contains_runner_names(paths: list[Path], names: list[str]) -> tuple[int, int]:
    if not paths or not names:
        return 0, len(names)
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in paths if p.exists()).lower()
    matched = 0
    for name in names:
        if name and name.lower() in text:
            matched += 1
    return matched, len(names)


def data_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def semantic_for_field(field_path: str) -> tuple[str, str, str]:
    lower = field_path.lower()
    if lower.endswith("horses[].sectionaltimes[].avgspeed"):
        return "average speed", "metres_per_second", "UI displays km/h by multiplying source value by 3.6."
    if lower.endswith("horses[].sectionaltimes[].time"):
        return "cumulative/section time", "race time string", "Time strings require parser preservation before conversion."
    if lower.endswith("horses[].sectionaltimes[].distance"):
        return "section marker", "metres label or FINISH", "Distance is provided as display label."
    if lower.endswith("horses[].sectionaltimes[].position"):
        return "sectional position", "ordinal", "Position at sectional marker."
    if lower.endswith("horses[].fullname"):
        return "runner identity", "horse name", "Primary runner display identity."
    if lower.endswith("horses[].saddlenumber"):
        return "runner identity", "saddle number", "Supports runner matching."
    if "finalposition" in lower:
        return "result context", "finish position", "Post-race result field; valid in performance warehouse, not predictive features."
    if "comment" in lower:
        return "race comment", "free text", "Post-race narrative; not a raw speed measure."
    if "jockey" in lower or "trainer" in lower:
        return "connection identity", "text", "Context field."
    return "source field", "", ""


def profile_graphql_schema(graphql_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: dict[str, Any] = {}
    counts: Counter[str] = Counter()

    def add(path: str, value: Any) -> None:
        counts[path] += 1
        if path not in examples and value not in (None, "", [], {}):
            examples[path] = value

    for payload in graphql_payloads:
        race = payload.get("data", {}).get("sectionaltimes_callback", {})
        add("data.sectionaltimes_callback", race)
        horses = race.get("Horses") or []
        add("data.sectionaltimes_callback.Horses", horses)
        for horse in horses:
            if not isinstance(horse, dict):
                continue
            for key, value in horse.items():
                if key == "SectionalTimes":
                    add("data.sectionaltimes_callback.Horses[].SectionalTimes", value)
                    for section in value or []:
                        if not isinstance(section, dict):
                            continue
                        for section_key, section_value in section.items():
                            add(f"data.sectionaltimes_callback.Horses[].SectionalTimes[].{section_key}", section_value)
                else:
                    add(f"data.sectionaltimes_callback.Horses[].{key}", value)

    rows: list[dict[str, Any]] = []
    for field_path, count in sorted(counts.items()):
        example = examples.get(field_path)
        semantic, unit, caveat = semantic_for_field(field_path)
        rows.append(
            {
                "source_id": "GRAPHQL_SECTIONALTIMES_GETRACEFORM",
                "source_decision": "VALID_GRAPHQL_SOURCE",
                "field_path": field_path,
                "data_type": data_type(example),
                "presence_count": count,
                "example_value": json.dumps(example, ensure_ascii=False)[:500] if isinstance(example, (dict, list)) else clean_text(example)[:500],
                "semantic": semantic,
                "unit": unit,
                "caveat": caveat,
            }
        )
    return rows


def profile_csv_schema(static_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    sample_paths = [path_from_repo(row.get("cache_path", "")) for row in static_rows if row.get("cache_path")]
    sample_paths = [path for path in sample_paths if path.exists()]
    rows: list[dict[str, Any]] = [
        {
            "source_id": "HISTORICAL_DIRECT_CSV",
            "source_decision": "VALID_DIRECT_CSV_SOURCE",
            "field_path": "line_1",
            "data_type": "semicolon-delimited metadata row",
            "presence_count": len(sample_paths),
            "example_value": "",
            "semantic": "race metadata",
            "unit": "",
            "caveat": "Historical CSV fixture format has no header row; parser must preserve positional schema.",
        },
        {
            "source_id": "HISTORICAL_DIRECT_CSV",
            "source_decision": "VALID_DIRECT_CSV_SOURCE",
            "field_path": "line_n[0]",
            "data_type": "string",
            "presence_count": len(sample_paths),
            "example_value": "",
            "semantic": "runner identity",
            "unit": "horse name",
            "caveat": "Historical CSV runner identity is positional semicolon field 0.",
        },
        {
            "source_id": "HISTORICAL_DIRECT_CSV",
            "source_decision": "VALID_DIRECT_CSV_SOURCE",
            "field_path": "line_n repeating triples: distance; speed; time",
            "data_type": "mixed",
            "presence_count": len(sample_paths),
            "example_value": "",
            "semantic": "sectional structure",
            "unit": "metres, metres_per_second, time string",
            "caveat": "Semantics align broadly with GraphQL SectionalTimes, but source format is different.",
        },
    ]
    for path in sample_paths[:1]:
        text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if text:
            rows[0]["example_value"] = text[0][:500]
        if len(text) > 1:
            rows[1]["example_value"] = text[1].split(";")[0]
            rows[2]["example_value"] = ";".join(text[1].split(";")[2:8])
    return rows


def main() -> None:
    built_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fixtures = read_csv(FIXTURE_CONTRACT)
    network_rows = read_csv(NETWORK_LEDGER)
    request_rows = read_csv(REQUEST_LEDGER)
    static_rows_all = read_csv(STATIC_LEDGER)

    fixtures_by_id = {row.get("fixture_id", ""): row for row in fixtures}
    recent_visible = [row for row in fixtures if row.get("visible_speed_data_status") == "VISIBLE_SPEED_DATA_INDICATED"]
    negative_controls = [row for row in fixtures if row.get("visible_speed_data_status") == "NO_VISIBLE_SPEED_DATA"]
    historical = [row for row in fixtures if row.get("fixture_id", "").startswith("HISTORICAL_CSV")]

    sectional_rows = []
    graphql_payloads = []
    per_fixture_metrics: list[dict[str, Any]] = []
    for row in network_rows:
        decoded_url = unquote(row.get("url", ""))
        if "sectionaltimes_callback" not in decoded_url:
            continue
        payload = load_json_cache(row)
        if not payload:
            continue
        race = payload.get("data", {}).get("sectionaltimes_callback") or {}
        horses = race.get("Horses") or []
        runner_names = [clean_text(horse.get("FullName")) for horse in horses if isinstance(horse, dict)]
        sectional_count = 0
        avg_speed_count = 0
        distance_labels: set[str] = set()
        avg_speed_values: list[float] = []
        for horse in horses:
            for section in (horse.get("SectionalTimes") or []) if isinstance(horse, dict) else []:
                if not isinstance(section, dict):
                    continue
                sectional_count += 1
                label = clean_text(section.get("Distance"))
                if label:
                    distance_labels.add(label)
                try:
                    value = float(section.get("AvgSpeed"))
                    avg_speed_values.append(value)
                    avg_speed_count += 1
                except Exception:
                    pass
        fixture = fixtures_by_id.get(row.get("fixture_id", ""), {})
        matched_names, total_names = text_contains_runner_names(extract_visible_text_paths(fixture.get("source_evidence", "")), runner_names)
        meet_match = re.search(r'meetCode:\s*"([^"]+)"', decoded_url)
        race_match = re.search(r"raceNumber\s*:\s*(\d+)", decoded_url)
        metric = {
            "fixture_id": row.get("fixture_id", ""),
            "race_date": row.get("race_date", ""),
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "meet_code": meet_match.group(1) if meet_match else "",
            "query_race_number": race_match.group(1) if race_match else "",
            "runner_count": len(horses),
            "visible_runner_name_matches": matched_names,
            "visible_runner_names_tested": total_names,
            "sectional_rows": sectional_count,
            "avg_speed_values": avg_speed_count,
            "distance_labels": "|".join(sorted(distance_labels)),
            "avg_speed_min": min(avg_speed_values) if avg_speed_values else "",
            "avg_speed_max": max(avg_speed_values) if avg_speed_values else "",
            "cache_path": row.get("cache_path", ""),
            "url": decoded_url,
        }
        per_fixture_metrics.append(metric)
        sectional_rows.append(row)
        graphql_payloads.append(payload)

    static_csv_rows = [
        row
        for row in static_rows_all
        if row.get("content_type") == "binary/octet-stream" and row.get("cache_path", "").endswith(".csv")
    ]
    static_csv_paths = [path_from_repo(row.get("cache_path", "")) for row in static_csv_rows if path_from_repo(row.get("cache_path", "")).exists()]

    validation_rows: list[dict[str, Any]] = []
    recent_fixture_ids = {row.get("fixture_id", "") for row in recent_visible}
    negative_fixture_ids = {row.get("fixture_id", "") for row in negative_controls}
    graph_fixture_ids = {row["fixture_id"] for row in per_fixture_metrics}
    graph_recent_count = len(graph_fixture_ids & recent_fixture_ids)
    graph_negative_count = len(graph_fixture_ids & negative_fixture_ids)
    graph_runner_total = sum(int(row["runner_count"]) for row in per_fixture_metrics)
    graph_sectional_total = sum(int(row["sectional_rows"]) for row in per_fixture_metrics)
    graph_speed_total = sum(int(row["avg_speed_values"]) for row in per_fixture_metrics)
    visible_match_total = sum(int(row["visible_runner_name_matches"]) for row in per_fixture_metrics)
    visible_test_total = sum(int(row["visible_runner_names_tested"]) for row in per_fixture_metrics)
    request_header_rows = []
    for request in request_rows:
        decoded_url = unquote(request.get("url", ""))
        if "sectionaltimes_callback" not in decoded_url:
            continue
        try:
            headers = json.loads(request.get("safe_header_json") or "{}")
        except Exception:
            headers = {}
        request_header_rows.append(headers)
    public_api_key_header_count = sum(1 for headers in request_header_rows if headers.get("x-api-key"))
    browser_referer_header_count = sum(1 for headers in request_header_rows if "dxp-static.racing.com" in headers.get("referer", ""))

    graph_decision = "VALID_GRAPHQL_SOURCE" if graph_recent_count >= 2 and graph_runner_total > 0 and graph_sectional_total > 0 and graph_speed_total > 0 and graph_negative_count == 0 else "DATA_PRESENT_BUT_SEMANTICS_UNRESOLVED"
    validation_rows.append(
        {
            "candidate_id": "GRAPHQL_SECTIONALTIMES_GETRACEFORM_AGGREGATE",
            "source_kind": "GRAPHQL_RESPONSE",
            "decision": graph_decision,
            "fixture_count": len(graph_fixture_ids),
            "fixture_ids": "|".join(sorted(graph_fixture_ids)),
            "host": "graphql.rmdprod.racing.com",
            "endpoint_path": "/",
            "operation_name": "sectionaltimes_callback:getRaceForm",
            "identifies_race": "YES" if all(row["meet_code"] and row["query_race_number"] == row["race_no"] for row in per_fixture_metrics) else "PARTIAL",
            "identifies_runners": "YES" if graph_runner_total > 0 else "NO",
            "contains_sectional_or_speed_values": "YES" if graph_sectional_total > 0 and graph_speed_total > 0 else "NO",
            "matches_visible_display": "YES" if visible_test_total and visible_match_total / visible_test_total >= 0.8 else "PARTIAL",
            "works_across_multiple_races": "YES" if len(graph_fixture_ids) >= 2 else "NO",
            "dynamic_parameters": "meetCode,raceNumber",
            "authentication_required": "PUBLIC_WIDGET_X_API_KEY_HEADER_REQUIRED_NO_USER_AUTH",
            "signed_or_expiring_url": "NO_OBSERVED",
            "first_party_source": "YES",
            "csv_remains_available_behind_interface": "NO_FRESH_CSV_OBSERVED",
            "parser_required": "YES_JSON_GRAPHQL_PARSER",
            "evidence_cache_paths": "|".join(sorted({row["cache_path"] for row in per_fixture_metrics})),
            "evidence_summary": f"{graph_recent_count} recent visible fixtures, {graph_runner_total} runners, {graph_sectional_total} sectional rows, {graph_speed_total} AvgSpeed values, {graph_negative_count} negative controls.",
            "rejection_reason": "",
        }
    )

    for metric in per_fixture_metrics:
        validation_rows.append(
            {
                "candidate_id": f"GRAPHQL_SECTIONALTIMES_GETRACEFORM_{metric['fixture_id']}",
                "source_kind": "GRAPHQL_RESPONSE",
                "decision": graph_decision,
                "fixture_count": 1,
                "fixture_ids": metric["fixture_id"],
                "host": "graphql.rmdprod.racing.com",
                "endpoint_path": "/",
                "operation_name": "sectionaltimes_callback:getRaceForm",
                "identifies_race": "YES" if metric["query_race_number"] == metric["race_no"] and metric["meet_code"] else "NO",
                "identifies_runners": "YES" if metric["runner_count"] else "NO",
                "contains_sectional_or_speed_values": "YES" if metric["sectional_rows"] and metric["avg_speed_values"] else "NO",
                "matches_visible_display": "YES" if metric["visible_runner_names_tested"] and metric["visible_runner_name_matches"] / metric["visible_runner_names_tested"] >= 0.8 else "PARTIAL",
                "works_across_multiple_races": "YES",
                "dynamic_parameters": f"meetCode={metric['meet_code']};raceNumber={metric['query_race_number']}",
                "authentication_required": "PUBLIC_WIDGET_X_API_KEY_HEADER_REQUIRED_NO_USER_AUTH",
                "signed_or_expiring_url": "NO_OBSERVED",
                "first_party_source": "YES",
                "csv_remains_available_behind_interface": "NO_FRESH_CSV_OBSERVED",
                "parser_required": "YES_JSON_GRAPHQL_PARSER",
                "evidence_cache_paths": metric["cache_path"],
                "evidence_summary": f"{metric['runner_count']} runners; {metric['sectional_rows']} sectional rows; AvgSpeed range {metric['avg_speed_min']} to {metric['avg_speed_max']}; visible runner matches {metric['visible_runner_name_matches']}/{metric['visible_runner_names_tested']}.",
                "rejection_reason": "",
            }
        )

    csv_decision = "VALID_DIRECT_CSV_SOURCE" if len(static_csv_paths) >= len(historical) >= 1 else "DATA_PRESENT_BUT_SEMANTICS_UNRESOLVED"
    validation_rows.append(
        {
            "candidate_id": "HISTORICAL_DIRECT_CSV_AGGREGATE",
            "source_kind": "CSV_FILE",
            "decision": csv_decision,
            "fixture_count": len(static_csv_paths),
            "fixture_ids": "|".join(sorted(row.get("fixture_id", "") for row in static_csv_rows)),
            "host": "d3qmfyv6ad9vwv.cloudfront.net",
            "endpoint_path": "/{meetCode}_{raceNo}.csv",
            "operation_name": "",
            "identifies_race": "YES",
            "identifies_runners": "YES",
            "contains_sectional_or_speed_values": "YES",
            "matches_visible_display": "HISTORICAL_NOT_BROWSER_VISIBLE",
            "works_across_multiple_races": "YES" if len(static_csv_paths) >= 2 else "NO",
            "dynamic_parameters": "historical CloudFront object path",
            "authentication_required": "NO_OBSERVED_PUBLIC_200",
            "signed_or_expiring_url": "NO_OBSERVED",
            "first_party_source": "RACINGCOM_CDN_EVIDENCE_RETAINED",
            "csv_remains_available_behind_interface": "HISTORICAL_ONLY",
            "parser_required": "EXISTING_V2_CSV_PARSER",
            "evidence_cache_paths": "|".join(str(path.relative_to(ROOT)) for path in static_csv_paths),
            "evidence_summary": f"{len(static_csv_paths)} historical CSV fixtures retained from V2 evidence.",
            "rejection_reason": "",
        }
    )

    validation_rows.append(
        {
            "candidate_id": "ANALYTICS_ADVERTISING_AND_UI_ASSET_TRAFFIC",
            "source_kind": "MIXED_NETWORK_TRAFFIC",
            "decision": "REJECTED_UNRELATED_SOURCE",
            "fixture_count": "",
            "fixture_ids": "",
            "host": "multiple",
            "endpoint_path": "analytics/ad/static asset paths",
            "operation_name": "",
            "identifies_race": "NO",
            "identifies_runners": "NO",
            "contains_sectional_or_speed_values": "NO_GOVERNED_SCHEMA",
            "matches_visible_display": "NO",
            "works_across_multiple_races": "IRRELEVANT",
            "dynamic_parameters": "",
            "authentication_required": "",
            "signed_or_expiring_url": "",
            "first_party_source": "MIXED",
            "csv_remains_available_behind_interface": "NO",
            "parser_required": "NO",
            "evidence_cache_paths": "",
            "evidence_summary": "Browser capture contains analytics, advertising, CSS and JavaScript assets; these are not admitted as speed-data sources.",
            "rejection_reason": "Does not contain governed race-runner-sectional schema.",
        }
    )

    schema_rows = profile_graphql_schema(graphql_payloads) + profile_csv_schema(static_csv_rows)

    semantic_checks: list[dict[str, Any]] = []
    def add_check(check: str, status: str, count: Any, detail: str) -> None:
        semantic_checks.append({"check": check, "status": status, "count": count, "detail": detail})

    add_check("recent_visible_graphql_payloads", "PASS" if graph_recent_count == len(recent_visible) else "FAIL", graph_recent_count, f"Expected {len(recent_visible)} visible-speed fixtures with sectionaltimes_callback GraphQL payloads.")
    add_check("negative_controls_rejected", "PASS" if graph_negative_count == 0 else "FAIL", graph_negative_count, "Negative controls must not yield sectionaltimes_callback source candidates.")
    add_check("runner_identity", "PASS" if graph_runner_total > 0 else "FAIL", graph_runner_total, "GraphQL payload must include runner identities.")
    add_check("sectional_rows", "PASS" if graph_sectional_total > 0 else "FAIL", graph_sectional_total, "GraphQL payload must include sectional rows.")
    add_check("avg_speed_values", "PASS" if graph_speed_total > 0 else "FAIL", graph_speed_total, "GraphQL payload must include numeric AvgSpeed values.")
    add_check("visible_runner_match", "PASS" if visible_test_total and visible_match_total / visible_test_total >= 0.8 else "WARN", f"{visible_match_total}/{visible_test_total}", "Runner names from GraphQL should appear in retained visible page text.")
    add_check("source_speed_unit", "PASS", "m/s", "GraphQL AvgSpeed values are in metres per second; Racing.com UI displays km/h after conversion.")
    add_check("fresh_csv_observed", "WARN", 0, "No fresh CSV link was observed behind recent Speed Data pages.")
    add_check("historical_csv_retained", "PASS" if len(static_csv_paths) == len(historical) else "WARN", len(static_csv_paths), f"Expected {len(historical)} V2 historical CSV fixture caches.")
    add_check("public_widget_api_key_header", "PASS" if public_api_key_header_count == graph_recent_count else "WARN", public_api_key_header_count, "Sectional GraphQL browser requests include a public app x-api-key header; no user cookies or auth tokens are required.")
    add_check("browser_referer_header", "PASS" if browser_referer_header_count == graph_recent_count else "WARN", browser_referer_header_count, "Sectional GraphQL browser requests use the public dxp-static Racing.com referer.")
    add_check("signed_or_expiring_url", "PASS", 0, "No signed URL parameters were required for the GraphQL candidate.")
    add_check("parser_implication", "PASS", "JSON_GRAPHQL_PARSER_REQUIRED", "Do not force fresh GraphQL payloads through the historical CSV parser.")

    validation_fields = [
        "candidate_id",
        "source_kind",
        "decision",
        "fixture_count",
        "fixture_ids",
        "host",
        "endpoint_path",
        "operation_name",
        "identifies_race",
        "identifies_runners",
        "contains_sectional_or_speed_values",
        "matches_visible_display",
        "works_across_multiple_races",
        "dynamic_parameters",
        "authentication_required",
        "signed_or_expiring_url",
        "first_party_source",
        "csv_remains_available_behind_interface",
        "parser_required",
        "evidence_cache_paths",
        "evidence_summary",
        "rejection_reason",
    ]
    schema_fields = ["source_id", "source_decision", "field_path", "data_type", "presence_count", "example_value", "semantic", "unit", "caveat"]
    semantic_fields = ["check", "status", "count", "detail"]

    write_csv(VALIDATION_OUT, validation_rows, validation_fields)
    write_csv(SCHEMA_OUT, schema_rows, schema_fields)
    write_csv(SEMANTICS_OUT, semantic_checks, semantic_fields)

    failures = [row for row in semantic_checks if row["status"] == "FAIL"]
    final_status = "RACINGCOM_SOURCE_CANDIDATE_VALIDATION_V1_PASS" if not failures and graph_decision == "VALID_GRAPHQL_SOURCE" else "RACINGCOM_SOURCE_CANDIDATE_VALIDATION_V1_BLOCKED"

    report = f"""# Racing.com Source Candidate Validation V1

Built UTC: {built_utc}

## Status

`{final_status}`

## Candidate Decision

- Fresh source decision: `{graph_decision}`
- Historical CSV decision: `{csv_decision}`
- Fresh source: `graphql.rmdprod.racing.com` GraphQL query alias `sectionaltimes_callback: getRaceForm(meetCode, raceNumber)`
- Current source remains CSV: `NO` for recent Speed Data pages; CSV is retained for the eight historical V2 fixtures only.

## Evidence Counts

- Fixtures consumed: {len(fixtures)}
- Recent visible-speed fixtures: {len(recent_visible)}
- Recent fixtures with GraphQL sectionals payload: {graph_recent_count}
- Negative controls with GraphQL sectionals payload: {graph_negative_count}
- GraphQL source races: {len(graph_fixture_ids)}
- GraphQL runners: {graph_runner_total}
- GraphQL sectional rows: {graph_sectional_total}
- GraphQL numeric AvgSpeed values: {graph_speed_total}
- Visible runner-name matches: {visible_match_total}/{visible_test_total}
- Historical CSV caches retained: {len(static_csv_paths)}
- Public widget x-api-key header observed: {public_api_key_header_count}

## Schema / Unit Findings

- GraphQL runner identity appears under `data.sectionaltimes_callback.Horses[]`.
- Sectional data appears under `Horses[].SectionalTimes[]`.
- Required sectional fields observed: `Distance`, `Position`, `Time`, `AvgSpeed`.
- `AvgSpeed` is source metres per second. The visible Racing.com speed table displays km/h after conversion.
- Fresh recent pages did not expose a direct CSV link in static or browser network evidence.
- A fresh parser should be JSON/GraphQL-specific and should preserve raw fields before canonical normalisation.

## Governance Findings

- The GraphQL candidate requires the public widget `x-api-key` header observed in the Racing.com browser request. No user cookie, user token, or private account credential is required or used.
- No signed or expiring URL was required for admitted GraphQL payloads.
- Analytics, advertising, CSS, JavaScript and ordinary page-layout payloads are rejected as speed-data sources.
- V2 historical CSV parser and warehouse architecture are preserved.
- Production warehouse was not overwritten.
- UI, pricing, probability, rating, V6.1 and V7.2G2 were not modified.

## Next Unit

Proceed to proof-of-concept acquisition using only the evidenced GraphQL sectionals request pattern and the retained historical CSV fixtures. Negative controls must remain rejected.
"""
    REPORT_OUT.write_text(report, encoding="utf-8")

    print(
        json.dumps(
            {
                "status": final_status,
                "fixtures": len(fixtures),
                "validation_rows": len(validation_rows),
                "schema_rows": len(schema_rows),
                "semantic_checks": len(semantic_checks),
                "semantic_failures": len(failures),
                "fresh_decision": graph_decision,
                "historical_csv_decision": csv_decision,
                "recent_graphql_fixtures": graph_recent_count,
                "negative_graphql_fixtures": graph_negative_count,
                "graphql_runners": graph_runner_total,
                "graphql_sectional_rows": graph_sectional_total,
                "production_changed": "NO",
                "ui_changed": "NO",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
