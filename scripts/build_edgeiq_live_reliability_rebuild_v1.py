import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")

RUNNER = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")
ENV = pd.read_csv(ROOT / "public/data/edgeiq_live_environment_v2_feed.csv")

# ----------------------------
# NORMALISE KEYS (CRITICAL FIX)
# ----------------------------
def norm_track(x):
    return str(x).upper().strip()

def norm_date(x):
    return str(x).split(" ")[0].strip()

RUNNER["track"] = RUNNER["track"].map(norm_track)
ENV["track"] = ENV["track"].map(norm_track)

# ensure required fields exist
if "meeting_date" not in ENV.columns:
    raise SystemExit("ENV missing meeting_date — REL source broken upstream")

ENV["meeting_date"] = ENV["meeting_date"].map(norm_date)

# ----------------------------
# BUILD RACE KEY (IDENTICAL LOGIC)
# ----------------------------
RUNNER["race_key"] = (
    RUNNER["track"].astype(str) + "|" +
    RUNNER["race_no"].astype(str)
)

ENV["race_key"] = (
    ENV["track"].astype(str) + "|" +
    ENV["race_no"].astype(str)
)

# ----------------------------
# REDUCE ENV TO RELIABILITY CORE
# ----------------------------
REL = ENV[[
    "race_key",
    "race_reliability_score_v1",
    "race_reliability_band_v1",
    "race_reliability_reason_v1"
]].copy()

# ----------------------------
# HARD ALIGNMENT FILTER (THIS IS THE FIX)
# ----------------------------
RUNNER_KEYS = set(RUNNER["race_key"])
REL = REL[REL["race_key"].isin(RUNNER_KEYS)]

# ----------------------------
# MERGE
# ----------------------------
merged = RUNNER.merge(
    REL,
    on="race_key",
    how="left"
)

# ----------------------------
# METRICS
# ----------------------------
print("[REL LIVE REBUILD COMPLETE]")
print("RUNNER rows:", len(RUNNER))
print("REL rows:", len(REL))
print("matched:", merged["race_reliability_band_v1"].notna().sum())

# ----------------------------
# WRITE OUTPUT
# ----------------------------
out_path = ROOT / "public/data/edgeiq_unified_live_reliability_v1.csv"
merged.to_csv(out_path, index=False)

print("wrote:", out_path)
