from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"

DETAIL = DATA / "edgeiq_runner_dna_weight_ladder_v1_detail.csv"
BY_RACE = DATA / "edgeiq_runner_dna_weight_ladder_v1_by_race.csv"
SUMMARY = DATA / "edgeiq_runner_dna_weight_ladder_v1_summary.csv"

CURRENT_COL = "runner_score"

WEIGHT_SETS = {
    "BASE": {
        "projected_rating_v5_2": 1.00,
        "sectional_strength_rating": 1.00,
        "strength_adjusted_rating_v6": 1.00,
        "confidence_adjusted_rating_v6": 1.00,
        "trainer_score": 0.25,
        "jockey_score": 0.25,
        "connection_score": 0.25,
    },
    "LIGHT": {
        "projected_rating_v5_2": 1.10,
        "sectional_strength_rating": 1.10,
        "strength_adjusted_rating_v6": 1.00,
        "confidence_adjusted_rating_v6": 1.00,
        "trainer_score": 0.25,
        "jockey_score": 0.35,
        "connection_score": 0.35,
    },
    "MEDIUM": {
        "projected_rating_v5_2": 1.15,
        "sectional_strength_rating": 1.15,
        "strength_adjusted_rating_v6": 1.05,
        "confidence_adjusted_rating_v6": 1.05,
        "trainer_score": 0.25,
        "jockey_score": 0.40,
        "connection_score": 0.40,
    },
    "AGGRESSIVE": {
        "projected_rating_v5_2": 1.25,
        "sectional_strength_rating": 1.15,
        "strength_adjusted_rating_v6": 1.10,
        "confidence_adjusted_rating_v6": 1.10,
        "trainer_score": 0.25,
        "jockey_score": 0.50,
        "connection_score": 0.50,
    },
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

def weighted_score(df, weights):
    total = pd.Series(0.0, index=df.index)
    weight_total = pd.Series(0.0, index=df.index)

    for col, w in weights.items():
        if col not in df.columns:
            continue
        vals = df[col].apply(num)
        valid = vals.notna()
        total.loc[valid] += vals.loc[valid] * w
        weight_total.loc[valid] += w

    return np.where(weight_total > 0, total / weight_total, np.nan)

df = pd.read_csv(SRC, dtype=str).fillna("")
built_at = datetime.now(timezone.utc).isoformat()

df["current_score_num"] = df[CURRENT_COL].apply(num)
df["won_num"] = df["won"].apply(num).fillna(0)
df["finish_num"] = df["finish_position"].apply(num)
df["placed_num"] = np.where(df["finish_num"].between(1, 3), 1, 0)

base_top_by_race = None
detail_frames = []
race_frames = []
summary_rows = []

for version, weights in WEIGHT_SETS.items():
    work = pd.DataFrame({
        "version": version,
        "meeting_date": df.get("meeting_date", ""),
        "track": df.get("track", ""),
        "race_no": df.get("race_no", ""),
        "race_key": df.get("race_key", ""),
        "horse": df.get("horse", ""),
        "horse_key": df.get("horse_key", ""),
        "score": pd.Series(weighted_score(df, weights)).round(3),
        "won": df["won_num"].astype(int),
        "placed": df["placed_num"].astype(int),
        "finish_position": df["finish_num"],
        "built_at": built_at,
    })

    work["band"] = work["score"].apply(band)
    work["rank"] = work.groupby("race_key")["score"].rank(method="min", ascending=False)

    if version == "BASE":
        base_top_by_race = (
            work.sort_values(["race_key", "rank"])
            .groupby("race_key")
            .first()
            .reset_index()[["race_key", "horse", "rank", "score", "band", "won", "placed"]]
            .rename(columns={
                "horse": "base_top",
                "score": "base_top_score",
                "band": "base_top_band",
                "won": "base_top_won",
                "placed": "base_top_placed",
            })
        )

    race_top = (
        work.sort_values(["race_key", "rank"])
        .groupby("race_key")
        .first()
        .reset_index()[["race_key", "meeting_date", "track", "race_no", "horse", "score", "band", "won", "placed"]]
        .rename(columns={
            "horse": "version_top",
            "score": "version_top_score",
            "band": "version_top_band",
            "won": "version_top_won",
            "placed": "version_top_placed",
        })
    )
    race_top["version"] = version

    race_frames.append(race_top)
    detail_frames.append(work)

detail = pd.concat(detail_frames, ignore_index=True)
race_out = pd.concat(race_frames, ignore_index=True)

race_out = race_out.merge(base_top_by_race, on="race_key", how="left")
race_out["top_changed_vs_base"] = race_out["version_top"] != race_out["base_top"]

detail_base = detail[detail["version"] == "BASE"][["race_key", "horse_key", "score", "band", "rank"]].rename(columns={
    "score": "base_score",
    "band": "base_band",
    "rank": "base_rank",
})
detail = detail.merge(detail_base, on=["race_key", "horse_key"], how="left")
detail["score_delta_vs_base"] = detail["score"] - detail["base_score"]
detail["rank_delta_vs_base"] = detail["rank"] - detail["base_rank"]
detail["band_changed_vs_base"] = detail["band"] != detail["base_band"]

for version, g in race_out.groupby("version"):
    d = detail[detail["version"] == version]
    races = len(g)

    summary_rows.append({
        "version": version,
        "rows": len(d),
        "races": races,
        "rank1_win_pct": round(g["version_top_won"].mean() * 100, 3),
        "rank1_place_pct": round(g["version_top_placed"].mean() * 100, 3),
        "top_changed_races": int(g["top_changed_vs_base"].sum()),
        "top_changed_pct": round(g["top_changed_vs_base"].mean() * 100, 3),
        "avg_abs_score_delta_vs_base": round(pd.to_numeric(d["score_delta_vs_base"], errors="coerce").abs().mean(), 3),
        "max_abs_score_delta_vs_base": round(pd.to_numeric(d["score_delta_vs_base"], errors="coerce").abs().max(), 3),
        "avg_abs_rank_delta_vs_base": round(pd.to_numeric(d["rank_delta_vs_base"], errors="coerce").abs().mean(), 3),
        "max_abs_rank_delta_vs_base": round(pd.to_numeric(d["rank_delta_vs_base"], errors="coerce").abs().max(), 3),
        "band_changed_rows_vs_base": int(d["band_changed_vs_base"].sum()),
        "research_only": "YES",
        "built_at": built_at,
    })

summary = pd.DataFrame(summary_rows)

detail.to_csv(DETAIL, index=False)
race_out.to_csv(BY_RACE, index=False)
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_WEIGHT_LADDER_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={DETAIL}")
print(f"wrote={BY_RACE}")
print(f"wrote={SUMMARY}")
