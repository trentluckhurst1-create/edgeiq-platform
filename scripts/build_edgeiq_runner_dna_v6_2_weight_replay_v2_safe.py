from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"

OUT = DATA / "edgeiq_runner_dna_v6_2_weight_replay_v2_safe.csv"
BY_RACE = DATA / "edgeiq_runner_dna_v6_2_weight_replay_v2_safe_by_race.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_2_weight_replay_v2_safe_summary.csv"

CURRENT_WEIGHTS = {
    "FORM": 1.00,
    "RATING": 0.50,
    "PACE": 0.00,
    "DISTANCE": 1.25,
    "CONDITION": 1.25,
    "CLASS": 1.25,
    "SECTIONALS": 1.00,
    "PROFILE": 0.50,
    "TRAINER": 0.25,
    "JOCKEY": 0.25,
    "COMBO": 0.25,
}

REPLAY_WEIGHTS = {
    "FORM": 1.00,
    "RATING": 0.65,
    "PACE": 0.00,
    "DISTANCE": 1.25,
    "CONDITION": 1.25,
    "CLASS": 1.25,
    "SECTIONALS": 1.15,
    "PROFILE": 0.50,
    "TRAINER": 0.25,
    "JOCKEY": 0.35,
    "COMBO": 0.30,
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

def weighted_score(g, weights):
    total_w = 0.0
    total = 0.0

    for _, r in g.iterrows():
        factor = str(r.get("factor", "")).upper()
        score = num(r.get("factor_score", ""))
        w = weights.get(factor, 0.0)

        if pd.isna(score) or w <= 0:
            continue

        total += score * w
        total_w += w

    if total_w <= 0:
        return np.nan

    return total / total_w

df = pd.read_csv(SRC, dtype=str).fillna("")
built_at = datetime.now(timezone.utc).isoformat()

rows = []

for join_key, g in df.groupby("join_key"):
    first = g.iloc[0]

    current = weighted_score(g, CURRENT_WEIGHTS)
    replay = weighted_score(g, REPLAY_WEIGHTS)

    rows.append({
        "race_date": first.get("race_date", ""),
        "track": first.get("track", ""),
        "race_no": first.get("race_no", ""),
        "horse": first.get("horse", ""),
        "join_key": join_key,
        "current_replay_score": "" if pd.isna(current) else round(current, 3),
        "current_replay_band": band(current),
        "v6_2_weight_replay_score": "" if pd.isna(replay) else round(replay, 3),
        "v6_2_weight_replay_band": band(replay),
        "score_delta": "" if pd.isna(current) or pd.isna(replay) else round(replay - current, 3),
        "built_at": built_at,
    })

out = pd.DataFrame(rows)

out["current_rank"] = out.groupby(["race_date", "track", "race_no"])["current_replay_score"].rank(method="min", ascending=False)
out["replay_rank"] = out.groupby(["race_date", "track", "race_no"])["v6_2_weight_replay_score"].rank(method="min", ascending=False)
out["rank_delta"] = out["replay_rank"] - out["current_rank"]
out["band_changed"] = np.where(out["current_replay_band"] != out["v6_2_weight_replay_band"], "YES", "NO")

out.to_csv(OUT, index=False)

race_rows = []
for keys, g in out.groupby(["race_date", "track", "race_no"]):
    base_top = g.sort_values("current_rank").iloc[0]
    replay_top = g.sort_values("replay_rank").iloc[0]

    race_rows.append({
        "race_date": keys[0],
        "track": keys[1],
        "race_no": keys[2],
        "current_top": base_top["horse"],
        "replay_top": replay_top["horse"],
        "current_top_score": base_top["current_replay_score"],
        "replay_top_score": replay_top["v6_2_weight_replay_score"],
        "top_changed": str(base_top["horse"]) != str(replay_top["horse"]),
    })

by_race = pd.DataFrame(race_rows)
by_race.to_csv(BY_RACE, index=False)

summary = pd.DataFrame([
    ["status", "RUNNER_DNA_V6_2_WEIGHT_REPLAY_V2_SAFE_BUILT"],
    ["source", SRC.name],
    ["rows", len(out)],
    ["races", len(by_race)],
    ["top_changed_races", int((by_race["top_changed"] == True).sum())],
    ["avg_score_delta", round(pd.to_numeric(out["score_delta"], errors="coerce").mean(), 3)],
    ["avg_abs_score_delta", round(pd.to_numeric(out["score_delta"], errors="coerce").abs().mean(), 3)],
    ["max_abs_score_delta", round(pd.to_numeric(out["score_delta"], errors="coerce").abs().max(), 3)],
    ["avg_abs_rank_delta", round(pd.to_numeric(out["rank_delta"], errors="coerce").abs().mean(), 3)],
    ["max_abs_rank_delta", round(pd.to_numeric(out["rank_delta"], errors="coerce").abs().max(), 3)],
    ["band_changed_rows", int((out["band_changed"] == "YES").sum())],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_V6_2_WEIGHT_REPLAY_V2_SAFE] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={BY_RACE}")
print(f"wrote={SUMMARY}")

