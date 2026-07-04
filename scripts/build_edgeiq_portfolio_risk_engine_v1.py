from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()

SRC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_capital_allocation_v1.csv"

OUT = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_portfolio_risk_v1.csv"

BANKROLL = 10000.0

def num(v):
    try:
        if pd.isna(v):
            return 0.0
        return float(str(v).replace("$","").replace(",","").strip())
    except:
        return 0.0

df = pd.read_csv(SRC, low_memory=False)

active = df[df["stake_fraction"] > 0].copy()

# =============================================================================
# PORTFOLIO METRICS
# =============================================================================

total_exposure = active["recommended_stake"].sum()
portfolio_heat = total_exposure / BANKROLL

active_positions = len(active)

high_conviction = (
    active["execution_conviction"]
    .astype(str)
    .str.upper()
    .isin(["HIGH_CONVICTION", "ELITE_CONVICTION"])
).sum()

roughies = (pd.to_numeric(active["market_price"], errors="coerce") >= 20).sum()

# =============================================================================
# RACE EXPOSURE
# =============================================================================

race_group = (
    active
    .groupby(["track", "race_no"], dropna=False)
    ["recommended_stake"]
    .sum()
    .reset_index()
)

race_group["race_exposure_pct"] = (
    race_group["recommended_stake"] / BANKROLL
) * 100

# =============================================================================
# TRACK EXPOSURE
# =============================================================================

track_group = (
    active
    .groupby(["track"], dropna=False)
    ["recommended_stake"]
    .sum()
    .reset_index()
)

track_group["track_exposure_pct"] = (
    track_group["recommended_stake"] / BANKROLL
) * 100

# =============================================================================
# PORTFOLIO RISK ASSESSMENT
# =============================================================================

risk_grade = "LOW"

if portfolio_heat >= 0.15:
    risk_grade = "EXTREME"

elif portfolio_heat >= 0.10:
    risk_grade = "HIGH"

elif portfolio_heat >= 0.06:
    risk_grade = "MEDIUM"

cluster_warning = "NONE"

if len(race_group[race_group["race_exposure_pct"] >= 2.5]) >= 3:
    cluster_warning = "RACE_CLUSTERING"

if len(track_group[track_group["track_exposure_pct"] >= 5]) >= 2:
    cluster_warning = "TRACK_CLUSTERING"

if roughies >= 10:
    cluster_warning = "ROUGHIE_OVERLOAD"

# =============================================================================
# SUMMARY TABLE
# =============================================================================

summary = pd.DataFrame([{
    "bankroll": BANKROLL,
    "active_positions": active_positions,
    "total_exposure": round(total_exposure, 2),
    "portfolio_heat_pct": round(portfolio_heat * 100, 2),
    "high_conviction_positions": int(high_conviction),
    "roughie_positions": int(roughies),
    "portfolio_risk_grade": risk_grade,
    "cluster_warning": cluster_warning
}])

summary.to_csv(OUT, index=False)

print("=" * 100)
print("EDGEIQ PORTFOLIO RISK ENGINE V1")
print("=" * 100)

print(summary.to_string(index=False))

print()
print("=" * 100)
print("TOP TRACK EXPOSURE")
print("=" * 100)

print(
    track_group
    .sort_values("recommended_stake", ascending=False)
    .head(10)
    .to_string(index=False)
)

print()
print("=" * 100)
print("TOP RACE EXPOSURE")
print("=" * 100)

print(
    race_group
    .sort_values("recommended_stake", ascending=False)
    .head(15)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
