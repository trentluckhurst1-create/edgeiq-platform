import pandas as pd
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def canon(x):
    if pd.isna(x):
        return ""

    x = str(x).upper()

    # fix apostrophes
    x = x.replace("’", "'").replace("?", "'")

    # remove all non-alphanumeric except spaces
    x = re.sub(r"[^A-Z0-9 ]", "", x)

    # collapse spaces
    x = re.sub(r"\s+", " ", x).strip()

    return x


full = pd.read_csv(ROOT / "public/data/tab_full_field_v2.csv")
runner = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")

full["horse_key"] = full["horse"].apply(canon)
runner["horse_key"] = runner["horse"].apply(canon)

merged = runner.merge(
    full,
    on=["track","race_no","horse_key"],
    how="left"
)

out = ROOT / "public/data/edgeiq_live_runner_board_v3.csv"
merged.to_csv(out, index=False)

print("[CANONICAL MERGE COMPLETE]")
print("rows:", len(merged))
print("matched:", merged["tab_fixed_win"].notna().sum())
print("unmatched:", merged["tab_fixed_win"].isna().sum())
