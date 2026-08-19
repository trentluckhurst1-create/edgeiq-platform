import pandas as pd
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
SCRATCHES = DATA / "scratchings.csv"

def norm(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^A-Z0-9]", "", x)
    return x.strip()

live = pd.read_csv(LIVE)

live["_key"] = live["horse"].apply(norm)
live["is_scratched"] = False
live["scratch_status"] = ""
live["runner_status"] = "ACTIVE"

if SCRATCHES.exists():
    scratches = pd.read_csv(SCRATCHES)

    horse_col = next((c for c in scratches.columns if "horse" in c.lower()), None)

    if horse_col:
        scratches["_key"] = scratches[horse_col].apply(norm)
        scratch_set = set(scratches["_key"])

        live["is_scratched"] = live["_key"].isin(scratch_set)
        live["scratch_status"] = live["is_scratched"].map(lambda x: "SCRATCHED" if x else "")
        live["runner_status"] = live["is_scratched"].map(lambda x: "SCRATCHED" if x else "ACTIVE")

live = live.drop(columns=["_key"], errors="ignore")
live.to_csv(LIVE, index=False)

print("SCRATCHINGS REPAIRED")
print("rows:", len(live))
print("scratched:", int((live["runner_status"] == "SCRATCHED").sum()))
print(live.loc[live["runner_status"] == "SCRATCHED", ["race_key","horse","horse_no","runner_status"]].head(50).to_string(index=False))
