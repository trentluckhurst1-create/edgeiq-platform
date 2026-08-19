from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = (
    DATA
    / "edgeiq_race_entry_performance_context_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_context_eligibility_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_context_eligibility_fact_v1.0.0"
)

SOURCE_CONTEXT_STATUS = (
    "FACTUAL_DECLARED_RACE_CONTEXT_GOVERNED"
)

ELIGIBLE = "ELIGIBLE"
MISSING = "INELIGIBLE_MISSING_CONTEXT"
INVALID = "INELIGIBLE_INVALID_CONTEXT"
UNSUPPORTED = "INELIGIBLE_UNSUPPORTED_CONTEXT"

COMPLETE_ELIGIBLE = "COMPLETE_CONTEXT_ELIGIBLE"
COMPLETE_INELIGIBLE = "COMPLETE_CONTEXT_INELIGIBLE"

OUTPUT_FIELDS = [
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


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


def normalise_token(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        text(value).upper(),
    )


def sha256_payload(
    parts: Iterable[object],
) -> str:
    payload = "\x1f".join(
        text(part)
        for part in parts
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def parse_decimal(
    value: object,
) -> Decimal | None:
    raw = text(value)

    if not raw:
        return None

    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return None

    if not parsed.is_finite():
        return None

    return parsed


def parse_integer(
    value: object,
) -> int | None:
    raw = text(value)

    if not raw:
        return None

    try:
        return int(raw)
    except ValueError:
        return None


def read_csv(
    path: Path,
) -> tuple[
    list[str],
    list[dict[str, str]],
]:
    if not path.exists():
        fail(
            f"Missing canonical input: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(
                f"Missing CSV header: {path}"
            )

        return (
            list(reader.fieldnames),
            list(reader),
        )


def require_fields(
    actual_fields: list[str],
    required_fields: Iterable[str],
) -> None:
    missing = [
        field
        for field in required_fields
        if field not in actual_fields
    ]

    if missing:
        fail(
            f"{INPUT_PATH.name} missing required fields: "
            f"{missing}"
        )


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )

    os.close(file_descriptor)

    temporary_path = Path(
        temporary_name
    )

    try:
        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=OUTPUT_FIELDS,
                extrasaction="raise",
                lineterminator="\n",
            )

            writer.writeheader()
            writer.writerows(rows)

        os.replace(
            temporary_path,
            path,
        )
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def text_eligibility(
    value: object,
) -> str:
    return (
        ELIGIBLE
        if text(value)
        else MISSING
    )


def historical_rating_eligibility(
    value: object,
) -> str:
    if not text(value):
        return MISSING

    parsed = parse_decimal(value)

    if parsed is None:
        return INVALID

    return ELIGIBLE


def distance_eligibility(
    value: object,
) -> str:
    if not text(value):
        return MISSING

    parsed = parse_integer(value)

    if parsed is None or parsed <= 0:
        return INVALID

    if parsed < 400 or parsed > 5000:
        return UNSUPPORTED

    return ELIGIBLE


def track_eligibility(
    track_id: object,
    track_name: object,
) -> str:
    if not text(track_id) or not text(track_name):
        return MISSING

    return ELIGIBLE


def track_condition_eligibility(
    value: object,
) -> str:
    token = normalise_token(value)

    if not token:
        return MISSING

    supported_patterns = (
        r"^FIRM(?: [12])?$",
        r"^GOOD(?: [34])?$",
        r"^SOFT(?: [567])?$",
        r"^HEAVY(?: (?:8|9|10))?$",
        r"^SYNTHETIC$",
    )

    if any(
        re.fullmatch(
            pattern,
            token,
        )
        for pattern in supported_patterns
    ):
        return ELIGIBLE

    return UNSUPPORTED


def surface_eligibility(
    value: object,
) -> str:
    token = normalise_token(value)

    if not token:
        return MISSING

    if token in {
        "TURF",
        "SYNTHETIC",
    }:
        return ELIGIBLE

    return UNSUPPORTED


def barrier_eligibility(
    barrier_value: object,
    field_size_value: object,
) -> str:
    if (
        not text(barrier_value)
        or not text(field_size_value)
    ):
        return MISSING

    barrier = parse_integer(
        barrier_value
    )

    field_size = parse_integer(
        field_size_value
    )

    if (
        barrier is None
        or field_size is None
        or barrier <= 0
        or field_size <= 0
        or barrier > field_size
    ):
        return INVALID

    return ELIGIBLE


