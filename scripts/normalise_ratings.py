import numpy as np
import pandas as pd

print("=" * 80)
print("NORMALISE RATINGS - SOFTMAX MARKET SHAPE")
print("=" * 80)

PATH = "public/data/ratings_final_v2.csv"
MARKET_TEMPERATURE = 11.0
UNIFORM_BLEND = 0.24


def boolish_value(x):
    return str(x).strip().lower() in {"1", "true", "yes", "y"}


def apply_race_softmax_prices(df):
    df = df.copy()
    if "is_scratched" not in df.columns:
        df["is_scratched"] = 0
    df["is_scratched_bool"] = df["is_scratched"].apply(boolish_value)
    df["rating_sum"] = np.nan
    df["prob"] = np.nan

    for race_id, g in df.groupby("race_id", dropna=False):
        live = g[(~g["is_scratched_bool"]) & pd.to_numeric(g["elite_today_rating"], errors="coerce").notna()].copy()
        if live.empty:
            continue
        ratings = pd.to_numeric(live["elite_today_rating"], errors="coerce").astype(float)
        if len(live) == 1:
            probs = np.array([1.0])
        else:
            centered = ((ratings - ratings.max()) / MARKET_TEMPERATURE).clip(-6, 6)
            weights = np.exp(centered)
            softmax = weights / weights.sum()
            uniform = np.ones(len(live)) / len(live)
            probs = ((1 - UNIFORM_BLEND) * softmax) + (UNIFORM_BLEND * uniform)
            probs = probs / probs.sum()
        df.loc[live.index, "rating_sum"] = float(ratings.sum())
        df.loc[live.index, "prob"] = probs

    df["elite_rated_price"] = np.where(df["prob"] > 0, 1 / df["prob"], np.nan)
    df.loc[df["is_scratched_bool"], "elite_rated_price"] = np.nan
    df["elite_rated_price"] = pd.to_numeric(df["elite_rated_price"], errors="coerce").round(3)
    return df


df = pd.read_csv(PATH, low_memory=False)

for col in ["elite_today_rating", "form_rating", "runs_used"]:
    if col not in df.columns:
        df[col] = np.nan

# Keep the full model rating from build_final_ratings.py. Only repair missing values.
df["form_rating"] = pd.to_numeric(df["form_rating"], errors="coerce").fillna(55.0)
df["runs_used"] = pd.to_numeric(df["runs_used"], errors="coerce").fillna(0).astype(int)
df["elite_today_rating"] = pd.to_numeric(df["elite_today_rating"], errors="coerce").fillna(df["form_rating"]).clip(35, 120)

df["race_date"] = pd.to_datetime(df["race_date"], errors="coerce").dt.date
df["track"] = df["track"].astype(str).str.upper().str.strip()
df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce")
df["race_id"] = df["race_date"].astype(str) + "_" + df["track"] + "_" + df["race_no"].astype(str)
df = apply_race_softmax_prices(df)

df.to_csv(PATH, index=False)

live = df[~df["is_scratched_bool"]].copy()
print("SAVED:", PATH)
print("ROWS:", len(df))
print("SCRATCHED:", int(df["is_scratched_bool"].sum()))
print("TRUE FORM MATCHED:", int((df["runs_used"] > 0).sum()))
print("BASELINE / NO HISTORY:", int((df["runs_used"] == 0).sum()))
print("PRICE RANGE LIVE:", round(float(live["elite_rated_price"].min()), 3) if len(live) else None, "to", round(float(live["elite_rated_price"].max()), 3) if len(live) else None)
print("PROB SUM CHECK SAMPLE:")
print(live.groupby("race_id")["prob"].sum().head(12).round(6).to_string())
print("\nSAMPLE:")
print(df[["horse", "is_scratched", "form_rating", "runs_used", "elite_today_rating", "prob", "elite_rated_price"]].head(20).to_string(index=False))
