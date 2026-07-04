from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Callable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT_PATH = DATA / "edgeiq_intelligence_ui_population_audit_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_intelligence_ui_population_audit_summary_v1.csv"

FILES = {
    "live_runner_board": DATA / "edgeiq_live_runner_board_v1.csv",
    "runner_intelligence": DATA / "edgeiq_runner_intelligence_v1.csv",
    "horse_drawer": DATA / "edgeiq_horse_intelligence_drawer_current.csv",
    "runner_dna_drawer": DATA / "edgeiq_runner_dna_drawer_feed_v2.csv",
    "connection_intelligence": DATA / "edgeiq_connection_intelligence_v1.csv",
    "explainability_terminal": DATA / "edgeiq_explainability_terminal_feed_v1_2.csv",
    "runner_profile_engine": DATA / "edgeiq_runner_profile_engine_current.csv",
    "runner_form_engine": DATA / "edgeiq_runner_form_engine_current.csv",
    "runner_form_history": DATA / "runner_form_history.csv",
    "runner_history_detail": DATA / "edgeiq_runner_history_detail_v1.csv",
    "horse_career_intelligence": DATA / "edgeiq_horse_career_intelligence_v1.csv",
    "horse_archetype_engine": DATA / "edgeiq_horse_archetype_engine_v1.csv",
    "horse_trajectory_engine": DATA / "edgeiq_horse_trajectory_engine_v1.csv",
    "horse_projection_engine": DATA / "edgeiq_horse_projection_engine_v1.csv",
    "factor_scorecard": DATA / "edgeiq_live_runner_factor_scorecard_v2.csv",
}

