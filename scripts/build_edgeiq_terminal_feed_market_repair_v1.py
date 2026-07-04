import pandas as pd
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TERMINAL = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
MARKET = DATA / "sportsbet_live_market_v1.csv"

OUT = DATA / "edgeiq_vic_live_terminal_feed_v1_market_repaired.csv"
AUDIT = DATA / "edgeiq_vic_live_terminal_feed_market_repair_audit_v1.csv"

print("=" * 90)
print("EDGEIQ TERMINAL FEED MARKET REPAIR V1")
print("=" * 90)

if not TERMINAL.exists():
    raise FileNotFoundError(TERMINAL)
if not MARKET.exists():
    raise FileNotFoundError(MARKET)

terminal = pd.read_csv(TERMINAL, low_memory=False)
market = pd.read_csv(MARKET, low_memory=False)

def norm_text(x):
    return re.sub(r"[^A-Z0-9]+", "", str(x).upper().strip())

def pick(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None

t_horse = pick(terminal, ["horse", "runner", "runner_name", "horse_name"])
t_track = pick(terminal, ["track", "venue"])
t_race_no = pick(terminal, ["race_no", "race_number", "race"])
t_date = pick(terminal, ["race_date", "date"])
t_price = pick(terminal, ["sportsbet_price", "market_price", "current_price"])

m_horse = pick(market, ["horse", "runner", "runner_name", "horse_name"])
m_track = pick(market, ["track", "venue"])
m_race_no = pick(market, ["race_no", "race_number", "race"])
m_date = pick(market, ["race_date", "date"])
m_price = pick(market, ["sportsbet_price", "market_price", "current_price", "price"])

required = {
    "terminal horse": t_horse,
    "terminal track": t_track,
    "terminal race_no": t_race_no,
    "terminal date": t_date,
    "market horse": m_horse,
    "market track": m_track,
    "market race_no": m_race_no,
    "market date": m_date,
    "market price": m_price,
}

missing = [k for k, v in required.items() if v is None]
if missing:
    print("TERMINAL COLUMNS:", list(terminal.columns))
    print("MARKET COLUMNS:", list(market.columns))
    raise ValueError(f"Missing required columns: {missing}")

terminal["_join_horse"] = terminal[t_horse].map(norm_text)
terminal["_join_track"] = terminal[t_track].map(norm_text)
terminal["_join_race_no"] = terminal[t_race_no].astype(str).str.replace(".0", "", regex=False).str.strip()
terminal["_join_date"] = terminal[t_date].astype(str).str.strip()

market["_join_horse"] = market[m_horse].map(norm_text)
market["_join_track"] = market[m_track].map(norm_text)
market["_join_race_no"] = market[m_race_no].astype(str).str.replace(".0", "", regex=False).str.strip()
market["_join_date"] = market[m_date].astype(str).str.strip()
market["_sportsbet_price_repaired"] = pd.to_numeric(market[m_price], errors="coerce")

market_small = market[
    ["_join_date", "_join_track", "_join_race_no", "_join_horse", "_sportsbet_price_repaired"]
].dropna(subset=["_sportsbet_price_repaired"]).drop_duplicates(
    ["_join_date", "_join_track", "_join_race_no", "_join_horse"],
    keep="last"
)

before_price_count = 0
if t_price:
    before_price_count = int(pd.to_numeric(terminal[t_price], errors="coerce").notna().sum())

merged = terminal.merge(
    market_small,
    on=["_join_date", "_join_track", "_join_race_no", "_join_horse"],
    how="left"
)

if "sportsbet_price" not in merged.columns:
    merged["sportsbet_price"] = ""

merged["sportsbet_price_before_repair"] = merged["sportsbet_price"]

merged["sportsbet_price"] = merged["_sportsbet_price_repaired"].combine_first(
    pd.to_numeric(merged["sportsbet_price"], errors="coerce")
)

merged["market_price_source"] = merged["_sportsbet_price_repaired"].apply(
    lambda x: "sportsbet_live_market_v1.csv" if pd.notna(x) else "UNCHANGED_OR_MISSING"
)

merged["market_repair_status"] = merged["_sportsbet_price_repaired"].apply(
    lambda x: "REPAIRED" if pd.notna(x) else "NO_CURRENT_MARKET_MATCH"
)

after_price_count = int(pd.to_numeric(merged["sportsbet_price"], errors="coerce").notna().sum())
repaired_count = int(merged["_sportsbet_price_repaired"].notna().sum())

drop_cols = [c for c in merged.columns if c.startswith("_join") or c == "_sportsbet_price_repaired"]
out = merged.drop(columns=drop_cols)

out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "terminal_rows", "value": len(terminal)},
    {"metric": "market_rows", "value": len(market)},
    {"metric": "usable_market_price_rows", "value": len(market_small)},
    {"metric": "terminal_price_count_before", "value": before_price_count},
    {"metric": "terminal_price_count_after", "value": after_price_count},
    {"metric": "prices_repaired_from_sportsbet_live", "value": repaired_count},
    {"metric": "rows_still_missing_price", "value": len(out) - after_price_count},
    {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
