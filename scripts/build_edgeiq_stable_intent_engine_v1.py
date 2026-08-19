import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_INTENT = DATA / "edgeiq_live_stable_intent_feed_v1.csv"
TRAINER_PREP = DATA / "edgeiq_trainer_stage_of_prep_engine_v1.csv"
CONNECTION = DATA / "edgeiq_connection_intelligence_v1.csv"

OUT = DATA / "edgeiq_stable_intent_engine_v1.csv"
SUMMARY = DATA / "edgeiq_stable_intent_engine_v1_summary.csv"

def clean_key(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper().replace(" ", "").replace(".", "").replace("'", "").replace("&", "")

def num(s, default=0):
    return pd.to_numeric(s, errors="coerce").fillna(default)

def trainer_score(signal, starts, win_lift, place_lift):
    if starts < 5:
        return 40
    s = 50
    s += min(max(win_lift, -30), 40) * 0.6
    s += min(max(place_lift, -30), 40) * 0.4
    if "EDGE" in str(signal):
        s += 10
    if "RISK" in str(signal) or "CAUTION" in str(signal):
        s -= 12
    return max(0, min(100, round(s, 1)))

def combo_score(signal, current_score):
    if signal == "COMBO_PREP_EDGE":
        return max(current_score, 88)
    if signal == "MILD_COMBO_PREP_EDGE":
        return max(current_score, 72)
    if signal == "COMBO_PREP_RISK":
        return min(current_score, 28)
    if signal == "NEUTRAL":
        return max(current_score, 50)
    return current_score

def band(score):
    if score >= 85:
        return "STRONG_INTENT"
    if score >= 68:
        return "POSITIVE_INTENT"
    if score >= 52:
        return "WATCH"
    if score <= 32:
        return "NEGATIVE_INTENT"
    return "LOW_EVIDENCE"

def narrative(row):
    parts = []

    if row["trainer_prep_signal"] not in ["", "NO_PROFILE"]:
        parts.append(f"Trainer prep profile: {row['trainer_prep_signal']} at {row['prep_stage']}.")

    if row["stable_intent_signal"] not in ["", "NO_PROFILE"]:
        parts.append(f"Trainer/jockey prep profile: {row['stable_intent_signal']} from {row['starts']} starts.")

    if row["connection_band"] not in ["", "NO_PROFILE"]:
        parts.append(f"Connection profile: {row['connection_band']}.")

    if not parts:
        return "No strong stable intent profile available yet. Treat as low-evidence until deeper history is rebuilt."

    return " ".join(parts)

print("[STABLE_INTENT_ENGINE_V1] loading inputs...")
live = pd.read_csv(LIVE_INTENT, low_memory=False)
trainer = pd.read_csv(TRAINER_PREP, low_memory=False)

if CONNECTION.exists():
    conn = pd.read_csv(CONNECTION, low_memory=False)
else:
    conn = pd.DataFrame()

live["race_date"] = pd.to_datetime(live["race_date"], errors="coerce")
live["trainer_key_join"] = live["trainer_key_resolved"].map(clean_key)
live["prep_stage"] = live["prep_stage"].fillna("").astype(str)

trainer["trainer_key_join"] = trainer["trainer"].map(clean_key)
trainer["prep_stage"] = trainer["prep_stage"].fillna("").astype(str)

trainer_keep = [
    "trainer_key_join",
    "prep_stage",
    "starts",
    "wins",
    "places",
    "win_pct",
    "place_pct",
    "win_lift_pct",
    "place_lift_pct",
    "signal",
    "evidence_band",
    "insight",
]

for c in trainer_keep:
    if c not in trainer.columns:
        trainer[c] = ""

trainer_small = trainer[trainer_keep].rename(columns={
    "starts": "trainer_prep_starts",
    "wins": "trainer_prep_wins",
    "places": "trainer_prep_places",
    "win_pct": "trainer_prep_win_pct",
    "place_pct": "trainer_prep_place_pct",
    "win_lift_pct": "trainer_prep_win_lift_pct",
    "place_lift_pct": "trainer_prep_place_lift_pct",
    "signal": "trainer_prep_signal",
    "evidence_band": "trainer_prep_evidence",
    "insight": "trainer_prep_insight",
})

out = live.merge(
    trainer_small,
    on=["trainer_key_join", "prep_stage"],
    how="left"
)

if not conn.empty:
    conn["race_date"] = pd.to_datetime(conn["race_date"], errors="coerce")
    conn["horse_key_join"] = conn["horse_key"].map(clean_key)
    out["horse_key_join"] = out["horse_key"].map(clean_key)

    conn_keep = [
        "race_date",
        "track",
        "race_no",
        "horse_key_join",
        "connection_score",
        "connection_band",
        "connection_narrative",
        "market_expectation_label",
        "sp_expectation_delta",
    ]

    for c in conn_keep:
        if c not in conn.columns:
            conn[c] = ""

    out = out.merge(
        conn[conn_keep],
        on=["race_date", "track", "race_no", "horse_key_join"],
        how="left"
    )
else:
    out["connection_score"] = ""
    out["connection_band"] = ""
    out["connection_narrative"] = ""
    out["market_expectation_label"] = ""
    out["sp_expectation_delta"] = ""

out["trainer_prep_signal"] = out["trainer_prep_signal"].fillna("NO_PROFILE")
out["trainer_prep_evidence"] = out["trainer_prep_evidence"].fillna("NO_PROFILE")
out["trainer_prep_win_lift_pct"] = num(out["trainer_prep_win_lift_pct"])
out["trainer_prep_place_lift_pct"] = num(out["trainer_prep_place_lift_pct"])
out["trainer_prep_starts"] = num(out["trainer_prep_starts"])

out["stable_intent_signal"] = out["stable_intent_signal"].fillna("NO_PROFILE")
out["stable_intent_score"] = num(out["stable_intent_score"], 40)
out["connection_score"] = num(out["connection_score"], 50)
out["connection_band"] = out["connection_band"].fillna("NO_PROFILE")

out["trainer_prep_score"] = out.apply(
    lambda r: trainer_score(
        r["trainer_prep_signal"],
        r["trainer_prep_starts"],
        r["trainer_prep_win_lift_pct"],
        r["trainer_prep_place_lift_pct"],
    ),
    axis=1
)

out["stable_intent_combined_score"] = (
    (out["trainer_prep_score"] * 0.45) +
    (out["stable_intent_score"] * 0.35) +
    (out["connection_score"] * 0.20)
).round(1)

out["stable_intent_combined_score"] = out.apply(
    lambda r: combo_score(r["stable_intent_signal"], r["stable_intent_combined_score"]),
    axis=1
)

out["stable_intent_combined_band"] = out["stable_intent_combined_score"].apply(band)
out["stable_intent_summary"] = out.apply(narrative, axis=1)
out["built_at"] = datetime.now(timezone.utc).isoformat()

cols = [
    "race_date",
    "day_bucket",
    "track",
    "race_no",
    "race_key",
    "horse",
    "horse_key",
    "saddlecloth",
    "barrier",
    "trainer",
    "jockey",
    "prep_stage",
    "trainer_prep_score",
    "trainer_prep_signal",
    "trainer_prep_evidence",
    "trainer_prep_starts",
    "trainer_prep_win_pct",
    "trainer_prep_place_pct",
    "trainer_prep_win_lift_pct",
    "trainer_prep_place_lift_pct",
    "stable_intent_score",
    "stable_intent_signal",
    "stable_intent_evidence",
    "starts",
    "wins",
    "places",
    "win_pct",
    "place_pct",
    "win_lift_pct",
    "place_lift_pct",
    "connection_score",
    "connection_band",
    "market_expectation_label",
    "sp_expectation_delta",
    "stable_intent_combined_score",
    "stable_intent_combined_band",
    "stable_intent_summary",
    "stable_intent_narrative",
    "connection_narrative",
    "is_scratched",
    "runner_status",
    "built_at",
]

for c in cols:
    if c not in out.columns:
        out[c] = ""

out = out[cols].sort_values(
    ["race_date", "track", "race_no", "stable_intent_combined_score"],
    ascending=[True, True, True, False]
)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "STABLE_INTENT_ENGINE_V1_BUILT",
    "rows": len(out),
    "trainer_prep_profiles": int((out["trainer_prep_signal"] != "NO_PROFILE").sum()),
    "combo_prep_profiles": int((out["stable_intent_signal"] != "NO_PROFILE").sum()),
    "connection_profiles": int((out["connection_band"] != "NO_PROFILE").sum()),
    "strong_intent": int((out["stable_intent_combined_band"] == "STRONG_INTENT").sum()),
    "positive_intent": int((out["stable_intent_combined_band"] == "POSITIVE_INTENT").sum()),
    "watch": int((out["stable_intent_combined_band"] == "WATCH").sum()),
    "negative_intent": int((out["stable_intent_combined_band"] == "NEGATIVE_INTENT").sum()),
    "low_evidence": int((out["stable_intent_combined_band"] == "LOW_EVIDENCE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[STABLE_INTENT_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
