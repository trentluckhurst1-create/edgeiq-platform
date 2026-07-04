import os
import re
import pandas as pd

ROOT = os.getcwd()
DATA = os.path.join(ROOT, "public", "data")

V5 = os.path.join(DATA, "edgeiq_historical_performance_rating_v5_1.csv")
V6 = os.path.join(DATA, "edgeiq_historical_performance_rating_v6_research.csv")
DAMAGED = os.path.join(DATA, "v6_damaged_winner_cases.csv")

OUT = os.path.join(DATA, "edgeiq_v5_vs_v6_component_decomposition_damaged_winners_v2.csv")
SUMMARY = os.path.join(DATA, "edgeiq_v5_vs_v6_component_decomposition_damaged_winners_v2_summary.csv")

def n(x):
    return pd.to_numeric(x, errors="coerce")

def clean(x):
    return str(x).upper().strip()

def extract(reason, key):
    if pd.isna(reason):
        return None
    s = str(reason)
    m = re.search(rf"{re.escape(key)}=([-+]?\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None

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

# recover date from source switch file by joining damaged winner case back to head-to-head file
h2h = pd.read_csv(os.path.join(DATA, "edgeiq_v6_vs_v5_prior_rank1_head_to_head.csv"), low_memory=False)
h2h["horse_key"] = h2h["v5_horse"].apply(clean)
h2h["track_key"] = h2h["v5_track"].astype(str).str.upper().str.strip()
h2h["distance_key"] = n(h2h["v5_distance"]).round(0).astype("Int64").astype(str)
h2h["race_date_key"] = h2h["v5_race_date"].astype(str).str[:10]

damaged = damaged.merge(
    h2h[["horse_key","track_key","distance_key","race_date_key"]],
    on=["horse_key","track_key","distance_key"],
    how="left"
).drop_duplicates()

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
    on=["horse_key","race_date_key","track_key","distance_key"],
    how="left"
)

m = m.merge(
    v6[v6_cols],
    on=["horse_key","race_date_key","track_key","distance_key"],
    how="left"
)

m["v5_rating_actual"] = n(m["performance_rating_v5_1"])
m["v6_rating_actual"] = n(m["performance_rating_v6_research"])
m["rating_delta_v6_minus_v5"] = m["v6_rating_actual"] - m["v5_rating_actual"]

m["v6_base"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract(x, "v6_base"))
m["v6_field_adj"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract(x, "field_adj"))
m["v6_class_adj"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract(x, "class_adj"))
m["v6_margin_penalty"] = m["performance_rating_v6_research_reason"].apply(lambda x: extract(x, "margin_penalty"))

m["v5_class_adj"] = n(m.get("class_quality_adjustment_v5_1"))
m["v5_finish_multiplier"] = n(m.get("finish_quality_multiplier_v5_1"))
m["v5_field_adj"] = n(m.get("field_size_adjustment_v5_1"))
m["v5_base"] = n(m.get("performance_rating_base_v5_1"))

m["base_delta_v6_minus_v5"] = m["v6_base"] - m["v5_base"]
m["field_delta_v6_minus_v5"] = m["v6_field_adj"] - m["v5_field_adj"]
m["class_delta_v6_minus_v5"] = m["v6_class_adj"] - m["v5_class_adj"]

m = m.sort_values("rating_delta_v6_minus_v5")
m.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric":"rows", "value":len(m)},
    {"metric":"matched_v5_rows", "value":int(m["v5_rating_actual"].notna().sum())},
    {"metric":"matched_v6_rows", "value":int(m["v6_rating_actual"].notna().sum())},
    {"metric":"avg_rating_delta_v6_minus_v5", "value":round(m["rating_delta_v6_minus_v5"].mean(),4)},
    {"metric":"avg_base_delta_v6_minus_v5", "value":round(m["base_delta_v6_minus_v5"].mean(),4)},
    {"metric":"avg_field_delta_v6_minus_v5", "value":round(m["field_delta_v6_minus_v5"].mean(),4)},
    {"metric":"avg_class_delta_v6_minus_v5", "value":round(m["class_delta_v6_minus_v5"].mean(),4)},
    {"metric":"avg_v6_margin_penalty", "value":round(m["v6_margin_penalty"].mean(),4)},
    {"metric":"avg_v5_finish_multiplier", "value":round(m["v5_finish_multiplier"].mean(),4)},
])

summary.to_csv(SUMMARY, index=False)

print("[V5_V6_COMPONENT_DECOMPOSITION_DAMAGED_WINNERS_V2] COMPLETE")
print(summary.to_string(index=False))
