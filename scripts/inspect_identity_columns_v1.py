from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

for file in [
    "edgeiq_execution_board_live.csv",
    "race_fields.csv",
    "form_card_runs.csv",
    "form_card_summary.csv",
    "edgeiq_official_runs_master_v1.csv",
    "edgeiq_sectional_master_v1.csv",
]:
    path = DATA / file
    print("=" * 100)
    print(file)
    if not path.exists():
        print("MISSING")
        continue
    df = pd.read_csv(path, low_memory=False)
    print("ROWS:", len(df))
    print("COLUMNS:")
    print(list(df.columns))
    print("HEAD:")
    print(df.head(3).to_string(index=False))
