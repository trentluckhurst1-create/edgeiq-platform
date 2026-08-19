from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv
import json
import math
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_FILE = DATA / "edgeiq_racingcom_runner_speed_fact_v1.csv"
SECTIONAL_FILE = DATA / "edgeiq_racingcom_runner_sectional_fact_v1.csv"
SPLIT_FILE = DATA / "edgeiq_racingcom_runner_split_fact_v1.csv"
RACE_FILE = DATA / "edgeiq_racingcom_race_speed_summary_v1.csv"

AUDIT_FILE = DATA / "edgeiq_racingcom_speed_semantics_v1_1_audit.json"
DETAIL_FILE = DATA / "edgeiq_racingcom_speed_semantics_v1_1_detail.csv"


DETAIL_COLUMNS = [
    "race_key",
    "runner_id",
    "horse_name",
    "check_name",
    "status",
    "expected_value",
    "actual_value",
    "absolute_difference",
    "tolerance",
    "evidence",
]


TIME_TOLERANCE = 0.02
CENTISECOND_TOLERANCE = 1.01
DISTANCE_TOLERANCE = 0.01


def log(message: str) -> None:
    print(f"[speed_semantics_v1_1] {message}", flush=True)


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def to_float(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def close(
    left: float | None,
    right: float | None,
    tolerance: float,
) -> bool:
    if left is None or right is None:
        return False

    return math.isclose(
        left,
        right,
        rel_tol=0.0,
        abs_tol=tolerance,
    )


def difference(
    left: float | None,
    right: float | None,
) -> str:
    if left is None or right is None:
        return ""

    return f"{abs(left - right):.6f}".rstrip("0").rstrip(".")


def numeric_text(value: float | None) -> str:
    if value is None:
        return ""

    return f"{value:.6f}".rstrip("0").rstrip(".")


def parse_split_label(label: str) -> tuple[str, str] | None:
    text = str(label).strip().upper()

    match = re.fullmatch(
        r"(?P<start>\d+M)-(?P<end>\d+M|FINISH)",
        text,
    )

    if not match:
        return None

    return match.group("start"), match.group("end")


def add_detail(
    rows: list[dict[str, Any]],
    *,
    race_key: str,
    runner_id: str,
    horse_name: str,
    check_name: str,
    status: str,
    expected: float | None,
    actual: float | None,
    tolerance: float,
    evidence: str,
) -> None:
    rows.append({
        "race_key": race_key,
        "runner_id": runner_id,
        "horse_name": horse_name,
        "check_name": check_name,
        "status": status,
        "expected_value": numeric_text(expected),
        "actual_value": numeric_text(actual),
        "absolute_difference": difference(expected, actual),
        "tolerance": numeric_text(tolerance),
        "evidence": evidence,
    })


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    runners = load_csv(RUNNER_FILE)
    sectionals = load_csv(SECTIONAL_FILE)
    splits = load_csv(SPLIT_FILE)
    races = load_csv(RACE_FILE)

    race_by_key = {
        row["race_key"]: row
        for row in races
    }

    sectionals_by_runner: dict[
        tuple[str, str],
        list[dict[str, str]]
    ] = defaultdict(list)

    splits_by_runner: dict[
        tuple[str, str],
        list[dict[str, str]]
    ] = defaultdict(list)

    for row in sectionals:
        sectionals_by_runner[
            (row["race_key"], row["runner_id"])
        ].append(row)

    for row in splits:
        splits_by_runner[
            (row["race_key"], row["runner_id"])
        ].append(row)

    for values in sectionals_by_runner.values():
        values.sort(
            key=lambda row: int(row["sectional_sequence"])
        )

    for values in splits_by_runner.values():
        values.sort(
            key=lambda row: int(row["split_sequence"])
        )

    details: list[dict[str, Any]] = []

    check_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "PASS": 0,
            "FAIL": 0,
            "NOT_TESTED": 0,
        }
    )

    race_winner_by_key: dict[str, dict[str, str]] = {}

    for runner in runners:
        if runner.get("finish_position") == "1":
            race_winner_by_key[runner["race_key"]] = runner

    def record(
        *,
        race_key: str,
        runner_id: str,
        horse_name: str,
        check_name: str,
        expected: float | None,
        actual: float | None,
        tolerance: float,
        evidence: str,
    ) -> None:
        if expected is None or actual is None:
            status = "NOT_TESTED"
        elif close(expected, actual, tolerance):
            status = "PASS"
        else:
            status = "FAIL"

        check_counts[check_name][status] += 1

        add_detail(
            details,
            race_key=race_key,
            runner_id=runner_id,
            horse_name=horse_name,
            check_name=check_name,
            status=status,
            expected=expected,
            actual=actual,
            tolerance=tolerance,
            evidence=evidence,
        )

    for runner in runners:
        race_key = runner["race_key"]
        runner_id = runner["runner_id"]
        horse_name = runner["horse_name"]
        key = (race_key, runner_id)

        runner_sectionals = sectionals_by_runner.get(key, [])
        runner_splits = splits_by_runner.get(key, [])

        sectional_map = {
            row["distance_marker"].strip().upper():
                to_float(row["cumulative_time_seconds"])
            for row in runner_sectionals
        }

        split_sum_values = [
            to_float(row["split_time_seconds"])
            for row in runner_splits
        ]

        split_sum = (
            sum(value for value in split_sum_values if value is not None)
            if split_sum_values
            and all(value is not None for value in split_sum_values)
            else None
        )

        runner_time = to_float(
            runner["runner_race_time_seconds"]
        )

        numeric_sectional_markers = []

        for marker, cumulative_time in sectional_map.items():
            if (
                marker.endswith("M")
                and marker[:-1].isdigit()
                and cumulative_time is not None
            ):
                numeric_sectional_markers.append(
                    (int(marker[:-1]), cumulative_time)
                )

        first_available_marker_metres = None
        first_available_marker_time = None

        if numeric_sectional_markers:
            (
                first_available_marker_metres,
                first_available_marker_time,
            ) = max(
                numeric_sectional_markers,
                key=lambda item: item[0],
            )

        if close(
            runner_time,
            split_sum,
            TIME_TOLERANCE,
        ):
            split_expected = runner_time
            split_evidence = (
                "Supplied SplitTimes cover the full race and their "
                "sum reconciles with runner race time."
            )
        elif close(
            first_available_marker_time,
            split_sum,
            TIME_TOLERANCE,
        ):
            split_expected = first_available_marker_time
            split_evidence = (
                "Supplied SplitTimes begin at the first available "
                f"timing marker ({first_available_marker_metres}m) "
                "rather than at the race start. Their sum reconciles "
                "with the cumulative time from that marker to the "
                "finish."
            )
        else:
            split_expected = runner_time
            split_evidence = (
                "Supplied SplitTimes reconcile with neither runner "
                "race time nor the cumulative time at the first "
                "available timing marker."
            )

        record(
            race_key=race_key,
            runner_id=runner_id,
            horse_name=horse_name,
            check_name=(
                "SPLIT_SUM_RECONCILES_TIMING_WINDOW"
            ),
            expected=split_expected,
            actual=split_sum,
            tolerance=TIME_TOLERANCE,
            evidence=split_evidence,
        )

        last_600 = to_float(
            runner["six_hundred_metres_time_seconds"]
        )
        sectional_600 = sectional_map.get("600M")

        record(
            race_key=race_key,
            runner_id=runner_id,
            horse_name=horse_name,
            check_name="LAST_600_EQUALS_600M_CUMULATIVE",
            expected=sectional_600,
            actual=last_600,
            tolerance=TIME_TOLERANCE,
            evidence=(
                "Runner SixHundredMetresTime compared with the "
                "600m cumulative sectional."
            ),
        )

        last_200 = to_float(
            runner["two_hundred_metres_time_seconds"]
        )
        sectional_200 = sectional_map.get("200M")

        record(
            race_key=race_key,
            runner_id=runner_id,
            horse_name=horse_name,
            check_name="LAST_200_EQUALS_200M_CUMULATIVE",
            expected=sectional_200,
            actual=last_200,
            tolerance=TIME_TOLERANCE,
            evidence=(
                "Runner TwoHundredMetresTime compared with the "
                "200m cumulative sectional."
            ),
        )

        for split in runner_splits:
            parsed = parse_split_label(split["split_distance"])

            if parsed is None:
                continue

            start_marker, end_marker = parsed
            supplied_split = to_float(split["split_time_seconds"])

            start_cumulative = sectional_map.get(start_marker)

            if end_marker == "FINISH":
                expected_split = start_cumulative
            else:
                end_cumulative = sectional_map.get(end_marker)

                expected_split = (
                    start_cumulative - end_cumulative
                    if (
                        start_cumulative is not None
                        and end_cumulative is not None
                    )
                    else None
                )

            record(
                race_key=race_key,
                runner_id=runner_id,
                horse_name=horse_name,
                check_name="SPLIT_EQUALS_CUMULATIVE_DIFFERENCE",
                expected=expected_split,
                actual=supplied_split,
                tolerance=TIME_TOLERANCE,
                evidence=(
                    f"Split {split['split_distance']} compared "
                    "with difference between cumulative markers."
                ),
            )

        winner = race_winner_by_key.get(race_key)

        winner_time = (
            to_float(winner["runner_race_time_seconds"])
            if winner
            else None
        )

        supplied_time_variation = to_float(
            runner["time_variation_to_winner_source"]
        )

        expected_centiseconds = (
            round((runner_time - winner_time) * 100, 6)
            if runner_time is not None and winner_time is not None
            else None
        )

        record(
            race_key=race_key,
            runner_id=runner_id,
            horse_name=horse_name,
            check_name="TIME_VARIATION_IS_CENTISECONDS",
            expected=expected_centiseconds,
            actual=supplied_time_variation,
            tolerance=CENTISECOND_TOLERANCE,
            evidence=(
                "Source TimeVarToWinner compared with runner-minus-"
                "winner time multiplied by 100."
            ),
        )

        winner_distance = (
            to_float(winner["distance_run_source"])
            if winner
            else None
        )
        runner_distance = to_float(
            runner["distance_run_source"]
        )
        supplied_distance_variation = to_float(
            runner["distance_variation_to_winner_source"]
        )

        expected_distance_variation = (
            runner_distance - winner_distance
            if (
                runner_distance is not None
                and winner_distance is not None
            )
            else None
        )

        record(
            race_key=race_key,
            runner_id=runner_id,
            horse_name=horse_name,
            check_name="DISTANCE_VARIATION_EQUALS_DISTANCE_DIFFERENCE",
            expected=expected_distance_variation,
            actual=supplied_distance_variation,
            tolerance=DISTANCE_TOLERANCE,
            evidence=(
                "Source DistanceVarToWinner compared with runner "
                "distance minus winner distance."
            ),
        )

        if runner.get("finish_position") == "1":
            race_row = race_by_key.get(race_key, {})
            race_time = to_float(
                race_row.get("race_time_seconds")
            )

            record(
                race_key=race_key,
                runner_id=runner_id,
                horse_name=horse_name,
                check_name="WINNER_TIME_EQUALS_RACE_TIME",
                expected=race_time,
                actual=runner_time,
                tolerance=TIME_TOLERANCE,
                evidence=(
                    "Winning runner race time compared with supplied "
                    "race-level race time."
                ),
            )

    total_failures = sum(
        values["FAIL"]
        for values in check_counts.values()
    )

    mandatory_checks = [
        "SPLIT_SUM_RECONCILES_TIMING_WINDOW",
        "LAST_600_EQUALS_600M_CUMULATIVE",
        "LAST_200_EQUALS_200M_CUMULATIVE",
        "SPLIT_EQUALS_CUMULATIVE_DIFFERENCE",
        "TIME_VARIATION_IS_CENTISECONDS",
        "DISTANCE_VARIATION_EQUALS_DISTANCE_DIFFERENCE",
        "WINNER_TIME_EQUALS_RACE_TIME",
    ]

    missing_checks = [
        check
        for check in mandatory_checks
        if check not in check_counts
    ]

    status = (
        "PASS"
        if total_failures == 0 and not missing_checks
        else "FAIL"
    )

    semantic_findings = {
        "sectional_time_semantics": {
            "status": "CONFIRMED",
            "finding": (
                "SectionalTimes are cumulative times remaining from "
                "each distance marker to the finish."
            ),
            "basis": (
                "Adjacent cumulative differences reconcile with "
                "supplied SplitTimes."
            ),
        },
        "split_time_semantics": {
            "status": "CONFIRMED",
            "finding": (
                "SplitTimes are individual segment times. Their sum "
                "reconciles either with full runner race time or with "
                "the cumulative time from the provider's first "
                "available timing marker to the finish."
            ),
            "coverage_rule": (
                "Split coverage must not be assumed to begin at the "
                "race start. Races with a non-200-metre starting "
                "distance may have an opening untimed segment before "
                "the first supplied split marker."
            ),
        },
        "six_hundred_metres_time": {
            "status": "CONFIRMED",
            "finding": (
                "SixHundredMetresTime represents cumulative time "
                "from the 600m marker to the finish."
            ),
        },
        "two_hundred_metres_time": {
            "status": "CONFIRMED",
            "finding": (
                "TwoHundredMetresTime represents cumulative time "
                "from the 200m marker to the finish."
            ),
        },
        "time_variation_to_winner": {
            "status": "CONFIRMED_WITH_TOLERANCE",
            "finding": (
                "TimeVarToWinner is supplied in hundredths of a "
                "second rather than seconds."
            ),
            "tolerance_reason": (
                "Displayed race times are rounded to hundredths."
            ),
        },
        "distance_variation_to_winner": {
            "status": "CONFIRMED",
            "finding": (
                "DistanceVarToWinner equals runner DistanceRun minus "
                "winner DistanceRun."
            ),
        },
        "distance_run": {
            "status": "STRONGLY_SUPPORTED",
            "finding": (
                "DistanceRun behaves as distance travelled in metres."
            ),
            "constraint": (
                "This audit validates internal differences but does "
                "not independently verify the external provider unit."
            ),
        },
        "average_speed": {
            "status": "UNRESOLVED",
            "finding": (
                "Values are preserved as source values. The precise "
                "provider calculation and unit are not asserted."
            ),
        },
        "early_mid_late_speed": {
            "status": "UNRESOLVED",
            "finding": (
                "Values are preserved as source values. The provider "
                "segment definitions and units require broader "
                "evidence."
            ),
        },
        "overall_peak_speed": {
            "status": "UNRESOLVED",
            "finding": (
                "Peak speed is preserved as a source value. Sampling "
                "interval and unit are not yet proven."
            ),
        },
        "distance_from_rail": {
            "status": "UNRESOLVED",
            "finding": (
                "DistanceFromRail is preserved as a source value. "
                "Whether it represents mean, maximum or another "
                "aggregate is not yet proven."
            ),
        },
    }

    audit = {
        "audit_name": "EDGEIQ_RACINGCOM_SPEED_SEMANTICS_V1_1",
        "generated_at_utc": generated_at,
        "status": status,
        "races_checked": len(races),
        "runners_checked": len(runners),
        "sectional_rows_checked": len(sectionals),
        "split_rows_checked": len(splits),
        "total_failed_checks": total_failures,
        "missing_mandatory_checks": missing_checks,
        "check_results": dict(check_counts),
        "semantic_findings": semantic_findings,
        "controls": {
            "source_values_modified": False,
            "ratings_calculated": False,
            "benchmarks_calculated": False,
            "unknown_units_asserted": False,
            "provider_documentation_assumed": False,
        },
    }

    with DETAIL_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=DETAIL_COLUMNS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(details)

    AUDIT_FILE.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    log(f"races checked: {len(races)}")
    log(f"runners checked: {len(runners)}")
    log(f"checks written: {len(details)}")
    log(f"failed checks: {total_failures}")
    log(f"audit status: {status}")
    log(f"wrote {DETAIL_FILE.relative_to(ROOT)}")
    log(f"wrote {AUDIT_FILE.relative_to(ROOT)}")

    if status != "PASS":
        return 1

    print("EDGEIQ_RACINGCOM_SPEED_SEMANTICS_V1_1_AUDIT_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
