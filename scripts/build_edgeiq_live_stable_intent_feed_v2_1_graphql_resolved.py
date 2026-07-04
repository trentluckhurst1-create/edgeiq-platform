import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
WAREHOUSE = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
RESOLVER = DATA / "edgeiq_live_graphql_entity_resolution_bridge_v3.csv"
TRAINER_PREP = DATA / "edgeiq_trainer_stage_of_prep_engine_v2_graphql.csv"
COMBO_PREP = DATA / "edgeiq_trainer_jockey_prep_engine_v2_graphql.csv"

OUT = DATA / "edgeiq_live_stable_intent_feed_v2_1_graphql_resolved.csv"
SUMMARY = DATA / "edgeiq_live_stable_intent_feed_v2_1_graphql_resolved_summary.csv"

SPELL_DAYS = 56

def key(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper().replace(" ", "").replace(".", "").replace("'", "")

def live_prep_stage(hist_dates, live_date):
    dates = sorted([d for d in hist_dates if pd.notna(d) and d < live_date])
    if not dates:
        return "FIRST_UP"

    last = dates[-1]
    if (live_date - last).days >= SPELL_DAYS:
        return "FIRST_UP"

    prep_dates = [last]
    for d in reversed(dates[:-1]):
        if (prep_dates[-1] - d).days >= SPELL_DAYS:
            break
        prep_dates.append(d)

    n = len(prep_dates) + 1
    if n == 2:
        return "SECOND_UP"
    if n == 3:
        return "THIRD_UP"
    if n == 4:
        return "FOURTH_UP"
    return "DEEP_PREP"

def score(trainer_signal, combo_signal, trainer_evidence, combo_evidence):
    s = 40

    if trainer_signal == "PREP_CONTEXT_EDGE":
        s = max(s, 78)
    elif trainer_signal == "MILD_PREP_CONTEXT_EDGE":
        s = max(s, 62)
    elif trainer_signal == "PREP_CONTEXT_RISK":
        s = min(s, 32)
    elif trainer_signal == "NEUTRAL":
        s = max(s, 48)

    if combo_signal == "COMBO_PREP_EDGE":
        s = max(s, 84)
    elif combo_signal == "MILD_COMBO_PREP_EDGE":
        s = max(s, 68)
    elif combo_signal == "COMBO_PREP_RISK":
        s = min(s, 28)
    elif combo_signal == "NEUTRAL":
        s = max(s, 50)

    if trainer_evidence in ["ELITE_SAMPLE", "STRONG"] and trainer_signal in ["PREP_CONTEXT_EDGE", "MILD_PREP_CONTEXT_EDGE"]:
        s += 4
    if combo_evidence in ["ELITE_SAMPLE", "STRONG"] and combo_signal in ["COMBO_PREP_EDGE", "MILD_COMBO_PREP_EDGE"]:
        s += 4

    return max(0, min(100, round(s, 1)))

def band(s):
    if s >= 80:
        return "STRONG_INTENT"
    if s >= 65:
        return "POSITIVE_INTENT"
    if s >= 50:
        return "WATCH"
    if s <= 34:
        return "CAUTION"
    return "LOW_EVIDENCE"

def reason(r):
    bits = []
    if r["trainer_prep_signal"] != "NO_PROFILE":
        bits.append(f"Trainer prep: {r['trainer_prep_signal']} ({r['trainer_prep_starts']} starts)")
    if r["combo_prep_signal"] != "NO_PROFILE":
        bits.append(f"Trainer/jockey prep: {r['combo_prep_signal']} ({r['combo_prep_starts']} starts)")
    if not bits:
        return "No GraphQL stable-intent profile available yet."
    return " | ".join(bits)

print("[LIVE_STABLE_INTENT_V2_1_GRAPHQL_RESOLVED] loading...")
live = pd.read_csv(LIVE, low_memory=False)
wh = pd.read_csv(WAREHOUSE, low_memory=False, usecols=["race_date","horse","scratched","finish_num"])
resolver = pd.read_csv(RESOLVER, low_memory=False)
trainer = pd.read_csv(TRAINER_PREP, low_memory=False)
combo = pd.read_csv(COMBO_PREP, low_memory=False)

live["race_date"] = pd.to_datetime(live["race_date"], errors="coerce")
live["horse_key_join"] = live["horse"].map(key)

resolver["entity_type"] = resolver["entity_type"].astype(str).str.upper()
resolver["live_name_key"] = resolver["live_name"].map(key)
resolver["graphql_key_resolved"] = resolver["graphql_name"].map(key)

trainer_res = resolver[
    (resolver["entity_type"] == "TRAINER") &
    (resolver["match_status"] == "MATCHED")
][["live_name_key","graphql_key_resolved","graphql_name"]].drop_duplicates("live_name_key")

jockey_res = resolver[
    (resolver["entity_type"] == "JOCKEY") &
    (resolver["match_status"] == "MATCHED")
][["live_name_key","graphql_key_resolved","graphql_name"]].drop_duplicates("live_name_key")

live["trainer_live_key"] = live["trainer"].map(key)
live["jockey_live_key"] = live["jockey"].map(key)

live = live.merge(
    trainer_res.rename(columns={
        "live_name_key": "trainer_live_key",
        "graphql_key_resolved": "trainer_key_resolved",
        "graphql_name": "trainer_graphql_name",
    }),
    on="trainer_live_key",
    how="left"
)

live = live.merge(
    jockey_res.rename(columns={
        "live_name_key": "jockey_live_key",
        "graphql_key_resolved": "jockey_key_resolved",
        "graphql_name": "jockey_graphql_name",
    }),
    on="jockey_live_key",
    how="left"
)

live["trainer_key_resolved"] = live["trainer_key_resolved"].fillna(live["trainer_live_key"])
live["jockey_key_resolved"] = live["jockey_key_resolved"].fillna(live["jockey_live_key"])
live["trainer_jockey_key_resolved"] = live["trainer_key_resolved"] + "|" + live["jockey_key_resolved"]

wh["race_date"] = pd.to_datetime(wh["race_date"], errors="coerce")
wh["horse_key_join"] = wh["horse"].map(key)
wh["scratched_bool"] = wh["scratched"].astype(str).str.lower().eq("true")
wh["finish_num"] = pd.to_numeric(wh["finish_num"], errors="coerce")
wh = wh[(wh["race_date"].notna()) & (~wh["scratched_bool"]) & (wh["finish_num"].notna())].copy()

hist_dates = wh.groupby("horse_key_join")["race_date"].apply(list).to_dict()

print("[LIVE_STABLE_INTENT_V2_1_GRAPHQL_RESOLVED] deriving prep stage...")
live["prep_stage"] = live.apply(
    lambda r: live_prep_stage(hist_dates.get(r["horse_key_join"], []), r["race_date"])
    if pd.notna(r["race_date"]) else "UNKNOWN",
    axis=1
)

trainer_small = trainer.rename(columns={
    "starts": "trainer_prep_starts",
    "wins": "trainer_prep_wins",
    "places": "trainer_prep_places",
    "win_pct": "trainer_prep_win_pct",
    "place_pct": "trainer_prep_place_pct",
    "win_lift_pct": "trainer_prep_win_lift_pct",
    "place_lift_pct": "trainer_prep_place_lift_pct",
    "signal": "trainer_prep_signal",
    "evidence_band": "trainer_prep_evidence",
})

combo_small = combo.rename(columns={
    "starts": "combo_prep_starts",
    "wins": "combo_prep_wins",
    "places": "combo_prep_places",
    "win_pct": "combo_prep_win_pct",
    "place_pct": "combo_prep_place_pct",
    "win_lift_pct": "combo_prep_win_lift_pct",
    "place_lift_pct": "combo_prep_place_lift_pct",
    "signal": "combo_prep_signal",
    "evidence_band": "combo_prep_evidence",
})

out = live.merge(
    trainer_small[[
        "trainer_key","prep_stage","trainer_prep_starts","trainer_prep_wins","trainer_prep_places",
        "trainer_prep_win_pct","trainer_prep_place_pct","trainer_prep_win_lift_pct","trainer_prep_place_lift_pct",
        "trainer_prep_signal","trainer_prep_evidence"
    ]],
    left_on=["trainer_key_resolved","prep_stage"],
    right_on=["trainer_key","prep_stage"],
    how="left"
)

out = out.merge(
    combo_small[[
        "trainer_jockey_key","prep_stage","combo_prep_starts","combo_prep_wins","combo_prep_places",
        "combo_prep_win_pct","combo_prep_place_pct","combo_prep_win_lift_pct","combo_prep_place_lift_pct",
        "combo_prep_signal","combo_prep_evidence"
    ]],
    left_on=["trainer_jockey_key_resolved","prep_stage"],
    right_on=["trainer_jockey_key","prep_stage"],
    how="left"
)

for c in ["trainer_prep_signal","trainer_prep_evidence","combo_prep_signal","combo_prep_evidence"]:
    out[c] = out[c].fillna("NO_PROFILE")

for c in ["trainer_prep_starts","combo_prep_starts"]:
    out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)

