from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
AUDIT_PATH = DATA / "edgeiq_historical_run_ratings_master_v1_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_historical_run_ratings_master_v1_audit_summary.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def pct(series: pd.Series) -> float:
    return 0.0 if len(series) == 0 else round(float(series.mean()) * 100.0, 2)


def main() -> None:
    built_at = now_iso()
    if not INPUT_PATH.exists():
        pd.DataFrame([{"status": "FAIL", "reason": "missing_master_file", "built_at": built_at}]).to_csv(SUMMARY_PATH, index=False)
        pd.DataFrame(columns=["status", "reason", "built_at"]).to_csv(AUDIT_PATH, index=False)
        raise SystemExit("[EDGEIQ_HISTORICAL_RUN_RATINGS_MASTER_AUDIT_V1] missing input file")

    df = pd.read_csv(INPUT_PATH, dtype=str).fillna("")
    if df.empty:
        pd.DataFrame([{"status": "FAIL", "reason": "empty_master_file", "built_at": built_at}]).to_csv(SUMMARY_PATH, index=False)
        pd.DataFrame(columns=["status", "reason", "built_at"]).to_csv(AUDIT_PATH, index=False)
        raise SystemExit("[EDGEIQ_HISTORICAL_RUN_RATINGS_MASTER_AUDIT_V1] empty master file")

    audit_df = df.copy()
    audit_df["has_horse"] = audit_df["horse"].astype(str).str.strip().ne("")
    audit_df["has_horse_key"] = audit_df["horse_key"].astype(str).str.strip().ne("")
    audit_df["has_race_date"] = audit_df["race_date"].astype(str).str.strip().ne("")
    audit_df["has_track"] = audit_df["track"].astype(str).str.strip().ne("")
    audit_df["has_race_no"] = audit_df["race_no"].astype(str).str.strip().ne("")
    audit_df["has_distance"] = audit_df["distance"].astype(str).str.strip().ne("")
    audit_df["has_finish_pos"] = audit_df["finish_pos"].astype(str).str.strip().ne("")
    audit_df["has_field_size"] = audit_df["field_size"].astype(str).str.strip().ne("")
    audit_df["has_performance_rating"] = audit_df["performance_rating"].astype(str).str.strip().ne("")
    audit_df["has_rating_band"] = audit_df["rating_band"].astype(str).str.strip().ne("")
    audit_df["has_rating_rank"] = audit_df["rating_rank_in_race"].astype(str).str.strip().ne("")
    audit_df["has_rating_confidence"] = audit_df["rating_confidence"].astype(str).str.strip().ne("")
    audit_df["has_race_strength"] = audit_df["race_strength"].astype(str).str.strip().ne("")
    audit_df["has_field_strength"] = audit_df["field_strength"].astype(str).str.strip().ne("")
    audit_df["has_sp"] = audit_df["sp"].astype(str).str.strip().ne("")
    audit_df["has_pos_800"] = audit_df["pos_800"].astype(str).str.strip().ne("")
    audit_df["has_pos_400"] = audit_df["pos_400"].astype(str).str.strip().ne("")
    audit_df["duplicate_key"] = audit_df[["horse_key", "race_date", "track", "race_no", "distance"]].astype(str).agg("|".join, axis=1)
    dup_counts = audit_df["duplicate_key"].value_counts()
    audit_df["duplicate_key_count"] = audit_df["duplicate_key"].map(dup_counts).fillna(0).astype(int)
    audit_df["duplicate_key_flag"] = audit_df["duplicate_key_count"] > 1
    audit_df["row_status"] = audit_df.apply(
        lambda row: "FAIL_DUPLICATE"
        if row["duplicate_key_flag"]
        else "WARN_MISSING_RATING"
        if not row["has_performance_rating"]
        else "PASS",
        axis=1,
    )
    audit_df.to_csv(AUDIT_PATH, index=False)

    duplicate_rows = int(audit_df["duplicate_key_flag"].sum())
    pct_rating = pct(audit_df["has_performance_rating"])
    pct_race_strength = pct(audit_df["has_race_strength"])
    pct_field_strength = pct(audit_df["has_field_strength"])
    pct_rank = pct(audit_df["has_rating_rank"])
    pct_conf = pct(audit_df["has_rating_confidence"])

    if duplicate_rows > 0 or pct_rating < 90 or pct_race_strength < 90 or pct_field_strength < 90:
        status = "FAIL"
    elif pct_rating < 95 or pct_rank < 95 or pct_conf < 95:
        status = "WARN"
    else:
        status = "PASS"

    summary = pd.DataFrame(
        [
            {
                "status": status,
                "rows": int(len(audit_df)),
                "unique_horses": int(audit_df["horse_key"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()),
                "unique_races": int((audit_df["race_date"].astype(str) + "|" + audit_df["track"].astype(str) + "|" + audit_df["race_no"].astype(str)).nunique()),
                "duplicate_key_rows": duplicate_rows,
                "pct_horse_populated": pct(audit_df["has_horse"]),
                "pct_horse_key_populated": pct(audit_df["has_horse_key"]),
                "pct_race_date_populated": pct(audit_df["has_race_date"]),
                "pct_track_populated": pct(audit_df["has_track"]),
                "pct_race_no_populated": pct(audit_df["has_race_no"]),
                "pct_distance_populated": pct(audit_df["has_distance"]),
                "pct_finish_pos_populated": pct(audit_df["has_finish_pos"]),
                "pct_field_size_populated": pct(audit_df["has_field_size"]),
                "pct_performance_rating_populated": pct_rating,
                "pct_rating_band_populated": pct(audit_df["has_rating_band"]),
                "pct_rating_rank_populated": pct_rank,
                "pct_rating_confidence_populated": pct_conf,
                "pct_race_strength_populated": pct_race_strength,
                "pct_field_strength_populated": pct_field_strength,
                "pct_sp_populated": pct(audit_df["has_sp"]),
                "pct_pos_800_populated": pct(audit_df["has_pos_800"]),
                "pct_pos_400_populated": pct(audit_df["has_pos_400"]),
                "rating_method_counts": "; ".join(f"{key}:{value}" for key, value in audit_df["rating_method"].value_counts(dropna=False).to_dict().items()),
                "rating_confidence_counts": "; ".join(f"{key}:{value}" for key, value in audit_df["rating_confidence"].value_counts(dropna=False).to_dict().items()),
                "warnings": "; ".join(
                    warning
                    for warning in [
                        "coverage_below_95" if pct_rating < 95 else "",
                        "race_strength_below_95" if pct_race_strength < 95 else "",
                        "rank_sparse" if pct_rank < 95 else "",
                        "sp_sparse" if pct(audit_df["has_sp"]) < 50 else "",
                    ]
                    if warning
                ),
                "built_at": built_at,
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_HISTORICAL_RUN_RATINGS_MASTER_AUDIT_V1] COMPLETE")
    print(summary.to_string(index=False))
    print(f"audit={AUDIT_PATH}")
    print(f"summary={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
