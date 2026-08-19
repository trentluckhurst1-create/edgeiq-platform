import pandas as pd
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
SB = DATA / "sportsbet_live_market_v1.csv"

def norm(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^A-Z0-9]", "", x)
    return x.strip()

def rn(x):
    return str(x).replace(".0", "").strip()

live = pd.read_csv(LIVE)
sb = pd.read_csv(SB)

live["_key"] = live["horse"].apply(norm)
live["_track"] = live["track"].astype(str).str.upper().str.strip()
live["_race"] = live["race_no"].apply(rn)

sb["_key"] = sb["horse"].apply(norm)
sb["_track"] = sb["track"].astype(str).str.upper().str.strip()
sb["_race"] = sb["race_no"].apply(rn)

for c in ["is_out","status","status_code","runner_status","selection_status","betting_status"]:
    if c not in sb.columns:
        sb[c] = ""

def explicit_scratched(row):
    text = " ".join(str(row.get(c, "")) for c in [
        "is_out","status","status_code","runner_status","selection_status","betting_status"
    ]).upper()
    return any(word in text for word in ["SCR", "SCRATCH", "SCRATCHED", "WITHDRAWN", "WITHDRAW", "LATE SCR"])

sb["sb_scratched"] = sb.apply(explicit_scratched, axis=1)

status = (
    sb.sort_values(["_track","_race","_key"])
      .drop_duplicates(["_track","_race","_key"], keep="last")
      [["_track","_race","_key","sb_scratched"]]
)

live = live.merge(status, on=["_track","_race","_key"], how="left")

live["is_scratched"] = live["sb_scratched"].fillna(False)
live["scratch_status"] = live["is_scratched"].map(lambda x: "SCRATCHED" if x else "")
live["runner_status"] = live["is_scratched"].map(lambda x: "SCRATCHED" if x else "ACTIVE")

live = live.drop(columns=["_key","_track","_race","sb_scratched"], errors="ignore")
live.to_csv(LIVE, index=False)

print("SCRATCHINGS FROM FRESH SPORTSBET STATUS COMPLETE")
print("scratched:", int((live["runner_status"] == "SCRATCHED").sum()))
print(live.loc[live["runner_status"] == "SCRATCHED", ["race_key","horse_no","horse","runner_status"]].to_string(index=False))
