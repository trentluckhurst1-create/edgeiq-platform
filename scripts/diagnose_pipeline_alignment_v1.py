import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")

runner = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")
rel = pd.read_csv(ROOT / "public/data/edgeiq_unified_live_reliability_v2.csv")

print("RUNNER races:", runner["race_no"].nunique())
print("REL races:", rel["race_no"].nunique())

# race coverage check
print("\nRUNNER keys:")
print(runner.groupby(["track","race_no"]).size().head(10))

print("\nREL keys:")
print(rel.groupby(["track","race_no"]).size().head(10))

# key mismatch detection
runner_keys = set(zip(runner["track"], runner["race_no"]))
rel_keys = set(zip(rel["track"], rel["race_no"]))

print("\nMissing REL races:", len(runner_keys - rel_keys))
print("Extra REL races:", len(rel_keys - runner_keys))
