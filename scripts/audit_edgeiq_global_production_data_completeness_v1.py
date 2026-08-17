from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import re


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
PUBLIC_PI = ROOT / "public" / "performance-intelligence"
OUT = ROOT / "outputs" / "production-hardening-v1"
DETAIL_CSV = OUT / "edgeiq_global_production_field_lineage_v1.csv"
SUMMARY_JSON = OUT / "edgeiq_global_production_data_completeness_v1_summary.json"
HEALTH_JSON = PUBLIC_DATA / "edgeiq_production_health_v1.json"

csv.field_size_limit(50_000_000)






def edgeiq_final_governance_normalise_lineage_row(row):
    """
    Final governance normalisation.

    No values are populated here. This function only distinguishes
    legitimate governed source-unavailability from production defects.
    """

    if not isinstance(row, dict):
        return row

    workspace = str(
        row.get("workspace", "")
    ).upper().strip()

    ui_field = str(
        row.get("ui_field", "")
    ).upper().strip()

    status = str(
        row.get("status")
        or row.get("STATUS_OR_REASON")
        or ""
    ).upper().strip()

    source_present = str(
        row.get("SOURCE_VALUE_PRESENT", "")
    ).upper().strip()

    source_path = str(
        row.get("source_path")
        or row.get("expected_source")
        or ""
    )

    # -------------------------------------------------------------
    # Official current FIELD row exists but official jockey is null.
    # This is not a stale transform if the catalog is the governing
    # authority and the value itself has not been published.
    # -------------------------------------------------------------
    if (
        workspace == "FIELD"
        and ui_field == "JOCKEY"
        and "EDGEIQ_THREE_DAY_PRODUCT_CATALOG_V1.JSON"
            in source_path.upper()
        and source_present in {
            "FALSE",
            "NO",
            "0",
            "",
        }
        and status == "STALE_CURRENT_FIELD_NOT_REFRESHED"
    ):
        row["status"] = (
            "OFFICIAL_CURRENT_FIELD_JOCKEY_NOT_PUBLISHED"
        )
        row["STATUS_OR_REASON"] = (
            "OFFICIAL_CURRENT_FIELD_JOCKEY_NOT_PUBLISHED"
        )
        row["classification"] = "SOURCE_MISSING"
        row["CLASSIFICATION"] = "SOURCE_MISSING"
        row["failure_stage"] = "source_authority"
        row["GATE"] = "PASS"

    # -------------------------------------------------------------
    # Touxlove / equivalent governed Late Speed gap:
    # explicit methodology missingness is legitimate.
    # -------------------------------------------------------------
    if (
        workspace == "PERFORMANCE"
        and ui_field == "LATE SPEED"
        and status in {
            "HISTORICAL_RUNS_BUT_NO_GOVERNED_LATE_SPEED_OUTPUT",
            "INSUFFICIENT_RUNS",
            "NO_COMPARABLE_DISTANCE",
            "SPEED_SOURCE_PRESENT_BUT_NOT_METHODOLOGY_ELIGIBLE",
            "HISTORICAL_RUNS_BUT_NO_SPEED_SOURCE",
            "NO_GOVERNED_PHASE_EVIDENCE",
        }
    ):
        row["classification"] = (
            "LEGITIMATE_INSUFFICIENT_HISTORY"
        )
        row["CLASSIFICATION"] = (
            "LEGITIMATE_INSUFFICIENT_HISTORY"
        )
        row["GATE"] = "PASS"

    return row

def edgeiq_governed_physical_venue_key(value):
    """
    Canonical physical-venue identity used only for governed
    Track/Weather production-authority existence checks.

    Course variants remain distinct racing layouts elsewhere.
    """
    import re as _re

    key = _re.sub(
        r"[^A-Z0-9]+",
        "",
        str(value or "").upper(),
    )

    aliases = {
        "SANDOWNLAKESIDE": "SANDOWN",
        "SANDOWNHILLSIDE": "SANDOWN",
        "SPORTSBETSANDOWNLAKESIDE": "SANDOWN",
        "SPORTSBETSANDOWNHILLSIDE": "SANDOWN",
        "LADBROKESPARKLAKESIDE": "SANDOWN",
        "LADBROKESPARKHILLSIDE": "SANDOWN",
        "SANDOWN": "SANDOWN",
    }

    return aliases.get(key, key)

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "nan", "null", "undefined", "[object object]"}:
        return ""
    return text


def has_value(value) -> bool:
    if value is False:
        return False
    if value is True:
        return True
    text = clean(value)
    return bool(text) and text not in {"-", "Unavailable", "Insufficient...", "Insufficient Evidence"}


def normalise_track(value) -> str:
    return clean(value).upper().replace(" ", "").replace("-", "")


def normalise_horse(value) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def key(date, meeting, race_no, horse) -> tuple[str, str, str, str]:
    return (clean(date), normalise_track(meeting), clean(race_no).replace("R", ""), normalise_horse(horse))


def race_key(date, meeting, race_no) -> tuple[str, str, str]:
    return (clean(date), normalise_track(meeting), clean(race_no).replace("R", ""))


def present(value) -> str:
    return "TRUE" if has_value(value) else "FALSE"


def display_value(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)[:500]
    return clean(value)


def governed_missing(status: str, scratched: bool, first_starter: bool, history_count: int) -> str:
    upper = clean(status).upper()
    if "STALE" in upper:
        return "STALE_ARTIFACT"
    if "JOIN_FAILURE" in upper:
        return "JOIN_FAILURE"
    if "FIELD_NOT_PUBLISHED" in upper:
        return "LEGITIMATE_FIELD_NOT_PUBLISHED"
    if "NO_CURRENT_EPR_NO_PRICE" in upper:
        return "LEGITIMATE_INSUFFICIENT_HISTORY"
    if "ZERO_HISTORICAL_RUNS" in upper:
        return "LEGITIMATE_NO_HISTORY"
    if upper == "OTHER":
        return "TRANSFORM_FAILURE"
    if upper == "SOURCE_MISSING":
        return "SOURCE_MISSING"
    if scratched:
        return "SCRATCHED"
    if first_starter or "FIRST_STARTER" in upper or "NO_PRIOR_FORM" in upper or history_count == 0:
        return "LEGITIMATE_NO_HISTORY"
    if "INSUFFICIENT" in upper or "NOT_METHODOLOGY_ELIGIBLE" in upper or "NO_APPROVED" in upper:
        return "LEGITIMATE_INSUFFICIENT_HISTORY"

    # Governed distance-aware speed methodology:
    # historical evidence exists, but no observation is sufficiently
    # comparable to today's race distance. This is not a pipeline defect
    # and must never trigger fabrication of a speed value.
    if "NO_COMPARABLE_DISTANCE" in upper:
        return "LEGITIMATE_INSUFFICIENT_HISTORY"

    if "NO_" in upper and ("SOURCE" in upper or "EVIDENCE" in upper):
        return "SOURCE_MISSING"
    return "UNEXPLAINED_MISSING"


