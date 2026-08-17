from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ADJUSTED_PERFORMANCE_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv"
)

COMPONENT_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_component_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_suitability_aggregate_fact_v1.0.0"
)

CURRENT_BRANCH_BUILDER_VERSION = (
    "edgeiq_ra_to_rcom_bridge_current_performance_rebuild_v1"
)

CURRENT_BRANCH_BUILT_AT_UTC = "2026-07-30T00:00:00Z"

PERFORMANCE_ADJUSTED = "PERFORMANCE_ADJUSTED"
PARAMETER_NOT_AVAILABLE = "PARAMETER_NOT_AVAILABLE"
CONTEXT_INELIGIBLE = "CONTEXT_INELIGIBLE"

AGGREGATE_DECISION = "SUITABILITY_AGGREGATED"
AGGREGATE_STATUS = "GOVERNED_SUITABILITY_AGGREGATE"

COMPONENT_ORDER = [
    "DISTANCE",
    "CLASS",
    "TRACK",
    "TRACK_CONFIGURATION",
    "TRACK_CONDITION",
    "SURFACE",
    "BARRIER",
    "WEIGHT",
    "FIELD_SIZE",
]

COMPONENT_OUTPUT_FIELDS = {
    "DISTANCE": "distance_suitability_value",
    "CLASS": "class_suitability_value",
    "TRACK": "track_suitability_value",
    "TRACK_CONFIGURATION": (
        "track_configuration_suitability_value"
    ),
    "TRACK_CONDITION": (
        "track_condition_suitability_value"
    ),
    "SURFACE": "surface_suitability_value",
    "BARRIER": "barrier_suitability_value",
    "WEIGHT": "weight_suitability_value",
    "FIELD_SIZE": "field_size_suitability_value",
}

COPIED_FIELDS = [
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
]

