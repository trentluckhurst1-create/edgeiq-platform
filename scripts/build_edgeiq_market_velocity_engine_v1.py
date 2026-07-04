import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")

TAPE_PATH = ROOT / "public" / "data" / "edgeiq_market_tape.csv"
OUT_PATH = ROOT / "public" / "data" / "edgeiq_market_velocity_v1.csv"

if not TAPE_PATH.exists():
    raise FileNotFoundError(TAPE_PATH)

df = pd.read_csv(TAPE_PATH)

required = ["snapshot_time", "track", "race_no", "horse", "live_price"]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

df["snapshot_time"] = pd.to_datetime(df["snapshot_time"], errors="coerce")

df["live_price"] = pd.to_numeric(df["live_price"], errors="coerce")

df = df.dropna(subset=["snapshot_time", "live_price"])

df = df.sort_values(
    ["track", "race_no", "horse", "snapshot_time"]
).reset_index(drop=True)

group_cols = ["track", "race_no", "horse"]

df["prev_price"] = df.groupby(group_cols)["live_price"].shift(1)

df["prev_time"] = df.groupby(group_cols)["snapshot_time"].shift(1)

df["price_delta"] = df["live_price"] - df["prev_price"]

df["pct_move"] = (
    (df["live_price"] - df["prev_price"])
    / df["prev_price"]
) * 100

df["seconds_since_update"] = (
    df["snapshot_time"] - df["prev_time"]
).dt.total_seconds()

def classify_move(x):
    if pd.isna(x):
        return "NEW"

    if x <= -15:
        return "HEAVY_FIRM"

    if x < -5:
        return "FIRM"

    if x >= 15:
        return "HEAVY_DRIFT"

    if x > 5:
        return "DRIFT"

    return "STABLE"

df["velocity_state"] = df["pct_move"].apply(classify_move)

df["movement_score"] = (
    df["pct_move"].abs().fillna(0)
)

df["pressure_rating"] = pd.cut(
    df["movement_score"],
    bins=[-1, 2, 5, 10, 1000],
    labels=[
        "LOW",
        "MODERATE",
        "HIGH",
        "EXTREME"
    ]
)

cols = [
    "snapshot_time",
    "track",
    "race_no",
    "horse",
    "live_price",
    "prev_price",
    "price_delta",
    "pct_move",
    "seconds_since_update",
    "velocity_state",
    "pressure_rating"
]

out = df[cols].copy()

out.to_csv(OUT_PATH, index=False)

print("=" * 80)
print("EDGEIQ MARKET VELOCITY ENGINE V1")
print("=" * 80)
print(f"rows: {len(out)}")
print(f"output: {OUT_PATH}")
print("=" * 80)

print(
    out.tail(25).to_string(index=False)
)
