import pandas as pd
import re
from pathlib import Path

def norm(s):
    if pd.isna(s):
        return ""
    s = str(s).upper()
    s = s.replace("’", "'")
    s = s.replace("?", "")
    s = re.sub(r"[^A-Z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

ROOT = Path(".")

TAB = pd.read_csv(ROOT / "public/data/edgeiq_tab_live_prices_direct_v1.csv")
RUN = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")

# sanity check
assert "tab_fixed_win" in TAB.columns, "TAB feed missing tab_fixed_win"

TAB["norm_horse"] = TAB["horse"].apply(norm)
RUN["norm_horse"] = RUN["horse"].apply(norm)

TAB["key"] = TAB["race_no"].astype(str) + "|" + TAB["norm_horse"]
RUN["key"] = RUN["race_no"].astype(str) + "|" + RUN["norm_horse"]

merged = RUN.merge(
    TAB[["key","tab_fixed_win","tab_fixed_betting_status"]],
    on="key",
    how="left"
)

out = ROOT / "public/data/edgeiq_live_runner_board_governed_v1.csv"
merged.to_csv(out, index=False)

print("[MERGE FIXED CLEAN PIPELINE]")
print("rows:", len(merged))
print("matched:", merged["tab_fixed_win"].notna().sum())
