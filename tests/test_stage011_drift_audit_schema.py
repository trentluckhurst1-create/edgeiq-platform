from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "research" / "audit_v2_stage011_baseline_drift.py"
SPEC = importlib.util.spec_from_file_location("stage011_drift_audit", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


def stage011_frame() -> pd.DataFrame:
    rows = [
        ("r1", "h1", 2022, 1, 0.50),
        ("r1", "h2", 2022, 0, 0.30),
        ("r1", "h3", 2022, 0, 0.20),
        ("r2", "h4", 2022, 0, 0.10),
        ("r2", "h5", 2022, 1, 0.70),
        ("r2", "h6", 2022, 0, 0.20),
    ]
    df = pd.DataFrame(rows, columns=["_race", "_horse", "evaluation_year", "y", "p"])
    df["race_date"] = ["2022-01-01"] * len(df)
    df["training_year_max"] = 2021
    df["raw"] = 0.0
    df["evidence_class"] = "REUSED_DEVELOPMENT"
    df["model_name"] = "V2_STAGE011_CLEAN_PLACING"
    df["model_seed"] = 42
    df["feature_manifest_sha256"] = "feature-sha"
    df["source_stage006_sha256"] = "stage006-sha"
    df["source_d45_sha256"] = "d45-sha"
    df["source_perf026_sha256"] = "perf026-sha"
    return df[
        [
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
        ]
    ]


def expect_runtime_contains(fragment: str, fn) -> None:
    try:
        fn()
    except RuntimeError as exc:
        assert fragment in str(exc), str(exc)
        return
    raise AssertionError(f"Expected RuntimeError containing {fragment!r}")


def test_stage011_y_is_detected_as_winner_column() -> None:
    df = stage011_frame()
    assert audit.detect_winner_column(df.columns) == "y"
    result = audit.validate_stage011_score_frame(df, "synthetic")
    assert result["winner_column"] == "y"
    assert result["runners"] == 6
    assert result["races"] == 2
    assert result["winners"] == 2


def test_y_without_stage011_provenance_fails_closed() -> None:
    df = stage011_frame()[["_race", "_horse", "y", "p"]]
    expect_runtime_contains(
        "STOP_Y_WITHOUT_STAGE011_PROVENANCE",
        lambda: audit.validate_stage011_score_frame(df, "synthetic"),
    )


def test_missing_winner_column_fails_closed() -> None:
    df = stage011_frame().drop(columns=["y"])
    expect_runtime_contains(
        "STOP_AMBIGUOUS_WINNER_COLUMN",
        lambda: audit.validate_stage011_score_frame(df, "synthetic"),
    )


def test_multiple_winners_per_race_fails() -> None:
    df = stage011_frame()
    df.loc[(df["_race"] == "r1") & (df["_horse"] == "h2"), "y"] = 1
    expect_runtime_contains(
        "STOP_WINNER_COUNT",
        lambda: audit.validate_stage011_score_frame(df, "synthetic"),
    )


def test_duplicate_runner_key_fails() -> None:
    df = pd.concat([stage011_frame(), stage011_frame().head(1)], ignore_index=True)
    expect_runtime_contains(
        "STOP_DUPLICATE_RUNNER_KEYS",
        lambda: audit.validate_stage011_score_frame(df, "synthetic"),
    )


def test_probability_mass_error_fails() -> None:
    df = stage011_frame()
    df.loc[(df["_race"] == "r1") & (df["_horse"] == "h1"), "p"] = 0.51
    expect_runtime_contains(
        "STOP_RACE_MASS",
        lambda: audit.validate_stage011_score_frame(df, "synthetic"),
    )


def test_non_binary_y_fails() -> None:
    df = stage011_frame()
    df.loc[(df["_race"] == "r1") & (df["_horse"] == "h1"), "y"] = 2
    expect_runtime_contains(
        "STOP_WINNER_NOT_BINARY",
        lambda: audit.validate_stage011_score_frame(df, "synthetic"),
    )


if __name__ == "__main__":
    test_stage011_y_is_detected_as_winner_column()
    test_y_without_stage011_provenance_fails_closed()
    test_missing_winner_column_fails_closed()
    test_multiple_winners_per_race_fails()
    test_duplicate_runner_key_fails()
    test_probability_mass_error_fails()
    test_non_binary_y_fails()
    print("SYNTHETIC_STAGE011_DRIFT_AUDIT_SCHEMA_TESTS=PASS")
