import os
import json
import pandas as pd
import numpy as np

ROOT = os.getcwd()
DATA = os.path.join(ROOT, "public", "data")

V5_FILE = os.path.join(DATA, "edgeiq_historical_performance_rating_v5_1.csv")
V6_FILE = os.path.join(DATA, "edgeiq_historical_performance_rating_v6_1_research.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_projection_v6_1_research_prior_rating_backtest.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_projection_v6_1_research_prior_rating_backtest_summary.csv")
OUT_BY_BAND = os.path.join(DATA, "edgeiq_projection_v6_1_research_prior_rating_backtest_by_band.csv")
OUT_VS_PROD = os.path.join(DATA, "edgeiq_projection_v6_1_research_prior_rating_backtest_vs_production.csv")
OUT_JSON = os.path.join(DATA, "edgeiq_projection_v6_1_research_prior_rating_backtest_summary.json")

POWER = 0.55
PROB_CAP = 0.35

def n(x):
    return pd.to_numeric(x, errors="coerce")

def clean(x):
    return str(x).upper().strip()

def make_race_key(df):
    race_name = df["race_name"].fillna("").astype(str) if "race_name" in df.columns else ""
    race_class = df["race_class_clean"].fillna("").astype(str) if "race_class_clean" in df.columns else ""
    condition = df["condition_recovered"].fillna("").astype(str) if "condition_recovered" in df.columns else ""

    return (
        df["race_date"].astype(str).str[:10] + "|" +
        df["track"].astype(str).str.upper().str.strip() + "|" +
        n(df["distance"]).fillna(0).astype(int).astype(str) + "|" +
        race_name.astype(str).str.upper().str.strip() + "|" +
        race_class.astype(str).str.upper().str.strip() + "|" +
        condition.astype(str).str.upper().str.strip()
    )

def band(g):
    if pd.isna(g): return "NO_MODEL"
    if g >= 10: return "ELITE"
    if g >= 6: return "STRONG"
    if g >= 3: return "POSITIVE"
    if g >= -2: return "NEUTRAL"
    if g >= -5: return "NEGATIVE"
    return "POOR"

def build_prior_model(df, model, rating_col):
    x = df.copy()
    x["race_date_dt"] = pd.to_datetime(x["race_date"], errors="coerce")
    x["horse_key"] = x["horse"].apply(clean)
    x["race_key"] = make_race_key(x)
    x["earned_rating"] = n(x[rating_col])
    x["finish_position_num"] = n(x["finish_position"])
    x["field_size"] = n(x["real_field_size"])

    x = x[x["race_date_dt"].notna()].copy()
    x = x[x["earned_rating"].notna()].copy()
    x = x[x["finish_position_num"].notna()].copy()

    x = x.sort_values(["horse_key", "race_date_dt", "race_key"]).copy()

    x["prior_rating"] = x.groupby("horse_key")["earned_rating"].shift(1)
    x["prior_starts"] = x.groupby("horse_key").cumcount()

    x = x[x["prior_rating"].notna()].copy()

    x["model"] = model
    x["rating"] = x["prior_rating"]

    x["won"] = (x["finish_position_num"] == 1).astype(int)
    x["placed"] = np.where(
        x["field_size"] >= 8,
        (x["finish_position_num"] <= 3).astype(int),
        (x["finish_position_num"] <= 2).astype(int)
    )

    x["race_runner_count"] = x.groupby("race_key")["horse_key"].transform("count")
    x = x[x["race_runner_count"] >= 4].copy()

    x["race_median_rating"] = x.groupby("race_key")["rating"].transform("median")
    x["race_avg_rating"] = x.groupby("race_key")["rating"].transform("mean")
    x["rating_gap"] = x["rating"] - x["race_median_rating"]

    x["rank"] = x.groupby("race_key")["rating"].rank(method="first", ascending=False)
    x["projection_band"] = x["rating_gap"].apply(band)

    def probs(g):
        gaps = (g["rating"] - g["rating"].median()).fillna(-99)
        raw = np.exp(np.clip(gaps * POWER / 10.0, -20, 20))
        p = raw / raw.sum()
        p = np.minimum(p, PROB_CAP)
        p = p / p.sum()
        return pd.Series(p, index=g.index)

    x["model_prob"] = x.groupby("race_key", group_keys=False).apply(probs)
    x["fair_price"] = np.where(x["model_prob"] > 0, 1 / x["model_prob"], np.nan)

    return x

