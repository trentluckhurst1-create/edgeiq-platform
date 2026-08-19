import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
UNDERSTANDING = DATA / "edgeiq_race_understanding_engine_v2.csv"
STABLE = DATA / "edgeiq_live_stable_intent_feed_v2_1_graphql_resolved.csv"

OUT = DATA / "edgeiq_race_intelligence_terminal_feed_v3_graphql.csv"
SUMMARY = DATA / "edgeiq_race_intelligence_terminal_feed_v3_graphql_summary.csv"

print("[TERMINAL_FEED_V3_GRAPHQL] loading...")
live = pd.read_csv(LIVE, low_memory=False)
under = pd.read_csv(UNDERSTANDING, low_memory=False)
stable = pd.read_csv(STABLE, low_memory=False)

for df in [live, under, stable]:
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
    "prep_stage",
    "trainer_graphql_name","jockey_graphql_name",
    "trainer_prep_signal","trainer_prep_evidence","trainer_prep_starts",
    "combo_prep_signal","combo_prep_evidence","combo_prep_starts",
    "stable_intent_v2_1_graphql_score",
    "stable_intent_v2_1_graphql_band",
    "stable_intent_v2_1_graphql_reason",
]

out = out.merge(
    stable[stable_cols],
    on=["race_date","track","race_no","horse_key"],
    how="left"
)

out["race_setup"] = out["race_setup"].fillna("No race understanding briefing available yet.")
out["customer_summary"] = out["customer_summary"].fillna("No race-level customer summary available yet.")
out["stable_intent_v2_1_graphql_band"] = out["stable_intent_v2_1_graphql_band"].fillna("NO_PROFILE")
out["stable_intent_v2_1_graphql_reason"] = out["stable_intent_v2_1_graphql_reason"].fillna("No GraphQL stable-intent profile available.")

out["edgeiq_terminal_intelligence_line_v3"] = (
    "Race: " + out["customer_summary"].astype(str) +
    " Runner intent: " + out["stable_intent_v2_1_graphql_band"].astype(str) +
    " — " + out["stable_intent_v2_1_graphql_reason"].astype(str)
)

cols = [
    "race_date","day_bucket","track","race_no","race_key","horse","horse_key",
    "saddlecloth","barrier","trainer","jockey","race_time","distance","race_class",
    "track_condition","live_price","fair_price","edge_pct","display_decision",
    "race_setup","key_separators","runners_helped","runners_hurt",
    "intent_watch_runners","intent_caution_runners","customer_summary",
    "prep_stage","trainer_graphql_name","jockey_graphql_name",
    "trainer_prep_signal","trainer_prep_evidence","trainer_prep_starts",
    "combo_prep_signal","combo_prep_evidence","combo_prep_starts",
    "stable_intent_v2_1_graphql_score","stable_intent_v2_1_graphql_band","stable_intent_v2_1_graphql_reason",
    "edgeiq_terminal_intelligence_line_v3",
    "is_scratched","runner_status"
]

for c in cols:
    if c not in out.columns:
        out[c] = ""

out = out[cols].sort_values(["race_date","track","race_no","saddlecloth"])
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RACE_INTELLIGENCE_TERMINAL_FEED_V3_GRAPHQL_BUILT",
    "rows": len(out),
    "rows_with_race_understanding": int((out["customer_summary"] != "No race-level customer summary available yet.").sum()),
    "rows_with_graphql_stable_intent": int((out["stable_intent_v2_1_graphql_band"] != "NO_PROFILE").sum()),
    "positive_intent": int((out["stable_intent_v2_1_graphql_band"] == "POSITIVE_INTENT").sum()),
    "watch": int((out["stable_intent_v2_1_graphql_band"] == "WATCH").sum()),
    "low_evidence": int((out["stable_intent_v2_1_graphql_band"] == "LOW_EVIDENCE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[TERMINAL_FEED_V3_GRAPHQL] COMPLETE")
print(summary.to_string(index=False))
