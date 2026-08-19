from pathlib import Path
import re
import pandas as pd

DATA = Path(r".\public\data")
EXEC = DATA / "edgeiq_execution_board_live.csv"
SPORTS = DATA / "sportsbet_live_market_v1.csv"

backup = DATA / "edgeiq_execution_board_live_PRE_SPORTSBET_PRICE_PATCH.csv"

def canon(v):
    s = "" if pd.isna(v) else str(v).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)

exec_df = pd.read_csv(EXEC, dtype=str, keep_default_na=False, low_memory=False)
sports = pd.read_csv(SPORTS, dtype=str, keep_default_na=False, low_memory=False)

exec_df.to_csv(backup, index=False)

exec_df["_horse_canon"] = exec_df["horse"].map(canon)
sports["_horse_canon"] = sports["horse"].map(canon)

sports["sportsbet_price_patch"] = pd.to_numeric(sports["sportsbet_price"], errors="coerce")
sports_keep = (
    sports[
        ["track", "race_no", "_horse_canon", "sportsbet_price_patch", "price_win", "event_id", "market_id", "timestamp"]
    ]
    .sort_values(["track", "race_no", "_horse_canon", "sportsbet_price_patch"], na_position="last")
    .drop_duplicates(["track", "race_no", "_horse_canon"], keep="first")
)

merged = exec_df.merge(
    sports_keep,
    on=["track", "race_no", "_horse_canon"],
    how="left",
)

mask = merged["sportsbet_price_patch"].notna() & (merged["sportsbet_price_patch"] > 0)

for col in ["sportsbet_price", "market_price", "live_price"]:
    if col not in merged.columns:
        merged[col] = ""
    merged.loc[mask, col] = merged.loc[mask, "sportsbet_price_patch"].map(lambda x: f"{float(x):.4f}".rstrip("0").rstrip("."))

if "price_win" not in merged.columns:
    merged["price_win"] = ""
merged.loc[mask & merged["price_win"].astype(str).str.strip().eq(""), "price_win"] = merged.loc[mask, "sportsbet_price_patch"].map(lambda x: f"{float(x):.4f}".rstrip("0").rstrip("."))

for src, dst in [("event_id", "sportsbet_event_id"), ("market_id", "sportsbet_market_id"), ("timestamp", "sportsbet_timestamp")]:
    if dst not in merged.columns:
        merged[dst] = ""
    if src in merged.columns:
        merged.loc[mask, dst] = merged.loc[mask, src].astype(str)

drop_cols = ["_horse_canon", "sportsbet_price_patch"]
for c in ["event_id", "market_id", "timestamp"]:
    if c in merged.columns and c not in exec_df.columns:
        drop_cols.append(c)

merged = merged.drop(columns=[c for c in drop_cols if c in merged.columns], errors="ignore")
merged.to_csv(EXEC, index=False)

print("EXEC rows:", len(exec_df))
print("SPORTS rows:", len(sports))
print("prices patched:", int(mask.sum()))
print("backup:", backup)
