from __future__ import annotations

from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import re
import sys

csv.field_size_limit(sys.maxsize)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "public" / "data"


def runtime_paths(data_root: Path):

    data_root = data_root.resolve()

    return {
        "entries":
            data_root
            / "edgeiq_race_entry_fact_v1.csv",

        "snapshot":
            data_root
            / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",

        "epr":
            data_root
            / "edgeiq_epr_horse_performance_rating_fact_v1.csv",

        "authority":
            data_root
            / "edgeiq_race_context_authority_fact_v1.csv",

        "parameters":
            data_root
            / "edgeiq_context_additive_parameter_registry_v1.csv",

        "mappings":
            data_root
            / "edgeiq_context_feature_mapping_registry_v1.csv",

        "context":
            data_root
            / "edgeiq_race_entry_performance_context_fact_v1.csv",

        "eligibility":
            data_root
            / "edgeiq_race_entry_context_eligibility_fact_v1.csv",

        "selection":
            data_root
            / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",

        "adjustment":
            data_root
            / "edgeiq_race_entry_context_adjustment_fact_v1.csv",

        "adjusted":
            data_root
            / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv",
    }

BUILT_AT = (
    datetime.now(timezone.utc)
    .replace(microsecond=0)
    .isoformat()
    .replace("+00:00", "Z")
)

CONTRACT_VERSION = "1.0.0"

CONTEXT_BUILDER = (
    "edgeiq_epr_context_additive_chain_v1.0.0:performance_context"
)

ELIGIBILITY_BUILDER = (
    "edgeiq_epr_context_additive_chain_v1.0.0:eligibility"
)

SELECTION_BUILDER = (
    "edgeiq_epr_context_additive_chain_v1.0.0:selection"
)

ADJUSTMENT_BUILDER = (
    "edgeiq_epr_context_additive_chain_v1.0.0:adjustment"
)

ADJUSTED_BUILDER = (
    "edgeiq_epr_context_additive_chain_v1.0.0:adjusted"
)


def t(v):
    return str(v or "").strip()


def upper(v):
    return t(v).upper()


def dec(v):

    raw = t(v)

    if not raw:
        return None

    m = re.search(
        r"-?\d+(?:\.\d+)?",
        raw,
    )

    if not m:
        return None

    try:
        return Decimal(
            m.group(0)
        )
    except InvalidOperation:
        return None


def dtext(v):
    return format(v, "f")


def sha(parts):

    return hashlib.sha256(
        "\x1f".join(
            t(v)
            for v in parts
        ).encode("utf-8")
    ).hexdigest()


def load(path):

    if not path.exists():
        raise RuntimeError(
            f"MISSING_INPUT={path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        return (
            list(reader.fieldnames or []),
            list(reader),
        )


def write(path, fields, rows):

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="raise",
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)


def relative_barrier(
    barrier,
    field_size,
):

    b = dec(barrier)
    f = dec(field_size)

    if (
        b is None
        or f is None
        or b <= 0
        or f <= 0
    ):
        return ""

    ratio = b / f

    if ratio <= Decimal("0.20"):
        return "INSIDE_20"

    if ratio <= Decimal("0.40"):
        return "20_40"

    if ratio <= Decimal("0.60"):
        return "40_60"

    if ratio <= Decimal("0.80"):
        return "60_80"

    return "OUTSIDE_20"


def field_size_band(value):

    f = dec(value)

    if f is None:
        return ""

    n = int(f)

    if n <= 8:
        return "02_08"

    if n <= 10:
        return "09_10"

    if n <= 12:
        return "11_12"

    if n <= 14:
        return "13_14"

    if n <= 16:
        return "15_16"

    if n <= 20:
        return "17_20"

    return "21_24"


# --------------------------------------------------------------------------------------------------
# LOAD CURRENT AUTHORITIES
# --------------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser()

parser.add_argument(
    "--data-root",
    type=Path,
    default=DEFAULT_DATA,
)

args = parser.parse_args()

DATA = args.data_root.resolve()

PATHS = runtime_paths(
    DATA
)

ENTRIES = PATHS["entries"]
SNAPSHOT = PATHS["snapshot"]
EPR = PATHS["epr"]
AUTHORITY = PATHS["authority"]
PARAMETERS = PATHS["parameters"]
MAPPINGS = PATHS["mappings"]

OUTPUTS = {
    "context":
        PATHS["context"],

    "eligibility":
        PATHS["eligibility"],

    "selection":
        PATHS["selection"],

    "adjustment":
        PATHS["adjustment"],

    "adjusted":
        PATHS["adjusted"],
}

print(
    f"DATA_ROOT={DATA}"
)

_, entries = load(ENTRIES)
_, snapshots = load(SNAPSHOT)
_, epr_rows = load(EPR)
_, authority_rows = load(AUTHORITY)
_, parameter_rows = load(PARAMETERS)
_, mapping_rows = load(MAPPINGS)


