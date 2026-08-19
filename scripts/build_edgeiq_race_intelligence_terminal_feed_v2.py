import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
UNDERSTANDING = DATA / "edgeiq_race_understanding_engine_v2.csv"
BRIEF = DATA / "edgeiq_race_briefing_engine_v2.csv"
STABLE = DATA / "edgeiq_stable_intent_engine_v1_1_rebalance.csv"

OUT = DATA / "edgeiq_race_intelligence_terminal_feed_v2.csv"
SUMMARY = DATA / "edgeiq_race_intelligence_terminal_feed_v2_summary.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

print("[RACE_INTELLIGENCE_TERMINAL_FEED_V2] loading inputs...")
live = pd.read_csv(LIVE, low_memory=False)
under = pd.read_csv(UNDERSTANDING, low_memory=False)
brief = pd.read_csv(BRIEF, low_memory=False)
stable = pd.read_csv(STABLE, low_memory=False)

for df in [live, under, brief, stable]:
    df["race_date"] = df["race_date"].astype(str).str[:10]
    df["track"] = df["track"].astype(str)
    df["race_no"] = df["race_no"].astype(str)

race_cols = [
    "race_date","track","race_no",
    "race_setup","key_separators","runners_helped","runners_hurt",
    "intent_watch_runners","intent_caution_runners","customer_summary"
]

out = live.merge(
    under[race_cols],
    on=["race_date","track","race_no"],
    how="left"
)

stable_cols = [
    "race_date","track","race_no","horse_key",
    "prep_stage","trainer_prep_signal","connection_band",
    "stable_intent_v1_1_score","stable_intent_v1_1_band","stable_intent_v1_1_reason"
]

out = out.merge(
    stable[stable_cols],
    on=["race_date","track","race_no","horse_key"],
    how="left"
)

out["race_setup"] = out["race_setup"].fillna("No race understanding briefing available yet.")
out["customer_summary"] = out["customer_summary"].fillna("No race-level customer summary available yet.")
out["stable_intent_v1_1_band"] = out["stable_intent_v1_1_band"].fillna("NO_PROFILE")
out["stable_intent_v1_1_reason"] = out["stable_intent_v1_1_reason"].fillna("No stable-intent profile available.")

out["edgeiq_terminal_intelligence_line"] = (
    "Race: " + out["customer_summary"].astype(str) +
    " Runner intent: " + out["stable_intent_v1_1_band"].astype(str) +
    " — " + out["stable_intent_v1_1_reason"].astype(str)
)

cols = [
    "race_date","day_bucket","track","race_no","race_key","horse","horse_key",
    "saddlecloth","barrier","trainer","jockey","race_time","distance","race_class",
    "track_condition","live_price","fair_price","edge_pct","display_decision",
    "race_setup","key_separators","runners_helped","runners_hurt",
    "intent_watch_runners","intent_caution_runners","customer_summary",
    "prep_stage","trainer_prep_signal","connection_band",
    "stable_intent_v1_1_score","stable_intent_v1_1_band","stable_intent_v1_1_reason",
    "edgeiq_terminal_intelligence_line",
    "is_scratched","runner_status"
]

for c in cols:
    if c not in out.columns:
        out[c] = ""

out = out[cols].sort_values(["race_date","track","race_no","saddlecloth"])
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RACE_INTELLIGENCE_TERMINAL_FEED_V2_BUILT",
    "rows": len(out),
    "rows_with_race_understanding": int((out["customer_summary"] != "No race-level customer summary available yet.").sum()),
    "rows_with_stable_intent": int((out["stable_intent_v1_1_band"] != "NO_PROFILE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[RACE_INTELLIGENCE_TERMINAL_FEED_V2] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
