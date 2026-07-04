from pathlib import Path
import pandas as pd

DATA = Path("./public/data")
SRC = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
OUT = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
BACKUP = DATA / "edgeiq_runner_dna_drawer_feed_v2_BEFORE_DATELESS_MATCH_FIX.csv"
SUMMARY = DATA / "edgeiq_runner_dna_drawer_feed_v2_dateless_match_fix_summary.csv"

df = pd.read_csv(SRC, dtype=str).fillna("")
df.to_csv(BACKUP, index=False)

before_nonblank = int((df["race_date"].astype(str).str.strip() != "").sum()) if "race_date" in df.columns else 0

df["race_date"] = ""

df.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "RUNNER_DNA_DRAWER_FEED_V2_DATELESS_MATCH_FIX_COMPLETE"},
    {"metric": "rows", "value": len(df)},
    {"metric": "race_date_nonblank_before", "value": before_nonblank},
    {"metric": "race_date_nonblank_after", "value": int((df["race_date"].astype(str).str.strip() != "").sum())},
    {"metric": "backup", "value": BACKUP.name},
    {"metric": "output", "value": OUT.name},
])
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_DRAWER_FEED_V2_DATELESS_MATCH_FIX] COMPLETE")
print(summary.to_string(index=False))
