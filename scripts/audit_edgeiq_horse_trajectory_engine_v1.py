from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = DATA / "edgeiq_horse_trajectory_engine_v1.csv"
AUDIT_PATH = DATA / "edgeiq_horse_trajectory_engine_v1_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_horse_trajectory_engine_v1_audit_summary.csv"

EXPECTED_DIRECTIONS = {"STRONG_UP", "UP", "STABLE", "DOWN", "STRONG_DOWN"}
EXPECTED_STRENGTHS = {"VERY_HIGH", "HIGH", "MEDIUM", "LOW"}
EXPECTED_PHASES = {"EMERGING", "ASCENDING", "PEAK", "PLATEAU", "DECLINING"}
EXPECTED_RISKS = {"VERY_HIGH", "HIGH", "MEDIUM", "LOW"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def parse_float(value: object) -> float | None:
    text = safe_text(value).replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def value_counts_summary(series: pd.Series) -> str:
    counts = series.value_counts()
    return "; ".join(f"{index}:{int(count)}" for index, count in counts.items())


def main() -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Missing horse trajectory file: {SOURCE_PATH}")

    df = pd.read_csv(SOURCE_PATH, dtype=str).fillna("")
    if df.empty:
        raise ValueError("Horse trajectory file is empty.")

    audit = df.copy()
    audit["duplicate_horse_key"] = audit.duplicated(subset=["horse_key"], keep=False)
    audit["missing_horse"] = audit["horse"].eq("")
    audit["missing_horse_key"] = audit["horse_key"].eq("")
    audit["missing_direction"] = audit["trajectory_direction"].eq("")
    audit["missing_phase"] = audit["career_phase"].eq("")
    audit["missing_breakout"] = audit["breakout_potential"].eq("")
    audit["missing_bounce"] = audit["bounce_risk"].eq("")
    audit["missing_regression"] = audit["regression_risk"].eq("")

    for column in [
        "latest_rating",
        "peak_rating",
        "average_rating",
        "last_3_average",
        "last_5_average",
        "last_10_average",
        "trajectory_score",
        "points_off_peak",
        "percent_of_peak",
        "runs_since_peak",
        "days_since_peak",
        "improvement_last_3",
        "improvement_last_5",
        "improvement_last_10",
        "next_run_projection",
        "ceiling_projection",
        "floor_projection",
    ]:
        audit[f"{column}_num"] = audit[column].map(parse_float)

    audit["direction_valid"] = audit["trajectory_direction"].isin(EXPECTED_DIRECTIONS)
    audit["strength_valid"] = audit["trajectory_strength"].isin(EXPECTED_STRENGTHS)
    audit["phase_valid"] = audit["career_phase"].isin(EXPECTED_PHASES)
    audit["breakout_valid"] = audit["breakout_potential"].isin(EXPECTED_RISKS)
    audit["bounce_valid"] = audit["bounce_risk"].isin(EXPECTED_RISKS)
    audit["regression_valid"] = audit["regression_risk"].isin(EXPECTED_RISKS)
    audit["trajectory_score_in_range"] = audit["trajectory_score_num"].between(0, 100, inclusive="both")
    audit["percent_of_peak_in_range"] = audit["percent_of_peak_num"].between(0, 150, inclusive="both")
    audit["points_off_peak_non_negative"] = audit["points_off_peak_num"].ge(0)

    audit["status"] = "PASS"
    fail_mask = (
        audit["duplicate_horse_key"]
        | audit["missing_horse_key"]
        | audit["missing_direction"]
        | audit["missing_phase"]
        | audit["missing_breakout"]
        | audit["missing_bounce"]
        | audit["missing_regression"]
        | ~audit["direction_valid"]
        | ~audit["strength_valid"]
        | ~audit["phase_valid"]
        | ~audit["breakout_valid"]
        | ~audit["bounce_valid"]
        | ~audit["regression_valid"]
        | ~audit["trajectory_score_in_range"]
        | ~audit["percent_of_peak_in_range"]
        | ~audit["points_off_peak_non_negative"]
    )
    audit.loc[fail_mask, "status"] = "FAIL"

    warn_mask = (
        (audit["status"] == "PASS")
        & (
            audit["missing_horse"]
            | audit["latest_rating_num"].isna()
            | audit["peak_rating_num"].isna()
            | audit["average_rating_num"].isna()
            | audit["next_run_projection_num"].isna()
            | audit["ceiling_projection_num"].isna()
            | audit["floor_projection_num"].isna()
        )
    )
    audit.loc[warn_mask, "status"] = "WARN"

    audit_output = audit[
        [
            "horse",
            "horse_key",
            "trajectory_direction",
            "trajectory_strength",
            "trajectory_score",
            "career_phase",
            "breakout_potential",
            "bounce_risk",
            "regression_risk",
            "points_off_peak",
            "percent_of_peak",
            "runs_since_peak",
            "days_since_peak",
            "improvement_last_3",
            "improvement_last_5",
            "improvement_last_10",
            "next_run_projection",
            "ceiling_projection",
            "floor_projection",
            "duplicate_horse_key",
            "missing_horse",
            "missing_horse_key",
            "missing_direction",
            "missing_phase",
            "missing_breakout",
            "missing_bounce",
            "missing_regression",
            "status",
        ]
    ].copy()
    audit_output["built_at"] = now_iso()
    audit_output.to_csv(AUDIT_PATH, index=False)

    rows = len(df)
    unique_horses = df["horse_key"].nunique()
    fail_rows = int((audit["status"] == "FAIL").sum())
    warn_rows = int((audit["status"] == "WARN").sum())
    duplicate_horse_keys = int(audit["duplicate_horse_key"].sum())

    if rows == 0 or unique_horses == 0 or duplicate_horse_keys > 0 or fail_rows > 0:
        status = "FAIL"
    elif warn_rows > 0:
        status = "WARN"
    else:
        status = "PASS"

    summary = pd.DataFrame(
        [
            {
                "status": status,
                "rows": rows,
                "unique_horses": unique_horses,
                "fail_rows": fail_rows,
                "warn_rows": warn_rows,
                "duplicate_horse_keys": duplicate_horse_keys,
                "direction_counts": value_counts_summary(df["trajectory_direction"]),
                "strength_counts": value_counts_summary(df["trajectory_strength"]),
                "phase_counts": value_counts_summary(df["career_phase"]),
                "breakout_potential_counts": value_counts_summary(df["breakout_potential"]),
                "bounce_risk_counts": value_counts_summary(df["bounce_risk"]),
                "regression_risk_counts": value_counts_summary(df["regression_risk"]),
                "null_counts": "; ".join(
                    f"{column}:{int(df[column].astype(str).str.strip().eq('').sum())}"
                    for column in [
                        "horse",
                        "horse_key",
                        "trajectory_direction",
                        "trajectory_strength",
                        "trajectory_score",
                        "career_phase",
                        "breakout_potential",
                        "bounce_risk",
                        "regression_risk",
                        "points_off_peak",
                        "percent_of_peak",
                        "runs_since_peak",
                        "days_since_peak",
                        "improvement_last_3",
                        "improvement_last_5",
                        "improvement_last_10",
                        "next_run_projection",
                        "ceiling_projection",
                        "floor_projection",
                    ]
                ),
                "built_at": now_iso(),
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