SOURCE_ALIAS = {
    "runner_intelligence": "runner_intelligence",
    "horse_drawer": "horse_drawer",
    "runner_dna_drawer": "runner_dna_drawer",
    "connection_intelligence": "connection_intelligence",
    "explainability_terminal": "explainability_terminal",
    "runner_profile": "runner_profile_engine",
    "runner_form": "runner_form_engine",
    "runner_form_history": "runner_form_history",
    "history_detail": "runner_history_detail",
    "horse_career": "horse_career_intelligence",
    "horse_archetype": "horse_archetype_engine",
    "horse_trajectory": "horse_trajectory_engine",
    "horse_projection": "horse_projection_engine",
    "factor_scorecard": "factor_scorecard",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse(value: object) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    text = re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", text)
    return text


def first_present(record: dict[str, str], columns: list[str]) -> str:
    for column in columns:
        value = clean_text(record.get(column, ""))
        if value:
            return value
    return ""


def truthy_flag(value: object) -> bool:
    return clean_text(value).upper() in {"1", "TRUE", "YES", "Y", "SCRATCHED"}


def parse_float(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace("%", "").replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_int(value: object) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    return int(round(number))


def meaningful(value: object) -> bool:
    text = clean_text(value)
    if not text:
        return False
    return text.upper() not in {"--", "N/A", "NA", "NO DATA", "NONE", "UNKNOWN", "PENDING"}


def is_populated_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return meaningful(value)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def prepare_records(df: pd.DataFrame) -> list[dict[str, str]]:
    if df.empty:
        return []
    prepared = df.copy()
    prepared["race_date_norm"] = prepared.apply(
        lambda row: first_present(row.to_dict(), ["race_date", "meeting_date", "run_date_iso", "run_date"]),
        axis=1,
    )
    prepared["track_norm"] = prepared.apply(
        lambda row: normalize_track(first_present(row.to_dict(), ["track", "meeting", "meeting_name"])),
        axis=1,
    )
    prepared["race_no_norm"] = prepared.apply(
        lambda row: first_present(row.to_dict(), ["race_no", "race_number", "race"]),
        axis=1,
    )
    prepared["horse_key_norm"] = prepared.apply(
        lambda row: normalize_horse(first_present(row.to_dict(), ["horse_key", "runner_key", "horse"])),
        axis=1,
    )
    prepared["horse_norm"] = prepared.apply(
        lambda row: normalize_horse(first_present(row.to_dict(), ["horse", "runner", "runner_name"])),
        axis=1,
    )
    prepared["runner_key_norm"] = prepared.apply(
        lambda row: normalize_horse(first_present(row.to_dict(), ["runner_key", "horse_key", "horse"])),
        axis=1,
    )
    return prepared.to_dict("records")


def active_base_rows() -> list[dict[str, str]]:
    df = load_csv(FILES["live_runner_board"])
    if df.empty:
        raise ValueError("edgeiq_live_runner_board_v1.csv is missing or empty.")

    rows = prepare_records(df)
    active = []
    for row in rows:
        scratched = (
            clean_text(row.get("runner_status", "")).upper() == "SCRATCHED"
            or truthy_flag(row.get("is_scratched", ""))
            or "SCRATCH" in clean_text(row.get("scratch_status", "")).upper()
        )
        if scratched:
            continue
        active.append(row)
    return active


def build_maps(records: list[dict[str, str]]) -> dict[str, dict[str, list[dict[str, str]]]]:
    maps: dict[str, dict[str, list[dict[str, str]]]] = {
        "DATE_TRACK_RACE_NO_RUNNER_KEY": {},
        "DATE_TRACK_RACE_NO_HORSE_KEY": {},
        "DATE_TRACK_RACE_NO_HORSE": {},
        "TRACK_RACE_NO_HORSE_KEY": {},
        "TRACK_RACE_NO_HORSE": {},
        "HORSE_KEY_ONLY": {},
    }

    for record in records:
        keys = {
            "DATE_TRACK_RACE_NO_RUNNER_KEY": [record.get("race_date_norm", ""), record.get("track_norm", ""), record.get("race_no_norm", ""), record.get("runner_key_norm", "")],
            "DATE_TRACK_RACE_NO_HORSE_KEY": [record.get("race_date_norm", ""), record.get("track_norm", ""), record.get("race_no_norm", ""), record.get("horse_key_norm", "")],
            "DATE_TRACK_RACE_NO_HORSE": [record.get("race_date_norm", ""), record.get("track_norm", ""), record.get("race_no_norm", ""), record.get("horse_norm", "")],
            "TRACK_RACE_NO_HORSE_KEY": [record.get("track_norm", ""), record.get("race_no_norm", ""), record.get("horse_key_norm", "")],
            "TRACK_RACE_NO_HORSE": [record.get("track_norm", ""), record.get("race_no_norm", ""), record.get("horse_norm", "")],
            "HORSE_KEY_ONLY": [record.get("horse_key_norm", "")],
        }
        for name, parts in keys.items():
            if all(parts):
                key = "|".join(parts)
                maps[name].setdefault(key, []).append(record)
    return maps


def source_bundle(name: str) -> dict[str, object]:
    path = FILES[name]
    df = load_csv(path)
    records = prepare_records(df)
    return {
        "name": name,
        "path": path,
        "exists": path.exists(),
        "columns": list(df.columns) if not df.empty else [],
        "records": records,
        "maps": build_maps(records),
    }


def match_records(base_row: dict[str, str], bundle: dict[str, object]) -> list[dict[str, str]]:
    maps = bundle["maps"]
    checks = [
        ("DATE_TRACK_RACE_NO_RUNNER_KEY", [base_row.get("race_date_norm", ""), base_row.get("track_norm", ""), base_row.get("race_no_norm", ""), base_row.get("runner_key_norm", "")]),
        ("DATE_TRACK_RACE_NO_HORSE_KEY", [base_row.get("race_date_norm", ""), base_row.get("track_norm", ""), base_row.get("race_no_norm", ""), base_row.get("horse_key_norm", "")]),
        ("DATE_TRACK_RACE_NO_HORSE", [base_row.get("race_date_norm", ""), base_row.get("track_norm", ""), base_row.get("race_no_norm", ""), base_row.get("horse_norm", "")]),
        ("TRACK_RACE_NO_HORSE_KEY", [base_row.get("track_norm", ""), base_row.get("race_no_norm", ""), base_row.get("horse_key_norm", "")]),
        ("TRACK_RACE_NO_HORSE", [base_row.get("track_norm", ""), base_row.get("race_no_norm", ""), base_row.get("horse_norm", "")]),
        ("HORSE_KEY_ONLY", [base_row.get("horse_key_norm", "")]),
    ]
    for method, parts in checks:
        if all(parts):
            key = "|".join(parts)
            hits = maps.get(method, {}).get(key, [])
            if hits:
                return hits
    return []


def factor_row(rows: list[dict[str, str]], factor_name: str) -> dict[str, str] | None:
    for row in rows:
        if clean_text(row.get("factor", "")).upper() == factor_name.upper():
            return row
    return None


def latest_history_rating(joined: dict[str, object]) -> float | None:
    history = joined["history_detail"]
    if history:
        ranked = sorted(history, key=lambda row: clean_text(row.get("run_date_iso", "")), reverse=True)
        for row in ranked:
            value = parse_float(first_present(row, ["run_rating_final", "run_rating", "performance_rating", "recovered_rating"]))
            if value is not None:
                return value
    runner_form = joined["runner_form"]
    return parse_float(first_present(runner_form, ["last_start_rating", "rating_1"])) if runner_form else None


def avg5_rating(joined: dict[str, object]) -> float | None:
    runner_form = joined["runner_form"]
    if runner_form:
        value = parse_float(first_present(runner_form, ["avg_rating_last5"]))
        if value is not None:
            return value
    history = joined["history_detail"]
    ratings = []
    if history:
        ranked = sorted(history, key=lambda row: clean_text(row.get("run_date_iso", "")), reverse=True)
        for row in ranked[:5]:
            value = parse_float(first_present(row, ["run_rating_final", "run_rating", "performance_rating", "recovered_rating"]))
            if value is not None:
                ratings.append(value)
    if ratings:
        return sum(ratings) / len(ratings)
    return None


def peak5_rating(joined: dict[str, object]) -> float | None:
    runner_form = joined["runner_form"]
    if runner_form:
        value = parse_float(first_present(runner_form, ["best_rating_last5", "peak_rating"]))
        if value is not None:
            return value
    history = joined["history_detail"]
    ratings = []
    if history:
        for row in history:
            value = parse_float(first_present(row, ["run_rating_final", "run_rating", "performance_rating", "recovered_rating"]))
            if value is not None:
                ratings.append(value)
    return max(ratings) if ratings else None


def projected_speed_value(joined: dict[str, object]) -> float | None:
    return (
        parse_float(first_present(joined["runner_intelligence"], ["projected_spd"]))
        or parse_float(first_present(joined["horse_drawer"], ["projected_spd"]))
        or parse_float(first_present(joined["base"], ["projected_spd", "early_speed_rating"]))
    )


def sectional_value(joined: dict[str, object]) -> float | None:
    return (
        parse_float(first_present(joined["runner_intelligence"], ["sectional_weapon_score"]))
        or parse_float(first_present(joined["horse_drawer"], ["sectional_weapon_score"]))
        or parse_float(first_present(joined["base"], ["sectional_weapon_score"]))
    )


def late_power_value(joined: dict[str, object]) -> float | None:
    return (
        parse_float(first_present(joined["runner_intelligence"], ["late_power_index", "late_power_score"]))
        or parse_float(first_present(joined["horse_drawer"], ["late_power_index", "late_power_score"]))
        or parse_float(first_present(joined["base"], ["late_power_index", "late_power_score"]))
    )


def track_fit_value(joined: dict[str, object]) -> float | None:
    return (
        parse_float(first_present(joined["horse_drawer"], ["track_fit_score"]))
        or parse_float(first_present(joined["base"], ["track_fit_score"]))
    )


def trainer_score_value(joined: dict[str, object]) -> float | None:
    factor = factor_row(joined["factor_scorecard"], "TRAINER")
    return (
        parse_float(first_present(factor or {}, ["factor_score"]))
        or parse_float(first_present(joined["runner_intelligence"], ["trainer_score"]))
        or parse_float(first_present(joined["horse_drawer"], ["trainer_score"]))
        or parse_float(first_present(joined["connection_intelligence"], ["trainer_track_sr", "connection_score"]))
    )


def jockey_score_value(joined: dict[str, object]) -> float | None:
    factor = factor_row(joined["factor_scorecard"], "JOCKEY")
    return (
        parse_float(first_present(factor or {}, ["factor_score"]))
        or parse_float(first_present(joined["runner_intelligence"], ["jockey_score"]))
        or parse_float(first_present(joined["horse_drawer"], ["jockey_score"]))
        or parse_float(first_present(joined["connection_intelligence"], ["jockey_track_sr", "connection_score"]))
    )


def connection_score_value(joined: dict[str, object]) -> float | None:
    factor = factor_row(joined["factor_scorecard"], "CONNECTION")
    combo = factor_row(joined["factor_scorecard"], "COMBO")
    return (
        parse_float(first_present(factor or {}, ["factor_score"]))
        or parse_float(first_present(combo or {}, ["factor_score"]))
        or parse_float(first_present(joined["runner_intelligence"], ["connection_score"]))
        or parse_float(first_present(joined["horse_drawer"], ["connection_score"]))
        or parse_float(first_present(joined["connection_intelligence"], ["connection_score", "combo_sr", "combo_track_sr"]))
    )


def pace_value(joined: dict[str, object]) -> float | None:
    factor = factor_row(joined["factor_scorecard"], "PACE")
    return (
        parse_float(first_present(factor or {}, ["factor_score"]))
        or parse_float(first_present(joined["runner_intelligence"], ["tempo_fit", "tactical_score", "projected_spd"]))
        or projected_speed_value(joined)
    )


def joined_rows(base_rows: list[dict[str, str]], bundles: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for base in base_rows:
        rows.append(
            {
                "base": base,
                "runner_intelligence": match_records(base, bundles["runner_intelligence"])[0] if match_records(base, bundles["runner_intelligence"]) else {},
                "horse_drawer": match_records(base, bundles["horse_drawer"])[0] if match_records(base, bundles["horse_drawer"]) else {},
                "runner_dna_drawer": match_records(base, bundles["runner_dna_drawer"])[0] if match_records(base, bundles["runner_dna_drawer"]) else {},
                "connection_intelligence": match_records(base, bundles["connection_intelligence"])[0] if match_records(base, bundles["connection_intelligence"]) else {},
                "explainability_terminal": match_records(base, bundles["explainability_terminal"])[0] if match_records(base, bundles["explainability_terminal"]) else {},
                "runner_profile": match_records(base, bundles["runner_profile_engine"])[0] if match_records(base, bundles["runner_profile_engine"]) else {},
                "runner_form": match_records(base, bundles["runner_form_engine"])[0] if match_records(base, bundles["runner_form_engine"]) else {},
                "runner_form_history": match_records(base, bundles["runner_form_history"]),
                "history_detail": match_records(base, bundles["runner_history_detail"]),
                "horse_career": match_records(base, bundles["horse_career_intelligence"])[0] if match_records(base, bundles["horse_career_intelligence"]) else {},
                "horse_archetype": match_records(base, bundles["horse_archetype_engine"])[0] if match_records(base, bundles["horse_archetype_engine"]) else {},
                "horse_trajectory": match_records(base, bundles["horse_trajectory_engine"])[0] if match_records(base, bundles["horse_trajectory_engine"]) else {},
                "horse_projection": match_records(base, bundles["horse_projection_engine"])[0] if match_records(base, bundles["horse_projection_engine"]) else {},
                "factor_scorecard": match_records(base, bundles["factor_scorecard"]),
            }
        )
    return rows


FieldEvaluator = Callable[[dict[str, object]], object]


def first_numeric_from_base(columns: list[str]) -> FieldEvaluator:
    return lambda joined: parse_float(first_present(joined["base"], columns))


def first_text_from_source(source_key: str, columns: list[str]) -> FieldEvaluator:
    return lambda joined: first_present(joined[source_key], columns)


def any_history_present(joined: dict[str, object]) -> object:
    return len(joined["history_detail"]) or len(joined["runner_form_history"])


FIELD_DEFS: list[dict[str, object]] = [
    {"section": "COMMAND", "field_name": "race_shape", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv", "source_keys": ["explainability_terminal"], "source_columns_checked": "race_shape_label", "evaluator": first_text_from_source("explainability_terminal", ["race_shape_label"])},
    {"section": "COMMAND", "field_name": "tempo", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv", "source_keys": ["explainability_terminal"], "source_columns_checked": "race_tempo", "evaluator": first_text_from_source("explainability_terminal", ["race_tempo"])},
    {"section": "COMMAND", "field_name": "pace_advantage", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv", "source_keys": ["explainability_terminal"], "source_columns_checked": "pace_advantage_runner", "evaluator": first_text_from_source("explainability_terminal", ["pace_advantage_runner"])},
    {"section": "COMMAND", "field_name": "late_power_beneficiary", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv", "source_keys": ["explainability_terminal"], "source_columns_checked": "late_power_beneficiary", "evaluator": first_text_from_source("explainability_terminal", ["late_power_beneficiary"])},
    {"section": "COMMAND", "field_name": "pressure_risk", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv", "source_keys": ["explainability_terminal"], "source_columns_checked": "pressure_risk_runner", "evaluator": first_text_from_source("explainability_terminal", ["pressure_risk_runner"])},
    {"section": "COMMAND", "field_name": "top_win_chance", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "win_pct", "evaluator": first_numeric_from_base(["win_pct", "V6_1_RESEARCH_probability"])},
    {"section": "COMMAND", "field_name": "largest_overlay", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "edge_pct", "evaluator": first_numeric_from_base(["edge_pct", "display_edge_pct"])},
    {"section": "COMMAND", "field_name": "edgeiq_price", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "fair_price|ui_fair_price|display_fair_price", "evaluator": first_numeric_from_base(["fair_price", "ui_fair_price", "display_fair_price"])},
    {"section": "COMMAND", "field_name": "tab_price", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "live_price|display_live_price", "evaluator": first_numeric_from_base(["live_price", "display_live_price"])},
    {"section": "COMMAND", "field_name": "edge", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "edge_pct|display_edge_pct", "evaluator": first_numeric_from_base(["edge_pct", "display_edge_pct"])},
    {"section": "MAP", "field_name": "speed_map_position", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "map_x_pct|settling_band|run_style|speed_map_bucket", "evaluator": lambda joined: first_present(joined["base"], ["map_x_pct", "settling_band", "run_style", "speed_map_bucket"])},
    {"section": "MAP", "field_name": "projected_speed", "source_file": "edgeiq_runner_intelligence_v1.csv|edgeiq_horse_intelligence_drawer_current.csv", "source_keys": ["runner_intelligence", "horse_drawer", "base"], "source_columns_checked": "projected_spd|early_speed_rating", "evaluator": projected_speed_value},
    {"section": "MAP", "field_name": "race_shape_story", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv", "source_keys": ["explainability_terminal"], "source_columns_checked": "race_shape_story", "evaluator": first_text_from_source("explainability_terminal", ["race_shape_story"])},
    {"section": "RUNNERS_RATINGS_TABLE", "field_name": "ls_rating", "source_file": "edgeiq_runner_form_engine_current.csv|edgeiq_runner_history_detail_v1.csv", "source_keys": ["runner_form", "history_detail"], "source_columns_checked": "last_start_rating|rating_1|run_rating_final", "evaluator": latest_history_rating},
    {"section": "RUNNERS_RATINGS_TABLE", "field_name": "avg5_rating", "source_file": "edgeiq_runner_form_engine_current.csv|edgeiq_runner_history_detail_v1.csv", "source_keys": ["runner_form", "history_detail"], "source_columns_checked": "avg_rating_last5|run_rating_final", "evaluator": avg5_rating},
    {"section": "RUNNERS_RATINGS_TABLE", "field_name": "peak_rating", "source_file": "edgeiq_runner_form_engine_current.csv|edgeiq_runner_history_detail_v1.csv", "source_keys": ["runner_form", "history_detail"], "source_columns_checked": "best_rating_last5|peak_rating|run_rating_final", "evaluator": peak5_rating},
    {"section": "RUNNERS_RATINGS_TABLE", "field_name": "form_dot_history", "source_file": "edgeiq_runner_history_detail_v1.csv|runner_form_history.csv", "source_keys": ["history_detail", "runner_form_history"], "source_columns_checked": "run_date_iso|run_rating_final|run_rating", "evaluator": any_history_present},
    {"section": "RUNNERS_RATINGS_TABLE", "field_name": "today_rating", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "projected_rating_V6_1_RESEARCH|projected_rating_v5_2", "evaluator": first_numeric_from_base(["projected_rating_V6_1_RESEARCH", "projected_rating_v5_2"])},
    {"section": "RUNNERS_RATINGS_TABLE", "field_name": "edgeiq_price", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "fair_price|ui_fair_price|display_fair_price", "evaluator": first_numeric_from_base(["fair_price", "ui_fair_price", "display_fair_price"])},
    {"section": "RUNNERS_RATINGS_TABLE", "field_name": "tab_price", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "live_price|display_live_price", "evaluator": first_numeric_from_base(["live_price", "display_live_price"])},
    {"section": "RUNNERS_RATINGS_TABLE", "field_name": "edge", "source_file": "edgeiq_live_runner_board_v1.csv", "source_keys": ["base"], "source_columns_checked": "edge_pct|display_edge_pct", "evaluator": first_numeric_from_base(["edge_pct", "display_edge_pct"])},
    {"section": "RUNNERS_PROFILE", "field_name": "career_intelligence", "source_file": "edgeiq_horse_career_intelligence_v1.csv", "source_keys": ["horse_career"], "source_columns_checked": "peak_rating|career_trend|consistency_score", "evaluator": lambda joined: first_present(joined["horse_career"], ["peak_rating", "career_trend", "consistency_score"])},
    {"section": "RUNNERS_PROFILE", "field_name": "archetype", "source_file": "edgeiq_horse_archetype_engine_v1.csv", "source_keys": ["horse_archetype"], "source_columns_checked": "horse_archetype", "evaluator": first_text_from_source("horse_archetype", ["horse_archetype"])},
    {"section": "RUNNERS_PROFILE", "field_name": "trajectory", "source_file": "edgeiq_horse_trajectory_engine_v1.csv", "source_keys": ["horse_trajectory"], "source_columns_checked": "trajectory_direction|career_phase", "evaluator": first_text_from_source("horse_trajectory", ["trajectory_direction", "career_phase"])},
    {"section": "RUNNERS_PROFILE", "field_name": "projection_outlook", "source_file": "edgeiq_horse_projection_engine_v1.csv", "source_keys": ["horse_projection"], "source_columns_checked": "next_run_projection|projection_band", "evaluator": lambda joined: first_present(joined["horse_projection"], ["next_run_projection", "projection_band"])},
    {"section": "RUNNERS_FORM", "field_name": "form_summary", "source_file": "edgeiq_runner_form_engine_current.csv", "source_keys": ["runner_form"], "source_columns_checked": "last5_summary|form_narrative|form_signal", "evaluator": first_text_from_source("runner_form", ["last5_summary", "form_narrative", "form_signal"])},
    {"section": "RUNNERS_FORM", "field_name": "history_rows", "source_file": "edgeiq_runner_history_detail_v1.csv|runner_form_history.csv", "source_keys": ["history_detail", "runner_form_history"], "source_columns_checked": "run_date_iso", "evaluator": any_history_present},
    {"section": "RUNNERS_CONNECTIONS", "field_name": "trainer_score", "source_file": "edgeiq_live_runner_factor_scorecard_v2.csv|edgeiq_connection_intelligence_v1.csv|edgeiq_runner_intelligence_v1.csv", "source_keys": ["factor_scorecard", "connection_intelligence", "runner_intelligence"], "source_columns_checked": "factor_score[TRAINER]|trainer_track_sr|trainer_score", "evaluator": trainer_score_value},
    {"section": "RUNNERS_CONNECTIONS", "field_name": "jockey_score", "source_file": "edgeiq_live_runner_factor_scorecard_v2.csv|edgeiq_connection_intelligence_v1.csv|edgeiq_runner_intelligence_v1.csv", "source_keys": ["factor_scorecard", "connection_intelligence", "runner_intelligence"], "source_columns_checked": "factor_score[JOCKEY]|jockey_track_sr|jockey_score", "evaluator": jockey_score_value},
    {"section": "RUNNERS_CONNECTIONS", "field_name": "connection_score", "source_file": "edgeiq_live_runner_factor_scorecard_v2.csv|edgeiq_connection_intelligence_v1.csv", "source_keys": ["factor_scorecard", "connection_intelligence"], "source_columns_checked": "factor_score[CONNECTION/COMBO]|connection_score|combo_sr", "evaluator": connection_score_value},
    {"section": "RUNNERS_EXPLAINABILITY", "field_name": "confidence", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv", "source_keys": ["explainability_terminal"], "source_columns_checked": "confidence_band|final_confidence_score", "evaluator": lambda joined: first_present(joined["explainability_terminal"], ["confidence_band", "final_confidence_score"])},
    {"section": "RUNNERS_EXPLAINABILITY", "field_name": "positives", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv|edgeiq_runner_dna_drawer_feed_v2.csv", "source_keys": ["explainability_terminal", "runner_dna_drawer"], "source_columns_checked": "positive_1|positive_1_factor", "evaluator": lambda joined: first_present(joined["explainability_terminal"], ["positive_1"]) or first_present(joined["runner_dna_drawer"], ["positive_1_factor"])},
    {"section": "RUNNERS_EXPLAINABILITY", "field_name": "risks", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv|edgeiq_runner_dna_drawer_feed_v2.csv", "source_keys": ["explainability_terminal", "runner_dna_drawer"], "source_columns_checked": "risk_1|negative_1_factor", "evaluator": lambda joined: first_present(joined["explainability_terminal"], ["risk_1"]) or first_present(joined["runner_dna_drawer"], ["negative_1_factor"])},
    {"section": "RUNNERS_EXPLAINABILITY", "field_name": "why_ranked_here", "source_file": "edgeiq_explainability_terminal_feed_v1_2.csv", "source_keys": ["explainability_terminal"], "source_columns_checked": "why_ranked_here", "evaluator": first_text_from_source("explainability_terminal", ["why_ranked_here"])},
    {"section": "FACTORS", "field_name": "dna_score", "source_file": "edgeiq_runner_dna_drawer_feed_v2.csv", "source_keys": ["runner_dna_drawer"], "source_columns_checked": "dna_v6_2_score", "evaluator": first_text_from_source("runner_dna_drawer", ["dna_v6_2_score"])},
    {"section": "FACTORS", "field_name": "sectionals", "source_file": "edgeiq_runner_intelligence_v1.csv|edgeiq_horse_intelligence_drawer_current.csv|edgeiq_live_runner_board_v1.csv", "source_keys": ["runner_intelligence", "horse_drawer", "base"], "source_columns_checked": "sectional_weapon_score", "evaluator": sectional_value},
    {"section": "FACTORS", "field_name": "late_power", "source_file": "edgeiq_runner_intelligence_v1.csv|edgeiq_horse_intelligence_drawer_current.csv|edgeiq_live_runner_board_v1.csv", "source_keys": ["runner_intelligence", "horse_drawer", "base"], "source_columns_checked": "late_power_index|late_power_score", "evaluator": late_power_value},
    {"section": "FACTORS", "field_name": "pace", "source_file": "edgeiq_live_runner_factor_scorecard_v2.csv|edgeiq_runner_intelligence_v1.csv|edgeiq_live_runner_board_v1.csv", "source_keys": ["factor_scorecard", "runner_intelligence", "base"], "source_columns_checked": "factor_score[PACE]|tempo_fit|projected_spd", "evaluator": pace_value},
    {"section": "FACTORS", "field_name": "track_fit", "source_file": "edgeiq_horse_intelligence_drawer_current.csv|edgeiq_live_runner_board_v1.csv", "source_keys": ["horse_drawer", "base"], "source_columns_checked": "track_fit_score", "evaluator": track_fit_value},
    {"section": "FACTORS", "field_name": "trainer", "source_file": "edgeiq_live_runner_factor_scorecard_v2.csv|edgeiq_connection_intelligence_v1.csv", "source_keys": ["factor_scorecard", "connection_intelligence"], "source_columns_checked": "factor_score[TRAINER]|trainer_track_sr", "evaluator": trainer_score_value},
    {"section": "FACTORS", "field_name": "jockey", "source_file": "edgeiq_live_runner_factor_scorecard_v2.csv|edgeiq_connection_intelligence_v1.csv", "source_keys": ["factor_scorecard", "connection_intelligence"], "source_columns_checked": "factor_score[JOCKEY]|jockey_track_sr", "evaluator": jockey_score_value},
    {"section": "FACTORS", "field_name": "connection", "source_file": "edgeiq_live_runner_factor_scorecard_v2.csv|edgeiq_connection_intelligence_v1.csv", "source_keys": ["factor_scorecard", "connection_intelligence"], "source_columns_checked": "factor_score[CONNECTION/COMBO]|connection_score", "evaluator": connection_score_value},
    {"section": "ADVANCED", "field_name": "historical_rating_coverage", "source_file": "edgeiq_runner_history_detail_v1.csv", "source_keys": ["history_detail"], "source_columns_checked": "run_rating_final|performance_rating", "evaluator": lambda joined: first_present((joined["history_detail"][0] if joined["history_detail"] else {}), ["run_rating_final", "performance_rating"])},
    {"section": "ADVANCED", "field_name": "race_strength", "source_file": "edgeiq_runner_history_detail_v1.csv", "source_keys": ["history_detail"], "source_columns_checked": "race_strength", "evaluator": lambda joined: first_present((joined["history_detail"][0] if joined["history_detail"] else {}), ["race_strength"])},
    {"section": "ADVANCED", "field_name": "source_confidence", "source_file": "edgeiq_runner_history_detail_v1.csv", "source_keys": ["history_detail"], "source_columns_checked": "source_confidence|rating_source", "evaluator": lambda joined: first_present((joined["history_detail"][0] if joined["history_detail"] else {}), ["source_confidence", "rating_source"])},
]


def infer_status(populated_pct: float, source_exists: bool, columns_present: bool) -> str:
    if not source_exists or not columns_present:
        return "FAIL"
    if populated_pct >= 85:
        return "PASS"
    if populated_pct >= 50:
        return "WARN"
    return "FAIL"


def infer_action(source_exists: bool, columns_present: bool, populated_pct: float, rows_available: int, matched_pct: float) -> str:
    if not source_exists:
        return "Hide or replace with clean pending copy - source file missing."
    if not columns_present:
        return "Hide field or remap source columns - expected columns missing."
    if rows_available == 0:
        return "Hide section for current card state - no joined source rows."
    if populated_pct < 50 and matched_pct < 85:
        return "Join failure suspected - demote UI and inspect matching logic."
    if populated_pct < 50:
        return "Genuinely sparse - collapse field or show compact unavailable copy."
    if populated_pct < 85:
        return "Keep with fallback/compact empty state - do not headline."
    return "Keep visible - good population."


def main() -> None:
    base_rows = active_base_rows()
    bundles = {name: source_bundle(name) for name in FILES if name != "live_runner_board"}
    joined = joined_rows(base_rows, bundles)
    built_at = now_iso()

    if not base_rows:
        raise ValueError("No active runners found in live runner board.")

    focus_sorted = sorted(
        base_rows,
        key=lambda row: (
            clean_text(row.get("race_date", "")),
            clean_text(row.get("track", "")),
            parse_int(row.get("race_no", "")) or 999,
        ),
        reverse=True,
    )
    focus = focus_sorted[0]
    focus_race_date = clean_text(focus.get("race_date", ""))
    focus_track = clean_text(focus.get("track", ""))
    focus_race_no = clean_text(focus.get("race_no", ""))
    focus_joined = [
        row for row in joined
        if clean_text(row["base"].get("race_date", "")) == focus_race_date
        and clean_text(row["base"].get("track", "")) == focus_track
        and clean_text(row["base"].get("race_no", "")) == focus_race_no
    ]

    audit_rows: list[dict[str, object]] = []
    for field_def in FIELD_DEFS:
        source_keys: list[str] = field_def["source_keys"]  # type: ignore[assignment]
        source_exists = any((key == "base") or bundles[SOURCE_ALIAS[key]]["exists"] for key in source_keys)
        source_columns = str(field_def["source_columns_checked"])
        expected_columns = [col.strip() for col in re.split(r"[|]", source_columns) if col.strip()]

        matched_rows = 0
        populated_rows = 0
        race_populated_rows = 0
        race_rows_available = 0
        matched_pct_candidates = []

        for key in source_keys:
            if key == "base":
                matched_pct_candidates.append(100.0)
            else:
                bundle = bundles[SOURCE_ALIAS[key]]
                matches = 0
                for row in joined:
                    matched = row[key]
                    if isinstance(matched, list):
                        if matched:
                            matches += 1
                    elif matched:
                        matches += 1
                matched_pct_candidates.append((matches / len(joined)) * 100 if joined else 0.0)
        matched_pct = max(matched_pct_candidates) if matched_pct_candidates else 0.0

        columns_present = False
        for key in source_keys:
            if key == "base":
                columns_present = True
                break
            available_columns = set(bundles[SOURCE_ALIAS[key]]["columns"])
            if any(part.split("[")[0] in available_columns for part in expected_columns):
                columns_present = True
                break

        for row in joined:
            joined_available = False
            for key in source_keys:
                if key == "base":
                    joined_available = True
                    break
                matched = row[key]
                if isinstance(matched, list) and matched:
                    joined_available = True
                    break
                if isinstance(matched, dict) and matched:
                    joined_available = True
                    break
            if joined_available:
                matched_rows += 1

            value = field_def["evaluator"](row)  # type: ignore[index]
            if is_populated_value(value):
                populated_rows += 1

        for row in focus_joined:
            joined_available = False
            for key in source_keys:
                if key == "base":
                    joined_available = True
                    break
                matched = row[key]
                if isinstance(matched, list) and matched:
                    joined_available = True
                    break
                if isinstance(matched, dict) and matched:
                    joined_available = True
                    break
            if joined_available:
                race_rows_available += 1
            value = field_def["evaluator"](row)  # type: ignore[index]
            if is_populated_value(value):
                race_populated_rows += 1

        populated_pct = round((populated_rows / matched_rows) * 100, 2) if matched_rows else 0.0
        active_race_populated_pct = round((race_populated_rows / race_rows_available) * 100, 2) if race_rows_available else 0.0
        status = infer_status(populated_pct, source_exists, columns_present)
        suggested_action = infer_action(source_exists, columns_present, populated_pct, matched_rows, matched_pct)

        audit_rows.append(
            {
                "section": field_def["section"],
                "field_name": field_def["field_name"],
                "source_file": field_def["source_file"],
                "source_columns_checked": source_columns,
                "rows_available": matched_rows,
                "populated_rows": populated_rows,
                "populated_pct": f"{populated_pct:.2f}",
                "active_race": f"{focus_race_date} {focus_track} R{focus_race_no}",
                "active_race_populated_pct": f"{active_race_populated_pct:.2f}",
                "matched_source_pct": f"{matched_pct:.2f}",
                "status": status,
                "suggested_action": suggested_action,
                "built_at": built_at,
            }
        )

    audit = pd.DataFrame(audit_rows)
    audit["populated_pct_num"] = pd.to_numeric(audit["populated_pct"], errors="coerce").fillna(0.0)
    audit.to_csv(OUT_PATH, index=False)

    summary_rows = []
    for section, group in audit.groupby("section", sort=False):
        summary_rows.append(
            {
                "section": section,
                "fields": len(group),
                "avg_populated_pct": f"{group['populated_pct_num'].mean():.2f}",
                "pass_fields": int((group["status"] == "PASS").sum()),
                "warn_fields": int((group["status"] == "WARN").sum()),
                "fail_fields": int((group["status"] == "FAIL").sum()),
                "lowest_field": group.sort_values("populated_pct_num").iloc[0]["field_name"],
                "lowest_pct": group.sort_values("populated_pct_num").iloc[0]["populated_pct"],
                "focus_race": f"{focus_race_date} {focus_track} R{focus_race_no}",
                "built_at": built_at,
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY_PATH, index=False)

    print(summary.to_string(index=False))
    print()
    print(audit[["section", "field_name", "rows_available", "populated_rows", "populated_pct", "status"]].to_string(index=False))


if __name__ == "__main__":
    main()
