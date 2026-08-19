from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_probability_research_v7_tab_candidate_t6.csv"

OUT = DATA / "edgeiq_market_vs_v7_tab_benchmark_v1.csv"
SUMMARY = DATA / "edgeiq_market_vs_v7_tab_benchmark_v1_summary.csv"
REPORT = DATA / "edgeiq_market_vs_v7_tab_benchmark_v1_report.txt"

print("[MARKET_VS_V7_TAB_BENCHMARK_V1] START")

df = pd.read_csv(SRC, low_memory=False)

df["_won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
df["_sp"] = pd.to_numeric(df["sp_price"], errors="coerce")
df["_v7"] = pd.to_numeric(df["v7_tab_probability_t6"], errors="coerce")
df["_race_group"] = df["_race_group_v4"].astype(str)

df = df[df["_sp"].notna() & (df["_sp"] > 1)].copy()

df["market_probability"] = 1 / df["_sp"]

market_sum = (
    df.groupby("_race_group")["market_probability"]
    .transform("sum")
)

df["market_probability"] = (
    df["market_probability"] / market_sum
)

eps = 1e-12

for col, prefix in [
    ("market_probability", "market"),
    ("_v7", "v7")
]:
    p = df[col].clip(eps, 1 - eps)

    df[f"{prefix}_log_loss"] = -(
        df["_won"] * np.log(p) +
        (1 - df["_won"]) * np.log(1 - p)
    )

    df[f"{prefix}_brier"] = (
        p - df["_won"]
    ) ** 2

df["market_rank"] = (
    df.groupby("_race_group")["market_probability"]
    .rank(method="first", ascending=False)
)

df["v7_rank"] = (
    df.groupby("_race_group")["_v7"]
    .rank(method="first", ascending=False)
)

market_top = (
    df.loc[df["market_rank"] == 1]
    .groupby("_race_group")["_won"]
    .max()
)

v7_top = (
    df.loc[df["v7_rank"] == 1]
    .groupby("_race_group")["_won"]
    .max()
)

market_top_wins = int(market_top.sum())
v7_top_wins = int(v7_top.sum())
races = df["_race_group"].nunique()

summary = pd.DataFrame([{
    "built_at":
        datetime.now(timezone.utc).isoformat(),
    "rows":
        len(df),
    "races":
        races,
    "market_log_loss":
        float(df["market_log_loss"].mean()),
    "v7_log_loss":
        float(df["v7_log_loss"].mean()),
    "log_loss_delta_v7_minus_market":
        float(
            df["v7_log_loss"].mean() -
            df["market_log_loss"].mean()
        ),
    "market_brier":
        float(df["market_brier"].mean()),
    "v7_brier":
        float(df["v7_brier"].mean()),
    "brier_delta_v7_minus_market":
        float(
            df["v7_brier"].mean() -
            df["market_brier"].mean()
        ),
    "market_top_pick_wins":
        market_top_wins,
    "v7_top_pick_wins":
        v7_top_wins,
    "market_top_pick_win_pct":
        round(
            market_top_wins / races * 100,
            2
        ),
    "v7_top_pick_win_pct":
        round(
            v7_top_wins / races * 100,
            2
        ),
    "top_pick_delta_v7_minus_market":
        round(
            (
                v7_top_wins -
                market_top_wins
            ) / races * 100,
            2
        ),
    "status":
        "MARKET_VS_V7_TAB_BENCHMARK_COMPLETE_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

summary.to_csv(OUT, index=False)

r = summary.iloc[0]

lines = []
lines.append("EDGEIQ MARKET VS V7 TAB BENCHMARK")
lines.append("=" * 50)
lines.append(f"built_at={r['built_at']}")
lines.append("")
lines.append(f"rows={int(r['rows'])}")
lines.append(f"races={int(r['races'])}")
lines.append("")
lines.append(f"market_log_loss={r['market_log_loss']:.6f}")
lines.append(f"v7_log_loss={r['v7_log_loss']:.6f}")
lines.append(f"log_loss_delta={r['log_loss_delta_v7_minus_market']:.6f}")
lines.append("")
lines.append(f"market_brier={r['market_brier']:.6f}")
lines.append(f"v7_brier={r['v7_brier']:.6f}")
lines.append(f"brier_delta={r['brier_delta_v7_minus_market']:.6f}")
lines.append("")
lines.append(f"market_top_pick_win_pct={r['market_top_pick_win_pct']:.2f}")
lines.append(f"v7_top_pick_win_pct={r['v7_top_pick_win_pct']:.2f}")
lines.append(f"top_pick_delta={r['top_pick_delta_v7_minus_market']:.2f}")
lines.append("")
lines.append("production_changed=NO")

REPORT.write_text(
    "\n".join(lines),
    encoding="utf-8"
)

print("[MARKET_VS_V7_TAB_BENCHMARK_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"report={REPORT}")
print("")
print(summary.to_string(index=False))