out["stable_intent_v2_1_graphql_score"] = out.apply(
    lambda r: score(r["trainer_prep_signal"], r["combo_prep_signal"], r["trainer_prep_evidence"], r["combo_prep_evidence"]),
    axis=1
)
out["stable_intent_v2_1_graphql_band"] = out["stable_intent_v2_1_graphql_score"].apply(band)
out["stable_intent_v2_1_graphql_reason"] = out.apply(reason, axis=1)
out["built_at"] = datetime.now(timezone.utc).isoformat()

cols = [
    "race_date","day_bucket","track","race_no","race_key","horse","horse_key","saddlecloth","barrier",
    "trainer","jockey","trainer_graphql_name","jockey_graphql_name",
    "trainer_key_resolved","jockey_key_resolved","trainer_jockey_key_resolved",
    "prep_stage",
    "trainer_prep_signal","trainer_prep_evidence","trainer_prep_starts","trainer_prep_win_pct","trainer_prep_place_pct","trainer_prep_win_lift_pct","trainer_prep_place_lift_pct",
    "combo_prep_signal","combo_prep_evidence","combo_prep_starts","combo_prep_win_pct","combo_prep_place_pct","combo_prep_win_lift_pct","combo_prep_place_lift_pct",
    "stable_intent_v2_1_graphql_score","stable_intent_v2_1_graphql_band","stable_intent_v2_1_graphql_reason",
    "is_scratched","runner_status","built_at"
]

