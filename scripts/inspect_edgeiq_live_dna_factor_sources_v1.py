from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CANDIDATES = [
    "edgeiq_historical_replay_settled_v1.csv",
    "edgeiq_live_runner_factor_scorecard_v2.csv",
    "edgeiq_live_runner_dna_v6_2.csv",
    "edgeiq_live_distance_dna_v1.csv",
    "edgeiq_live_condition_dna_v1.csv",
    "edgeiq_live_class_dna_v3.csv",
    "edgeiq_live_trainer_jockey_factor_feed_v3.csv",
]

for f in CANDIDATES:
    p = DATA / f
    print("\n" + "=" * 100)
    print(f)

    if not p.exists():
        print("MISSING")
        continue

    df = pd.read_csv(p, nrows=3, dtype=str).fillna("")
    print("columns:")
    for c in df.columns:
        if any(x in c.lower() for x in [
            "distance", "condition", "class", "trainer", "jockey", "combo",
            "score", "band", "won", "finish", "sp", "race_key", "horse"
        ]):
            print(" -", c)

    print("\npreview:")
    print(df.head(3).to_string(index=False))
