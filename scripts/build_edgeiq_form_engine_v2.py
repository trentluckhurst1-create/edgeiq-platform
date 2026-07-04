from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path

from edgeiq_csv_utils import build_lookup, clean, first, num, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
VALIDATION = DATA / "edgeiq_sectional_validation_engine.csv"
NORMALISATION = DATA / "edgeiq_sectional_normalisation_v1.csv"
TRUSTED = DATA / "edgeiq_trusted_sectional_universe.csv"
IDENTITY_V3 = DATA / "edgeiq_sectional_identity_engine_v3.csv"
OUT = DATA / "edgeiq_form_engine_v2.csv"

SOURCE_FILES = [
    "edgeiq_active_form_bridge_v1.csv", "edgeiq_active_runner_form_truth_v1.csv",
    "edgeiq_live_form_context_v1.csv", "edgeiq_official_runs_master_v1.csv",
    "edgeiq_form_depth_ability_v2.csv", "edgeiq_runner_intelligence_v1.csv",
    "edgeiq_horse_energy_profile_v1.csv",
]

FIELDS = [
    "built_at", "race_date", "track", "race_no", "horse", "horse_key", "last_5",
    "avg_last_3", "avg_last_5", "peak_rating", "days_since_run", "career_record",
    "track_record", "distance_record", "condition_record", "class_move",
    "last_start_summary", "form_confidence", "sectional_quality_grade",
    "sectional_confidence", "normalised_late_speed", "normalised_sustained_speed",
    "fatigue_index", "sectional_rating", "sectional_identity_status",
    "sectional_match_confidence", "trusted_sectional_flag", "field_composition_confidence",
    "identity_v2_status", "identity_v3_status", "runner_entity_confidence",
    "trusted_identity_flag", "trusted_runner_identity", "trusted_modelling_identity",
]


def now_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def valid_date(row: dict[str, str]) -> bool:
    raw = clean(row.get("race_date"))
    if not raw:
        return True
    try:
        race_date = datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return True
    today = datetime.now().astimezone().date()
    return today <= race_date <= today + timedelta(days=2)


def form_string(row: dict[str, str]) -> str:
    return first(row, ["last_5", "last5", "form_string", "recent_form", "horse_form", "official_form", "form"])


