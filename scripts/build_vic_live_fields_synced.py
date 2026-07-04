from pathlib import Path
import pandas as pd
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_vic_live_fields_synced.csv"

live = pd.read_csv(LIVE, dtype=str, keep_default_na=False).fillna("")

cols = [
    "race_date",
    "track",
    "race_no",
    "race_time",
    "distance",
    "race_class",
    "track_condition",
    "horse_no",
    "horse",
    "horse_key",
    "barrier",
    "jockey",
    "trainer",
    "is_scratched",
    "scratch_status",
    "runner_status",
    "silkUrl",
    "silk_url",
    "local_silk_path",
    "ui_price",
    "sportsbet_price",
    "fixed_win",
    "ui_fair_price",
    "rated_price",
    "ui_edge_pct",
    "execution_action",
    "ui_action",
]

for c in cols:
    if c not in live.columns:
        live[c] = ""

out = live[cols].copy()
out["synced_at"] = datetime.now().isoformat(timespec="seconds")
out["source"] = "edgeiq_vic_live_terminal_feed_v1"

out.to_csv(OUT, index=False, encoding="utf-8")

print("=" * 90)
print("EDGEIQ VIC LIVE FIELDS SYNCED")
print("=" * 90)
print("ROWS:", len(out))
print("OUT:", OUT)
print("=" * 90)
print(out.groupby(["track", "race_no"]).size().reset_index(name="runners").to_string(index=False))
