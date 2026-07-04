import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
HIST = DATA / "edgeiq_trainer_jockey_runner_history_v1.csv"
BRIDGE = DATA / "edgeiq_live_entity_resolution_bridge_v2.csv"
ENGINE = DATA / "edgeiq_trainer_jockey_prep_engine_v1.csv"

OUT = DATA / "edgeiq_live_stable_intent_feed_v1.csv"
SUMMARY = DATA / "edgeiq_live_stable_intent_feed_v1_summary.csv"

SPELL_DAYS = 56

def clean_key(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper().replace(" ", "").replace(".", "").replace("'", "").replace("&", "")

def live_prep_stage(hist_dates, live_date):
    dates = sorted([d for d in hist_dates if pd.notna(d) and d < live_date])
    if not dates:
        return "FIRST_UP"

    last = dates[-1]
    days_since = (live_date - last).days

    if days_since >= SPELL_DAYS:
        return "FIRST_UP"

    prep_dates = [last]
    for d in reversed(dates[:-1]):
        gap = (prep_dates[-1] - d).days
        if gap >= SPELL_DAYS:
            break
        prep_dates.append(d)

    next_run_no = len(prep_dates) + 1

    if next_run_no == 2:
        return "SECOND_UP"
    if next_run_no == 3:
        return "THIRD_UP"
    if next_run_no == 4:
        return "FOURTH_UP"
    return "DEEP_PREP"

def intent_score(signal, evidence):
    if signal == "COMBO_PREP_EDGE":
        return 90 if evidence == "STRONG" else 84
    if signal == "MILD_COMBO_PREP_EDGE":
        return 76 if evidence in ["STRONG", "MODERATE"] else 68
    if signal == "COMBO_PREP_RISK":
        return 25
    if signal == "NEUTRAL":
        return 50
    return 40

def intent_band(score):
    if score >= 85:
        return "STRONG_INTENT"
    if score >= 65:
        return "POSITIVE_INTENT"
    if score <= 30:
        return "NEGATIVE_INTENT"
    if score < 50:
        return "LOW_EVIDENCE"
    return "NEUTRAL"

print("[LIVE_STABLE_INTENT_FEED_V1] loading inputs...")
live = pd.read_csv(LIVE, low_memory=False)
hist = pd.read_csv(HIST, low_memory=False)
bridge = pd.read_csv(BRIDGE, low_memory=False)
engine = pd.read_csv(ENGINE, low_memory=False)

live["race_date"] = pd.to_datetime(live["race_date"], errors="coerce")
hist["meeting_date"] = pd.to_datetime(hist["meeting_date"], errors="coerce")

live["trainer_display_key"] = live["trainer"].map(clean_key)
live["jockey_display_key"] = live["jockey"].map(clean_key)
live["horse_key_clean"] = live["horse_key"].map(clean_key)

bridge["entity_type"] = bridge["entity_type"].fillna("").astype(str).str.upper()
bridge["display_key"] = bridge["display_key"].map(clean_key)
bridge["canonical_key"] = bridge["canonical_key"].map(clean_key)

trainer_bridge = bridge[
    (bridge["entity_type"] == "TRAINER") &
    (bridge["match_status"] == "MATCHED")
][["display_key", "canonical_key", "canonical_name"]].drop_duplicates("display_key")

jockey_bridge = bridge[
    (bridge["entity_type"] == "JOCKEY") &
    (bridge["match_status"] == "MATCHED")
][["display_key", "canonical_key", "canonical_name"]].drop_duplicates("display_key")

live = live.merge(
    trainer_bridge.rename(columns={
        "display_key": "trainer_display_key",
        "canonical_key": "trainer_key_resolved",
        "canonical_name": "trainer_canonical"
    }),
    on="trainer_display_key",
    how="left"
)

live = live.merge(
    jockey_bridge.rename(columns={
        "display_key": "jockey_display_key",
        "canonical_key": "jockey_key_resolved",
        "canonical_name": "jockey_canonical"
    }),
    on="jockey_display_key",
    how="left"
)

live["trainer_key_resolved"] = live["trainer_key_resolved"].fillna(live["trainer_display_key"])
live["jockey_key_resolved"] = live["jockey_key_resolved"].fillna(live["jockey_display_key"])
live["trainer_jockey_key_v1"] = live["trainer_key_resolved"] + "|" + live["jockey_key_resolved"]

hist["horse_key_clean"] = hist["horse_key"].map(clean_key)
hist_dates = (
    hist[hist["meeting_date"].notna()]
    .groupby("horse_key_clean")["meeting_date"]
    .apply(list)
    .to_dict()
)

print("[LIVE_STABLE_INTENT_FEED_V1] deriving live prep stage...")
live["prep_stage"] = live.apply(
    lambda r: live_prep_stage(hist_dates.get(r["horse_key_clean"], []), r["race_date"])
    if pd.notna(r["race_date"]) else "UNKNOWN",
    axis=1
)

engine["trainer_jockey_key_v1"] = engine["trainer_jockey_key_v1"].fillna("").astype(str)
engine["prep_stage"] = engine["prep_stage"].fillna("").astype(str)

keep = [
    "trainer_jockey_key_v1",
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
    "insight",
]

out = live.merge(
    engine[keep],
    on=["trainer_jockey_key_v1", "prep_stage"],
    how="left"
)

out["stable_intent_signal"] = out["signal"].fillna("NO_PROFILE")
out["stable_intent_evidence"] = out["evidence_band"].fillna("NO_PROFILE")
out["stable_intent_score"] = out.apply(
    lambda r: intent_score(r["stable_intent_signal"], r["stable_intent_evidence"]),
    axis=1
)
out["stable_intent_band"] = out["stable_intent_score"].apply(intent_band)

out["stable_intent_narrative"] = out["insight"].fillna(
    "No stable intent profile available yet for this trainer/jockey/prep-stage combination."
)

out["built_at"] = datetime.now(timezone.utc).isoformat()

cols = [
    "race_date",
    "day_bucket",
    "track",
    "race_no",
    "race_key",
    "horse",
    "horse_key",
    "horse_no",
    "saddlecloth",
    "barrier",
    "trainer",
    "jockey",
    "trainer_canonical",
    "jockey_canonical",
    "trainer_key_resolved",
    "jockey_key_resolved",
    "trainer_jockey_key_v1",
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
    "stable_intent_signal",
    "stable_intent_evidence",
    "stable_intent_score",
    "stable_intent_band",
    "stable_intent_narrative",
    "is_scratched",
    "runner_status",
    "built_at",
]

for c in cols:
    if c not in out.columns:
        out[c] = ""

out = out[cols].sort_values(["race_date", "track", "race_no", "saddlecloth"])
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "LIVE_STABLE_INTENT_FEED_V1_BUILT",
    "rows": len(out),
    "matched_profiles": int((out["stable_intent_signal"] != "NO_PROFILE").sum()),
    "no_profile": int((out["stable_intent_signal"] == "NO_PROFILE").sum()),
    "strong_intent": int((out["stable_intent_band"] == "STRONG_INTENT").sum()),
    "positive_intent": int((out["stable_intent_band"] == "POSITIVE_INTENT").sum()),
    "negative_intent": int((out["stable_intent_band"] == "NEGATIVE_INTENT").sum()),
    "low_evidence": int((out["stable_intent_band"] == "LOW_EVIDENCE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[LIVE_STABLE_INTENT_FEED_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
