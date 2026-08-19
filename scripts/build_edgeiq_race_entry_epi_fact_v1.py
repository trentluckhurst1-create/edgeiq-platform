from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

COMPONENT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_component_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA
    / "edgeiq_epi_parameter_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_race_entry_epi_fact_v1.0.0"

EXPECTED_METHODOLOGY = (
    "NORMALISED_WEIGHTED_ADDITIVE_EPI_V1"
)

PUBLICATION_DECISION = "EPI_PUBLISHED"
RECONCILIATION_DECISION = "EPI_RECONCILED"
GOVERNED_STATUS = "GOVERNED_RACE_ENTRY_EPI"

COMPONENT_PUBLICATION = "EPI_COMPONENT_PUBLISHED"
COMPONENT_RECONCILIATION = "EPI_COMPONENT_RECONCILED"
COMPONENT_STATUS = "GOVERNED_RACE_ENTRY_EPI_COMPONENT"

QUANTUM = Decimal("0.000001")
DECIMAL_PLACES = 6

COMPONENT_CODES = [
    "HISTORICAL_PERFORMANCE",
    "SUITABILITY",
    "RACE_CONTEXT",
]

WEIGHT_FIELD_BY_COMPONENT = {
    "HISTORICAL_PERFORMANCE": (
        "historical_performance_weight"
    ),
    "SUITABILITY": (
        "suitability_weight"
    ),
    "RACE_CONTEXT": (
        "race_context_weight"
    ),
}

OUTPUT_FIELDS = [
    "race_entry_epi_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "epi_methodology",
    "epi_base_value",
    "historical_performance_component_id",
    "historical_performance_component_evidence_sha256",
    "historical_performance_normalised_value",
    "historical_performance_weight",
    "historical_performance_weighted_value",
    "suitability_component_id",
    "suitability_component_evidence_sha256",
    "suitability_normalised_value",
    "suitability_weight",
    "suitability_weighted_value",
    "race_context_component_id",
    "race_context_component_evidence_sha256",
    "race_context_normalised_value",
    "race_context_weight",
    "race_context_weighted_value",
    "total_component_weight",
    "weighted_component_total",
    "epi_value",
    "epi_parameter_id",
    "epi_publication_decision",
    "epi_reconciliation_decision",
    "epi_status",
    "race_entry_epi_evidence_sha256",
    "source_lineage",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


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


def decimal_value(
    value: object,
    field_name: str,
) -> Decimal:
    raw = text(value)

    if not raw:
        raise RuntimeError(
            f"Missing decimal value: {field_name}"
        )

    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise RuntimeError(
            f"Invalid decimal value for {field_name}: {raw}"
        ) from error

    if not parsed.is_finite():
        raise RuntimeError(
            f"Non-finite decimal value for {field_name}: {raw}"
        )

    return parsed


def decimal_text(
    value: Decimal,
) -> str:
    return format(
        value.quantize(
            QUANTUM,
            rounding=ROUND_HALF_EVEN,
        ),
        f".{DECIMAL_PLACES}f",
    )


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise RuntimeError(
            f"Required governed input does not exist: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                f"Missing CSV header: {path}"
            )

        return list(reader.fieldnames), list(reader)


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, str]],
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


def active_on_date(
    race_date: str,
    effective_from: str,
    effective_to: str,
) -> bool:
    return (
        race_date >= effective_from
        and (
            not effective_to
            or race_date <= effective_to
        )
    )


