from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

board_file = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_market_alignment_engine_v1.csv"
SUMMARY = DATA / "edgeiq_market_alignment_engine_v1_summary.csv"
AUDIT = DATA / "edgeiq_market_alignment_engine_v1_audit.csv"
REPORT = DATA / "edgeiq_market_alignment_engine_v1_report.txt"

df = pd.read_csv(board_file, low_memory=False)
df = df.loc[:, ~df.columns.duplicated()].copy()

def pick_col(names):
    lower = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

track_col = pick_col(["track"])
race_col = pick_col(["race_no", "race_number"])
horse_col = pick_col(["horse", "runner", "runner_name", "horse_name"])
fair_col = pick_col(["display_fair_price", "fair_price", "ui_fair_price", "V6_1_RESEARCH_fair_price"])
live_col = pick_col(["live_price", "display_live_price", "market_price", "sportsbet_price", "fixed_win"])
prob_col = pick_col(["V6_1_RESEARCH_probability", "win_pct"])
conf_col = pick_col(["confidence_score", "confidence", "confidence_pct"])

for c in [fair_col, live_col, prob_col, conf_col]:
    if c:
        df[c] = pd.to_numeric(df[c], errors="coerce")

if prob_col:
    med = df[prob_col].median()
    df["_edge_prob_pct"] = df[prob_col] * 100 if pd.notna(med) and med <= 1 else df[prob_col]
else:
    df["_edge_prob_pct"] = np.nan

df["_market_implied_prob"] = np.where(df[live_col] > 0, 100 / df[live_col], np.nan) if live_col else np.nan
df["_price_ratio"] = np.where(
    (df[fair_col] > 0) & (df[live_col] > 0),
    np.minimum(df[fair_col] / df[live_col], df[live_col] / df[fair_col]),
    np.nan
) if fair_col and live_col else np.nan
df["_price_alignment_score"] = (pd.Series(df["_price_ratio"], index=df.index).clip(0, 1) * 100).round(1)

status_col = pick_col(["status", "runner_status", "scratched_status"])
if status_col:
    active_mask = ~df[status_col].astype(str).str.upper().str.contains("SCRATCH", na=False)
else:
    active_mask = pd.Series(True, index=df.index)

has_market = pd.Series(False, index=df.index)
if live_col:
    has_market = pd.to_numeric(df[live_col], errors="coerce").gt(0)

group_cols = [c for c in [track_col, race_col] if c]

df["market_rank"] = np.nan
if group_cols and live_col:
    rank_mask = active_mask & has_market
    df.loc[rank_mask, "market_rank"] = (
        df.loc[rank_mask].groupby(group_cols)[live_col]
        .rank(method="min", ascending=True)
    )

df["edge_rank"] = np.nan
if group_cols:
    if df["_edge_prob_pct"].notna().sum() > 0:
        df.loc[active_mask, "edge_rank"] = (
            df.loc[active_mask].groupby(group_cols)["_edge_prob_pct"]
            .rank(method="min", ascending=False)
        )
    elif fair_col:
        df.loc[active_mask, "edge_rank"] = (
            df.loc[active_mask].groupby(group_cols)[fair_col]
            .rank(method="min", ascending=True)
        )

rank_diff = (df["edge_rank"] - df["market_rank"]).abs()
df["rank_alignment_score"] = (100 - (rank_diff.fillna(9) * 10)).clip(10, 100)

prob_gap = (df["_edge_prob_pct"] - df["_market_implied_prob"]).abs()
df["probability_alignment_score"] = np.select(
    [prob_gap <= 2, prob_gap <= 5, prob_gap <= 10, prob_gap <= 15],
    [100, 85, 65, 40],
    default=15
)

confidence_component = pd.to_numeric(df[conf_col], errors="coerce").fillna(50).clip(0,100) if conf_col else pd.Series(50, index=df.index)

df["market_alignment_score"] = (
    df["rank_alignment_score"].fillna(50) * 0.40 +
    df["_price_alignment_score"].fillna(50) * 0.30 +
    pd.Series(df["probability_alignment_score"], index=df.index).fillna(50) * 0.20 +
    confidence_component * 0.10
).clip(0,100).round(1)

