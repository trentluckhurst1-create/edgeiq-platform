from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SELECTION_PATH = (
    DATA
    / "edgeiq_race_entry_context_parameter_selection_fact_v1.csv"
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
    / "edgeiq_race_entry_context_adjustment_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_context_adjustment_fact_v1.0.1_empty_input_guard"
)

PARAMETER_STATUS = "CONTEXT_PARAMETER_GOVERNED"

PARAMETER_SELECTED = "PARAMETER_SELECTED"
PARAMETER_NOT_AVAILABLE = "PARAMETER_NOT_AVAILABLE"
CONTEXT_INELIGIBLE = "CONTEXT_INELIGIBLE"

ADJUSTMENT_APPLIED = "ADJUSTMENT_APPLIED"

APPLIED_STATUS = (
    "GOVERNED_CONTEXT_ADJUSTMENT_APPLIED"
)

NOT_AVAILABLE_STATUS = (
    "GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE"
)

INELIGIBLE_STATUS = (
    "CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTMENT"
)

ADJUSTMENT_FIELDS = [
    "distance_adjustment",
    "class_adjustment",
    "track_adjustment",
    "track_configuration_adjustment",
    "track_condition_adjustment",
    "surface_adjustment",
    "barrier_adjustment",
    "weight_adjustment",
    "field_size_adjustment",
]

OUTPUT_FIELDS = [
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


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


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
    field_name: str,
) -> Decimal:
    raw = text(value)

    if not raw:
        fail(
            f"Blank required decimal: {field_name}"
        )

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


def decimal_text(
    value: Decimal,
) -> str:
    if value == 0:
        return "0"

    rendered = format(
        value.normalize(),
        "f",
    )

    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")

    return rendered


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


