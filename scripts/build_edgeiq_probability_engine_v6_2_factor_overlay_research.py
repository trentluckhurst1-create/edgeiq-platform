from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA_FILE = DATA / "edgeiq_live_runner_dna_v6_2.csv"
SCORECARD_FILE = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"

OUT = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research.csv"
SUMMARY = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_summary.csv"
BY_FACTOR = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_by_factor.csv"
BY_RACE = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_by_race.csv"

FACTOR_WEIGHTS = {
    "FORM": 1.0,
    "RATING": 1.0,
    "PACE": 0.75,
    "DISTANCE": 1.25,
    "CONDITION": 1.25,
    "CLASS": 1.25,
    "SECTIONALS": 1.0,
    "PROFILE": 1.0,
    "TRAINER": 0.5,
    "JOCKEY": 0.5,
    "COMBO": 0.5,
}

def num(x):
    try:
        s = str(x).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def s(row, key):
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

required = ["race_date", "track", "race_no", "horse", "join_key", "fair_price"]
missing = [c for c in required if c not in dna.columns]
if missing:
    raise RuntimeError(f"DNA missing required columns: {missing}. Available={list(dna.columns)[:40]}")

required_sc = ["join_key", "factor", "factor_score"]
missing_sc = [c for c in required_sc if c not in scorecard.columns]
if missing_sc:
    raise RuntimeError(f"Scorecard missing required columns: {missing_sc}. Available={list(scorecard.columns)[:40]}")

built_at = datetime.now(timezone.utc).isoformat()

factor_lookup = {}
for _, r in scorecard.iterrows():
    jk = s(r, "join_key")
    f = s(r, "factor").upper()
    factor_lookup.setdefault(jk, {})[f] = num(r.get("factor_score", ""))

out_rows = []
factor_rows = []

for _, r in dna.iterrows():
    jk = s(r, "join_key")
    factors = factor_lookup.get(jk, {})

    overlay = 0.0
    pos = 0
    neg = 0

    for factor, weight in FACTOR_WEIGHTS.items():
        score = factors.get(factor, np.nan)
        polarity = "NEUTRAL"
        signal = 0.0

        if not pd.isna(score):
            if score >= 65:
                polarity = "POSITIVE"
                pos += 1
                signal = weight
            elif score < 35:
                polarity = "NEGATIVE"
                neg += 1
                signal = -weight

        overlay += signal

        factor_rows.append({
            "race_date": s(r, "race_date"),
            "track": s(r, "track"),
            "race_no": s(r, "race_no"),
            "horse": s(r, "horse"),
            "join_key": jk,
            "factor": factor,
            "factor_score": "" if pd.isna(score) else round(score, 3),
            "factor_weight": weight,
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
    row["factor_overlay_score_v6_2"] = round(overlay, 3)
    row["factor_adjustment_pct_v6_2"] = adjustment
    row["positive_factor_total_v6_2"] = pos
    row["negative_factor_total_v6_2"] = neg
    row["base_probability"] = "" if pd.isna(base_prob) else round(base_prob, 8)
    row["research_probability_v6_2"] = "" if pd.isna(research_prob) else round(research_prob, 8)
    row["research_fair_price_v6_2"] = "" if pd.isna(research_fair) else round(research_fair, 4)
    row["research_only"] = "YES"
    row["production_prices_changed"] = "NO"
    row["production_probability_changed"] = "NO"
    row["built_at_v6_2_factor_overlay"] = built_at
    out_rows.append(row)

out = pd.DataFrame(out_rows)

out["fair_price_num"] = out["fair_price"].apply(num)
out["research_fair_price_v6_2_num"] = out["research_fair_price_v6_2"].apply(num)

out["base_rank"] = out.groupby(["race_date", "track", "race_no"])["fair_price_num"].rank(method="min", ascending=True)
out["v6_2_rank"] = out.groupby(["race_date", "track", "race_no"])["research_fair_price_v6_2_num"].rank(method="min", ascending=True)

race_rows = []
for keys, g in out.groupby(["race_date", "track", "race_no"], dropna=False):
    priced = g[g["fair_price_num"].notna()].copy()
    if priced.empty:
        continue
    base_top = priced.sort_values("fair_price_num").iloc[0]
    v62_top = priced.sort_values("research_fair_price_v6_2_num").iloc[0]

    race_rows.append({
        "race_date": keys[0],
        "track": keys[1],
        "race_no": keys[2],
        "base_top": base_top["horse"],
        "v6_2_top": v62_top["horse"],
        "base_top_fair": base_top["fair_price"],
        "v6_2_top_fair": v62_top["research_fair_price_v6_2"],
        "top_changed": str(base_top["horse"]) != str(v62_top["horse"]),
    })

by_race = pd.DataFrame(race_rows)

out.to_csv(OUT, index=False)
pd.DataFrame(factor_rows).to_csv(BY_FACTOR, index=False)
by_race.to_csv(BY_RACE, index=False)

priced = out[out["fair_price_num"].notna()].copy()
priced["fair_delta_pct"] = np.where(
    priced["fair_price_num"] > 0,
    ((priced["research_fair_price_v6_2_num"] - priced["fair_price_num"]) / priced["fair_price_num"]) * 100,
    np.nan,
)

summary = pd.DataFrame([
    ["status", "PROBABILITY_ENGINE_V6_2_FACTOR_OVERLAY_RESEARCH_BUILT"],
    ["rows", len(out)],
    ["priced_rows", len(priced)],
    ["races", out.groupby(["race_date", "track", "race_no"]).ngroups],
    ["top_changed_races", int(by_race["top_changed"].sum()) if not by_race.empty else 0],
    ["positive_factor_total", int(out["positive_factor_total_v6_2"].sum())],
    ["negative_factor_total", int(out["negative_factor_total_v6_2"].sum())],
    ["avg_overlay_score", round(out["factor_overlay_score_v6_2"].mean(), 3)],
    ["avg_adjustment_pct", round(out["factor_adjustment_pct_v6_2"].mean(), 3)],
    ["avg_abs_fair_delta_pct", round(priced["fair_delta_pct"].abs().mean(), 3) if len(priced) else ""],
    ["max_abs_fair_delta_pct", round(priced["fair_delta_pct"].abs().max(), 3) if len(priced) else ""],
    ["production_prices_changed", "NO"],
    ["production_probability_changed", "NO"],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[PROBABILITY_ENGINE_V6_2_FACTOR_OVERLAY_RESEARCH] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
print(f"wrote={BY_FACTOR}")
print(f"wrote={BY_RACE}")
