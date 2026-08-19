from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT = DATA / "edgeiq_pricing_replay_spine_v4_tab_quality.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_spine_v4_tab_quality_summary.csv"
AUDIT = DATA / "edgeiq_pricing_replay_spine_v4_tab_quality_audit.csv"

TAB_TRACK_HINTS = [
    "FLEMINGTON",
    "CAULFIELD",
    "THE VALLEY",
    "MOONEE VALLEY",
    "SANDOWN",
    "PAKENHAM",
    "CRANBOURNE",
    "BALLARAT",
    "BENDIGO",
    "GEELONG",
    "SEYMOUR",
    "WARRNAMBOOL",
    "SALE",
    "MORNINGTON",
    "DONALD",
    "ARARAT",
    "STAWELL",
    "TERANG",
    "HAMILTON",
    "KYNETON",
    "COLAC",
    "CASTERTON",
    "WANGARATTA",
    "WODONGA",
    "ECHUCA",
    "BENALLA",
    "MILDURA",
    "KILMORE",
    "YARRA VALLEY",
    "BAIRNSDALE",
    "SWAN HILL",
    "HORSHAM",
    "WERRIBEE",
    "MOE"
]

EXCLUDE_TRACK_HINTS = [
    "BALNARRING",
    "WOOLAMAI",
    "HEALESVILLE",
    "YEA",
    "HANGING ROCK",
    "ALEXANDRA",
    "DROUIN",
    "BUCHAN",
    "MERTON",
    "DEDERANG",
    "HINNOMUNJIE",
    "MANSFIELD",
    "SWIFTS CREEK",
    "TOWONG"
]

print("[PRICING_REPLAY_SPINE_V4_TAB_QUALITY] START")

df = pd.read_csv(SRC, low_memory=False)

df["race_date"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.date.astype("string")
df["track_clean"] = df["track"].astype(str).str.upper().str.strip()
df["race_no_clean"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64").astype("string")
df["horse_clean"] = df["horse"].astype(str).str.upper().str.strip()

df["_race_group_v4"] = (
    df["race_date"].fillna("") + "|" +
    df["track_clean"].fillna("") + "|" +
    df["race_no_clean"].fillna("")
)

df["derived_field_size_v4"] = (
    df.groupby("_race_group_v4")["horse"]
    .transform("count")
)

df["sp_price"] = pd.to_numeric(df["sp_num_settled"], errors="coerce")
df["market_price"] = df["sp_price"]
df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
df["rating_v4"] = pd.to_numeric(df["governed_projection_rating_v6"], errors="coerce")

def is_tab_track(track):
    if any(x in track for x in EXCLUDE_TRACK_HINTS):
        return False
    return any(x in track for x in TAB_TRACK_HINTS)

df["tab_track_flag_v4"] = df["track_clean"].apply(is_tab_track)

df["valid_winner_race_v4"] = (
    df.groupby("_race_group_v4")["won"]
    .transform("sum")
    .eq(1)
)

df["valid_sp_v4"] = df["sp_price"].notna() & (df["sp_price"] > 1)
df["valid_rating_v4"] = df["rating_v4"].notna()

df["tab_quality_flag_v4"] = (
    df["tab_track_flag_v4"] &
    df["derived_field_size_v4"].ge(6) &
    df["valid_winner_race_v4"] &
    df["valid_sp_v4"] &
    df["valid_rating_v4"]
)

out = df[df["tab_quality_flag_v4"]].copy()

out = out[
    [
        "race_date",
        "track",
        "race_no",
        "horse",
        "won",
        "finish_position",
        "sp_price",
        "market_price",
        "rating_v4",
        "derived_field_size_v4",
        "_race_group_v4",
        "tab_track_flag_v4",
        "valid_winner_race_v4",
        "valid_sp_v4",
        "valid_rating_v4",
        "tab_quality_flag_v4"
    ]
].rename(columns={
    "rating_v4": "rating",
    "derived_field_size_v4": "field_size"
})

out["source_quality"] = "TAB_QUALITY_REPLAY_V4"
out["production_changed"] = "NO"
out["built_at"] = datetime.now(timezone.utc).isoformat()

out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"check": "source_rows", "rows": len(df)},
    {"check": "source_races", "rows": df["_race_group_v4"].nunique()},
    {"check": "tab_track_rows", "rows": int(df["tab_track_flag_v4"].sum())},
    {"check": "field_size_ge_6_rows", "rows": int(df["derived_field_size_v4"].ge(6).sum())},
    {"check": "valid_winner_rows", "rows": int(df["valid_winner_race_v4"].sum())},
    {"check": "valid_sp_rows", "rows": int(df["valid_sp_v4"].sum())},
    {"check": "valid_rating_rows", "rows": int(df["valid_rating_v4"].sum())},
    {"check": "tab_quality_rows", "rows": len(out)},
    {"check": "tab_quality_races", "rows": out["_race_group_v4"].nunique()},
])

audit.to_csv(AUDIT, index=False)

field_dist = (
    out["field_size"]
    .value_counts()
    .sort_index()
    .reset_index()
)
field_dist.columns = ["field_size", "rows"]

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "source_rows": len(df),
    "source_races": df["_race_group_v4"].nunique(),
    "tab_quality_rows": len(out),
    "tab_quality_races": out["_race_group_v4"].nunique(),
    "avg_field_size": round(float(out["field_size"].mean()), 2) if len(out) else 0,
    "min_field_size": int(out["field_size"].min()) if len(out) else 0,
    "max_field_size": int(out["field_size"].max()) if len(out) else 0,
    "status": "TAB_QUALITY_PRICING_REPLAY_SPINE_V4_BUILT_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[PRICING_REPLAY_SPINE_V4_TAB_QUALITY] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print("")
print(summary.to_string(index=False))
print("")
print("[AUDIT]")
print(audit.to_string(index=False))
print("")
print("[FIELD_SIZE]")
print(field_dist.to_string(index=False))