OUTPUT_FIELDS = [
    "race_entry_suitability_aggregate_id",
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
    "distance_suitability_value",
    "class_suitability_value",
    "track_suitability_value",
    "track_configuration_suitability_value",
    "track_condition_suitability_value",
    "surface_suitability_value",
    "barrier_suitability_value",
    "weight_suitability_value",
    "field_size_suitability_value",
    "suitability_component_count",
    "aggregate_suitability_value",
    "suitability_aggregate_decision",
    "race_entry_suitability_aggregate_status",
    "source_adjusted_performance_evidence_sha256",
    "source_component_evidence_set_sha256",
    "race_entry_suitability_aggregate_evidence_sha256",
    "source_adjusted_performance_builder_version",
    "source_component_builder_version",
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


def parse_required_decimal(
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


def build_current_runner_aggregate_rows(
    component_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    output_rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    seen_component_ids: set[str] = set()

    for component in component_rows:
        component_id = text(
            component.get(
                "race_entry_suitability_component_id"
            )
        )

        if not component_id:
            fail("Blank current suitability component ID.")

        if component_id in seen_component_ids:
            fail(
                f"Duplicate current suitability component ID: "
                f"{component_id}"
            )

        seen_component_ids.add(component_id)

        if text(component.get("suitability_component_type")) != (
            "LIVE_CURRENT_SUITABILITY"
        ):
            fail(
                f"{component_id}: unsupported current suitability "
                "component type."
            )

        if text(component.get("suitability_component_decision")) != (
            "SUITABILITY_COMPONENT_PUBLISHED"
        ):
            fail(
                f"{component_id}: unsupported current suitability "
                "component decision."
            )

        if text(
            component.get("race_entry_suitability_component_status")
        ) != "GOVERNED_SUITABILITY_COMPONENT":
            fail(
                f"{component_id}: unsupported current suitability "
                "component status."
            )

        suitability_value = decimal_text(
            parse_required_decimal(
                component.get("suitability_component_value"),
                "suitability_component_value",
            )
        )

        aggregate_id = (
            "RESA-CUR-"
            + component_id.removeprefix("RESC-CUR-")
        )

        if aggregate_id in seen_ids:
            fail(
                f"Duplicate deterministic current suitability "
                f"aggregate ID: {aggregate_id}"
            )

        seen_ids.add(aggregate_id)

        component_evidence = text(
            component.get(
                "race_entry_suitability_component_evidence_sha256"
            )
        )
        source_adjusted_evidence = text(
            component.get(
                "source_adjusted_performance_evidence_sha256"
            )
        )

        if not component_evidence or not source_adjusted_evidence:
            fail(
                f"{component_id}: incomplete current suitability "
                "lineage."
            )

        evidence_hash = sha256_payload(
            [
                aggregate_id,
                suitability_value,
                "edgeiq_form_guide_enriched_v2",
            ]
        )

        output_row: dict[str, object] = {
            "race_entry_suitability_aggregate_id": aggregate_id,
            "race_entry_context_adjusted_performance_id": "",
            "suitability_component_count": "1",
            "aggregate_suitability_value": suitability_value,
            "suitability_aggregate_decision": AGGREGATE_DECISION,
            "race_entry_suitability_aggregate_status": AGGREGATE_STATUS,
            "source_adjusted_performance_evidence_sha256": (
                source_adjusted_evidence
            ),
            "source_component_evidence_set_sha256": (
                sha256_payload([component_id])
            ),
            "race_entry_suitability_aggregate_evidence_sha256": (
                evidence_hash
            ),
            "source_adjusted_performance_builder_version": (
                text(
                    component.get(
                        "source_adjusted_performance_builder_version"
                    )
                )
            ),
            "source_component_builder_version": (
                CURRENT_BRANCH_BUILDER_VERSION
            ),
            "builder_version": CURRENT_BRANCH_BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": CURRENT_BRANCH_BUILT_AT_UTC,
        }

        for copied_field in COPIED_FIELDS:
            output_row[copied_field] = text(
                component.get(copied_field)
            )

        for output_field in COMPONENT_OUTPUT_FIELDS.values():
            output_row[output_field] = ""

        output_rows.append(output_row)

    output_rows.sort(
        key=lambda row: (
            text(row["race_date"]),
            text(row["race_id"]),
            text(row["race_entry_id"]),
        )
    )

    return output_rows


def main() -> None:
    adjusted_fields, adjusted_rows = read_csv(
        ADJUSTED_PERFORMANCE_PATH
    )

    require_fields(
        ADJUSTED_PERFORMANCE_PATH,
        adjusted_fields,
        [
            "race_entry_context_adjusted_performance_id",
            *COPIED_FIELDS,
            "context_adjusted_performance_decision",
            "race_entry_context_adjusted_performance_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )

    if not adjusted_rows:
        component_fields, component_rows = read_csv(
            COMPONENT_PATH
        )

        require_fields(
            COMPONENT_PATH,
            component_fields,
            [
                "race_entry_suitability_component_id",
                *COPIED_FIELDS,
                "suitability_component_type",
                "suitability_component_value",
                "suitability_component_decision",
                "race_entry_suitability_component_status",
                "race_entry_suitability_component_evidence_sha256",
                "source_adjusted_performance_evidence_sha256",
                "source_adjusted_performance_builder_version",
                "builder_version",
                "contract_version",
            ],
        )

        output_rows = build_current_runner_aggregate_rows(
            component_rows
        )

        atomic_write_csv(
            OUTPUT_PATH,
            output_rows,
        )

        print(
            "EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_BUILD_PASS"
        )
        print("context_adjusted_performance_rows=0")
        print(f"suitability_component_rows={len(component_rows)}")
        print("eligible_adjusted_performance_rows=0")
        print("parameter_not_available_rows=0")
        print("context_ineligible_rows=0")
        print(f"suitability_aggregate_rows={len(output_rows)}")
        print(f"output={OUTPUT_PATH}")
        return

    component_fields, component_rows = read_csv(
        COMPONENT_PATH
    )

    require_fields(
        COMPONENT_PATH,
        component_fields,
        [
            "race_entry_suitability_component_id",
            "race_entry_context_adjusted_performance_id",
            *COPIED_FIELDS,
            "suitability_component_type",
            "suitability_component_value",
            "suitability_component_decision",
            "race_entry_suitability_component_status",
            "race_entry_suitability_component_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )

    adjusted_by_id: dict[str, dict[str, str]] = {}
    eligible_adjusted_ids: set[str] = set()

    unavailable_count = 0
    ineligible_count = 0

    for row in adjusted_rows:
        adjusted_id = text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        if not adjusted_id:
            fail(
                "Blank context-adjusted performance ID."
            )

        if adjusted_id in adjusted_by_id:
            fail(
                f"Duplicate context-adjusted performance ID: "
                f"{adjusted_id}"
            )

        adjusted_by_id[adjusted_id] = row

        decision = text(
            row[
                "context_adjusted_performance_decision"
            ]
        )

        if decision == PERFORMANCE_ADJUSTED:
            eligible_adjusted_ids.add(
                adjusted_id
            )

        elif decision == PARAMETER_NOT_AVAILABLE:
            unavailable_count += 1

        elif decision == CONTEXT_INELIGIBLE:
            ineligible_count += 1

        else:
            fail(
                f"{adjusted_id}: unsupported adjusted "
                f"performance decision {decision!r}."
            )

    components_by_adjusted_id: dict[
        str,
        dict[str, dict[str, str]],
    ] = defaultdict(dict)

    seen_component_ids: set[str] = set()

    for component in component_rows:
        component_id = text(
            component[
                "race_entry_suitability_component_id"
            ]
        )

        adjusted_id = text(
            component[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        component_type = text(
            component[
                "suitability_component_type"
            ]
        )

        if not component_id:
            fail(
                "Blank suitability component ID."
            )

        if component_id in seen_component_ids:
            fail(
                f"Duplicate suitability component ID: "
                f"{component_id}"
            )

        seen_component_ids.add(
            component_id
        )

        if adjusted_id not in eligible_adjusted_ids:
            fail(
                f"{component_id}: component belongs to "
                f"non-eligible adjusted-performance row "
                f"{adjusted_id}."
            )

        if component_type not in COMPONENT_OUTPUT_FIELDS:
            fail(
                f"{component_id}: unsupported component type "
                f"{component_type!r}."
            )

        if (
            component_type
            in components_by_adjusted_id[adjusted_id]
        ):
            fail(
                f"{adjusted_id}: duplicate component type "
                f"{component_type}."
            )

        if text(
            component[
                "suitability_component_decision"
            ]
        ) != "COMPONENT_PUBLISHED":
            fail(
                f"{component_id}: non-governed component "
                "decision."
            )

        if text(
            component[
                "race_entry_suitability_component_status"
            ]
        ) != "GOVERNED_SUITABILITY_COMPONENT":
            fail(
                f"{component_id}: non-governed component "
                "status."
            )

        components_by_adjusted_id[
            adjusted_id
        ][
            component_type
        ] = component

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []
    seen_output_ids: set[str] = set()

    for adjusted_id in sorted(
        eligible_adjusted_ids
    ):
        adjusted = adjusted_by_id[
            adjusted_id
        ]

        components = components_by_adjusted_id.get(
            adjusted_id,
            {},
        )

        actual_types = set(
            components
        )

        required_types = set(
            COMPONENT_ORDER
        )

        if actual_types != required_types:
            missing = sorted(
                required_types - actual_types
            )

            unexpected = sorted(
                actual_types - required_types
            )

            fail(
                f"{adjusted_id}: incomplete component set. "
                f"missing={missing}, "
                f"unexpected={unexpected}"
            )

        component_values: dict[str, str] = {}
        component_decimals: dict[str, Decimal] = {}
        ordered_component_evidence: list[str] = []
        source_component_builders: set[str] = set()

        for component_type in COMPONENT_ORDER:
            component = components[
                component_type
            ]

            for copied_field in COPIED_FIELDS:
                if text(
                    component[copied_field]
                ) != text(
                    adjusted[copied_field]
                ):
                    fail(
                        f"{adjusted_id}: component source "
                        f"mismatch for {component_type} / "
                        f"{copied_field}."
                    )

            decimal_value = parse_required_decimal(
                component[
                    "suitability_component_value"
                ],
                (
                    f"{component_type}."
                    "suitability_component_value"
                ),
            )

            component_value = decimal_text(
                decimal_value
            )

            component_values[
                component_type
            ] = component_value

            component_decimals[
                component_type
            ] = decimal_value

            component_evidence = text(
                component[
                    "race_entry_suitability_component_evidence_sha256"
                ]
            )

            component_builder = text(
                component[
                    "builder_version"
                ]
            )

            if (
                not component_evidence
                or not component_builder
            ):
                fail(
                    f"{adjusted_id}: incomplete component "
                    f"lineage for {component_type}."
                )

            ordered_component_evidence.append(
                component_evidence
            )

            source_component_builders.add(
                component_builder
            )

        if len(source_component_builders) != 1:
            fail(
                f"{adjusted_id}: component builder versions "
                "are inconsistent."
            )

        aggregate_decimal = sum(
            (
                component_decimals[
                    component_type
                ]
                for component_type
                in COMPONENT_ORDER
            ),
            Decimal("0"),
        )

        aggregate_value = decimal_text(
            aggregate_decimal
        )

        total_context_adjustment = (
            parse_required_decimal(
                adjusted[
                    "total_context_adjustment"
                ],
                "total_context_adjustment",
            )
        )

        if aggregate_decimal != total_context_adjustment:
            fail(
                f"{adjusted_id}: suitability aggregate "
                f"{aggregate_value} does not reconcile to "
                f"total context adjustment "
                f"{decimal_text(total_context_adjustment)}."
            )

        adjusted_evidence = text(
            adjusted[
                "race_entry_context_adjusted_performance_evidence_sha256"
            ]
        )

        adjusted_builder = text(
            adjusted["builder_version"]
        )

        if (
            not adjusted_evidence
            or not adjusted_builder
        ):
            fail(
                f"{adjusted_id}: incomplete adjusted "
                "performance lineage."
            )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                adjusted_id,
                AGGREGATE_DECISION,
            ]
        )

        aggregate_id = (
            f"RESA1-"
            f"{identity_hash[:24].upper()}"
        )

        if aggregate_id in seen_output_ids:
            fail(
                f"Duplicate deterministic suitability "
                f"aggregate ID: {aggregate_id}"
            )

        seen_output_ids.add(
            aggregate_id
        )

        component_evidence_set_sha256 = (
            sha256_payload(
                ordered_component_evidence
            )
        )

        evidence_hash = sha256_payload(
            [
                aggregate_id,
                adjusted_evidence,
                component_evidence_set_sha256,
                *[
                    component_values[
                        component_type
                    ]
                    for component_type
                    in COMPONENT_ORDER
                ],
                aggregate_value,
                decimal_text(
                    total_context_adjustment
                ),
                AGGREGATE_DECISION,
                AGGREGATE_STATUS,
            ]
        )

        output_row: dict[str, object] = {
            "race_entry_suitability_aggregate_id": (
                aggregate_id
            ),
            "race_entry_context_adjusted_performance_id": (
                adjusted_id
            ),
            "suitability_component_count": (
                len(COMPONENT_ORDER)
            ),
            "aggregate_suitability_value": (
                aggregate_value
            ),
            "suitability_aggregate_decision": (
                AGGREGATE_DECISION
            ),
            "race_entry_suitability_aggregate_status": (
                AGGREGATE_STATUS
            ),
            "source_adjusted_performance_evidence_sha256": (
                adjusted_evidence
            ),
            "source_component_evidence_set_sha256": (
                component_evidence_set_sha256
            ),
            "race_entry_suitability_aggregate_evidence_sha256": (
                evidence_hash
            ),
            "source_adjusted_performance_builder_version": (
                adjusted_builder
            ),
            "source_component_builder_version": (
                next(iter(source_component_builders))
            ),
            "builder_version": BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": built_at_utc,
        }

        for copied_field in COPIED_FIELDS:
            output_row[copied_field] = text(
                adjusted[copied_field]
            )

        for component_type in COMPONENT_ORDER:
            output_field = COMPONENT_OUTPUT_FIELDS[
                component_type
            ]

            output_row[output_field] = (
                component_values[
                    component_type
                ]
            )

        output_rows.append(
            output_row
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
        "EDGEIQ_RACE_ENTRY_SUITABILITY_AGGREGATE_FACT_V1_BUILD_PASS"
    )
    print(
        f"context_adjusted_performance_rows={len(adjusted_rows)}"
    )
    print(
        f"suitability_component_rows={len(component_rows)}"
    )
    print(
        f"eligible_adjusted_performance_rows={len(eligible_adjusted_ids)}"
    )
    print(
        f"parameter_not_available_rows={unavailable_count}"
    )
    print(
        f"context_ineligible_rows={ineligible_count}"
    )
    print(
        f"suitability_aggregate_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