for c in cols:
    if c not in out.columns:
        out[c] = ""

out = out[cols].sort_values(["race_date","track","race_no","saddlecloth"])

out["_profile_strength_sort"] = (
    out["trainer_prep_starts"].fillna(0).astype(int) +
    out["combo_prep_starts"].fillna(0).astype(int)
)

out = (
    out.sort_values(
        ["race_date","track","race_no","horse_key","_profile_strength_sort","stable_intent_v2_1_graphql_score"],
        ascending=[True, True, True, True, False, False]
    )
    .drop_duplicates(["race_date","track","race_no","horse_key"], keep="first")
    .drop(columns=["_profile_strength_sort"])
    .sort_values(["race_date","track","race_no","saddlecloth"])
)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "LIVE_STABLE_INTENT_FEED_V2_1_GRAPHQL_RESOLVED_BUILT",
    "rows": len(out),
    "trainer_profiles": int((out["trainer_prep_signal"] != "NO_PROFILE").sum()),
    "combo_profiles": int((out["combo_prep_signal"] != "NO_PROFILE").sum()),
    "strong_intent": int((out["stable_intent_v2_1_graphql_band"] == "STRONG_INTENT").sum()),
    "positive_intent": int((out["stable_intent_v2_1_graphql_band"] == "POSITIVE_INTENT").sum()),
    "watch": int((out["stable_intent_v2_1_graphql_band"] == "WATCH").sum()),
    "caution": int((out["stable_intent_v2_1_graphql_band"] == "CAUTION").sum()),
    "low_evidence": int((out["stable_intent_v2_1_graphql_band"] == "LOW_EVIDENCE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[LIVE_STABLE_INTENT_V2_1_GRAPHQL_RESOLVED] COMPLETE")
print(summary.to_string(index=False))

