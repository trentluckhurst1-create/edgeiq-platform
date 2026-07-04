import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
OUT = DATA / "edgeiq_trainer_jockey_prep_engine_v2_graphql.csv"
SUMMARY = DATA / "edgeiq_trainer_jockey_prep_engine_v2_graphql_summary.csv"

SPELL_DAYS = 56

def key(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper().replace(" ", "").replace(".", "").replace("'", "")

def signal(starts, win_lift, place_lift):
    if starts < 8:
        return "LOW_SAMPLE"
    if win_lift >= 20 and place_lift >= 15:
        return "COMBO_PREP_EDGE"
    if win_lift >= 10 or place_lift >= 10:
        return "MILD_COMBO_PREP_EDGE"
    if win_lift <= -15 and place_lift <= -10:
        return "COMBO_PREP_RISK"
    return "NEUTRAL"

def evidence(starts):
    if starts >= 80:
        return "ELITE_SAMPLE"
    if starts >= 40:
        return "STRONG"
    if starts >= 20:
        return "MODERATE"
    if starts >= 8:
        return "DEVELOPING"
    return "LOW_SAMPLE"

print("[TRAINER_JOCKEY_PREP_V2_GRAPHQL] loading warehouse...")
df = pd.read_csv(INP, low_memory=False)

df["race_date"] = pd.to_datetime(df["race_date"], errors="coerce")
df["horse_key"] = df["horse"].map(key)
df["trainer_key"] = df["trainer"].map(key)
df["jockey_key"] = df["jockey"].map(key)
df["finish_num"] = pd.to_numeric(df["finish_num"], errors="coerce")
df["won"] = (df["finish_num"] == 1).astype(int)
df["placed"] = df["finish_num"].isin([1,2,3]).astype(int)
df["scratched_bool"] = df["scratched"].astype(str).str.lower().eq("true")

df = df[
    (df["race_date"].notna()) &
    (df["horse_key"] != "") &
    (df["trainer_key"] != "") &
    (df["jockey_key"] != "") &
    (~df["scratched_bool"]) &
    (df["finish_num"].notna())
].copy()

print("[TRAINER_JOCKEY_PREP_V2_GRAPHQL] deriving prep stage...")
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

df["trainer_jockey_key"] = df["trainer_key"] + "|" + df["jockey_key"]
df["trainer_jockey_name"] = df["trainer"].astype(str).str.strip() + " + " + df["jockey"].astype(str).str.strip()

base = (
    df.groupby(["trainer_jockey_key","trainer_key","trainer","jockey_key","jockey","trainer_jockey_name"], dropna=False)
    .agg(
        combo_base_starts=("trainer_jockey_key","count"),
        combo_base_wins=("won","sum"),
        combo_base_places=("placed","sum"),
    )
    .reset_index()
)

base["combo_base_win_pct"] = (base["combo_base_wins"] / base["combo_base_starts"] * 100).round(4)
base["combo_base_place_pct"] = (base["combo_base_places"] / base["combo_base_starts"] * 100).round(4)

out = (
    df.groupby(["trainer_jockey_key","trainer_key","trainer","jockey_key","jockey","trainer_jockey_name","prep_stage"], dropna=False)
    .agg(
        starts=("trainer_jockey_key","count"),
        wins=("won","sum"),
        places=("placed","sum"),
        first_date=("race_date","min"),
        last_date=("race_date","max"),
    )
    .reset_index()
    .merge(
        base[["trainer_jockey_key","combo_base_starts","combo_base_win_pct","combo_base_place_pct"]],
        on="trainer_jockey_key",
        how="left"
    )
)

out["win_pct"] = (out["wins"] / out["starts"] * 100).round(4)
out["place_pct"] = (out["places"] / out["starts"] * 100).round(4)
out["win_lift_pct"] = (out["win_pct"] - out["combo_base_win_pct"]).round(4)
out["place_lift_pct"] = (out["place_pct"] - out["combo_base_place_pct"]).round(4)
out["signal"] = out.apply(lambda r: signal(r["starts"], r["win_lift_pct"], r["place_lift_pct"]), axis=1)
out["evidence_band"] = out["starts"].apply(evidence)
out["first_date"] = out["first_date"].dt.strftime("%Y-%m-%d")
out["last_date"] = out["last_date"].dt.strftime("%Y-%m-%d")
out["built_at"] = datetime.now(timezone.utc).isoformat()

out = out.sort_values(
    ["signal","evidence_band","win_lift_pct","place_lift_pct","starts"],
    ascending=[True, True, False, False, False]
)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "TRAINER_JOCKEY_PREP_ENGINE_V2_GRAPHQL_BUILT",
    "source_rows": len(df),
    "rows": len(out),
    "unique_combos": out["trainer_jockey_key"].nunique(),
    "combo_edges": int((out["signal"] == "COMBO_PREP_EDGE").sum()),
    "mild_combo_edges": int((out["signal"] == "MILD_COMBO_PREP_EDGE").sum()),
    "combo_risks": int((out["signal"] == "COMBO_PREP_RISK").sum()),
    "low_sample": int((out["signal"] == "LOW_SAMPLE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[TRAINER_JOCKEY_PREP_V2_GRAPHQL] COMPLETE")
print(summary.to_string(index=False))
