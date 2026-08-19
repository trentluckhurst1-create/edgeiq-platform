from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any
import csv
import json
import math
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

BASE_BUILDER = (
    SCRIPTS
    / "build_edgeiq_racingcom_canonical_speed_warehouse_v2.py"
)

SEMANTICS_AUDIT = (
    DATA
    / "edgeiq_racingcom_speed_semantics_v1_1_audit.json"
)

SOURCE_RUNNERS = (
    DATA
    / "edgeiq_racingcom_runner_speed_fact_v1.csv"
)

SOURCE_SECTIONALS = (
    DATA
    / "edgeiq_racingcom_runner_sectional_fact_v1.csv"
)

SOURCE_SPLITS = (
    DATA
    / "edgeiq_racingcom_runner_split_fact_v1.csv"
)

SOURCE_RACES = (
    DATA
    / "edgeiq_racingcom_race_speed_summary_v1.csv"
)

RUNNER_OUT = (
    DATA
    / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv"
)

SECTIONAL_OUT = (
    DATA
    / "edgeiq_racingcom_canonical_runner_sectional_fact_v2_1.csv"
)

SPLIT_OUT = (
    DATA
    / "edgeiq_racingcom_canonical_runner_split_fact_v2_1.csv"
)

RACE_OUT = (
    DATA
    / "edgeiq_racingcom_canonical_race_speed_fact_v2_1.csv"
)

BASE_AUDIT_OUT = (
    DATA
    / "edgeiq_racingcom_canonical_speed_warehouse_v2_1_base_audit.json"
)

AUDIT_OUT = (
    DATA
    / "edgeiq_racingcom_canonical_speed_warehouse_v2_1_audit.json"
)


SEMANTIC_VERSION = "RACINGCOM_SPEED_SEMANTICS_V1_1"
WAREHOUSE_VERSION = "RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1"

TIME_TOLERANCE = 0.02


RUNNER_COVERAGE_COLUMNS = [
    "split_coverage_type",
    "split_window_start_marker_metres",
    "split_window_finish_marker_metres",
    "split_window_distance_metres",
    "opening_untimed_distance_metres",
    "full_race_split_coverage",
    "split_window_seconds",
    "split_window_source",
]

SPLIT_COVERAGE_COLUMNS = [
    "split_coverage_type",
    "split_window_start_marker_metres",
    "split_window_finish_marker_metres",
    "split_window_distance_metres",
    "full_race_split_coverage",
]

RACE_COVERAGE_COLUMNS = [
    "full_race_coverage_runner_count",
    "partial_timing_window_runner_count",
    "unresolved_coverage_runner_count",
]


def log(message: str) -> None:
    print(
        f"[canonical_speed_warehouse_v2_1] {message}",
        flush=True,
    )


def clean(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def to_float(value: Any) -> float | None:
    text = clean(value)

    if not text:
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def numeric(value: float | None) -> str:
    if value is None:
        return ""

    return (
        f"{value:.6f}"
        .rstrip("0")
        .rstrip(".")
    )


def close(
    left: float | None,
    right: float | None,
    tolerance: float = TIME_TOLERANCE,
) -> bool:
    if left is None or right is None:
        return False

    return math.isclose(
        left,
        right,
        rel_tol=0.0,
        abs_tol=tolerance,
    )


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])

    return fields, rows


