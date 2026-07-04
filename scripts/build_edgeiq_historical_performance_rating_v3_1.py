import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

RATING = DATA / "edgeiq_historical_performance_rating_v3.csv"
CLEAN = DATA / "edgeiq_historical_class_clean_v2.csv"

OUT = DATA / "edgeiq_historical_performance_rating_v3_1.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v3_1_audit.csv"

print("=" * 90)
print("EDGEIQ HISTORICAL PERFORMANCE RATING V3.1 — CLEAN CLASS JOIN")
print("=" * 90)

rating = pd.read_csv(RATING, low_memory=False)
clean = pd.read_csv(CLEAN, low_memory=False)

def norm(x):
    return str(x).upper().strip()

def race_no_key(x):
    return str(x).replace(".0", "").strip()

for df in [rating, clean]:
    df["_horse_key"] = df["horse"].map(norm)
    df["_track_key"] = df["track"].map(norm)
    df["_distance_key"] = pd.to_numeric(df["distance"], errors="coerce").round(0).astype("Int64").astype(str)
    df["_finish_key"] = pd.to_numeric(df["finish_position"] if "finish_position" in df.columns else df["finish_pos"].astype(str).str.extract(r"(\d+)")[0], errors="coerce").astype("Int64").astype(str)

rating["_race_date_key"] = rating["race_date"].astype(str).str.strip()
clean["_race_date_key"] = clean["race_date"].astype(str).str.strip()

# Some source rows do not have dates. Use broad key fallback too.
clean_keep = clean[[
    "_horse_key",
    "_track_key",
    "_race_date_key",
    "_distance_key",
    "_finish_key",
    "race_class_model_v2",
    "class_model_family_v2",
    "class_model_confidence_v2",
    "race_type_recovered",
    "age_restriction_recovered",
    "sex_restriction_recovered",
    "condition_token_recovered",
    "class_recovery_status",
    "class_recovery_reason",
    "race_name",
    "race_class_raw",
]].copy()

clean_keep = clean_keep.drop_duplicates(
    ["_horse_key", "_track_key", "_race_date_key", "_distance_key", "_finish_key"],
    keep="first"
)

merged = rating.merge(
    clean_keep,
    on=["_horse_key", "_track_key", "_race_date_key", "_distance_key", "_finish_key"],
    how="left"
)

# Fallback merge without date for rows where date is missing or changed.
missing_mask = merged["race_class_model_v2"].isna()

if missing_mask.any():
    clean_fallback = clean[[
        "_horse_key",
        "_track_key",
        "_distance_key",
        "_finish_key",
        "race_class_model_v2",
        "class_model_family_v2",
        "class_model_confidence_v2",
        "race_type_recovered",
        "age_restriction_recovered",
        "sex_restriction_recovered",
        "condition_token_recovered",
        "class_recovery_status",
        "class_recovery_reason",
        "race_name",
        "race_class_raw",
    ]].drop_duplicates(
        ["_horse_key", "_track_key", "_distance_key", "_finish_key"],
        keep="first"
    )

    fallback = rating.loc[missing_mask].merge(
        clean_fallback,
        on=["_horse_key", "_track_key", "_distance_key", "_finish_key"],
        how="left",
        suffixes=("", "_fb")
    )

    for c in [
        "race_class_model_v2",
        "class_model_family_v2",
        "class_model_confidence_v2",
        "race_type_recovered",
        "age_restriction_recovered",
        "sex_restriction_recovered",
        "condition_token_recovered",
        "class_recovery_status",
        "class_recovery_reason",
        "race_name",
        "race_class_raw",
    ]:
        merged.loc[missing_mask, c] = fallback[c].values

merged["clean_class_join_status"] = merged["race_class_model_v2"].apply(
    lambda x: "JOINED" if pd.notna(x) and str(x).strip() else "NOT_JOINED"
)

# Do not overwrite original fields; create clean V3.1 fields.
merged["race_class_clean_v3_1"] = merged["race_class_model_v2"]
merged["race_class_family_v3_1"] = merged["class_model_family_v2"]
merged["race_class_confidence_v3_1"] = merged["class_model_confidence_v2"]

drop_cols = [c for c in merged.columns if c.startswith("_")]
merged = merged.drop(columns=drop_cols)

merged["built_at_v3_1"] = datetime.now().isoformat(timespec="seconds")
merged.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rating_rows_loaded", "value": len(rating)},
    {"metric": "rows_written", "value": len(merged)},
    {"metric": "clean_class_joined", "value": int(merged["clean_class_join_status"].eq("JOINED").sum())},
    {"metric": "clean_class_not_joined", "value": int(merged["clean_class_join_status"].eq("NOT_JOINED").sum())},
    {"metric": "usable_clean_class_rows", "value": int(merged["race_class_confidence_v3_1"].isin(["HIGH","MEDIUM"]).sum())},
    {"metric": "unresolved_clean_class_rows", "value": int(merged["race_class_family_v3_1"].eq("UNRESOLVED").sum())},
    {"metric": "excluded_trial_jumpout_rows", "value": int(merged["race_class_family_v3_1"].eq("EXCLUDED_TRIAL_JUMPOUT").sum())},
])

audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
