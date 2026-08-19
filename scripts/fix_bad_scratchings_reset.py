import pandas as pd
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"

df = pd.read_csv(LIVE)

# Reset wrong scratchings
df["is_scratched"] = False
df["scratch_status"] = ""
df["runner_status"] = "ACTIVE"

# MOE R8 official visible scratchings from Sportsbet screen:
# 1 In Haste
# 4 Conflict
# 7 Mauna Kea Miss
# 8 Hi Val
# 16 Stirrup
moe_r8_scratched = {"1", "4", "7", "8", "16"}

track = df["track"].astype(str).str.upper().str.strip()
race = df["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()
horse_no = df["horse_no"].astype(str).str.replace(".0", "", regex=False).str.strip()

mask = (
    (track == "MOE") &
    (race == "8") &
    (horse_no.isin(moe_r8_scratched))
)

df.loc[mask, "is_scratched"] = True
df.loc[mask, "scratch_status"] = "SCRATCHED"
df.loc[mask, "runner_status"] = "SCRATCHED"

df.to_csv(LIVE, index=False)

print("SCRATCHINGS RESET AND MOE R8 FIXED")
print(df.loc[(track == "MOE") & (race == "8"), ["race_no","horse_no","horse","is_scratched","runner_status"]].to_string(index=False))
