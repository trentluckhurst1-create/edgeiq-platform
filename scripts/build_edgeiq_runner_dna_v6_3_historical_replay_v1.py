from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT = DATA / "edgeiq_runner_dna_v6_3_historical_replay_v1.csv"
BY_RACE = DATA / "edgeiq_runner_dna_v6_3_historical_replay_v1_by_race.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_3_historical_replay_v1_summary.csv"

CURRENT_COL = "runner_score"

V6_3_WEIGHTS = {
    "projected_rating_v5_2": 1.25,
    "sectional_strength_rating": 1.15,
    "strength_adjusted_rating_v6": 1.10,
    "confidence_adjusted_rating_v6": 1.10,
    "trainer_score": 0.25,
    "jockey_score": 0.35,
    "connection_score": 0.30,
}

def num(x):
    try:
        s = str(x).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def band(score):
    if pd.isna(score):
        return "NO_SCORE"
    if score >= 85:
        return "ELITE"
    if score >= 72:
        return "STRONG"
    if score >= 55:
        return "POSITIVE"
    if score >= 40:
        return "NEUTRAL"
    if score >= 25:
        return "NEGATIVE"
    return "POOR"

df = pd.read_csv(SRC, dtype=str).fillna("")
built_at = datetime.now(timezone.utc).isoformat()

for c in [CURRENT_COL, "won", "finish_position"]:
    if c not in df.columns:
        raise RuntimeError(f"Missing required column: {c}")

df["current_score_num"] = df[CURRENT_COL].apply(num)
df["won_num"] = df["won"].apply(num).fillna(0)
df["finish_num"] = df["finish_position"].apply(num)
df["placed_num"] = np.where(df["finish_num"].between(1, 3), 1, 0)

score_total = pd.Series(0.0, index=df.index)
weight_total = pd.Series(0.0, index=df.index)

for col, w in V6_3_WEIGHTS.items():
    if col not in df.columns:
        continue
    vals = df[col].apply(num)
    valid = vals.notna()
    score_total.loc[valid] += vals.loc[valid] * w
    weight_total.loc[valid] += w

df["v6_3_research_score"] = np.where(weight_total > 0, score_total / weight_total, np.nan)

out = pd.DataFrame({
    "meeting_date": df.get("meeting_date", ""),
    "track": df.get("track", ""),
    "race_no": df.get("race_no", ""),
    "race_key": df.get("race_key", ""),
    "horse": df.get("horse", ""),
    "horse_key": df.get("horse_key", ""),
    "current_score": df["current_score_num"].round(3),
    "current_band": df["current_score_num"].apply(band),
    "v6_3_research_score": pd.to_numeric(df["v6_3_research_score"], errors="coerce").round(3),
    "v6_3_research_band": df["v6_3_research_score"].apply(band),
    "score_delta": (df["v6_3_research_score"] - df["current_score_num"]).round(3),
    "won": df["won_num"].astype(int),
    "placed": df["placed_num"].astype(int),
    "finish_position": df["finish_num"],
    "built_at": built_at,
})

out["current_rank"] = out.groupby("race_key")["current_score"].rank(method="min", ascending=False)
out["v6_3_rank"] = out.groupby("race_key")["v6_3_research_score"].rank(method="min", ascending=False)
out["rank_delta"] = out["v6_3_rank"] - out["current_rank"]
out["band_changed"] = np.where(out["current_band"] != out["v6_3_research_band"], "YES", "NO")

out.to_csv(OUT, index=False)

race_rows = []
for race_key, g in out.groupby("race_key"):
    g = g.copy()
    current_top = g.sort_values("current_rank").iloc[0]
    v63_top = g.sort_values("v6_3_rank").iloc[0]

    race_rows.append({
        "race_key": race_key,
        "meeting_date": current_top["meeting_date"],
        "track": current_top["track"],
        "race_no": current_top["race_no"],
        "current_top": current_top["horse"],
        "v6_3_top": v63_top["horse"],
        "current_top_won": int(current_top["won"]),
        "v6_3_top_won": int(v63_top["won"]),
        "current_top_placed": int(current_top["placed"]),
        "v6_3_top_placed": int(v63_top["placed"]),
        "top_changed": str(current_top["horse"]) != str(v63_top["horse"]),
    })

by_race = pd.DataFrame(race_rows)
by_race.to_csv(BY_RACE, index=False)

races = len(by_race)
same_rank1 = int((by_race["top_changed"] == False).sum())
top_changed = int((by_race["top_changed"] == True).sum())

summary = pd.DataFrame([
    ["status", "RUNNER_DNA_V6_3_HISTORICAL_REPLAY_V1_BUILT"],
    ["source", SRC.name],
    ["rows", len(out)],
    ["races", races],
    ["same_rank1", same_rank1],
    ["top_changed_races", top_changed],
    ["top_changed_pct", round(top_changed / races * 100, 3) if races else ""],
    ["current_rank1_win_pct", round(by_race["current_top_won"].mean() * 100, 3)],
    ["v6_3_rank1_win_pct", round(by_race["v6_3_top_won"].mean() * 100, 3)],
    ["current_rank1_place_pct", round(by_race["current_top_placed"].mean() * 100, 3)],
    ["v6_3_rank1_place_pct", round(by_race["v6_3_top_placed"].mean() * 100, 3)],
    ["avg_abs_score_delta", round(pd.to_numeric(out["score_delta"], errors="coerce").abs().mean(), 3)],
    ["max_abs_score_delta", round(pd.to_numeric(out["score_delta"], errors="coerce").abs().max(), 3)],
    ["avg_abs_rank_delta", round(pd.to_numeric(out["rank_delta"], errors="coerce").abs().mean(), 3)],
    ["max_abs_rank_delta", round(pd.to_numeric(out["rank_delta"], errors="coerce").abs().max(), 3)],
    ["band_changed_rows", int((out["band_changed"] == "YES").sum())],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_V6_3_HISTORICAL_REPLAY_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={BY_RACE}")
print(f"wrote={SUMMARY}")
