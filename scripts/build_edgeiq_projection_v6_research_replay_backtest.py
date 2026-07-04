import os
import json
import pandas as pd
import numpy as np

ROOT = os.getcwd()
DATA = os.path.join(ROOT, "public", "data")

V5_FILE = os.path.join(DATA, "edgeiq_historical_performance_rating_v5_1.csv")
V6_FILE = os.path.join(DATA, "edgeiq_historical_performance_rating_v6_research.csv")

OUT_DETAIL = os.path.join(DATA, "edgeiq_projection_v6_research_backtest.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_projection_v6_research_backtest_summary.csv")
OUT_BY_BAND = os.path.join(DATA, "edgeiq_projection_v6_research_backtest_by_band.csv")
OUT_VS_PROD = os.path.join(DATA, "edgeiq_projection_v6_research_backtest_vs_production.csv")
OUT_GAPS = os.path.join(DATA, "edgeiq_projection_v6_research_backtest_gap_buckets.csv")
OUT_JSON = os.path.join(DATA, "edgeiq_projection_v6_research_backtest_summary.json")

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

def gap_bucket(g):
    if pd.isna(g): return "NO_MODEL"
    a = abs(float(g))
    if a < 2: return "0-2"
    if a < 4: return "2-4"
    if a < 6: return "4-6"
    if a < 8: return "6-8"
    if a < 10: return "8-10"
    return "10+"

def model_frame(df, model, rating_col):
    out = df.copy()

    out["model"] = model
    out["horse_key"] = out["horse"].apply(clean)
    out["race_key"] = make_race_key(out)

    out["rating"] = n(out[rating_col])
    out["finish_position_num"] = n(out["finish_position"])
    out["field_size"] = n(out["real_field_size"])

    out = out[out["rating"].notna()].copy()
    out = out[out["finish_position_num"].notna()].copy()
    out = out[out["race_key"].notna()].copy()

    out["won"] = (out["finish_position_num"] == 1).astype(int)
    out["placed"] = np.where(
        out["field_size"] >= 8,
        (out["finish_position_num"] <= 3).astype(int),
        (out["finish_position_num"] <= 2).astype(int)
    )

    out["race_runner_count"] = out.groupby("race_key")["horse_key"].transform("count")
    out = out[out["race_runner_count"] >= 4].copy()

    out["race_median_rating"] = out.groupby("race_key")["rating"].transform("median")
    out["race_avg_rating"] = out.groupby("race_key")["rating"].transform("mean")
    out["rating_gap"] = out["rating"] - out["race_median_rating"]

    out["rank"] = out.groupby("race_key")["rating"].rank(method="first", ascending=False)

    out["projection_band"] = out["rating_gap"].apply(band)
    out["gap_bucket"] = out["rating_gap"].apply(gap_bucket)

    def probs(g):
        gaps = (g["rating"] - g["rating"].median()).fillna(-99)
        raw = np.exp(np.clip(gaps * POWER / 10.0, -20, 20))
        p = raw / raw.sum()
        p = np.minimum(p, PROB_CAP)
        p = p / p.sum()
        return pd.Series(p, index=g.index)

    out["model_prob"] = out.groupby("race_key", group_keys=False).apply(probs)
    out["fair_price"] = np.where(out["model_prob"] > 0, 1 / out["model_prob"], np.nan)

    return out

def summary(df):
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
            "avg_rating": round(g["rating"].mean(), 4),
            "max_rating": round(g["rating"].max(), 4),
            "elite_count": int((g["projection_band"] == "ELITE").sum()),
            "strong_count": int((g["projection_band"] == "STRONG").sum()),
            "positive_count": int((g["projection_band"] == "POSITIVE").sum()),
            "ten_plus_gap_count": int((g["gap_bucket"] == "10+").sum()),
            "max_gap": round(g["rating_gap"].max(), 4),
            "avg_rank1_fair_price": round(r1["fair_price"].mean(), 4),
            "min_rank1_fair_price": round(r1["fair_price"].min(), 4),
        })
    return pd.DataFrame(rows)

