from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_pricing_replay_spine_v3_1_reconstructed.csv"

OUT = DATA / "edgeiq_probability_research_v7_candidate_t575.csv"
SUMMARY = DATA / "edgeiq_probability_research_v7_candidate_t575_summary.csv"
AUDIT = DATA / "edgeiq_probability_research_v7_candidate_t575_audit.csv"

TEMP = 5.75

print("[PROBABILITY_RESEARCH_V7_CANDIDATE_T575] START")

df = pd.read_csv(SRC, low_memory=False)

df["_race_group_v3_3"] = (
    pd.to_datetime(df["race_date"], errors="coerce").dt.date.astype("string").fillna("") + "|" +
    df["track"].astype(str).str.upper().str.strip() + "|" +
    pd.to_numeric(df["race_no"], errors="coerce").astype("Int64").astype("string").fillna("")
)

df["_rating"] = pd.to_numeric(df["reconstructed_rating_v3_1"], errors="coerce")

frames = []

for race_key, g in df.groupby("_race_group_v3_3", dropna=False):
    g = g.copy()
    r = pd.to_numeric(g["_rating"], errors="coerce")

    if r.notna().sum() < 2:
        g["replay_probability_temperature6_v3_3"] = 1 / len(g)
        g["temperature6_status_v3_3"] = "EQUAL_PROB_INSUFFICIENT_RATING"
    else:
        sd = r.std()

        if pd.isna(sd) or sd == 0:
            z = r - r.mean()
        else:
            z = (r - r.mean()) / sd

        exp_z = np.exp(z / TEMP)
        g["replay_probability_temperature6_v3_3"] = exp_z / exp_z.sum()
        g["temperature6_status_v3_3"] = "RECONSTRUCTED_TEMPERATURE_6"

    frames.append(g)

out = pd.concat(frames, ignore_index=True)

out["replay_fair_price_temperature6_v3_3"] = np.where(
    out["replay_probability_temperature6_v3_3"] > 0,
    1 / out["replay_probability_temperature6_v3_3"],
    np.nan
)

out["probability_sum_temperature6_v3_3"] = (
    out.groupby("_race_group_v3_3")["replay_probability_temperature6_v3_3"]
    .transform("sum")
)

out["probability_sum_ok_temperature6_v3_3"] = (
    out["probability_sum_temperature6_v3_3"].between(0.995, 1.005)
)

out["built_at_v3_3"] = datetime.now(timezone.utc).isoformat()

out.to_csv(OUT, index=False)

race_audit = (
    out.groupby("_race_group_v3_3")
    .agg(
        runners=("horse", "count"),
        winners=("won", "sum"),
        prob_sum=("probability_sum_temperature6_v3_3", "first"),
        fav_prob=("replay_probability_temperature6_v3_3", "max"),
        fav_fair=("replay_fair_price_temperature6_v3_3", "min"),
        status=("temperature6_status_v3_3", "first")
    )
    .reset_index()
)

race_audit.to_csv(AUDIT, index=False)

out["_won"] = pd.to_numeric(out["won"], errors="coerce").fillna(0)
out["_p"] = pd.to_numeric(out["replay_probability_temperature6_v3_3"], errors="coerce")
out["_fair"] = pd.to_numeric(out["replay_fair_price_temperature6_v3_3"], errors="coerce")
out["_rank"] = out.groupby("_race_group_v3_3")["_p"].rank(method="first", ascending=False)

eps = 1e-12
out["_log_loss"] = -(
    out["_won"] * np.log(out["_p"].clip(eps, 1 - eps)) +
    (1 - out["_won"]) * np.log((1 - out["_p"]).clip(eps, 1 - eps))
)
out["_brier"] = (out["_p"] - out["_won"]) ** 2

top_pick_wins = int(out.loc[out["_rank"] == 1, "_won"].sum())

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(out),
    "races": out["_race_group_v3_3"].nunique(),
    "temperature": TEMP,
    "probability_rows": int(out["_p"].notna().sum()),
    "probability_coverage_pct": round(float(out["_p"].notna().mean() * 100), 2),
    "races_prob_sum_ok": int(race_audit["prob_sum"].between(0.995, 1.005).sum()),
    "races_prob_sum_bad": int((~race_audit["prob_sum"].between(0.995, 1.005)).sum()),
    "avg_log_loss": float(out["_log_loss"].mean()),
    "avg_brier": float(out["_brier"].mean()),
    "top_pick_wins": top_pick_wins,
    "top_pick_win_pct": round(float(top_pick_wins / out["_race_group_v3_3"].nunique() * 100), 2),
    "avg_fav_prob": float(race_audit["fav_prob"].mean()),
    "avg_fav_fair": float(race_audit["fav_fair"].mean()),
    "status": "PROBABILITY_RESEARCH_V7_CANDIDATE_T575_BUILT_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[PROBABILITY_RESEARCH_V7_CANDIDATE_T575] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(summary.to_string(index=False))
