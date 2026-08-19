from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTED_PATH = (
    DATA
    / "edgeiq_race_entry_projected_performance_fact_v1.csv"
)

SUITABILITY_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv"
)

ERI_CONTEXT_PATH = (
    DATA
    / "edgeiq_race_entry_eri_context_fact_v1.csv"
)

EPI_PARAMETER_PATH = (
    DATA
    / "edgeiq_epi_parameter_fact_v1.csv"
)

NORMALISATION_PARAMETER_PATH = (
    DATA
    / "edgeiq_epi_component_normalisation_parameter_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_component_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_race_entry_epi_component_fact_v1.0.0"
)

PUBLICATION_DECISION = "EPI_COMPONENT_PUBLISHED"
RECONCILIATION_DECISION = "EPI_COMPONENT_RECONCILED"
GOVERNED_STATUS = "GOVERNED_RACE_ENTRY_EPI_COMPONENT"

DECIMAL_PLACES = 6
QUANTUM = Decimal("0.000001")

OUTPUT_FIELDS = [
    "race_entry_epi_component_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "epi_component_code",
    "component_source_fact_name",
    "component_source_fact_id",
    "component_source_value_field",
    "component_source_evidence_sha256",
    "raw_component_value",
    "field_population_count",
    "field_component_mean",
    "field_component_population_standard_deviation",
    "unbounded_normalised_component_value",
    "capped_normalised_component_value",
    "authorised_component_weight",
    "weighted_component_value",
    "epi_parameter_id",
    "epi_component_normalisation_parameter_id",
    "epi_component_publication_decision",
    "epi_component_reconciliation_decision",
    "epi_component_status",
    "race_entry_epi_component_evidence_sha256",
    "source_lineage",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

COMPONENT_CONFIG = {
    "HISTORICAL_PERFORMANCE": {
        "path": PROJECTED_PATH,
        "fact_name": (
            "edgeiq_race_entry_projected_performance_fact_v1"
        ),
        "id_candidates": [
            "race_entry_projected_performance_id",
        ],
        "value_candidates": [
            "projected_performance_value",
        ],
        "evidence_candidates": [
            "race_entry_projected_performance_evidence_sha256",
            "projected_performance_evidence_sha256",
        ],
        "weight_field": "historical_performance_weight",
    },
    "SUITABILITY": {
        "path": SUITABILITY_PATH,
        "fact_name": (
            "edgeiq_race_entry_suitability_aggregate_fact_v1"
        ),
        "id_candidates": [
            "race_entry_suitability_aggregate_id",
            "race_entry_suitability_id",
        ],
        "value_candidates": [
            "suitability_aggregate_value",
            "race_entry_suitability_aggregate_value",
            "aggregate_suitability_value",
            "suitability_value",
        ],
        "evidence_candidates": [
            "race_entry_suitability_aggregate_evidence_sha256",
            "suitability_aggregate_evidence_sha256",
            "race_entry_suitability_evidence_sha256",
        ],
        "weight_field": "suitability_weight",
    },
    "RACE_CONTEXT": {
        "path": ERI_CONTEXT_PATH,
        "fact_name": (
            "edgeiq_race_entry_eri_context_fact_v1"
        ),
        "id_candidates": [
            "race_entry_eri_context_id",
        ],
        "value_candidates": [
            "projected_performance_vs_eri",
        ],
        "evidence_candidates": [
            "race_entry_eri_context_evidence_sha256",
            "eri_context_evidence_sha256",
        ],
        "weight_field": "race_context_weight",
    },
}


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


def sha256_payload(parts: Iterable[object]) -> str:
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
            f"Missing decimal value for {field_name}."
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


def decimal_text(value: Decimal) -> str:
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


def resolve_field(
    fields: list[str],
    candidates: list[str],
    label: str,
    allow_missing_when_empty: bool = False,
    row_count: int = 0,
) -> str:
    for candidate in candidates:
        if candidate in fields:
            return candidate

    if allow_missing_when_empty and row_count == 0:
        return candidates[0]

    raise RuntimeError(
        f"Unable to resolve {label}. "
        f"Candidates={candidates}; fields={fields}"
    )


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


def race_entry_key(
    row: dict[str, str],
) -> tuple[str, str, str]:
    race_entry_id = text(
        row.get("race_entry_id")
    )
    race_id = text(
        row.get("race_id")
    )
    race_date = text(
        row.get("race_date")
    )

    if not race_entry_id or not race_id or not race_date:
        raise RuntimeError(
            "Every component source row requires "
            "race_entry_id, race_id and race_date."
        )

    return (
        race_entry_id,
        race_id,
        race_date,
    )


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
    epi_fields, epi_rows = read_csv(
        EPI_PARAMETER_PATH
    )

    if len(epi_rows) != 1:
        raise RuntimeError(
            "EPI Parameter Fact V1 must contain exactly one row."
        )

    epi_parameter = epi_rows[0]

    if text(
        epi_parameter.get(
            "epi_parameter_status"
        )
    ) != "GOVERNED_EPI_PARAMETER":
        raise RuntimeError(
            "EPI parameter is not governed."
        )

    epi_parameter_id = text(
        epi_parameter.get(
            "epi_parameter_id"
        )
    )

    if not epi_parameter_id:
        raise RuntimeError(
            "Missing epi_parameter_id."
        )

    weight_by_component = {
        component_code: decimal_value(
            epi_parameter[
                config["weight_field"]
            ],
            config["weight_field"],
        )
        for component_code, config in COMPONENT_CONFIG.items()
    }

    if sum(
        weight_by_component.values(),
        Decimal("0"),
    ) != Decimal("1.000000"):
        raise RuntimeError(
            "EPI component weights do not total exactly 1.000000."
        )

    normalisation_fields, normalisation_rows = read_csv(
        NORMALISATION_PARAMETER_PATH
    )

    if len(normalisation_rows) != 3:
        raise RuntimeError(
            "Normalisation Parameter Fact V1 must contain exactly three rows."
        )

    normalisation_by_component: dict[
        str,
        dict[str, str],
    ] = {}

    for row in normalisation_rows:
        component_code = text(
            row.get(
                "epi_component_code"
            )
        )

        if component_code in normalisation_by_component:
            raise RuntimeError(
                f"Duplicate normalisation parameter: {component_code}"
            )

        if text(
            row.get(
                "normalisation_parameter_status"
            )
        ) != "GOVERNED_EPI_NORMALISATION_PARAMETER":
            raise RuntimeError(
                f"Ungoverned normalisation parameter: {component_code}"
            )

        normalisation_by_component[
            component_code
        ] = row

    if set(
        normalisation_by_component
    ) != set(
        COMPONENT_CONFIG
    ):
        raise RuntimeError(
            "Normalisation component population is incomplete."
        )

    source_records: dict[
        str,
        dict[
            tuple[str, str, str],
            dict[str, object],
        ],
    ] = {}

    source_row_counts: dict[str, int] = {}

    for component_code, config in COMPONENT_CONFIG.items():
        fields, rows = read_csv(
            config["path"]
        )

        source_row_counts[
            component_code
        ] = len(rows)

        id_field = resolve_field(
            fields,
            config["id_candidates"],
            f"{component_code} source ID",
            allow_missing_when_empty=True,
            row_count=len(rows),
        )

        value_field = resolve_field(
            fields,
            config["value_candidates"],
            f"{component_code} source value",
            allow_missing_when_empty=True,
            row_count=len(rows),
        )

        evidence_field = resolve_field(
            fields,
            config["evidence_candidates"],
            f"{component_code} source evidence",
            allow_missing_when_empty=True,
            row_count=len(rows),
        )

        records: dict[
            tuple[str, str, str],
            dict[str, object],
        ] = {}

        for row in rows:
            key = race_entry_key(
                row
            )

            if key in records:
                raise RuntimeError(
                    f"Duplicate {component_code} source key: {key}"
                )

            source_fact_id = text(
                row.get(
                    id_field
                )
            )

            source_evidence = text(
                row.get(
                    evidence_field
                )
            )

            if not source_fact_id:
                raise RuntimeError(
                    f"Missing {component_code} source fact ID for {key}"
                )

            if not source_evidence:
                raise RuntimeError(
                    f"Missing {component_code} source evidence for {key}"
                )

            records[key] = {
                "row": row,
                "source_fact_id": source_fact_id,
                "source_evidence": source_evidence,
                "value_field": value_field,
                "raw_value": decimal_value(
                    row.get(
                        value_field
                    ),
                    (
                        f"{component_code}."
                        f"{value_field}"
                    ),
                ),
            }

        source_records[
            component_code
        ] = records

    count_population = set(
        source_row_counts.values()
    )

    if count_population != {0}:
        empty_components = [
            component_code
            for component_code, count in source_row_counts.items()
            if count == 0
        ]

        if empty_components:
            raise RuntimeError(
                "Mixed empty/non-empty EPI component sources. "
                f"Empty components={empty_components}"
            )

    key_sets = {
        component_code: set(records)
        for component_code, records in source_records.items()
    }

    if any(key_sets.values()):
        first_component = next(
            iter(COMPONENT_CONFIG)
        )

        expected_keys = key_sets[
            first_component
        ]

        population_errors = {
            component_code: {
                "missing": sorted(
                    expected_keys - keys
                )[:20],
                "unexpected": sorted(
                    keys - expected_keys
                )[:20],
            }
            for component_code, keys in key_sets.items()
            if keys != expected_keys
        }

        if population_errors:
            raise RuntimeError(
                "EPI component source populations do not reconcile: "
                f"{population_errors}"
            )

    all_keys = set.intersection(
        *key_sets.values()
    ) if key_sets else set()

    grouped_values: dict[
        tuple[str, str, str],
        list[
            tuple[
                tuple[str, str, str],
                Decimal,
            ]
        ],
    ] = defaultdict(list)

    for component_code, records in source_records.items():
        for key, record in records.items():
            _, race_id, race_date = key

            grouped_values[
                (
                    race_id,
                    race_date,
                    component_code,
                )
            ].append(
                (
                    key,
                    record["raw_value"],
                )
            )

    stats: dict[
        tuple[str, str, str],
        dict[str, object],
    ] = {}

    with localcontext() as context:
        context.prec = 50

        for group_key, values in grouped_values.items():
            race_id, race_date, component_code = group_key

            parameter = normalisation_by_component[
                component_code
            ]

            effective_from = text(
                parameter.get(
                    "effective_from_date"
                )
            )

            effective_to = text(
                parameter.get(
                    "effective_to_date"
                )
            )

            if not active_on_date(
                race_date,
                effective_from,
                effective_to,
            ):
                raise RuntimeError(
                    "No active normalisation parameter for "
                    f"{component_code}, race={race_id}, date={race_date}"
                )

            minimum_population = int(
                text(
                    parameter.get(
                        "minimum_population_count"
                    )
                )
            )

            population_count = len(
                values
            )

            if population_count < minimum_population:
                raise RuntimeError(
                    f"Race {race_id} component {component_code} "
                    f"has population {population_count}; "
                    f"minimum={minimum_population}."
                )

            raw_values = [
                value
                for _, value in values
            ]

            mean = (
                sum(
                    raw_values,
                    Decimal("0"),
                )
                / Decimal(
                    population_count
                )
            )

            variance = (
                sum(
                    (
                        value - mean
                    )
                    * (
                        value - mean
                    )
                    for value in raw_values
                )
                / Decimal(
                    population_count
                )
            )

            if variance == Decimal("0"):
                raise RuntimeError(
                    f"Zero component variance for race={race_id}, "
                    f"component={component_code}; FAIL_CLOSED."
                )

            if variance < Decimal("0"):
                raise RuntimeError(
                    f"Negative variance for race={race_id}, "
                    f"component={component_code}."
                )

            population_standard_deviation = (
                variance.sqrt()
            )

            lower_cap = decimal_value(
                parameter[
                    "normalised_lower_cap"
                ],
                "normalised_lower_cap",
            )

            upper_cap = decimal_value(
                parameter[
                    "normalised_upper_cap"
                ],
                "normalised_upper_cap",
            )

            stats[group_key] = {
                "population_count": population_count,
                "mean": mean,
                "population_standard_deviation": (
                    population_standard_deviation
                ),
                "lower_cap": lower_cap,
                "upper_cap": upper_cap,
                "normalisation_parameter_id": text(
                    parameter[
                        "epi_component_normalisation_parameter_id"
                    ]
                ),
            }

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[
        dict[str, str]
    ] = []

    with localcontext() as context:
        context.prec = 50

        for key in sorted(
            all_keys,
            key=lambda value: (
                value[2],
                value[1],
                value[0],
            ),
        ):
            race_entry_id, race_id, race_date = key

            for component_code in [
                "HISTORICAL_PERFORMANCE",
                "SUITABILITY",
                "RACE_CONTEXT",
            ]:
                config = COMPONENT_CONFIG[
                    component_code
                ]

                source_record = source_records[
                    component_code
                ][
                    key
                ]

                raw_value = source_record[
                    "raw_value"
                ]

                group_stats = stats[
                    (
                        race_id,
                        race_date,
                        component_code,
                    )
                ]

                mean = group_stats[
                    "mean"
                ]

                standard_deviation = group_stats[
                    "population_standard_deviation"
                ]

                unbounded = (
                    raw_value - mean
                ) / standard_deviation

                capped = min(
                    group_stats[
                        "upper_cap"
                    ],
                    max(
                        group_stats[
                            "lower_cap"
                        ],
                        unbounded,
                    ),
                )

                authorised_weight = weight_by_component[
                    component_code
                ]

                weighted = (
                    capped
                    * authorised_weight
                )

                raw_text = decimal_text(
                    raw_value
                )

                mean_text = decimal_text(
                    mean
                )

                standard_deviation_text = decimal_text(
                    standard_deviation
                )

                unbounded_text = decimal_text(
                    unbounded
                )

                capped_text = decimal_text(
                    capped
                )

                weight_text = decimal_text(
                    authorised_weight
                )

                weighted_text = decimal_text(
                    weighted
                )

                source_fact_id = text(
                    source_record[
                        "source_fact_id"
                    ]
                )

                source_evidence = text(
                    source_record[
                        "source_evidence"
                    ]
                )

                value_field = text(
                    source_record[
                        "value_field"
                    ]
                )

                normalisation_parameter_id = text(
                    group_stats[
                        "normalisation_parameter_id"
                    ]
                )

                identity_hash = sha256_payload(
                    [
                        CONTRACT_VERSION,
                        race_entry_id,
                        race_id,
                        race_date,
                        component_code,
                        source_fact_id,
                        epi_parameter_id,
                        normalisation_parameter_id,
                        PUBLICATION_DECISION,
                    ]
                )

                component_id = (
                    f"REEPIC1-"
                    f"{identity_hash[:24].upper()}"
                )

                source_lineage = (
                    f"{config['fact_name']}:{source_fact_id}"
                    f"|edgeiq_epi_parameter_fact_v1:{epi_parameter_id}"
                    f"|edgeiq_epi_component_normalisation_parameter_fact_v1:"
                    f"{normalisation_parameter_id}"
                )

                evidence_hash = sha256_payload(
                    [
                        component_id,
                        race_entry_id,
                        race_id,
                        race_date,
                        component_code,
                        config[
                            "fact_name"
                        ],
                        source_fact_id,
                        value_field,
                        source_evidence,
                        raw_text,
                        str(
                            group_stats[
                                "population_count"
                            ]
                        ),
                        mean_text,
                        standard_deviation_text,
                        unbounded_text,
                        capped_text,
                        weight_text,
                        weighted_text,
                        epi_parameter_id,
                        normalisation_parameter_id,
                        PUBLICATION_DECISION,
                        RECONCILIATION_DECISION,
                        GOVERNED_STATUS,
                        source_lineage,
                    ]
                )

                output_rows.append(
                    {
                        "race_entry_epi_component_id": (
                            component_id
                        ),
                        "race_entry_id": race_entry_id,
                        "race_id": race_id,
                        "race_date": race_date,
                        "epi_component_code": (
                            component_code
                        ),
                        "component_source_fact_name": (
                            config[
                                "fact_name"
                            ]
                        ),
                        "component_source_fact_id": (
                            source_fact_id
                        ),
                        "component_source_value_field": (
                            value_field
                        ),
                        "component_source_evidence_sha256": (
                            source_evidence
                        ),
                        "raw_component_value": (
                            raw_text
                        ),
                        "field_population_count": str(
                            group_stats[
                                "population_count"
                            ]
                        ),
                        "field_component_mean": (
                            mean_text
                        ),
                        "field_component_population_standard_deviation": (
                            standard_deviation_text
                        ),
                        "unbounded_normalised_component_value": (
                            unbounded_text
                        ),
                        "capped_normalised_component_value": (
                            capped_text
                        ),
                        "authorised_component_weight": (
                            weight_text
                        ),
                        "weighted_component_value": (
                            weighted_text
                        ),
                        "epi_parameter_id": (
                            epi_parameter_id
                        ),
                        "epi_component_normalisation_parameter_id": (
                            normalisation_parameter_id
                        ),
                        "epi_component_publication_decision": (
                            PUBLICATION_DECISION
                        ),
                        "epi_component_reconciliation_decision": (
                            RECONCILIATION_DECISION
                        ),
                        "epi_component_status": (
                            GOVERNED_STATUS
                        ),
                        "race_entry_epi_component_evidence_sha256": (
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
        "EDGEIQ_RACE_ENTRY_EPI_COMPONENT_FACT_V1_BUILD_PASS"
    )
    print(
        f"projected_rows={source_row_counts['HISTORICAL_PERFORMANCE']}"
    )
    print(
        f"suitability_rows={source_row_counts['SUITABILITY']}"
    )
    print(
        f"eri_context_rows={source_row_counts['RACE_CONTEXT']}"
    )
    print(
        f"eligible_race_entries={len(all_keys)}"
    )
    print(
        f"epi_component_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
