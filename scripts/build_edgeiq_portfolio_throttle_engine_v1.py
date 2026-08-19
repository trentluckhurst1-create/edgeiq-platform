from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()

SRC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_capital_allocation_v1.csv"

OUT = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_portfolio_throttle_v1.csv"

BANKROLL = 10000.0
MAX_PORTFOLIO_HEAT = 0.055
MAX_ROUGHIE_POSITIONS = 28
MAX_ACTIVE_POSITIONS = 65

def num(v):
    try:
        if pd.isna(v):
            return 0.0
        return float(str(v).replace("$","").replace(",","").strip())
    except Exception:
        return 0.0

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

df = pd.read_csv(SRC, low_memory=False)

df["market_price_num"] = pd.to_numeric(df.get("market_price"), errors="coerce")
df["stake_fraction_num"] = pd.to_numeric(df.get("stake_fraction"), errors="coerce").fillna(0)
df["recommended_stake_num"] = pd.to_numeric(df.get("recommended_stake"), errors="coerce").fillna(0)
df["conviction_score_num"] = pd.to_numeric(df.get("execution_conviction_score"), errors="coerce").fillna(0)
df["edge_num"] = pd.to_numeric(df.get("edge_pct"), errors="coerce").fillna(0)

df["throttle_action"] = "KEEP"
df["throttled_stake_fraction"] = df["stake_fraction_num"]
df["throttled_stake"] = df["recommended_stake_num"]
df["throttle_reason"] = "kept"

active = df[df["stake_fraction_num"] > 0].copy()

# Higher priority survives.
active["priority_score"] = (
    active["conviction_score_num"] * 2.0
    + active["edge_num"] * 0.60
    - active["market_price_num"].fillna(999) * 0.35
)

active.loc[
    active["execution_conviction"].astype(str).str.upper().eq("HIGH_CONVICTION"),
    "priority_score"
] += 30

active.loc[
    active["stake_tier"].astype(str).str.upper().isin(["STANDARD", "STRONG", "AGGRESSIVE"]),
    "priority_score"
] += 25

active.loc[
    active["market_price_num"] >= 20,
    "priority_score"
] -= 20

active.loc[
    active["execution_conviction"].astype(str).str.upper().eq("NO_CONVICTION"),
    "priority_score"
] -= 50

active = active.sort_values("priority_score", ascending=False)

kept_idx = []
roughie_count = 0
heat = 0.0

for idx, row in active.iterrows():
    stake_frac = num(row.get("stake_fraction_num"))
    price = num(row.get("market_price_num"))
    is_roughie = price >= 20

    if len(kept_idx) >= MAX_ACTIVE_POSITIONS:
        continue

    if is_roughie and roughie_count >= MAX_ROUGHIE_POSITIONS:
        continue

    if heat + stake_frac > MAX_PORTFOLIO_HEAT:
        continue

    kept_idx.append(idx)
    heat += stake_frac
    if is_roughie:
        roughie_count += 1

active_idx = set(active.index)
kept_idx = set(kept_idx)
cut_idx = active_idx - kept_idx

df.loc[list(cut_idx), "throttle_action"] = "CUT"
df.loc[list(cut_idx), "throttled_stake_fraction"] = 0
df.loc[list(cut_idx), "throttled_stake"] = 0
df.loc[list(cut_idx), "throttle_reason"] = "portfolio throttle: weak / excess exposure"

# Add portfolio metadata
df["portfolio_heat_limit"] = MAX_PORTFOLIO_HEAT
df["max_roughie_positions"] = MAX_ROUGHIE_POSITIONS
df["max_active_positions"] = MAX_ACTIVE_POSITIONS

df.to_csv(OUT, index=False)

summary = {
    "original_active": int((df["stake_fraction_num"] > 0).sum()),
    "throttled_active": int((df["throttled_stake_fraction"] > 0).sum()),
    "original_exposure": round(float(df["recommended_stake_num"].sum()), 2),
    "throttled_exposure": round(float(df["throttled_stake"].sum()), 2),
    "original_heat_pct": round(float(df["recommended_stake_num"].sum()) / BANKROLL * 100, 2),
    "throttled_heat_pct": round(float(df["throttled_stake"].sum()) / BANKROLL * 100, 2),
    "kept_roughies": int(((df["throttled_stake_fraction"] > 0) & (df["market_price_num"] >= 20)).sum()),
    "cut_positions": int((df["throttle_action"] == "CUT").sum()),
}

print("=" * 100)
print("EDGEIQ PORTFOLIO THROTTLE ENGINE V1")
print("=" * 100)

for k, v in summary.items():
    print(f"{k}: {v}")

print()
print("=" * 100)
print("KEPT PORTFOLIO")
print("=" * 100)

cols = [
    "track","race_no","horse","market_price","edge_pct",
    "execution_conviction","execution_conviction_score",
    "stake_tier","recommended_stake","throttled_stake",
    "throttle_action","throttle_reason"
]
cols = [c for c in cols if c in df.columns]

print(
    df[df["throttled_stake"] > 0]
    .sort_values(["throttled_stake","execution_conviction_score"], ascending=False)
    [cols]
    .head(40)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
