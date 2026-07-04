import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST = DATA / "edgeiq_trainer_jockey_runner_history_v1.csv"
OUT = DATA / "edgeiq_trainer_jockey_prep_engine_v1.csv"
SUMMARY = DATA / "edgeiq_trainer_jockey_prep_engine_v1_summary.csv"

SPELL_DAYS = 56

def clean_key(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper().replace(" ", "").replace(".", "").replace("'", "")

def evidence_band(starts):
    if starts >= 20:
        return "STRONG"
    if starts >= 10:
        return "MODERATE"
    if starts >= 5:
        return "DEVELOPING"
    return "LOW_SAMPLE"

def signal_row(row):
    starts = row["starts"]
    win_lift = row["win_lift_pct"]
    place_lift = row["place_lift_pct"]

    if starts < 5:
        return "LOW_SAMPLE"
    if win_lift >= 50 and place_lift >= 30:
        return "COMBO_PREP_EDGE"
    if win_lift >= 20 or place_lift >= 20:
        return "MILD_COMBO_PREP_EDGE"
    if win_lift <= -30 and place_lift <= -20:
        return "COMBO_PREP_RISK"
    return "NEUTRAL"

def make_insight(row):
    combo = f"{row['trainer']} + {row['jockey']}"
    stage = str(row["prep_stage"]).replace("_", " ").title()
    sig = row["signal"]
    starts = int(row["starts"])
    win_pct = round(float(row["win_pct"]), 1)
    place_pct = round(float(row["place_pct"]), 1)
    win_lift = round(float(row["win_lift_pct"]), 1)
    place_lift = round(float(row["place_lift_pct"]), 1)

    if sig == "COMBO_PREP_EDGE":
        return f"{combo} has a strong {stage} intent profile: {win_pct}% wins / {place_pct}% places from {starts} starts, lifting win rate {win_lift} pts and place rate {place_lift} pts above the partnership baseline."
    if sig == "MILD_COMBO_PREP_EDGE":
        return f"{combo} shows a positive {stage} profile: {win_pct}% wins / {place_pct}% places from {starts} starts, ahead of the partnership baseline."
    if sig == "COMBO_PREP_RISK":
        return f"{combo} has underperformed when presenting runners {stage}: {win_pct}% wins / {place_pct}% places from {starts} starts, below the partnership baseline."
    if sig == "LOW_SAMPLE":
        return f"{combo} has limited evidence {stage}: only {starts} starts, so treat the signal cautiously."
    return f"{combo} is neutral {stage}: {win_pct}% wins / {place_pct}% places from {starts} starts, broadly in line with its normal profile."

print("[TRAINER_JOCKEY_PREP_ENGINE_V1] loading history...")
df = pd.read_csv(HIST, low_memory=False)

df["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce")
df["trainer_key"] = df["trainer_key"].fillna("").map(clean_key)
df["jockey_key"] = df["jockey_key"].fillna("").map(clean_key)
df["horse_key"] = df["horse_key"].fillna("").map(clean_key)
df["trainer"] = df["trainer"].fillna("").astype(str).str.strip()
df["jockey"] = df["jockey"].fillna("").astype(str).str.strip()

df = df[
    (df["meeting_date"].notna()) &
    (df["trainer_key"] != "") &
    (df["jockey_key"] != "") &
    (df["horse_key"] != "")
].copy()

df["won_v1"] = pd.to_numeric(df["won_v1"], errors="coerce").fillna(0).astype(int)
df["placed_v1"] = pd.to_numeric(df["placed_v1"], errors="coerce").fillna(0).astype(int)
df["sp_num"] = pd.to_numeric(df["sp"], errors="coerce")

print("[TRAINER_JOCKEY_PREP_ENGINE_V1] deriving prep stage...")
df = df.sort_values(["horse_key", "meeting_date", "track", "race_no"]).copy()
df["prev_run_date"] = df.groupby("horse_key")["meeting_date"].shift(1)
df["days_since_prev"] = (df["meeting_date"] - df["prev_run_date"]).dt.days
df["new_prep"] = df["days_since_prev"].isna() | (df["days_since_prev"] >= SPELL_DAYS)
df["prep_id"] = df.groupby("horse_key")["new_prep"].cumsum()
df["prep_run_no"] = df.groupby(["horse_key", "prep_id"]).cumcount() + 1

df["prep_stage"] = "DEEP_PREP"
df.loc[df["prep_run_no"] == 1, "prep_stage"] = "FIRST_UP"
df.loc[df["prep_run_no"] == 2, "prep_stage"] = "SECOND_UP"
df.loc[df["prep_run_no"] == 3, "prep_stage"] = "THIRD_UP"
df.loc[df["prep_run_no"] == 4, "prep_stage"] = "FOURTH_UP"

df["trainer_jockey_key_v1"] = df["trainer_key"] + "|" + df["jockey_key"]

base = (
    df.groupby(["trainer_jockey_key_v1", "trainer_key", "trainer", "jockey_key", "jockey"], dropna=False)
    .agg(
        combo_base_starts=("race_no", "count"),
        combo_base_wins=("won_v1", "sum"),
        combo_base_places=("placed_v1", "sum"),
    )
    .reset_index()
)

base["combo_base_win_pct"] = (base["combo_base_wins"] / base["combo_base_starts"] * 100).round(4)
base["combo_base_place_pct"] = (base["combo_base_places"] / base["combo_base_starts"] * 100).round(4)

agg = (
    df.groupby(
        ["trainer_jockey_key_v1", "trainer_key", "trainer", "jockey_key", "jockey", "prep_stage"],
        dropna=False
    )
    .agg(
        starts=("race_no", "count"),
        wins=("won_v1", "sum"),
        places=("placed_v1", "sum"),
        avg_sp=("sp_num", "mean"),
        first_meeting_date=("meeting_date", "min"),
        last_meeting_date=("meeting_date", "max"),
    )
    .reset_index()
)

agg["win_pct"] = (agg["wins"] / agg["starts"] * 100).round(4)
agg["place_pct"] = (agg["places"] / agg["starts"] * 100).round(4)
agg["avg_sp"] = agg["avg_sp"].round(4)

out = agg.merge(
    base[[
        "trainer_jockey_key_v1",
        "combo_base_starts",
        "combo_base_win_pct",
        "combo_base_place_pct",
    ]],
    on="trainer_jockey_key_v1",
    how="left"
)

out["win_lift_pct"] = (out["win_pct"] - out["combo_base_win_pct"]).round(4)
out["place_lift_pct"] = (out["place_pct"] - out["combo_base_place_pct"]).round(4)
out["signal"] = out.apply(signal_row, axis=1)
out["evidence_band"] = out["starts"].apply(evidence_band)
out["insight"] = out.apply(make_insight, axis=1)
out["built_at"] = datetime.now(timezone.utc).isoformat()

out["first_meeting_date"] = out["first_meeting_date"].dt.strftime("%Y-%m-%d")
out["last_meeting_date"] = out["last_meeting_date"].dt.strftime("%Y-%m-%d")

cols = [
    "trainer_jockey_key_v1",
    "trainer_key",
    "trainer",
    "jockey_key",
    "jockey",
    "prep_stage",
    "starts",
    "wins",
    "places",
    "win_pct",
    "place_pct",
    "combo_base_starts",
    "combo_base_win_pct",
    "combo_base_place_pct",
    "win_lift_pct",
    "place_lift_pct",
    "avg_sp",
    "signal",
    "evidence_band",
    "first_meeting_date",
    "last_meeting_date",
    "insight",
    "built_at",
]

out = out[cols].sort_values(
    ["signal", "evidence_band", "win_lift_pct", "place_lift_pct", "starts"],
    ascending=[True, True, False, False, False]
)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "TRAINER_JOCKEY_PREP_ENGINE_V1_BUILT",
    "rows": len(out),
    "history_rows_used": len(df),
    "unique_trainers": out["trainer_key"].nunique(),
    "unique_jockeys": out["jockey_key"].nunique(),
    "unique_combos": out["trainer_jockey_key_v1"].nunique(),
    "combo_prep_edges": int((out["signal"] == "COMBO_PREP_EDGE").sum()),
    "mild_combo_prep_edges": int((out["signal"] == "MILD_COMBO_PREP_EDGE").sum()),
    "combo_prep_risks": int((out["signal"] == "COMBO_PREP_RISK").sum()),
    "low_sample": int((out["signal"] == "LOW_SAMPLE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[TRAINER_JOCKEY_PREP_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
