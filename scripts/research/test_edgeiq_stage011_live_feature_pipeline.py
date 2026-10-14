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

from run_edgeiq_stage011_live_feature_pipeline import (
    FEATURES,
    Paths,
    build_matrix,
    load_form,
    rcom_current_id,
    resolve_source,
    write_outputs,
)


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
    lab245b_warehouse=Path(
        r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv"
    ),
    perf026=Path(
        r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv"
    ),
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
    warehouse = root / "warehouse.csv"
    perf026 = root / "perf026.csv"
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
                "eiq_horse_id": rcom_current_id("HORSE", "H1"),
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
                "eiq_horse_id": rcom_current_id("HORSE", "H2"),
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
    write_csv(
        warehouse,
        [
            {
                "canonical_race_id": "WR1",
                "canonical_horse_id": rcom_current_id("HORSE", "H1"),
                "race_date": "2026-09-01",
                "distance_metres": "1400",
                "field_size": "6",
                "finish_position": "2",
                "finish_margin": "2.0",
                "runner_lvs": "1.0",
            },
            {
                "canonical_race_id": "WR2",
                "canonical_horse_id": rcom_current_id("HORSE", "H1"),
                "race_date": "2026-10-01",
                "distance_metres": "1600",
                "field_size": "8",
                "finish_position": "1",
                "finish_margin": "3.0",
                "runner_lvs": "3.0",
            },
        ],
    )
    write_csv(
        perf026,
        [
            {
                "canonical_race_id": "P1",
                "canonical_horse_id": rcom_current_id("HORSE", "H1"),
                "canonical_jockey_id": rcom_current_id("JOCKEY", "J1"),
                "canonical_trainer_id": rcom_current_id("TRAINER", "T1"),
                "race_date": "2026-08-01",
                "finish_position": "1",
                "epi_status_026": "CALCULATED",
            },
            {
                "canonical_race_id": "P2",
                "canonical_horse_id": rcom_current_id("HORSE", "H9"),
                "canonical_jockey_id": rcom_current_id("JOCKEY", "J1"),
                "canonical_trainer_id": rcom_current_id("TRAINER", "T1"),
                "race_date": "2026-09-01",
                "finish_position": "3",
                "epi_status_026": "CALCULATED",
            },
            {
                "canonical_race_id": "P3",
                "canonical_horse_id": rcom_current_id("HORSE", "H8"),
                "canonical_jockey_id": rcom_current_id("JOCKEY", "J1"),
                "canonical_trainer_id": rcom_current_id("TRAINER", "T1"),
                "race_date": "2026-10-14",
                "finish_position": "1",
                "epi_status_026": "CALCULATED",
            },
        ],
    )
    return Paths(field, form, snapshot, candidates, warehouse, perf026, root / "out")


def test_synthetic_strict_prior_and_stage011_formulas() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        matrix, coverage, feature_status, identity_bridge, audit = build_matrix(
            paths, "2026-10-14", "Caulfield", expected_rows=2
        )
        row = matrix[matrix["runner_id"].eq("E1")].iloc[0]
        assert row["hist_runs"] == 2.0
        assert row["margin_last1"] == 3.0
        assert row["margin_last2"] == 2.0
        assert abs(row["margin_per_runner_last1"] - (3.0 / 7.0)) < 1e-12
        assert row["margin_per_runner_last2"] == 0.4
        assert row["margin_change_l1_l2"] == 1.0
        assert row["days_since_last"] == 13.0
        assert row["clean_last_won"] == 1.0
        assert row["clean_last_top3"] == 1.0
        assert row["barrier_position_pct"] == 1.0
        assert row["dist200_runs"] == 2.0
        assert row["historical_identity_status"] == "LAB245B_IDENTITY_BRIDGE_CERTIFIED"
        assert row["identity_bridge_matched_prior_records"] == 2
        assert row["lvs_last1"] == 3.0
        assert row["lvs_mean3"] == 2.0
        assert row["jockey_prior_starts"] == 2.0
        assert abs(row["jockey_prior_win_rate"] - (2.0 / 12.0)) < 1e-12
        assert abs(row["jockey_prior_top3_rate"] - (5.0 / 12.0)) < 1e-12
        assert row["jockey_prior_status"] == "D45_FULL_HISTORY_PRIOR"
        assert audit["declared_runners"] == 2
        assert audit["lab245b_identity_bridge_certified"] == 1
        assert identity_bridge["identity_bridge_status"].tolist() == [
            "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH",
            "NO_STRICT_PRIOR_LAB245B_HISTORY",
        ]
        assert set(coverage["family"]) == {"CURRENT_CONTEXT", "RCOM_NATIVE_HISTORY", "LVS_TIMING", "PERSONNEL_FULL_HISTORY"}
        assert not feature_status.empty


def test_load_form_preserves_prior_winner_margin_source_convention() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        form = load_form(paths.form, "2026-10-14")
        winner = form[form["finish_num"].eq(1)].iloc[0]
        assert winner["margin_len"] == 3.0
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
    matrix, coverage, feature_status, identity_bridge, audit = build_matrix(
        DEFAULT_PATHS, "2026-10-14", "Caulfield", expected_rows=104
    )
    assert len(matrix) == 104
    assert matrix["race_id"].nunique() == 8
    assert not matrix.duplicated(["race_id", "runner_id"]).any()
    assert FEATURES == list(matrix[FEATURES].columns)
    assert int(matrix["eligible_for_stage011_scoring"].sum()) == 79
    assert audit["no_market_features"] is True
    assert audit["no_current_race_outcomes"] is True
    assert set(["sp", "bsp", "winner", "y"]).isdisjoint({c.lower() for c in matrix.columns})
    assert coverage["total_cells"].sum() == 104 * 35
    assert len(feature_status) == 104 * 35
    assert len(identity_bridge) == 104
    assert audit["lab245b_identity_bridge_certified"] >= 0


