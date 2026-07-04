from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
FACTOR_PATH = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"
DNA_PATH = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
CONNECTION_PATH = DATA / "edgeiq_connection_intelligence_v1.csv"
EXPLAIN_PATH = DATA / "edgeiq_explainability_terminal_feed_v1_2.csv"

DETAIL_PATH = DATA / "edgeiq_ui_factor_population_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_ui_factor_population_v1_summary.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper_text(value: object) -> str:
    return safe_text(value).upper()


def normalize_track(value: object) -> str:
    text = upper_text(value)
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return "".join(ch for ch in text if ch.isalnum())


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def to_num(value: object) -> float | None:
    text = safe_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace("%", "").replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number):
        return None
    return number


def is_scratched_row(row: pd.Series) -> bool:
    tokens = " ".join(
        upper_text(row.get(col))
        for col in ["runner_status", "is_scratched", "scratch_status", "tab_fixed_betting_status"]
    )
    return any(token in tokens for token in ["SCRATCH", "LATESCRATCHED", "LATE SCRATCHED", "TRUE", " YES "]) or upper_text(row.get("is_scratched")) in {"TRUE", "YES", "Y", "1"}


def make_primary_key(row: pd.Series | dict[str, object]) -> str:
    return "|".join(
        [
            safe_text((row.get("race_date") if isinstance(row, dict) else row.get("race_date"))),
            upper_text((row.get("track") if isinstance(row, dict) else row.get("track"))),
            safe_text((row.get("race_no") if isinstance(row, dict) else row.get("race_no"))),
            upper_text((row.get("horse_key") if isinstance(row, dict) else row.get("horse_key"))),
        ]
    )


def make_fallback_key(row: pd.Series | dict[str, object]) -> str:
    return "|".join(
        [
            safe_text((row.get("race_date") if isinstance(row, dict) else row.get("race_date"))),
            normalize_track((row.get("track") if isinstance(row, dict) else row.get("track"))),
            safe_text((row.get("race_no") if isinstance(row, dict) else row.get("race_no"))),
            normalize_horse((row.get("horse") if isinstance(row, dict) else row.get("horse")) or (row.get("horse_key") if isinstance(row, dict) else row.get("horse_key"))),
        ]
    )


def first_value(row: dict[str, object] | None, columns: list[str]) -> str:
    if row is None:
        return ""
    for column in columns:
        value = safe_text(row.get(column))
        if value:
            return value
    return ""


def factor_lookup(rows: list[dict[str, object]], factor_name: str) -> str:
    for row in rows:
        if upper_text(row.get("factor")) == factor_name.upper():
            return safe_text(row.get("factor_score"))
    return ""


def count_present(values: list[str]) -> int:
    return sum(1 for value in values if safe_text(value))