def main() -> None:
    parameter_fields, parameter_rows = read_csv(
        PARAMETER_PATH
    )

    if len(parameter_rows) != 1:
        raise RuntimeError(
            "EPI Parameter Fact V1 must contain exactly one row."
        )

    parameter = parameter_rows[0]

    epi_parameter_id = text(
        parameter.get(
            "epi_parameter_id"
        )
    )

    epi_methodology = text(
        parameter.get(
            "epi_methodology"
        )
    )

    if not epi_parameter_id:
        raise RuntimeError(
            "Missing governed epi_parameter_id."
        )

    if epi_methodology != EXPECTED_METHODOLOGY:
        raise RuntimeError(
            f"Unexpected EPI methodology: {epi_methodology}"
        )

    if text(
        parameter.get(
            "epi_parameter_publication_decision"
        )
    ) != "EPI_PARAMETER_AUTHORISED":
        raise RuntimeError(
            "EPI parameter is not authorised."
        )

    if text(
        parameter.get(
            "epi_parameter_reconciliation_decision"
        )
    ) != "EPI_PARAMETER_RECONCILED":
        raise RuntimeError(
            "EPI parameter is not reconciled."
        )

    if text(
        parameter.get(
            "epi_parameter_status"
        )
    ) != "GOVERNED_EPI_PARAMETER":
        raise RuntimeError(
            "EPI parameter is not governed."
        )

    minimum_required_component_count = int(
        text(
            parameter.get(
                "minimum_required_component_count"
            )
        )
    )

    if minimum_required_component_count != 3:
        raise RuntimeError(
            "EPI V1 requires exactly three components."
        )

    base_value = decimal_value(
        parameter.get(
            "epi_base_value"
        ),
        "epi_base_value",
    )

    expected_weights = {
        component_code: decimal_value(
            parameter.get(
                WEIGHT_FIELD_BY_COMPONENT[
                    component_code
                ]
            ),
            WEIGHT_FIELD_BY_COMPONENT[
                component_code
            ],
        )
        for component_code in COMPONENT_CODES
    }

    expected_total_weight = sum(
        expected_weights.values(),
        Decimal("0"),
    )

    published_parameter_total_weight = decimal_value(
        parameter.get(
            "total_component_weight"
        ),
        "total_component_weight",
    )

    if expected_total_weight != Decimal("1.000000"):
        raise RuntimeError(
            "Authorised EPI component weights do not total 1.000000."
        )

    if (
        published_parameter_total_weight
        != expected_total_weight
    ):
        raise RuntimeError(
            "Published EPI parameter total weight does not reconcile."
        )

    component_fields, component_rows = read_csv(
        COMPONENT_PATH
    )

    grouped: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in component_rows:
        race_entry_id = text(
            row.get(
                "race_entry_id"
            )
        )

        if not race_entry_id:
            raise RuntimeError(
                "Component row is missing race_entry_id."
            )

        grouped[
            race_entry_id
        ].append(
            row
        )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, str]] = []

    for race_entry_id in sorted(grouped):
        rows = grouped[
            race_entry_id
        ]

        if len(rows) != 3:
            raise RuntimeError(
                f"Race entry {race_entry_id} has "
                f"{len(rows)} component rows; expected 3."
            )

        component_by_code: dict[
            str,
            dict[str, str],
        ] = {}

        race_ids: set[str] = set()
        race_dates: set[str] = set()
        component_parameter_ids: set[str] = set()

        for row in rows:
            component_code = text(
                row.get(
                    "epi_component_code"
                )
            )

            if component_code not in COMPONENT_CODES:
                raise RuntimeError(
                    f"Unexpected EPI component code: {component_code}"
                )

            if component_code in component_by_code:
                raise RuntimeError(
                    f"Duplicate component {component_code} "
                    f"for race entry {race_entry_id}."
                )

            if text(
                row.get(
                    "epi_component_publication_decision"
                )
            ) != COMPONENT_PUBLICATION:
                raise RuntimeError(
                    f"Unpublished component for {race_entry_id}."
                )

            if text(
                row.get(
                    "epi_component_reconciliation_decision"
                )
            ) != COMPONENT_RECONCILIATION:
                raise RuntimeError(
                    f"Unreconciled component for {race_entry_id}."
                )

            if text(
                row.get(
                    "epi_component_status"
                )
            ) != COMPONENT_STATUS:
                raise RuntimeError(
                    f"Ungoverned component for {race_entry_id}."
                )

            component_id = text(
                row.get(
                    "race_entry_epi_component_id"
                )
            )

            component_evidence = text(
                row.get(
                    "race_entry_epi_component_evidence_sha256"
                )
            )

            if not component_id or not component_evidence:
                raise RuntimeError(
                    f"Incomplete component lineage for {race_entry_id}."
                )

            race_ids.add(
                text(
                    row.get(
                        "race_id"
                    )
                )
            )

            race_dates.add(
                text(
                    row.get(
                        "race_date"
                    )
                )
            )

            component_parameter_ids.add(
                text(
                    row.get(
                        "epi_parameter_id"
                    )
                )
            )

            component_by_code[
                component_code
            ] = row

        if set(component_by_code) != set(COMPONENT_CODES):
            raise RuntimeError(
                f"Incomplete component population for {race_entry_id}."
            )

        if len(race_ids) != 1 or "" in race_ids:
            raise RuntimeError(
                f"Race identity disagreement for {race_entry_id}."
            )

        if len(race_dates) != 1 or "" in race_dates:
            raise RuntimeError(
                f"Race date disagreement for {race_entry_id}."
            )

        if component_parameter_ids != {
            epi_parameter_id
        }:
            raise RuntimeError(
                f"EPI parameter disagreement for {race_entry_id}."
            )

        race_id = next(iter(race_ids))
        race_date = next(iter(race_dates))

        if not active_on_date(
            race_date,
            text(
                parameter.get(
                    "effective_from_date"
                )
            ),
            text(
                parameter.get(
                    "effective_to_date"
                )
            ),
        ):
            raise RuntimeError(
                f"EPI parameter is inactive for race date {race_date}."
            )

        normalised_values: dict[
            str,
            Decimal,
        ] = {}

        weights: dict[
            str,
            Decimal,
        ] = {}

        weighted_values: dict[
            str,
            Decimal,
        ] = {}

        for component_code in COMPONENT_CODES:
            row = component_by_code[
                component_code
            ]

            normalised_values[
                component_code
            ] = decimal_value(
                row.get(
                    "capped_normalised_component_value"
                ),
                (
                    f"{race_entry_id}."
                    f"{component_code}.normalised"
                ),
            )

            weights[
                component_code
            ] = decimal_value(
                row.get(
                    "authorised_component_weight"
                ),
                (
                    f"{race_entry_id}."
                    f"{component_code}.weight"
                ),
            )

            weighted_values[
                component_code
            ] = decimal_value(
                row.get(
                    "weighted_component_value"
                ),
                (
                    f"{race_entry_id}."
                    f"{component_code}.weighted"
                ),
            )

            if (
                weights[
                    component_code
                ]
                != expected_weights[
                    component_code
                ]
            ):
                raise RuntimeError(
                    f"Weight disagreement for {race_entry_id}, "
                    f"component={component_code}."
                )

            expected_weighted = (
                normalised_values[
                    component_code
                ]
                * weights[
                    component_code
                ]
            ).quantize(
                QUANTUM,
                rounding=ROUND_HALF_EVEN,
            )

            if (
                weighted_values[
                    component_code
                ].quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
                != expected_weighted
            ):
                raise RuntimeError(
                    f"Weighted component arithmetic disagreement for "
                    f"{race_entry_id}, component={component_code}."
                )

        total_component_weight = sum(
            weights.values(),
            Decimal("0"),
        )

        if total_component_weight != Decimal("1.000000"):
            raise RuntimeError(
                f"Component weights do not total 1.000000 "
                f"for {race_entry_id}."
            )

        weighted_component_total = sum(
            weighted_values.values(),
            Decimal("0"),
        )

        epi_value = (
            base_value
            + weighted_component_total
        )

        base_value_text = decimal_text(
            base_value
        )

        total_component_weight_text = decimal_text(
            total_component_weight
        )

        weighted_component_total_text = decimal_text(
            weighted_component_total
        )

        epi_value_text = decimal_text(
            epi_value
        )

        historical = component_by_code[
            "HISTORICAL_PERFORMANCE"
        ]

        suitability = component_by_code[
            "SUITABILITY"
        ]

        race_context = component_by_code[
            "RACE_CONTEXT"
        ]

        historical_component_id = text(
            historical[
                "race_entry_epi_component_id"
            ]
        )

        suitability_component_id = text(
            suitability[
                "race_entry_epi_component_id"
            ]
        )

        race_context_component_id = text(
            race_context[
                "race_entry_epi_component_id"
            ]
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_entry_id,
                race_id,
                race_date,
                epi_parameter_id,
                historical_component_id,
                suitability_component_id,
                race_context_component_id,
                PUBLICATION_DECISION,
            ]
        )

        race_entry_epi_id = (
            f"REEPI1-"
            f"{identity_hash[:24].upper()}"
        )

        source_lineage = (
            "edgeiq_race_entry_epi_component_fact_v1:"
            f"{historical_component_id},"
            f"{suitability_component_id},"
            f"{race_context_component_id}"
            "|edgeiq_epi_parameter_fact_v1:"
            f"{epi_parameter_id}"
        )

        historical_normalised_text = decimal_text(
            normalised_values[
                "HISTORICAL_PERFORMANCE"
            ]
        )

        historical_weight_text = decimal_text(
            weights[
                "HISTORICAL_PERFORMANCE"
            ]
        )

        historical_weighted_text = decimal_text(
            weighted_values[
                "HISTORICAL_PERFORMANCE"
            ]
        )

        suitability_normalised_text = decimal_text(
            normalised_values[
                "SUITABILITY"
            ]
        )

        suitability_weight_text = decimal_text(
            weights[
                "SUITABILITY"
            ]
        )

        suitability_weighted_text = decimal_text(
            weighted_values[
                "SUITABILITY"
            ]
        )

        race_context_normalised_text = decimal_text(
            normalised_values[
                "RACE_CONTEXT"
            ]
        )

        race_context_weight_text = decimal_text(
            weights[
                "RACE_CONTEXT"
            ]
        )

        race_context_weighted_text = decimal_text(
            weighted_values[
                "RACE_CONTEXT"
            ]
        )

        evidence_hash = sha256_payload(
            [
                race_entry_epi_id,
                race_entry_id,
                race_id,
                race_date,
                epi_methodology,
                base_value_text,
                historical_component_id,
                text(
                    historical[
                        "race_entry_epi_component_evidence_sha256"
                    ]
                ),
                historical_normalised_text,
                historical_weight_text,
                historical_weighted_text,
                suitability_component_id,
                text(
                    suitability[
                        "race_entry_epi_component_evidence_sha256"
                    ]
                ),
                suitability_normalised_text,
                suitability_weight_text,
                suitability_weighted_text,
                race_context_component_id,
                text(
                    race_context[
                        "race_entry_epi_component_evidence_sha256"
                    ]
                ),
                race_context_normalised_text,
                race_context_weight_text,
                race_context_weighted_text,
                total_component_weight_text,
                weighted_component_total_text,
                epi_value_text,
                epi_parameter_id,
                PUBLICATION_DECISION,
                RECONCILIATION_DECISION,
                GOVERNED_STATUS,
                source_lineage,
            ]
        )

        output_rows.append(
            {
                "race_entry_epi_id": (
                    race_entry_epi_id
                ),
                "race_entry_id": (
                    race_entry_id
                ),
                "race_id": (
                    race_id
                ),
                "race_date": (
                    race_date
                ),
                "epi_methodology": (
                    epi_methodology
                ),
                "epi_base_value": (
                    base_value_text
                ),
                "historical_performance_component_id": (
                    historical_component_id
                ),
                "historical_performance_component_evidence_sha256": (
                    text(
                        historical[
                            "race_entry_epi_component_evidence_sha256"
                        ]
                    )
                ),
                "historical_performance_normalised_value": (
                    historical_normalised_text
                ),
                "historical_performance_weight": (
                    historical_weight_text
                ),
                "historical_performance_weighted_value": (
                    historical_weighted_text
                ),
                "suitability_component_id": (
                    suitability_component_id
                ),
                "suitability_component_evidence_sha256": (
                    text(
                        suitability[
                            "race_entry_epi_component_evidence_sha256"
                        ]
                    )
                ),
                "suitability_normalised_value": (
                    suitability_normalised_text
                ),
                "suitability_weight": (
                    suitability_weight_text
                ),
                "suitability_weighted_value": (
                    suitability_weighted_text
                ),
                "race_context_component_id": (
                    race_context_component_id
                ),
                "race_context_component_evidence_sha256": (
                    text(
                        race_context[
                            "race_entry_epi_component_evidence_sha256"
                        ]
                    )
                ),
                "race_context_normalised_value": (
                    race_context_normalised_text
                ),
                "race_context_weight": (
                    race_context_weight_text
                ),
                "race_context_weighted_value": (
                    race_context_weighted_text
                ),
                "total_component_weight": (
                    total_component_weight_text
                ),
                "weighted_component_total": (
                    weighted_component_total_text
                ),
                "epi_value": (
                    epi_value_text
                ),
                "epi_parameter_id": (
                    epi_parameter_id
                ),
                "epi_publication_decision": (
                    PUBLICATION_DECISION
                ),
                "epi_reconciliation_decision": (
                    RECONCILIATION_DECISION
                ),
                "epi_status": (
                    GOVERNED_STATUS
                ),
                "race_entry_epi_evidence_sha256": (
                    evidence_hash
                ),
                "source_lineage": (
                    source_lineage
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

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ENTRY_EPI_FACT_V1_BUILD_PASS"
    )
    print(
        f"epi_component_rows={len(component_rows)}"
    )
    print(
        f"race_entry_epi_rows={len(output_rows)}"
    )
    print(
        f"epi_parameter_id={epi_parameter_id}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