def test_write_outputs_includes_long_status_blockers_and_score_input() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        matrix, coverage, feature_status, identity_bridge, audit = build_matrix(
            paths, "2026-10-14", "Caulfield", expected_rows=2
        )
        outputs = write_outputs(matrix, coverage, feature_status, identity_bridge, audit, paths.output_dir)
        assert outputs["matrix"].is_file()
        assert outputs["feature_status"].is_file()
        assert outputs["identity_bridge"].is_file()
        assert outputs["blockers"].is_file()
        assert outputs["runner_certification"].is_file()
        runner_certification = pd.read_csv(outputs["runner_certification"])
        assert len(runner_certification) == 2
        assert runner_certification["certification_decision"].tolist() == [
            "FEATURE_PROVENANCE_ELIGIBLE_RESEARCH_ONLY",
            "WITHHELD_FEATURE_OR_PROVENANCE_BLOCKER",
        ]
        score = pd.read_csv(outputs["score_input"])
        assert list(score.columns) == ["race_id", "runner_id", "scratch_status", "scoring_timestamp", "scheduled_start_time"] + FEATURES
        assert len(score) == 1
        assert score.iloc[0]["runner_id"] == "E1"


def test_false_live_identity_hash_downgrades_bridge() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        field = pd.read_csv(paths.field, dtype="string")
        field.loc[field["race_entry_id"].eq("E1"), "eiq_horse_id"] = "EIQ_HORSE_WRONG"
        field.to_csv(paths.field, index=False)
        matrix, _, _, identity_bridge, _ = build_matrix(paths, "2026-10-14", "Caulfield", expected_rows=2)
        alpha = identity_bridge[identity_bridge["runner_id"].eq("E1")].iloc[0]
        assert alpha["identity_bridge_status"] == "FIELD_EIQ_PROVENANCE_FAIL"
        assert not bool(matrix[matrix["runner_id"].eq("E1")]["eligible_for_stage011_scoring"].iloc[0])


def test_duplicate_prior_race_records_downgrade_bridge() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        warehouse = pd.read_csv(paths.lab245b_warehouse, dtype="string")
        warehouse = pd.concat([warehouse, warehouse.iloc[[0]]], ignore_index=True)
        warehouse.to_csv(paths.lab245b_warehouse, index=False)
        _, _, _, identity_bridge, _ = build_matrix(paths, "2026-10-14", "Caulfield", expected_rows=2)
        alpha = identity_bridge[identity_bridge["runner_id"].eq("E1")].iloc[0]
        assert alpha["identity_bridge_status"] == "DUPLICATE_PRIOR_RACE_RECORDS"


def test_missing_lab245b_field_size_recovers_from_exact_prior_form_fact() -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = synthetic_paths(Path(td))
        warehouse = pd.read_csv(paths.lab245b_warehouse, dtype="string")
        warehouse.loc[warehouse["canonical_race_id"].eq("WR2"), "field_size"] = ""
        warehouse.to_csv(paths.lab245b_warehouse, index=False)
        matrix, _, _, identity_bridge, _ = build_matrix(paths, "2026-10-14", "Caulfield", expected_rows=2)
        alpha = matrix[matrix["runner_id"].eq("E1")].iloc[0]
        bridge_alpha = identity_bridge[identity_bridge["runner_id"].eq("E1")].iloc[0]
        assert abs(alpha["margin_per_runner_last1"] - (3.0 / 7.0)) < 1e-12
        assert bridge_alpha["field_size_recovered_from_form_records"] == 1
        assert "RCOM_STRICT_PRIOR_FORM_EXACT_FACT_MATCH" in bridge_alpha["latest_prior_field_size_recovery"]


def test_missing_optional_source_resolves_fail_closed_without_crash() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        missing = root / "missing_candidates.csv"
        resolution = resolve_source("lab245b_candidates", missing, [root], required=False)
        assert resolution.status == "MISSING_OPTIONAL_SOURCE"
        assert not resolution.resolved_path


def main() -> None:
    test_synthetic_strict_prior_and_stage011_formulas()
    test_load_form_preserves_prior_winner_margin_source_convention()
    test_duplicate_live_runner_fails_closed()
    test_false_live_identity_hash_downgrades_bridge()
    test_duplicate_prior_race_records_downgrade_bridge()
    test_missing_lab245b_field_size_recovers_from_exact_prior_form_fact()
    test_missing_optional_source_resolves_fail_closed_without_crash()
    test_caulfield_live_contract_is_fail_closed_without_market_or_outcomes()
    test_write_outputs_includes_long_status_blockers_and_score_input()
    print("EDGEIQ_STAGE011_LIVE_FEATURE_PIPELINE_TESTS: PASS")
    print("NO_OUTCOMES; NO_MARKET; NO_MODEL_FIT; NO_STAGE011_SCORING")


if __name__ == "__main__":
    main()
