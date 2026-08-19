import pandas as pd
import re
from pathlib import Path

def norm(s):
    if pd.isna(s):
        return ""
    s = str(s).upper()
    s = s.replace("’", "'")
    s = s.replace("?", "")
    s = re.sub(r"\(NZ\)|\(IRE\)|\(GB\)|\(AUS\)", "", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

ROOT = Path(".")

TAB = pd.read_csv(ROOT / "public/data/edgeiq_tab_live_prices_direct_v1.csv")
RUN = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")

# 🔴 CRITICAL FIX: REMOVE SCR BEFORE ANY JOIN
TAB = TAB[TAB["tab_fixed_betting_status"] != "SCR"]

TAB["n"] = TAB["horse"].apply(norm)
RUN["n"] = RUN["horse"].apply(norm)

TAB["key"] = TAB["race_no"].astype(str) + "|" + TAB["n"]
RUN["key"] = RUN["race_no"].astype(str) + "|" + RUN["n"]

merged = RUN.merge(
    TAB[["key","tab_fixed_win","tab_fixed_betting_status"]],
    on="key",
    how="left"
)

print("[SCR FILTERED MERGE COMPLETE]")
print("rows:", len(merged))
print("matched:", merged["tab_fixed_win"].notna().sum())

out = ROOT / "public/data/edgeiq_live_runner_board_governed_v1.csv"
merged.to_csv(out, index=False)
