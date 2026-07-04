import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

NARR = DATA / "edgeiq_narrative_engine_v1.csv"
STABLE = DATA / "edgeiq_stable_intent_engine_v1_1_rebalance.csv"

OUT = DATA / "edgeiq_factor_selection_engine_v2_1_separation.csv"
SUMMARY = DATA / "edgeiq_factor_selection_engine_v2_1_separation_summary.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def add_factor(rows, race_key, factor_type, factor_name, direction, strength, horse, detail):
    if not factor_name:
        return
    rows.append({
        "race_key": race_key,
        "race_date": race_key[0],
        "track": race_key[1],
        "race_no": race_key[2],
        "factor_type": factor_type,
        "factor_name": factor_name,
        "direction": direction,
        "strength": strength,
        "horse": horse,
        "detail": detail,
    })

print("[FACTOR_SELECTION_ENGINE_V2] loading inputs...")
stable = pd.read_csv(STABLE, low_memory=False)
narr = pd.read_csv(NARR, low_memory=False) if NARR.exists() else pd.DataFrame()

stable["race_date"] = pd.to_datetime(stable["race_date"], errors="coerce").dt.strftime("%Y-%m-%d")
stable["track"] = stable["track"].astype(str)
stable["race_no"] = stable["race_no"].astype(str)

rows = []

for _, r in stable.iterrows():
    race_key = (clean(r["race_date"]), clean(r["track"]), clean(r["race_no"]))
    horse = clean(r.get("horse"))

    band = clean(r.get("stable_intent_v1_1_band"))
    reason = clean(r.get("stable_intent_v1_1_reason"))
    conn = clean(r.get("connection_band"))
    trainer_sig = clean(r.get("trainer_prep_signal"))
    combo_sig = clean(r.get("stable_intent_signal"))
    prep_stage = clean(r.get("prep_stage"))

    if band in ["WATCH", "POSITIVE_INTENT", "STRONG_INTENT"]:
        add_factor(rows, race_key, "STABLE_INTENT", f"Stable intent: {prep_stage}", "HELPS", 2 if band == "WATCH" else 3, horse, reason)

    if band == "CAUTION":
        add_factor(rows, race_key, "STABLE_INTENT", f"Stable intent caution: {prep_stage}", "HURTS", 3, horse, reason)

    if conn in ["STRONG", "ELITE", "POSITIVE"]:
        add_factor(rows, race_key, "CONNECTION", f"Connection profile: {conn}", "HELPS", 2 if conn == "POSITIVE" else 3, horse, reason)

    if conn in ["NEGATIVE", "POOR"]:
        add_factor(rows, race_key, "CONNECTION", f"Connection profile: {conn}", "HURTS", 2 if conn == "NEGATIVE" else 3, horse, reason)

    if trainer_sig == "MILD_PREP_CONTEXT_EDGE":
        add_factor(rows, race_key, "TRAINER_PREP", f"Trainer prep edge: {prep_stage}", "HELPS", 2, horse, reason)

    if trainer_sig == "PREP_CONTEXT_RISK":
        add_factor(rows, race_key, "TRAINER_PREP", f"Trainer prep risk: {prep_stage}", "HURTS", 3, horse, reason)

    if combo_sig in ["COMBO_PREP_EDGE", "MILD_COMBO_PREP_EDGE"]:
        add_factor(rows, race_key, "TRAINER_JOCKEY_PREP", f"Trainer/jockey prep edge: {prep_stage}", "HELPS", 3, horse, reason)

factor_rows = pd.DataFrame(rows)

if factor_rows.empty:
    out = pd.DataFrame(columns=[
        "race_date","track","race_no","runner_count","factor_count",
        "what_matters_1","what_matters_1_direction","what_matters_1_strength","what_matters_1_runners",
        "what_matters_2","what_matters_2_direction","what_matters_2_strength","what_matters_2_runners",
        "what_matters_3","what_matters_3_direction","what_matters_3_strength","what_matters_3_runners",
        "what_helps","what_hurts","what_to_watch","race_factor_view","built_at"
    ])