def rating(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        parsed = num(row.get(name))
        if not math.isnan(parsed):
            return f"{parsed:.1f}"
    return ""


def record(row: dict[str, str], names: list[str]) -> str:
    return first(row, names)


def summary(row: dict[str, str]) -> str:
    supplied = first(row, ["last_start_summary", "last_start", "recent_run_summary", "comment", "comments"])
    if supplied:
        return supplied
    pieces = [piece for piece in [first(row, ["last_start_finish", "last_finish", "finish_position"]), first(row, ["last_start_track", "last_track"]), first(row, ["last_start_distance", "last_distance"]), rating(row, ["last_start_rating", "last_rating", "run_rating"])] if piece]
    return " / ".join(pieces)


def confidence(row: dict[str, str]) -> str:
    supplied = first(row, ["form_confidence", "confidence", "match_confidence", "form_quality"])
    if supplied:
        return supplied
    present = sum(1 for value in [form_string(row), rating(row, ["avg_last_3", "last3_avg", "average_last_3"]), rating(row, ["avg_last_5", "last5_avg", "average_last_5"]), rating(row, ["peak_rating", "peak", "best_rating"]), first(row, ["days_since_run", "days_since_last_run", "gap"]), record(row, ["career_record", "career"])] if value)
    if present >= 5:
        return "HIGH"
    if present >= 3:
        return "MEDIUM"
    if present:
        return "LOW"
    return "UNMAPPED"


def merge_sources(base: dict[str, str], maps: list[dict[str, dict[str, str]]]) -> dict[str, str]:
    merged = dict(base)
    key = runner_key(base)
    for mapping in maps:
        extra = mapping.get(key)
        if not extra:
            continue
        for col, value in extra.items():
            if clean(value) and not clean(merged.get(col)):
                merged[col] = value
            elif clean(value):
                merged[f"{col}_extra"] = value
    return merged


def sectional_values(base: dict[str, str], validation_map: dict[str, dict[str, str]], normalisation_map: dict[str, dict[str, str]], trusted_map: dict[str, dict[str, str]], identity_v3_map: dict[str, dict[str, str]]) -> dict[str, str]:
    key = runner_key(base)
    validation = validation_map.get(key, {})
    normalisation = normalisation_map.get(key, {})
    trusted = trusted_map.get(key, {})
    identity = identity_v3_map.get(key, {})
    trusted_flag = "YES" if clean(trusted.get("trusted_for_modelling")).upper() == "YES" else "PARTIAL" if clean(trusted.get("trusted_for_modelling")).upper() == "PARTIAL" else ""
    return {
        "sectional_quality_grade": first(trusted, ["sectional_quality_grade"]) or first(validation, ["sectional_quality_grade"]),
        "sectional_confidence": first(trusted, ["sectional_confidence"]) or first(validation, ["sectional_confidence"]),
        "normalised_late_speed": first(normalisation, ["normalised_late_speed"]),
        "normalised_sustained_speed": first(normalisation, ["normalised_sustained_speed"]),
        "fatigue_index": first(normalisation, ["fatigue_index"]),
        "sectional_rating": first(normalisation, ["sectional_rating"]),
        "sectional_identity_status": first(trusted, ["identity_status"]) or first(identity, ["identity_v3_status"]),
        "sectional_match_confidence": first(trusted, ["identity_v3_confidence", "match_confidence"]) or first(identity, ["identity_v3_confidence"]),
        "trusted_sectional_flag": trusted_flag,
        "field_composition_confidence": first(trusted, ["field_composition_confidence"]) or first(identity, ["field_composition_confidence"]),
        "identity_v2_status": first(trusted, ["identity_v2_status"]) or first(identity, ["identity_v2_status"]),
        "identity_v3_status": first(trusted, ["identity_v3_status"]) or first(identity, ["identity_v3_status"]),
        "runner_entity_confidence": first(trusted, ["runner_entity_confidence"]) or first(identity, ["runner_entity_confidence"]),
        "trusted_identity_flag": first(trusted, ["trusted_modelling_identity"]) or first(identity, ["trusted_modelling_identity"]),
        "trusted_runner_identity": first(trusted, ["trusted_runner_identity"]) or first(identity, ["trusted_runner_identity"]),
        "trusted_modelling_identity": first(trusted, ["trusted_modelling_identity"]) or first(identity, ["trusted_modelling_identity"]),
    }


def main() -> None:
    universe = [row for row in read_csv(UNIVERSE) if valid_date(row)]
    maps = [build_lookup(read_csv(DATA / filename)) for filename in SOURCE_FILES]
    validation_map = build_lookup(read_csv(VALIDATION))
    normalisation_map = build_lookup(read_csv(NORMALISATION))
    trusted_map = build_lookup([row for row in read_csv(TRUSTED) if clean(row.get("trusted_for_modelling")).upper() == "YES"])
    identity_v3_map = build_lookup(read_csv(IDENTITY_V3))
    built_at = now_stamp()
    out: list[dict[str, object]] = []
    for base in universe:
        row = merge_sources(base, maps)
        sectionals = sectional_values(base, validation_map, normalisation_map, trusted_map, identity_v3_map)
        out.append({
            "built_at": built_at, "race_date": first(row, ["race_date", "date"]), "track": first(row, ["track", "meeting"]),
            "race_no": first(row, ["race_no", "race_number"]), "horse": first(row, ["horse", "runner", "horse_name", "runner_name"]),
            "horse_key": first(row, ["horse_key"]) or runner_key(row).split("|")[-1], "last_5": form_string(row),
            "avg_last_3": rating(row, ["avg_last_3", "last3_avg", "average_last_3", "rating_last_3_avg"]),
            "avg_last_5": rating(row, ["avg_last_5", "last5_avg", "average_last_5", "rating_last_5_avg"]),
            "peak_rating": rating(row, ["peak_rating", "peak", "best_rating", "max_rating"]),
            "days_since_run": first(row, ["days_since_run", "days_since_last_run", "gap", "run_gap_days"]),
            "career_record": record(row, ["career_record", "career", "record", "career_stats"]),
            "track_record": record(row, ["track_record", "track_stats", "course_record"]),
            "distance_record": record(row, ["distance_record", "distance_stats", "dist_record"]),
            "condition_record": record(row, ["condition_record", "wet_record", "going_record", "track_condition_record"]),
            "class_move": record(row, ["class_move", "class_change", "grade_move"]),
            "last_start_summary": summary(row), "form_confidence": confidence(row), **sectionals,
        })
    write_csv(OUT, out, FIELDS)
    print("=" * 90)
    print("EDGEIQ FORM ENGINE V2")
    print("=" * 90)
    print("ROWS:", len(out))
    print("WITH TRUSTED SECTIONALS:", sum(1 for row in out if clean(row.get("trusted_sectional_flag")) == "YES"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
