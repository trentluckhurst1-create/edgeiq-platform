from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FILES = [
    "edgeiq_projected_settling_engine_v4.csv",
    "edgeiq_execution_board_live.csv",
    "edgeiq_execution_board_terminal.csv",
    "edgeiq_execution_board.csv",
    "sportsbet_live_market_v1.csv",
    "edgeiq_price_truth_adjustments.csv",
    "ratings_final_v2.csv",
    "race_card_report.csv",
    "race_fields.csv",
]

print("=" * 100)
print("EDGEIQ RACE TAB LIVE PRICE / EXECUTION DATA AUDIT")
print("=" * 100)

for name in FILES:
    path = DATA / name
    print()
    print("-" * 100)
    print(name)
    print("-" * 100)

    if not path.exists():
        print("MISSING")
        continue

    try:
        df = pd.read_csv(path, nrows=20)
        print("EXISTS")
        print("COLUMNS:")
        print(", ".join(list(df.columns)))
        print()
        print("SAMPLE:")
        cols = [c for c in df.columns if c.lower() in [
            "horse","horse_name","runner","runner_name",
            "track","race_no","race_number","race_date",
            "fixed_win","market_price","live_price","current_price","sportsbet_price",
            "rated_price","fair_price","elite_rated_price",
            "edge_pct","overlay_pct","execution_action","action",
            "model_confidence_score","confidence","suppression_reason"
        ]]
        if not cols:
            cols = list(df.columns[:12])
        print(df[cols].head(8).to_string(index=False))
    except Exception as e:
        print("FAILED:", repr(e))

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)
