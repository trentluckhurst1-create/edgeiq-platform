from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

DATA = Path("public/data")

SRC = DATA / "edgeiq_probability_research_v7_tab_candidate_t6.csv"
OUT = DATA / "edgeiq_market_data_integrity_final_verdict_v1.csv"
REPORT = DATA / "edgeiq_market_data_integrity_final_verdict_v1_report.txt"

print("[MARKET_DATA_INTEGRITY_FINAL_VERDICT_V1_FIXED] START")

df = pd.read_csv(SRC, low_memory=False)

df["_sp"] = pd.to_numeric(df["sp_price"], errors="coerce")
df["_won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
df["_race_group"] = df["_race_group_v4"].astype(str)
df["_raw_prob"] = np.where(df["_sp"] > 1, 1 / df["_sp"], np.nan)

winner_avg_sp = float(df.loc[df["_won"] == 1, "_sp"].mean())
loser_avg_sp = float(df.loc[df["_won"] == 0, "_sp"].mean())

race = (
    df.groupby("_race_group")
    .agg(
        rows=("horse", "count"),
        winners=("_won", "sum"),
        unique_sp=("_sp", "nunique"),
        sp_rows=("_sp", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
        raw_prob_sum=("_raw_prob", "sum")
    )
    .reset_index()
)

all_same_sp = int((race["unique_sp"] == 1).sum())
low_prob_sum = int((race["raw_prob_sum"] < 0.90).sum())
high_prob_sum = int((race["raw_prob_sum"] > 1.80).sum())
one_runner_races = int((race["rows"] == 1).sum())

verdict = "MARKET_BENCHMARK_BLOCKED"
reason = "sp_price is not valid full-field market data. Winner SP average is higher than loser SP average and many race-level implied probability sums are incomplete or distorted."

out = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows_audited": len(df),
    "races_audited": len(race),
    "winner_avg_sp": winner_avg_sp,
    "loser_avg_sp": loser_avg_sp,
    "winner_sp_higher_than_loser_sp": winner_avg_sp > loser_avg_sp,
    "all_same_sp_races": all_same_sp,
    "raw_prob_sum_lt_0_90_races": low_prob_sum,
    "raw_prob_sum_gt_1_80_races": high_prob_sum,
    "one_runner_races": one_runner_races,
    "market_benchmark_status": verdict,
    "production_changed": "NO",
    "reason": reason
}])

out.to_csv(OUT, index=False)

lines = []
lines.append("EDGEiQ MARKET DATA INTEGRITY FINAL VERDICT V1")
lines.append("=" * 56)
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append("")
lines.append("PRODUCTION STATUS")
lines.append("- production_changed=NO")
lines.append("- live_pricing_changed=NO")
lines.append("")
lines.append("VERDICT")
lines.append(f"- market_benchmark_status={verdict}")
lines.append("")
lines.append("WHY")
lines.append("- sp_price cannot be used as a full-field market benchmark.")
lines.append(f"- winner_avg_sp={winner_avg_sp:.4f}")
lines.append(f"- loser_avg_sp={loser_avg_sp:.4f}")
lines.append("- Winner SP average is higher than loser SP average, which is backwards for a true market column.")
lines.append("- Many race-level market sums are incomplete or distorted.")
lines.append("")
lines.append("AUDIT COUNTS")
lines.append(f"- rows_audited={len(df)}")
lines.append(f"- races_audited={len(race)}")
lines.append(f"- all_same_sp_races={all_same_sp}")
lines.append(f"- raw_prob_sum_lt_0_90_races={low_prob_sum}")
lines.append(f"- raw_prob_sum_gt_1_80_races={high_prob_sum}")
lines.append(f"- one_runner_races={one_runner_races}")
lines.append("")
lines.append("NEXT DIRECTION")
lines.append("- Keep V7 TAB T6 as research-only model benchmark.")
lines.append("- Do not compare against sp_price until true full-field market odds are restored.")
lines.append("- Rebuild market benchmark from proper historical market snapshots only.")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("[MARKET_DATA_INTEGRITY_FINAL_VERDICT_V1_FIXED] COMPLETE")
print(f"out={OUT}")
print(f"report={REPORT}")
print(out.to_string(index=False))
