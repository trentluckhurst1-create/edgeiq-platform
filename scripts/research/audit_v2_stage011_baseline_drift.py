from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


DEFAULT_SCORES_DIR = Path("outputs/research/model_v2/stage011_reproduction")
DEFAULT_YEARS = (2022, 2023, 2024)
MASS_TOLERANCE = 1e-12

STAGE011_SCORE_PROVENANCE_COLUMNS = {
    "_race",
    "_horse",
    "race_date",
    "evaluation_year",
    "training_year_max",
    "y",
    "raw",
    "p",
    "evidence_class",
    "model_name",
    "model_seed",
    "feature_manifest_sha256",
    "source_stage006_sha256",
    "source_d45_sha256",
    "source_perf026_sha256",
}

LEGACY_WINNER_COLUMNS = (
    "winner",
    "is_winner",
    "won",
    "winner_flag",
    "finish_winner",
)


def _format_missing(missing: Iterable[str]) -> str:
    return "[" + ", ".join(sorted(missing)) + "]"


def detect_winner_column(columns: Iterable[str]) -> str:
    """Return the certified winner column for Stage011 score artifacts.

    The Stage011 score-file contract uses ``y`` for the binary winner target.
    Accepting that short name is only safe when the rest of the Stage011
    provenance schema is present, so this detector fails closed otherwise.
    """

    cols = list(columns)
    colset = set(cols)
    legacy_matches = [c for c in LEGACY_WINNER_COLUMNS if c in colset]

    if "y" in colset:
        missing = STAGE011_SCORE_PROVENANCE_COLUMNS - colset
        if missing:
            raise RuntimeError(
                "STOP_Y_WITHOUT_STAGE011_PROVENANCE: "
                f"missing={_format_missing(missing)}; columns={cols}"
            )
        if legacy_matches:
            raise RuntimeError(
                "STOP_AMBIGUOUS_WINNER_COLUMN: "
                f"candidates={['y'] + legacy_matches}; columns={cols}"
            )
        return "y"

    if len(legacy_matches) == 1:
        return legacy_matches[0]

    raise RuntimeError(
        "STOP_AMBIGUOUS_WINNER_COLUMN: "
        f"candidates={legacy_matches}; columns={cols}"
    )


def validate_stage011_score_frame(df: pd.DataFrame, source_name: str = "<frame>") -> dict:
    required = {"_race", "_horse", "p"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(
            f"STOP_MISSING_SCORE_FIELDS: source={source_name}; "
            f"missing={_format_missing(missing)}"
        )

    winner_col = detect_winner_column(df.columns)
    if df.empty:
        raise RuntimeError(f"STOP_EMPTY_SCORE_FILE: source={source_name}")

    keys = df[["_race", "_horse"]]
    if keys.isna().any().any():
        raise RuntimeError(f"STOP_NULL_RUNNER_KEYS: source={source_name}")
    if df.duplicated(["_race", "_horse"]).any():
        raise RuntimeError(f"STOP_DUPLICATE_RUNNER_KEYS: source={source_name}")

    winner = pd.to_numeric(df[winner_col], errors="coerce")
    if winner.isna().any():
        raise RuntimeError(f"STOP_WINNER_NULL_OR_NON_NUMERIC: source={source_name}")
    if not winner.isin([0, 1]).all():
        raise RuntimeError(f"STOP_WINNER_NOT_BINARY: source={source_name}")

    winner_counts = winner.groupby(df["_race"]).sum()
    bad_winner_races = winner_counts[~winner_counts.eq(1)]
    if not bad_winner_races.empty:
        examples = bad_winner_races.head(5).to_dict()
        raise RuntimeError(
            f"STOP_WINNER_COUNT: source={source_name}; examples={examples}"
        )

    prob = pd.to_numeric(df["p"], errors="coerce")
    if prob.isna().any() or not np.isfinite(prob.to_numpy(dtype=float)).all():
        raise RuntimeError(f"STOP_PROBABILITY_NON_FINITE: source={source_name}")
    if not prob.between(0, 1).all():
        raise RuntimeError(f"STOP_PROBABILITY_RANGE: source={source_name}")

    mass_error = float((prob.groupby(df["_race"]).sum() - 1.0).abs().max())
    if mass_error > MASS_TOLERANCE:
        raise RuntimeError(
            f"STOP_RACE_MASS: source={source_name}; max_abs_error={mass_error:.17g}"
        )

    return {
        "source": source_name,
        "winner_column": winner_col,
        "runners": int(len(df)),
        "races": int(df["_race"].nunique()),
        "winners": int(winner.sum()),
        "max_race_probability_mass_error": mass_error,
    }


def read_score_file(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def audit_scores(scores_dir: Path, years: Iterable[int]) -> dict:
    year_results = []
    for year in years:
        path = scores_dir / f"STAGE011_RUNNER_PROBABILITIES_{int(year)}.csv"
        if not path.is_file():
            raise RuntimeError(f"STOP_MISSING_SCORE_FILE: {path}")
        df = read_score_file(path)
        result = validate_stage011_score_frame(df, str(path))
        if "evaluation_year" in df.columns and not df["evaluation_year"].eq(int(year)).all():
            raise RuntimeError(f"STOP_EVALUATION_YEAR_MISMATCH: source={path}")
        result["year"] = int(year)
        year_results.append(result)

    return {
        "status": "PASS",
        "audit": "READ_ONLY_STAGE011_BASELINE_DRIFT_SCHEMA",
        "winner_column_contract": "y",
        "mass_tolerance": MASS_TOLERANCE,
        "no_refit": True,
        "no_rescore": True,
        "no_prediction_modification": True,
        "year_results": year_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only Stage011 score-file schema and baseline drift audit."
    )
    parser.add_argument("--scores-dir", type=Path, default=DEFAULT_SCORES_DIR)
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = audit_scores(args.scores_dir, args.years)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
