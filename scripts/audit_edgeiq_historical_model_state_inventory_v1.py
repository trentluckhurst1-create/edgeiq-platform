from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

targets = [
    "edgeiq_probability_engine_v2.csv",
    "edgeiq_probability_engine_v4.csv",
    "edgeiq_probability_engine_v4_1.csv",
    "edgeiq_probability_engine_v4_2_candidate_replay.csv",
    "edgeiq_probability_research_v5_compression_fix.csv",
    "edgeiq_probability_research_v6_candidate.csv",
    "edgeiq_contextual_probability_engine_v5.csv",
    "edgeiq_historical_performance_rating_v6_1_research.csv",
    "edgeiq_historical_replay_v1.csv",
    "edgeiq_historical_replay_settled_v1.csv",
    "edgeiq_fair_price_v6.csv",
    "edgeiq_fair_price_v6_1.csv",
    "edgeiq_fair_price_v7.csv",
    "edgeiq_fair_price_v7_1.csv",
    "edgeiq_fair_price_v7_2.csv",
    "edgeiq_current_fair_prices_v6_research_replay.csv",
    "edgeiq_current_fair_prices_v5_2_research_replay.csv",
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_live_runner_board_v2.csv",
    "edgeiq_live_runner_board_v3.csv",
    "edgeiq_live_runner_board_v4.csv",
    "edgeiq_live_runner_board_governed_v1.csv",
    "edgeiq_live_runner_board_FINAL_UNIFIED_v7.csv"
]

records = []

for name in targets:

    path = DATA / name

    if not path.exists():
        continue

    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        continue

    cols = [str(c) for c in df.columns]

    probability_cols = [
        c for c in cols
        if "prob" in c.lower()
    ]

    rating_cols = [
        c for c in cols
        if "rating" in c.lower()
    ]

    price_cols = [
        c for c in cols
        if "price" in c.lower()
    ]

    identity_cols = [
        c for c in cols
        if any(
            x in c.lower()
            for x in [
                "race",
                "horse",
                "runner",
                "track",
                "date"
            ]
        )
    ]

    records.append({
        "file": name,
        "rows": len(df),
        "columns": len(cols),
        "probability_cols": ";".join(probability_cols),
        "rating_cols": ";".join(rating_cols),
        "price_cols": ";".join(price_cols),
        "identity_cols": ";".join(identity_cols)
    })

out = pd.DataFrame(records)

outfile = (
    DATA /
    "edgeiq_historical_model_state_inventory_v1.csv"
)

out.to_csv(outfile, index=False)

print("[HISTORICAL_MODEL_STATE_INVENTORY] COMPLETE")
print(out.to_string(index=False))
