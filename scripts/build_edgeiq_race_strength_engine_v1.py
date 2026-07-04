import os
import re
import math
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

SRC = os.path.join(DATA, "edgeiq_racingcom_results_warehouse_v1.csv")
OUT = os.path.join(DATA, "edgeiq_race_strength_v1.csv")
HORSE_OUT = os.path.join(DATA, "edgeiq_horse_results_power_ratings_v1.csv")
AUDIT = os.path.join(DATA, "edgeiq_race_strength_v1_audit.csv")

print("=" * 100)
print("EDGEIQ RACE STRENGTH ENGINE V1")
print("=" * 100)
print(f"SRC: {SRC}")

if not os.path.exists(SRC):
    raise FileNotFoundError(f"Missing results warehouse: {SRC}")

df = pd.read_csv(SRC, dtype=str).fillna("")

def clean_key(x):
    x = str(x).upper().strip()
    x = re.sub(r"\([^)]*\)", "", x)
    x = re.sub(r"[^A-Z0-9]+", "", x)
    return x

def num(x):
    s = str(x).strip().replace("$", "").replace(",", "")
    if s == "":
        return np.nan
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else np.nan

def finish_num(x):
    s = str(x).strip().upper()
    if s in ["", "SCR", "LSCR", "NP", "DNF", "FF", "F", "BD", "LR"]:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def class_bonus(x):
    s = str(x).upper()
    if "GROUP 1" in s or "G1" in s:
        return 18
    if "GROUP 2" in s or "G2" in s:
        return 14
    if "GROUP 3" in s or "G3" in s:
        return 11
    if "LISTED" in s:
        return 8
    m = re.search(r"BM\s?(\d+)", s)
    if m:
        return max(-4, min(10, (float(m.group(1)) - 58) / 4))
    if "MAIDEN" in s or "MDN" in s:
        return -8
    return 0

