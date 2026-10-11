#!/usr/bin/env python3
"""Issue #16 read-only predictive diagnostics for frozen 2019/2020 HGB.

No fitting, tuning, recalibration, market data, Stage011 edits, or production
changes. Reads committed Issue #14 predictions and the local PIT matrix.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PREDICTIONS = "outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_OOS_PREDICTIONS.csv"
PIT_MATRIX = "outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv"
RUNNER_PARTITION = "outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_RUNNER_PARTITION.csv"
ISSUE14_RESULTS = "outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_RESULTS.json"

JOIN_COLS = ["year", "race_key", "runner_key"]
PIT_COLS = JOIN_COLS + [
    "field_size",
    "barrier",
    "barrier_position_pct",
    "distance_metres",
    "weight",
    "horse_prior_starts",
    "horse_no_prior_history",
    "trainer_id_missing",
    "jockey_id_missing",
]
RUNNER_PARTITION_COLS = JOIN_COLS + ["source_file", "race_eligible", "scratched", "winner"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def race_metrics(df: pd.DataFrame) -> dict:
    race_ll = []
    uniform_ll = []
    ranks = []
    winner_probs = []
    uniform_brier = []
    for _, g in df.groupby("race_key", sort=False):
        g = g.sort_values(["p_model", "runner_key"], ascending=[False, True]).reset_index(drop=True)
        winner_idx = np.flatnonzero(g["y"].to_numpy(dtype=int) == 1)
        if len(winner_idx) != 1:
            raise RuntimeError("Race without exactly one winner in diagnostic input")
        idx = int(winner_idx[0])
        p = float(g.loc[idx, "p_model"])
        race_ll.append(-math.log(max(p, 1e-15)))
        uniform_ll.append(math.log(len(g)))
        ranks.append(idx + 1)
        winner_probs.append(p)
        uniform_p = 1.0 / len(g)
        uniform_brier.extend((uniform_p - g["y"].to_numpy(dtype=float)) ** 2)
    ranks_arr = np.asarray(ranks, dtype=float)
    return {
        "runners": int(len(df)),
        "races": int(df["race_key"].nunique()),
        "race_log_loss": float(np.mean(race_ll)),
        "uniform_race_log_loss": float(np.mean(uniform_ll)),
        "race_log_loss_gain_vs_uniform": float(np.mean(uniform_ll) - np.mean(race_ll)),
        "runner_brier": float(((df["p_model"] - df["y"]) ** 2).mean()),
        "uniform_runner_brier": float(np.mean(uniform_brier)),
        "runner_brier_gain_vs_uniform": float(np.mean(uniform_brier) - ((df["p_model"] - df["y"]) ** 2).mean()),
        "top1": float(np.mean(ranks_arr <= 1)),
        "top3": float(np.mean(ranks_arr <= 3)),
        "mrr": float(np.mean(1.0 / ranks_arr)),
        "mean_winner_rank": float(np.mean(ranks_arr)),
        "mean_winner_probability": float(np.mean(winner_probs)),
    }


def per_race_frame(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for race_key, g in df.groupby("race_key", sort=False):
        g = g.sort_values(["p_model", "runner_key"], ascending=[False, True]).reset_index(drop=True)
        winner_idx = np.flatnonzero(g["y"].to_numpy(dtype=int) == 1)
        if len(winner_idx) != 1:
            raise RuntimeError(f"Race {race_key} not exactly one winner")
        idx = int(winner_idx[0])
        p = float(g.loc[idx, "p_model"])
        uniform_p = 1.0 / len(g)
        rows.append(
            {
                "year": int(g.loc[0, "year"]),
                "race_key": race_key,
                "field_size": int(len(g)),
                "winner_rank": idx + 1,
                "winner_probability": p,
                "race_log_loss": -math.log(max(p, 1e-15)),
                "uniform_race_log_loss": math.log(len(g)),
                "top1": int(idx == 0),
                "top3": int(idx <= 2),
                "runner_brier": float(((g["p_model"] - g["y"]) ** 2).mean()),
                "uniform_runner_brier": float(((uniform_p - g["y"]) ** 2).mean()),
            }
        )
    return pd.DataFrame(rows)


def bootstrap_ci(race_df: pd.DataFrame, seed: int = 1601, reps: int = 2000) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for year, g in race_df.groupby("year"):
        n = len(g)
        metrics = {
            "ll_gain_vs_uniform": (g["uniform_race_log_loss"] - g["race_log_loss"]).to_numpy(float),
            "brier_gain_vs_uniform": (g["uniform_runner_brier"] - g["runner_brier"]).to_numpy(float),
            "top1": g["top1"].to_numpy(float),
            "top3": g["top3"].to_numpy(float),
        }
        for metric, values in metrics.items():
            samples = np.empty(reps)
            for i in range(reps):
                idx = rng.integers(0, n, size=n)
                samples[i] = values[idx].mean()
            rows.append(
                {
                    "year": int(year),
                    "metric": metric,
                    "observed": float(values.mean()),
                    "ci_low_2_5": float(np.quantile(samples, 0.025)),
                    "ci_high_97_5": float(np.quantile(samples, 0.975)),
                    "bootstrap_reps": reps,
                    "race_blocks": n,
                }
            )
    return rows


def calibration(df: pd.DataFrame) -> list[dict]:
    bins = [0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.0]
    tmp = df.copy()
    tmp["prob_band"] = pd.cut(tmp["p_model"], bins=bins, include_lowest=True, right=True)
    rows = []
    for (year, band), g in tmp.groupby(["year", "prob_band"], observed=False):
        if g.empty:
            rows.append({"year": int(year), "prob_band": str(band), "rows": 0, "winners": 0, "mean_p": "", "win_rate": "", "calibration_error": "", "brier": ""})
        else:
            mean_p = float(g["p_model"].mean())
            win_rate = float(g["y"].mean())
            rows.append(
                {
                    "year": int(year),
                    "prob_band": str(band),
                    "rows": int(len(g)),
                    "winners": int(g["y"].sum()),
                    "mean_p": mean_p,
                    "win_rate": win_rate,
                    "calibration_error": win_rate - mean_p,
                    "brier": float(((g["p_model"] - g["y"]) ** 2).mean()),
                }
            )
    return rows


def ranking_diagnostics(df: pd.DataFrame) -> list[dict]:
    rows = []
    for year, ydf in df.groupby("year"):
        ranked = []
        for race_key, g in ydf.groupby("race_key", sort=False):
            g = g.sort_values(["p_model", "runner_key"], ascending=[False, True]).reset_index(drop=True)
            g["model_rank"] = np.arange(1, len(g) + 1)
            ranked.append(g)
        r = pd.concat(ranked, ignore_index=True)
        for label, g in r.groupby(pd.cut(r["model_rank"], bins=[0, 1, 2, 3, 5, 10, 1000], include_lowest=True), observed=False):
            if g.empty:
                rows.append({"year": int(year), "rank_band": str(label), "rows": 0, "winners": 0, "mean_p": "", "win_rate": ""})
            else:
                rows.append(
                    {
                        "year": int(year),
                        "rank_band": str(label),
                        "rows": int(len(g)),
                        "winners": int(g["y"].sum()),
                        "mean_p": float(g["p_model"].mean()),
                        "win_rate": float(g["y"].mean()),
                    }
                )
    return rows


def cohort_performance(df: pd.DataFrame) -> list[dict]:
    rows = []
    work = df.copy()
    work["field_size_band"] = pd.cut(work["field_size"], bins=[0, 7, 10, 14, 40], labels=["small_<=7", "medium_8_10", "large_11_14", "very_large_15plus"])
    work["distance_band"] = pd.cut(work["distance_metres"], bins=[0, 1200, 1600, 2200, 10000], labels=["sprint_<=1200", "mileish_1201_1600", "middle_1601_2200", "staying_2201plus"])
    work["horse_history_band"] = np.where(work["horse_no_prior_history"].fillna(0).astype(float).eq(1), "no_prior", "prior_history")
    cohort_defs = [
        ("field_size_band", "field_size"),
        ("distance_band", "distance"),
        ("horse_history_band", "horse_history"),
        ("jockey_id_missing", "jockey_missing"),
        ("trainer_id_missing", "trainer_missing"),
    ]
    for col, family in cohort_defs:
        for (year, value), g in work.groupby(["year", col], observed=False):
            if g.empty:
                continue
            m = race_metrics(g) if col in {"field_size_band", "distance_band"} else {
                "runners": int(len(g)),
                "races": int(g["race_key"].nunique()),
                "runner_brier": float(((g["p_model"] - g["y"]) ** 2).mean()),
                "uniform_runner_brier": float(((1 / g["field_size"] - g["y"]) ** 2).mean()),
                "runner_brier_gain_vs_uniform": float(((1 / g["field_size"] - g["y"]) ** 2).mean() - ((g["p_model"] - g["y"]) ** 2).mean()),
            }
            rows.append({"year": int(year), "family": family, "cohort": str(value), **m})
    return rows


def missing_integrity(df: pd.DataFrame) -> list[dict]:
    rows = []
    checks = {
        "barrier_missing": df["barrier"].isna(),
        "weight_missing": df["weight"].isna(),
        "jockey_id_missing": df["jockey_id_missing"].fillna(0).astype(float).eq(1),
    }
    for name, mask in checks.items():
        g = df[mask].copy()
        for year, ydf in g.groupby("year"):
            race_counts = ydf.groupby("race_key").size()
            winner_races = ydf.loc[ydf["y"].eq(1), "race_key"].nunique()
            rows.append(
                {
                    "year": int(year),
                    "missing_group": name,
                    "rows": int(len(ydf)),
                    "races_affected": int(ydf["race_key"].nunique()),
                    "winner_rows": int(ydf["y"].sum()),
                    "winner_races": int(winner_races),
                    "mean_p": float(ydf["p_model"].mean()) if len(ydf) else "",
                    "max_rows_in_one_race": int(race_counts.max()) if len(race_counts) else 0,
                    "races_all_runners_missing": int(sum(race_counts == df[df["race_key"].isin(race_counts.index)].groupby("race_key").size().reindex(race_counts.index))),
                }
            )
    return rows


def missing_affected_races(df: pd.DataFrame) -> list[dict]:
    rows = []
    checks = {
        "barrier_missing": df["barrier"].isna(),
        "weight_missing": df["weight"].isna(),
        "jockey_id_missing": df["jockey_id_missing"].fillna(0).astype(float).eq(1),
    }
    field_sizes = df.groupby("race_key").size()
    for name, mask in checks.items():
        for (year, race_key), g in df[mask].groupby(["year", "race_key"]):
            rows.append(
                {
                    "year": int(year),
                    "missing_group": name,
                    "race_key": race_key,
                    "missing_rows": int(len(g)),
                    "field_size": int(field_sizes.loc[race_key]),
                    "share_of_field_missing": float(len(g) / field_sizes.loc[race_key]),
                    "winner_rows_in_missing_group": int(g["y"].sum()),
                    "mean_p_missing_group": float(g["p_model"].mean()),
                    "max_p_missing_group": float(g["p_model"].max()),
                    "all_runners_missing": int(len(g) == field_sizes.loc[race_key]),
                }
            )
    return rows


def missing_provenance(df: pd.DataFrame, runner_path: Path) -> list[dict]:
    if not runner_path.is_file():
        return [{"status": "BLOCKED", "reason": f"runner partition not found: {runner_path}"}]
    affected_keys = df.loc[
        df["barrier"].isna()
        | df["weight"].isna()
        | df["jockey_id_missing"].fillna(0).astype(float).eq(1),
        JOIN_COLS,
    ].drop_duplicates()
    if affected_keys.empty:
        return []
    runner = pd.read_csv(runner_path, usecols=RUNNER_PARTITION_COLS)
    joined = affected_keys.merge(runner, on=JOIN_COLS, how="left", validate="one_to_one")
    rows = []
    for (year, source_file, race_eligible, scratched), g in joined.groupby(["year", "source_file", "race_eligible", "scratched"], dropna=False):
        rows.append(
            {
                "year": int(year),
                "source_file": source_file,
                "race_eligible": race_eligible,
                "scratched": scratched,
                "rows": int(len(g)),
                "winner_rows": int(pd.to_numeric(g["winner"], errors="coerce").fillna(0).sum()),
                "missing_join_rows": int(g["source_file"].isna().sum()),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", default=PREDICTIONS)
    parser.add_argument("--pit-matrix", default=PIT_MATRIX)
    parser.add_argument("--runner-partition", default=RUNNER_PARTITION)
    parser.add_argument("--issue14-results", default=ISSUE14_RESULTS)
    parser.add_argument("--out", default="outputs/research/issue14_predictive_diagnostics")
    args = parser.parse_args()

    pred_path = Path(args.predictions)
    pit_path = Path(args.pit_matrix)
    runner_path = Path(args.runner_partition)
    result_path = Path(args.issue14_results)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for path in (pred_path, pit_path, result_path):
        if not path.is_file():
            raise SystemExit(f"BLOCKED: missing input {path}")

    pred = pd.read_csv(pred_path)
    pit = pd.read_csv(pit_path, usecols=PIT_COLS)
    df = pred.merge(pit, on=JOIN_COLS, how="left", validate="one_to_one")
    if df[PIT_COLS].isna().all(axis=1).any():
        raise RuntimeError("PIT join failed for at least one prediction row")
    if set(df["year"].unique()) != {2019, 2020}:
        raise RuntimeError("Diagnostics input must contain only 2019/2020 predictions")

    race_df = per_race_frame(df)
    summary_rows = []
    for year, g in df.groupby("year"):
        summary_rows.append({"year": int(year), **race_metrics(g)})

    outputs = {
        "ISSUE16_YEAR_SUMMARY.csv": summary_rows,
        "ISSUE16_RACE_BLOCK_BOOTSTRAP.csv": bootstrap_ci(race_df),
        "ISSUE16_CALIBRATION_BY_PROB_BAND.csv": calibration(df),
        "ISSUE16_RANKING_DIAGNOSTICS.csv": ranking_diagnostics(df),
        "ISSUE16_COHORT_PERFORMANCE.csv": cohort_performance(df),
        "ISSUE16_MISSING_FIELD_INTEGRITY.csv": missing_integrity(df),
        "ISSUE16_MISSING_FIELD_AFFECTED_RACES.csv": missing_affected_races(df),
        "ISSUE16_MISSING_FIELD_PROVENANCE.csv": missing_provenance(df, runner_path),
    }
    for filename, rows in outputs.items():
        write_csv(out / filename, rows)

    with result_path.open("r", encoding="utf-8") as f:
        issue14 = json.load(f)
    manifest = {
        "status": "PASS_READ_ONLY_DIAGNOSTICS_COMPLETE",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_fitting": "NO",
        "model_scoring": "NO_NEW_MODEL_SCORING_USED_EXISTING_PREDICTIONS",
        "market_access": "NO",
        "sealed_2025_2026_access": "NO",
        "inputs": {
            "predictions": str(pred_path),
            "predictions_sha256": sha256_file(pred_path),
            "pit_matrix": str(pit_path),
            "pit_matrix_sha256": sha256_file(pit_path),
            "runner_partition": str(runner_path),
            "runner_partition_sha256": sha256_file(runner_path) if runner_path.is_file() else "",
            "issue14_results": str(result_path),
            "issue14_results_sha256": sha256_file(result_path),
        },
        "rows": int(len(df)),
        "races": int(df["race_key"].nunique()),
        "issue14_status": issue14.get("status"),
        "outputs": sorted(outputs),
        "next_pre_registered_hypothesis": "Audit and potentially replace the raw missing-field handling for 2019 missing barrier/weight/jockey rows with explicit source-provenance cohort flags only if Grok approves; do not tune model parameters or use market data.",
    }
    (out / "ISSUE16_DIAGNOSTIC_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "rows": manifest["rows"], "races": manifest["races"], "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