def summarize(df):
    rows = []
    for model, g in df.groupby("model"):
        r1 = g[g["rank"] == 1]
        r2 = g[g["rank"] == 2]
        r3 = g[g["rank"] == 3]
        rows.append({
            "model": model,
            "races": g["race_key"].nunique(),
            "runners": len(g),
            "rank1_count": len(r1),
            "rank1_win_pct": round(r1["won"].mean() * 100, 2),
            "rank1_place_pct": round(r1["placed"].mean() * 100, 2),
            "rank2_win_pct": round(r2["won"].mean() * 100, 2),
            "rank3_win_pct": round(r3["won"].mean() * 100, 2),
            "avg_prior_rating": round(g["rating"].mean(), 4),
            "max_prior_rating": round(g["rating"].max(), 4),
            "elite_count": int((g["projection_band"] == "ELITE").sum()),
            "strong_count": int((g["projection_band"] == "STRONG").sum()),
            "positive_count": int((g["projection_band"] == "POSITIVE").sum()),
            "max_gap": round(g["rating_gap"].max(), 4),
            "avg_rank1_fair_price": round(r1["fair_price"].mean(), 4),
            "min_rank1_fair_price": round(r1["fair_price"].min(), 4),
        })
    return pd.DataFrame(rows)

def by_band(df):
    rows = []
    order = ["ELITE","STRONG","POSITIVE","NEUTRAL","NEGATIVE","POOR","NO_MODEL"]
    for (model, b), g in df.groupby(["model", "projection_band"]):
        rows.append({
            "model": model,
            "projection_band": b,
            "band_order": order.index(b) if b in order else 99,
            "runners": len(g),
            "wins": int(g["won"].sum()),
            "places": int(g["placed"].sum()),
            "win_pct": round(g["won"].mean() * 100, 2),
            "place_pct": round(g["placed"].mean() * 100, 2),
            "avg_gap": round(g["rating_gap"].mean(), 4),
            "avg_fair_price": round(g["fair_price"].mean(), 4),
        })
    return pd.DataFrame(rows).sort_values(["model", "band_order"]).drop(columns=["band_order"])

def main():
    print("[V6_PRIOR_RATING_BACKTEST] START")

    v5 = pd.read_csv(V5_FILE, low_memory=False)
    v6 = pd.read_csv(V6_FILE, low_memory=False)

    v5_bt = build_prior_model(v5, "V5_1_PRODUCTION_PRIOR", "performance_rating_v5_1")
    v6_bt = build_prior_model(v6, "V6_1_RESEARCH_PRIOR", "performance_rating_v6_1_research")

    combined = pd.concat([v5_bt, v6_bt], ignore_index=True, sort=False)

    cols = [
        "model","race_key","race_date","track","distance","race_name",
        "horse","finish_position_num","field_size","prior_starts",
        "earned_rating","prior_rating","rating","race_median_rating",
        "rating_gap","rank","projection_band","model_prob","fair_price",
        "won","placed"
    ]
    cols = [c for c in cols if c in combined.columns]

    combined[cols].to_csv(OUT_DETAIL, index=False)

    s = summarize(combined)
    s.to_csv(OUT_SUMMARY, index=False)

    bb = by_band(combined)
    bb.to_csv(OUT_BY_BAND, index=False)

    prod = s[s["model"] == "V5_1_PRODUCTION_PRIOR"].iloc[0].to_dict()
    res = s[s["model"] == "V6_1_RESEARCH_PRIOR"].iloc[0].to_dict()

    comp = []
    for k in s.columns:
        if k == "model":
            continue
        a = prod.get(k)
        b = res.get(k)
        try:
            delta = round(float(b) - float(a), 4)
        except:
            delta = ""
        comp.append({"metric": k, "production_v5_1_prior": a, "V6_1_RESEARCH_PRIOR": b, "delta": delta})

    pd.DataFrame(comp).to_csv(OUT_VS_PROD, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "status": "COMPLETE",
            "method": "Uses each horse's latest prior earned rating only. Same-race leakage removed.",
            "power": POWER,
            "prob_cap": PROB_CAP,
            "outputs": {
                "detail": OUT_DETAIL,
                "summary": OUT_SUMMARY,
                "by_band": OUT_BY_BAND,
                "vs_production": OUT_VS_PROD
            },
            "summary": s.to_dict(orient="records")
        }, f, indent=2)

    print("[V6_PRIOR_RATING_BACKTEST] COMPLETE")
    print(s.to_string(index=False))

if __name__ == "__main__":
    main()
