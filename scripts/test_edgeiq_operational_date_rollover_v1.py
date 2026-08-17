from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from edgeiq_three_day_window_v1_common import (
    TIMEZONE_NAME,
    build_operational_dates,
    get_operational_today,
)
from ensure_edgeiq_current_data_rollover_v1 import dates_match_expected

ROOT = Path(__file__).resolve().parents[1]


def dates(runtime_date: str) -> list[str]:
    today, source = get_operational_today(
        now=datetime.fromisoformat(runtime_date).replace(
            tzinfo=ZoneInfo(TIMEZONE_NAME),
        )
    )
    assert source == "AUSTRALIA_MELBOURNE_CLOCK"
    return [item.isoformat() for item in build_operational_dates(today)]


def assert_equal(name: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{name}: actual={actual} expected={expected}")
    print(f"{name}=PASS")


def run_rollover_tests() -> None:
    assert_equal(
        "NORMAL_ROLLOVER",
        dates("2026-08-15T09:00:00"),
        ["2026-08-15", "2026-08-16", "2026-08-17"],
    )
    assert_equal(
        "NEXT_DAY_ROLLOVER",
        dates("2026-08-16T09:00:00"),
        ["2026-08-16", "2026-08-17", "2026-08-18"],
    )
    assert_equal(
        "MONTH_BOUNDARY_TEST",
        dates("2026-08-31T09:00:00"),
        ["2026-08-31", "2026-09-01", "2026-09-02"],
    )
    assert_equal(
        "YEAR_BOUNDARY_TEST",
        dates("2026-12-31T09:00:00"),
        ["2026-12-31", "2027-01-01", "2027-01-02"],
    )
    assert_equal(
        "LEAP_YEAR_TEST",
        dates("2028-02-28T09:00:00"),
        ["2028-02-28", "2028-02-29", "2028-03-01"],
    )
    assert_equal(
        "DST_TEST",
        dates("2026-10-04T03:30:00"),
        ["2026-10-04", "2026-10-05", "2026-10-06"],
    )


def run_stale_artifact_test() -> None:
    stale_dates = ["2026-08-14", "2026-08-15", "2026-08-16"]
    expected_dates = ["2026-08-15", "2026-08-16", "2026-08-17"]
    assert_equal(
        "STALE_ARTIFACT_DETECTION",
        dates_match_expected(stale_dates, expected_dates),
        False,
    )


def run_dynamic_completion_contract_test() -> None:
    script = (
        ROOT
        / "scripts"
        / "complete_edgeiq_current_early_late_distance_aware_v3.py"
    ).read_text(encoding="utf-8")

    forbidden_fragments = [
        "20260812_204223",
        "EXPECTED_EARLY_BASELINE_312",
        "EXPECTED_LATE_BASELINE_291",
        "EXPECTED_CURRENT_ROWS_732",
        "EARLY_ROW_COUNT_732",
        "LATE_ROW_COUNT_732",
        "EARLY_ORIGINAL_VALUES_PRESERVED_312",
        "LATE_ORIGINAL_VALUES_PRESERVED_291",
    ]

    for fragment in forbidden_fragments:
        assert_equal(
            f"DYNAMIC_COMPLETION_CONTRACT_NO_{fragment}",
            fragment in script,
            False,
        )


def main() -> int:
    run_rollover_tests()
    run_stale_artifact_test()
    run_dynamic_completion_contract_test()
    print("EDGEIQ_OPERATIONAL_DATE_ROLLOVER_TESTS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
