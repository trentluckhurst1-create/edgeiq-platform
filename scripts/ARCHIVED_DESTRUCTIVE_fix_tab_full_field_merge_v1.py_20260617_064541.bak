import pandas as pd
from pathlib import Path

ROOT = Path(".")

RUN = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")
TAB = pd.read_csv(ROOT / "public/data/tab_full_field_v1.csv")

def norm(s):
    if pd.isna(s):
        return ""
    return str(s).upper().replace(" ", "")

RUN["k"] = RUN["horse"].apply(norm) + RUN["race_no"].astype(str)
TAB["k"] = TAB["horse"].apply(norm) + TAB["race_no"].astype(str)

merged = RUN.merge(TAB, on="k", how="left")

out = ROOT / "public/data/edgeiq_live_runner_board_governed_v1.csv"
merged.to_csv(out, index=False)

print("[FINAL FIX COMPLETE]")
print("rows", len(merged))
print("matched", merged["horse_y"].notna().sum())