if len(parameter_rows) != 87:
    raise RuntimeError(
        f"ADDITIVE_PARAMETER_REGISTRY_NOT_87={len(parameter_rows)}"
    )


# --------------------------------------------------------------------------------------------------
# FEATURE AUTHORITIES
# --------------------------------------------------------------------------------------------------

distance_map = {}

class_map = {}


for row in mapping_rows:

    if (
        row["mapping_status"]
        != "PRODUCTION_ACTIVE"
    ):
        continue

    kind = row["mapping_type"]

    if kind == "DISTANCE_METRES":

        distance_map[
            int(row["source_value"])
        ] = upper(
            row["mapped_value"]
        )

    elif kind == "RACE_CLASS":

        class_map[
            upper(row["source_value"])
        ] = upper(
            row["mapped_value"]
        )


if len(distance_map) != 96:
    raise RuntimeError(
        f"DISTANCE_MAPPING_NOT_96={len(distance_map)}"
    )

if len(class_map) != 559:
    raise RuntimeError(
        f"CLASS_MAPPING_NOT_559={len(class_map)}"
    )


effects = defaultdict(dict)
parameter_ids = defaultdict(dict)


for row in parameter_rows:

    if (
        row["parameter_status"]
        != "PRODUCTION_ACTIVE"
    ):
        continue

    family = upper(
        row["context_family"]
    )

    level = upper(
        row["context_level"]
    )

    value = dec(
        row["adjustment_value"]
    )

    if value is None:
        raise RuntimeError(
            f"INVALID_PARAMETER={family}:{level}"
        )

    if level in effects[family]:
        raise RuntimeError(
            f"DUPLICATE_PARAMETER={family}:{level}"
        )

    effects[family][level] = value

    parameter_ids[family][level] = (
        row[
            "context_additive_parameter_id"
        ]
    )


expected_families = {
    "DISTANCE_BAND": 4,
    "CLASS_GROUP": 71,
    "RELATIVE_BARRIER": 5,
    "FIELD_SIZE_BAND": 7,
}


for family, expected in expected_families.items():

    actual = len(
        effects[family]
    )

    if actual != expected:
        raise RuntimeError(
            f"PARAMETER_FAMILY_COUNT_FAILURE="
            f"{family}:{actual}/{expected}"
        )


# --------------------------------------------------------------------------------------------------
# CURRENT GRAIN INDICES
# --------------------------------------------------------------------------------------------------

entry_by_key = {}


for row in entries:

    race_id = t(
        row.get("canonical_race_id")
    )

    runner_id = t(
        row.get("canonical_runner_id")
    )

    if not race_id or not runner_id:
        continue

    key = (
        race_id,
        runner_id,
    )

    if key in entry_by_key:
        raise RuntimeError(
            f"DUPLICATE_ENTRY={key}"
        )

    entry_by_key[key] = row


snapshot_by_key = {}


for row in snapshots:

    race_id = t(
        row.get("canonical_race_id")
    )

    runner_id = t(
        row.get("canonical_runner_id")
    )

    if not race_id or not runner_id:
        continue

    key = (
        race_id,
        runner_id,
    )

    if key in snapshot_by_key:
        raise RuntimeError(
            f"DUPLICATE_SNAPSHOT={key}"
        )

    snapshot_by_key[key] = row


authority_by_race = {}


for row in authority_rows:

    race_id = t(
        row.get("canonical_race_id")
    )

    if not race_id:
        continue

    if race_id in authority_by_race:
        raise RuntimeError(
            f"DUPLICATE_RACE_AUTHORITY={race_id}"
        )

    authority_by_race[race_id] = row


epr_groups = defaultdict(list)


for row in epr_rows:

    horse_id = t(
        row.get("canonical_horse_id")
    )

    if horse_id:
        epr_groups[horse_id].append(row)


epr_by_horse = {}


for horse_id, rows in epr_groups.items():

    epr_by_horse[horse_id] = sorted(
        rows,
        key=lambda row: (
            t(
                row.get("rating_as_of_date")
            ),
            t(
                row.get(
                    "horse_performance_rating_id"
                )
            ),
        ),
        reverse=True,
    )[0]


# Only currently active entries participate.
active_entries = [
    row
    for row in entries
    if upper(
        row.get("scratching_status")
    ) == "ACTIVE"
]


field_size_by_race = Counter(
    t(
        row.get("canonical_race_id")
    )
    for row in active_entries
)


# Governed EPR-backed race-entry population.
population = []


