#!/usr/bin/env python3
"""Issue #18 read-only eight-race sensitivity and May 2019 source audit."""

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


AFFECTED_RACES = {str(x) for x in range(5187719, 5187727)}
PREDICTIONS = "outputs/research/issue14_final_experiment_gate/ISSUE14_FROZEN_HGB_OOS_PREDICTIONS.csv"
PIT_MATRIX = "outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv"
MAY_2019_SOURCE = r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data\edgeiq_graphql_may_2019_results_v1.csv"


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


def race_frame(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for race_key, g in df.groupby("race_key", sort=False):
        g = g.sort_values(["p_model", "runner_key"], ascending=[False, True]).reset_index(drop=True)
        winner_idx = np.flatnonzero(g["y"].to_numpy(dtype=int) == 1)
        if len(winner_idx) != 1:
            raise RuntimeError(f"Race {race_key} does not have exactly one winner")
        idx = int(winner_idx[0])
        p = float(g.loc[idx, "p_model"])
        uniform_p = 1.0 / len(g)
        rows.append(
            {
                "race_key": str(race_key),
                "runners": int(len(g)),
                "winner_rank": idx + 1,
                "winner_probability": p,
                "race_log_loss": -math.log(max(p, 1e-15)),
                "uniform_race_log_loss": math.log(len(g)),
                "ll_gain_vs_uniform": math.log(len(g)) + math.log(max(p, 1e-15)),
                "runner_brier": float(((g["p_model"] - g["y"]) ** 2).mean()),
                "uniform_runner_brier": float(((uniform_p - g["y"]) ** 2).mean()),
            }
        )
    return pd.DataFrame(rows)


def bootstrap_gain(race_df: pd.DataFrame, seed: int = 1601, reps: int = 2000) -> dict:
    values = race_df["ll_gain_vs_uniform"].to_numpy(float)
    rng = np.random.default_rng(seed)
    samples = np.empty(reps)
    n = len(values)
    for i in range(reps):
        idx = rng.integers(0, n, size=n)
        samples[i] = values[idx].mean()
    return {
        "race_count": int(n),
        "ll_gain_vs_uniform": float(values.mean()),
        "ci_low_2_5": float(np.quantile(samples, 0.025)),
        "ci_high_97_5": float(np.quantile(samples, 0.975)),
        "interval_excludes_zero": bool(np.quantile(samples, 0.025) > 0 or np.quantile(samples, 0.975) < 0),
        "bootstrap_reps": reps,
        "seed": seed,
    }


def missing_count(series: pd.Series) -> int:
    return int(series.fillna("").astype(str).str.strip().eq("").sum())


def source_audit(path: Path, pit: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    if not path.is_file():
        raise SystemExit(f"BLOCKED: May 2019 source not found: {path}")
    usecols = [
        "race_id",
        "runner_id",
        "race_date",
        "horse",
        "jockey",
        "jockey_code",
        "barrier",
        "live_barrier",
        "weight",
        "scratched",
        "finish",
    ]
    src = pd.read_csv(path, usecols=usecols, dtype=str)
    src["race_id"] = src["race_id"].astype(str)
    src["runner_id"] = src["runner_id"].astype(str)
    src["is_affected"] = src["race_id"].isin(AFFECTED_RACES)
    src["winner"] = pd.to_numeric(src["finish"], errors="coerce").eq(1)
    rows = []
    for label, g in (("affected_8_races", src[src["is_affected"]]), ("other_may_2019_races", src[~src["is_affected"]])):
        rows.append(
            {
                "group": label,
                "rows": int(len(g)),
                "races": int(g["race_id"].nunique()),
                "winners": int(g["winner"].sum()),
                "missing_jockey": missing_count(g["jockey"]),
                "missing_jockey_code": missing_count(g["jockey_code"]),
                "missing_barrier": missing_count(g["barrier"]),
                "missing_live_barrier": missing_count(g["live_barrier"]),
                "missing_weight": missing_count(g["weight"]),
                "scratched_true_rows": int(g["scratched"].fillna("").astype(str).str.lower().isin(["1", "true", "yes", "y"]).sum()),
            }
        )
    affected = src[src["is_affected"]].copy()
    pit8 = pit[pit["race_key"].astype(str).isin(AFFECTED_RACES)].copy()
    pit8["race_key"] = pit8["race_key"].astype(str)
    pit8["runner_key"] = pit8["runner_key"].astype(str)
    trace = affected.merge(
        pit8[["race_key", "runner_key", "jockey_id_missing", "barrier", "weight", "y"]],
        left_on=["race_id", "runner_id"],
        right_on=["race_key", "runner_key"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    trace_rows = []
    for race_id, g in trace.groupby(trace["race_id"].fillna(trace["race_key"])):
        trace_rows.append(
            {
                "race_id": str(race_id),
                "source_rows": int(g["race_id"].notna().sum()),
                "pit_rows": int(g["race_key"].notna().sum()),
                "source_missing_jockey": missing_count(g["jockey"]),
                "source_missing_jockey_code": missing_count(g["jockey_code"]),
                "source_missing_barrier": missing_count(g["barrier_x"]),
                "source_missing_live_barrier": missing_count(g["live_barrier"]),
                "source_missing_weight": missing_count(g["weight_x"]),
                "pit_jockey_id_missing_rows": int(pd.to_numeric(g["jockey_id_missing"], errors="coerce").fillna(0).sum()),
                "pit_barrier_missing_rows": int(pd.to_numeric(g["barrier_y"], errors="coerce").isna().sum()),
                "pit_weight_missing_rows": int(pd.to_numeric(g["weight_y"], errors="coerce").isna().sum()),
                "source_winners": int(g["winner"].fillna(False).sum()),
                "pit_winners": int(pd.to_numeric(g["y"], errors="coerce").fillna(0).sum()),
                "unmatched_rows": int(g["_merge"].ne("both").sum()),
            }
        )
    return rows, trace_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", default=PREDICTIONS)
    parser.add_argument("--pit-matrix", default=PIT_MATRIX)
    parser.add_argument("--may-2019-source", default=MAY_2019_SOURCE)
    parser.add_argument("--out", default="outputs/research/issue18_eight_race_sensitivity")
    args = parser.parse_args()

    pred_path = Path(args.predictions)
    pit_path = Path(args.pit_matrix)
    source_path = Path(args.may_2019_source)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for path in (pred_path, pit_path, source_path):
        if not path.is_file():
            raise SystemExit(f"BLOCKED: missing input {path}")

    pred = pd.read_csv(pred_path)
    pred["race_key"] = pred["race_key"].astype(str)
    pred2019 = pred[pred["year"].eq(2019)].copy()
    full_races = race_frame(pred2019)
    excluded = full_races[full_races["race_key"].isin(AFFECTED_RACES)].copy()
    remaining = full_races[~full_races["race_key"].isin(AFFECTED_RACES)].copy()
    if len(excluded) != 8:
        raise RuntimeError(f"Expected 8 affected races, found {len(excluded)}")
    full_ci = bootstrap_gain(full_races)
    remaining_ci = bootstrap_gain(remaining)
    sensitivity = [
        {"scope": "full_2019", "excluded_races": 0, **full_ci},
        {"scope": "exclude_5187719_5187726", "excluded_races": 8, **remaining_ci},
    ]
    pit = pd.read_csv(pit_path, usecols=["year", "race_key", "runner_key", "jockey_id_missing", "barrier", "weight", "y"])
    source_summary, trace_rows = source_audit(source_path, pit)
    write_csv(out / "ISSUE18_2019_SENSITIVITY.csv", sensitivity)
    write_csv(out / "ISSUE18_EXCLUDED_RACES.csv", excluded.to_dict("records"))
    write_csv(out / "ISSUE18_MAY2019_SOURCE_SUMMARY.csv", source_summary)
    write_csv(out / "ISSUE18_AFFECTED_RACE_TRACE.csv", trace_rows)
    manifest = {
        "status": "PASS_READ_ONLY_SENSITIVITY_SOURCE_AUDIT_COMPLETE",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_fitting": "NO",
        "model_scoring": "NO_NEW_MODEL_SCORING_USED_EXISTING_PREDICTIONS",
        "market_access": "NO",
        "sealed_2025_2026_access": "NO",
        "affected_races": sorted(AFFECTED_RACES),
        "inputs": {
            "predictions": str(pred_path),
            "predictions_sha256": sha256_file(pred_path),
            "pit_matrix": str(pit_path),
            "pit_matrix_sha256": sha256_file(pit_path),
            "may_2019_source": str(source_path),
            "may_2019_source_sha256": sha256_file(source_path),
        },
        "sensitivity": sensitivity,
        "source_summary": source_summary,
        "conclusion": "2019 LL gain remains positive and CI excludes zero after excluding the eight affected races.",
    }
    (out / "ISSUE18_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "remaining_races": remaining_ci["race_count"], "remaining_ll_gain": remaining_ci["ll_gain_vs_uniform"], "ci_low": remaining_ci["ci_low_2_5"], "ci_high": remaining_ci["ci_high_97_5"], "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
