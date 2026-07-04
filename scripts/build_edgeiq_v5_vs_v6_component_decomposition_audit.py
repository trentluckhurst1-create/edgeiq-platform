import os
import re
import pandas as pd

ROOT = os.getcwd()
DATA = os.path.join(ROOT, "public", "data")

V5 = os.path.join(DATA, "edgeiq_historical_performance_rating_v5_1.csv")
V6 = os.path.join(DATA, "edgeiq_historical_performance_rating_v6_research.csv")
DAMAGED = os.path.join(DATA, "v6_damaged_winner_cases.csv")

OUT = os.path.join(DATA, "edgeiq_v5_vs_v6_component_decomposition_damaged_winners_v1.csv")
SUMMARY = os.path.join(DATA, "edgeiq_v5_vs_v6_component_decomposition_damaged_winners_v1_summary.csv")

def n(x):
    return pd.to_numeric(x, errors="coerce")

def clean(x):
    return str(x).upper().strip()

def extract_v6_reason(reason, key):
    if pd.isna(reason):
        return None
    s = str(reason)
    m = re.search(rf"{re.escape(key)}=([-+]?\d+(?:\.\d+)?)", s)
    if not m:
        return None
    return float(m.group(1))

v5 = pd.read_csv(V5, low_memory=False)
v6 = pd.read_csv(V6, low_memory=False)
damaged = pd.read_csv(DAMAGED, low_memory=False)

for df in [v5, v6]:
    df["horse_key"] = df["horse"].apply(clean)
    df["race_date_key"] = df["race_date"].astype(str).str[:10]
    df["track_key"] = df["track"].astype(str).str.upper().str.strip()
    df["distance_key"] = n(df["distance"]).round(0).astype("Int64").astype(str)

damaged["horse_key"] = damaged["v5_horse"].apply(clean)
damaged["track_key"] = damaged["v5_track"].astype(str).str.upper().str.strip()
damaged["distance_key"] = n(damaged["v5_distance"]).round(0).astype("Int64").astype(str)

v5_cols = [
    "horse_key","race_date_key","track_key","distance_key",
    "performance_rating_v3",
    "performance_rating_base_v5_1",
    "class_quality_adjustment_v5_1",
    "finish_quality_multiplier_v5_1",
    "field_size_adjustment_v5_1",
    "performance_rating_v5_1",
    "rating_v5_1_status",
    "margin",
    "finish_position",
    "real_field_size",
    "race_class_clean",
    "race_class_clean_v3_3",
    "condition_recovered",
    "performance_reason_v3"
]
v5_cols = [c for c in v5_cols if c in v5.columns]

v6_cols = [
    "horse_key","race_date_key","track_key","distance_key",
    "performance_rating_v6_research",
    "performance_rating_v6_research_reason",
    "research_delta_v6_minus_v5_1"
]
v6_cols = [c for c in v6_cols if c in v6.columns]

m = damaged.merge(
    v5[v5_cols],
    on=["horse_key","track_key","distance_key"],
    how="left",
    suffixes=("","_v5row")
)

m = m.merge(
    v6[v6_cols],
    on=["horse_key","track_key","distance_key"],
    how="left",
    suffixes=("","_v6row")
)

m["v5_rating_actual"] = n(m["performance_rating_v5_1"])
m["v6_rating_actual"] = n(m["performance_rating_v6_research"])
m["rating_delta_v6_minus_v5"] = m["v6_rating_actual"] - m["v5_rating_actual"]

if "performance_rating_v6_research_reason" in m.columns:
    m["v6_base"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract_v6_reason(x, "v6_base"))
    m["v6_field_adj"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract_v6_reason(x, "field_adj"))
    m["v6_class_adj"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract_v6_reason(x, "class_adj"))
    m["v6_margin"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract_v6_reason(x, "margin"))
    m["v6_margin_penalty"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract_v6_reason(x, "margin_penalty"))

m["v5_class_adj"] = n(m.get("class_quality_adjustment_v5_1"))
m["v5_finish_multiplier"] = n(m.get("finish_quality_multiplier_v5_1"))
m["v5_field_adj"] = n(m.get("field_size_adjustment_v5_1"))
m["v5_base"] = n(m.get("performance_rating_base_v5_1"))

m["base_delta_v6_minus_v5"] = m["v6_base"] - m["v5_base"]
m["field_delta_v6_minus_v5"] = m["v6_field_adj"] - m["v5_field_adj"]
m["class_delta_v6_minus_v5"] = m["v6_class_adj"] - m["v5_class_adj"]

m = m.sort_values("rating_delta_v6_minus_v5")

m.to_csv(OUT, index=False)

summary_rows = []

summary_rows.append({"metric":"rows", "value":len(m)})
summary_rows.append({"metric":"avg_rating_delta_v6_minus_v5", "value":round(m["rating_delta_v6_minus_v5"].mean(),4)})
summary_rows.append({"metric":"min_rating_delta_v6_minus_v5", "value":round(m["rating_delta_v6_minus_v5"].min(),4)})
summary_rows.append({"metric":"max_rating_delta_v6_minus_v5", "value":round(m["rating_delta_v6_minus_v5"].max(),4)})
summary_rows.append({"metric":"avg_base_delta_v6_minus_v5", "value":round(m["base_delta_v6_minus_v5"].mean(),4)})
summary_rows.append({"metric":"avg_field_delta_v6_minus_v5", "value":round(m["field_delta_v6_minus_v5"].mean(),4)})
summary_rows.append({"metric":"avg_class_delta_v6_minus_v5", "value":round(m["class_delta_v6_minus_v5"].mean(),4)})
summary_rows.append({"metric":"avg_v6_margin_penalty", "value":round(m["v6_margin_penalty"].mean(),4)})
summary_rows.append({"metric":"avg_v5_finish_multiplier", "value":round(m["v5_finish_multiplier"].mean(),4)})

pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

print("[V5_V6_COMPONENT_DECOMPOSITION_DAMAGED_WINNERS] COMPLETE")
print(pd.DataFrame(summary_rows).to_string(index=False))
