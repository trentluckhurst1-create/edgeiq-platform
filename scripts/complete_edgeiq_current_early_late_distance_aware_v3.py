from __future__ import annotations

import csv
import json
import math
import os
import re
import shutil

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL = (
    DATA
    / "edgeiq_historical_run_intelligence_fact_v1.csv"
)

RACE_FIELDS = (
    DATA
    / "race_fields.csv"
)

EARLY_CURRENT = (
    DATA
    / "edgeiq_current_early_speed_v1.csv"
)

EARLY_CURRENT_JSON = (
    DATA
    / "edgeiq_current_early_speed_v1.json"
)

LATE_CURRENT = (
    DATA
    / "edgeiq_current_late_speed_v1.csv"
)

LATE_CURRENT_JSON = (
    DATA
    / "edgeiq_current_late_speed_v1.json"
)

BASELINE_DIR = (
    DATA
    / "edgeiq_current_speed_completion_backups"
    / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
)

EARLY_BASELINE = (
    BASELINE_DIR
    / "edgeiq_current_early_speed_v1.csv"
)

LATE_BASELINE = (
    BASELINE_DIR
    / "edgeiq_current_late_speed_v1.csv"
)

AUDIT = (
    DATA
    / "edgeiq_current_speed_distance_aware_completion_v3_audit.csv"
)

SUMMARY = (
    DATA
    / "edgeiq_current_speed_distance_aware_completion_v3_summary.json"
)

BACKUP_DIR = (
    DATA
    / "edgeiq_current_speed_distance_aware_completion_backups"
    / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
)

DISTANCE_TOLERANCE = 400.0
MAX_OBSERVATIONS = 8


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    text = clean(v)

    if not text:
        return None

    try:
        value = float(text)

        if not math.isfinite(value):
            return None

        return value

    except Exception:
        return None


def integer(v):
    value = num(v)

    if value is None:
        return None

    return int(round(value))


def norm_horse(v):
    text = clean(v).upper()

    text = re.sub(
        r"\s*\((NZ|GB|IRE|FR|USA|JPN|SAF|GER|ARG|BRZ|CAN|CHI|ITY|AUS)\)\s*$",
        "",
        text,
    )

    text = (
        text
        .replace("’", "")
        .replace("'", "")
        .replace("`", "")
        .replace("&", "AND")
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )


def norm_track(v):
    text = clean(v).upper()

    text = re.sub(
        r"\b(BET365|SPORTSBET|LADBROKES|PICKLEBET|TAB|THE)\b",
        " ",
        text,
    )

    text = re.sub(
        r"\b(PARK|RACECOURSE|RACING|TRACK)\b",
        " ",
        text,
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )


def race_no(v):
    match = re.search(
        r"\d+",
        clean(v),
    )

    return (
        str(int(match.group(0)))
        if match
        else ""
    )


def race_date(v):
    text = clean(v)[:10]

    if re.match(
        r"^\d{4}-\d{2}-\d{2}$",
        text,
    ):
        return text

    return ""


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        return (
            list(reader),
            reader.fieldnames or [],
        )


def write_csv_atomic(
    path,
    rows,
    fields,
):
    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temp.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)

    os.replace(
        temp,
        path,
    )


def write_projection_json_atomic(
    path,
    schema_version,
    source_version,
    rows,
):
    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    payload = {
        "schemaVersion": schema_version,
        "sourceVersion": source_version,
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),
        "completionVersion": (
            "CURRENT_SPEED_DISTANCE_AWARE_COMPLETION_V3"
        ),
        "runners": rows,
    }

    temp.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    os.replace(
        temp,
        path,
    )


def historical_distance(row):
    for field in (
        "distance",
        "distance_m",
        "race_distance",
        "race_distance_m",
        "race_distance_metres",
    ):
        value = num(
            row.get(field)
        )

        if (
            value is not None
            and value > 0
        ):
            return value

    return None


def historical_metric(
    row,
    phase,
):
    fields = (
        (
            "early_speed",
            "earlySpeed",
            "early_raw",
        )
        if phase == "EARLY"
        else (
            "late_speed",
            "lateSpeed",
            "late_raw",
        )
    )

    for field in fields:

        value = num(
            row.get(field)
        )

        if value is not None:
            return value

    return None


