import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
HORSE_OUT = DATA / "edgeiq_horse_stage_of_prep_engine_v2_graphql.csv"
TRAINER_OUT = DATA / "edgeiq_trainer_stage_of_prep_engine_v2_graphql.csv"
SUMMARY = DATA / "edgeiq_stage_of_prep_engine_v2_graphql_summary.csv"

SPELL_DAYS = 56

def key(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper().replace(" ", "").replace(".", "").replace("'", "")

def signal(starts, win_lift, place_lift):
    if starts < 5:
        return "LOW_SAMPLE"
    if win_lift >= 20 and place_lift >= 15:
        return "PREP_CONTEXT_EDGE"
    if win_lift >= 10 or place_lift >= 10:
        return "MILD_PREP_CONTEXT_EDGE"
    if win_lift <= -15 and place_lift <= -10:
        return "PREP_CONTEXT_RISK"
    return "NEUTRAL"

def evidence(starts):
    if starts >= 100:
        return "ELITE_SAMPLE"
    if starts >= 40:
        return "STRONG"
    if starts >= 15:
        return "MODERATE"
    if starts >= 5:
        return "DEVELOPING"
    return "LOW_SAMPLE"

print("[STAGE_OF_PREP_V2_GRAPHQL] loading warehouse...")
df = pd.read_csv(INP, low_memory=False)

df["race_date"] = pd.to_datetime(df["race_date"], errors="coerce")
df["horse_key"] = df["horse"].map(key)
df["trainer_key"] = df["trainer"].map(key)
df["finish_num"] = pd.to_numeric(df["finish_num"], errors="coerce")
df["won"] = (df["finish_num"] == 1).astype(int)
df["placed"] = df["finish_num"].isin([1,2,3]).astype(int)
df["scratched_bool"] = df["scratched"].astype(str).str.lower().eq("true")

df = df[
    (df["race_date"].notna()) &
    (df["horse_key"] != "") &
    (~df["scratched_bool"]) &
    (df["finish_num"].notna())
].copy()

print("[STAGE_OF_PREP_V2_GRAPHQL] deriving prep stage...")
df = df.sort_values(["horse_key","race_date","track","race_no"]).copy()
df["prev_run_date"] = df.groupby("horse_key")["race_date"].shift(1)
df["days_since_prev"] = (df["race_date"] - df["prev_run_date"]).dt.days
df["new_prep"] = df["days_since_prev"].isna() | (df["days_since_prev"] >= SPELL_DAYS)
df["prep_id"] = df.groupby("horse_key")["new_prep"].cumsum()
df["prep_run_no"] = df.groupby(["horse_key","prep_id"]).cumcount() + 1

df["prep_stage"] = "DEEP_PREP"
df.loc[df["prep_run_no"] == 1, "prep_stage"] = "FIRST_UP"
df.loc[df["prep_run_no"] == 2, "prep_stage"] = "SECOND_UP"
df.loc[df["prep_run_no"] == 3, "prep_stage"] = "THIRD_UP"
df.loc[df["prep_run_no"] == 4, "prep_stage"] = "FOURTH_UP"

horse_base = (
    df.groupby(["horse_key","horse"], dropna=False)
    .agg(horse_base_starts=("horse_key","count"), horse_base_wins=("won","sum"), horse_base_places=("placed","sum"))
    .reset_index()
)
horse_base["horse_base_win_pct"] = (horse_base["horse_base_wins"] / horse_base["horse_base_starts"] * 100).round(4)
horse_base["horse_base_place_pct"] = (horse_base["horse_base_places"] / horse_base["horse_base_starts"] * 100).round(4)

horse = (
    df.groupby(["horse_key","horse","prep_stage"], dropna=False)
    .agg(starts=("horse_key","count"), wins=("won","sum"), places=("placed","sum"))
    .reset_index()
    .merge(horse_base[["horse_key","horse_base_starts","horse_base_win_pct","horse_base_place_pct"]], on="horse_key", how="left")
)

horse["win_pct"] = (horse["wins"] / horse["starts"] * 100).round(4)
horse["place_pct"] = (horse["places"] / horse["starts"] * 100).round(4)
horse["win_lift_pct"] = (horse["win_pct"] - horse["horse_base_win_pct"]).round(4)
horse["place_lift_pct"] = (horse["place_pct"] - horse["horse_base_place_pct"]).round(4)
horse["signal"] = horse.apply(lambda r: signal(r["starts"], r["win_lift_pct"], r["place_lift_pct"]), axis=1)
horse["evidence_band"] = horse["starts"].apply(evidence)
horse["built_at"] = datetime.now(timezone.utc).isoformat()

trainer_df = df[df["trainer_key"] != ""].copy()

trainer_base = (
    trainer_df.groupby(["trainer_key","trainer"], dropna=False)
    .agg(trainer_base_starts=("trainer_key","count"), trainer_base_wins=("won","sum"), trainer_base_places=("placed","sum"))
    .reset_index()
)
trainer_base["trainer_base_win_pct"] = (trainer_base["trainer_base_wins"] / trainer_base["trainer_base_starts"] * 100).round(4)
trainer_base["trainer_base_place_pct"] = (trainer_base["trainer_base_places"] / trainer_base["trainer_base_starts"] * 100).round(4)

trainer = (
    trainer_df.groupby(["trainer_key","trainer","prep_stage"], dropna=False)
    .agg(starts=("trainer_key","count"), wins=("won","sum"), places=("placed","sum"))
    .reset_index()
    .merge(trainer_base[["trainer_key","trainer_base_starts","trainer_base_win_pct","trainer_base_place_pct"]], on="trainer_key", how="left")
)

trainer["win_pct"] = (trainer["wins"] / trainer["starts"] * 100).round(4)
trainer["place_pct"] = (trainer["places"] / trainer["starts"] * 100).round(4)
trainer["win_lift_pct"] = (trainer["win_pct"] - trainer["trainer_base_win_pct"]).round(4)
trainer["place_lift_pct"] = (trainer["place_pct"] - trainer["trainer_base_place_pct"]).round(4)
trainer["signal"] = trainer.apply(lambda r: signal(r["starts"], r["win_lift_pct"], r["place_lift_pct"]), axis=1)
trainer["evidence_band"] = trainer["starts"].apply(evidence)
trainer["built_at"] = datetime.now(timezone.utc).isoformat()

horse.to_csv(HORSE_OUT, index=False)
trainer.to_csv(TRAINER_OUT, index=False)

summary = pd.DataFrame([{
    "status": "STAGE_OF_PREP_ENGINE_V2_GRAPHQL_BUILT",
    "source_rows": len(df),
    "horse_stage_rows": len(horse),
    "trainer_stage_rows": len(trainer),
    "horse_edges": int((horse["signal"] == "PREP_CONTEXT_EDGE").sum()),
    "horse_mild_edges": int((horse["signal"] == "MILD_PREP_CONTEXT_EDGE").sum()),
    "horse_risks": int((horse["signal"] == "PREP_CONTEXT_RISK").sum()),
    "trainer_edges": int((trainer["signal"] == "PREP_CONTEXT_EDGE").sum()),
    "trainer_mild_edges": int((trainer["signal"] == "MILD_PREP_CONTEXT_EDGE").sum()),
    "trainer_risks": int((trainer["signal"] == "PREP_CONTEXT_RISK").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[STAGE_OF_PREP_V2_GRAPHQL] COMPLETE")
print(summary.to_string(index=False))