def write_csv(
    path: Path,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow({
                column: row.get(column, "")
                for column in columns
            })


def make_runner_key(
    race_key: str,
    runner_id: str,
) -> str:
    return f"{race_key}|RUNNER:{runner_id}"


def marker_metres(marker: Any) -> float | None:
    text = clean(marker).upper()

    if text == "FINISH":
        return 0.0

    if text.endswith("M"):
        return to_float(text[:-1])

    return None


def official_race_distance(
    row: dict[str, str],
) -> float | None:
    candidate_fields = [
        "race_distance_metres",
        "race_distance",
        "distance_metres",
        "distance",
    ]

    for field in candidate_fields:
        value = to_float(row.get(field))

        if value is not None and value > 0:
            return value

    return None


def import_base_builder():
    if not BASE_BUILDER.exists():
        raise FileNotFoundError(BASE_BUILDER)

    spec = spec_from_file_location(
        "edgeiq_canonical_speed_v2_base",
        BASE_BUILDER,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load canonical V2 builder."
        )

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_base_builder() -> int:
    module = import_base_builder()

    module.SEMANTICS_AUDIT = SEMANTICS_AUDIT
    module.RUNNER_OUT = RUNNER_OUT
    module.SECTIONAL_OUT = SECTIONAL_OUT
    module.SPLIT_OUT = SPLIT_OUT
    module.RACE_OUT = RACE_OUT
    module.AUDIT_OUT = BASE_AUDIT_OUT
    module.SEMANTIC_VERSION = SEMANTIC_VERSION

    return int(module.main())


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    semantics = json.loads(
        SEMANTICS_AUDIT.read_text(encoding="utf-8")
    )

    if semantics.get("status") != "PASS":
        raise RuntimeError(
            "Corrected semantics V1.1 audit is not PASS."
        )

    base_return_code = run_base_builder()

    if base_return_code != 0:
        raise RuntimeError(
            "Canonical V2 base build failed."
        )

    runner_columns, canonical_runners = load_csv(RUNNER_OUT)
    split_columns, canonical_splits = load_csv(SPLIT_OUT)
    race_columns, canonical_races = load_csv(RACE_OUT)

    _, source_runners = load_csv(SOURCE_RUNNERS)
    _, source_sectionals = load_csv(SOURCE_SECTIONALS)
    _, source_splits = load_csv(SOURCE_SPLITS)
    _, source_races = load_csv(SOURCE_RACES)

    source_runner_by_key: dict[
        str,
        dict[str, str],
    ] = {}

    source_race_by_key = {
        row["race_key"]: row
        for row in source_races
    }

    sectionals_by_runner: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    splits_by_runner: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in source_runners:
        runner_key = make_runner_key(
            row["race_key"],
            clean(row.get("runner_id")),
        )

        source_runner_by_key[runner_key] = row

    for row in source_sectionals:
        runner_key = make_runner_key(
            row["race_key"],
            clean(row.get("runner_id")),
        )

        sectionals_by_runner[runner_key].append(row)

    for row in source_splits:
        runner_key = make_runner_key(
            row["race_key"],
            clean(row.get("runner_id")),
        )

        splits_by_runner[runner_key].append(row)

    coverage_by_runner: dict[
        str,
        dict[str, str],
    ] = {}

    unresolved_runner_keys: list[str] = []
    coverage_counts: Counter[str] = Counter()

    for runner in canonical_runners:
        runner_key = runner["runner_key"]
        source_runner = source_runner_by_key.get(
            runner_key,
            {},
        )

        runner_sectionals = sectionals_by_runner.get(
            runner_key,
            [],
        )

        runner_splits = splits_by_runner.get(
            runner_key,
            [],
        )

        race_time = to_float(
            source_runner.get(
                "runner_race_time_seconds"
            )
        )

        split_values = [
            to_float(row.get("split_time_seconds"))
            for row in runner_splits
        ]

        split_sum = (
            sum(
                value
                for value in split_values
                if value is not None
            )
            if (
                split_values
                and all(
                    value is not None
                    for value in split_values
                )
            )
            else None
        )

        split_start_values = [
            marker_metres(
                clean(row.get("split_distance"))
                .split("-", 1)[0]
            )
            for row in runner_splits
            if "-" in clean(row.get("split_distance"))
        ]

        split_start_values = [
            value
            for value in split_start_values
            if value is not None
        ]

        split_window_start = (
            max(split_start_values)
            if split_start_values
            else None
        )

        split_window_finish = (
            0.0
            if runner_splits
            else None
        )

        split_window_distance = (
            split_window_start - split_window_finish
            if (
                split_window_start is not None
                and split_window_finish is not None
            )
            else None
        )

        sectional_candidates: list[
            tuple[float, float]
        ] = []

        for sectional in runner_sectionals:
            distance = marker_metres(
                sectional.get("distance_marker")
            )

            cumulative = to_float(
                sectional.get(
                    "cumulative_time_seconds"
                )
            )

            if (
                distance is not None
                and distance > 0
                and cumulative is not None
            ):
                sectional_candidates.append(
                    (distance, cumulative)
                )

        first_sectional_distance = None
        first_sectional_time = None

        if sectional_candidates:
            (
                first_sectional_distance,
                first_sectional_time,
            ) = max(
                sectional_candidates,
                key=lambda item: item[0],
            )

        if close(split_sum, race_time):
            coverage_type = "FULL_RACE"
            full_coverage = "true"
            source_rule = (
                "SUPPLIED_SPLIT_SUM_RECONCILES_"
                "TO_RUNNER_RACE_TIME"
            )

        elif close(split_sum, first_sectional_time):
            coverage_type = "PARTIAL_TIMING_WINDOW"
            full_coverage = "false"
            source_rule = (
                "SUPPLIED_SPLIT_SUM_RECONCILES_"
                "TO_FIRST_AVAILABLE_SECTIONAL_MARKER"
            )

        else:
            coverage_type = "UNRESOLVED"
            full_coverage = ""
            source_rule = (
                "SUPPLIED_SPLIT_SUM_DID_NOT_RECONCILE"
            )
            unresolved_runner_keys.append(runner_key)

        coverage_counts[coverage_type] += 1

        race_row = source_race_by_key.get(
            runner["race_key"],
            {},
        )

        race_distance = official_race_distance(
            race_row
        )

        opening_untimed_distance = (
            max(
                race_distance - split_window_start,
                0.0,
            )
            if (
                race_distance is not None
                and split_window_start is not None
            )
            else None
        )

        coverage = {
            "split_coverage_type": coverage_type,
            "split_window_start_marker_metres": (
                numeric(split_window_start)
            ),
            "split_window_finish_marker_metres": (
                numeric(split_window_finish)
            ),
            "split_window_distance_metres": (
                numeric(split_window_distance)
            ),
            "opening_untimed_distance_metres": (
                numeric(opening_untimed_distance)
            ),
            "full_race_split_coverage": (
                full_coverage
            ),
            "split_window_seconds": numeric(split_sum),
            "split_window_source": source_rule,
        }

        coverage_by_runner[runner_key] = coverage
        runner.update(coverage)
        runner["semantic_version"] = SEMANTIC_VERSION

    for split in canonical_splits:
        coverage = coverage_by_runner.get(
            split["runner_key"],
            {},
        )

        for field in SPLIT_COVERAGE_COLUMNS:
            split[field] = coverage.get(field, "")

        split["semantic_version"] = SEMANTIC_VERSION

    race_coverage: dict[
        str,
        Counter[str],
    ] = defaultdict(Counter)

    for runner in canonical_runners:
        race_coverage[
            runner["race_key"]
        ][
            runner["split_coverage_type"]
        ] += 1

    for race in canonical_races:
        counts = race_coverage.get(
            race["race_key"],
            Counter(),
        )

        race[
            "full_race_coverage_runner_count"
        ] = counts.get("FULL_RACE", 0)

        race[
            "partial_timing_window_runner_count"
        ] = counts.get(
            "PARTIAL_TIMING_WINDOW",
            0,
        )

        race[
            "unresolved_coverage_runner_count"
        ] = counts.get("UNRESOLVED", 0)

        race["semantic_version"] = SEMANTIC_VERSION

    for field in RUNNER_COVERAGE_COLUMNS:
        if field not in runner_columns:
            runner_columns.append(field)

    for field in SPLIT_COVERAGE_COLUMNS:
        if field not in split_columns:
            split_columns.append(field)

    for field in RACE_COVERAGE_COLUMNS:
        if field not in race_columns:
            race_columns.append(field)

    write_csv(
        RUNNER_OUT,
        runner_columns,
        canonical_runners,
    )

    write_csv(
        SPLIT_OUT,
        split_columns,
        canonical_splits,
    )

    write_csv(
        RACE_OUT,
        race_columns,
        canonical_races,
    )

    orphan_split_runner_keys = sorted({
        row["runner_key"]
        for row in canonical_splits
        if row["runner_key"] not in coverage_by_runner
    })

    runner_keys = [
        row["runner_key"]
        for row in canonical_runners
    ]

    duplicate_runner_keys = sorted(
        key
        for key, count in Counter(
            runner_keys
        ).items()
        if count > 1
    )

    missing_coverage_rows = [
        row["runner_key"]
        for row in canonical_runners
        if not clean(
            row.get("split_coverage_type")
        )
    ]

    failures = []

    if unresolved_runner_keys:
        failures.append(
            "UNRESOLVED_SPLIT_COVERAGE"
        )

    if orphan_split_runner_keys:
        failures.append(
            "ORPHAN_SPLIT_COVERAGE"
        )

    if duplicate_runner_keys:
        failures.append(
            "DUPLICATE_RUNNER_KEYS"
        )

    if missing_coverage_rows:
        failures.append(
            "MISSING_RUNNER_COVERAGE"
        )

    if len(canonical_runners) != len(source_runners):
        failures.append(
            "RUNNER_COUNT_MISMATCH"
        )

    if len(canonical_splits) != len(source_splits):
        failures.append(
            "SPLIT_COUNT_MISMATCH"
        )

    status = "PASS" if not failures else "FAIL"

    audit = {
        "audit_name": (
            "EDGEIQ_RACINGCOM_CANONICAL_"
            "SPEED_WAREHOUSE_V2_1"
        ),
        "generated_at_utc": generated_at,
        "status": status,
        "failures": failures,
        "warehouse_version": WAREHOUSE_VERSION,
        "semantic_dependency": {
            "file": (
                SEMANTICS_AUDIT
                .relative_to(ROOT)
                .as_posix()
            ),
            "required_status": "PASS",
            "actual_status": semantics.get("status"),
            "semantic_version": SEMANTIC_VERSION,
        },
        "base_builder": {
            "file": (
                BASE_BUILDER
                .relative_to(ROOT)
                .as_posix()
            ),
            "return_code": base_return_code,
            "base_audit_file": (
                BASE_AUDIT_OUT
                .relative_to(ROOT)
                .as_posix()
            ),
        },
        "canonical_counts": {
            "races": len(canonical_races),
            "runners": len(canonical_runners),
            "sectionals": len(
                load_csv(SECTIONAL_OUT)[1]
            ),
            "splits": len(canonical_splits),
        },
        "split_coverage_counts": {
            "FULL_RACE": coverage_counts.get(
                "FULL_RACE",
                0,
            ),
            "PARTIAL_TIMING_WINDOW": (
                coverage_counts.get(
                    "PARTIAL_TIMING_WINDOW",
                    0,
                )
            ),
            "UNRESOLVED": coverage_counts.get(
                "UNRESOLVED",
                0,
            ),
        },
        "unresolved_runner_keys": (
            unresolved_runner_keys
        ),
        "orphan_split_runner_keys": (
            orphan_split_runner_keys
        ),
        "duplicate_runner_keys": (
            duplicate_runner_keys
        ),
        "missing_coverage_rows": (
            missing_coverage_rows
        ),
        "controls": {
            "ratings_calculated": False,
            "standard_times_calculated": False,
            "lengths_vs_standard_calculated": False,
            "estimated_values_created": False,
            "unknown_race_distances_invented": False,
            "opening_untimed_distance_blank_when_unavailable": True,
            "provider_split_values_preserved": True,
            "partial_timing_windows_explicitly_classified": True,
        },
        "outputs": {
            "runner_fact": (
                RUNNER_OUT
                .relative_to(ROOT)
                .as_posix()
            ),
            "sectional_fact": (
                SECTIONAL_OUT
                .relative_to(ROOT)
                .as_posix()
            ),
            "split_fact": (
                SPLIT_OUT
                .relative_to(ROOT)
                .as_posix()
            ),
            "race_fact": (
                RACE_OUT
                .relative_to(ROOT)
                .as_posix()
            ),
        },
    }

    AUDIT_OUT.write_text(
        json.dumps(
            audit,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    log(f"canonical races: {len(canonical_races)}")
    log(f"canonical runners: {len(canonical_runners)}")
    log(f"canonical splits: {len(canonical_splits)}")
    log(
        "full-race coverage runners: "
        f"{coverage_counts.get('FULL_RACE', 0)}"
    )
    log(
        "partial-window runners: "
        f"{coverage_counts.get('PARTIAL_TIMING_WINDOW', 0)}"
    )
    log(
        "unresolved runners: "
        f"{coverage_counts.get('UNRESOLVED', 0)}"
    )
    log(f"audit status: {status}")
    log(f"wrote {RUNNER_OUT.relative_to(ROOT)}")
    log(f"wrote {SECTIONAL_OUT.relative_to(ROOT)}")
    log(f"wrote {SPLIT_OUT.relative_to(ROOT)}")
    log(f"wrote {RACE_OUT.relative_to(ROOT)}")
    log(f"wrote {AUDIT_OUT.relative_to(ROOT)}")

    if status != "PASS":
        log(f"failures: {', '.join(failures)}")
        return 1

    print(
        "EDGEIQ_RACINGCOM_CANONICAL_SPEED_"
        "WAREHOUSE_V2_1_AUDIT_PASS"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
