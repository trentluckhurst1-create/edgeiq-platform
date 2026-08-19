import pandas as pd
import re
from pathlib import Path

def norm(s):
    if pd.isna(s):
        return ""
    s = str(s).upper()
    s = s.replace("’", "'")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

ROOT = Path(".")

RUN = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")
TAB = pd.read_csv(ROOT / "public/data/edgeiq_tab_live_prices_direct_v1.csv")

# RUNNER BOARD = SOURCE OF TRUTH
RUN["n"] = RUN["horse"].apply(norm)
TAB["n"] = TAB["horse"].apply(norm)

RUN["key"] = RUN["race_no"].astype(str) + "|" + RUN["n"]
TAB["key"] = TAB["race_no"].astype(str) + "|" + TAB["n"]

# LEFT JOIN TAB ONTO RUNNERS (NOT THE OTHER WAY AROUND)
merged = RUN.merge(
    TAB[["key","tab_fixed_win","tab_fixed_betting_status"]],
    on="key",
    how="left"
)

print("[SOURCE-LED MERGE COMPLETE]")
print("rows:", len(merged))
print("matched:", merged["tab_fixed_win"].notna().sum())

out = ROOT / "public/data/edgeiq_live_runner_board_governed_v1.csv"
merged.to_csv(out, index=False)
