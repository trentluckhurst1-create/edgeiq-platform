from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_pricing_replay_spine_v3_1_reconstructed.csv"

OUT = DATA / "edgeiq_pricing_replay_spine_v3_1_sanity_audit.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_spine_v3_1_sanity_summary.csv"

print("[PRICING_REPLAY_SPINE_V3_1_SANITY_AUDIT_FIXED] START")

df = pd.read_csv(SRC, low_memory=False)

df["_prob"] = pd.to_numeric(df["reconstructed_replay_probability_v3_1"], errors="coerce")
df["_price"] = pd.to_numeric(df["reconstructed_replay_fair_price_v3_1"], errors="coerce")

if "_replay_join_key_v3_1" in df.columns:
    df["_race_group"] = df["_replay_join_key_v3_1"].astype(str).str.split("|").str[0:3].str.join("|")
else:
    date_col = next((c for c in df.columns if c.lower() in ["race_date", "meeting_date", "date"]), None)
    track_col = next((c for c in df.columns if c.lower() in ["track", "venue"]), None)
    race_col = next((c for c in df.columns if c.lower() in ["race_no", "race_number", "race"]), None)
    if not all([date_col, track_col, race_col]):
        raise RuntimeError("No race grouping fields found")
    df["_race_group"] = (
        pd.to_datetime(df[date_col], errors="coerce").dt.date.astype("string").fillna("") + "|" +
        df[track_col].astype(str).str.upper().str.strip() + "|" +
        pd.to_numeric(df[race_col], errors="coerce").astype("Int64").astype("string").fillna("")
    )

winner_col = next((c for c in df.columns if c.lower() in ["won", "winner", "is_winner", "finish_winner"]), None)

if winner_col:
    df["_won"] = pd.to_numeric(df[winner_col], errors="coerce").fillna(0)
else:
    df["_won"] = 0

race_sum = (
    df.groupby("_race_group")
    .agg(
        runners=("_prob", "count"),
        prob_sum=("_prob", "sum"),
        min_prob=("_prob", "min"),
        max_prob=("_prob", "max"),
        min_price=("_price", "min"),
        max_price=("_price", "max"),
        winners=("_won", "sum")
    )
    .reset_index()
)

race_sum["prob_sum_ok"] = race_sum["prob_sum"].between(0.995, 1.005)

df["prob_bucket"] = pd.cut(
    df["_prob"],
    bins=[0, .02, .05, .08, .12, .18, .25, .35, 1],
    labels=["0-2%", "2-5%", "5-8%", "8-12%", "12-18%", "18-25%", "25-35%", "35%+"],
    include_lowest=True
)

bucket_audit = (
    df.groupby("prob_bucket", observed=False)
    .agg(
        rows=("_prob", "count"),
        avg_prob=("_prob", "mean"),
        winners=("_won", "sum"),
        actual_win_rate=("_won", "mean"),
        avg_price=("_price", "mean")
    )
    .reset_index()
)

bucket_audit.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(df),
    "races": df["_race_group"].nunique(),
    "prob_rows": int(df["_prob"].notna().sum()),
    "prob_coverage_pct": round(float(df["_prob"].notna().mean() * 100), 2),
    "races_prob_sum_ok": int(race_sum["prob_sum_ok"].sum()),
    "races_prob_sum_bad": int((~race_sum["prob_sum_ok"]).sum()),
    "min_probability": float(df["_prob"].min()),
    "max_probability": float(df["_prob"].max()),
    "min_fair_price": float(df["_price"].min()),
    "max_fair_price": float(df["_price"].max()),
    "winner_col": winner_col or "",
    "winners_found": int(df["_won"].sum()),
    "status": "SANITY_AUDIT_FIXED_COMPLETE_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[PRICING_REPLAY_SPINE_V3_1_SANITY_AUDIT_FIXED] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
print("")
print(bucket_audit.to_string(index=False))
