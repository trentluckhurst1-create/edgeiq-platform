from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"
ALIGN = DATA / "edgeiq_market_alignment_engine_v1.csv"

OUT = DATA / "edgeiq_dynamic_confidence_engine_v1.csv"
SUMMARY = DATA / "edgeiq_dynamic_confidence_engine_v1_summary.csv"
AUDIT = DATA / "edgeiq_dynamic_confidence_engine_v1_audit.csv"
REPORT = DATA / "edgeiq_dynamic_confidence_engine_v1_report.txt"

df = pd.read_csv(BOARD, low_memory=False)
df = df.loc[:, ~df.columns.duplicated()].copy()

if ALIGN.exists():
    align = pd.read_csv(ALIGN, low_memory=False)
    align = align.loc[:, ~align.columns.duplicated()].copy()
    join_cols = [c for c in ["track","race_no","horse"] if c in df.columns and c in align.columns]
    keep = join_cols + [c for c in ["market_alignment_score","market_alignment_band"] if c in align.columns]
    if join_cols and len(keep) > len(join_cols):
        df = df.merge(align[keep], on=join_cols, how="left", suffixes=("","_align"))

def n(col):
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[col], errors="coerce")

def band_score(series, mapping, default=50):
    return series.astype(str).str.upper().map(mapping).fillna(default)

projection_band = df["projection_band_V6_1_RESEARCH"] if "projection_band_V6_1_RESEARCH" in df.columns else pd.Series("", index=df.index)
price_status = df["V6_1_RESEARCH_price_status"] if "V6_1_RESEARCH_price_status" in df.columns else pd.Series("", index=df.index)

projection_score = band_score(
    projection_band,
    {
        "ELITE": 92,
        "STRONG": 84,
        "POSITIVE": 74,
        "NEUTRAL": 62,
        "NEGATIVE": 45,
        "POOR": 28,
        "NO_PROJECTION": 12
    },
    default=40
)

price_status_score = band_score(
    price_status,
    {
        "RESEARCH_RATED": 88,
        "NO_PRICE_LOW_COVERAGE": 25,
        "NO_PRICE": 10,
        "NO_PROJECTION_FALLBACK": 15
    },
    default=35
)

gap = n("projection_gap_V6_1_RESEARCH")
gap_strength_score = np.select(
    [
        gap >= 10,
        gap >= 6,
        gap >= 2,
        gap >= -2,
        gap >= -6,
        gap.notna()
    ],
    [92, 84, 74, 62, 45, 28],
    default=12
)

prob = n("V6_1_RESEARCH_probability")
prob_pct = np.where(prob <= 1, prob * 100, prob)
prob_score = np.select(
    [
        pd.Series(prob_pct).ge(12),
        pd.Series(prob_pct).ge(9),
        pd.Series(prob_pct).ge(6),
        pd.Series(prob_pct).ge(3),
        pd.Series(prob_pct).gt(0)
    ],
    [88, 78, 66, 48, 32],
    default=10
)

data_coverage_score = np.select(
    [
        projection_band.astype(str).str.upper().ne("NO_PROJECTION") & price_status.astype(str).str.upper().eq("RESEARCH_RATED"),
        projection_band.astype(str).str.upper().ne("NO_PROJECTION"),
        price_status.astype(str).str.upper().eq("RESEARCH_RATED")
    ],
    [90, 65, 55],
    default=15
)

market_band = df["market_alignment_band"] if "market_alignment_band" in df.columns else pd.Series("NO_MARKET_DATA", index=df.index)
market_score = pd.to_numeric(df["market_alignment_score"], errors="coerce") if "market_alignment_score" in df.columns else pd.Series(np.nan, index=df.index)
market_component = np.where(
    market_band.astype(str).str.upper().eq("NO_MARKET_DATA"),
    50,
    market_score.fillna(50)
)

pace_cols = [c for c in ["early_speed_rating","edgeiq_score_pace_v3","race_pressure_score_v3"] if c in df.columns]
if pace_cols:
    pace_vals = pd.concat([n(c) for c in pace_cols], axis=1)
    pace_score = pace_vals.mean(axis=1).fillna(50).clip(0,100)
else:
    pace_score = pd.Series(50, index=df.index)

connection_cols = [c for c in ["edgeiq_score_connections_v3","connection_score","trainer_score","jockey_score"] if c in df.columns]
if connection_cols:
    connection_vals = pd.concat([n(c) for c in connection_cols], axis=1)
    connection_score = connection_vals.mean(axis=1).fillna(50).clip(0,100)