def historical_horse(row):
    for field in (
        "horse",
        "runner",
        "horse_name",
        "runner_name",
        "horse_key",
    ):
        value = clean(
            row.get(field)
        )

        if value:
            return norm_horse(
                value
            )

    return ""


def mean(values):
    if not values:
        return None

    return (
        sum(values)
        / len(values)
    )


def fmt(value):
    if value is None:
        return ""

    return (
        f"{float(value):.4f}"
        .rstrip("0")
        .rstrip(".")
    )


print("=" * 124)
print("EDGEIQ — CURRENT EARLY/LATE DISTANCE-AWARE COMPLETION V3")
print("=" * 124)

for required in (
    HISTORICAL,
    RACE_FIELDS,
    EARLY_CURRENT,
    LATE_CURRENT,
):

    if not required.exists():

        raise RuntimeError(
            f"MISSING_REQUIRED_FILE={required}"
        )


# ==============================================================================
# 1. Confirm immutable baseline
# ==============================================================================

print("")
print("[1] PRE-COMPLETION BASELINE")

BASELINE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

for source, destination in (
    (EARLY_CURRENT, EARLY_BASELINE),
    (LATE_CURRENT, LATE_BASELINE),
):

    shutil.copy2(
        source,
        destination,
    )

    print(
        f"BASELINE_SNAPSHOT={source} -> "
        f"{destination}"
    )

early_base, early_fields = read_csv(
    EARLY_BASELINE
)

late_base, late_fields = read_csv(
    LATE_BASELINE
)

early_baseline_populated = sum(
    1
    for row in early_base
    if num(
        row.get(
            "earlySpeed"
        )
    )
    is not None
)

late_baseline_populated = sum(
    1
    for row in late_base
    if num(
        row.get(
            "lateSpeed"
        )
    )
    is not None
)

print(
    f"EARLY_BASELINE_ROWS="
    f"{len(early_base)}"
)

print(
    f"EARLY_BASELINE_POPULATED="
    f"{early_baseline_populated}"
)

print(
    f"LATE_BASELINE_ROWS="
    f"{len(late_base)}"
)

print(
    f"LATE_BASELINE_POPULATED="
    f"{late_baseline_populated}"
)


# ==============================================================================
# 2. Current runner/race distance authority
# ==============================================================================

print("")
print("[2] CURRENT DISTANCE AUTHORITY")

race_field_rows, _ = read_csv(
    RACE_FIELDS
)

distance_by_runner = {}
distance_by_race = {}

for row in race_field_rows:

    distance = (
        num(
            row.get(
                "distance_m"
            )
        )
        or num(
            row.get(
                "distance"
            )
        )
    )

    if distance is None:
        continue

    date = race_date(
        row.get(
            "race_date"
        )
    )

    track = norm_track(
        row.get(
            "display_track"
        )
        or row.get(
            "track"
        )
    )

    rn = race_no(
        row.get(
            "race_number"
        )
        or row.get(
            "race_no"
        )
    )

    runner_id = clean(
        row.get(
            "runner_id"
        )
    )

    horse = norm_horse(
        row.get(
            "horse"
        )
        or row.get(
            "runner"
        )
    )

    runner_key = (
        date,
        track,
        rn,
        runner_id,
    )

    horse_key = (
        date,
        track,
        rn,
        horse,
    )

    race_key = (
        date,
        track,
        rn,
    )

    if runner_id:
        distance_by_runner[
            runner_key
        ] = distance

    if horse:
        distance_by_runner[
            horse_key
        ] = distance

    existing = distance_by_race.get(
        race_key
    )

    if (
        existing is not None
        and abs(
            existing
            - distance
        )
        > 0.001
    ):

        raise RuntimeError(
            f"INCONSISTENT_RACE_DISTANCE={race_key}"
        )

    distance_by_race[
        race_key
    ] = distance

print(
    f"RACE_FIELD_ROWS="
    f"{len(race_field_rows)}"
)

print(
    f"RUNNER_DISTANCE_KEYS="
    f"{len(distance_by_runner)}"
)