for entry in active_entries:

    race_id = t(
        entry.get("canonical_race_id")
    )

    runner_id = t(
        entry.get("canonical_runner_id")
    )

    key = (
        race_id,
        runner_id,
    )

    snapshot = snapshot_by_key.get(key)

    if snapshot is None:
        continue

    horse_id = t(
        snapshot.get("canonical_horse_id")
    )

    if not horse_id:
        continue

    epr = epr_by_horse.get(
        horse_id
    )

    if epr is None:
        continue

    epr_value = dec(
        epr.get(
            "horse_performance_rating_value"
        )
    )

    if epr_value is None:
        continue

    authority = authority_by_race.get(
        race_id
    )

    if authority is None:
        raise RuntimeError(
            f"MISSING_RACE_AUTHORITY={race_id}"
        )

    official_class = t(
        authority.get("race_class_code")
    )

    # EDGEIQ_C12R6_RACE_FIELDS_CLASS_FALLBACK
    #
    # Governing current-race class fallback:
    # if canonical race authority has no race_class_code,
    # resolve the exact race from governed race_fields.csv.
    #
    # Matching contract:
    #   race date
    #   normalised track
    #   race number
    #   distance
    #
    # Fail closed on zero or conflicting class values.

    if not official_class:

        import csv as _edgeiq_class_csv
        import re as _edgeiq_class_re

        def _edgeiq_norm_track(value):
            return _edgeiq_class_re.sub(
                r"[^A-Z0-9]+",
                "",
                str(value or "").strip().upper(),
            )

        _race_fields_path = DATA / "race_fields.csv"

        _parts = str(race_id).split("|")

        if len(_parts) < 5:
            raise RuntimeError(
                f"INVALID_CANONICAL_RACE_ID_FOR_CLASS={race_id}"
            )

        _target_date = _parts[1]
        _target_track = _edgeiq_norm_track(_parts[2])

        _target_race_no = (
            _parts[3][1:]
            if _parts[3].upper().startswith("R")
            else _parts[3]
        )

        _target_distance = (
            _parts[4][:-1]
            if _parts[4].upper().endswith("M")
            else _parts[4]
        )

        _class_values = set()

        if _race_fields_path.exists():

            with _race_fields_path.open(
                "r",
                encoding="utf-8-sig",
                errors="replace",
                newline="",
            ) as _rf:

                _reader = _edgeiq_class_csv.DictReader(
                    _rf
                )

                for _row in _reader:

                    if (
                        str(
                            _row.get("race_date") or ""
                        ).strip()
                        != _target_date
                    ):
                        continue

                    if (
                        _edgeiq_norm_track(
                            _row.get("track")
                            or
                            _row.get("display_track")
                        )
                        != _target_track
                    ):
                        continue

                    _row_race_no = str(
                        _row.get("race_no")
                        or
                        _row.get("race_number")
                        or
                        ""
                    ).strip()

                    if (
                        _row_race_no
                        != _target_race_no
                    ):
                        continue

                    _row_distance = str(
                        _row.get("distance_m")
                        or
                        _row.get("distance")
                        or
                        ""
                    ).strip()

                    _row_distance = (
                        _row_distance[:-1]
                        if _row_distance.lower().endswith("m")
                        else _row_distance
                    )

                    if (
                        _row_distance
                        != _target_distance
                    ):
                        continue

                    _candidate_class = str(
                        _row.get("race_class")
                        or
                        _row.get("class")
                        or
                        ""
                    ).strip()

                    if _candidate_class:
                        _class_values.add(
                            _candidate_class
                        )

        if len(_class_values) == 1:

            official_class = next(
                iter(_class_values)
            )

        elif len(_class_values) > 1:

            raise RuntimeError(
                f"CONFLICTING_OFFICIAL_RACE_CLASS="
                f"{race_id}|"
                + "|".join(
                    sorted(_class_values)
                )
            )

    if not official_class:

        raise RuntimeError(
            f"MISSING_OFFICIAL_RACE_CLASS={race_id}"
        )

    distance = dec(
        entry.get("race_distance_metres")
    )

    if distance is None:
        raise RuntimeError(
            f"MISSING_DISTANCE={key}"
        )

    distance_level = distance_map.get(
        int(distance),
        "",
    )

    class_level = class_map.get(
        upper(official_class),
        "",
    )

    barrier_level = relative_barrier(
        entry.get("barrier"),
        field_size_by_race[race_id],
    )

    field_level = field_size_band(
        field_size_by_race[race_id]
    )

    missing = []

    for family, level in {
        "DISTANCE_BAND":
            distance_level,

        "CLASS_GROUP":
            class_level,

        "RELATIVE_BARRIER":
            barrier_level,

        "FIELD_SIZE_BAND":
            field_level,
    }.items():

        if not level:
            missing.append(
                f"{family}:UNRESOLVED"
            )

        elif level not in effects[family]:
            missing.append(
                f"{family}:{level}"
            )


    if missing:
        raise RuntimeError(
            f"UNSUPPORTED_CURRENT_FEATURE={key}|"
            + "|".join(missing)
        )


    population.append(
        {
            "entry":
                entry,

            "snapshot":
                snapshot,

            "epr":
                epr,

            "authority":
                authority,

            "race_id":
                race_id,

            "runner_id":
                runner_id,

            "horse_id":
                horse_id,

            "epr_value":
                epr_value,

            "distance_level":
                distance_level,

            "class_level":
                class_level,

            "barrier_level":
                barrier_level,

            "field_level":
                field_level,

            "field_size":
                field_size_by_race[
                    race_id
                ],
        }
    )


