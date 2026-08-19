from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]

PUBLIC = ROOT / "public"
DATA = PUBLIC / "data"
SILKS_DIR = PUBLIC / "silks"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"

OUT = DATA / "edgeiq_real_silk_lookup.csv"

def norm(v):
    s = str(v or "").upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def main():
    live = pd.read_csv(LIVE, dtype=str).fillna("")

    pngs = list(SILKS_DIR.glob("*"))

    lookup = []

    for f in pngs:
        key = norm(f.stem)

        lookup.append({
            "horse_key": key,
            "silk_path": f"/silks/{f.name}"
        })

    lookup_df = pd.DataFrame(lookup)

    lookup_df.to_csv(OUT, index=False)

    print("=" * 90)
    print("REAL SILK LOOKUP BUILT")
    print("=" * 90)
    print("FILES:", len(lookup_df))
    print("OUT:", OUT)

if __name__ == "__main__":
    main()
