from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CANDIDATES = [
    "edgeiq_historical_performance_rating_v6_research.csv",
    "edgeiq_historical_runner_scores_v1.csv",
    "edgeiq_historical_replay_settled_v1.csv",
    "edgeiq_historical_pace_trust_replay_v1.csv",
    "edgeiq_execution_board_live_sectionals_v1.csv",
    "edgeiq_racingcom_results_warehouse_v2.csv",
]

for file in CANDIDATES:
    path = DATA / file
    print("\n" + "=" * 100)
    print(file)

    if not path.exists():
        print("MISSING")
        continue

    df = pd.read_csv(path, nrows=3, dtype=str).fillna("")
    print("rows_sample=3")
    print("columns:")
    for c in df.columns:
        print(" -", c)

    print("\nfirst rows:")
    print(df.head(3).to_string(index=False))
