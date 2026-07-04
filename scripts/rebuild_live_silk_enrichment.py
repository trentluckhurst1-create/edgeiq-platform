import pandas as pd
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")

LIVE_PATH = ROOT / "public/data/edgeiq_vic_live_terminal_feed_v1.csv"
SILKS_PATH = ROOT / "public/data/horse_silks.csv"
SCRATCH_PATH = ROOT / "public/data/scratchings.csv"

live = pd.read_csv(LIVE_PATH)
silks = pd.read_csv(SILKS_PATH)

def norm(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^A-Z0-9]", "", x)
    return x.strip()

live["horse_key_norm"] = live["horse"].apply(norm)
silks["horse_key_norm"] = silks["horse"].apply(norm)

silks = silks.drop_duplicates("horse_key_norm")

merge_cols = [
    "horse_key_norm",
    "silk_url",
    "local_silk_path"
]

live = live.drop(
    columns=[
        c for c in [
            "silk_url",
            "local_silk_path",
            "silkUrl"
        ]
        if c in live.columns
    ],
    errors="ignore"
)

live = live.merge(
    silks[merge_cols],
    on="horse_key_norm",
    how="left"
)

live["silkUrl"] = live["local_silk_path"]

if Path(SCRATCH_PATH).exists():
    scratches = pd.read_csv(SCRATCH_PATH)

    scratch_cols = [c.lower() for c in scratches.columns]

    horse_col = None

    for c in scratches.columns:
        if "horse" in c.lower():
            horse_col = c
            break

    if horse_col:
        scratches["horse_key_norm"] = scratches[horse_col].apply(norm)

        scratch_set = set(scratches["horse_key_norm"])

        live["is_scratched"] = live["horse_key_norm"].isin(scratch_set)
        live["runner_status"] = live["is_scratched"].map(
            lambda x: "SCRATCHED" if x else "ACTIVE"
        )

live.drop(columns=["horse_key_norm"], inplace=True)

live.to_csv(LIVE_PATH, index=False)

print("=" * 80)
print("EDGEIQ LIVE SILK ENRICHMENT COMPLETE")
print("=" * 80)

print("LIVE ROWS:", len(live))
print(
    "SILKS MATCHED:",
    live["local_silk_path"].notna().sum()
)

print(
    "SCRATCHED:",
    (live["runner_status"] == "SCRATCHED").sum()
)

print("=" * 80)
