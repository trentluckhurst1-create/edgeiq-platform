import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

full = pd.read_csv(ROOT / "public/data/tab_full_field_v2.csv")
runner = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")

# NORMALISE KEYS
full["horse_key"] = full["horse"].astype(str).str.upper().str.strip()
runner["horse_key"] = runner["horse"].astype(str).str.upper().str.strip()

merged = runner.merge(
    full,
    on=["track","race_no","horse_key"],
    how="left"
)

out = ROOT / "public/data/edgeiq_live_runner_board_v2.csv"
merged.to_csv(out, index=False)

print("[MERGE FIXED - HORSE KEY]")
print("rows:", len(merged))
print("matched TAB fields:", merged["tab_fixed_win"].notna().sum())
