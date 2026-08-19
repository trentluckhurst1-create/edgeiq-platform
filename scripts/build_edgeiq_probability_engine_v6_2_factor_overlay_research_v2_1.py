from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA_FILE = DATA / "edgeiq_live_runner_dna_v6_2.csv"
SCORECARD_FILE = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"

OUT = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_1.csv"
SUMMARY = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_1_summary.csv"
BY_FACTOR = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_1_by_factor.csv"
BY_RACE = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_1_by_race.csv"

MISSING_ZERO_NEUTRAL_FACTORS = {"DISTANCE", "CONDITION", "CLASS"}

FACTOR_CONFIG = {
    "CLASS":      {"neg": 53.5, "pos": 77.9, "weight": 1.25},
    "CONDITION":  {"neg": 27.0, "pos": 72.9, "weight": 1.25},
    "DISTANCE":   {"neg": 25.0, "pos": 76.3, "weight": 1.25},
    "FORM":       {"neg": 56.6, "pos": 74.0, "weight": 1.0},
    "RATING":     {"neg": 24.0, "pos": 46.0, "weight": 1.0},
    "SECTIONALS": {"neg": 63.0, "pos": 66.0, "weight": 1.0},
    "TRAINER":    {"neg": 50.0, "pos": 75.0, "weight": 0.5},
    "JOCKEY":     {"neg": 25.0, "pos": 75.0, "weight": 0.5},
    "COMBO":      {"neg": 50.0, "pos": 75.0, "weight": 0.5},
    "PROFILE":    {"neg": 68.0, "pos": 85.0, "weight": 1.0},
}

def num(x):
    try:
        s = str(x).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def txt(row, key):
    return str(row.get(key, "")).strip()

def adj(score):
    if score >= 8:
        return 6
    if score >= 5:
        return 4
    if score >= 2:
        return 2
    if score <= -8:
        return -6
    if score <= -5:
        return -4
    if score <= -2:
        return -2
    return 0

dna = pd.read_csv(DNA_FILE, dtype=str).fillna("")
scorecard = pd.read_csv(SCORECARD_FILE, dtype=str).fillna("")

built_at = datetime.now(timezone.utc).isoformat()

factor_lookup = {}
for _, r in scorecard.iterrows():
    jk = txt(r, "join_key")
    factor = txt(r, "factor").upper()
    factor_lookup.setdefault(jk, {})[factor] = num(r.get("factor_score", ""))

rows = []
factor_rows = []

for _, r in dna.iterrows():
    jk = txt(r, "join_key")
    factors = factor_lookup.get(jk, {})

    overlay = 0.0
    pos = 0
    neg = 0

    for factor, cfg in FACTOR_CONFIG.items():
        score = factors.get(factor, np.nan)
        polarity = "NEUTRAL"
        signal = 0.0

        if not pd.isna(score):
            if factor in MISSING_ZERO_NEUTRAL_FACTORS and score == 0:
                polarity = "NO_PROFILE_NEUTRAL"
                signal = 0.0
            elif score >= cfg["pos"]:
                polarity = "POSITIVE"
                signal = cfg["weight"]
                pos += 1
            elif score < cfg["neg"]:
                polarity = "NEGATIVE"
                signal = -cfg["weight"]
                neg += 1

        overlay += signal

        factor_rows.append({
            "race_date": txt(r, "race_date"),
            "track": txt(r, "track"),
            "race_no": txt(r, "race_no"),
            "horse": txt(r, "horse"),
            "join_key": jk,
            "factor": factor,
            "factor_score": "" if pd.isna(score) else round(score, 3),
            "negative_threshold": cfg["neg"],
            "positive_threshold": cfg["pos"],
            "factor_weight": cfg["weight"],
            "factor_polarity": polarity,
            "weighted_signal": round(signal, 3),
            "built_at": built_at,
        })

    adjustment = adj(overlay)

    fair = num(r.get("fair_price", ""))
    base_prob = np.nan if pd.isna(fair) or fair <= 0 else 1 / fair

    research_prob = np.nan
    research_fair = np.nan

    if not pd.isna(base_prob):
        research_prob = base_prob * (1 + adjustment / 100)
        research_prob = max(0.0001, min(0.95, research_prob))
        research_fair = 1 / research_prob

    row = r.to_dict()
    row["factor_overlay_score_v6_2_v2_1"] = round(overlay, 3)
    row["factor_adjustment_pct_v6_2_v2_1"] = adjustment
    row["positive_factor_total_v6_2_v2_1"] = pos
    row["negative_factor_total_v6_2_v2_1"] = neg
    row["base_probability"] = "" if pd.isna(base_prob) else round(base_prob, 8)
    row["research_probability_v6_2_v2_1"] = "" if pd.isna(research_prob) else round(research_prob, 8)
    row["research_fair_price_v6_2_v2_1"] = "" if pd.isna(research_fair) else round(research_fair, 4)
    row["research_only"] = "YES"
    row["production_prices_changed"] = "NO"
    row["production_probability_changed"] = "NO"
    row["built_at_v6_2_factor_overlay_v2"] = built_at
    rows.append(row)