print(
    f"RACE_DISTANCE_KEYS="
    f"{len(distance_by_race)}"
)


# ==============================================================================
# 3. Historical governed observations
# ==============================================================================

print("")
print("[3] HISTORICAL GOVERNED SPEED AUTHORITY")

history = defaultdict(
    lambda: {
        "EARLY": [],
        "LATE": [],
    }
)

historical_rows = 0

with HISTORICAL.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as handle:

    reader = csv.DictReader(handle)

    for row in reader:

        historical_rows += 1

        horse = historical_horse(
            row
        )

        if not horse:
            continue

        date = race_date(
            row.get(
                "race_date"
            )
        )

        distance = historical_distance(
            row
        )

        # Preserve genuine governed phase evidence even when this historical
        # row has no recoverable race distance. Unknown-distance observations
        # cannot qualify for the +/-400m comparable sample below, but remain
        # eligible for the existing all-distance governed fallback.
        early = historical_metric(
            row,
            "EARLY",
        )

        late = historical_metric(
            row,
            "LATE",
        )

        if early is not None:

            history[
                horse
            ][
                "EARLY"
            ].append(
                {
                    "race_date": date,
                    "distance": distance,
                    "value": early,
                }
            )

        if late is not None:

            history[
                horse
            ][
                "LATE"
            ].append(
                {
                    "race_date": date,
                    "distance": distance,
                    "value": late,
                }
            )

        if (
            historical_rows
            % 100000
            == 0
        ):

            print(
                f"HISTORICAL_ROWS_SCANNED="
                f"{historical_rows}"
            )

for horse in history:

    for phase in (
        "EARLY",
        "LATE",
    ):

        history[
            horse
        ][
            phase
        ].sort(
            key=lambda observation: (
                observation[
                    "race_date"
                ]
            ),
            reverse=True,
        )

print(
    f"HISTORICAL_ROWS="
    f"{historical_rows}"
)

print(
    f"HISTORICAL_HORSES_WITH_SPEED="
    f"{len(history)}"
)


# ==============================================================================
# 4. Completion function
# ==============================================================================

