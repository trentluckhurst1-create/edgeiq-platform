import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V3 = DATA / "edgeiq_race_intelligence_terminal_feed_v3_graphql.csv"
CTX = DATA / "edgeiq_live_context_signal_feed_v2_graphql.csv"

OUT = DATA / "edgeiq_race_intelligence_terminal_feed_v4_graphql.csv"
SUMMARY = DATA / "edgeiq_race_intelligence_terminal_feed_v4_graphql_summary.csv"

print("[TERMINAL_FEED_V4_GRAPHQL] loading...")
v3 = pd.read_csv(V3, low_memory=False)
ctx = pd.read_csv(CTX, low_memory=False)

for df in [v3, ctx]:
    df["race_date"] = df["race_date"].astype(str).str[:10]
    df["track"] = df["track"].astype(str)
    df["race_no"] = df["race_no"].astype(str)

ctx_cols = [
    "race_date","track","race_no","horse_key",
    "context_signal_count",
    "context_signal_1_entity_type","context_signal_1_context","context_signal_1_signal","context_signal_1_insight",
    "context_signal_2_entity_type","context_signal_2_context","context_signal_2_signal","context_signal_2_insight",
    "context_signal_3_entity_type","context_signal_3_context","context_signal_3_signal","context_signal_3_insight",
]

out = v3.merge(ctx[ctx_cols], on=["race_date","track","race_no","horse_key"], how="left")

out["context_signal_count"] = pd.to_numeric(out["context_signal_count"], errors="coerce").fillna(0).astype(int)

for c in ctx_cols:
    if c not in ["race_date","track","race_no","horse_key","context_signal_count"]:
        out[c] = out[c].fillna("")

def intelligence_line(r):
    parts = []
    parts.append(f"Race: {r.get('customer_summary','')}")
    parts.append(f"Stable intent: {r.get('stable_intent_v2_1_graphql_band','NO_PROFILE')} — {r.get('stable_intent_v2_1_graphql_reason','')}")
    if int(r.get("context_signal_count", 0)) > 0:
        parts.append(f"Context: {r.get('context_signal_1_insight','')}")
    else:
        parts.append("Context: No major GraphQL context signal identified.")
    return " ".join([str(p).strip() for p in parts if str(p).strip()])

out["edgeiq_terminal_intelligence_line_v4"] = out.apply(intelligence_line, axis=1)
out["built_at_v4_graphql"] = datetime.now(timezone.utc).isoformat()

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RACE_INTELLIGENCE_TERMINAL_FEED_V4_GRAPHQL_BUILT",
    "rows": len(out),
    "rows_with_race_understanding": int((out["customer_summary"].fillna("") != "").sum()),
    "rows_with_stable_intent": int((out["stable_intent_v2_1_graphql_band"].fillna("") != "").sum()),
    "rows_with_context_signals": int((out["context_signal_count"] > 0).sum()),
    "positive_intent": int((out["stable_intent_v2_1_graphql_band"] == "POSITIVE_INTENT").sum()),
    "watch": int((out["stable_intent_v2_1_graphql_band"] == "WATCH").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[TERMINAL_FEED_V4_GRAPHQL] COMPLETE")
print(summary.to_string(index=False))