def main() -> None:
    built_at = now_iso()

    live_df = read_csv(LIVE_PATH)
    factor_df = read_csv(FACTOR_PATH)
    dna_df = read_csv(DNA_PATH)
    connection_df = read_csv(CONNECTION_PATH)
    explain_df = read_csv(EXPLAIN_PATH)

    if live_df.empty:
        raise SystemExit("Live runner board is empty or missing.")

    live_active = live_df.loc[~live_df.apply(is_scratched_row, axis=1)].copy()

    factor_by_primary: dict[str, list[dict[str, object]]] = {}
    factor_by_fallback: dict[str, list[dict[str, object]]] = {}
    for _, row in factor_df.iterrows():
        record = row.to_dict()
        factor_by_primary.setdefault(make_primary_key(row), []).append(record)
        factor_by_fallback.setdefault(make_fallback_key(row), []).append(record)

    def singleton_maps(df: pd.DataFrame) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
        primary: dict[str, dict[str, object]] = {}
        fallback: dict[str, dict[str, object]] = {}
        for _, row in df.iterrows():
            record = row.to_dict()
            primary[make_primary_key(row)] = record
            fallback[make_fallback_key(row)] = record
        return primary, fallback

    dna_by_primary, dna_by_fallback = singleton_maps(dna_df)
    connection_by_primary, connection_by_fallback = singleton_maps(connection_df)
    explain_by_primary, explain_by_fallback = singleton_maps(explain_df)

    detail_rows: list[dict[str, object]] = []

    for _, row in live_active.iterrows():
        primary_key = make_primary_key(row)
        fallback_key = make_fallback_key(row)

        factor_rows = factor_by_primary.get(primary_key)
        factor_join_method = "PRIMARY"
        if factor_rows is None:
            factor_rows = factor_by_fallback.get(fallback_key, [])
            factor_join_method = "FALLBACK" if factor_rows else "MISSING"

        dna_row = dna_by_primary.get(primary_key)
        dna_join_method = "PRIMARY"
        if dna_row is None:
            dna_row = dna_by_fallback.get(fallback_key)
            dna_join_method = "FALLBACK" if dna_row else "MISSING"

        connection_row = connection_by_primary.get(primary_key)
        connection_join_method = "PRIMARY"
        if connection_row is None:
            connection_row = connection_by_fallback.get(fallback_key)
            connection_join_method = "FALLBACK" if connection_row else "MISSING"

        explain_row = explain_by_primary.get(primary_key)
        explain_join_method = "PRIMARY"
        if explain_row is None:
            explain_row = explain_by_fallback.get(fallback_key)
            explain_join_method = "FALLBACK" if explain_row else "MISSING"

        trainer_score = factor_lookup(factor_rows, "TRAINER") or first_value(row.to_dict(), ["trainer_score"]) or first_value(dna_row, ["trainer_score"]) or first_value(explain_row, ["connection_score"])
        jockey_score = factor_lookup(factor_rows, "JOCKEY") or first_value(row.to_dict(), ["jockey_score"]) or first_value(dna_row, ["jockey_score"]) or first_value(explain_row, ["connection_score"])
        combo_score = factor_lookup(factor_rows, "COMBO") or first_value(connection_row, ["combo_sr"]) or first_value(explain_row, ["combo_sr"])
        connection_score = factor_lookup(factor_rows, "CONNECTION") or first_value(connection_row, ["connection_score"]) or first_value(explain_row, ["connection_score"])
        distance_fit = factor_lookup(factor_rows, "DISTANCE") or first_value(dna_row, ["distance_fit_score"])
        condition_fit = factor_lookup(factor_rows, "CONDITION") or first_value(dna_row, ["condition_fit_score"])
        class_fit = factor_lookup(factor_rows, "CLASS") or first_value(dna_row, ["class_fit_score"])
        sectionals = factor_lookup(factor_rows, "SECTIONALS") or first_value(dna_row, ["sectional_score"]) or first_value(row.to_dict(), ["sectional_weapon_score"])
        late_power = factor_lookup(factor_rows, "LATE POWER") or factor_lookup(factor_rows, "LATE_POWER") or first_value(row.to_dict(), ["late_power_index", "late_power_score"])
        projected_speed = factor_lookup(factor_rows, "PACE") or first_value(row.to_dict(), ["projected_spd", "early_speed_rating"])
        confidence = first_value(explain_row, ["final_confidence_score", "confidence_band", "confidence_explanation"])
        race_shape = first_value(explain_row, ["race_shape_label", "race_tempo"])
        top_positives_count = count_present([
            first_value(explain_row, ["positive_1"]),
            first_value(explain_row, ["positive_2"]),
            first_value(explain_row, ["positive_3"]),
        ])
        top_risks_count = count_present([
            first_value(explain_row, ["risk_1"]),
            first_value(explain_row, ["risk_2"]),
            first_value(explain_row, ["risk_3"]),
        ])

        detail_rows.append(
            {
                "race_date": safe_text(row.get("race_date")),
                "track": safe_text(row.get("track")),
                "race_no": safe_text(row.get("race_no")),
                "horse": safe_text(row.get("horse")),
                "horse_key": safe_text(row.get("horse_key")),
                "runner_key": safe_text(row.get("runner_key")),
                "has_factor_scorecard_join": "YES" if factor_join_method != "MISSING" else "NO",
                "factor_scorecard_join_method": factor_join_method,
                "factor_scorecard_row_count": len(factor_rows),
                "has_dna_drawer_join": "YES" if dna_join_method != "MISSING" else "NO",
                "dna_drawer_join_method": dna_join_method,
                "has_connection_join": "YES" if connection_join_method != "MISSING" else "NO",
                "connection_join_method": connection_join_method,
                "has_explainability_join": "YES" if explain_join_method != "MISSING" else "NO",
                "explainability_join_method": explain_join_method,
                "trainer_score_value": trainer_score,
                "jockey_score_value": jockey_score,
                "combo_score_value": combo_score,
                "connection_score_value": connection_score,
                "distance_fit_value": distance_fit,
                "condition_fit_value": condition_fit,
                "class_fit_value": class_fit,
                "sectionals_value": sectionals,
                "late_power_value": late_power,
                "projected_speed_value": projected_speed,
                "confidence_value": confidence,
                "race_shape_value": race_shape,
                "top_positives_count": top_positives_count,
                "top_risks_count": top_risks_count,
                "trainer_populated": "YES" if safe_text(trainer_score) else "NO",
                "jockey_populated": "YES" if safe_text(jockey_score) else "NO",
                "combo_populated": "YES" if safe_text(combo_score) else "NO",
                "connection_populated": "YES" if safe_text(connection_score) else "NO",
                "distance_fit_populated": "YES" if safe_text(distance_fit) else "NO",
                "condition_fit_populated": "YES" if safe_text(condition_fit) else "NO",
                "class_fit_populated": "YES" if safe_text(class_fit) else "NO",
                "sectionals_populated": "YES" if safe_text(sectionals) else "NO",
                "late_power_populated": "YES" if safe_text(late_power) else "NO",
                "projected_speed_populated": "YES" if safe_text(projected_speed) else "NO",
                "confidence_populated": "YES" if safe_text(confidence) else "NO",
                "race_shape_populated": "YES" if safe_text(race_shape) else "NO",
                "top_positives_populated": "YES" if top_positives_count > 0 else "NO",
                "top_risks_populated": "YES" if top_risks_count > 0 else "NO",
                "built_at": built_at,
            }
        )

    detail_df = pd.DataFrame(detail_rows)

    def yes_count(column: str) -> int:
        return int((detail_df[column] == "YES").sum()) if not detail_df.empty else 0

    def rate(column: str) -> float:
        return round((yes_count(column) / len(detail_df)) * 100.0, 4) if len(detail_df) else 0.0

    summary_row = {
        "status": "EDGEIQ_UI_FACTOR_POPULATION_AUDIT_COMPLETE",
        "active_runner_count": len(live_active),
        "factor_scorecard_join_rows": yes_count("has_factor_scorecard_join"),
        "factor_scorecard_join_rate_pct": rate("has_factor_scorecard_join"),
        "dna_drawer_join_rows": yes_count("has_dna_drawer_join"),
        "dna_drawer_join_rate_pct": rate("has_dna_drawer_join"),
        "connection_join_rows": yes_count("has_connection_join"),
        "connection_join_rate_pct": rate("has_connection_join"),
        "explainability_join_rows": yes_count("has_explainability_join"),
        "explainability_join_rate_pct": rate("has_explainability_join"),
        "trainer_populated_rows": yes_count("trainer_populated"),
        "trainer_populated_rate_pct": rate("trainer_populated"),
        "jockey_populated_rows": yes_count("jockey_populated"),
        "jockey_populated_rate_pct": rate("jockey_populated"),
        "combo_populated_rows": yes_count("combo_populated"),
        "combo_populated_rate_pct": rate("combo_populated"),
        "connection_populated_rows": yes_count("connection_populated"),
        "connection_populated_rate_pct": rate("connection_populated"),
        "distance_fit_populated_rows": yes_count("distance_fit_populated"),
        "distance_fit_populated_rate_pct": rate("distance_fit_populated"),
        "condition_fit_populated_rows": yes_count("condition_fit_populated"),
        "condition_fit_populated_rate_pct": rate("condition_fit_populated"),
        "class_fit_populated_rows": yes_count("class_fit_populated"),
        "class_fit_populated_rate_pct": rate("class_fit_populated"),
        "sectionals_populated_rows": yes_count("sectionals_populated"),
        "sectionals_populated_rate_pct": rate("sectionals_populated"),
        "late_power_populated_rows": yes_count("late_power_populated"),
        "late_power_populated_rate_pct": rate("late_power_populated"),
        "projected_speed_populated_rows": yes_count("projected_speed_populated"),
        "projected_speed_populated_rate_pct": rate("projected_speed_populated"),
        "confidence_populated_rows": yes_count("confidence_populated"),
        "confidence_populated_rate_pct": rate("confidence_populated"),
        "race_shape_populated_rows": yes_count("race_shape_populated"),
        "race_shape_populated_rate_pct": rate("race_shape_populated"),
        "top_positives_populated_rows": yes_count("top_positives_populated"),
        "top_positives_populated_rate_pct": rate("top_positives_populated"),
        "top_risks_populated_rows": yes_count("top_risks_populated"),
        "top_risks_populated_rate_pct": rate("top_risks_populated"),
        "live_runner_board_dates": "; ".join(sorted(set(live_active["race_date"].astype(str)))) if "race_date" in live_active else "",
        "factor_scorecard_dates": "; ".join(sorted(set(factor_df["race_date"].astype(str)))) if not factor_df.empty and "race_date" in factor_df else "",
        "dna_drawer_dates": "; ".join(sorted(set(dna_df["race_date"].astype(str)))) if not dna_df.empty and "race_date" in dna_df else "",
        "connection_dates": "; ".join(sorted(set(connection_df["race_date"].astype(str)))) if not connection_df.empty and "race_date" in connection_df else "",
        "explainability_dates": "; ".join(sorted(set(explain_df["race_date"].astype(str)))) if not explain_df.empty and "race_date" in explain_df else "",
        "built_at": built_at,
    }

    detail_df.to_csv(DETAIL_PATH, index=False)
    pd.DataFrame([summary_row]).to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_UI_FACTOR_POPULATION_V1] COMPLETE")
    print(f"active_runner_count={summary_row['active_runner_count']}")
    print(f"factor_scorecard_join_rate_pct={summary_row['factor_scorecard_join_rate_pct']}")
    print(f"dna_drawer_join_rate_pct={summary_row['dna_drawer_join_rate_pct']}")
    print(f"connection_join_rate_pct={summary_row['connection_join_rate_pct']}")
    print(f"explainability_join_rate_pct={summary_row['explainability_join_rate_pct']}")
    print(f"trainer_populated_rate_pct={summary_row['trainer_populated_rate_pct']}")
    print(f"jockey_populated_rate_pct={summary_row['jockey_populated_rate_pct']}")
    print(f"connection_populated_rate_pct={summary_row['connection_populated_rate_pct']}")
    print(f"factor_scorecard_dates={summary_row['factor_scorecard_dates']}")
    print(f"wrote={DETAIL_PATH}")
    print(f"summary={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