def by_band(df):
    rows = []
    order = ["ELITE","STRONG","POSITIVE","NEUTRAL","NEGATIVE","POOR","NO_MODEL"]
    for (model, b), g in df.groupby(["model","projection_band"]):
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
    return pd.DataFrame(rows).sort_values(["model","band_order"]).drop(columns=["band_order"])

def by_gap(df):
    rows = []
    order = ["0-2","2-4","4-6","6-8","8-10","10+","NO_MODEL"]
    for (model, b), g in df.groupby(["model","gap_bucket"]):
        rows.append({
            "model": model,
            "gap_bucket": b,
            "bucket_order": order.index(b) if b in order else 99,
            "runners": len(g),
            "wins": int(g["won"].sum()),
            "places": int(g["placed"].sum()),
            "win_pct": round(g["won"].mean() * 100, 2),
            "place_pct": round(g["placed"].mean() * 100, 2),
            "avg_gap": round(g["rating_gap"].mean(), 4),
            "avg_fair_price": round(g["fair_price"].mean(), 4),
        })
    return pd.DataFrame(rows).sort_values(["model","bucket_order"]).drop(columns=["bucket_order"])

def main():
    print("[V6_RESEARCH_BACKTEST] START")

    v5 = pd.read_csv(V5_FILE, low_memory=False)
    v6 = pd.read_csv(V6_FILE, low_memory=False)

    required = ["horse","race_date","track","distance","finish_position","real_field_size"]
    for c in required:
        if c not in v5.columns:
            raise RuntimeError(f"V5 missing required column: {c}")
        if c not in v6.columns:
            raise RuntimeError(f"V6 missing required column: {c}")

    v5_bt = model_frame(v5, "V5_1_PRODUCTION_SCALE", "performance_rating_v5_1")
    v6_bt = model_frame(v6, "V6_RESEARCH_SCALE", "performance_rating_v6_research")

    combined = pd.concat([v5_bt, v6_bt], ignore_index=True, sort=False)

    detail_cols = [
        "model","race_key","race_date","track","distance","race_name",
        "horse","horse_key","finish_position_num","field_size",
        "rating","race_median_rating","race_avg_rating","rating_gap",
        "rank","projection_band","gap_bucket","model_prob","fair_price",
        "won","placed"
    ]
    detail_cols = [c for c in detail_cols if c in combined.columns]

    combined[detail_cols].to_csv(OUT_DETAIL, index=False)

    s = summary(combined)
    s.to_csv(OUT_SUMMARY, index=False)

    bb = by_band(combined)
    bb.to_csv(OUT_BY_BAND, index=False)

    bg = by_gap(combined)
    bg.to_csv(OUT_GAPS, index=False)

    prod = s[s["model"] == "V5_1_PRODUCTION_SCALE"].iloc[0].to_dict()
    res = s[s["model"] == "V6_RESEARCH_SCALE"].iloc[0].to_dict()

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
        comp.append({"metric": k, "production_v5_1": a, "v6_research": b, "delta": delta})

    pd.DataFrame(comp).to_csv(OUT_VS_PROD, index=False)

    payload = {
        "status": "COMPLETE",
        "note": "No SP/ROI available in these rating files. This backtest validates rank/order/band outcomes only.",
        "race_key": "race_date|track|distance|race_name|race_class_clean|condition_recovered",
        "power": POWER,
        "prob_cap": PROB_CAP,
        "outputs": {
            "detail": OUT_DETAIL,
            "summary": OUT_SUMMARY,
            "by_band": OUT_BY_BAND,
            "gap_buckets": OUT_GAPS,
            "vs_production": OUT_VS_PROD
        },
        "summary": s.to_dict(orient="records")
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("[V6_RESEARCH_BACKTEST] COMPLETE")
    print(s.to_string(index=False))

if __name__ == "__main__":
    main()
