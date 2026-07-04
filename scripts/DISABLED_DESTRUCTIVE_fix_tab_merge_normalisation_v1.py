import pandas as pd
import re
from pathlib import Path

def norm(s):
    if pd.isna(s):
        return ""
    s = str(s).upper()

    # fix encoding garbage
    s = s.replace("’", "'")
    s = s.replace("?", "")
    s = s.replace("-", " ")

    # remove punctuation noise
    s = re.sub(r"[^A-Z0-9 ]", "", s)

    # collapse spaces
    s = re.sub(r"\s+", " ", s).strip()

    return s

ROOT = Path(".")
TAB = pd.read_csv(ROOT / "public/data/edgeiq_tab_live_prices_direct_v1.csv")
RUN = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_governed_v1.csv")

TAB["norm_horse"] = TAB["horse"].apply(norm)
RUN["norm_horse"] = RUN["horse"].apply(norm)

merged = RUN.merge(
    TAB[["race_no","norm_horse","tab_fixed_win","tab_fixed_betting_status"]],
    on=["race_no","norm_horse"],
    how="left"
)

out_path = ROOT / "public/data/edgeiq_live_runner_board_governed_v1.csv"
merged.to_csv(out_path, index=False)

print("[FIXED MERGE COMPLETE]")
print("rows", len(merged))
print("matched", merged["tab_fixed_win"].notna().sum())
