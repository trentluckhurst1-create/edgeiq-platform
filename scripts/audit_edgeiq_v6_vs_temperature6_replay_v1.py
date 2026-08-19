from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

BASE = DATA / "edgeiq_pricing_replay_spine_v3_3_temperature6.csv"
V6 = DATA / "edgeiq_probability_v6_expanded_replay_v1.csv"

OUT = DATA / "edgeiq_v6_vs_temperature6_replay_v1.csv"
SUMMARY = DATA / "edgeiq_v6_vs_temperature6_replay_v1_summary.csv"

print("[V6_VS_TEMPERATURE6_REPLAY] START")

base = pd.read_csv(BASE, low_memory=False)
v6 = pd.read_csv(V6, low_memory=False)

for df in (base, v6):
    df["_join_key"] = (
        pd.to_datetime(df["race_date"], errors="coerce").dt.date.astype("string").fillna("") + "|" +
        df["track"].astype(str).str.upper().str.strip() + "|" +
        pd.to_numeric(df["race_no"], errors="coerce").astype("Int64").astype("string").fillna("") + "|" +
        df["horse"].astype(str).str.upper().str.strip()
    )

base = base[
    [
        "_join_key",
        "replay_probability_temperature6_v3_3",
        "replay_fair_price_temperature6_v3_3"
    ]
].copy()

v6 = v6[
    [
        "_join_key",
        "race_date",
        "track",
        "race_no",
        "horse",
        "v6_probability",
        "won"
    ]
].copy()

df = v6.merge(
    base,
    on="_join_key",
    how="left"
)

df["baseline_probability"] = pd.to_numeric(
    df["replay_probability_temperature6_v3_3"],
    errors="coerce"
)

df["baseline_fair_price"] = pd.to_numeric(
    df["replay_fair_price_temperature6_v3_3"],
    errors="coerce"
)

df["v6_probability"] = pd.to_numeric(
    df["v6_probability"],
    errors="coerce"
)

df["won"] = pd.to_numeric(
    df["won"],
    errors="coerce"
).fillna(0)

eps = 1e-12

for model in ["baseline", "v6"]:

    p = df[f"{model}_probability"].clip(eps, 1 - eps)

    df[f"{model}_log_loss"] = -(
        df["won"] * np.log(p) +
        (1 - df["won"]) * np.log(1 - p)
    )

    df[f"{model}_brier"] = (
        p - df["won"]
    ) ** 2

df["_race_group"] = (
    pd.to_datetime(df["race_date"], errors="coerce").dt.date.astype("string").fillna("") + "|" +
    df["track"].astype(str).str.upper().str.strip() + "|" +
    pd.to_numeric(df["race_no"], errors="coerce").astype("Int64").astype("string").fillna("")
)

df["baseline_rank"] = (
    df.groupby("_race_group")["baseline_probability"]
    .rank(method="first", ascending=False)
)

df["v6_rank"] = (
    df.groupby("_race_group")["v6_probability"]
    .rank(method="first", ascending=False)
)

baseline_top_wins = int(
    df.loc[df["baseline_rank"] == 1, "won"].sum()
)

v6_top_wins = int(
    df.loc[df["v6_rank"] == 1, "won"].sum()
)

summary = pd.DataFrame([{
    "built_at":
        datetime.now(timezone.utc).isoformat(),

    "rows":
        len(df),

    "races":
        df["_race_group"].nunique(),

    "matched_rows":
        int(df["baseline_probability"].notna().sum()),

    "baseline_log_loss":
        float(df["baseline_log_loss"].mean()),

    "v6_log_loss":
        float(df["v6_log_loss"].mean()),

    "log_loss_delta":
        float(
            df["v6_log_loss"].mean() -
            df["baseline_log_loss"].mean()
        ),

    "baseline_brier":
        float(df["baseline_brier"].mean()),

    "v6_brier":
        float(df["v6_brier"].mean()),

    "brier_delta":
        float(
            df["v6_brier"].mean() -
            df["baseline_brier"].mean()
        ),

    "baseline_top_pick_wins":
        baseline_top_wins,

    "v6_top_pick_wins":
        v6_top_wins,

    "baseline_top_pick_win_pct":
        round(
            baseline_top_wins /
            df["_race_group"].nunique() *
            100,
            2
        ),

    "v6_top_pick_win_pct":
        round(
            v6_top_wins /
            df["_race_group"].nunique() *
            100,
            2
        ),

    "status":
        "V6_VS_TEMPERATURE6_REPLAY_COMPLETE_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)
df.to_csv(OUT, index=False)

print("[V6_VS_TEMPERATURE6_REPLAY] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
