from pathlib import Path
import pandas as pd
import re
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
POWER = DATA / "edgeiq_horse_results_power_ratings_v1.csv"

OUT = DATA / "edgeiq_historical_performance_rating_v5_1_BACKFILLED_POWER_V1.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v5_1_backfilled_power_v1_audit.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def horse_key(x):
    s = clean(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def num(x):
    try:
        s = clean(x)
        if s == "":
            return math.nan
        return float(s)
    except Exception:
        return math.nan

def main():
    hist = pd.read_csv(HIST, dtype=str, keep_default_na=False, low_memory=False)
    power = pd.read_csv(POWER, dtype=str, keep_default_na=False, low_memory=False)

    hist["horse_key_backfill"] = hist["horse"].map(horse_key)
    power["horse_key_backfill"] = power["horse_key"].map(horse_key)

    existing = set(hist["horse_key_backfill"].dropna().astype(str))

    power["meeting_date_dt"] = pd.to_datetime(power["meeting_date"], errors="coerce")
    power["performance_rating_num"] = pd.to_numeric(power["performance_rating"], errors="coerce")

    usable = power[
        power["horse_key_backfill"].ne("") &
        power["meeting_date_dt"].notna() &
        power["performance_rating_num"].notna()
    ].copy()

    missing = usable[~usable["horse_key_backfill"].isin(existing)].copy()

    backfill = pd.DataFrame()
    if len(missing):
        backfill = pd.DataFrame({
            "horse": missing["horse"].map(clean),
            "race_date": missing["meeting_date"].map(clean),
            "track": missing["race_key"].map(lambda x: clean(x).split("|")[1] if "|" in clean(x) and len(clean(x).split("|")) > 1 else ""),
            "distance": "",
            "race_class_clean": "UNKNOWN",
            "condition_recovered": "",
            "source_file": "edgeiq_horse_results_power_ratings_v1.csv",
            "finish_pos_raw": missing["finish"].map(clean),
            "finish_position": missing["finish"].map(clean),
            "real_field_size": "",
            "real_field_size_source": "power_rating_backfill",
            "margin_raw": missing["margin"].map(clean),
            "margin": missing["margin"].map(clean),
            "performance_rating_v3": missing["performance_rating"].map(clean),
            "performance_band_v3": "POWER_RATING_BACKFILL",
            "performance_reason_v3": "backfilled from edgeiq_horse_results_power_ratings_v1.performance_rating",
            "recovery_confidence": "BACKFILLED",
            "clean_class_join_status_v3_3": "BACKFILLED_POWER_RATING",
            "clean_class_join_key_v3_3": "horse_key",
            "race_class_model_v3": "UNKNOWN",
            "class_model_family_v3": "UNRESOLVED",
            "class_model_confidence_v3": "UNRESOLVED",
            "is_class_usable_v3": "False",
            "is_excluded_from_class_model_v3": "False",
            "class_recovery_status": "BACKFILLED_POWER_RATING",
            "class_recovery_reason": "missing_from_v5_1_history",
            "race_type_recovered": "FLAT",
            "age_restriction_recovered": "OPEN",
            "sex_restriction_recovered": "OPEN",
            "condition_token_recovered": "",
            "race_name": "",
            "race_class_raw": "UNKNOWN",
            "race_class_recovered": "UNKNOWN",
            "cup_name_detected_v3": "FALSE",
            "race_name_recovery_applied_v3": "FALSE",
            "race_name_recovery_reason_v3": "",
            "clean_class_match_count_v3_3": "",
            "clean_class_distinct_class_count_v3_3": "",
            "clean_class_ambiguous_match_v3_3": "FALSE",
            "race_class_clean_v3_3": "UNKNOWN",
            "race_class_family_v3_3": "UNRESOLVED",
            "race_class_confidence_v3_3": "UNRESOLVED",
            "built_at_v3_3": "",
            "class_ladder_score_v1": "",
            "class_ladder_norm_v1": "",
            "class_ladder_rank_v1": "",
            "class_ladder_reason_v1": "",
            "sample_confidence_v1": "",
            "class_quality_adjustment_v5_1": "0.0",
            "finish_quality_multiplier_v5_1": "1.0",
            "field_size_adjustment_v5_1": "0.0",
            "performance_rating_base_v5_1": missing["performance_rating"].map(clean),
            "performance_rating_v5_1": missing["performance_rating"].map(clean),
            "rating_v5_1_status": "BACKFILLED_POWER_RATING",
            "built_at_v5_1": pd.Timestamp.utcnow().isoformat(),
        })

    for c in hist.columns:
        if c == "horse_key_backfill":
            continue
        if c not in backfill.columns:
            backfill[c] = ""

    backfill = backfill[[c for c in hist.columns if c != "horse_key_backfill"]]
    out = pd.concat([hist.drop(columns=["horse_key_backfill"]), backfill], ignore_index=True)

    out.to_csv(OUT, index=False)

    audit = pd.DataFrame([
        ["hist_rows_before", len(hist)],
        ["power_rows", len(power)],
        ["usable_power_rows", len(usable)],
        ["backfill_rows_added", len(backfill)],
        ["hist_rows_after", len(out)],
        ["out", OUT.name],
    ], columns=["metric","value"])
    audit.to_csv(AUDIT, index=False)

    print("[V5_1_HISTORY_POWER_BACKFILL_V1] COMPLETE")
    print(audit.to_string(index=False))
    print(f"out={OUT}")

if __name__ == "__main__":
    main()