def main() -> None:
    selection_fields, selection_rows = read_csv(
        SELECTION_PATH
    )

    require_fields(
        SELECTION_PATH,
        selection_fields,
        [
            "race_entry_context_parameter_selection_id",
            "race_entry_context_eligibility_id",
            "race_entry_performance_context_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "context_parameter_id",
            "context_parameter_selection_decision",
            "source_selection_evidence_sha256"
            if False
            else "race_entry_context_parameter_selection_evidence_sha256",
            "builder_version",
        ],
    )

    if not selection_rows:
        atomic_write_csv(
            OUTPUT_PATH,
            [],
        )

        print(
            "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_BUILD_PASS"
        )
        print("context_parameter_selection_rows=0")
        print("performance_context_rows=NOT_REQUIRED")
        print("context_parameter_registry_rows=NOT_REQUIRED")
        print("adjustment_applied_rows=0")
        print("parameter_not_available_rows=0")
        print("context_ineligible_rows=0")
        print("context_adjustment_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    context_fields, context_rows = read_csv(
        CONTEXT_PATH
    )

    has_selected_parameter = any(
        text(row.get("context_parameter_selection_decision", "")) == PARAMETER_SELECTED
        for row in selection_rows
    )

    if has_selected_parameter:
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
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "context_historical_rating_value",
            "race_entry_performance_context_evidence_sha256",
            "builder_version",
        ],
    )

    if has_selected_parameter:
        require_fields(
            PARAMETER_PATH,
            parameter_fields,
            [
                "context_parameter_id",
                *ADJUSTMENT_FIELDS,
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
                f"Duplicate performance context ID: {context_id}"
            )

        context_by_id[context_id] = row

    parameter_by_id: dict[str, dict[str, str]] = {}

    for row in parameter_rows:
        parameter_id = text(
            row["context_parameter_id"]
        )

        if not parameter_id:
            fail(
                "Blank context_parameter_id."
            )

        if parameter_id in parameter_by_id:
            fail(
                f"Duplicate context parameter ID: {parameter_id}"
            )

        parameter_by_id[parameter_id] = row

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []

    seen_selection_ids: set[str] = set()
    seen_adjustment_ids: set[str] = set()

    applied_count = 0
    unavailable_count = 0
    ineligible_count = 0

    for selection in selection_rows:
        selection_id = text(
            selection[
                "race_entry_context_parameter_selection_id"
            ]
        )

        if not selection_id:
            fail(
                "Blank parameter-selection ID."
            )

        if selection_id in seen_selection_ids:
            fail(
                f"Duplicate parameter-selection ID: {selection_id}"
            )

        seen_selection_ids.add(
            selection_id
        )

        context_id = text(
            selection[
                "race_entry_performance_context_id"
            ]
        )

        context = context_by_id.get(
            context_id
        )

        if context is None:
            fail(
                f"{selection_id}: missing performance context "
                f"{context_id}."
            )

        identity_fields = [
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
        ]

        for field_name in identity_fields:
            if (
                text(selection[field_name])
                != text(context[field_name])
            ):
                fail(
                    f"{selection_id}: source identity mismatch "
                    f"for {field_name}."
                )

        historical_rating = parse_decimal(
            context[
                "context_historical_rating_value"
            ],
            "context_historical_rating_value",
        )

        historical_rating_value = decimal_text(
            historical_rating
        )

        source_decision = text(
            selection[
                "context_parameter_selection_decision"
            ]
        )

        parameter_id = text(
            selection["context_parameter_id"]
        )

        parameter_evidence = ""
        parameter_builder = ""

        adjustment_values = {
            field_name: ""
            for field_name in ADJUSTMENT_FIELDS
        }

        total_adjustment = ""

        if source_decision == PARAMETER_SELECTED:
            if not parameter_id:
                fail(
                    f"{selection_id}: selected decision has "
                    "blank parameter ID."
                )

            parameter = parameter_by_id.get(
                parameter_id
            )

            if parameter is None:
                fail(
                    f"{selection_id}: selected parameter "
                    f"{parameter_id} does not exist."
                )

            if (
                text(parameter["parameter_status"])
                != PARAMETER_STATUS
            ):
                fail(
                    f"{selection_id}: selected parameter "
                    "is not governed."
                )

            parameter_evidence = text(
                parameter[
                    "context_parameter_evidence_sha256"
                ]
            )

            parameter_builder = text(
                parameter["builder_version"]
            )

            parameter_contract = text(
                parameter["contract_version"]
            )

            if (
                not parameter_evidence
                or not parameter_builder
                or not parameter_contract
            ):
                fail(
                    f"{selection_id}: incomplete parameter lineage."
                )

            parsed_adjustments: list[Decimal] = []

            for field_name in ADJUSTMENT_FIELDS:
                parsed = parse_decimal(
                    parameter[field_name],
                    field_name,
                )

                parsed_adjustments.append(
                    parsed
                )

                adjustment_values[field_name] = (
                    decimal_text(parsed)
                )

            total = sum(
                parsed_adjustments,
                Decimal("0"),
            )

            total_adjustment = decimal_text(
                total
            )

            application_decision = ADJUSTMENT_APPLIED
            application_status = APPLIED_STATUS
            applied_count += 1

        elif source_decision == PARAMETER_NOT_AVAILABLE:
            if parameter_id:
                fail(
                    f"{selection_id}: unavailable decision has "
                    "a parameter ID."
                )

            application_decision = PARAMETER_NOT_AVAILABLE
            application_status = NOT_AVAILABLE_STATUS
            unavailable_count += 1

        elif source_decision == CONTEXT_INELIGIBLE:
            if parameter_id:
                fail(
                    f"{selection_id}: ineligible decision has "
                    "a parameter ID."
                )

            application_decision = CONTEXT_INELIGIBLE
            application_status = INELIGIBLE_STATUS
            ineligible_count += 1

        else:
            fail(
                f"{selection_id}: unsupported source decision "
                f"{source_decision!r}."
            )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                selection_id,
                (
                    parameter_id
                    if parameter_id
                    else "NO_PARAMETER"
                ),
                application_decision,
            ]
        )

        adjustment_id = (
            f"RECA1-{identity_hash[:24].upper()}"
        )

        if adjustment_id in seen_adjustment_ids:
            fail(
                f"Duplicate deterministic adjustment ID: "
                f"{adjustment_id}"
            )

        seen_adjustment_ids.add(
            adjustment_id
        )

        selection_evidence = text(
            selection[
                "race_entry_context_parameter_selection_evidence_sha256"
            ]
        )

        context_evidence = text(
            context[
                "race_entry_performance_context_evidence_sha256"
            ]
        )

        selection_builder = text(
            selection["builder_version"]
        )

        context_builder = text(
            context["builder_version"]
        )

        if (
            not selection_evidence
            or not context_evidence
            or not selection_builder
            or not context_builder
        ):
            fail(
                f"{selection_id}: incomplete source lineage."
            )

        evidence_hash = sha256_payload(
            [
                adjustment_id,
                selection_evidence,
                context_evidence,
                parameter_evidence,
                historical_rating_value,
                *[
                    adjustment_values[field_name]
                    for field_name in ADJUSTMENT_FIELDS
                ],
                total_adjustment,
                application_decision,
                application_status,
            ]
        )

        output_rows.append(
            {
                "race_entry_context_adjustment_id": (
                    adjustment_id
                ),
                "race_entry_context_parameter_selection_id": (
                    selection_id
                ),
                "race_entry_context_eligibility_id": text(
                    selection[
                        "race_entry_context_eligibility_id"
                    ]
                ),
                "race_entry_performance_context_id": (
                    context_id
                ),
                "race_entry_id": text(
                    selection["race_entry_id"]
                ),
                "race_id": text(
                    selection["race_id"]
                ),
                "race_date": text(
                    selection["race_date"]
                ),
                "runner_id": text(
                    selection["runner_id"]
                ),
                "canonical_horse_id": text(
                    selection["canonical_horse_id"]
                ),
                "canonical_horse_name": text(
                    selection["canonical_horse_name"]
                ),
                "historical_rating_value": (
                    historical_rating_value
                ),
                "context_parameter_id": parameter_id,
                "source_parameter_selection_decision": (
                    source_decision
                ),
                **adjustment_values,
                "total_context_adjustment": (
                    total_adjustment
                ),
                "context_adjustment_application_decision": (
                    application_decision
                ),
                "race_entry_context_adjustment_status": (
                    application_status
                ),
                "source_selection_evidence_sha256": (
                    selection_evidence
                ),
                "source_context_evidence_sha256": (
                    context_evidence
                ),
                "source_parameter_evidence_sha256": (
                    parameter_evidence
                ),
                "race_entry_context_adjustment_evidence_sha256": (
                    evidence_hash
                ),
                "source_selection_builder_version": (
                    selection_builder
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
        "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTMENT_FACT_V1_BUILD_PASS"
    )
    print(
        f"context_parameter_selection_rows={len(selection_rows)}"
    )
    print(
        f"performance_context_rows={len(context_rows)}"
    )
    print(
        f"context_parameter_registry_rows={len(parameter_rows)}"
    )
    print(
        f"adjustment_applied_rows={applied_count}"
    )
    print(
        f"parameter_not_available_rows={unavailable_count}"
    )
    print(
        f"context_ineligible_rows={ineligible_count}"
    )
    print(
        f"context_adjustment_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
