import pandas as pd
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
SPORTSBET = DATA / "sportsbet_live_market_v1.csv"

def norm(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^A-Z0-9]", "", x)
    return x.strip()

def race_no(x):
    return str(x).replace(".0", "").strip()

live = pd.read_csv(LIVE)
sb = pd.read_csv(SPORTSBET)

live["_key"] = live["horse"].apply(norm)
live["_track"] = live["track"].astype(str).str.upper().str.strip()
live["_race"] = live["race_no"].apply(race_no)

sb["_key"] = sb["horse"].apply(norm)
sb["_track"] = sb["track"].astype(str).str.upper().str.strip()
sb["_race"] = sb["race_no"].apply(race_no)

for col in ["is_out", "status", "status_code", "runner_status", "live_price"]:
    if col not in sb.columns:
        sb[col] = ""

def sb_scratched(row):
    text = " ".join([
        str(row.get("is_out", "")),
        str(row.get("status", "")),
        str(row.get("status_code", "")),
        str(row.get("runner_status", "")),
    ]).upper()

    if "SCR" in text or "OUT" in text or "WITHDRAW" in text:
        return True

    if pd.isna(row.get("live_price")) or str(row.get("live_price", "")).strip() == "":
        return True

    return False

sb["sb_scratched"] = sb.apply(sb_scratched, axis=1)

sb_status = (
    sb.sort_values(["_track", "_race", "_key"])
      .drop_duplicates(["_track", "_race", "_key"], keep="last")
      [["_track", "_race", "_key", "sb_scratched"]]
)

live = live.merge(sb_status, on=["_track", "_race", "_key"], how="left")

live["is_scratched"] = live["sb_scratched"].fillna(False)
live["scratch_status"] = live["is_scratched"].map(lambda x: "SCRATCHED" if x else "")
live["runner_status"] = live["is_scratched"].map(lambda x: "SCRATCHED" if x else "ACTIVE")

for col in ["live_price", "sportsbet_price", "market_price", "fixed_win", "ui_price"]:
    if col in live.columns:
        live.loc[live["is_scratched"], col] = pd.NA

live = live.drop(columns=["_key", "_track", "_race", "sb_scratched"], errors="ignore")
live.to_csv(LIVE, index=False)

print("SPORTSBET SCRATCHINGS REBUILT")
print("live rows:", len(live))
print("scratched:", int((live["runner_status"] == "SCRATCHED").sum()))
print(
    live.loc[
        live["runner_status"] == "SCRATCHED",
        ["race_key", "horse_no", "horse", "runner_status"]
    ].to_string(index=False)
)
