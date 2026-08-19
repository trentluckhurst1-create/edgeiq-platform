import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_context_warehouse_v2_graphql.csv"
OUT = DATA / "edgeiq_context_warehouse_v2_graphql_signal_view.csv"
SUMMARY = DATA / "edgeiq_context_warehouse_v2_graphql_signal_view_summary.csv"

print("[CONTEXT_SIGNAL_VIEW_V2_GRAPHQL] loading...")
df = pd.read_csv(INP, low_memory=False)

out = df[
    (df["signal"].isin(["STRONG_POSITIVE","POSITIVE","NEGATIVE"])) &
    (pd.to_numeric(df["starts"], errors="coerce") >= 20)
].copy()

out["importance_score"] = (
    pd.to_numeric(out["starts"], errors="coerce").fillna(0).clip(upper=200) * 0.05 +
    pd.to_numeric(out["win_lift_pct"], errors="coerce").fillna(0).abs() +
    pd.to_numeric(out["place_lift_pct"], errors="coerce").fillna(0).abs()
).round(4)

out = out.sort_values(
    ["signal","importance_score","starts"],
    ascending=[True,False,False]
)

out["built_at_signal_view"] = datetime.now(timezone.utc).isoformat()
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "CONTEXT_WAREHOUSE_V2_GRAPHQL_SIGNAL_VIEW_BUILT",
    "rows": len(out),
    "strong_positive": int((out["signal"] == "STRONG_POSITIVE").sum()),
    "positive": int((out["signal"] == "POSITIVE").sum()),
    "negative": int((out["signal"] == "NEGATIVE").sum()),
    "horse_rows": int((out["entity_type"] == "HORSE").sum()),
    "trainer_rows": int((out["entity_type"] == "TRAINER").sum()),
    "jockey_rows": int((out["entity_type"] == "JOCKEY").sum()),
    "connection_rows": int((out["entity_type"] == "CONNECTION").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[CONTEXT_SIGNAL_VIEW_V2_GRAPHQL] COMPLETE")
print(summary.to_string(index=False))
