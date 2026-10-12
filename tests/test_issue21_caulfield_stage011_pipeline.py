import math
from pathlib import Path

import numpy as np
import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "research"))

from edgeiq_stage011_live_scorer import softmax  # noqa: E402
from run_issue21_caulfield_stage011_pipeline import (  # noqa: E402
    extract_race_records,
    parse_elapsed_seconds,
    race_id,
)


def test_elapsed_time_parser_rejects_scheduled_timestamp_shape():
    assert parse_elapsed_seconds("1:04.77") == 64.77
    assert parse_elapsed_seconds("59.85") == 59.85
    assert math.isnan(parse_elapsed_seconds(None))


def test_duplicate_race_payloads_keep_separate_operations_without_conflict():
    payloads = [
        {
            "data": {
                "getNoCacheRacesForMeet": [
                    {
                        "id": "1",
                        "raceNumber": 1,
                        "distance": "1200m",
                        "time": "2026-10-14T01:00:00.000Z",
                        "raceTime": "1:10.00",
                        "isTrial": 0,
                        "isJumpOut": 0,
                    }
                ],
                "getRacesForMeet": [
                    {
                        "id": "1",
                        "raceNumber": 1,
                        "distance": "1200m",
                        "time": "2026-10-14T01:00:00.000Z",
                        "isTrial": 0,
                        "isJumpOut": 0,
                    }
                ],
            }
        }
    ]
    frame = extract_race_records(payloads)
    assert set(frame["source_operation"]) == {"getNoCacheRacesForMeet", "getRacesForMeet"}
    assert frame["race_id"].eq(race_id("1")).all()


def test_trials_and_jumpouts_are_rejected_from_timing_records():
    payloads = [
        {
            "data": {
                "getNoCacheRacesForMeet": [
                    {"id": "1", "distance": "800m", "raceTime": "45.0", "isTrial": 1, "isJumpOut": 0},
                    {"id": "2", "distance": "800m", "raceTime": "45.0", "isTrial": 0, "isJumpOut": 1},
                    {"id": "3", "distance": "1000m", "raceTime": "58.0", "isTrial": 0, "isJumpOut": 0},
                ]
            }
        }
    ]
    frame = extract_race_records(payloads)
    assert frame["race_code"].tolist() == ["3"]


def test_race_softmax_sums_to_one():
    values = np.array([-2.0, 0.0, 2.0])
    probs = softmax(values)
    assert np.isclose(probs.sum(), 1.0, atol=1e-12)
    assert probs.argmax() == 2


if __name__ == "__main__":
    test_elapsed_time_parser_rejects_scheduled_timestamp_shape()
    test_duplicate_race_payloads_keep_separate_operations_without_conflict()
    test_trials_and_jumpouts_are_rejected_from_timing_records()
    test_race_softmax_sums_to_one()
    print("ISSUE21_TESTS_PASS")
