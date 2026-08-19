import pandas as pd
from pathlib import Path

DATA = Path("./public/data")

REPLAY = DATA / "edgeiq_runner_dna_v6_3_historical_replay_v1.csv"
FLIPS = DATA / "edgeiq_runner_dna_v6_3_safe_factor_flip_analysis_v1.csv"
SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT_DETAIL = DATA / "edgeiq_connection_flip_races_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_connection_flip_races_v1_summary.csv"

replay = pd.read_csv(REPLAY)
flips = pd.read_csv(FLIPS)
settled = pd.read_csv(SETTLED)

for df in [replay, flips, settled]:
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = df[c].fillna("").astype(str)

available_join = [c for c in ["race_key", "horse_key"] if c in replay.columns and c in settled.columns]

extra_cols = [
    c for c in [
        "race_key","horse_key","horse","trainer","jockey",
        "connection_score","combo_score","combo_factor_score_v1",
        "trainer_jockey_blend_score_v3","trainer_jockey_blend_band_v3",
        "trainer_score","jockey_score","won","placed"
    ]
    if c in settled.columns
]

if available_join:
    replay = replay.merge(
        settled[extra_cols].drop_duplicates(subset=available_join),
        on=available_join,
        how="left",
        suffixes=("", "_settled")
    )

for c in ["trainer","jockey"]:
    if c not in replay.columns:
        replay[c] = "UNKNOWN"
    replay[c] = replay[c].replace("", "UNKNOWN").fillna("UNKNOWN")

connection_flips = flips[flips["largest_factor_shift"].str.upper() == "CONNECTION"].copy()
connection_flip_keys = set(connection_flips["race_key"])

detail = replay[replay["race_key"].isin(connection_flip_keys)].copy()

detail["is_base_top"] = detail.groupby("race_key")["current_rank"].transform(lambda s: s == 1)
detail["is_new_top"] = detail.groupby("race_key")["v6_3_rank"].transform(lambda s: s == 1)
detail["is_flip_runner"] = detail["is_base_top"] | detail["is_new_top"]
detail["connection_pair"] = detail["trainer"].astype(str) + " / " + detail["jockey"].astype(str)

summary = detail[detail["is_flip_runner"]].groupby("connection_pair", dropna=False).agg(
    flip_runner_rows=("horse","count"),
    unique_flip_races=("race_key","nunique"),
    wins=("won", lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()),
    places=("placed", lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()),
    avg_score_delta=("score_delta", lambda s: pd.to_numeric(s, errors="coerce").mean()),
    avg_rank_delta=("rank_delta", lambda s: pd.to_numeric(s, errors="coerce").mean()),
).reset_index()

summary["win_rate"] = (summary["wins"] / summary["flip_runner_rows"] * 100).round(2)
summary["place_rate"] = (summary["places"] / summary["flip_runner_rows"] * 100).round(2)
summary = summary.sort_values(["unique_flip_races","wins","place_rate"], ascending=[False,False,False])

detail.to_csv(OUT_DETAIL, index=False)
summary.to_csv(OUT_SUMMARY, index=False)

print("[CONNECTION_FLIP_RACES_V1] COMPLETE")
print(f"connection_factor_flip_races={len(connection_flip_keys)}")
print(f"detail_rows={len(detail)}")
print(f"summary_rows={len(summary)}")
print(summary.head(25).to_string(index=False))
