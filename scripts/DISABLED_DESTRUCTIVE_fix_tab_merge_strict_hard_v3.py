import pandas as pd
import re
from pathlib import Path

def norm(s):
    if pd.isna(s):
        return ""

    s = str(s).upper()

    # fix unicode noise
    s = s.replace("’", "'")
    s = s.replace("`", "")
    s = s.replace("?", "")

    # remove country tags
    s = re.sub(r"\(NZ\)|\(IRE\)|\(GB\)|\(AUS\)", "", s)

    # remove all punctuation except spaces/numbers
    s = re.sub(r"[^A-Z0-9 ]", " ", s)

    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    return s

ROOT = Path(".")

TAB = pd.read_csv(ROOT / "public/data/edgeiq_tab_live_prices_direct_v1.csv")
RUN = pd.read_csv(ROOT / "public/data/edgeiq_live_runner_board_v1.csv")

TAB["n"] = TAB["horse"].apply(norm)
RUN["n"] = RUN["horse"].apply(norm)

TAB["key"] = TAB["race_no"].astype(str) + "|" + TAB["n"]
RUN["key"] = RUN["race_no"].astype(str) + "|" + RUN["n"]

merged = RUN.merge(
    TAB[["key","tab_fixed_win","tab_fixed_betting_status"]],
    on="key",
    how="left"
)

print("[HARD NORMALISATION MERGE]")
print("rows:", len(merged))
print("matched:", merged["tab_fixed_win"].notna().sum())

out = ROOT / "public/data/edgeiq_live_runner_board_governed_v1.csv"
merged.to_csv(out, index=False)
