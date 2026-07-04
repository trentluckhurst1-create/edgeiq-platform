import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")

RUNNER = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")

# CREATE LIVE REL FROM RUNNER CONTEXT (NOT HISTORICAL FILE)

REL_LIVE = RUNNER.groupby(["track","race_no"]).agg({
    "horse": "count"
}).reset_index()

REL_LIVE["race_reliability_score_v1"] = 50
REL_LIVE["race_reliability_band_v1"] = "LIVE_PROXY"
REL_LIVE["race_reliability_reason_v1"] = "LIVE_RUNNER_DERIVED"

merged = RUNNER.merge(
    REL_LIVE,
    on=["track","race_no"],
    how="left"
)

out = ROOT / "public/data/edgeiq_unified_live_reliability_v2.csv"
merged.to_csv(out, index=False)

print("[LIVE REL FIXED]")
print("rows:", len(merged))
print("races:", merged["race_no"].nunique())
print("wrote:", out)