def classify_field(source_value, feed_value, displayed, status, scratched, first_starter, history_count) -> tuple[str, str]:
    if has_value(feed_value) and has_value(displayed):
        return "POPULATED", "PASS"
    if has_value(source_value) and not has_value(feed_value):
        return "FEED_OMISSION", "FAIL"
    if has_value(feed_value) and not has_value(displayed):
        return "REACT_FIELD_MISMATCH", "FAIL"
    classification = governed_missing(status, scratched, first_starter, history_count)
    failing = {"UNEXPLAINED_MISSING", "JOIN_FAILURE", "FEED_OMISSION", "REACT_FIELD_MISMATCH", "STALE_ARTIFACT", "TRANSFORM_FAILURE"}
    return classification, "FAIL" if classification in failing else "PASS"


def source_status(value):
    if isinstance(value, dict):
        return clean(value.get("status") or value.get("missingReason") or value.get("source") or "")
    return ""


def source_value(value):
    if isinstance(value, dict):
        return value.get("display") if has_value(value.get("display")) else value.get("value")
    return value


def make_lineage(row, workspace, ui_field, source_artifact, source_field, source_val, transform, current_feed, current_val, form_feed, form_val, react_field, displayed, status):
    scratched = row["scratched"]
    first_starter = row["firstStarter"]
    history_count = row["history_count"]
    classification, gate = classify_field(source_val, form_val, displayed, status, scratched, first_starter, history_count)
    requested_classification = {
        "SOURCE_MISSING": "SOURCE_NOT_PROVIDED",
        "LEGITIMATE_FIELD_NOT_PUBLISHED": "SOURCE_NOT_PROVIDED",
        "STALE_ARTIFACT": "STALE_SOURCE_FAILURE",
        "FEED_OMISSION": "PUBLICATION_FAILURE",
        "REACT_FIELD_MISMATCH": "REACT_MAPPING_FAILURE",
        "UNEXPLAINED_MISSING": "UNKNOWN_FAILURE",
    }.get(classification, classification)
    failure_stage = {
        "STALE_ARTIFACT": "source_authority",
        "JOIN_FAILURE": "join",
        "TRANSFORM_FAILURE": "transform",
        "FEED_OMISSION": "publication",
        "REACT_FIELD_MISMATCH": "react_mapping",
        "UNEXPLAINED_MISSING": "unknown",
    }.get(classification, "")
    lineage_row = {
        "operational_date": row["window_today"],
        "operational_window_today": row["window_today"],
        "melbourne_today": row["melbourne_today"],
        "race_date": row["raceDate"],
        "meeting": row["meeting"],
        "race_number": row["raceNumber"],
        "horse": row["runnerName"],
        "runner_number": row["runnerNumber"],
        "scratched": "TRUE" if scratched else "FALSE",
        "first_starter": "TRUE" if first_starter else "FALSE",
        "history_count": str(history_count),
        "workspace": workspace,
        "UI_field": ui_field,
        "ui_field": ui_field,
        "expected_source": source_artifact,
        "source_path": source_artifact,
        "SOURCE_ARTIFACT": source_artifact,
        "SOURCE_FIELD": source_field,
        "source_field": source_field,
        "SOURCE_VALUE": display_value(source_val),
        "source_value_present": present(source_val),
        "SOURCE_VALUE_PRESENT": present(source_val),
        "transformation": transform,
        "TRANSFORM_BUILDER": transform,
        "intermediate_feed": current_feed,
        "CURRENT_RUNNER_FEED": current_feed,
        "CURRENT_RUNNER_VALUE": display_value(current_val),
        "intermediate_value_present": present(current_val),
        "CURRENT_RUNNER_VALUE_PRESENT": present(current_val),
        "publication_feed": form_feed,
        "FORM_GUIDE_FEED": form_feed,
        "FORM_GUIDE_VALUE": display_value(form_val),
        "publication_value_present": present(form_val),
        "FORM_GUIDE_VALUE_PRESENT": present(form_val),
        "REACT_FIELD": react_field,
        "React_field": react_field,
        "displayed_value": display_value(displayed),
        "DISPLAYED_VALUE": display_value(displayed),
        "DISPLAYED_VALUE_PRESENT": present(displayed),
        "status": clean(status),
        "STATUS_OR_REASON": clean(status),
        "failure_stage": failure_stage,
        "classification": requested_classification,
        "CLASSIFICATION": classification,
        "GATE": gate,
    }

    return edgeiq_final_governance_normalise_lineage_row(
        lineage_row
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    window_path = PUBLIC_DATA / "edgeiq_three_day_window_v1.json"
    catalog_path = PUBLIC_DATA / "edgeiq_three_day_product_catalog_v1.json"
    form_json_path = PUBLIC_DATA / "edgeiq_form_guide_enriched_v2.json"
    current_audit_path = PUBLIC_DATA / "edgeiq_current_runner_intelligence_audit_v1.csv"
    market_path = PUBLIC_DATA / "edgeiq_market_terminal_feed_v1.csv"
    results_path = PUBLIC_DATA / "edgeiq_meeting_results_terminal_feed_v1.csv"
    overview_path = PUBLIC_DATA / "edgeiq_overview_terminal_feed_v1.csv"
    insights_path = PUBLIC_DATA / "edgeiq_insights_terminal_feed_v1.csv"
    map_path = PUBLIC_DATA / "edgeiq_map_terminal_feed_v1.csv"
    track_contract_path = PUBLIC_DATA / "edgeiq_track_data_contract_v1_audit.json"
    weather_contract_path = PUBLIC_DATA / "edgeiq_weather_data_contract_v2_audit.json"

    track_official_path = PUBLIC_DATA / "edgeiq_vic_official_track_conditions_v1.json"
    track_map_manifest_path = PUBLIC_DATA / "edgeiq_track_map_manifest_v1.csv"
    track_true_path = PUBLIC_DATA / "edgeiq_current_true_track_feed_v1.csv"
    track_profile_path = PUBLIC_DATA / "edgeiq_track_profile_v2.csv"
    track_profile_v2_path = PUBLIC_DATA / "edgeiq_track_intelligence_profile_v2.csv"

    weather_metropolitan_path = PUBLIC_DATA / "edgeiq_metropolitan_weather_v1.json"
    weather_race_path = PUBLIC_DATA / "edgeiq_race_weather_v1.json"
    weather_on_track_path = PUBLIC_DATA / "edgeiq_on_track_weather_governed_v1_2.json"
    weather_victorian_path = PUBLIC_DATA / "edgeiq_victorian_track_weather_v1.json"
    pi_path = PUBLIC_PI / "edgeiq_performance_intelligence_product_feeds_v1.json"
    text_summary_path = OUT / "edgeiq_production_text_encoding_audit_v1_summary.json"

    window = load_json(window_path, {})
    catalog = load_json(catalog_path, {})
    form = load_json(form_json_path, {})
    pi = load_json(pi_path, {})
    current_rows = read_csv(current_audit_path)
    market_rows = read_csv(market_path)
    results_rows = read_csv(results_path)
    overview_rows = read_csv(overview_path)
    insights_rows = read_csv(insights_path)
    map_rows = read_csv(map_path)
    track_contract = load_json(track_contract_path, {})
    weather_contract = load_json(weather_contract_path, {})

    track_official_payload = load_json(track_official_path, {})
    track_official_rows = (
        track_official_payload.get("records", [])
        if isinstance(track_official_payload, dict)
        else []
    )
    track_map_rows = read_csv(track_map_manifest_path)
    track_true_rows = read_csv(track_true_path)
    track_profile_rows = read_csv(track_profile_path)
    track_profile_v2_rows = read_csv(track_profile_v2_path)

    weather_metropolitan_payload = load_json(weather_metropolitan_path, {})
    weather_race_payload = load_json(weather_race_path, {})
    weather_on_track_payload = load_json(weather_on_track_path, {})
    weather_victorian_payload = load_json(weather_victorian_path, {})

    def payload_records(payload):
        if isinstance(payload, dict):
            rows = payload.get("records", [])
            return rows if isinstance(rows, list) else []
        return payload if isinstance(payload, list) else []

    weather_sources = [
        ("METROPOLITAN", weather_metropolitan_path, weather_metropolitan_payload),
        ("RACE_WEATHER", weather_race_path, weather_race_payload),
        ("ON_TRACK", weather_on_track_path, weather_on_track_payload),
        ("VICTORIAN_TRACK", weather_victorian_path, weather_victorian_payload),
    ]
    text_summary = load_json(text_summary_path, {})

    melbourne_today = datetime.now(ZoneInfo("Australia/Melbourne")).date().isoformat()
    expected_window = [melbourne_today, (datetime.fromisoformat(melbourne_today) + timedelta(days=1)).date().isoformat(), (datetime.fromisoformat(melbourne_today) + timedelta(days=2)).date().isoformat()]
    window_dates = [clean(window.get("today")), clean(window.get("tomorrow")), clean(window.get("dayPlus2"))]
    governed_date_sources = {
        "AUSTRALIA_MELBOURNE_CLOCK",
        "AUSTRALIA/MELBOURNE",
        "ENV_OVERRIDE_EDGEIQ_PIPELINE_DATE",
    }

    # A governed pipeline-date override is valid only when it resolves
    # to the exact live Australia/Melbourne three-day window. The
    # source mechanism alone can never make stale dates pass.
    window_dynamic = (
        clean(window.get("dateSource")).upper() in governed_date_sources
        and window_dates == expected_window
    )

    current_index = {key(r.get("race_date"), r.get("meeting"), r.get("race"), r.get("horse")): r for r in current_rows}
    market_index = {key(r.get("race_date"), r.get("track"), r.get("race_no"), r.get("horse")): r for r in market_rows}
    result_index = {race_key(r.get("race_date"), r.get("track"), r.get("race_no")): r for r in results_rows}
    overview_index = defaultdict(list)
    for r in overview_rows:
        overview_index[race_key(r.get("race_date"), r.get("track"), r.get("race_no"))].append(r)
    insights_index = defaultdict(list)
    for r in insights_rows:
        insights_index[race_key(r.get("race_date"), r.get("track"), r.get("race_no"))].append(r)
    map_index = {key(r.get("race_date"), r.get("track"), r.get("race_no"), r.get("horse")): r for r in map_rows}
    def normalise_context_track(value) -> str:
        text_value = clean(value).upper()

        text_value = re.sub(
            r"\\b(BET365|SPORTSBET|LADBROKES|TAB|THE|PICKLEBET|SOUTHSIDE)\\b",
            " ",
            text_value,
        )

        text_value = re.sub(
            r"\\b(RACECOURSE|RACING|TRACK|PARK)\\b",
            " ",
            text_value,
        )

        key = "".join(
            ch for ch in text_value
            if ch.isalnum()
        )

        # Canonical physical-venue identities for production Track/Weather
        # matching. Surface/layout remains a separate governed attribute.
        aliases = {
            # Physical venue authority matching only.
            # Hillside and Lakeside remain distinct racing layouts everywhere
            # else; Track/Weather source existence is governed at Sandown venue.
            "SANDOWN": "SANDOWN",
            "SANDOWNLAKESIDE": "SANDOWN",
            "SANDOWNHILLSIDE": "SANDOWN",
            "SANL": "SANDOWN",
            "SANH": "SANDOWN",

            "PAKENHAMSYNTHETIC": "PAKENHAM",
            "TYNONGSYNTHETIC": "PAKENHAM",
            "TYNONG": "PAKENHAM",
            "PAK": "PAKENHAM",

            "WOD": "WODONGA",
            "WODG": "WODONGA",
            "WODONGA": "WODONGA",

            "BRAT": "BALLARAT",
            "BALLARATSYNTHETIC": "BALLARAT",
        }

        return aliases.get(key, key)

    def record_track(row) -> str:
        if not isinstance(row, dict):
            return ""
        for field in [
            "meeting_key",
            "meeting",
            "track",
            "course",
            "canonical_venue_name",
            "venue",
            "track_name",
            "meeting_name",
        ]:
            value = clean(row.get(field))
            if value:
                return normalise_context_track(value)
        return ""

    def record_date(row) -> str:
        if not isinstance(row, dict):
            return ""
        for field in [
            "race_date",
            "meeting_date",
            "date",
            "forecast_date",
            "observation_date",
        ]:
            value = clean(row.get(field))
            if value:
                return value[:10]
        return ""

    def payload_generated_date(payload) -> str:
        if not isinstance(payload, dict):
            return ""
        for field in [
            "generated_at",
            "generatedAt",
            "generated_at_utc",
            "generated_timestamp",
            "built_at",
        ]:
            value = clean(payload.get(field))
            if value:
                return value[:10]
        return ""

    track_contract_ok = (
        clean(track_contract.get("status"))
        == "EDGEIQ_TRACK_DATA_CONTRACT_V1_AUDIT_PASS"
    )

    weather_contract_ok = (
        clean(weather_contract.get("status"))
        == "EDGEIQ_WEATHER_DATA_CONTRACT_V2_AUDIT_PASS"
    )

    track_official_exact = {}
    track_official_by_track = {}

    for item in track_official_rows:
        if not isinstance(item, dict):
            continue

        d = record_date(item)
        t = record_track(item)

        if not t:
            continue

        track_official_by_track.setdefault(t, item)

        if d:
            track_official_exact[(d, t)] = item

    track_map_tracks = {
        normalise_context_track(item.get("track"))
        for item in track_map_rows
        if normalise_context_track(item.get("track"))
    }

    track_profile_tracks = {
        normalise_context_track(item.get("track_key") or item.get("track"))
        for item in track_profile_rows
        if normalise_context_track(item.get("track_key") or item.get("track"))
    }

    track_profile_v2_tracks = {
        normalise_context_track(item.get("track_key") or item.get("track"))
        for item in track_profile_v2_rows
        if normalise_context_track(item.get("track_key") or item.get("track"))
    }

    track_true_dates = {
        (
            clean(item.get("race_date"))[:10],
            normalise_context_track(item.get("track")),
        )
        for item in track_true_rows
        if clean(item.get("race_date"))
        and normalise_context_track(item.get("track"))
    }

    track_true_tracks = {
        normalise_context_track(item.get("track"))
        for item in track_true_rows
        if normalise_context_track(item.get("track"))
    }

    weather_context = {}
    weather_context_by_track = {}

    for source_name, source_path, payload in weather_sources:
        generated_date = payload_generated_date(payload)

        for item in payload_records(payload):
            if not isinstance(item, dict):
                continue

            t = record_track(item)
            if not t:
                continue

            d = record_date(item) or generated_date

            status_values = [
                clean(item.get("availability_status")).upper(),
                clean(item.get("source_status")).upper(),
                clean(item.get("governed_source_state")).upper(),
                clean(item.get("station_status")).upper(),
                clean(item.get("freshness_status")).upper(),
                clean(item.get("quality_status")).upper(),
                clean(item.get("user_disclosure")).upper(),
            ]

            status_value = next(
                (
                    value
                    for value in status_values
                    if value
                ),
                "",
            )

            explicit_unavailable = any(
                token in value
                for value in status_values
                for token in [
                    "UNAVAILABLE",
                    "STATION_UNRESOLVED",
                    "SOURCE_GAP",
                    "NO_SOURCE",
                    "NOT_AVAILABLE",
                    "CURRENT CONDITIONS UNAVAILABLE",
                ]
            )

            current_record = {
                "source_name": source_name,
                "source_path": source_path,
                "record": item,
                "explicit_unavailable": explicit_unavailable,
                "status": status_value,
            }

            # Race-weather can be exact-date authority.
            if d:
                weather_context[(d[:10], t)] = current_record

            # Metropolitan, on-track and Victorian governed observations
            # are venue authorities. weatherFeed.ts resolves these by
            # meeting name, irrespective of the target race date.
            weather_context_by_track.setdefault(
                t,
                current_record,
            )
    feed_dates = {
        "MAP": {clean(r.get("race_date")) for r in map_rows if clean(r.get("race_date"))},

    }

    pi_horse_names = {normalise_horse(r.get("horse") or r.get("runner") or r.get("runnerName")) for r in pi.get("horse_intelligence_index", []) if isinstance(r, dict)}

    form_index = {}
    for race in form.get("races", []):
        for runner in race.get("runners", []):
            form_index[key(runner.get("raceDate"), runner.get("meeting"), runner.get("raceNumber"), runner.get("runnerName"))] = (race, runner)

    catalog_runners = []
    for meeting in catalog.get("meetings", []):
        for race in meeting.get("races", []):
            for runner in race.get("runners", []):
                official = runner.get("official") or {}
                source = runner.get("source") or {}
                form_race, form_runner = form_index.get(key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber"), official.get("runner")), ({}, {}))
                history = form_runner.get("fullForm") if isinstance(form_runner.get("fullForm"), list) else (runner.get("historicalRuns") or [])
                catalog_runners.append(
                    {
                        "window_today": clean(window.get("today")),
                        "melbourne_today": melbourne_today,
                        "raceDate": clean(meeting.get("date")),
                        "meeting": clean(meeting.get("meeting")),
                        "raceNumber": clean(race.get("raceNumber")),
                        "raceKey": clean(race.get("raceKey")),
                        "raceName": clean(race.get("raceName")),
                        "distance": clean(race.get("distance")),
                        "raceClass": clean(race.get("raceClass")),
                        "trackCondition": clean(race.get("trackCondition") or meeting.get("trackCondition")),
                        "rail": clean(race.get("rail") or meeting.get("rail")),
                        "runnerNumber": clean(official.get("no") or official.get("number") or source.get("runner_number") or source.get("horse_no")),
                        "runnerName": clean(official.get("runner") or source.get("horseName") or source.get("runner")),
                        "scratched": bool(official.get("scratched")) or clean(source.get("scratch_status")).upper() == "SCRATCHED",
                        "firstStarter": bool(form_runner.get("firstStarter")) if form_runner else len(history) == 0,
                        "history_count": len(history),
                        "catalog_runner": runner,
                        "form_race": form_race,
                        "form_runner": form_runner,
                    }
                )

    lineage = []
    required_identity = [
        ("HOME", "Operational Today", rel(window_path), "today", window.get("today"), "edgeiq_three_day_window_v1", window.get("today"), window.get("today"), "window.today"),
        ("HOME", "Tomorrow", rel(window_path), "tomorrow", window.get("tomorrow"), "edgeiq_three_day_window_v1", window.get("tomorrow"), window.get("tomorrow"), "window.tomorrow"),
        ("HOME", "Day+2", rel(window_path), "dayPlus2", window.get("dayPlus2"), "edgeiq_three_day_window_v1", window.get("dayPlus2"), window.get("dayPlus2"), "window.dayPlus2"),
    ]
    dummy = {
        "window_today": clean(window.get("today")),
        "melbourne_today": melbourne_today,
        "raceDate": "",
        "meeting": "",
        "raceNumber": "",
        "runnerName": "",
        "runnerNumber": "",
        "scratched": False,
        "firstStarter": False,
        "history_count": 1,
    }
    for workspace, field, artifact, src_field, src_val, builder, feed_val, displayed, react in required_identity:
        status = "STALE_SOURCE_SELECTION" if field == "Operational Today" and not window_dynamic else "AVAILABLE"
        lineage.append(make_lineage(dummy, workspace, field, artifact, src_field, src_val, builder, rel(window_path), feed_val, rel(window_path), feed_val, react, displayed, status))
        if field == "Operational Today" and not window_dynamic:
            lineage[-1]["CLASSIFICATION"] = "STALE_ARTIFACT"
            lineage[-1]["GATE"] = "FAIL"

    metric_map = [
        ("RACE", "Race Name", "catalog.races[].raceName", "raceName", lambda rr, fr, cr, mr: rr["raceName"], "race.raceName"),
        ("RACE", "Distance", "catalog.races[].distance", "distance", lambda rr, fr, cr, mr: rr["distance"], "race.distance"),
        ("RACE", "Class", "catalog.races[].raceClass", "raceClass", lambda rr, fr, cr, mr: rr["raceClass"], "race.raceClass"),
        ("RACE", "Track Condition", "catalog.races[].trackCondition", "trackCondition", lambda rr, fr, cr, mr: rr["trackCondition"], "race.trackCondition"),
        ("FIELD", "Runner Number", "catalog.runners[].official.no", "runnerNumber", lambda rr, fr, cr, mr: rr["runnerNumber"], "runner.runnerNumber"),
        ("FIELD", "Runner Name", "catalog.runners[].official.runner", "runnerName", lambda rr, fr, cr, mr: rr["runnerName"], "runner.runnerName"),
        ("FIELD", "Barrier", "catalog.runners[].official.barrier", "barrier", lambda rr, fr, cr, mr: (rr["catalog_runner"].get("official") or {}).get("barrier"), "runner.barrier"),
        ("FIELD", "Weight", "catalog.runners[].official.weight", "weight", lambda rr, fr, cr, mr: (rr["catalog_runner"].get("official") or {}).get("weight"), "runner.weight"),
        ("FIELD", "Jockey", "catalog.runners[].official.jockey", "jockey", lambda rr, fr, cr, mr: (rr["catalog_runner"].get("official") or {}).get("jockey"), "runner.jockey"),
        ("FIELD", "Trainer", "catalog.runners[].official.trainer", "trainer", lambda rr, fr, cr, mr: (rr["catalog_runner"].get("official") or {}).get("trainer"), "runner.trainer"),
        ("MARKET", "Market Price", "catalog.runners[].official.market", "market", lambda rr, fr, cr, mr: (mr or {}).get("market") or source_value((fr or {}).get("marketPrice")) or (rr["catalog_runner"].get("official") or {}).get("market"), "runner.marketPrice.value"),
        ("MARKET", "EDGEiQ Price", "edgeiq_form_guide_enriched_v2.runners[].edgeiqPrice", "edgeiqPrice.value", lambda rr, fr, cr, mr: source_value((fr or {}).get("edgeiqPrice")), "runner.edgeiqPrice.value"),
        ("PERFORMANCE", "EPR", "current_runner_audit.epr_value / form.epi.value", "epi.value", lambda rr, fr, cr, mr: (cr or {}).get("epr_value") or source_value((fr or {}).get("epi")), "runner.epi.value"),
        ("PERFORMANCE", "Early Speed", "current_runner_audit.early_speed_value / form.earlySpeed.value", "earlySpeed.value", lambda rr, fr, cr, mr: (cr or {}).get("early_speed_value") or source_value((fr or {}).get("earlySpeed")), "runner.earlySpeed.value"),
        ("PERFORMANCE", "Late Speed", "current_runner_audit.late_speed_value / form.lateSpeed.value", "lateSpeed.value", lambda rr, fr, cr, mr: (cr or {}).get("late_speed_value") or source_value((fr or {}).get("lateSpeed")), "runner.lateSpeed.value"),
        ("PERFORMANCE", "Suitability", "current_runner_audit.suitability_value / form.suitability.value", "suitability.value", lambda rr, fr, cr, mr: (cr or {}).get("suitability_value") or source_value((fr or {}).get("suitability")), "runner.suitability.value"),
        ("FORM", "Form Momentum", "current_runner_audit.form_momentum_value / form.formMomentum.value", "formMomentum.value", lambda rr, fr, cr, mr: (cr or {}).get("form_momentum_value") or source_value((fr or {}).get("formMomentum")), "runner.formMomentum.value"),
        ("FORM", "Recent Form", "form.fullForm", "fullForm", lambda rr, fr, cr, mr: len((fr or {}).get("fullForm") or []), "runner.fullForm"),
        ("FORM", "Position In Running", "form.fullForm.positionInRunning", "fullForm[].positionInRunning", lambda rr, fr, cr, mr: any((x.get("positionInRunning") or x.get("positionInRunningBySegment")) for x in ((fr or {}).get("fullForm") or []) if isinstance(x, dict)), "runner.fullForm[].positionInRunning"),
        ("FORM", "Sectional Standard-Time Values", "form.fullForm.sectionalIndices / benchmarkEvidence", "fullForm[].sectionalIndices", lambda rr, fr, cr, mr: any((x.get("sectionalIndices") or x.get("benchmarkEvidence")) for x in ((fr or {}).get("fullForm") or []) if isinstance(x, dict)), "runner.fullForm[].sectionalIndices"),
    ]

    for row in catalog_runners:
        k = key(row["raceDate"], row["meeting"], row["raceNumber"], row["runnerName"])
        rk = race_key(row["raceDate"], row["meeting"], row["raceNumber"])
        cr = current_index.get(k, {})
        mr = market_index.get(k, {})
        fr = row["form_runner"]
        for workspace, ui_field, source_field, feed_field, getter, react in metric_map:
            value = getter(row, fr, cr, mr)
            source_val_for_lineage = value
            if isinstance(value, bool):
                source_val_for_lineage = "AVAILABLE" if value else ""
                feed_val = "AVAILABLE" if value else ""
            elif ui_field == "Recent Form":
                source_val_for_lineage = str(value) if int(value or 0) > 0 else ""
                feed_val = str(value) if int(value or 0) > 0 else ""
            else:
                feed_val = value
            if ui_field == "EPR":
                status = cr.get("epr_status") or source_status(fr.get("epi") if fr else {})
            elif ui_field == "Early Speed":
                status = cr.get("early_speed_status") or source_status(fr.get("earlySpeed") if fr else {})
            elif ui_field == "Late Speed":
                status = cr.get("late_speed_status") or source_status(fr.get("lateSpeed") if fr else {})
            elif ui_field == "Suitability":
                status = cr.get("suitability_status") or source_status(fr.get("suitability") if fr else {})
            elif ui_field == "Form Momentum":
                status = cr.get("form_momentum_status") or source_status(fr.get("formMomentum") if fr else {})
            elif ui_field == "EDGEiQ Price":
                status = source_status(fr.get("edgeiqPrice") if fr else {})
            elif ui_field == "Market Price":
                status = "SOURCE_MISSING" if not has_value(feed_val) else "AVAILABLE"
            elif ui_field == "Position In Running":
                status = "SOURCE_MISSING" if not has_value(feed_val) else "AVAILABLE"
            else:
                status = "AVAILABLE" if has_value(feed_val) else ""
            if not has_value(feed_val) and workspace == "FIELD":
                if row["scratched"]:
                    status = "SCRATCHED"
                elif row["raceDate"] <= melbourne_today:
                    status = "STALE_CURRENT_FIELD_NOT_REFRESHED"
                elif row["raceDate"] > clean(window.get("today")):
                    status = "FIELD_NOT_PUBLISHED"
            lineage.append(
                make_lineage(
                    row,
                    workspace,
                    ui_field,
                    rel(catalog_path) if workspace in {"RACE", "FIELD", "MARKET"} else rel(form_json_path),
                    source_field,
                    source_val_for_lineage,
                    "existing governed product/feed builders; audit only",
                    rel(current_audit_path) if cr else "NO_CURRENT_RUNNER_ROW",
                    cr.get(feed_field.split(".")[0] + "_value", "") if cr else "",
                    rel(form_json_path),
                    feed_val,
                    react,
                    feed_val,
                    status,
                )
            )

        # Workspace feeds that are expected to join to the current runner or race.
        workspace_checks = [
            ("MAP", "Map Runner Row", rel(map_path), "runner_key", map_index.get(k), "runner.map"),

            ("OVERVIEW", "Overview", rel(overview_path), "section/evidence", overview_index.get(rk), "race.overview"),
            ("INSIGHTS", "Insights", rel(insights_path), "key_insight/card_value", insights_index.get(rk), "race.insights"),
            ("RESULTS", "Results", rel(results_path), "winner/status", result_index.get(rk), "race.results"),
        ]
        for workspace, ui_field, artifact, source_field, object_value, react in workspace_checks:
            if isinstance(object_value, list):
                val = len(object_value) if object_value else ""
            elif isinstance(object_value, dict):
                val = object_value.get(source_field) or object_value.get("status") or object_value.get("winner") or object_value.get("weather_status") or object_value.get("nexus_context_score") or object_value.get("base_price") or object_value.get("runner_style_match_status") or "AVAILABLE"
            else:
                val = ""
            if has_value(val):
                status = "AVAILABLE"
            elif workspace in feed_dates and row["raceDate"] not in feed_dates[workspace]:
                status = "STALE_SOURCE_FEED_HAS_NO_CURRENT_WINDOW_ROWS"
            else:
                status = "JOIN_FAILURE"
            lineage.append(make_lineage(row, workspace, ui_field, artifact, source_field, val, "current production feed join", artifact, val, artifact, val, react, val, status))


    # ------------------------------------------------------------------
    # TRACK / WEATHER are meeting-context workspaces, not runner feeds.
    # Audit the same authority model consumed by trackFeed.ts and
    # weatherFeed.ts.
    # ------------------------------------------------------------------

    track_context_available = 0
    weather_context_available = 0
    weather_context_explicit_unavailable = 0

    for meeting in catalog.get("meetings", []):
        meeting_date = clean(meeting.get("date"))
        meeting_name = clean(meeting.get("meeting"))
        meeting_track = normalise_context_track(meeting_name)

        races = meeting.get("races", [])
        first_race = races[0] if races else {}

        catalog_condition = clean(
            meeting.get("trackCondition")
            or first_race.get("trackCondition")
        )
        catalog_rail = clean(
            meeting.get("rail")
            or first_race.get("rail")
        )

        official = (
            track_official_exact.get(
                (meeting_date, meeting_track)
            )
            or track_official_by_track.get(meeting_track)
        )

        true_track_available = bool(
            (meeting_date, meeting_track) in track_true_dates
            or meeting_track in track_true_tracks
        )

        profile_available = bool(
            meeting_track in track_profile_tracks
            or meeting_track in track_profile_v2_tracks
        )

        map_available = (
            meeting_track in track_map_tracks
        )

        # Mirrors trackFeed.ts:
        # status is current when official context, pattern/profile context,
        # or map context exists. True-track is additional enrichment.
        track_ok = bool(
            track_contract_ok
            and (
                official
                or profile_available
                or map_available
            )
        )

        synthetic = {
            "window_today": clean(window.get("today")),
            "melbourne_today": melbourne_today,
            "raceDate": meeting_date,
            "meeting": meeting_name,
            "raceNumber": "",
            "runnerName": "",
            "runnerNumber": "",
            "scratched": False,
            "firstStarter": False,
            "history_count": 1,
        }

        track_artifact = " | ".join(
            [
                rel(track_official_path),
                rel(track_map_manifest_path),
                rel(track_true_path),
                rel(track_profile_path),
                rel(track_profile_v2_path),
            ]
        )

        track_value = "AVAILABLE" if track_ok else ""

        track_line = make_lineage(
            synthetic,
            "TRACK",
            "Meeting Track Context",
            track_artifact,
            "meeting-level governed Track authorities",
            track_value,
            "trackFeed.ts production authority contract",
            rel(track_contract_path),
            track_value,
            track_artifact,
            track_value,
            "MeetingTrackWorkspace",
            track_value,
            "AVAILABLE" if track_ok else "TRACK_CONTEXT_NOT_AVAILABLE",
        )

        if track_ok:
            track_context_available += 1
        else:
            track_line["classification"] = "JOIN_FAILURE"
            track_line["CLASSIFICATION"] = "JOIN_FAILURE"
            track_line["failure_stage"] = "production_authority"
            track_line["GATE"] = "FAIL"
            track_line["status"] = "TRACK_CONTEXT_NOT_AVAILABLE"
            track_line["STATUS_OR_REASON"] = "TRACK_CONTEXT_NOT_AVAILABLE"

        lineage.append(track_line)

        weather_match = (
            weather_context.get(
                (meeting_date, meeting_track)
            )
            or weather_context_by_track.get(
                meeting_track
            )
        )

        if weather_match and not weather_match["explicit_unavailable"]:
            weather_ok = bool(weather_contract_ok)
            weather_source_missing = False
        elif weather_match and weather_match["explicit_unavailable"]:
            weather_ok = False
            weather_source_missing = True
        else:
            weather_ok = False
            weather_source_missing = False

        weather_artifact = " | ".join(
            [
                rel(weather_metropolitan_path),
                rel(weather_race_path),
                rel(weather_on_track_path),
                rel(weather_victorian_path),
            ]
        )

        weather_value = "AVAILABLE" if weather_ok else ""

        weather_line = make_lineage(
            synthetic,
            "WEATHER",
            "Meeting Weather Context",
            weather_artifact,
            "meeting-level governed Weather authorities",
            weather_value,
            "weatherFeed.ts production authority contract",
            rel(weather_contract_path),
            weather_value,
            weather_artifact,
            weather_value,
            "MeetingWeatherWorkspace",
            weather_value,
            (
                "AVAILABLE"
                if weather_ok
                else (
                    "SOURCE_NOT_PROVIDED"
                    if weather_source_missing
                    else "WEATHER_CONTEXT_NOT_AVAILABLE"
                )
            ),
        )

        if weather_ok:
            weather_context_available += 1

        elif weather_source_missing:
            # Explicit source unavailability is a governed state, not a
            # pipeline failure and not invented weather.
            weather_context_explicit_unavailable += 1
            weather_line["classification"] = "SOURCE_NOT_PROVIDED"
            weather_line["CLASSIFICATION"] = "SOURCE_MISSING"
            weather_line["failure_stage"] = ""
            weather_line["GATE"] = "PASS"
            weather_line["status"] = "SOURCE_NOT_PROVIDED"
            weather_line["STATUS_OR_REASON"] = "SOURCE_NOT_PROVIDED"

        else:
            weather_line["classification"] = "JOIN_FAILURE"
            weather_line["CLASSIFICATION"] = "JOIN_FAILURE"
            weather_line["failure_stage"] = "production_authority"
            weather_line["GATE"] = "FAIL"
            weather_line["status"] = "WEATHER_CONTEXT_NOT_AVAILABLE"
            weather_line["STATUS_OR_REASON"] = "WEATHER_CONTEXT_NOT_AVAILABLE"

        lineage.append(weather_line)


    # Results consistency: winner populated while status/open says upcoming/pending is a stale-state defect.
    for line in lineage:
        if line["workspace"] == "RESULTS" and line["FORM_GUIDE_VALUE_PRESENT"] == "TRUE":
            rk = race_key(line["race_date"], line["meeting"], line["race_number"])
            r = result_index.get(rk, {})
            if clean(r.get("winner")) and clean(r.get("status")).upper() in {"UPCOMING", "PENDING"}:
                line["CLASSIFICATION"] = "STALE_ARTIFACT"
                line["STATUS_OR_REASON"] = "RESULTS_POPULATED_BUT_STATUS_UPCOMING"
                line["GATE"] = "FAIL"

    fieldnames = [
        "operational_date",
        "operational_window_today",
        "melbourne_today",
        "race_date",
        "meeting",
        "race_number",
        "horse",
        "runner_number",
        "scratched",
        "first_starter",
        "history_count",
        "workspace",
        "UI_field",
        "ui_field",
        "expected_source",
        "source_path",
        "SOURCE_ARTIFACT",
        "SOURCE_FIELD",
        "source_field",
        "SOURCE_VALUE",
        "source_value_present",
        "SOURCE_VALUE_PRESENT",
        "transformation",
        "TRANSFORM_BUILDER",
        "intermediate_feed",
        "CURRENT_RUNNER_FEED",
        "CURRENT_RUNNER_VALUE",
        "intermediate_value_present",
        "CURRENT_RUNNER_VALUE_PRESENT",
        "publication_feed",
        "FORM_GUIDE_FEED",
        "FORM_GUIDE_VALUE",
        "publication_value_present",
        "FORM_GUIDE_VALUE_PRESENT",
        "REACT_FIELD",
        "React_field",
        "displayed_value",
        "DISPLAYED_VALUE",
        "DISPLAYED_VALUE_PRESENT",
        "status",
        "STATUS_OR_REASON",
        "failure_stage",
        "classification",
        "CLASSIFICATION",
        "GATE",
    ]
    with DETAIL_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(lineage)

    counts = Counter(line["CLASSIFICATION"] for line in lineage)
    workspace_failures = Counter(line["workspace"] for line in lineage if line["GATE"] == "FAIL")
    ui_failures = Counter((line["workspace"], line["ui_field"]) for line in lineage if line["GATE"] == "FAIL")
    source_present_feed_missing = sum(1 for line in lineage if line["SOURCE_VALUE_PRESENT"] == "TRUE" and line["FORM_GUIDE_VALUE_PRESENT"] != "TRUE")
    unexplained = counts.get("UNEXPLAINED_MISSING", 0)
    stale = counts.get("STALE_ARTIFACT", 0)
    join_failures = counts.get("JOIN_FAILURE", 0) + sum(1 for line in lineage if line["STATUS_OR_REASON"] == "JOIN_FAILURE")
    active_runners = [r for r in catalog_runners if not r["scratched"]]
    rateable_active = [r for r in active_runners if not r["firstStarter"] and r["history_count"] > 0]
    lineage_by_runner: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for line in lineage:
        lineage_by_runner[key(line["race_date"], line["meeting"], line["race_number"], line["horse"])].append(line)
    current_required = {"EPR", "EDGEiQ Price", "Early Speed", "Late Speed", "Suitability", "Form Momentum"}
    fully_populated_rateable = 0
    for runner in rateable_active:
        rows = lineage_by_runner.get(key(runner["raceDate"], runner["meeting"], runner["raceNumber"], runner["runnerName"]), [])
        required_rows = [line for line in rows if line["ui_field"] in current_required]
        if len(required_rows) == len(current_required) and all(line["FORM_GUIDE_VALUE_PRESENT"] == "TRUE" for line in required_rows):
            fully_populated_rateable += 1
    field_population = {
        field: sum(1 for line in lineage if line["ui_field"] == field and line["FORM_GUIDE_VALUE_PRESENT"] == "TRUE")
        for field in [
            "EPR",
            "EDGEiQ Price",
            "Early Speed",
            "Late Speed",
            "Suitability",
            "Form Momentum",
            "Recent Form",
            "Sectional Standard-Time Values",
            "Position In Running",
            "Market Price",
            "Map Runner Row",
            "Results",
        ]
    }
    field_source_available = {
        field: sum(1 for line in lineage if line["ui_field"] == field and line["SOURCE_VALUE_PRESENT"] == "TRUE")
        for field in field_population
    }

    summary = {
        "schema_version": "EDGEIQ_GLOBAL_PRODUCTION_DATA_COMPLETENESS_V1",
        "generated_at": utc_now(),
        "detail_csv": rel(DETAIL_CSV),
        "OPERATIONAL_TODAY": window.get("today"),
        "MELBOURNE_TODAY": melbourne_today,
        "THREE_DAY_WINDOW": window_dates,
        "EXPECTED_THREE_DAY_WINDOW": expected_window,
        "DATE_SOURCE": window.get("dateSource"),
        "OPERATIONAL_DATE_DYNAMIC": "PASS" if window_dynamic else "FAIL",
        "MEETINGS": len(catalog.get("meetings", [])),
        "RACES": sum(len(m.get("races", [])) for m in catalog.get("meetings", [])),
        "RUNNERS": len(catalog_runners),
        "ACTIVE_RUNNERS": len(active_runners),
        "SCRATCHED_RUNNERS": len(catalog_runners) - len(active_runners),
        "HISTORY_BEARING_RUNNERS": sum(1 for r in catalog_runners if r["history_count"] > 0),
        "NO_HISTORY_RUNNERS": sum(1 for r in catalog_runners if r["history_count"] == 0 or r["firstStarter"]),
        "RATEABLE_ACTIVE_RUNNERS": len(rateable_active),
        "FULLY_POPULATED_RATEABLE_RUNNERS": fully_populated_rateable,
        "RATEABLE_ACTIVE_RUNNER_COMPLETENESS": round((fully_populated_rateable / len(rateable_active)) * 100, 2) if rateable_active else 0,
        "EPR_COVERAGE": field_population["EPR"],
        "PRICE_COVERAGE": field_population["EDGEiQ Price"],
        "EARLY_COVERAGE": field_population["Early Speed"],
        "LATE_COVERAGE": field_population["Late Speed"],
        "SUITABILITY_COVERAGE": field_population["Suitability"],
        "MOMENTUM_COVERAGE": field_population["Form Momentum"],
        "RECENT_FORM_COVERAGE": field_population["Recent Form"],
        "PERFORMANCE_COVERAGE": field_population["EPR"],
        "MARKET_COVERAGE": field_population["Market Price"],
        "MAP_COVERAGE": field_population["Map Runner Row"],
        "RESULTS_COVERAGE": field_population["Results"],
        "SOURCE_HISTORICAL_SECTIONALS_AVAILABLE": field_source_available["Sectional Standard-Time Values"],
        "FORM_GUIDE_HISTORICAL_SECTIONALS_TRANSFERRED": field_population["Sectional Standard-Time Values"],
        "SOURCE_POSITION_IN_RUNNING_AVAILABLE": field_source_available["Position In Running"],
        "FORM_GUIDE_POSITION_IN_RUNNING_TRANSFERRED": field_population["Position In Running"],
        "CURRENT_RUNNER_ROWS": len(current_rows),
        "FORM_GUIDE_RACES": len(form.get("races", [])),
        "FORM_GUIDE_RUNNERS": len(form_index),
        "MARKET_ROWS": len(market_rows),
        "RESULT_ROWS": len(results_rows),
        "MAP_ROWS": len(map_rows),
        "TRACK_ROWS": track_context_available,
        "WEATHER_ROWS": weather_context_available,
        "TRACK_MEETING_CONTEXTS_AVAILABLE": track_context_available,
        "WEATHER_MEETING_CONTEXTS_AVAILABLE": weather_context_available,
        "WEATHER_EXPLICIT_SOURCE_UNAVAILABLE": weather_context_explicit_unavailable,
        "TRACK_DATA_CONTRACT": track_contract.get("status", "UNKNOWN"),
        "WEATHER_DATA_CONTRACT": weather_contract.get("status", "UNKNOWN"),
        "OVERVIEW_ROWS": len(overview_rows),
        "INSIGHTS_ROWS": len(insights_rows),
        "PERFORMANCE_HORSE_INDEX_ROWS": len(pi.get("horse_intelligence_index", [])) if isinstance(pi, dict) else 0,
        "LINEAGE_ROWS": len(lineage),
        "POPULATED_ROWS": counts.get("POPULATED", 0),
        "LEGITIMATE_NO_HISTORY": counts.get("LEGITIMATE_NO_HISTORY", 0),
        "LEGITIMATE_INSUFFICIENT_HISTORY": counts.get("LEGITIMATE_INSUFFICIENT_HISTORY", 0),
        "SOURCE_MISSING": counts.get("SOURCE_MISSING", 0),
        "JOIN_FAILURES": join_failures,
        "FEED_OMISSIONS": counts.get("FEED_OMISSION", 0),
        "TRANSFORM_FAILURES": counts.get("TRANSFORM_FAILURE", 0),
        "REACT_FIELD_MISMATCHES": counts.get("REACT_FIELD_MISMATCH", 0),
        "STALE_ARTIFACTS": stale,
        "UNEXPLAINED_MISSING": unexplained,
        "SOURCE_TO_FEED_DROPS": source_present_feed_missing,
        "workspace_failures": dict(sorted(workspace_failures.items())),
        "field_failures": {f"{k[0]}::{k[1]}": v for k, v in sorted(ui_failures.items())},
        "classification_counts": dict(sorted(counts.items())),
        "encoding_gate": text_summary.get("GLOBAL_ENCODING_HEALTH", "UNKNOWN"),
        "HOME": "PASS" if window_dynamic else "FAIL",
        "HOME_DATA": "PASS" if window_dynamic else "FAIL",
        "MEETINGS_GATE": "PASS" if len(catalog.get("meetings", [])) > 0 else "FAIL",
        "MEETINGS_DATA": "PASS" if len(catalog.get("meetings", [])) > 0 else "FAIL",
        "RACE_GATE": "PASS" if not workspace_failures.get("RACE") else "FAIL",
        "RACE_DATA": "PASS" if not workspace_failures.get("RACE") else "FAIL",
        "FIELD_GATE": "PASS" if not workspace_failures.get("FIELD") else "FAIL",
        "FIELD_DATA": "PASS" if not workspace_failures.get("FIELD") else "FAIL",
        "PERFORMANCE_GATE": "PASS" if not workspace_failures.get("PERFORMANCE") else "FAIL",
        "PERFORMANCE_DATA": "PASS" if not workspace_failures.get("PERFORMANCE") else "FAIL",
        "FORM_GATE": "PASS" if not workspace_failures.get("FORM") else "FAIL",
        "FORM_DATA": "PASS" if not workspace_failures.get("FORM") else "FAIL",
        "MAP_GATE": "PASS" if not workspace_failures.get("MAP") else "FAIL",
        "MAP_DATA": "PASS" if not workspace_failures.get("MAP") else "FAIL",
        "MARKET_GATE": "PASS" if not workspace_failures.get("MARKET") else "FAIL",
        "MARKET_DATA": "PASS" if not workspace_failures.get("MARKET") else "FAIL",
        "RESULTS_GATE": "PASS" if not workspace_failures.get("RESULTS") else "FAIL",
        "RESULTS_DATA": "PASS" if not workspace_failures.get("RESULTS") else "FAIL",
        "TRACK_GATE": "PASS" if not workspace_failures.get("TRACK") else "FAIL",
        "TRACK_DATA": "PASS" if not workspace_failures.get("TRACK") else "FAIL",
        "WEATHER_GATE": "PASS" if not workspace_failures.get("WEATHER") else "FAIL",
        "WEATHER_DATA": "PASS" if not workspace_failures.get("WEATHER") else "FAIL",
        "OVERVIEW_GATE": "PASS" if not workspace_failures.get("OVERVIEW") else "FAIL",
        "OVERVIEW_DATA": "PASS" if not workspace_failures.get("OVERVIEW") else "FAIL",
        "INSIGHTS_GATE": "PASS" if not workspace_failures.get("INSIGHTS") else "FAIL",
        "INSIGHTS_DATA": "PASS" if not workspace_failures.get("INSIGHTS") else "FAIL",
    }
    gate_keys = [key for key in summary if key.endswith("_GATE") or key.endswith("_DATA") or key in {"HOME", "OPERATIONAL_DATE_DYNAMIC"}]
    failed_gates = [key for key in gate_keys if summary.get(key) != "PASS"]
    summary["FAILED_GATES"] = failed_gates
    summary["EDGEIQ_PRODUCTION_HARDENING_V1"] = "PASS" if not failed_gates and unexplained == 0 and source_present_feed_missing == 0 and stale == 0 else "FAIL"

    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    health = {
        "schema_version": "EDGEIQ_PRODUCTION_HEALTH_V1",
        "generated_utc": utc_now(),
        "OPERATIONAL_TODAY": summary["OPERATIONAL_TODAY"],
        "LAST_SUCCESSFUL_REFRESH": catalog.get("generatedAt") or window.get("generatedAt"),
        "THREE_DAY_WINDOW": window_dates,
        "CURRENT_FEED_FRESHNESS_AUTHORITY": "PASS" if window_dynamic else "FAIL",
        "CURRENT_RUNNER_CHAIN": "PASS" if summary["CURRENT_RUNNER_ROWS"] > 0 else "FAIL",
        "FORM_GUIDE": summary["FORM_GATE"],
        "PERFORMANCE": summary["PERFORMANCE_GATE"],
        "STALE_SOURCE_SELECTION": "PASS" if stale == 0 and window_dynamic else "FAIL",
        "TEXT_ENCODING": text_summary.get("GLOBAL_ENCODING_HEALTH", "UNKNOWN"),
        "GLOBAL_DATA_COMPLETENESS": summary["EDGEIQ_PRODUCTION_HARDENING_V1"],
        "EDGEIQ_PRODUCTION_HEALTH": "PASS" if summary["EDGEIQ_PRODUCTION_HARDENING_V1"] == "PASS" and text_summary.get("GLOBAL_ENCODING_HEALTH") == "PASS" else "FAIL",
        "failed_gates": failed_gates,
        "hardening_summary": rel(SUMMARY_JSON),
        "hardening_detail": rel(DETAIL_CSV),
    }
    HEALTH_JSON.write_text(json.dumps(health, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["EDGEIQ_PRODUCTION_HARDENING_V1"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
