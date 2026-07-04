from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

REPLAY_PATH = DATA / "edgeiq_historical_replay_v1.csv"
TRUST_REPLAY_PATH = DATA / "edgeiq_trust_band_replay_v1.csv"

TABLE_OUT = DATA / "edgeiq_trust_band_contender_capture_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_trust_band_contender_capture_v1_summary.csv"

SUBSETS = [
    ("ALL", {"A_PLUS", "A", "B", "C", "D"}),
    ("A_PLUS_ONLY", {"A_PLUS"}),
    ("A_PLUS_A", {"A_PLUS", "A"}),
    ("A_PLUS_A_B", {"A_PLUS", "A", "B"}),
    ("A_PLUS_A_B_C", {"A_PLUS", "A", "B", "C"}),
    ("DROPPED_D_ONLY", {"D"}),
]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def build_join_key(df: pd.DataFrame) -> pd.Series:
    race_no = pd.to_numeric(df["race_no"], errors="coerce").fillna(-1).astype(int).astype(str)
    return df["meeting_date"].astype(str).str[:10] + "|" + df["track"].map(normalize_track) + "|" + race_no


def load_replay() -> pd.DataFrame:
    if not REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing replay file: {REPLAY_PATH}")
    usecols = ["meeting_date", "track", "race_no", "race_key", "horse", "runner_rank", "won"]
    df = pd.read_csv(REPLAY_PATH, low_memory=False, usecols=usecols)
    df["meeting_date"] = df["meeting_date"].fillna("").astype(str).str[:10]
    df["track"] = df["track"].fillna("").astype(str)
    df["horse"] = df["horse"].fillna("").astype(str)
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce")
    df["runner_rank"] = pd.to_numeric(df["runner_rank"], errors="coerce")
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["join_key_v1"] = build_join_key(df)
    return df.copy()


def load_trust_replay() -> pd.DataFrame:
    if not TRUST_REPLAY_PATH.exists():
        raise FileNotFoundError(f"Missing trust replay file: {TRUST_REPLAY_PATH}")
    usecols = ["meeting_date", "track", "race_no", "trust_band_v1", "trust_index_v1"]
    df = pd.read_csv(TRUST_REPLAY_PATH, low_memory=False, usecols=usecols)
    df["meeting_date"] = df["meeting_date"].fillna("").astype(str).str[:10]
    df["track"] = df["track"].fillna("").astype(str)
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce")
    df["trust_band_v1"] = df["trust_band_v1"].fillna("UNMATCHED").astype(str)
    df["trust_index_v1"] = pd.to_numeric(df["trust_index_v1"], errors="coerce")
    df["join_key_v1"] = build_join_key(df)
    race_level = (
        df.groupby("join_key_v1", dropna=False)
        .agg(
            trust_band_v1=("trust_band_v1", "first"),
            trust_index_v1=("trust_index_v1", "first"),
        )
        .reset_index()
    )
    return race_level


def calculate_subset_metrics(df: pd.DataFrame, subset_name: str, included_bands: set[str], all_races: int, all_winners: int, all_metrics: dict[str, float]) -> dict[str, object]:
    subset = df[df["trust_band_v1"].isin(included_bands)].copy()
    races = int(subset["join_key_v1"].nunique())
    race_retention_pct = (races / all_races) if all_races else math.nan

    winners = subset[subset["won"].eq(1)].copy()
    winner_rows = int(len(winners))
    winner_retention_pct = (winner_rows / all_winners) if all_winners else math.nan
    winner_top1_rate = float(winners["runner_rank"].le(1).mean()) if winner_rows else math.nan
    winner_top3_rate = float(winners["runner_rank"].le(3).mean()) if winner_rows else math.nan
    winner_top5_rate = float(winners["runner_rank"].le(5).mean()) if winner_rows else math.nan
    winner_top10_rate = float(winners["runner_rank"].le(10).mean()) if winner_rows else math.nan
    avg_winner_rank = float(winners["runner_rank"].mean()) if winner_rows else math.nan

    return {
        "subset_name": subset_name,
        "included_trust_bands": "|".join(sorted(included_bands)),
        "races": races,
        "race_retention_pct": race_retention_pct,
        "winner_rows": winner_rows,
        "winner_retention_pct": winner_retention_pct,
        "winner_top1_rate": winner_top1_rate,
        "winner_top3_rate": winner_top3_rate,
        "winner_top5_rate": winner_top5_rate,
        "winner_top10_rate": winner_top10_rate,
        "avg_winner_rank": avg_winner_rank,
        "improvement_vs_all_top1": winner_top1_rate - all_metrics["winner_top1_rate"] if pd.notna(winner_top1_rate) else math.nan,
        "improvement_vs_all_top3": winner_top3_rate - all_metrics["winner_top3_rate"] if pd.notna(winner_top3_rate) else math.nan,
        "improvement_vs_all_top5": winner_top5_rate - all_metrics["winner_top5_rate"] if pd.notna(winner_top5_rate) else math.nan,
        "improvement_vs_all_avg_rank": all_metrics["avg_winner_rank"] - avg_winner_rank if pd.notna(avg_winner_rank) else math.nan,
    }


