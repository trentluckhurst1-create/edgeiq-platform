import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")

LIVE_BOARD = ROOT / "public" / "data" / "edgeiq_bookmaker_board_v1.csv"
OUT_DIR = ROOT / "public" / "data"

TAPE_PATH = OUT_DIR / "edgeiq_market_tape.csv"
SNAPSHOT_DIR = OUT_DIR / "market_snapshots"

SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

if not LIVE_BOARD.exists():
    raise FileNotFoundError(LIVE_BOARD)

df = pd.read_csv(LIVE_BOARD)

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
snapshot_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

df["snapshot_time"] = timestamp

snapshot_file = SNAPSHOT_DIR / f"market_snapshot_{snapshot_stamp}.csv"

df.to_csv(snapshot_file, index=False)

if TAPE_PATH.exists():
    tape = pd.read_csv(TAPE_PATH)

    combined = pd.concat([tape, df], ignore_index=True)

    combined = combined.drop_duplicates(
        subset=["snapshot_time", "track", "race_no", "horse"],
        keep="last"
    )
else:
    combined = df.copy()

combined.to_csv(TAPE_PATH, index=False)

print("=" * 80)
print("EDGEIQ MARKET TAPE ENGINE V1")
print("=" * 80)
print(f"snapshot rows: {len(df)}")
print(f"tape rows: {len(combined)}")
print(f"snapshot file: {snapshot_file}")
print(f"tape file: {TAPE_PATH}")
print("=" * 80)

preview_cols = [
    c for c in [
        "snapshot_time",
        "track",
        "race_no",
        "horse",
        "live_price",
        "open_price",
        "move_direction"
    ]
    if c in combined.columns
]

print(combined[preview_cols].tail(15).to_string(index=False))
