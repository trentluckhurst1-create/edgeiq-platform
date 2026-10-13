"""Tests for the research-only Stage011 live feature pipeline.

The tests use synthetic inputs for formula checks and the Caulfield dry-run
files for the live contract. They do not read outcomes, prices, or models.
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import pandas as pd

from run_edgeiq_stage011_live_feature_pipeline import FEATURES, Paths, build_matrix, load_form, write_outputs


DEFAULT_PATHS = Paths(
    field=Path(
        r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\october_graphql_field_identities.csv"
    ),
    form=Path(
        r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv"
    ),
    public_snapshot=Path(
        r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\public_race_snapshot_20261012T051330Z.json"
    ),
    lab245b_candidates=Path(r"C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_LIVE_HISTORY_FEATURE_CANDIDATES_V3.csv"),
    output_dir=Path("outputs/research/stage011_live_completion"),
)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def synthetic_paths(root: Path) -> Paths:
    field = root / "field.csv"
    form = root / "form.csv"
    snapshot = root / "snapshot.json"
    candidates = root / "candidates.csv"
    write_csv(
        field,
        [
            {
                "race_date": "2026-10-14",
                "venue": "Caulfield",
                "race_no": "1",
                "race_id": "R1",
                "horse_name": "Alpha",
                "horse_code": "H1",
                "race_entry_id": "E1",
                "barrier": "2",
                "scratched": "false",
                "trainer_code": "T1",
                "jockey_code": "J1",
            },
            {
                "race_date": "2026-10-14",
                "venue": "Caulfield",
                "race_no": "1",
                "race_id": "R1",
                "horse_name": "Beta",
                "horse_code": "H2",
                "race_entry_id": "E2",
                "barrier": "1",
                "scratched": "false",
                "trainer_code": "T2",
                "jockey_code": "J2",
            },
        ],
    )
    write_csv(
        form,
        [
            {
                "horse_code": "H1",
                "horse_name": "Alpha",
                "race_date": "2026-09-01",
                "race_code": "9001",
                "distance": "1400m",
                "field_size": "6",
                "finish": "2",
                "margin": "2.0L",
                "jockey_id": "J1",
                "trainer_id": "T1",
            },
            {
                "horse_code": "H1",
                "horse_name": "Alpha",
                "race_date": "2026-10-01",
                "race_code": "9002",
                "distance": "1600m",
                "field_size": "8",
                "finish": "1",
                "margin": "3.0L",
                "jockey_id": "J1",
                "trainer_id": "T1",
            },
            {
                "horse_code": "H1",
                "horse_name": "Alpha",
                "race_date": "2026-10-14",
                "race_code": "9999",
                "distance": "1600m",
                "field_size": "8",
                "finish": "9",
                "margin": "99.0L",
                "jockey_id": "J1",
                "trainer_id": "T1",
            },
        ],
    )
    snapshot.write_text(
        json.dumps(
            {
                "races": [
                    {
                        "race_date": "2026-10-14",
                        "venue": "Caulfield",
                        "race_no": "1",
                        "raw_text": "Race 1\n12:30pm\n1600m\n",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    write_csv(
        candidates,
        [
            {
                "race_date": "2026-10-14",
                "race_no": "1",
                "horse_name": "Alpha",
                "canonical_horse_id": "C1",
                "feature_status": "UNVERIFIED",
            }
        ],
    )
    return Paths(field, form, snapshot, candidates, root / "out")


def test_synthetic_strict_prior_and_stage011_formulas() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        matrix, coverage, feature_status, audit = build_matrix(paths, "2026-10-14", "Caulfield", expected_rows=2)
        row = matrix[matrix["runner_id"].eq("E1")].iloc[0]
        assert row["hist_runs"] == 2.0
        assert row["margin_last1"] == 0.0
        assert row["margin_last2"] == 2.0
        assert row["margin_per_runner_last1"] == 0.0
        assert row["margin_per_runner_last2"] == 0.4
        assert row["margin_change_l1_l2"] == -2.0
        assert row["days_since_last"] == 13.0
        assert row["clean_last_won"] == 1.0
        assert row["clean_last_top3"] == 1.0
        assert row["barrier_position_pct"] == 1.0
        assert row["dist200_runs"] == 2.0
        assert row["historical_identity_status"] == "HISTORICAL_LVS_CANDIDATE_UNCERTIFIED"
        assert audit["declared_runners"] == 2
        assert set(coverage["family"]) == {"CURRENT_CONTEXT", "RCOM_NATIVE_HISTORY", "LVS_TIMING", "PERSONNEL_PARTIAL"}
        assert not feature_status.empty


def test_load_form_sets_prior_winner_margin_to_zero() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        form = load_form(paths.form, "2026-10-14")
        winner = form[form["finish_num"].eq(1)].iloc[0]
        assert winner["margin_len"] == 0.0
        assert not form["race_date"].eq("2026-10-14").any()


def test_duplicate_live_runner_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        field = pd.read_csv(paths.field, dtype="string")
        field = pd.concat([field, field.iloc[[0]]], ignore_index=True)
        field.to_csv(paths.field, index=False)
        try:
            build_matrix(paths, "2026-10-14", "Caulfield", expected_rows=None)
        except RuntimeError as exc:
            assert "Duplicate live runners" in str(exc)
        else:
            raise AssertionError("duplicate live runner was accepted")


def test_caulfield_live_contract_is_fail_closed_without_market_or_outcomes() -> None:
    matrix, coverage, feature_status, audit = build_matrix(DEFAULT_PATHS, "2026-10-14", "Caulfield", expected_rows=104)
    assert len(matrix) == 104
    assert matrix["race_id"].nunique() == 8
    assert not matrix.duplicated(["race_id", "runner_id"]).any()
    assert FEATURES == list(matrix[FEATURES].columns)
    assert int(matrix["eligible_for_stage011_scoring"].sum()) == 0
    assert audit["no_market_features"] is True
    assert audit["no_current_race_outcomes"] is True
    assert set(["sp", "bsp", "winner", "y"]).isdisjoint({c.lower() for c in matrix.columns})
    assert coverage["total_cells"].sum() == 104 * 35
    assert len(feature_status) == 104 * 35


def test_write_outputs_includes_long_status_and_empty_score_input() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        matrix, coverage, feature_status, audit = build_matrix(paths, "2026-10-14", "Caulfield", expected_rows=2)
        outputs = write_outputs(matrix, coverage, feature_status, audit, paths.output_dir)
        assert outputs["matrix"].is_file()
        assert outputs["feature_status"].is_file()
        score = pd.read_csv(outputs["score_input"])
        assert list(score.columns) == ["race_id", "runner_id", "scratch_status", "scoring_timestamp", "scheduled_start_time"] + FEATURES
        assert score.empty


def main() -> None:
    test_synthetic_strict_prior_and_stage011_formulas()
    test_load_form_sets_prior_winner_margin_to_zero()
    test_duplicate_live_runner_fails_closed()
    test_caulfield_live_contract_is_fail_closed_without_market_or_outcomes()
    test_write_outputs_includes_long_status_and_empty_score_input()
    print("EDGEIQ_STAGE011_LIVE_FEATURE_PIPELINE_TESTS: PASS")
    print("NO_OUTCOMES; NO_MARKET; NO_MODEL_FIT; NO_STAGE011_SCORING")


if __name__ == "__main__":
    main()
