import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
LIVE = ROOT / "public/data/edgeiq_vic_live_terminal_feed_v1.csv"

df = pd.read_csv(LIVE)

target = (
    (df["track"].astype(str).str.upper().str.strip() == "MOE") &
    (df["race_no"].astype(str).str.replace(".0", "", regex=False) == "5")
)

scratch_numbers = {"1", "3", "5", "11", "14"}

horse_no = df["horse_no"].astype(str).str.replace(".0", "", regex=False)

df.loc[target, "is_scratched"] = False
df.loc[target, "scratch_status"] = ""
df.loc[target, "runner_status"] = "ACTIVE"

mask = target & horse_no.isin(scratch_numbers)

df.loc[mask, "is_scratched"] = True
df.loc[mask, "scratch_status"] = "SCRATCHED"
df.loc[mask, "runner_status"] = "SCRATCHED"
df.loc[mask, "live_price"] = ""
df.loc[mask, "sportsbet_price"] = ""
df.loc[mask, "market_price"] = ""
df.loc[mask, "fixed_win"] = ""

df.to_csv(LIVE, index=False)

print("FORCED MOE R5 SCRATCHINGS")
print(df.loc[target, ["race_no","horse_no","horse","is_scratched","runner_status"]].to_string(index=False))
