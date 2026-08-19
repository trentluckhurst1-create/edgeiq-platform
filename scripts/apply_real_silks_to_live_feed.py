from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
LOOKUP = DATA / "edgeiq_real_silk_lookup.csv"

def norm(v):
    s = str(v or "").upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def main():
    live = pd.read_csv(LIVE, dtype=str).fillna("")
    lookup = pd.read_csv(LOOKUP, dtype=str).fillna("")

    silk_map = {
        norm(r["horse_key"]): r["silk_path"]
        for _, r in lookup.iterrows()
    }

    matched = 0

    for idx, row in live.iterrows():
        key = norm(row.get("horse_key") or row.get("horse"))

        silk = silk_map.get(key, "")

        if silk:
            matched += 1
            live.at[idx, "silkUrl"] = silk
            live.at[idx, "silk_url"] = silk
            live.at[idx, "local_silk_path"] = silk

    live.to_csv(LIVE, index=False)

    print("=" * 90)
    print("LIVE FEED REAL SILKS APPLIED")
    print("=" * 90)
    print("MATCHED:", matched)
    print("ROWS:", len(live))

if __name__ == "__main__":
    main()
