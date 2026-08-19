from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "scripts"
    / "audit_edgeiq_racingcom_speed_semantics_v1.py"
)

TARGET = (
    ROOT
    / "scripts"
    / "audit_edgeiq_racingcom_speed_semantics_v1_1.py"
)


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = text.count(old)

    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one match, found {count}"
        )

    return text.replace(old, new, 1)


def main() -> int:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    text = SOURCE.read_text(encoding="utf-8-sig")

    text = replace_once(
        text,
        'AUDIT_FILE = DATA / '
        '"edgeiq_racingcom_speed_semantics_v1_audit.json"',
        'AUDIT_FILE = DATA / '
        '"edgeiq_racingcom_speed_semantics_v1_1_audit.json"',
        "audit output",
    )

    text = replace_once(
        text,
        'DETAIL_FILE = DATA / '
        '"edgeiq_racingcom_speed_semantics_v1_detail.csv"',
        'DETAIL_FILE = DATA / '
        '"edgeiq_racingcom_speed_semantics_v1_1_detail.csv"',
        "detail output",
    )

    text = replace_once(
        text,
        'print(f"[speed_semantics_v1] {message}", flush=True)',
        'print(f"[speed_semantics_v1_1] {message}", flush=True)',
        "log prefix",
    )

    old_split_check = '''        record(
            race_key=race_key,
            runner_id=runner_id,
            horse_name=horse_name,
            check_name="SPLIT_SUM_EQUALS_RUNNER_TIME",
            expected=runner_time,
            actual=split_sum,
            tolerance=TIME_TOLERANCE,
            evidence=(
                "Sum of all supplied runner SplitTimes compared "
                "with runner race time."
            ),
        )
'''

    new_split_check = '''        numeric_sectional_markers = []

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
'''

    text = replace_once(
        text,
        old_split_check,
        new_split_check,
        "split timing-window validation",
    )

    text = replace_once(
        text,
        '"SPLIT_SUM_EQUALS_RUNNER_TIME",',
        '"SPLIT_SUM_RECONCILES_TIMING_WINDOW",',
        "mandatory split check",
    )

    old_finding = '''        "split_time_semantics": {
            "status": "CONFIRMED",
            "finding": (
                "SplitTimes are individual segment times and their "
                "sum reconciles with runner race time."
            ),
        },
'''

    new_finding = '''        "split_time_semantics": {
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
'''

    text = replace_once(
        text,
        old_finding,
        new_finding,
        "split semantic finding",
    )

    text = replace_once(
        text,
        '"audit_name": "EDGEIQ_RACINGCOM_SPEED_SEMANTICS_V1",',
        '"audit_name": "EDGEIQ_RACINGCOM_SPEED_SEMANTICS_V1_1",',
        "audit name",
    )

    text = replace_once(
        text,
        'print("EDGEIQ_RACINGCOM_SPEED_SEMANTICS_V1_AUDIT_PASS")',
        'print('
        '"EDGEIQ_RACINGCOM_SPEED_SEMANTICS_V1_1_AUDIT_PASS"'
        ')',
        "pass marker",
    )

    TARGET.write_text(text, encoding="utf-8")

    print(f"CREATED: {TARGET}")
    print("CORRECTION: SPLIT_TIMING_WINDOW_SEMANTICS")
    print("ORIGINAL_V1_PRESERVED: YES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