df["market_alignment_band"] = np.select(
    [
        df["market_alignment_score"] >= 85,
        df["market_alignment_score"] >= 65,
        df["market_alignment_score"] >= 45,
        df["market_alignment_score"] >= 25
    ],
    ["STRONG_ALIGNMENT", "MODERATE_ALIGNMENT", "NEUTRAL_ALIGNMENT", "WEAK_ALIGNMENT"],
    default="EXTREME_DISAGREEMENT"
)

df.loc[~has_market, "market_alignment_score"] = np.nan
df.loc[~has_market, "market_alignment_band"] = "NO_MARKET_DATA"

df["market_support_flag"] = has_market & (df["edge_rank"] <= 3) & (df["market_rank"] <= 3)
df["positive_value_signal"] = has_market & (df["edge_rank"] <= 3) & (df["market_rank"] <= 5) & (df[live_col] > df[fair_col])
df["contrarian_signal"] = has_market & (df["edge_rank"] <= 2) & (df["market_rank"] >= 8)
df["longshot_risk_flag"] = has_market & (df[live_col] >= 12) & (df["market_alignment_score"] < 40)

def narrative(row):
    if row["market_alignment_band"] == "NO_MARKET_DATA":
        return "No live market price is currently available for this runner, so market alignment is not assessed."
    if row["market_alignment_band"] == "STRONG_ALIGNMENT":
        return "Historical ability and market pricing are strongly aligned."
    if row["market_alignment_band"] == "MODERATE_ALIGNMENT":
        return "The market broadly agrees with the assessment."
    if row["market_alignment_band"] == "NEUTRAL_ALIGNMENT":
        return "The market and model are neither strongly aligned nor opposed."
    if row["market_alignment_band"] == "WEAK_ALIGNMENT":
        return "EDGEiQ and the market materially disagree."
    return "Historical and market assessments are materially opposed and should be treated as a high-uncertainty profile."

df["market_alignment_summary"] = df.apply(narrative, axis=1)

df.to_csv(OUT, index=False)

pd.DataFrame([{
    "status": "EDGEIQ_MARKET_ALIGNMENT_ENGINE_V1_REBUILT_NO_MARKET_SAFE",
    "rows": len(df),
    "market_rows": int(has_market.sum()),
    "no_market_rows": int((~has_market).sum()),
    "avg_alignment_score_market_only": round(df.loc[has_market, "market_alignment_score"].mean(), 2),
    "strong_alignment": int((df["market_alignment_band"] == "STRONG_ALIGNMENT").sum()),
    "moderate_alignment": int((df["market_alignment_band"] == "MODERATE_ALIGNMENT").sum()),
    "neutral_alignment": int((df["market_alignment_band"] == "NEUTRAL_ALIGNMENT").sum()),
    "weak_alignment": int((df["market_alignment_band"] == "WEAK_ALIGNMENT").sum()),
    "extreme_disagreement": int((df["market_alignment_band"] == "EXTREME_DISAGREEMENT").sum()),
    "no_market_data": int((df["market_alignment_band"] == "NO_MARKET_DATA").sum()),
    "prob_col": prob_col,
    "fair_col": fair_col,
    "live_col": live_col,
    "built_at": datetime.now(timezone.utc).isoformat()
}]).to_csv(SUMMARY, index=False)

pd.DataFrame([{
    "input_file": board_file.name,
    "track_col": track_col,
    "race_col": race_col,
    "horse_col": horse_col,
    "fair_col": fair_col,
    "live_col": live_col,
    "prob_col": prob_col,
    "conf_col": conf_col,
    "market_rank_nonblank": int(df["market_rank"].notna().sum()),
    "edge_rank_nonblank": int(df["edge_rank"].notna().sum()),
    "market_rows": int(has_market.sum()),
    "no_market_rows": int((~has_market).sum())
}]).to_csv(AUDIT, index=False)

REPORT.write_text("EDGEIQ_MARKET_ALIGNMENT_ENGINE_V1_REBUILT_NO_MARKET_SAFE\n", encoding="utf-8")

print("[EDGEIQ_MARKET_ALIGNMENT_ENGINE_V1_REBUILT_NO_MARKET_SAFE] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
