from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = DATA / "edgeiq_horse_projection_engine_v1.csv"
AUDIT_PATH = DATA / "edgeiq_horse_projection_engine_v1_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_horse_projection_engine_v1_audit_summary.csv"

EXPECTED_BANDS = {"MAJOR_UPSIDE", "POSITIVE", "STABLE", "NEGATIVE", "HIGH_RISK"}
EXPECTED_CONFIDENCE = {"VERY_HIGH", "HIGH", "MEDIUM", "LOW"}


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
        raise FileNotFoundError(f"Missing horse projection file: {SOURCE_PATH}")

    df = pd.read_csv(SOURCE_PATH, dtype=str).fillna("")
    if df.empty:
        raise ValueError("Horse projection file is empty.")

    audit = df.copy()
    audit["duplicate_horse_key"] = audit.duplicated(subset=["horse_key"], keep=False)
    audit["missing_horse"] = audit["horse"].eq("")
    audit["missing_horse_key"] = audit["horse_key"].eq("")
    audit["missing_projection_band"] = audit["projection_band"].eq("")
    audit["missing_projection_confidence"] = audit["projection_confidence"].eq("")

    numeric_columns = [
        "latest_rating",
        "peak_rating",
        "average_rating",
        "next_run_projection",
        "expected_improvement",
        "expected_regression",
        "ceiling_projection",
        "floor_projection",
        "improvement_probability",
        "regression_probability",
        "peak_revisit_probability",
        "breakout_probability",
        "bounce_probability",
        "runs_to_peak_estimate",
        "days_to_peak_estimate",
    ]
    for column in numeric_columns:
        audit[f"{column}_num"] = audit[column].map(parse_float)

    audit["projection_band_valid"] = audit["projection_band"].isin(EXPECTED_BANDS)
    audit["projection_confidence_valid"] = audit["projection_confidence"].isin(EXPECTED_CONFIDENCE)

    probability_columns = [
        "improvement_probability",
        "regression_probability",
        "peak_revisit_probability",
        "breakout_probability",
        "bounce_probability",
    ]
    for column in probability_columns:
        audit[f"{column}_range_ok"] = audit[f"{column}_num"].between(0, 100, inclusive="both")

    audit["expected_non_negative"] = audit["expected_improvement_num"].ge(0) & audit["expected_regression_num"].ge(0)
    audit["ceiling_not_below_next"] = audit["ceiling_projection_num"].ge(audit["next_run_projection_num"])
    audit["floor_not_above_next"] = audit["floor_projection_num"].le(audit["next_run_projection_num"])

    audit["status"] = "PASS"
    fail_mask = (
        audit["duplicate_horse_key"]
        | audit["missing_horse_key"]
        | audit["missing_projection_band"]
        | audit["missing_projection_confidence"]
        | ~audit["projection_band_valid"]
        | ~audit["projection_confidence_valid"]
        | ~audit["expected_non_negative"]
        | ~audit["ceiling_not_below_next"]
        | ~audit["floor_not_above_next"]
    )
    for column in probability_columns:
        fail_mask = fail_mask | ~audit[f"{column}_range_ok"]
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
            "projection_band",
            "projection_confidence",
            "next_run_projection",
            "expected_improvement",
            "expected_regression",
            "ceiling_projection",
            "floor_projection",
            "improvement_probability",
            "regression_probability",
            "peak_revisit_probability",
            "breakout_probability",
            "bounce_probability",
            "runs_to_peak_estimate",
            "days_to_peak_estimate",
            "duplicate_horse_key",
            "missing_horse",
            "missing_horse_key",
            "missing_projection_band",
            "missing_projection_confidence",
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

    probability_ranges = []
    for column in probability_columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if values.empty:
            probability_ranges.append(f"{column}:NA")
        else:
            probability_ranges.append(f"{column}:{values.min():.1f}-{values.max():.1f}")

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
                "projection_band_counts": value_counts_summary(df["projection_band"]),
                "confidence_counts": value_counts_summary(df["projection_confidence"]),
                "null_counts": "; ".join(
                    f"{column}:{int(df[column].astype(str).str.strip().eq('').sum())}"
                    for column in [
                        "horse",
                        "horse_key",
                        "latest_rating",
                        "peak_rating",
                        "average_rating",
                        "next_run_projection",
                        "expected_improvement",
                        "expected_regression",
                        "ceiling_projection",
                        "floor_projection",
                        "improvement_probability",
                        "regression_probability",
                        "peak_revisit_probability",
                        "breakout_probability",
                        "bounce_probability",
                        "runs_to_peak_estimate",
                        "days_to_peak_estimate",
                        "projection_band",
                        "projection_confidence",
                    ]
                ),
                "probability_ranges": "; ".join(probability_ranges),
                "built_at": now_iso(),
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
