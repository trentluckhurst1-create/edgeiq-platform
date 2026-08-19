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

ELIGIBILITY_PATH = (
    DATA
    / "edgeiq_race_entry_context_eligibility_fact_v1.csv"
)

CONTEXT_PATH = (
    DATA
    / "edgeiq_race_entry_performance_context_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA
    / "edgeiq_context_parameter_registry_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_context_parameter_selection_fact_v1.0.1_empty_input_guard"
)

ELIGIBLE_STATUS = "COMPLETE_CONTEXT_ELIGIBLE"
INELIGIBLE_STATUS = "COMPLETE_CONTEXT_INELIGIBLE"

PARAMETER_STATUS = "CONTEXT_PARAMETER_GOVERNED"

SELECTED = "PARAMETER_SELECTED"
NOT_AVAILABLE = "PARAMETER_NOT_AVAILABLE"
CONTEXT_INELIGIBLE = "CONTEXT_INELIGIBLE"

SELECTED_STATUS = "EXACT_CONTEXT_PARAMETER_SELECTED"
NOT_AVAILABLE_STATUS = "EXACT_CONTEXT_PARAMETER_NOT_AVAILABLE"
INELIGIBLE_SELECTION_STATUS = (
    "CONTEXT_NOT_ELIGIBLE_FOR_PARAMETER_SELECTION"
)

OUTPUT_FIELDS = [
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


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


def token(value: object) -> str:
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


def decimal_value(
    value: object,
    field_name: str,
) -> Decimal:
    raw = text(value)

    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal {field_name}: {raw!r}"
        ) from exc

    if not parsed.is_finite():
        fail(
            f"Non-finite decimal {field_name}: {raw!r}"
        )

    return parsed


def integer_value(
    value: object,
    field_name: str,
) -> int:
    raw = text(value)

    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid integer {field_name}: {raw!r}"
        ) from exc


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
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

        return list(reader.fieldnames), list(reader)


def require_fields(
    path: Path,
    actual: list[str],
    required: Iterable[str],
) -> None:
    missing = [
        field
        for field in required
        if field not in actual
    ]

    if missing:
        fail(
            f"{path.name} missing required fields: {missing}"
        )


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )

    os.close(descriptor)
    temporary_path = Path(temporary_name)

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


def barrier_band(
    barrier: int,
    field_size: int,
) -> str:
    if barrier <= 0 or field_size <= 0 or barrier > field_size:
        fail(
            "Invalid barrier and field-size relationship."
        )

    proportion = (
        Decimal(barrier)
        / Decimal(field_size)
    )

    if proportion <= Decimal("0.333333"):
        return "INNER"

    if proportion <= Decimal("0.666667"):
        return "MIDDLE"

    return "OUTER"


def weight_band(
    weight: Decimal,
) -> str:
    if Decimal("35") <= weight < Decimal("50"):
        return "WEIGHT_35_TO_49_999999"

    if Decimal("50") <= weight < Decimal("55"):
        return "WEIGHT_50_TO_54_999999"

    if Decimal("55") <= weight < Decimal("60"):
        return "WEIGHT_55_TO_59_999999"

    if Decimal("60") <= weight < Decimal("65"):
        return "WEIGHT_60_TO_64_999999"

    if Decimal("65") <= weight <= Decimal("80"):
        return "WEIGHT_65_TO_80"

    fail(
        f"Unsupported allocated weight: {weight}"
    )


def field_size_band(
    field_size: int,
) -> str:
    if 1 <= field_size <= 8:
        return "FIELD_1_TO_8"

    if field_size <= 12:
        return "FIELD_9_TO_12"

    if field_size <= 16:
        return "FIELD_13_TO_16"

    if field_size <= 24:
        return "FIELD_17_TO_24"

    if field_size <= 40:
        return "FIELD_25_TO_40"

    fail(
        f"Unsupported field size: {field_size}"
    )


def signature_parts(
    row: dict[str, str],
) -> tuple[str, ...]:
    distance = integer_value(
        row["race_distance_m"],
        "race_distance_m",
    )

    barrier = integer_value(
        row["barrier"],
        "barrier",
    )

    field_size = integer_value(
        row["declared_field_size"],
        "declared_field_size",
    )

    weight = decimal_value(
        row["allocated_weight_kg"],
        "allocated_weight_kg",
    )

    return (
        str(distance),
        token(row["race_class_code"]),
        token(row["track_id"]),
        token(row["track_configuration"]),
        token(row["track_condition"]),
        token(row["racing_surface"]),
        barrier_band(
            barrier,
            field_size,
        ),
        weight_band(weight),
        field_size_band(field_size),
    )


