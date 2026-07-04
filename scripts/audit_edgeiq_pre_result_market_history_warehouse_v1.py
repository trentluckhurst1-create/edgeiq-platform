from pathlib import Path
import pandas as pd

FILE = Path(
    r".\public\data\edgeiq_pre_result_market_history_warehouse_v1.csv"
)

print("[PRE_RESULT_MARKET_HISTORY_WAREHOUSE_AUDIT_V1] START")

df = pd.read_csv(FILE, low_memory=False)

print("")
print("[ROWS]")
print(len(df))

print("")
print("[COLUMNS]")
for c in df.columns:
    print(c)

print("")

possible = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "market_price",
    "fixed_win",
    "sportsbet_price",
    "live_price",
    "open_price",
    "close_price",
    "snapshot",
    "timestamp",
    "price"
]

print("[LIKELY_MARKET_COLUMNS]")

for c in df.columns:
    lc = c.lower()
    if any(x in lc for x in possible):
        print(c)

print("")

race_cols = [
    c for c in df.columns
    if c.lower() in
    [
        "race_date",
        "track",
        "race_no",
        "horse"
    ]
]

print("[RACE_COLS]")
print(race_cols)

print("")

if set(["race_date","track","race_no"]).issubset(df.columns):

    races = (
        df[
            ["race_date","track","race_no"]
        ]
        .drop_duplicates()
    )

    print("[RACES]")
    print(len(races))

print("")
print(df.head(10).to_string())
