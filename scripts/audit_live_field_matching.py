import pandas as pd
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

live = pd.read_csv(DATA / "edgeiq_vic_live_terminal_feed_v1.csv", dtype=str).fillna("")
fields = pd.read_csv(DATA / "race_fields.csv", dtype=str).fillna("")

def norm(v):
    s = str(v).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

live["horse_norm"] = live["horse"].apply(norm)
fields["horse_norm"] = fields["horse"].apply(norm)

live["track_norm"] = live["track"].apply(norm)
fields["track_norm"] = fields["track"].apply(norm)

live["race_norm"] = live["race_no"].astype(str).str.extract(r"(\d+)").fillna("")
fields["race_norm"] = fields["race_no"].astype(str).str.extract(r"(\d+)").fillna("")

matched = []
unmatched = []

field_keys = set(
    (
        r.track_norm,
        r.race_norm,
        r.horse_norm
    )
    for _, r in fields.iterrows()
)

for _, r in live.iterrows():

    key = (
        r.track_norm,
        r.race_norm,
        r.horse_norm
    )

    row = {
        "track": r.track,
        "race_no": r.race_no,
        "horse": r.horse,
        "horse_norm": r.horse_norm,
        "matched": key in field_keys
    }

    if key in field_keys:
        matched.append(row)
    else:
        unmatched.append(row)

pd.DataFrame(matched).to_csv(
    DATA / "edgeiq_live_field_matches.csv",
    index=False
)

pd.DataFrame(unmatched).to_csv(
    DATA / "edgeiq_live_field_unmatched.csv",
    index=False
)

print("=" * 80)
print("EDGEIQ LIVE FIELD MATCH AUDIT")
print("=" * 80)
print("LIVE:", len(live))
print("MATCHED:", len(matched))
print("UNMATCHED:", len(unmatched))
print("=" * 80)
