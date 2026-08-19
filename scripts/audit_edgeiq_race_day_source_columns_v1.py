from pathlib import Path
import pandas as pd

DATA = Path.cwd() / "public" / "data"

files = [
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_race_shape_story_v1.csv",
    "edgeiq_track_intelligence_card_v1.csv",
]

for f in files:
    path = DATA / f
    print("")
    print("=" * 80)
    print(f)
    if not path.exists():
        print("MISSING")
        continue

    df = pd.read_csv(path, dtype=str).fillna("")
    print(f"rows={len(df)} cols={len(df.columns)}")

    cols = [c for c in df.columns if any(k in c.lower() for k in [
        "rail", "tempo", "pace", "shape", "condition", "track", "story", "bias"
    ])]

    for c in cols:
        sample = df[c].astype(str).replace("", pd.NA).dropna().head(5).tolist()
        print(f"{c}: {sample}")
