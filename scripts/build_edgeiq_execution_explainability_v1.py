from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_board_v1.csv"
OUT = DATA / "edgeiq_execution_board_v2.csv"


import pandas as pd
import numpy as np
from pathlib import Path



print("=" * 100)
print("EDGEIQ EXECUTION EXPLAINABILITY ENGINE V1")
print("=" * 100)
print("SRC:", SRC)

df = pd.read_csv(SRC, low_memory=False)

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan

for c in ["adjusted_edge_pct", "confidence_score", "projected_spd"]:
    if c in df.columns:
        df[c] = df[c].apply(num)

df["execution_explanation"] = (
    "EDGE "
    + df["adjusted_edge_pct"].astype(str)
    + " | CONF "
    + df["confidence_score"].astype(str)
)

df["priority_score"] = (
    df["adjusted_edge_pct"].fillna(0)
    + df["confidence_score"].fillna(0) * 0.35
)

df = df.sort_values("priority_score", ascending=False)

df.to_csv(OUT, index=False)

print(df[[
    "track",
    "race_no",
    "horse",
    "execution_action",
    "priority_score",
    "execution_explanation"
]].head(20).to_string(index=False))

print()
print("OUTPUT:", OUT)