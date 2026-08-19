from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = DATA / "edgeiq_horse_career_intelligence_v1.csv"
AUDIT_PATH = DATA / "edgeiq_horse_career_intelligence_v1_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_horse_career_intelligence_v1_audit_summary.csv"


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


def main() -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Missing source file: {SOURCE_PATH}")

    df = pd.read_csv(SOURCE_PATH, dtype=str).fillna("")
    if df.empty:
        raise ValueError("Horse career intelligence file is empty.")

    audit = df.copy()
    audit["peak_missing"] = audit["peak_rating"].eq("")
    audit["latest_missing"] = audit["latest_rating"].eq("")
    audit["average_missing"] = audit["average_rating"].eq("")
    audit["consistency_missing"] = audit["consistency_score"].eq("")
    audit["volatility_missing"] = audit["volatility_score"].eq("")
    audit["best_track_missing"] = audit["best_track"].eq("")
    audit["best_distance_missing"] = audit["best_distance"].eq("")
    audit["best_condition_missing"] = audit["best_condition"].eq("")
    audit["best_class_missing"] = audit["best_class"].eq("")
    audit["career_starts_num"] = audit["career_starts"].map(parse_float)
    audit["career_rating_percentile_num"] = audit["career_rating_percentile"].map(parse_float)
    audit["status"] = "PASS"
    audit.loc[
        audit["peak_missing"]
        | audit["latest_missing"]
        | audit["average_missing"]
        | audit["career_starts_num"].isna(),
        "status",
    ] = "FAIL"
    audit.loc[
        (audit["status"] == "PASS")
        & (
            audit["best_track_missing"]
            | audit["best_distance_missing"]
            | audit["best_condition_missing"]
            | audit["best_class_missing"]
            | audit["consistency_missing"]
            | audit["volatility_missing"]
        ),
        "status",
    ] = "WARN"

    duplicate_mask = audit.duplicated(subset=["horse_key"], keep=False)

    audit_output = audit[
        [
            "horse",
            "horse_key",
            "career_starts",
            "career_wins",
            "career_places",
            "peak_rating",
            "average_rating",
            "latest_rating",
            "career_trend",
            "career_rating_percentile",
            "rating_band",
            "consistency_score",
            "volatility_score",
            "best_track",
            "best_distance",
            "best_condition",
            "best_class",
            "peak_missing",
            "latest_missing",
            "average_missing",
            "consistency_missing",
            "volatility_missing",
            "status",
        ]
    ].copy()
    audit_output["built_at"] = now_iso()
    audit_output.to_csv(AUDIT_PATH, index=False)

    rows = len(df)
    unique_horses = audit["horse_key"].nunique()
    missing_peak = int(audit["peak_missing"].sum())
    missing_latest = int(audit["latest_missing"].sum())
    missing_average = int(audit["average_missing"].sum())
    fail_rows = int((audit["status"] == "FAIL").sum())
    warn_rows = int((audit["status"] == "WARN").sum())
    duplicate_horse_keys = int(duplicate_mask.sum())

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
                "missing_peak": missing_peak,
                "missing_latest": missing_latest,
                "missing_average": missing_average,
                "pct_peak_populated": round((1 - (missing_peak / rows)) * 100, 2),
                "pct_latest_populated": round((1 - (missing_latest / rows)) * 100, 2),
                "pct_average_populated": round((1 - (missing_average / rows)) * 100, 2),
                "duplicate_horse_keys": duplicate_horse_keys,
                "warn_rows": warn_rows,
                "fail_rows": fail_rows,
                "band_counts": "; ".join(
                    f"{band}:{count}" for band, count in df["rating_band"].value_counts().sort_index().items()
                ),
                "trend_counts": "; ".join(
                    f"{trend}:{count}" for trend, count in df["career_trend"].value_counts().sort_index().items()
                ),
                "built_at": now_iso(),
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