def build_summary(table_df: pd.DataFrame) -> pd.DataFrame:
    summary_rows: list[dict[str, object]] = []

    all_row = table_df[table_df["subset_name"] == "ALL"].iloc[0]
    non_all = table_df[table_df["subset_name"] != "ALL"].copy()

    best_top1 = non_all.sort_values(["winner_top1_rate", "races"], ascending=[False, False]).iloc[0]
    best_avg_rank = non_all.sort_values(["avg_winner_rank", "races"], ascending=[True, False]).iloc[0]

    tradeoff_pool = non_all[non_all["race_retention_pct"].ge(0.50)].copy()
    if tradeoff_pool.empty:
        tradeoff_row = best_top1
    else:
        tradeoff_row = tradeoff_pool.sort_values(["winner_top1_rate", "races"], ascending=[False, False]).iloc[0]

    dropped_d_row = table_df[table_df["subset_name"] == "A_PLUS_A_B_C"].iloc[0]
    d_only_row = table_df[table_df["subset_name"] == "DROPPED_D_ONLY"].iloc[0]

    summary_rows.extend(
        [
            {"metric": "all_races", "value": int(all_row["races"])},
            {"metric": "all_winner_rows", "value": int(all_row["winner_rows"])},
            {"metric": "baseline_top1", "value": float(all_row["winner_top1_rate"])},
            {"metric": "baseline_top3", "value": float(all_row["winner_top3_rate"])},
            {"metric": "baseline_top5", "value": float(all_row["winner_top5_rate"])},
            {"metric": "baseline_avg_winner_rank", "value": float(all_row["avg_winner_rank"])},
            {"metric": "best_top1_subset", "value": best_top1["subset_name"]},
            {"metric": "best_top1_rate", "value": float(best_top1["winner_top1_rate"])},
            {"metric": "best_avg_rank_subset", "value": best_avg_rank["subset_name"]},
            {"metric": "best_avg_rank", "value": float(best_avg_rank["avg_winner_rank"])},
            {"metric": "best_tradeoff_subset_ge_50pct_retention", "value": tradeoff_row["subset_name"]},
            {"metric": "best_tradeoff_subset_top1", "value": float(tradeoff_row["winner_top1_rate"])},
            {"metric": "best_tradeoff_subset_race_retention_pct", "value": float(tradeoff_row["race_retention_pct"])},
            {"metric": "drop_d_subset", "value": dropped_d_row["subset_name"]},
            {"metric": "drop_d_top1_improvement", "value": float(dropped_d_row["improvement_vs_all_top1"])},
            {"metric": "drop_d_top3_improvement", "value": float(dropped_d_row["improvement_vs_all_top3"])},
            {"metric": "drop_d_top5_improvement", "value": float(dropped_d_row["improvement_vs_all_top5"])},
            {"metric": "drop_d_avg_rank_improvement", "value": float(dropped_d_row["improvement_vs_all_avg_rank"])},
            {"metric": "drop_d_race_retention_pct", "value": float(dropped_d_row["race_retention_pct"])},
            {"metric": "d_only_top1_rate", "value": float(d_only_row["winner_top1_rate"])},
            {"metric": "d_only_race_retention_pct", "value": float(d_only_row["race_retention_pct"])},
        ]
    )

    return pd.DataFrame(summary_rows)


def main() -> None:
    replay_df = load_replay()
    trust_df = load_trust_replay()
    merged = replay_df.merge(trust_df, on="join_key_v1", how="left")
    merged["trust_band_v1"] = merged["trust_band_v1"].fillna("UNMATCHED")

    all_races = int(merged["join_key_v1"].nunique())
    all_winners = int(merged["won"].sum())

    all_winners_df = merged[merged["won"].eq(1)].copy()
    all_metrics = {
        "winner_top1_rate": float(all_winners_df["runner_rank"].le(1).mean()),
        "winner_top3_rate": float(all_winners_df["runner_rank"].le(3).mean()),
        "winner_top5_rate": float(all_winners_df["runner_rank"].le(5).mean()),
        "winner_top10_rate": float(all_winners_df["runner_rank"].le(10).mean()),
        "avg_winner_rank": float(all_winners_df["runner_rank"].mean()),
    }

    rows = [calculate_subset_metrics(merged, name, bands, all_races, all_winners, all_metrics) for name, bands in SUBSETS]
    table_df = pd.DataFrame(rows)
    table_df.to_csv(TABLE_OUT, index=False)

    summary_df = build_summary(table_df)
    summary_df.to_csv(SUMMARY_OUT, index=False)

    print("[EDGEIQ_TRUST_BAND_CONTENDER_CAPTURE_V1] COMPLETE")
    print(f"races={all_races}")
    print(f"winner_rows={all_winners}")
    best_top1 = table_df.sort_values(["winner_top1_rate", "races"], ascending=[False, False]).iloc[0]
    print(f"best_top1_subset={best_top1['subset_name']}")
    print(f"best_top1_rate={float(best_top1['winner_top1_rate']):.6f}")
    print(f"table_out={TABLE_OUT}")
    print(f"summary_out={SUMMARY_OUT}")


if __name__ == "__main__":
    main()