print(
    f"ACTIVE_ENTRY_ROWS={len(active_entries)}"
)

print(
    f"EPR_BACKED_CONTEXT_POPULATION={len(population)}"
)


# --------------------------------------------------------------------------------------------------
# CLASS POLICY
# --------------------------------------------------------------------------------------------------

ALLOWED = {
    "BENCHMARK",
    "BLACKTYPE",
    "OPEN",
    "PICNIC",
}

GATED = {
    "MAIDEN",
    "QUALITY",
    "HURDLE",
}


# --------------------------------------------------------------------------------------------------
# SCHEMAS
# --------------------------------------------------------------------------------------------------

CONTEXT_FIELDS = [
    "race_entry_performance_context_id",
    "race_entry_horse_performance_snapshot_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "selected_horse_performance_rating_id",
    "selected_rating_as_of_date",
    "rating_age_days",
    "context_historical_rating_value",
    "race_distance_m",
    "race_class_code",
    "track_id",
    "track_name",
    "track_configuration",
    "track_condition",
    "racing_surface",
    "rail_position",
    "barrier",
    "allocated_weight_kg",
    "declared_field_size",
    "race_entry_performance_context_status",
    "source_snapshot_evidence_sha256",
    "source_race_entry_evidence_sha256",
    "race_entry_performance_context_evidence_sha256",
    "source_snapshot_builder_version",
    "source_race_entry_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

ELIGIBILITY_FIELDS = [
    "race_entry_context_eligibility_id",
    "race_entry_performance_context_id",
    "race_entry_horse_performance_snapshot_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "historical_rating_eligibility",
    "distance_context_eligibility",
    "class_context_eligibility",
    "track_context_eligibility",
    "track_configuration_eligibility",
    "track_condition_eligibility",
    "surface_context_eligibility",
    "rail_context_eligibility",
    "barrier_context_eligibility",
    "allocated_weight_eligibility",
    "field_size_eligibility",
    "complete_context_eligibility",
    "primary_context_eligibility_reason_code",
    "race_entry_context_eligibility_status",
    "source_context_evidence_sha256",
    "race_entry_context_eligibility_evidence_sha256",
    "source_context_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

SELECTION_FIELDS = [
    "race_entry_context_parameter_selection_id",
    "race_entry_context_eligibility_id",
    "race_entry_performance_context_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "complete_context_eligibility",
    "source_context_eligibility_reason_code",
    "race_distance_m",
    "race_class_code",
    "track_id",
    "track_configuration",
    "track_condition",
    "racing_surface",
    "barrier_band",
    "weight_band",
    "field_size_band",
    "context_signature_sha256",
    "context_parameter_id",
    "context_parameter_selection_decision",
    "race_entry_context_parameter_selection_status",
    "source_eligibility_evidence_sha256",
    "source_context_evidence_sha256",
    "source_parameter_evidence_sha256",
    "race_entry_context_parameter_selection_evidence_sha256",
    "source_eligibility_builder_version",
    "source_context_builder_version",
    "source_parameter_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

ADJUSTMENT_FIELDS = [
    "race_entry_context_adjustment_id",
    "race_entry_context_parameter_selection_id",
    "race_entry_context_eligibility_id",
    "race_entry_performance_context_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "historical_rating_value",
    "context_parameter_id",
    "source_parameter_selection_decision",
    "distance_adjustment",
    "class_adjustment",
    "track_adjustment",
    "track_configuration_adjustment",
    "track_condition_adjustment",
    "surface_adjustment",
    "barrier_adjustment",
    "weight_adjustment",
    "field_size_adjustment",
    "total_context_adjustment",
    "context_adjustment_application_decision",
    "race_entry_context_adjustment_status",
    "source_selection_evidence_sha256",
    "source_context_evidence_sha256",
    "source_parameter_evidence_sha256",
    "race_entry_context_adjustment_evidence_sha256",
    "source_selection_builder_version",
    "source_context_builder_version",
    "source_parameter_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

ADJUSTED_FIELDS = [
    "race_entry_context_adjusted_performance_id",
    "race_entry_context_adjustment_id",
    "race_entry_context_parameter_selection_id",
    "race_entry_context_eligibility_id",
    "race_entry_performance_context_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "historical_rating_value",
    "context_parameter_id",
    "total_context_adjustment",
    "context_adjusted_performance_value",
    "source_adjustment_decision",
    "context_adjusted_performance_decision",
    "race_entry_context_adjusted_performance_status",
    "source_adjustment_evidence_sha256",
    "race_entry_context_adjusted_performance_evidence_sha256",
    "source_adjustment_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


context_rows = []
eligibility_rows = []
selection_rows = []
adjustment_rows = []
adjusted_rows = []


for item in population:

    entry = item["entry"]
    snapshot = item["snapshot"]
    epr = item["epr"]
    authority = item["authority"]

    race_id = item["race_id"]
    runner_id = item["runner_id"]
    horse_id = item["horse_id"]
    base = item["epr_value"]

    distance_level = item[
        "distance_level"
    ]

    class_level = item[
        "class_level"
    ]

    barrier_level = item[
        "barrier_level"
    ]

    field_level = item[
        "field_level"
    ]


    if class_level in ALLOWED:
        class_policy = "CONTEXT_ALLOWED"

    elif class_level in GATED:
        class_policy = (
            "CONTEXT_BLOCKED_UNSTABLE_CLASS"
        )

    else:
        class_policy = (
            "CONTEXT_BLOCKED_UNVALIDATED_CLASS"
        )


    race_entry_id = (
        t(
            snapshot.get("race_entry_id")
        )
        or t(
            entry.get("race_entry_id")
        )
    )

    if not race_entry_id:

        race_entry_id = (
            "SHADOW-RE-"
            + sha(
                [
                    race_id,
                    runner_id,
                ]
            )[:24].upper()
        )


    snapshot_id = (
        t(
            snapshot.get(
                "race_entry_horse_performance_snapshot_id"
            )
        )
        or (
            "SHADOW-SNAP-"
            + sha(
                [
                    race_id,
                    runner_id,
                    horse_id,
                ]
            )[:24].upper()
        )
    )


    context_id = (
        "EIQ-REPC1-"
        + sha(
            [
                CONTRACT_VERSION,
                race_entry_id,
                snapshot_id,
                race_id,
                runner_id,
                horse_id,
                t(
                    authority.get(
                        "race_class_code"
                    )
                ),
                t(
                    entry.get(
                        "race_distance_metres"
                    )
                ),
            ]
        )[:24].upper()
    )


    context_evidence = sha(
        [
            context_id,
            t(
                epr.get(
                    "horse_performance_rating_id"
                )
            ),
            dtext(base),
            t(
                authority.get(
                    "race_class_code"
                )
            ),
            t(
                entry.get("barrier")
            ),
            item["field_size"],
        ]
    )


    context = {
        "race_entry_performance_context_id":
            context_id,

        "race_entry_horse_performance_snapshot_id":
            snapshot_id,

        "race_entry_id":
            race_entry_id,

        "race_id":
            race_id,

        "race_date":
            t(
                entry.get("race_date")
            ),

        "runner_id":
            runner_id,

        "canonical_horse_id":
            horse_id,

        "canonical_horse_name":
            t(
                epr.get(
                    "canonical_horse_name"
                )
            )
            or t(
                entry.get("runner_name")
            ),

        "selected_horse_performance_rating_id":
            t(
                epr.get(
                    "horse_performance_rating_id"
                )
            ),

        "selected_rating_as_of_date":
            t(
                epr.get("rating_as_of_date")
            ),

        "rating_age_days":
            "",

        "context_historical_rating_value":
            dtext(base),

        "race_distance_m":
            t(
                entry.get(
                    "race_distance_metres"
                )
            ),

        "race_class_code":
            t(
                authority.get(
                    "race_class_code"
                )
            ),

        "track_id":
            t(
                entry.get(
                    "canonical_track"
                )
            ),

        "track_name":
            t(
                entry.get(
                    "canonical_track"
                )
            ),

        "track_configuration":
            t(
                entry.get(
                    "course_identity"
                )
            ),

        "track_condition":
            t(
                entry.get(
                    "track_condition_number"
                )
            ),

        "racing_surface":
            t(
                entry.get(
                    "surface_group"
                )
            ),

        "rail_position":
            t(
                authority.get(
                    "rail_position"
                )
            ),

        "barrier":
            t(
                entry.get("barrier")
            ),

        "allocated_weight_kg":
            t(
                entry.get("weight_kg")
            ),

        "declared_field_size":
            str(
                item["field_size"]
            ),

        "race_entry_performance_context_status":
            "CONTEXT_AVAILABLE",

        "source_snapshot_evidence_sha256":
            t(
                snapshot.get(
                    "race_entry_horse_performance_snapshot_evidence_sha256"
                )
            ),

        "source_race_entry_evidence_sha256":
            t(
                entry.get("source_hash")
            ),

        "race_entry_performance_context_evidence_sha256":
            context_evidence,

        "source_snapshot_builder_version":
            t(
                snapshot.get(
                    "builder_version"
                )
            ),

        "source_race_entry_builder_version":
            t(
                entry.get("source_system")
            ),

        "builder_version":
            CONTEXT_BUILDER,

        "contract_version":
            CONTRACT_VERSION,

        "built_at_utc":
            BUILT_AT,
    }


    eligibility_id = (
        "EIQ-RECE1-"
        + sha(
            [
                context_id,
                race_entry_id,
                horse_id,
            ]
        )[:24].upper()
    )


    eligibility_evidence = sha(
        [
            eligibility_id,
            context_evidence,
            "ELIGIBLE",
            class_policy,
        ]
    )


    eligibility = {
        "race_entry_context_eligibility_id":
            eligibility_id,

        "race_entry_performance_context_id":
            context_id,

        "race_entry_horse_performance_snapshot_id":
            snapshot_id,

        "race_entry_id":
            race_entry_id,

        "race_id":
            race_id,

        "race_date":
            context["race_date"],

        "runner_id":
            runner_id,

        "canonical_horse_id":
            horse_id,

        "canonical_horse_name":
            context[
                "canonical_horse_name"
            ],

        "historical_rating_eligibility":
            "ELIGIBLE",

        "distance_context_eligibility":
            "ELIGIBLE",

        "class_context_eligibility":
            "ELIGIBLE",

        "track_context_eligibility":
            "NOT_REQUIRED_BY_ADDITIVE_V1",

        "track_configuration_eligibility":
            "NOT_REQUIRED_BY_ADDITIVE_V1",

        "track_condition_eligibility":
            "NOT_REQUIRED_BY_ADDITIVE_V1",

        "surface_context_eligibility":
            "NOT_REQUIRED_BY_ADDITIVE_V1",

        "rail_context_eligibility":
            "NOT_REQUIRED_BY_ADDITIVE_V1",

        "barrier_context_eligibility":
            "ELIGIBLE",

        "allocated_weight_eligibility":
            "NOT_REQUIRED_BY_ADDITIVE_V1",

        "field_size_eligibility":
            "ELIGIBLE",

        "complete_context_eligibility":
            "ELIGIBLE",

        "primary_context_eligibility_reason_code":
            (
                "ADDITIVE_CONTEXT_ALLOWED"
                if class_policy
                == "CONTEXT_ALLOWED"
                else
                "ADDITIVE_CONTEXT_CLASS_GATED"
            ),

        "race_entry_context_eligibility_status":
            "ELIGIBLE",

        "source_context_evidence_sha256":
            context_evidence,

        "race_entry_context_eligibility_evidence_sha256":
            eligibility_evidence,

        "source_context_builder_version":
            CONTEXT_BUILDER,

        "builder_version":
            ELIGIBILITY_BUILDER,

        "contract_version":
            CONTRACT_VERSION,

        "built_at_utc":
            BUILT_AT,
    }


    family_levels = {
        "DISTANCE_BAND":
            distance_level,

        "CLASS_GROUP":
            class_level,

        "RELATIVE_BARRIER":
            barrier_level,

        "FIELD_SIZE_BAND":
            field_level,
    }


    selected_parameter_ids = [
        parameter_ids[family][level]
        for family, level
        in family_levels.items()
    ]


    bundle_id = (
        "EIQ-ADDITIVE-BUNDLE-"
        + sha(
            selected_parameter_ids
        )[:24].upper()
    )


    signature = sha(
        [
            context[
                "race_distance_m"
            ],
            context[
                "race_class_code"
            ],
            distance_level,
            class_level,
            barrier_level,
            field_level,
            class_policy,
        ]
    )


    selection_id = (
        "EIQ-RECPS1-"
        + sha(
            [
                eligibility_id,
                bundle_id,
                signature,
            ]
        )[:24].upper()
    )


    selection_decision = (
        "ADDITIVE_PARAMETERS_SELECTED"
        if class_policy
        == "CONTEXT_ALLOWED"
        else
        "ADDITIVE_CLASS_GATED_ZERO_ADJUSTMENT"
    )


    parameter_evidence = sha(
        selected_parameter_ids
    )


    selection_evidence = sha(
        [
            selection_id,
            bundle_id,
            *selected_parameter_ids,
            selection_decision,
            signature,
        ]
    )


    selection = {
        "race_entry_context_parameter_selection_id":
            selection_id,

        "race_entry_context_eligibility_id":
            eligibility_id,

        "race_entry_performance_context_id":
            context_id,

        "race_entry_id":
            race_entry_id,

        "race_id":
            race_id,

        "race_date":
            context["race_date"],

        "runner_id":
            runner_id,

        "canonical_horse_id":
            horse_id,

        "canonical_horse_name":
            context[
                "canonical_horse_name"
            ],

        "complete_context_eligibility":
            "ELIGIBLE",

        "source_context_eligibility_reason_code":
            eligibility[
                "primary_context_eligibility_reason_code"
            ],

        "race_distance_m":
            context[
                "race_distance_m"
            ],

        "race_class_code":
            context[
                "race_class_code"
            ],

        "track_id":
            context[
                "track_id"
            ],

        "track_configuration":
            context[
                "track_configuration"
            ],

        "track_condition":
            context[
                "track_condition"
            ],

        "racing_surface":
            context[
                "racing_surface"
            ],

        "barrier_band":
            barrier_level,

        "weight_band":
            "NOT_USED_ADDITIVE_V1",

        "field_size_band":
            field_level,

        "context_signature_sha256":
            signature,

        "context_parameter_id":
            bundle_id,

        "context_parameter_selection_decision":
            selection_decision,

        "race_entry_context_parameter_selection_status":
            "ADDITIVE_SELECTION_COMPLETE",

        "source_eligibility_evidence_sha256":
            eligibility_evidence,

        "source_context_evidence_sha256":
            context_evidence,

        "source_parameter_evidence_sha256":
            parameter_evidence,

        "race_entry_context_parameter_selection_evidence_sha256":
            selection_evidence,

        "source_eligibility_builder_version":
            ELIGIBILITY_BUILDER,

        "source_context_builder_version":
            CONTEXT_BUILDER,

        "source_parameter_builder_version":
            "edgeiq_context_additive_parameter_registry_v1.0.0",

        "builder_version":
            SELECTION_BUILDER,

        "contract_version":
            CONTRACT_VERSION,

        "built_at_utc":
            BUILT_AT,
    }


    if class_policy == "CONTEXT_ALLOWED":

        distance_adjustment = effects[
            "DISTANCE_BAND"
        ][distance_level]

        class_adjustment = effects[
            "CLASS_GROUP"
        ][class_level]

        barrier_adjustment = effects[
            "RELATIVE_BARRIER"
        ][barrier_level]

        field_adjustment = effects[
            "FIELD_SIZE_BAND"
        ][field_level]

    else:

        distance_adjustment = Decimal("0")
        class_adjustment = Decimal("0")
        barrier_adjustment = Decimal("0")
        field_adjustment = Decimal("0")


    total = (
        distance_adjustment
        + class_adjustment
        + barrier_adjustment
        + field_adjustment
    )


    adjustment_id = (
        "EIQ-RECA1-"
        + sha(
            [
                selection_id,
                dtext(total),
            ]
        )[:24].upper()
    )


    adjustment_evidence = sha(
        [
            adjustment_id,
            selection_evidence,
            dtext(distance_adjustment),
            dtext(class_adjustment),
            dtext(barrier_adjustment),
            dtext(field_adjustment),
            dtext(total),
        ]
    )


    application_decision = (
        "ADDITIVE_CONTEXT_APPLIED"
        if class_policy
        == "CONTEXT_ALLOWED"
        else
        "ADDITIVE_CLASS_GATED_ZERO_ADJUSTMENT"
    )


    adjustment = {
        "race_entry_context_adjustment_id":
            adjustment_id,

        "race_entry_context_parameter_selection_id":
            selection_id,

        "race_entry_context_eligibility_id":
            eligibility_id,

        "race_entry_performance_context_id":
            context_id,

        "race_entry_id":
            race_entry_id,

        "race_id":
            race_id,

        "race_date":
            context["race_date"],

        "runner_id":
            runner_id,

        "canonical_horse_id":
            horse_id,

        "canonical_horse_name":
            context[
                "canonical_horse_name"
            ],

        "historical_rating_value":
            dtext(base),

        "context_parameter_id":
            bundle_id,

        "source_parameter_selection_decision":
            selection_decision,

        "distance_adjustment":
            dtext(distance_adjustment),

        "class_adjustment":
            dtext(class_adjustment),

        "track_adjustment":
            "0",

        "track_configuration_adjustment":
            "0",

        "track_condition_adjustment":
            "0",

        "surface_adjustment":
            "0",

        "barrier_adjustment":
            dtext(barrier_adjustment),

        "weight_adjustment":
            "0",

        "field_size_adjustment":
            dtext(field_adjustment),

        "total_context_adjustment":
            dtext(total),

        "context_adjustment_application_decision":
            application_decision,

        "race_entry_context_adjustment_status":
            "ADDITIVE_ADJUSTMENT_COMPLETE",

        "source_selection_evidence_sha256":
            selection_evidence,

        "source_context_evidence_sha256":
            context_evidence,

        "source_parameter_evidence_sha256":
            parameter_evidence,

        "race_entry_context_adjustment_evidence_sha256":
            adjustment_evidence,

        "source_selection_builder_version":
            SELECTION_BUILDER,

        "source_context_builder_version":
            CONTEXT_BUILDER,

        "source_parameter_builder_version":
            "edgeiq_context_additive_parameter_registry_v1.0.0",

        "builder_version":
            ADJUSTMENT_BUILDER,

        "contract_version":
            CONTRACT_VERSION,

        "built_at_utc":
            BUILT_AT,
    }


    adjusted_value = (
        base + total
    )


    adjusted_id = (
        "EIQ-RECAP1-"
        + sha(
            [
                adjustment_id,
                dtext(adjusted_value),
            ]
        )[:24].upper()
    )


    adjusted_evidence = sha(
        [
            adjusted_id,
            adjustment_evidence,
            dtext(base),
            dtext(total),
            dtext(adjusted_value),
        ]
    )


    adjusted = {
        "race_entry_context_adjusted_performance_id":
            adjusted_id,

        "race_entry_context_adjustment_id":
            adjustment_id,

        "race_entry_context_parameter_selection_id":
            selection_id,

        "race_entry_context_eligibility_id":
            eligibility_id,

        "race_entry_performance_context_id":
            context_id,

        "race_entry_id":
            race_entry_id,

        "race_id":
            race_id,

        "race_date":
            context["race_date"],

        "runner_id":
            runner_id,

        "canonical_horse_id":
            horse_id,

        "canonical_horse_name":
            context[
                "canonical_horse_name"
            ],

        "historical_rating_value":
            dtext(base),

        "context_parameter_id":
            bundle_id,

        "total_context_adjustment":
            dtext(total),

        "context_adjusted_performance_value":
            dtext(adjusted_value),

        "source_adjustment_decision":
            application_decision,

        "context_adjusted_performance_decision":
            "PERFORMANCE_ADJUSTED",

        "race_entry_context_adjusted_performance_status":
            "ADJUSTED_PERFORMANCE_AVAILABLE",

        "source_adjustment_evidence_sha256":
            adjustment_evidence,

        "race_entry_context_adjusted_performance_evidence_sha256":
            adjusted_evidence,

        "source_adjustment_builder_version":
            ADJUSTMENT_BUILDER,

        "builder_version":
            ADJUSTED_BUILDER,

        "contract_version":
            CONTRACT_VERSION,

        "built_at_utc":
            BUILT_AT,
    }


    context_rows.append(context)
    eligibility_rows.append(eligibility)
    selection_rows.append(selection)
    adjustment_rows.append(adjustment)
    adjusted_rows.append(adjusted)


# --------------------------------------------------------------------------------------------------
# STRICT INTERNAL GATES
# --------------------------------------------------------------------------------------------------

count = len(population)


if not (
    len(context_rows)
    == len(eligibility_rows)
    == len(selection_rows)
    == len(adjustment_rows)
    == len(adjusted_rows)
    == count
):
    raise RuntimeError(
        "ADDITIVE_CHAIN_ROW_ACCOUNTING_FAILURE"
    )


applied = sum(
    1
    for row in adjustment_rows
    if row[
        "context_adjustment_application_decision"
    ]
    == "ADDITIVE_CONTEXT_APPLIED"
)


gated = sum(
    1
    for row in adjustment_rows
    if row[
        "context_adjustment_application_decision"
    ]
    == "ADDITIVE_CLASS_GATED_ZERO_ADJUSTMENT"
)


large = sum(
    1
    for row in adjustment_rows
    if abs(
        dec(
            row["total_context_adjustment"]
        )
        or Decimal("0")
    )
    >= Decimal("5")
)


if large:
    raise RuntimeError(
        f"EXTREME_ADJUSTMENT_FAILURE={large}"
    )


write(
    OUTPUTS["context"],
    CONTEXT_FIELDS,
    context_rows,
)

write(
    OUTPUTS["eligibility"],
    ELIGIBILITY_FIELDS,
    eligibility_rows,
)

write(
    OUTPUTS["selection"],
    SELECTION_FIELDS,
    selection_rows,
)

write(
    OUTPUTS["adjustment"],
    ADJUSTMENT_FIELDS,
    adjustment_rows,
)

write(
    OUTPUTS["adjusted"],
    ADJUSTED_FIELDS,
    adjusted_rows,
)


print(
    f"PERFORMANCE_CONTEXT_ROWS={len(context_rows)}"
)

print(
    f"ELIGIBILITY_ROWS={len(eligibility_rows)}"
)

print(
    f"SELECTION_ROWS={len(selection_rows)}"
)

print(
    f"ADJUSTMENT_ROWS={len(adjustment_rows)}"
)

print(
    f"ADJUSTED_ROWS={len(adjusted_rows)}"
)

print(
    f"ADDITIVE_CONTEXT_APPLIED_ROWS={applied}"
)

print(
    f"ADDITIVE_CLASS_GATED_ROWS={gated}"
)

print(
    f"ABS_ADJUSTMENT_GTE_5_ROWS={large}"
)

print(
    "EDGEIQ_EPR_CONTEXT_DYNAMIC_ADDITIVE_CHAIN=PASS"
)
