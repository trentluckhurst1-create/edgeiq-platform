from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"
BY_RACE = DATA / "edgeiq_runner_dna_weight_ladder_v1_by_race.csv"

OUT = DATA / "edgeiq_runner_dna_v6_3_safe_factor_flip_analysis_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_3_safe_factor_flip_analysis_v1_summary.csv"

VERSION = "MEDIUM"

FACTOR_COLS = {
    "PROJECTED_RATING": "projected_rating_v5_2",
    "SECTIONALS": "sectional_strength_rating",
    "STRENGTH_ADJUSTED": "strength_adjusted_rating_v6",
    "CONFIDENCE_ADJUSTED": "confidence_adjusted_rating_v6",
    "TRAINER": "trainer_score",
    "JOCKEY": "jockey_score",
    "CONNECTION": "connection_score",
}

MEDIUM_WEIGHTS = {
    "PROJECTED_RATING": 1.15,
    "SECTIONALS": 1.15,
    "STRENGTH_ADJUSTED": 1.05,
    "CONFIDENCE_ADJUSTED": 1.05,
    "TRAINER": 0.25,
    "JOCKEY": 0.40,
    "CONNECTION": 0.40,
}

def num(x):
    try:
        s = str(x).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

df = pd.read_csv(SRC, dtype=str).fillna("")
races = pd.read_csv(BY_RACE, dtype=str).fillna("")

built_at = datetime.now(timezone.utc).isoformat()

improved = races[
    (races["version"] == VERSION) &
    (races["top_changed_vs_base"] == "True") &
    (races["base_top_won"] == "0") &
    (races["version_top_won"] == "1")
].copy()

rows = []

for _, r in improved.iterrows():
    race_key = r["race_key"]
    base_top = r["base_top"]
    new_top = r["version_top"]

    race_df = df[df["race_key"] == race_key].copy()

    b = race_df[race_df["horse"] == base_top]
    n = race_df[race_df["horse"] == new_top]

    if b.empty or n.empty:
        continue

    b = b.iloc[0]
    n = n.iloc[0]

    factor_deltas = {}

    for factor, col in FACTOR_COLS.items():
        b_score = num(b.get(col, ""))
        n_score = num(n.get(col, ""))

        if pd.isna(b_score):
            b_score = 0.0
        if pd.isna(n_score):
            n_score = 0.0

        score_delta = n_score - b_score
        contribution_delta = score_delta * MEDIUM_WEIGHTS.get(factor, 0.0)

        factor_deltas[factor] = contribution_delta

    positive_deltas = {k: v for k, v in factor_deltas.items() if v > 0}

    if positive_deltas:
        main_factor = max(positive_deltas, key=positive_deltas.get)
        main_delta = positive_deltas[main_factor]
    else:
        main_factor = max(factor_deltas, key=factor_deltas.get)
        main_delta = factor_deltas[main_factor]

    row = {
        "race_key": race_key,
        "meeting_date": r.get("meeting_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "base_top": base_top,
        "new_top": new_top,
        "largest_factor_shift": main_factor,
        "largest_factor_delta": round(main_delta, 4),
        "improvement_type": "BASE_LOST_NEW_WON",
        "built_at": built_at,
    }

    for factor, delta in factor_deltas.items():
        row[f"{factor.lower()}_delta"] = round(delta, 4)

    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

if len(out):
    factor_summary = (
        out.groupby("largest_factor_shift")
        .size()
        .reset_index(name="times_responsible")
        .sort_values("times_responsible", ascending=False)
    )
    factor_summary["pct_of_improvements"] = (factor_summary["times_responsible"] / len(out) * 100).round(2)
else:
    factor_summary = pd.DataFrame(columns=["largest_factor_shift", "times_responsible", "pct_of_improvements"])

header = pd.DataFrame([
    ["status", "RUNNER_DNA_V6_3_SAFE_FACTOR_FLIP_ANALYSIS_V1_BUILT"],
    ["version", VERSION],
    ["improvement_rows", len(out)],
    ["source", SRC.name],
    ["source_by_race", BY_RACE.name],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric", "value"])

summary_path_rows = []
for _, row in factor_summary.iterrows():
    summary_path_rows.append([
        f"factor_{row['largest_factor_shift']}",
        f"{int(row['times_responsible'])} ({row['pct_of_improvements']}%)"
    ])

summary = pd.concat([header, pd.DataFrame(summary_path_rows, columns=["metric", "value"])], ignore_index=True)
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_V6_3_SAFE_FACTOR_FLIP_ANALYSIS_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
