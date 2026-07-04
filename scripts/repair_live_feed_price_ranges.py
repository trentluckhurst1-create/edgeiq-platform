import pandas as pd
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
BOOK_PATH = DATA / "edgeiq_bookmaker_board_v1.csv"
TAPE_PATH = DATA / "edgeiq_market_tape.csv"

def norm(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^A-Z0-9]", "", x)
    return x.strip()

def to_num(s):
    return pd.to_numeric(s, errors="coerce")

live = pd.read_csv(LIVE_PATH)
book = pd.read_csv(BOOK_PATH)

live["_horse_norm"] = live["horse"].apply(norm)
book["_horse_norm"] = book["horse"].apply(norm)

key_cols = ["race_date", "track", "race_no", "_horse_norm"]

for df in [live, book]:
    df["race_no"] = df["race_no"].astype(str).str.replace(".0", "", regex=False)
    df["track"] = df["track"].astype(str).str.upper().str.strip()

book["live_price"] = to_num(book.get("live_price"))
book["open_price"] = to_num(book.get("open_price"))
book["low_price"] = to_num(book.get("low_price"))
book["high_price"] = to_num(book.get("high_price"))
book["previous_price"] = to_num(book.get("previous_price"))

book = book.sort_values(["race_date", "track", "race_no", "_horse_norm"]).drop_duplicates(key_cols, keep="last")

merge_cols = key_cols + [
    "live_price",
    "open_price",
    "low_price",
    "high_price",
    "previous_price",
    "move_direction",
    "move_delta",
]

fixed = live.merge(
    book[merge_cols],
    on=key_cols,
    how="left",
    suffixes=("", "_book"),
)

for col in ["live_price", "open_price", "low_price", "high_price", "previous_price"]:
    book_col = f"{col}_book"
    if book_col in fixed.columns:
        fixed[col] = fixed[book_col].combine_first(pd.to_numeric(fixed.get(col), errors="coerce"))

if TAPE_PATH.exists():
    tape = pd.read_csv(TAPE_PATH)
    tape["_horse_norm"] = tape["horse"].apply(norm)
    tape["race_no"] = tape["race_no"].astype(str).str.replace(".0", "", regex=False)
    tape["track"] = tape["track"].astype(str).str.upper().str.strip()
    tape["live_price"] = to_num(tape.get("live_price"))

    hist = (
        tape.dropna(subset=["live_price"])
        .groupby(["track", "race_no", "_horse_norm"], as_index=False)
        .agg(
            tape_open_price=("live_price", "first"),
            tape_low_price=("live_price", "min"),
            tape_high_price=("live_price", "max"),
            tape_previous_price=("live_price", lambda x: x.iloc[-2] if len(x) > 1 else x.iloc[-1]),
        )
    )

    fixed = fixed.merge(
        hist,
        on=["track", "race_no", "_horse_norm"],
        how="left",
    )

    fixed["open_price"] = fixed["tape_open_price"].combine_first(pd.to_numeric(fixed.get("open_price"), errors="coerce"))
    fixed["low_price"] = fixed["tape_low_price"].combine_first(pd.to_numeric(fixed.get("low_price"), errors="coerce"))
    fixed["high_price"] = fixed["tape_high_price"].combine_first(pd.to_numeric(fixed.get("high_price"), errors="coerce"))
    fixed["previous_price"] = fixed["tape_previous_price"].combine_first(pd.to_numeric(fixed.get("previous_price"), errors="coerce"))

fixed["sportsbet_price"] = pd.to_numeric(fixed.get("live_price"), errors="coerce")
fixed["market_price"] = pd.to_numeric(fixed.get("live_price"), errors="coerce")
fixed["fixed_win"] = pd.to_numeric(fixed.get("live_price"), errors="coerce")

drop_cols = [
    c for c in fixed.columns
    if c.endswith("_book")
    or c.startswith("tape_")
    or c == "_horse_norm"
]

fixed = fixed.drop(columns=drop_cols, errors="ignore")

fixed.to_csv(LIVE_PATH, index=False)

print("=" * 80)
print("EDGEIQ LIVE MARKET PRICE RANGE REPAIR COMPLETE")
print("=" * 80)
print("rows:", len(fixed))
print("live priced:", fixed["live_price"].notna().sum())
print("open priced:", fixed["open_price"].notna().sum())
print("low priced:", fixed["low_price"].notna().sum())
print("high priced:", fixed["high_price"].notna().sum())
print("previous priced:", fixed["previous_price"].notna().sum())
print("=" * 80)