def complete(
    baseline_rows,
    phase,
    value_field,
):

    output = []

    audit = []

    counts = Counter()

    for original in baseline_rows:

        row = dict(
            original
        )

        existing = num(
            row.get(
                value_field
            )
        )

        # Original current-engine value:
        # immutable.
        if existing is not None:

            counts[
                "ORIGINAL_VALUE_PRESERVED"
            ] += 1

            output.append(
                row
            )

            continue

        date = race_date(
            row.get(
                "raceDate"
            )
            or row.get(
                "race_date"
            )
        )

        track = norm_track(
            row.get(
                "meeting"
            )
            or row.get(
                "track"
            )
        )

        rn = race_no(
            row.get(
                "raceNumber"
            )
            or row.get(
                "race_number"
            )
        )

        runner_id = clean(
            row.get(
                "runnerId"
            )
            or row.get(
                "runner_id"
            )
        )

        horse_name = clean(
            row.get(
                "runnerName"
            )
            or row.get(
                "runner"
            )
            or row.get(
                "horse"
            )
        )

        horse = norm_horse(
            horse_name
        )

        runner_key = (
            date,
            track,
            rn,
            runner_id,
        )

        horse_key = (
            date,
            track,
            rn,
            horse,
        )

        race_key = (
            date,
            track,
            rn,
        )

        current_distance = (
            distance_by_runner.get(
                runner_key
            )
            or distance_by_runner.get(
                horse_key
            )
            or distance_by_race.get(
                race_key
            )
        )

        observations = (
            history.get(
                horse,
                {}
            ).get(
                phase,
                []
            )
        )

        # Strict no-future leakage.
        eligible = [
            observation
            for observation in observations
            if (
                not date
                or not observation[
                    "race_date"
                ]
                or observation[
                    "race_date"
                ]
                < date
            )
        ]

        comparable = []

        if current_distance is not None:

            comparable = [
                observation
                for observation in eligible
                if (
                    observation[
                        "distance"
                    ]
                    is not None
                    and abs(
                        observation[
                            "distance"
                        ]
                        - current_distance
                    )
                    <= DISTANCE_TOLERANCE
                )
            ]

        selected = []
        method = ""

        if comparable:

            selected = (
                comparable[
                    :MAX_OBSERVATIONS
                ]
            )

            method = (
                "COMPARABLE_DISTANCE_PLUS_MINUS_400M"
            )

        elif eligible:

            selected = (
                eligible[
                    :MAX_OBSERVATIONS
                ]
            )

            method = (
                "ALL_DISTANCE_FALLBACK_NO_COMPARABLE_EVIDENCE"
            )

        else:

            counts[
                "NO_GOVERNED_PHASE_EVIDENCE"
            ] += 1

            audit.append({
                "phase": phase,
                "runner": horse_name,
                "race_date": date,
                "meeting": clean(
                    row.get(
                        "meeting"
                    )
                ),
                "race_number": rn,
                "current_distance": (
                    fmt(
                        current_distance
                    )
                ),
                "eligible_observations": 0,
                "comparable_observations": 0,
                "selected_observations": 0,
                "published_value": "",
                "method": (
                    "NO_GOVERNED_PHASE_EVIDENCE"
                ),
            })

            # EDGEIQ_V3_NO_GOVERNED_STATUS_PROPAGATION_V1
            #
            # V3 has proven that no governed phase observation exists.
            # Preserve the blank value but publish the governed reason
            # instead of leaving the base-builder's ambiguous OTHER status.
            #
            # No value is invented.

            if "evidenceRuns" in row:
                row[
                    "evidenceRuns"
                ] = "0"

            if (
                phase == "LATE"
                and "comparableDistanceRuns"
                in row
            ):
                row[
                    "comparableDistanceRuns"
                ] = "0"

            if "joinMethod" in row:
                row[
                    "joinMethod"
                ] = (
                    "GOVERNED_HISTORY_COMPLETION_V3:"
                    "NO_GOVERNED_PHASE_EVIDENCE"
                )

            if "blankReason" in row:
                row[
                    "blankReason"
                ] = (
                    "NO_GOVERNED_PHASE_EVIDENCE"
                )

            output.append(
                row
            )

            continue

        values = [
            observation[
                "value"
            ]
            for observation in selected
        ]

        published = mean(
            values
        )

        row[
            value_field
        ] = fmt(
            published
        )

        if (
            "evidenceRuns"
            in row
        ):

            row[
                "evidenceRuns"
            ] = str(
                len(
                    selected
                )
            )

        if (
            phase == "LATE"
            and "comparableDistanceRuns"
            in row
        ):

            row[
                "comparableDistanceRuns"
            ] = str(
                len(
                    comparable
                )
            )

        if (
            "joinMethod"
            in row
        ):

            row[
                "joinMethod"
            ] = (
                "GOVERNED_HISTORY_COMPLETION_V3:"
                + method
            )

        if (
            "blankReason"
            in row
        ):

            row[
                "blankReason"
            ] = ""

        counts[
            "POPULATED"
        ] += 1

        counts[
            method
        ] += 1

        if len(
            selected
        ) == 1:

            counts[
                "SINGLE_OBSERVATION"
            ] += 1

        else:

            counts[
                "MULTI_OBSERVATION"
            ] += 1

        audit.append({
            "phase": phase,
            "runner": horse_name,
            "race_date": date,
            "meeting": clean(
                row.get(
                    "meeting"
                )
            ),
            "race_number": rn,
            "current_distance": (
                fmt(
                    current_distance
                )
            ),
            "eligible_observations": (
                len(
                    eligible
                )
            ),
            "comparable_observations": (
                len(
                    comparable
                )
            ),
            "selected_observations": (
                len(
                    selected
                )
            ),
            "published_value": (
                fmt(
                    published
                )
            ),
            "method": method,
        })

        output.append(
            row
        )

    return (
        output,
        audit,
        counts,
    )


# ==============================================================================
# 5. Rebuild Early from immutable baseline
# ==============================================================================

print("")
print("[4] EARLY DISTANCE-AWARE COMPLETION")