def main() -> None:
    eligibility_fields, eligibility_rows = read_csv(
        ELIGIBILITY_PATH
    )

    require_fields(
        ELIGIBILITY_PATH,
        eligibility_fields,
        [
            "race_entry_context_eligibility_id",
            "race_entry_performance_context_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "complete_context_eligibility",
            "primary_context_eligibility_reason_code",
            "race_entry_context_eligibility_status",
            "race_entry_context_eligibility_evidence_sha256",
            "builder_version",
        ],
    )

    if not eligibility_rows:
        atomic_write_csv(
            OUTPUT_PATH,
            [],
        )

        print(
            "EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_BUILD_PASS"
        )
        print("context_eligibility_rows=0")
        print("performance_context_rows=NOT_REQUIRED")
        print("context_parameter_registry_rows=NOT_REQUIRED")
        print("parameter_selected_rows=0")
        print("parameter_not_available_rows=0")
        print("context_ineligible_rows=0")
        print("context_parameter_selection_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    context_fields, context_rows = read_csv(
        CONTEXT_PATH
    )

    has_eligible_context = any(
        text(row.get("complete_context_eligibility", "")) == "ELIGIBLE"
        for row in eligibility_rows
    )

    if has_eligible_context:
        parameter_fields, parameter_rows = read_csv(
            PARAMETER_PATH
        )
    else:
        parameter_fields, parameter_rows = [], []

    require_fields(
        CONTEXT_PATH,
        context_fields,
        [
            "race_entry_performance_context_id",
            "race_entry_horse_performance_snapshot_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "race_distance_m",
            "race_class_code",
            "track_id",
            "track_configuration",
            "track_condition",
            "racing_surface",
            "barrier",
            "allocated_weight_kg",
            "declared_field_size",
            "race_entry_performance_context_evidence_sha256",
            "builder_version",
        ],
    )

    if has_eligible_context:
        require_fields(
            PARAMETER_PATH,
            parameter_fields,
            [
                "context_parameter_id",
                "race_distance_m",
                "race_class_code",
                "track_id",
                "track_configuration",
                "track_condition",
                "racing_surface",
                "barrier_band",
                "weight_band",
                "field_size_band",
                "parameter_status",
                "context_parameter_evidence_sha256",
                "builder_version",
                "contract_version",
            ],
        )

    context_by_id: dict[str, dict[str, str]] = {}

    for row in context_rows:
        context_id = text(
            row["race_entry_performance_context_id"]
        )

        if not context_id:
            fail(
                "Blank race_entry_performance_context_id."
            )

        if context_id in context_by_id:
            fail(
                f"Duplicate context ID: {context_id}"
            )

        context_by_id[context_id] = row

    parameter_by_signature: dict[
        tuple[str, ...],
        dict[str, str],
    ] = {}

    for row in parameter_rows:
        parameter_id = text(
            row["context_parameter_id"]
        )

        if not parameter_id:
            fail(
                "Blank context_parameter_id."
            )

        if text(row["parameter_status"]) != PARAMETER_STATUS:
            continue

        signature = (
            str(
                integer_value(
                    row["race_distance_m"],
                    "race_distance_m",
                )
            ),
            token(row["race_class_code"]),
            token(row["track_id"]),
            token(row["track_configuration"]),
            token(row["track_condition"]),
            token(row["racing_surface"]),
            token(row["barrier_band"]),
            token(row["weight_band"]),
            token(row["field_size_band"]),
        )

        if signature in parameter_by_signature:
            fail(
                "Duplicate governed parameter signature: "
                f"{signature}"
            )

        if (
            not text(
                row[
                    "context_parameter_evidence_sha256"
                ]
            )
            or not text(row["builder_version"])
            or not text(row["contract_version"])
        ):
            fail(
                f"{parameter_id}: incomplete parameter lineage."
            )

        parameter_by_signature[signature] = row

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []
    seen_eligibility_ids: set[str] = set()
    seen_selection_ids: set[str] = set()

    selected_count = 0
    unavailable_count = 0
    ineligible_count = 0

    for eligibility in eligibility_rows:
        eligibility_id = text(
            eligibility[
                "race_entry_context_eligibility_id"
            ]
        )

        if not eligibility_id:
            fail(
                "Blank race_entry_context_eligibility_id."
            )

        if eligibility_id in seen_eligibility_ids:
            fail(
                f"Duplicate eligibility ID: {eligibility_id}"
            )

        seen_eligibility_ids.add(
            eligibility_id
        )

        context_id = text(
            eligibility[
                "race_entry_performance_context_id"
            ]
        )

        context = context_by_id.get(
            context_id
        )

        if context is None:
            fail(
                f"{eligibility_id}: missing context {context_id}."
            )

        copied_fields = [
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
        ]

        for field_name in copied_fields:
            if (
                text(eligibility[field_name])
                != text(context[field_name])
            ):
                fail(
                    f"{eligibility_id}: source identity "
                    f"disagrees for {field_name}."
                )

        complete_eligibility = text(
            eligibility[
                "complete_context_eligibility"
            ]
        )

        source_reason = text(
            eligibility[
                "primary_context_eligibility_reason_code"
            ]
        )

        eligibility_status = text(
            eligibility[
                "race_entry_context_eligibility_status"
            ]
        )

        if complete_eligibility == "ELIGIBLE":
            if eligibility_status != ELIGIBLE_STATUS:
                fail(
                    f"{eligibility_id}: inconsistent eligible status."
                )
        elif complete_eligibility == "INELIGIBLE":
            if eligibility_status != INELIGIBLE_STATUS:
                fail(
                    f"{eligibility_id}: inconsistent ineligible status."
                )
        else:
            fail(
                f"{eligibility_id}: invalid complete eligibility."
            )

        signature = signature_parts(
            context
        )

        signature_hash = sha256_payload(
            signature
        )

        parameter = None

        if complete_eligibility == "ELIGIBLE":
            parameter = parameter_by_signature.get(
                signature
            )

            if parameter is None:
                parameter_id = ""
                parameter_evidence = ""
                parameter_builder = ""
                decision = NOT_AVAILABLE
                selection_status = NOT_AVAILABLE_STATUS
                unavailable_count += 1
            else:
                parameter_id = text(
                    parameter["context_parameter_id"]
                )

                parameter_evidence = text(
                    parameter[
                        "context_parameter_evidence_sha256"
                    ]
                )

                parameter_builder = text(
                    parameter["builder_version"]
                )

                decision = SELECTED
                selection_status = SELECTED_STATUS
                selected_count += 1
        else:
            parameter_id = ""
            parameter_evidence = ""
            parameter_builder = ""
            decision = CONTEXT_INELIGIBLE
            selection_status = INELIGIBLE_SELECTION_STATUS
            ineligible_count += 1

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                eligibility_id,
                (
                    parameter_id
                    if parameter_id
                    else "NO_PARAMETER"
                ),
                decision,
            ]
        )

        selection_id = (
            f"RECPS1-{identity_hash[:24].upper()}"
        )

        if selection_id in seen_selection_ids:
            fail(
                f"Duplicate selection ID: {selection_id}"
            )

        seen_selection_ids.add(
            selection_id
        )

        eligibility_evidence = text(
            eligibility[
                "race_entry_context_eligibility_evidence_sha256"
            ]
        )

        context_evidence = text(
            context[
                "race_entry_performance_context_evidence_sha256"
            ]
        )

        eligibility_builder = text(
            eligibility["builder_version"]
        )

        context_builder = text(
            context["builder_version"]
        )

        if (
            not eligibility_evidence
            or not context_evidence
            or not eligibility_builder
            or not context_builder
        ):
            fail(
                f"{eligibility_id}: incomplete source lineage."
            )

        selection_evidence = sha256_payload(
            [
                selection_id,
                eligibility_evidence,
                context_evidence,
                parameter_evidence,
                signature_hash,
                decision,
                selection_status,
                source_reason,
            ]
        )

        output_rows.append(
            {
                "race_entry_context_parameter_selection_id": (
                    selection_id
                ),
                "race_entry_context_eligibility_id": (
                    eligibility_id
                ),
                "race_entry_performance_context_id": (
                    context_id
                ),
                "race_entry_id": text(
                    eligibility["race_entry_id"]
                ),
                "race_id": text(
                    eligibility["race_id"]
                ),
                "race_date": text(
                    eligibility["race_date"]
                ),
                "runner_id": text(
                    eligibility["runner_id"]
                ),
                "canonical_horse_id": text(
                    eligibility["canonical_horse_id"]
                ),
                "canonical_horse_name": text(
                    eligibility["canonical_horse_name"]
                ),
                "complete_context_eligibility": (
                    complete_eligibility
                ),
                "source_context_eligibility_reason_code": (
                    source_reason
                ),
                "race_distance_m": signature[0],
                "race_class_code": signature[1],
                "track_id": signature[2],
                "track_configuration": signature[3],
                "track_condition": signature[4],
                "racing_surface": signature[5],
                "barrier_band": signature[6],
                "weight_band": signature[7],
                "field_size_band": signature[8],
                "context_signature_sha256": (
                    signature_hash
                ),
                "context_parameter_id": (
                    parameter_id
                ),
                "context_parameter_selection_decision": (
                    decision
                ),
                "race_entry_context_parameter_selection_status": (
                    selection_status
                ),
                "source_eligibility_evidence_sha256": (
                    eligibility_evidence
                ),
                "source_context_evidence_sha256": (
                    context_evidence
                ),
                "source_parameter_evidence_sha256": (
                    parameter_evidence
                ),
                "race_entry_context_parameter_selection_evidence_sha256": (
                    selection_evidence
                ),
                "source_eligibility_builder_version": (
                    eligibility_builder
                ),
                "source_context_builder_version": (
                    context_builder
                ),
                "source_parameter_builder_version": (
                    parameter_builder
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(row["race_date"]),
            text(row["race_id"]),
            text(row["race_entry_id"]),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ENTRY_CONTEXT_PARAMETER_SELECTION_FACT_V1_BUILD_PASS"
    )
    print(
        f"context_eligibility_rows={len(eligibility_rows)}"
    )
    print(
        f"performance_context_rows={len(context_rows)}"
    )
    print(
        f"context_parameter_registry_rows={len(parameter_rows)}"
    )
    print(
        f"parameter_selected_rows={selected_count}"
    )
    print(
        f"parameter_not_available_rows={unavailable_count}"
    )
    print(
        f"context_ineligible_rows={ineligible_count}"
    )
    print(
        f"context_parameter_selection_rows={len(output_rows)}"
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