def allocated_weight_eligibility(
    value: object,
) -> str:
    if not text(value):
        return MISSING

    parsed = parse_decimal(value)

    if parsed is None or parsed <= 0:
        return INVALID

    if (
        parsed < Decimal("35")
        or parsed > Decimal("80")
    ):
        return UNSUPPORTED

    return ELIGIBLE


def field_size_eligibility(
    value: object,
) -> str:
    if not text(value):
        return MISSING

    parsed = parse_integer(value)

    if parsed is None or parsed <= 0:
        return INVALID

    if parsed > 40:
        return UNSUPPORTED

    return ELIGIBLE


def main() -> None:
    input_fields, input_rows = read_csv(
        INPUT_PATH
    )

    require_fields(
        input_fields,
        [
            "race_entry_performance_context_id",
            "race_entry_horse_performance_snapshot_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
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
            "race_entry_performance_context_evidence_sha256",
            "builder_version",
        ],
    )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[
        dict[str, object]
    ] = []

    seen_context_ids: set[str] = set()
    seen_eligibility_ids: set[str] = set()

    for row in input_rows:
        context_id = text(
            row[
                "race_entry_performance_context_id"
            ]
        )

        if not context_id:
            fail(
                "Blank race_entry_performance_context_id."
            )

        if context_id in seen_context_ids:
            fail(
                f"Duplicate context ID: {context_id}"
            )

        seen_context_ids.add(
            context_id
        )

        if (
            text(
                row[
                    "race_entry_performance_context_status"
                ]
            )
            != SOURCE_CONTEXT_STATUS
        ):
            fail(
                f"{context_id}: source context "
                "status is not governed."
            )

        source_evidence = text(
            row[
                "race_entry_performance_context_evidence_sha256"
            ]
        )

        source_builder = text(
            row["builder_version"]
        )

        if (
            not source_evidence
            or not source_builder
        ):
            fail(
                f"{context_id}: incomplete source lineage."
            )

        identity_fields = [
            "race_entry_horse_performance_snapshot_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
        ]

        for field_name in identity_fields:
            if not text(
                row[field_name]
            ):
                fail(
                    f"{context_id}: blank identity field "
                    f"{field_name}."
                )

        decisions = {
            "historical_rating_eligibility": (
                historical_rating_eligibility(
                    row[
                        "context_historical_rating_value"
                    ]
                )
            ),
            "distance_context_eligibility": (
                distance_eligibility(
                    row["race_distance_m"]
                )
            ),
            "class_context_eligibility": (
                text_eligibility(
                    row["race_class_code"]
                )
            ),
            "track_context_eligibility": (
                track_eligibility(
                    row["track_id"],
                    row["track_name"],
                )
            ),
            "track_configuration_eligibility": (
                text_eligibility(
                    row["track_configuration"]
                )
            ),
            "track_condition_eligibility": (
                track_condition_eligibility(
                    row["track_condition"]
                )
            ),
            "surface_context_eligibility": (
                surface_eligibility(
                    row["racing_surface"]
                )
            ),
            "rail_context_eligibility": (
                text_eligibility(
                    row["rail_position"]
                )
            ),
            "barrier_context_eligibility": (
                barrier_eligibility(
                    row["barrier"],
                    row["declared_field_size"],
                )
            ),
            "allocated_weight_eligibility": (
                allocated_weight_eligibility(
                    row["allocated_weight_kg"]
                )
            ),
            "field_size_eligibility": (
                field_size_eligibility(
                    row["declared_field_size"]
                )
            ),
        }

        reason_order = [
            (
                "historical_rating_eligibility",
                "HISTORICAL_RATING",
            ),
            (
                "distance_context_eligibility",
                "DISTANCE_CONTEXT",
            ),
            (
                "class_context_eligibility",
                "CLASS_CONTEXT",
            ),
            (
                "track_context_eligibility",
                "TRACK_CONTEXT",
            ),
            (
                "track_configuration_eligibility",
                "TRACK_CONFIGURATION",
            ),
            (
                "track_condition_eligibility",
                "TRACK_CONDITION",
            ),
            (
                "surface_context_eligibility",
                "SURFACE_CONTEXT",
            ),
            (
                "rail_context_eligibility",
                "RAIL_CONTEXT",
            ),
            (
                "barrier_context_eligibility",
                "BARRIER_CONTEXT",
            ),
            (
                "allocated_weight_eligibility",
                "ALLOCATED_WEIGHT",
            ),
            (
                "field_size_eligibility",
                "FIELD_SIZE",
            ),
        ]

        all_eligible = all(
            value == ELIGIBLE
            for value in decisions.values()
        )

        if all_eligible:
            complete_eligibility = ELIGIBLE
            eligibility_status = COMPLETE_ELIGIBLE
            primary_reason_code = (
                "ALL_REQUIRED_CONTEXT_ELIGIBLE"
            )
        else:
            complete_eligibility = (
                "INELIGIBLE"
            )

            eligibility_status = (
                COMPLETE_INELIGIBLE
            )

            primary_reason_code = ""

            for (
                decision_field,
                reason_prefix,
            ) in reason_order:
                decision = decisions[
                    decision_field
                ]

                if decision != ELIGIBLE:
                    primary_reason_code = (
                        f"{reason_prefix}_"
                        f"{decision}"
                    )
                    break

            if not primary_reason_code:
                fail(
                    f"{context_id}: unable to derive "
                    "primary reason code."
                )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                context_id,
            ]
        )

        eligibility_id = (
            f"RECE1-{identity_hash[:24].upper()}"
        )

        if eligibility_id in seen_eligibility_ids:
            fail(
                "Duplicate deterministic eligibility ID: "
                f"{eligibility_id}"
            )

        seen_eligibility_ids.add(
            eligibility_id
        )

        evidence_hash = sha256_payload(
            [
                eligibility_id,
                source_evidence,
                *[
                    decisions[
                        field_name
                    ]
                    for field_name, _
                    in reason_order
                ],
                complete_eligibility,
                primary_reason_code,
                eligibility_status,
            ]
        )

        output_rows.append(
            {
                "race_entry_context_eligibility_id": (
                    eligibility_id
                ),
                "race_entry_performance_context_id": (
                    context_id
                ),
                "race_entry_horse_performance_snapshot_id": (
                    text(
                        row[
                            "race_entry_horse_performance_snapshot_id"
                        ]
                    )
                ),
                "race_entry_id": (
                    text(
                        row[
                            "race_entry_id"
                        ]
                    )
                ),
                "race_id": (
                    text(
                        row["race_id"]
                    )
                ),
                "race_date": (
                    text(
                        row["race_date"]
                    )
                ),
                "runner_id": (
                    text(
                        row["runner_id"]
                    )
                ),
                "canonical_horse_id": (
                    text(
                        row[
                            "canonical_horse_id"
                        ]
                    )
                ),
                "canonical_horse_name": (
                    text(
                        row[
                            "canonical_horse_name"
                        ]
                    )
                ),
                **decisions,
                "complete_context_eligibility": (
                    complete_eligibility
                ),
                "primary_context_eligibility_reason_code": (
                    primary_reason_code
                ),
                "race_entry_context_eligibility_status": (
                    eligibility_status
                ),
                "source_context_evidence_sha256": (
                    source_evidence
                ),
                "race_entry_context_eligibility_evidence_sha256": (
                    evidence_hash
                ),
                "source_context_builder_version": (
                    source_builder
                ),
                "builder_version": (
                    BUILDER_VERSION
                ),
                "contract_version": (
                    CONTRACT_VERSION
                ),
                "built_at_utc": (
                    built_at_utc
                ),
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(
                row["race_date"]
            ),
            text(
                row["race_id"]
            ),
            text(
                row["race_entry_id"]
            ),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    eligible_rows = sum(
        1
        for row in output_rows
        if (
            row[
                "complete_context_eligibility"
            ]
            == ELIGIBLE
        )
    )

    ineligible_rows = (
        len(output_rows)
        - eligible_rows
    )

    print(
        "EDGEIQ_RACE_ENTRY_CONTEXT_ELIGIBILITY_FACT_V1_BUILD_PASS"
    )
    print(
        "race_entry_performance_context_rows="
        f"{len(input_rows)}"
    )
    print(
        "complete_context_eligible_rows="
        f"{eligible_rows}"
    )
    print(
        "complete_context_ineligible_rows="
        f"{ineligible_rows}"
    )
    print(
        "race_entry_context_eligibility_rows="
        f"{len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
