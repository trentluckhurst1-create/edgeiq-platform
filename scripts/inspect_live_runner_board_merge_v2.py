from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]

LIVE_BOARD = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_live_runner_board_v1.csv"
EXECUTION = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_execution_board_live.csv"

def canon(x):
    if pd.isna(x):
        return ""
    return (
        str(x)
        .upper()
        .replace("'", "")
        .replace(".", "")
        .replace("-", "")
        .replace(" ", "")
        .strip()
    )

live = pd.read_csv(LIVE_BOARD, low_memory=False)
exe = pd.read_csv(EXECUTION, low_memory=False)

live["horse_canon_test"] = live["horse"].apply(canon)
exe["horse_canon_test"] = exe["horse"].apply(canon)

live["track_test"] = live["track"].astype(str).str.upper().str.strip()
exe["track_test"] = exe["track"].astype(str).str.upper().str.strip()

live["race_test"] = (
    live["race_no"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.strip()
)

exe["race_test"] = (
    exe["race_no"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.strip()
)

live["_key"] = (
    live["track_test"] + "|" +
    live["race_test"] + "|" +
    live["horse_canon_test"]
)

exe["_key"] = (
    exe["track_test"] + "|" +
    exe["race_test"] + "|" +
    exe["horse_canon_test"]
)

live_keys = set(live["_key"])
exe_keys = set(exe["_key"])

matched = live_keys & exe_keys
missing = live_keys - exe_keys

print("=" * 100)
print("LIVE RUNNER BOARD MERGE INSPECTION")
print("=" * 100)

print()
print(f"LIVE ROWS: {len(live)}")
print(f"EXECUTION ROWS: {len(exe)}")
print(f"MATCHED KEYS: {len(matched)}")
print(f"MISSING KEYS: {len(missing)}")

print()
print("=" * 100)
print("SAMPLE MISSING")
print("=" * 100)

for k in list(sorted(missing))[:50]:
    print(k)

print()
print("=" * 100)
print("EXECUTION SAMPLE")
print("=" * 100)

print(
    exe[
        ["track","race_no","horse","v3_probability","v3_fair_price","v3_edge_pct"]
    ]
    .head(20)
    .to_string(index=False)
)
