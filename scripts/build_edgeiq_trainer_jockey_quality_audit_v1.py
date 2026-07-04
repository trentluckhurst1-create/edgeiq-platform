from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_trainer_jockey_runner_history_v1.csv"

OUT_TRAINER = DATA / "edgeiq_trainer_quality_audit_v1.csv"
OUT_JOCKEY = DATA / "edgeiq_jockey_quality_audit_v1.csv"
OUT_COMBO = DATA / "edgeiq_trainer_jockey_combo_quality_audit_v1.csv"
OUT_YEAR = DATA / "edgeiq_trainer_jockey_quality_by_year_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_quality_summary_v1.csv"
OUT_AUDIT = DATA / "edgeiq_trainer_jockey_quality_audit_v1.json"


def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def num(s):
    return pd.to_numeric(s, errors="coerce")


def entity_table(df, group_cols, entity_type, min_starts):
    g = (
        df.groupby(group_cols, dropna=False)
        .agg(
            starts=("is_runner", "sum"),
            wins=("won_v1_num", "sum"),
            places=("placed_v1_num", "sum"),
            races=("race_key_v1", "nunique"),
            horses=("horse_key", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
        )
        .reset_index()
    )

    g["win_pct"] = np.where(g["starts"] > 0, g["wins"] / g["starts"] * 100, 0).round(2)
    g["place_pct"] = np.where(g["starts"] > 0, g["places"] / g["starts"] * 100, 0).round(2)

    g["sample_band"] = np.select(
        [
            g["starts"] >= 500,
            g["starts"] >= 250,
            g["starts"] >= 100,
            g["starts"] >= 50,
            g["starts"] >= 20,
        ],
        ["A_500_PLUS", "B_250_499", "C_100_249", "D_50_99", "E_20_49"],
        default="F_UNDER_20",
    )

    g["meets_min_threshold"] = np.where(g["starts"] >= min_starts, "YES", "NO")
    g["entity_type"] = entity_type

    return g.sort_values(["starts", "wins"], ascending=[False, False])


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT, low_memory=False)

    required = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "trainer",
        "trainer_key",
        "jockey",
        "jockey_key",
        "finish_position_v1",
        "won_v1",
        "placed_v1",
        "race_key_v1",
        "trainer_jockey_key_v1",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["trainer_norm"] = df["trainer"].map(norm)
    df["jockey_norm"] = df["jockey"].map(norm)
    df["trainer_key_norm"] = df["trainer_key"].map(norm)
    df["jockey_key_norm"] = df["jockey_key"].map(norm)
    df["horse_key"] = df["horse_key"].map(norm)
    df["race_key_v1"] = df["race_key_v1"].map(norm)
    df["trainer_jockey_combo"] = df["trainer_norm"] + " + " + df["jockey_norm"]

    df["won_v1_num"] = num(df["won_v1"]).fillna(0).astype(int)
    df["placed_v1_num"] = num(df["placed_v1"]).fillna(0).astype(int)
    df["finish_position_num"] = num(df["finish_position_v1"])
    df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year

    # Count all runners, including SCR/TBC/no finish rows, as starts only when they have a finish position.
    # This prevents scratched/non-runner rows from polluting strike rates.
    df["is_runner"] = np.where(df["finish_position_num"].notna(), 1, 0)

    runner_df = df[df["is_runner"] == 1].copy()

    trainer = entity_table(runner_df, ["trainer_norm", "trainer_key_norm"], "TRAINER", 100)
    jockey = entity_table(runner_df, ["jockey_norm", "jockey_key_norm"], "JOCKEY", 100)
    combo = entity_table(
        runner_df,
        ["trainer_norm", "jockey_norm", "trainer_key_norm", "jockey_key_norm", "trainer_jockey_combo"],
        "TRAINER_JOCKEY_COMBO",
        50,
    )

    by_year = (
        runner_df.groupby("year", dropna=False)
        .agg(
            runner_rows=("is_runner", "sum"),
            races=("race_key_v1", "nunique"),
            horses=("horse_key", "nunique"),
            trainers=("trainer_key_norm", "nunique"),
            jockeys=("jockey_key_norm", "nunique"),
            wins=("won_v1_num", "sum"),
            places=("placed_v1_num", "sum"),
        )
        .reset_index()
        .sort_values("year")
    )

    summary = pd.DataFrame(
        [
            ["raw_rows", len(df)],
            ["runner_rows_used", len(runner_df)],
            ["non_runner_or_no_finish_rows_excluded", int((df["is_runner"] == 0).sum())],
            ["unique_races", runner_df["race_key_v1"].nunique()],
            ["unique_horses", runner_df["horse_key"].nunique()],
            ["unique_trainers", runner_df["trainer_key_norm"].nunique()],
            ["unique_jockeys", runner_df["jockey_key_norm"].nunique()],
            ["unique_trainer_jockey_combos", runner_df["trainer_jockey_combo"].nunique()],
            ["total_wins", int(runner_df["won_v1_num"].sum())],
            ["total_places", int(runner_df["placed_v1_num"].sum())],
            ["trainer_missing_pct", round((runner_df["trainer_norm"].eq("").mean() * 100), 4)],
            ["jockey_missing_pct", round((runner_df["jockey_norm"].eq("").mean() * 100), 4)],
            ["finish_column_used", "finish_position_v1"],
            ["win_column_used", "won_v1"],
            ["place_column_used", "placed_v1"],
            ["trainer_min_100_count", int((trainer["starts"] >= 100).sum())],
            ["jockey_min_100_count", int((jockey["starts"] >= 100).sum())],
            ["combo_min_50_count", int((combo["starts"] >= 50).sum())],
        ],
        columns=["metric", "value"],
    )

    trainer.to_csv(OUT_TRAINER, index=False)
    jockey.to_csv(OUT_JOCKEY, index=False)
    combo.to_csv(OUT_COMBO, index=False)
    by_year.to_csv(OUT_YEAR, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    audit = {
        "status": "COMPLETE",
        "input": str(INPUT),
        "runner_rows_used": int(len(runner_df)),
        "excluded_no_finish_rows": int((df["is_runner"] == 0).sum()),
        "outputs": {
            "trainer": str(OUT_TRAINER),
            "jockey": str(OUT_JOCKEY),
            "combo": str(OUT_COMBO),
            "by_year": str(OUT_YEAR),
            "summary": str(OUT_SUMMARY),
        },
    }

    OUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_QUALITY_AUDIT_V1] COMPLETE")
    print(f"raw_rows={len(df)}")
    print(f"runner_rows_used={len(runner_df)}")
    print(f"excluded_no_finish_rows={(df['is_runner'] == 0).sum()}")
    print(f"races={runner_df['race_key_v1'].nunique()}")
    print(f"trainers={runner_df['trainer_key_norm'].nunique()}")
    print(f"jockeys={runner_df['jockey_key_norm'].nunique()}")
    print(f"combos={runner_df['trainer_jockey_combo'].nunique()}")
    print(f"wins={int(runner_df['won_v1_num'].sum())}")
    print(f"trainer_min_100={(trainer['starts'] >= 100).sum()}")
    print(f"jockey_min_100={(jockey['starts'] >= 100).sum()}")
    print(f"combo_min_50={(combo['starts'] >= 50).sum()}")


if __name__ == "__main__":
    main()