out = pd.DataFrame(rows)
out["fair_price_num"] = out["fair_price"].apply(num)
out["research_fair_price_v6_2_v2_1_num"] = out["research_fair_price_v6_2_v2_1"].apply(num)

out["base_rank"] = out.groupby(["race_date", "track", "race_no"])["fair_price_num"].rank(method="min", ascending=True)
out["v6_2_v2_1_rank"] = out.groupby(["race_date", "track", "race_no"])["research_fair_price_v6_2_v2_1_num"].rank(method="min", ascending=True)

race_rows = []
for keys, g in out.groupby(["race_date", "track", "race_no"], dropna=False):
    priced = g[g["fair_price_num"].notna()].copy()
    if priced.empty:
        continue

    base_top = priced.sort_values("fair_price_num").iloc[0]
    v2_top = priced.sort_values("research_fair_price_v6_2_v2_1_num").iloc[0]

    race_rows.append({
        "race_date": keys[0],
        "track": keys[1],
        "race_no": keys[2],
        "base_top": base_top["horse"],
        "v6_2_v2_1_top": v2_top["horse"],
        "base_top_fair": base_top["fair_price"],
        "v6_2_v2_1_top_fair": v2_top["research_fair_price_v6_2_v2_1"],
        "top_changed": str(base_top["horse"]) != str(v2_top["horse"]),
    })

by_race = pd.DataFrame(race_rows)

priced = out[out["fair_price_num"].notna()].copy()
priced["fair_delta_pct"] = np.where(
    priced["fair_price_num"] > 0,
    ((priced["research_fair_price_v6_2_v2_1_num"] - priced["fair_price_num"]) / priced["fair_price_num"]) * 100,
    np.nan,
)

out.to_csv(OUT, index=False)
pd.DataFrame(factor_rows).to_csv(BY_FACTOR, index=False)
by_race.to_csv(BY_RACE, index=False)

summary = pd.DataFrame([
    ["status", "PROBABILITY_ENGINE_V6_2_FACTOR_OVERLAY_RESEARCH_V2_1_BUILT"],
    ["rows", len(out)],
    ["priced_rows", len(priced)],
    ["races", out.groupby(["race_date", "track", "race_no"]).ngroups],
    ["top_changed_races", int(by_race["top_changed"].sum()) if not by_race.empty else 0],
    ["positive_factor_total", int(out["positive_factor_total_v6_2_v2_1"].sum())],
    ["negative_factor_total", int(out["negative_factor_total_v6_2_v2_1"].sum())],
    ["avg_overlay_score", round(out["factor_overlay_score_v6_2_v2_1"].mean(), 3)],
    ["avg_adjustment_pct", round(out["factor_adjustment_pct_v6_2_v2_1"].mean(), 3)],
    ["avg_abs_fair_delta_pct", round(priced["fair_delta_pct"].abs().mean(), 3) if len(priced) else ""],
    ["max_abs_fair_delta_pct", round(priced["fair_delta_pct"].abs().max(), 3) if len(priced) else ""],
    ["pace_excluded", "YES"],
    ["calibrated_thresholds", "YES"],
    ["zero_missing_fit_neutralised", "DISTANCE|CONDITION|CLASS"],
    ["production_prices_changed", "NO"],
    ["production_probability_changed", "NO"],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[PROBABILITY_ENGINE_V6_2_FACTOR_OVERLAY_RESEARCH_V2_1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
print(f"wrote={BY_FACTOR}")
print(f"wrote={BY_RACE}")

