from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()

SRC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_execution_quality_v2.csv"

OUT = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_capital_allocation_v1.csv"

BANKROLL = 10000.0

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(str(v).replace("$","").replace(",","").strip())
    except:
        return np.nan

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def allocate(row):

    edge = num(row.get("edge_pct"))
    odds = num(row.get("market_price"))
    conviction = safe(row.get("execution_conviction")).upper()
    risk = safe(row.get("execution_risk")).upper()
    quality = safe(row.get("execution_quality")).upper()

    if pd.isna(edge) or pd.isna(odds) or odds <= 1:
        return (
            "NO_BET",
            0,
            0,
            0,
            "NO_MARKET",
            0,
            "No valid market"
        )

    implied = 1.0 / odds
    estimated = implied * (1.0 + (edge / 100.0))

    estimated = max(0.001, min(0.95, estimated))

    b = odds - 1.0
    p = estimated
    q = 1.0 - p

    kelly_raw = ((b * p) - q) / b

    kelly_raw = max(-1.0, min(1.0, kelly_raw))

    # =============================================================================
    # FRACTIONAL / CAPPED KELLY
    # =============================================================================

    fraction = 0.10

    if conviction == "HIGH_CONVICTION":
        fraction = 0.20

    elif conviction == "ELITE_CONVICTION":
        fraction = 0.33

    elif conviction == "LOW_CONVICTION":
        fraction = 0.05

    elif conviction == "NO_CONVICTION":
        fraction = 0.01

    if risk == "HIGH":
        fraction *= 0.50

    elif risk == "EXTREME":
        fraction *= 0.20

    kelly_capped = kelly_raw * fraction

    # =============================================================================
    # HARD RISK CAPS
    # =============================================================================

    max_cap = 0.015

    if conviction == "ELITE_CONVICTION":
        max_cap = 0.04

    elif conviction == "HIGH_CONVICTION":
        max_cap = 0.025

    elif conviction == "LOW_CONVICTION":
        max_cap = 0.0075

    elif conviction == "NO_CONVICTION":
        max_cap = 0.0025

    if odds >= 50:
        max_cap *= 0.35

    elif odds >= 25:
        max_cap *= 0.50

    elif odds >= 15:
        max_cap *= 0.70

    stake_fraction = max(
        0,
        min(max_cap, kelly_capped)
    )

    stake_amount = BANKROLL * stake_fraction

    # =============================================================================
    # STAKE TIERS
    # =============================================================================

    tier = "NO_BET"

    if stake_fraction >= 0.025:
        tier = "AGGRESSIVE"

    elif stake_fraction >= 0.012:
        tier = "STRONG"

    elif stake_fraction >= 0.006:
        tier = "STANDARD"

    elif stake_fraction >= 0.002:
        tier = "SMALL"

    elif stake_fraction > 0:
        tier = "TOKEN"

    capital_risk = "LOW"

    if odds >= 40:
        capital_risk = "EXTREME"

    elif odds >= 20:
        capital_risk = "HIGH"

    elif odds >= 10:
        capital_risk = "MEDIUM"

    commentary = (
        f"{tier} | "
        f"conviction={conviction} | "
        f"edge={edge:.1f}% | "
        f"kelly={kelly_raw:.4f} | "
        f"fraction={stake_fraction:.4f} | "
        f"stake=${stake_amount:.2f}"
    )

    return (
        tier,
        round(kelly_raw, 5),
        round(kelly_capped, 5),
        round(stake_fraction, 5),
        capital_risk,
        round(stake_amount, 2),
        commentary
    )

df = pd.read_csv(SRC, low_memory=False)

tiers = []
kelly_raws = []
kelly_caps = []
fractions = []
risks = []
stakes = []
comments = []

for _, row in df.iterrows():

    t, kr, kc, sf, r, sa, c = allocate(row)

    tiers.append(t)
    kelly_raws.append(kr)
    kelly_caps.append(kc)
    fractions.append(sf)
    risks.append(r)
    stakes.append(sa)
    comments.append(c)

df["stake_tier"] = tiers
df["kelly_fraction_raw"] = kelly_raws
df["kelly_fraction_capped"] = kelly_caps
df["stake_fraction"] = fractions
df["capital_risk_grade"] = risks
df["recommended_stake"] = stakes
df["allocation_commentary"] = comments

df.to_csv(OUT, index=False)

print("=" * 100)
print("EDGEIQ CAPITAL ALLOCATION ENGINE V1")
print("=" * 100)

print(df["stake_tier"].value_counts().to_string())

print()
print("=" * 100)
print("TOP CAPITAL DEPLOYMENTS")
print("=" * 100)

top = (
    df[
        df["stake_fraction"] > 0
    ]
    .sort_values(
        ["stake_fraction", "execution_conviction_score"],
        ascending=False
    )
)

cols = [
    "track",
    "race_no",
    "horse",
    "market_price",
    "edge_pct",
    "execution_conviction",
    "execution_conviction_score",
    "stake_tier",
    "stake_fraction",
    "recommended_stake",
    "allocation_commentary"
]

cols = [c for c in cols if c in top.columns]

print(
    top[cols]
    .head(30)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
