from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = DATA / "edgeiq_horse_archetype_engine_v1.csv"
AUDIT_PATH = DATA / "edgeiq_horse_archetype_engine_v1_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_horse_archetype_engine_v1_audit_summary.csv"

EXPECTED_ARCHETYPES = {
    "ELITE_PERFORMER",
    "CONSISTENT_GRINDER",
    "HIGH_CEILING",
    "BOOM_OR_BUST",
    "LATE_MATURER",
    "DISTANCE_SPECIALIST",
    "TRACK_SPECIALIST",
    "SEASONAL_PERFORMER",
    "DECLINING_VETERAN",
    "IMPROVING_YOUNGSTER",
}
EXPECTED_DEVELOPMENT = {"EMERGING", "IMPROVING", "PEAK", "PLATEAU", "DECLINING"}
EXPECTED_IMPROVEMENT = {"RAPID", "STEADY", "FLAT", "DECLINING"}
EXPECTED_CONSISTENCY = {"ELITE", "HIGH", "MEDIUM", "LOW"}
EXPECTED_FRESHNESS = {"FIRST_UP", "SECOND_UP", "PEAK_THIRD_UP", "NEEDS_RACING", "NO_PATTERN"}
EXPECTED_DISTANCE = {"SPRINTER", "MILER", "MIDDLE_DISTANCE", "STAYER", "VERSATILE"}
EXPECTED_SEASONAL = {"WINTER", "SPRING", "SUMMER", "AUTUMN", "NO_PATTERN"}


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
        raise FileNotFoundError(f"Missing horse archetype file: {SOURCE_PATH}")

    df = pd.read_csv(SOURCE_PATH, dtype=str).fillna("")
    if df.empty:
        raise ValueError("Horse archetype file is empty.")

    audit = df.copy()
    audit["duplicate_horse_key"] = audit.duplicated(subset=["horse_key"], keep=False)
    audit["missing_horse"] = audit["horse"].eq("")
    audit["missing_horse_key"] = audit["horse_key"].eq("")
    audit["missing_archetype"] = audit["horse_archetype"].eq("")
    audit["missing_development"] = audit["development_stage"].eq("")
    audit["missing_improvement"] = audit["improvement_profile"].eq("")
    audit["missing_consistency"] = audit["consistency_profile"].eq("")
    audit["missing_freshness"] = audit["freshness_profile"].eq("")
    audit["missing_distance"] = audit["distance_profile"].eq("")
    audit["missing_seasonality"] = audit["seasonality_profile"].eq("")
    audit["career_percentile_num"] = audit["career_percentile"].map(parse_float)
    audit["days_since_peak_num"] = audit["days_since_peak"].map(parse_float)
    audit["runs_since_peak_num"] = audit["runs_since_peak"].map(parse_float)

    audit["archetype_valid"] = audit["horse_archetype"].isin(EXPECTED_ARCHETYPES)
    audit["development_valid"] = audit["development_stage"].isin(EXPECTED_DEVELOPMENT)
    audit["improvement_valid"] = audit["improvement_profile"].isin(EXPECTED_IMPROVEMENT)
    audit["consistency_valid"] = audit["consistency_profile"].isin(EXPECTED_CONSISTENCY)
    audit["freshness_valid"] = audit["freshness_profile"].isin(EXPECTED_FRESHNESS)
    audit["distance_valid"] = audit["distance_profile"].isin(EXPECTED_DISTANCE)
    audit["seasonality_valid"] = audit["seasonality_profile"].isin(EXPECTED_SEASONAL)

    audit["status"] = "PASS"
    fail_mask = (
        audit["duplicate_horse_key"]
        | audit["missing_horse_key"]
        | audit["missing_archetype"]
        | ~audit["archetype_valid"]
        | ~audit["development_valid"]
        | ~audit["improvement_valid"]
        | ~audit["consistency_valid"]
        | ~audit["freshness_valid"]
        | ~audit["distance_valid"]
        | ~audit["seasonality_valid"]
    )
    audit.loc[fail_mask, "status"] = "FAIL"

    warn_mask = (
        (audit["status"] == "PASS")
        & (
            audit["missing_horse"]
            | audit["career_percentile_num"].isna()
            | audit["days_since_peak_num"].isna()
            | audit["runs_since_peak_num"].isna()
        )
    )
    audit.loc[warn_mask, "status"] = "WARN"

    audit_output = audit[
        [
            "horse",
            "horse_key",
            "horse_archetype",
            "development_stage",
            "improvement_profile",
            "consistency_profile",
            "freshness_profile",
            "distance_profile",
            "seasonality_profile",
            "career_peak_age",
            "runs_since_peak",
            "days_since_peak",
            "peak_trend",
            "last_3_average",
            "last_5_average",
            "last_10_average",
            "peak_delta",
            "career_percentile",
            "boom_or_bust_flag",
            "improver_flag",
            "regressor_flag",
            "late_maturer_flag",
            "early_maturer_flag",
            "duplicate_horse_key",
            "missing_horse",
            "missing_horse_key",
            "missing_archetype",
            "missing_development",
            "missing_improvement",
            "missing_consistency",
            "missing_freshness",
            "missing_distance",
            "missing_seasonality",
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
                "archetype_counts": value_counts_summary(df["horse_archetype"]),
                "development_stage_counts": value_counts_summary(df["development_stage"]),
                "improvement_profile_counts": value_counts_summary(df["improvement_profile"]),
                "consistency_profile_counts": value_counts_summary(df["consistency_profile"]),
                "freshness_profile_counts": value_counts_summary(df["freshness_profile"]),
                "distance_profile_counts": value_counts_summary(df["distance_profile"]),
                "seasonality_profile_counts": value_counts_summary(df["seasonality_profile"]),
                "null_counts": "; ".join(
                    f"{column}:{int(df[column].astype(str).str.strip().eq('').sum())}"
                    for column in [
                        "horse",
                        "horse_key",
                        "horse_archetype",
                        "development_stage",
                        "improvement_profile",
                        "consistency_profile",
                        "freshness_profile",
                        "distance_profile",
                        "seasonality_profile",
                        "career_peak_age",
                        "runs_since_peak",
                        "days_since_peak",
                        "peak_trend",
                        "career_percentile",
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