required = ["meeting_date", "track", "race_no", "horseName"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce")
df["race_no_num"] = df["race_no"].apply(num)
df["horse_key_calc"] = df.get("horseKey", df["horseName"]).apply(clean_key)
df["finish_num"] = df["finishPosition"].apply(finish_num)
df["margin_num"] = df["margin"].apply(num) if "margin" in df.columns else np.nan
df["sp_num"] = df["sp"].apply(num) if "sp" in df.columns else np.nan
df["distance_num"] = df["distance"].apply(num) if "distance" in df.columns else np.nan
df["race_class_bonus"] = df["raceClass"].apply(class_bonus) if "raceClass" in df.columns else 0

df = df.dropna(subset=["meeting_date", "race_no_num"])
df["race_key"] = (
    df["meeting_date"].dt.strftime("%Y-%m-%d") + "|" +
    df["track"].str.upper().str.strip() + "|R" +
    df["race_no_num"].astype(int).astype(str)
)

active = df[df["finish_num"].notna()].copy()
active = active[active["horse_key_calc"] != ""].copy()
active = active.sort_values(["meeting_date", "track", "race_no_num", "finish_num"])

ratings = {}
starts = {}
race_rows = []
horse_snapshots = []

for race_key, g in active.groupby("race_key", sort=False):
    g = g.copy()
    date = g["meeting_date"].iloc[0]
    track = g["track"].iloc[0]
    race_no = int(g["race_no_num"].iloc[0])
    distance = g["distance_num"].dropna().iloc[0] if g["distance_num"].notna().any() else np.nan
    race_class = g["raceClass"].iloc[0] if "raceClass" in g.columns else ""
    condition = g["trackCondition"].iloc[0] if "trackCondition" in g.columns else ""

    field_size = len(g)
    g["pre_rating"] = g["horse_key_calc"].map(lambda h: ratings.get(h, 50.0))
    g["prior_starts"] = g["horse_key_calc"].map(lambda h: starts.get(h, 0))

    reliable = g[g["prior_starts"] >= 1]
    strength_base = reliable if len(reliable) >= max(3, field_size * 0.35) else g

    winner_rating = g.loc[g["finish_num"] == 1, "pre_rating"].mean()
    top3_avg_rating = g[g["finish_num"] <= 3]["pre_rating"].mean()
    field_avg_rating = strength_base["pre_rating"].mean()
    field_rating_stddev = strength_base["pre_rating"].std(ddof=0)

    class_adj = float(g["race_class_bonus"].mean()) if "race_class_bonus" in g.columns else 0.0
    depth_bonus = min(5.0, max(0.0, (field_size - 6) * 0.55))
    reliability = min(1.0, len(reliable) / max(1, field_size))

    raw_strength = field_avg_rating + (field_rating_stddev * 0.22 if not pd.isna(field_rating_stddev) else 0) + class_adj + depth_bonus
    field_strength_score = round(raw_strength, 3)

    race_rows.append({
        "race_key": race_key,
        "meeting_date": date.strftime("%Y-%m-%d"),
        "track": track,
        "race_no": race_no,
        "distance": distance,
        "raceClass": race_class,
        "trackCondition": condition,
        "field_size": field_size,
        "rated_field_size": len(reliable),
        "rating_reliability": round(reliability, 3),
        "winner_rating": round(winner_rating, 3) if not pd.isna(winner_rating) else "",
        "top3_avg_rating": round(top3_avg_rating, 3) if not pd.isna(top3_avg_rating) else "",
        "field_avg_rating": round(field_avg_rating, 3) if not pd.isna(field_avg_rating) else "",
        "field_rating_stddev": round(field_rating_stddev, 3) if not pd.isna(field_rating_stddev) else "",
        "field_strength_score": field_strength_score,
    })

    for _, r in g.iterrows():
        h = r["horse_key_calc"]
        finish = r["finish_num"]
        margin = r["margin_num"]
        sp = r["sp_num"]
        pre = ratings.get(h, 50.0)

        pos_score = 78 - ((finish - 1) * 4.5)
        margin_penalty = 0 if pd.isna(margin) else min(18, margin * 1.8)
        sp_bonus = 0 if pd.isna(sp) or sp <= 0 else max(-4, min(5, 4 - math.log(sp)))
        perf = pos_score - margin_penalty + sp_bonus + class_adj
        perf = max(25, min(95, perf))

        new_rating = (pre * 0.82) + (perf * 0.18)
        ratings[h] = new_rating
        starts[h] = starts.get(h, 0) + 1

        horse_snapshots.append({
            "meeting_date": date.strftime("%Y-%m-%d"),
            "race_key": race_key,
            "horse": r["horseName"],
            "horse_key": h,
            "finish": finish,
            "margin": margin,
            "pre_rating": round(pre, 3),
            "performance_rating": round(perf, 3),
            "post_rating": round(new_rating, 3),
            "career_starts_seen": starts[h],
        })

race_df = pd.DataFrame(race_rows)

if race_df.empty:
    raise RuntimeError("No race strength rows built.")

race_df["field_strength_percentile"] = (race_df["field_strength_score"].rank(pct=True) * 100).round(2)

def band(p):
    if p >= 95:
        return "ELITE"
    if p >= 85:
        return "VERY_STRONG"
    if p >= 70:
        return "STRONG"
    if p >= 45:
        return "SOLID"
    if p >= 25:
        return "WEAK"
    return "VERY_WEAK"

race_df["race_strength_band"] = race_df["field_strength_percentile"].apply(band)

horse_df = pd.DataFrame(horse_snapshots)
latest_horse = (
    horse_df.sort_values(["horse_key", "meeting_date", "race_key"])
    .groupby("horse_key", as_index=False)
    .tail(1)
    .sort_values("post_rating", ascending=False)
)

audit = pd.DataFrame([{
    "source_rows": len(df),
    "active_runner_rows": len(active),
    "race_strength_rows": len(race_df),
    "unique_races": race_df["race_key"].nunique(),
    "unique_horses_rated": len(latest_horse),
    "avg_strength": round(race_df["field_strength_score"].mean(), 3),
    "min_strength": round(race_df["field_strength_score"].min(), 3),
    "max_strength": round(race_df["field_strength_score"].max(), 3),
}])

race_df.to_csv(OUT, index=False)
latest_horse.to_csv(HORSE_OUT, index=False)
audit.to_csv(AUDIT, index=False)

print("")
print("DONE")
print(f"WROTE: {OUT}")
print(f"WROTE: {HORSE_OUT}")
print(f"WROTE: {AUDIT}")
print("")
print(audit.to_string(index=False))
print("")
print("TOP 20 STRONGEST RACES")
print(race_df.sort_values("field_strength_score", ascending=False).head(20)[[
    "meeting_date","track","race_no","raceClass","field_size",
    "field_strength_score","field_strength_percentile","race_strength_band"
]].to_string(index=False))
