import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_class_recovery_engine_v2.csv"
OUT = DATA / "edgeiq_historical_class_clean_v2.csv"
AUDIT = DATA / "edgeiq_historical_class_clean_v2_audit.csv"

print("=" * 90)
print("EDGEIQ HISTORICAL CLASS CLEAN V2")
print("=" * 90)

df = pd.read_csv(SRC, low_memory=False)

usable_status = [
    "RECOVERED",
    "KEPT_EXISTING",
]

exclude_status = [
    "EXCLUDE_TRIAL_JUMPOUT",
]

df["is_class_usable_v2"] = df["class_recovery_status"].isin(usable_status)
df["is_excluded_from_class_model_v2"] = df["class_recovery_status"].isin(exclude_status)

df["race_class_model_v2"] = df["race_class_recovered"]

# Classes that should not be used as ordinary flat benchmark classes.
special = {
    "JUMPS_RATING_BAND",
    "BM120",
    "HURDLE",
    "STEEPLECHASE",
}

df["class_model_family_v2"] = "UNRESOLVED"

df.loc[df["race_class_model_v2"].str.match(r"^BM[0-9]{2,3}$", na=False), "class_model_family_v2"] = "BENCHMARK"
df.loc[df["race_class_model_v2"].str.match(r"^CLASS [1-6]$", na=False), "class_model_family_v2"] = "CLASS"
df.loc[df["race_class_model_v2"].eq("MAIDEN"), "class_model_family_v2"] = "MAIDEN"
df.loc[df["race_class_model_v2"].isin(["GROUP 1","GROUP 2","GROUP 3","LISTED"]), "class_model_family_v2"] = "BLACKTYPE"
df.loc[df["race_class_model_v2"].isin(["OPEN","SET WEIGHTS","SET WEIGHTS PENALTIES"]), "class_model_family_v2"] = "OPEN_SET_WEIGHTS"
df.loc[df["race_class_model_v2"].isin(["COUNTRY","PROVINCIAL","MIDWAY","HIGHWAY"]), "class_model_family_v2"] = "REGIONAL_RESTRICTED"
df.loc[df["race_class_model_v2"].isin(special), "class_model_family_v2"] = "JUMPS_OR_HIGHWEIGHT"
df.loc[df["is_excluded_from_class_model_v2"], "class_model_family_v2"] = "EXCLUDED_TRIAL_JUMPOUT"

df["class_model_confidence_v2"] = "LOW"
df.loc[df["class_recovery_status"].eq("KEPT_EXISTING"), "class_model_confidence_v2"] = "HIGH"
df.loc[df["class_recovery_status"].eq("RECOVERED"), "class_model_confidence_v2"] = "MEDIUM"
df.loc[df["class_model_family_v2"].eq("UNRESOLVED"), "class_model_confidence_v2"] = "UNRESOLVED"
df.loc[df["class_model_family_v2"].eq("EXCLUDED_TRIAL_JUMPOUT"), "class_model_confidence_v2"] = "EXCLUDED"

df["built_at"] = datetime.now().isoformat(timespec="seconds")
df.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_loaded", "value": len(df)},
    {"metric": "rows_usable_class", "value": int(df["is_class_usable_v2"].sum())},
    {"metric": "rows_excluded_trial_jumpout", "value": int(df["is_excluded_from_class_model_v2"].sum())},
    {"metric": "rows_unresolved_family", "value": int(df["class_model_family_v2"].eq("UNRESOLVED").sum())},
    {"metric": "benchmark_rows", "value": int(df["class_model_family_v2"].eq("BENCHMARK").sum())},
    {"metric": "class_rows", "value": int(df["class_model_family_v2"].eq("CLASS").sum())},
    {"metric": "maiden_rows", "value": int(df["class_model_family_v2"].eq("MAIDEN").sum())},
    {"metric": "blacktype_rows", "value": int(df["class_model_family_v2"].eq("BLACKTYPE").sum())},
    {"metric": "jumps_or_highweight_rows", "value": int(df["class_model_family_v2"].eq("JUMPS_OR_HIGHWEIGHT").sum())},
    {"metric": "regional_restricted_rows", "value": int(df["class_model_family_v2"].eq("REGIONAL_RESTRICTED").sum())},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