else:
    connection_score = pd.Series(50, index=df.index)

df["dynamic_confidence_score"] = (
    pd.Series(projection_score, index=df.index) * 0.22 +
    pd.Series(price_status_score, index=df.index) * 0.20 +
    pd.Series(gap_strength_score, index=df.index) * 0.18 +
    pd.Series(prob_score, index=df.index) * 0.12 +
    pd.Series(data_coverage_score, index=df.index) * 0.15 +
    pd.Series(market_component, index=df.index) * 0.05 +
    pd.Series(pace_score, index=df.index) * 0.04 +
    pd.Series(connection_score, index=df.index) * 0.04
).clip(0,100).round(1)

df["dynamic_confidence_band"] = np.select(
    [
        df["dynamic_confidence_score"] >= 85,
        df["dynamic_confidence_score"] >= 70,
        df["dynamic_confidence_score"] >= 55,
        df["dynamic_confidence_score"] >= 40,
    ],
    [
        "VERY_HIGH_CONFIDENCE",
        "HIGH_CONFIDENCE",
        "MODERATE_CONFIDENCE",
        "LOW_CONFIDENCE"
    ],
    default="VERY_LOW_CONFIDENCE"
)

df["confidence_market_status"] = np.where(
    market_band.astype(str).str.upper().eq("NO_MARKET_DATA"),
    "MARKET_NOT_AVAILABLE",
    "MARKET_AVAILABLE"
)

df["confidence_primary_driver"] = np.select(
    [
        projection_band.astype(str).str.upper().isin(["ELITE","STRONG"]),
        price_status.astype(str).str.upper().eq("RESEARCH_RATED"),
        projection_band.astype(str).str.upper().eq("NO_PROJECTION"),
        price_status.astype(str).str.upper().isin(["NO_PRICE","NO_PRICE_LOW_COVERAGE"])
    ],
    [
        "Strong projection profile",
        "Research-rated price available",
        "Projection unavailable",
        "Price coverage limited"
    ],
    default="Mixed evidence profile"
)

df["confidence_summary"] = (
    "Ability confidence: " + df["dynamic_confidence_band"].astype(str) +
    " | Projection: " + projection_band.astype(str) +
    " | Price status: " + price_status.astype(str) +
    " | Market: " + df["confidence_market_status"].astype(str)
)

df.to_csv(OUT, index=False)

pd.DataFrame([{
    "status": "EDGEIQ_DYNAMIC_CONFIDENCE_ENGINE_V1_BUILT",
    "rows": len(df),
    "avg_confidence_score": round(df["dynamic_confidence_score"].mean(), 2),
    "very_high": int((df["dynamic_confidence_band"] == "VERY_HIGH_CONFIDENCE").sum()),
    "high": int((df["dynamic_confidence_band"] == "HIGH_CONFIDENCE").sum()),
    "moderate": int((df["dynamic_confidence_band"] == "MODERATE_CONFIDENCE").sum()),
    "low": int((df["dynamic_confidence_band"] == "LOW_CONFIDENCE").sum()),
    "very_low": int((df["dynamic_confidence_band"] == "VERY_LOW_CONFIDENCE").sum()),
    "market_not_available": int((df["confidence_market_status"] == "MARKET_NOT_AVAILABLE").sum()),
    "production_changed": "NO",
    "pricing_changed": "NO",
    "ui_changed": "NO",
    "built_at": datetime.now(timezone.utc).isoformat()
}]).to_csv(SUMMARY, index=False)

pd.DataFrame([{
    "input_board": BOARD.name,
    "market_alignment_file_exists": ALIGN.exists(),
    "rows": len(df),
    "projection_non_no_projection": int(projection_band.astype(str).str.upper().ne("NO_PROJECTION").sum()),
    "research_rated_rows": int(price_status.astype(str).str.upper().eq("RESEARCH_RATED").sum()),
    "market_alignment_rows": int(market_band.astype(str).str.upper().ne("NO_MARKET_DATA").sum())
}]).to_csv(AUDIT, index=False)

REPORT.write_text(
    "EDGEIQ_DYNAMIC_CONFIDENCE_ENGINE_V1 BUILT\n"
    "Production changed: NO\n"
    "Pricing changed: NO\n"
    "UI changed: NO\n",
    encoding="utf-8"
)

print("[EDGEIQ_DYNAMIC_CONFIDENCE_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(f"report={REPORT}")
