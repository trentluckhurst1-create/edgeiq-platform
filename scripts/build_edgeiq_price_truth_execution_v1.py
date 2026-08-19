
import pandas as pd
import numpy as np
from pathlib import Path

DASH = Path(__file__).resolve().parents[1]
DATA = DASH / "public" / "data"

SRC = DATA / "edgeiq_live_runner_board_v1.csv"
OUT = DATA / "edgeiq_live_runner_board_v1.csv"
AUDIT = DATA / "edgeiq_price_truth_audit_v1.csv"

print("=" * 100)
print("EDGEIQ PRICE TRUTH + EXECUTION DISCIPLINE V1")
print("=" * 100)
print("DASH:", DASH)
print("SRC :", SRC)
print("OUT :", OUT)

if not SRC.exists():
    raise FileNotFoundError(f"Missing live runner board: {SRC}")

df = pd.read_csv(SRC, low_memory=False)

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan

for c in ["live_price", "fair_price", "edge_pct", "confidence_score"]:
    if c in df.columns:
        df[c] = df[c].apply(num)
    else:
        df[c] = np.nan

def price_truth(row):
    live = row.get("live_price")
    fair = row.get("fair_price")
    conf = row.get("confidence_score")

    reasons = []

    if pd.isna(live):
        return "NO LIVE", "NO_LIVE_PRICE", np.nan, np.nan

    if pd.isna(fair) or fair <= 1:
        return "NO BET", "NO_VALID_FAIR_PRICE", np.nan, np.nan

    if pd.isna(conf):
        conf = 35

    raw_edge = ((live / fair) - 1) * 100
    adjusted_fair = fair

    if live >= 50 and fair <= 20:
        adjusted_fair = max(adjusted_fair, live * 0.55)
        reasons.append("EXTREME_LONGSHOT_FAIR_TOO_SHORT")

    if raw_edge >= 150:
        adjusted_fair = max(adjusted_fair, live * 0.65)
        reasons.append("IMPOSSIBLE_OVERLAY_CAP")

    if conf < 45:
        adjusted_fair = max(adjusted_fair, fair * 1.35)
        reasons.append("LOW_CONFIDENCE_PENALTY")

    adjusted_edge = ((live / adjusted_fair) - 1) * 100

    if adjusted_edge >= 25 and conf >= 60 and live <= 30:
        action = "EXECUTE"
    elif adjusted_edge >= 12 and conf >= 45 and live <= 50:
        action = "WATCH"
    elif adjusted_edge <= -20:
        action = "UNDERLAY"
    else:
        action = "PASS"

    if not reasons:
        reasons.append("OK")

    return action, "|".join(reasons), round(adjusted_fair, 4), round(adjusted_edge, 1)

results = df.apply(price_truth, axis=1, result_type="expand")

df["execution_action"] = results[0]
df["price_truth_reason"] = results[1]
df["adjusted_fair_price"] = results[2]
df["adjusted_edge_pct"] = results[3]

df.to_csv(OUT, index=False)

audit_cols = [
    "track",
    "race_no",
    "horse",
    "live_price",
    "fair_price",
    "adjusted_fair_price",
    "edge_pct",
    "adjusted_edge_pct",
    "confidence_score",
    "execution_action",
    "price_truth_reason",
]

for c in audit_cols:
    if c not in df.columns:
        df[c] = ""

audit = df[df["live_price"].notna()][audit_cols].copy()
audit.to_csv(AUDIT, index=False)

print(audit.to_string(index=False))
print()
print("UPDATED:", OUT)
print("AUDIT  :", AUDIT)