(
    early_output,
    early_audit,
    early_counts,
) = complete(
    early_base,
    "EARLY",
    "earlySpeed",
)

for name, value in sorted(
    early_counts.items()
):

    print(
        f"EARLY_{name}="
        f"{value}"
    )


# ==============================================================================
# 6. Rebuild Late from immutable baseline
# ==============================================================================

print("")
print("[5] LATE DISTANCE-AWARE COMPLETION")

(
    late_output,
    late_audit,
    late_counts,
) = complete(
    late_base,
    "LATE",
    "lateSpeed",
)

for name, value in sorted(
    late_counts.items()
):

    print(
        f"LATE_{name}="
        f"{value}"
    )


# ==============================================================================
# 7. Coverage + hard gates
# ==============================================================================

print("")
print("[6] COVERAGE")

early_after = sum(
    1
    for row in early_output
    if num(
        row.get(
            "earlySpeed"
        )
    )
    is not None
)

late_after = sum(
    1
    for row in late_output
    if num(
        row.get(
            "lateSpeed"
        )
    )
    is not None
)

print(
    f"EARLY_POPULATED_BEFORE="
    f"{early_baseline_populated}"
)

print(
    f"EARLY_POPULATED_AFTER="
    f"{early_after}"
)

print(
    f"EARLY_GAIN="
    f"{early_after - early_baseline_populated}"
)

print(
    f"EARLY_BLANK_AFTER="
    f"{len(early_output) - early_after}"
)

print(
    f"LATE_POPULATED_BEFORE="
    f"{late_baseline_populated}"
)

print(
    f"LATE_POPULATED_AFTER="
    f"{late_after}"
)

print(
    f"LATE_GAIN="
    f"{late_after - late_baseline_populated}"
)

print(
    f"LATE_BLANK_AFTER="
    f"{len(late_output) - late_after}"
)

print("")
print("[7] HARD GATES")

checks = {
    "EARLY_ROW_COUNT_CURRENT": (
        len(
            early_output
        )
        == len(
            early_base
        )
    ),

    "LATE_ROW_COUNT_CURRENT": (
        len(
            late_output
        )
        == len(
            late_base
        )
    ),

    "EARLY_ORIGINAL_VALUES_PRESERVED": (
        early_counts[
            "ORIGINAL_VALUE_PRESERVED"
        ]
        == early_baseline_populated
    ),

    "LATE_ORIGINAL_VALUES_PRESERVED": (
        late_counts[
            "ORIGINAL_VALUE_PRESERVED"
        ]
        == late_baseline_populated
    ),

    "EARLY_COVERAGE_NOT_REDUCED": (
        early_after
        >= early_baseline_populated
    ),

    "LATE_COVERAGE_NOT_REDUCED": (
        late_after
        >= late_baseline_populated
    ),

    "CURRENT_DISTANCE_AUTHORITY_GT_ZERO": (
        len(
            distance_by_race
        )
        > 0
    ),
}

quality_checks = {
    "EARLY_COMPARABLE_DISTANCE_GT_ZERO": (
        early_counts[
            "COMPARABLE_DISTANCE_PLUS_MINUS_400M"
        ]
        > 0
    ),

    "LATE_COMPARABLE_DISTANCE_GT_ZERO": (
        late_counts[
            "COMPARABLE_DISTANCE_PLUS_MINUS_400M"
        ]
        > 0
    ),

    "EARLY_GAIN_GT_ZERO": (
        early_after
        > early_baseline_populated
    ),

    "LATE_GAIN_GT_ZERO": (
        late_after
        > late_baseline_populated
    ),
}

for name, passed in checks.items():

    print(
        f"{name}="
        f"{'PASS' if passed else 'FAIL'}"
    )

for name, passed in quality_checks.items():

    print(
        f"{name}="
        f"{'YES' if passed else 'NO'}"
    )

failures = [
    name
    for name, passed
    in checks.items()
    if not passed
]

if failures:

    raise RuntimeError(
        "DISTANCE_AWARE_V3_GATE_FAILED="
        + ",".join(
            failures
        )
    )


# ==============================================================================
# 8. Backup existing current feeds
# ==============================================================================

