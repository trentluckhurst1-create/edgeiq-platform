from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
FAIR = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
AUDIT = DATA / "edgeiq_live_runner_board_fair_price_repair_v1_audit.csv"

def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def clean_race_no(value):
    text = clean(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    return str(int(digits)) if digits else text

def canon(value):
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("’", "").replace("'", "").replace(".", "")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())

def num(value):
    return pd.to_numeric(value, errors="coerce")

print("=" * 90)
print("EDGEIQ LIVE RUNNER BOARD FAIR PRICE REPAIR V1")
print("=" * 90)

board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False)
fair = pd.read_csv(FAIR, dtype=str, keep_default_na=False, low_memory=False)

for df in [board, fair]:
    df["track_key"] = df["track"].map(lambda x: clean(x).upper())
    df["race_no_key"] = df["race_no"].map(clean_race_no)

board["horse_key"] = board["horse"].map(canon)
fair["horse_key"] = fair["horse"].map(canon)

fair_price_col = "rated_price_v5_2_review"
if fair_price_col not in fair.columns:
    raise ValueError(f"Missing fair price column: {fair_price_col}")

fair_small = fair[["track_key", "race_no_key", "horse_key", fair_price_col]].copy()
fair_small = fair_small.rename(columns={fair_price_col: "fair_price_repair"})
fair_small["fair_price_repair_num"] = num(fair_small["fair_price_repair"])
fair_small = fair_small[fair_small["fair_price_repair_num"].notna()].copy()
fair_small = fair_small.drop_duplicates(["track_key", "race_no_key", "horse_key"], keep="first")

before_with_fair = int(num(board.get("fair_price", pd.Series(dtype=str))).notna().sum()) if "fair_price" in board.columns else 0

merged = board.merge(fair_small, on=["track_key", "race_no_key", "horse_key"], how="left")

if "fair_price" not in merged.columns:
    merged["fair_price"] = ""
if "rated_price" not in merged.columns:
    merged["rated_price"] = ""
if "edge_pct" not in merged.columns:
    merged["edge_pct"] = ""

fair_num = num(merged["fair_price_repair"])
matched = fair_num.notna()

merged.loc[matched, "fair_price"] = fair_num[matched].round(2).map(lambda x: f"{x:.2f}")
merged.loc[matched, "rated_price"] = fair_num[matched].round(2).map(lambda x: f"{x:.2f}")
merged.loc[matched, "edgeiq_price"] = fair_num[matched].round(2).map(lambda x: f"{x:.2f}")

live_col = "live_price" if "live_price" in merged.columns else "market_price"
live_num = num(merged[live_col])
edge = ((live_num / fair_num) - 1.0) * 100.0
edge_valid = matched & live_num.notna() & (live_num > 0) & (fair_num > 0)
merged.loc[edge_valid, "edge_pct"] = edge[edge_valid].round(1).map(lambda x: f"{x:.1f}")

if "execution_action" in merged.columns:
    edge_num = num(merged["edge_pct"])
    merged.loc[edge_num >= 18, "execution_action"] = "EXECUTE"
    merged.loc[(edge_num >= 10) & (edge_num < 18), "execution_action"] = "WATCH"
    merged.loc[(edge_num < 10) & edge_num.notna(), "execution_action"] = "PASS"

drop_cols = ["track_key", "race_no_key", "horse_key", "fair_price_repair", "fair_price_repair_num"]
merged = merged.drop(columns=[c for c in drop_cols if c in merged.columns])

merged.to_csv(BOARD, index=False, encoding="utf-8")

after_with_fair = int(num(merged["fair_price"]).notna().sum())
after_with_edge = int(num(merged["edge_pct"]).notna().sum())

audit = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "board_rows": len(board),
    "fair_rows": len(fair),
    "fair_rows_usable": len(fair_small),
    "before_with_fair": before_with_fair,
    "after_with_fair": after_with_fair,
    "after_with_edge": after_with_edge,
    "status": "OK" if after_with_fair > before_with_fair else "NO_NEW_FAIR_PRICES_JOINED",
}])
audit.to_csv(AUDIT, index=False, encoding="utf-8")

print(audit.to_string(index=False))
print("=" * 90)