else:
    grouped = []

    for race_key, g in factor_rows.groupby(["race_date", "track", "race_no"], dropna=False):
        race_date, track, race_no = race_key
        runner_count = stable[
            (stable["race_date"] == race_date) &
            (stable["track"] == track) &
            (stable["race_no"].astype(str) == str(race_no))
        ]["horse"].nunique()

        fg = (
            g.groupby(["factor_type", "factor_name", "direction"], dropna=False)
            .agg(
                runners=("horse", lambda x: ", ".join(list(dict.fromkeys([str(v) for v in x if str(v).strip()]))[:6])),
                runner_count=("horse", "nunique"),
                strength=("strength", "sum"),
            )
            .reset_index()
        )

        fg["coverage_pct"] = (fg["runner_count"] / max(runner_count, 1) * 100).round(2)

        def coverage_penalty(pct):
            if pct >= 80:
                return 10
            if pct >= 65:
                return 7
            if pct >= 50:
                return 5
            if pct >= 35:
                return 2
            return 0

        fg["coverage_penalty"] = fg["coverage_pct"].apply(coverage_penalty)
        fg["importance_score"] = fg["strength"] + fg["runner_count"] - fg["coverage_penalty"]

        broad_first_up = (
            (fg["factor_name"] == "Stable intent: FIRST_UP") &
            (fg["coverage_pct"] >= 45)
        )
        fg.loc[broad_first_up, "importance_score"] = -1

        broad_negative_connection = (
            (fg["factor_name"] == "Connection profile: NEGATIVE") &
            (fg["coverage_pct"] >= 30)
        )
        fg.loc[broad_negative_connection, "importance_score"] = -1

        fg = fg.sort_values(
            ["importance_score", "runner_count", "coverage_pct"],
            ascending=[False, False, True]
        ).head(3)

        helps = g[g["direction"] == "HELPS"]["horse"].dropna().astype(str).unique().tolist()
        hurts = g[g["direction"] == "HURTS"]["horse"].dropna().astype(str).unique().tolist()

        top = fg.to_dict("records")
        while len(top) < 3:
            top.append({"factor_name": "", "direction": "", "importance_score": 0, "runners": "", "coverage_pct": 0})

        what_helps = ", ".join(helps[:8]) if helps else "No clear positive cluster detected."
        what_hurts = ", ".join(hurts[:8]) if hurts else "No clear caution cluster detected."

        watch_bits = []
        for item in top:
            if item["factor_name"]:
                watch_bits.append(f"{item['factor_name']} ({item['direction']})")
        what_to_watch = "; ".join(watch_bits) if watch_bits else "No dominant race factor detected."

        race_factor_view = (
            f"This race appears most shaped by: {what_to_watch}."
            if watch_bits else
            "No dominant race-level factor has separated the field yet."
        )

        grouped.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "runner_count": runner_count,
            "factor_count": len(g),
            "what_matters_1": top[0]["factor_name"],
            "what_matters_1_direction": top[0]["direction"],
            "what_matters_1_strength": top[0]["importance_score"],
            "what_matters_1_runners": top[0]["runners"],
            "what_matters_2": top[1]["factor_name"],
            "what_matters_2_direction": top[1]["direction"],
            "what_matters_2_strength": top[1]["importance_score"],
            "what_matters_2_runners": top[1]["runners"],
            "what_matters_3": top[2]["factor_name"],
            "what_matters_3_direction": top[2]["direction"],
            "what_matters_3_strength": top[2]["importance_score"],
            "what_matters_3_runners": top[2]["runners"],
            "what_helps": what_helps,
            "what_hurts": what_hurts,
            "what_to_watch": what_to_watch,
            "race_factor_view": race_factor_view,
            "built_at": datetime.now(timezone.utc).isoformat(),
        })

    out = pd.DataFrame(grouped).sort_values(["race_date", "track", "race_no"])

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "FACTOR_SELECTION_ENGINE_V2_1_SEPARATION_BUILT",
    "race_rows": len(out),
    "factor_detail_rows": len(factor_rows),
    "races_with_factors": int((out["factor_count"].fillna(0).astype(float) > 0).sum()) if len(out) else 0,
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[FACTOR_SELECTION_ENGINE_V2] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))