print("")
print("[8] BACKUP CURRENT FEEDS")

BACKUP_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

for path in (
    EARLY_CURRENT,
    LATE_CURRENT,
):

    destination = (
        BACKUP_DIR
        / path.name
    )

    shutil.copy2(
        path,
        destination,
    )

    print(
        f"BACKUP={path} -> "
        f"{destination}"
    )


# ==============================================================================
# 9. Publish corrected feeds
# ==============================================================================

print("")
print("[9] PUBLISH CORRECTED CURRENT FEEDS")

write_csv_atomic(
    EARLY_CURRENT,
    early_output,
    early_fields,
)

write_projection_json_atomic(
    EARLY_CURRENT_JSON,
    "edgeiq_current_early_speed_v1",
    "CURRENT_EARLY_SPEED_V1",
    early_output,
)

write_csv_atomic(
    LATE_CURRENT,
    late_output,
    late_fields,
)

write_projection_json_atomic(
    LATE_CURRENT_JSON,
    "edgeiq_current_late_speed_v1",
    "CURRENT_LATE_SPEED_V1",
    late_output,
)

audit_rows = (
    early_audit
    + late_audit
)

audit_fields = [
    "phase",
    "runner",
    "race_date",
    "meeting",
    "race_number",
    "current_distance",
    "eligible_observations",
    "comparable_observations",
    "selected_observations",
    "published_value",
    "method",
]

write_csv_atomic(
    AUDIT,
    audit_rows,
    audit_fields,
)

summary = {
    "built_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "baseline_dir": str(
        BASELINE_DIR
    ),

    "distance_tolerance_metres": (
        DISTANCE_TOLERANCE
    ),

    "max_observations": (
        MAX_OBSERVATIONS
    ),

    "early": {
        "baseline_populated": (
            early_baseline_populated
        ),
        "final_populated": (
            early_after
        ),
        "gain": (
            early_after
            - early_baseline_populated
        ),
        "blank_after": (
            len(
                early_output
            )
            - early_after
        ),
        "counts": dict(
            early_counts
        ),
    },

    "late": {
        "baseline_populated": (
            late_baseline_populated
        ),
        "final_populated": (
            late_after
        ),
        "gain": (
            late_after
            - late_baseline_populated
        ),
        "blank_after": (
            len(
                late_output
            )
            - late_after
        ),
        "counts": dict(
            late_counts
        ),
    },

    "checks": {
        name: (
            "PASS"
            if passed
            else "FAIL"
        )
        for name, passed
        in checks.items()
    },

    "quality_checks": {
        name: (
            "YES"
            if passed
            else "NO"
        )
        for name, passed
        in quality_checks.items()
    },

    "policy": (
        "IMMUTABLE_PRE_COMPLETION_BASELINE;"
        "NO_FUTURE_LEAKAGE;"
        "PLUS_MINUS_400M_FIRST;"
        "MOST_RECENT_UP_TO_8;"
        "ARITHMETIC_MEAN;"
        "SINGLE_OBSERVATION_ALLOWED;"
        "ALL_DISTANCE_FALLBACK_ONLY_WHEN_NO_COMPARABLE"
    ),
}

SUMMARY.write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)

print(
    f"EARLY_OUTPUT={EARLY_CURRENT}"
)

print(
    f"LATE_OUTPUT={LATE_CURRENT}"
)

print(
    f"AUDIT={AUDIT}"
)

print(
    f"SUMMARY={SUMMARY}"
)

print("")
print("=" * 124)
print(
    "CURRENT_SPEED_DISTANCE_AWARE_COMPLETION_V3=PASS"
)
print(
    "ORIGINAL_ENGINE_VALUES_OVERWRITTEN=NO"
)
print(
    "COMPARABLE_DISTANCE_METHOD_ACTIVE="
    + (
        "YES"
        if (
            early_counts[
                "COMPARABLE_DISTANCE_PLUS_MINUS_400M"
            ]
            > 0
            or late_counts[
                "COMPARABLE_DISTANCE_PLUS_MINUS_400M"
            ]
            > 0
        )
        else "NO"
    )
)
print("=" * 124)
