from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_pricing_replay_spine_v4_tab_quality.csv"

OUT = DATA / "edgeiq_probability_research_v7_tab_candidate_t6.csv"
SUMMARY = DATA / "edgeiq_probability_research_v7_tab_candidate_t6_summary.csv"
AUDIT = DATA / "edgeiq_probability_research_v7_tab_candidate_t6_audit.csv"

TEMP = 6.0

print("[V7_TAB_CANDIDATE_T6] START")

df = pd.read_csv(SRC, low_memory=False)

df["_rating"] = pd.to_numeric(df["rating"], errors="coerce")
df["_won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
df["_race_group"] = df["_race_group_v4"].astype(str)

frames = []

for race_key, g in df.groupby("_race_group", dropna=False):
    g = g.copy()
    r = pd.to_numeric(g["_rating"], errors="coerce")

    if r.notna().sum() < 2:
        g["v7_tab_probability_t6"] = 1 / len(g)
        g["v7_tab_probability_status"] = "EQUAL_PROB_INSUFFICIENT_RATING"
    else:
        sd = r.std()
        z = (r - r.mean()) / sd if pd.notna(sd) and sd != 0 else r - r.mean()
        exp_z = np.exp(z / TEMP)
        g["v7_tab_probability_t6"] = exp_z / exp_z.sum()
        g["v7_tab_probability_status"] = "V7_TAB_T6_RATING_SOFTMAX"

    frames.append(g)

out = pd.concat(frames, ignore_index=True)

out["v7_tab_fair_price_t6"] = np.where(
    out["v7_tab_probability_t6"] > 0,
    1 / out["v7_tab_probability_t6"],
    np.nan
)

out["v7_tab_probability_sum_t6"] = (
    out.groupby("_race_group")["v7_tab_probability_t6"].transform("sum")
)

out["v7_tab_probability_sum_ok_t6"] = (
    out["v7_tab_probability_sum_t6"].between(0.995, 1.005)
)

out["_rank"] = out.groupby("_race_group")["v7_tab_probability_t6"].rank(method="first", ascending=False)

eps = 1e-12
p = out["v7_tab_probability_t6"].clip(eps, 1 - eps)

out["v7_tab_log_loss_t6"] = -(
    out["_won"] * np.log(p) +
    (1 - out["_won"]) * np.log(1 - p)
)

out["v7_tab_brier_t6"] = (p - out["_won"]) ** 2

out["built_at"] = datetime.now(timezone.utc).isoformat()
out["production_changed"] = "NO"

out.to_csv(OUT, index=False)

race_audit = (
    out.groupby("_race_group")
    .agg(
        runners=("horse", "count"),
        field_size=("field_size", "first"),
        winners=("won", "sum"),
        prob_sum=("v7_tab_probability_sum_t6", "first"),
        fav_prob=("v7_tab_probability_t6", "max"),
        fav_fair=("v7_tab_fair_price_t6", "min"),
        top_pick_won=("_won", lambda s: int(s.loc[out.loc[s.index, "_rank"] == 1].sum()) if any(out.loc[s.index, "_rank"] == 1) else 0)
    )
    .reset_index()
)

race_audit.to_csv(AUDIT, index=False)

top_pick_wins = int(race_audit["top_pick_won"].sum())

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(out),
    "races": out["_race_group"].nunique(),
    "temperature": TEMP,
    "probability_rows": int(out["v7_tab_probability_t6"].notna().sum()),
    "probability_coverage_pct": round(float(out["v7_tab_probability_t6"].notna().mean() * 100), 2),
    "races_prob_sum_ok": int(race_audit["prob_sum"].between(0.995, 1.005).sum()),
    "races_prob_sum_bad": int((~race_audit["prob_sum"].between(0.995, 1.005)).sum()),
    "avg_log_loss": float(out["v7_tab_log_loss_t6"].mean()),
    "avg_brier": float(out["v7_tab_brier_t6"].mean()),
    "top_pick_wins": top_pick_wins,
    "top_pick_win_pct": round(float(top_pick_wins / out["_race_group"].nunique() * 100), 2),
    "avg_fav_prob": float(race_audit["fav_prob"].mean()),
    "avg_fav_fair": float(race_audit["fav_fair"].mean()),
    "status": "V7_TAB_CANDIDATE_T6_BUILT_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[V7_TAB_CANDIDATE_T6] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(summary.to_string(index=False))
