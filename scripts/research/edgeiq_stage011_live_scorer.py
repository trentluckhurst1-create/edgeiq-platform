from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


FEATURES = [
    "current_distance",
    "hist_runs",
    "lvs_last1",
    "lvs_mean3",
    "lvs_mean5",
    "lvs_median5",
    "lvs_std5",
    "lvs_peak",
    "lvs_worst5",
    "margin_mean5",
    "margin_std5",
    "margin_worst5",
    "margin_last1",
    "margin_last2",
    "last_distance",
    "margin_change_l1_l2",
    "margin_per_runner_last1",
    "margin_per_runner_last2",
    "days_since_last",
    "dist200_runs",
    "dist200_lvs_mean",
    "dist200_lvs_best",
    "represented_field_size",
    "barrier_position_pct",
    "jockey_prior_starts",
    "jockey_prior_win_rate",
    "jockey_prior_top3_rate",
    "trainer_prior_starts",
    "trainer_prior_win_rate",
    "trainer_prior_top3_rate",
    "clean_finish_mean5",
    "clean_last_finish",
    "clean_last_won",
    "clean_last_top3",
    "clean_finish_hist_n",
]

FEATURE_SHA256 = hashlib.sha256(
    json.dumps(FEATURES, separators=(",", ":")).encode()
).hexdigest()

FORBIDDEN = {
    "y",
    "winner",
    "won",
    "result",
    "result_position",
    "finish_position",
    "finishing_position",
    "outcome",
    "sp",
    "bsp",
    "market_price",
    "starting_price",
    "fixed_odds",
    "betfair_price",
}

REQUIRED = {"race_id", "runner_id", "scoring_timestamp", "scratch_status"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def softmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite raw scores")
    shifted = values - values.max()
    exp_values = np.exp(shifted)
    return exp_values / exp_values.sum()


def score_stage011(
    model_path: Path,
    features_path: Path,
    output_path: Path,
    expected_model_sha256: str,
    expected_feature_sha256: str,
) -> dict:
    if expected_feature_sha256.lower() != FEATURE_SHA256:
        raise RuntimeError("Feature manifest SHA256 mismatch")

    actual_model_hash = sha256_file(model_path)
    if actual_model_hash != expected_model_sha256.lower():
        raise RuntimeError("Model artifact SHA256 mismatch")

    model = joblib.load(model_path)
    if not hasattr(model, "decision_function"):
        raise RuntimeError("Model has no decision_function")

    frame = pd.read_csv(features_path)
    missing = (REQUIRED | set(FEATURES)) - set(frame.columns)
    if missing:
        raise RuntimeError(f"Missing columns: {sorted(missing)}")

    prohibited = FORBIDDEN & {c.lower() for c in frame.columns}
    if prohibited:
        raise RuntimeError(f"Forbidden columns: {sorted(prohibited)}")

    if frame.empty:
        raise RuntimeError("Empty feature matrix")
    if frame[["race_id", "runner_id"]].isna().any().any():
        raise RuntimeError("Missing runner identity")
    if frame.duplicated(["race_id", "runner_id"]).any():
        raise RuntimeError("Duplicate race/runner identity")
    if not frame["scratch_status"].eq("ACTIVE").all():
        raise RuntimeError("Inactive or scratched runners included")

    pd.to_datetime(frame["scoring_timestamp"], utc=True, errors="raise")
    for race_id, group in frame.groupby("race_id", sort=False):
        if len(group) < 2:
            raise RuntimeError(f"Race has fewer than 2 runners: {race_id}")

    X = frame[FEATURES].apply(pd.to_numeric, errors="raise")
    X = X.replace([np.inf, -np.inf], np.nan)
    if X.notna().sum().sum() == 0:
        raise RuntimeError("All feature values missing")

    if hasattr(model, "feature_names_in_") and list(model.feature_names_in_) != FEATURES:
        raise RuntimeError("Fitted model feature order mismatch")

    raw = np.asarray(model.decision_function(X), dtype=float)
    if raw.ndim != 1 or len(raw) != len(frame):
        raise RuntimeError("Invalid model score dimensions")

    scored = frame[["race_id", "runner_id", "scoring_timestamp", "scratch_status"]].copy()
    scored["raw"] = raw
    scored["probability"] = scored.groupby("race_id", sort=False)["raw"].transform(
        lambda s: softmax(s.to_numpy())
    )

    mass = scored.groupby("race_id")["probability"].sum()
    if not np.allclose(mass.to_numpy(), 1.0, atol=1e-12, rtol=0):
        raise RuntimeError("Probability mass violation")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    scored[
        ["race_id", "runner_id", "probability", "scoring_timestamp", "scratch_status"]
    ].to_csv(output_path, index=False)

    return {
        "status": "STAGE011_SCORING_PASS",
        "races": int(scored["race_id"].nunique()),
        "runners": int(len(scored)),
        "feature_manifest_sha256": FEATURE_SHA256,
        "model_sha256": actual_model_hash,
        "probability_mass_max_abs_error": float((mass - 1.0).abs().max()),
        "output": str(output_path),
        "prospective_publication_attested": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--features", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-model-sha256", required=True)
    parser.add_argument("--expected-feature-sha256", required=True)
    args = parser.parse_args()

    result = score_stage011(
        Path(args.model),
        Path(args.features),
        Path(args.output),
        args.expected_model_sha256,
        args.expected_feature_sha256,
    )
    for key, value in result.items():
        print(f"{key.upper()}={value}")


if __name__ == "__main__":
    main()
