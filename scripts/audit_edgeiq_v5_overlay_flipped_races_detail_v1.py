import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path.cwd()

audit = pd.read_csv(
    ROOT / "public/data/edgeiq_probability_engine_v5_factor_overlay_research_audit_v1.csv",
    low_memory=False
)

race_tops = pd.read_csv(
    ROOT / "public/data/edgeiq_probability_engine_v5_factor_overlay_research_audit_v1_race_tops.csv",
    low_memory=False
)

flip_races = race_tops[
    race_tops["top_changed"] == True
].copy()

rows = []

for _, race in flip_races.iterrows():

    track = race["track"]
    race_no = race["race_no"]

    subset = audit[
        (audit["track"] == track) &
        (audit["race_no"].astype(str) == str(race_no))
    ].copy()

    subset = subset.sort_values(
        "research_probability_v5_num",
        ascending=False
    )

    rows.append(subset)

if rows:
    out = pd.concat(rows, ignore_index=True)
else:
    out = pd.DataFrame()

out.to_csv(
    ROOT / "public/data/edgeiq_v5_overlay_flipped_races_detail.csv",
    index=False
)

summary = pd.DataFrame([
    {
        "status": "V5_OVERLAY_FLIP_AUDIT_COMPLETE",
        "flip_races": len(flip_races),
        "rows": len(out)
    }
])

summary.to_csv(
    ROOT / "public/data/edgeiq_v5_overlay_flipped_races_detail_summary.csv",
    index=False
)

print(summary)
