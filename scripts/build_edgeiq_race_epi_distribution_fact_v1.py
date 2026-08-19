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

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_epi_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_epi_distribution_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_race_epi_distribution_fact_v1.0.0"
)

SOURCE_PUBLICATION = "EPI_PUBLISHED"
SOURCE_RECONCILIATION = "EPI_RECONCILED"
SOURCE_STATUS = "GOVERNED_RACE_ENTRY_EPI"

PUBLICATION_DECISION = (
    "RACE_EPI_DISTRIBUTION_PUBLISHED"
)

RECONCILIATION_DECISION = (
    "RACE_EPI_DISTRIBUTION_RECONCILED"
)

GOVERNED_STATUS = (
    "GOVERNED_RACE_EPI_DISTRIBUTION"
)

QUANTUM = Decimal("0.000001")
DECIMAL_PLACES = 6

OUTPUT_FIELDS = [
    "race_epi_distribution_id",
    "race_id",
    "race_date",
    "eligible_epi_population_count",
    "field_epi_total",
    "field_epi_mean",
    "field_epi_population_variance",
    "field_epi_population_standard_deviation",
    "minimum_epi",
    "maximum_epi",
    "epi_range",
    "source_population_sha256",
    "race_epi_distribution_publication_decision",
    "race_epi_distribution_reconciliation_decision",
    "race_epi_distribution_status",
    "race_epi_distribution_evidence_sha256",
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
            f"Required governed source does not exist: {path}"
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


def main() -> None:
    source_fields, source_rows = read_csv(
        SOURCE_PATH
    )

    required_source_fields = {
        "race_entry_epi_id",
        "race_entry_id",
        "race_id",
        "race_date",
        "epi_value",
        "epi_publication_decision",
        "epi_reconciliation_decision",
        "epi_status",
        "race_entry_epi_evidence_sha256",
    }

    missing_source_fields = sorted(
        required_source_fields
        - set(source_fields)
    )

    if missing_source_fields:
        raise RuntimeError(
            "Race Entry EPI Fact is missing required fields: "
            f"{missing_source_fields}"
        )

    grouped: dict[
        tuple[str, str],
        list[dict[str, object]],
    ] = defaultdict(list)

    seen_epi_ids: set[str] = set()
    seen_race_entry_ids: set[str] = set()

    for row in source_rows:
        race_entry_epi_id = text(
            row.get(
                "race_entry_epi_id"
            )
        )

        race_entry_id = text(
            row.get(
                "race_entry_id"
            )
        )

        race_id = text(
            row.get(
                "race_id"
            )
        )

        race_date = text(
            row.get(
                "race_date"
            )
        )

        source_evidence = text(
            row.get(
                "race_entry_epi_evidence_sha256"
            )
        )

        if not race_entry_epi_id:
            raise RuntimeError(
                "Race Entry EPI source row is missing race_entry_epi_id."
            )

        if race_entry_epi_id in seen_epi_ids:
            raise RuntimeError(
                f"Duplicate Race Entry EPI ID: {race_entry_epi_id}"
            )

        seen_epi_ids.add(
            race_entry_epi_id
        )

        if not race_entry_id:
            raise RuntimeError(
                "Race Entry EPI source row is missing race_entry_id."
            )

        if race_entry_id in seen_race_entry_ids:
            raise RuntimeError(
                f"Duplicate race_entry_id in Race Entry EPI Fact: "
                f"{race_entry_id}"
            )

        seen_race_entry_ids.add(
            race_entry_id
        )

        if not race_id or not race_date:
            raise RuntimeError(
                f"Incomplete race identity for race entry {race_entry_id}."
            )

        if not source_evidence:
            raise RuntimeError(
                f"Missing EPI evidence for race entry {race_entry_id}."
            )

        if text(
            row.get(
                "epi_publication_decision"
            )
        ) != SOURCE_PUBLICATION:
            raise RuntimeError(
                f"Unpublished source EPI for race entry {race_entry_id}."
            )

        if text(
            row.get(
                "epi_reconciliation_decision"
            )
        ) != SOURCE_RECONCILIATION:
            raise RuntimeError(
                f"Unreconciled source EPI for race entry {race_entry_id}."
            )

        if text(
            row.get(
                "epi_status"
            )
        ) != SOURCE_STATUS:
            raise RuntimeError(
                f"Ungoverned source EPI for race entry {race_entry_id}."
            )

        epi_value = decimal_value(
            row.get(
                "epi_value"
            ),
            f"{race_entry_id}.epi_value",
        )

        grouped[
            (
                race_id,
                race_date,
            )
        ].append(
            {
                "race_entry_epi_id": race_entry_epi_id,
                "race_entry_id": race_entry_id,
                "epi_value": epi_value,
                "epi_value_text": decimal_text(
                    epi_value
                ),
                "source_evidence": source_evidence,
            }
        )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, str]] = []

    with localcontext() as context:
        context.prec = 50

        for race_key in sorted(
            grouped,
            key=lambda value: (
                value[1],
                value[0],
            ),
        ):
            race_id, race_date = race_key

            population = sorted(
                grouped[
                    race_key
                ],
                key=lambda record: (
                    text(
                        record[
                            "race_entry_id"
                        ]
                    ),
                    text(
                        record[
                            "race_entry_epi_id"
                        ]
                    ),
                ),
            )

            race_entry_ids = [
                text(
                    record[
                        "race_entry_id"
                    ]
                )
                for record in population
            ]

            if len(
                race_entry_ids
            ) != len(
                set(
                    race_entry_ids
                )
            ):
                raise RuntimeError(
                    f"Duplicate race-entry population in race {race_id}."
                )

            population_count = len(
                population
            )

            if population_count < 1:
                raise RuntimeError(
                    f"Empty grouped population for race {race_id}."
                )

            epi_values = [
                record[
                    "epi_value"
                ]
                for record in population
            ]

            epi_total = sum(
                epi_values,
                Decimal("0"),
            )

            epi_mean = (
                epi_total
                / Decimal(
                    population_count
                )
            )

            population_variance = (
                sum(
                    (
                        value - epi_mean
                    )
                    * (
                        value - epi_mean
                    )
                    for value in epi_values
                )
                / Decimal(
                    population_count
                )
            )

            if population_variance < Decimal("0"):
                raise RuntimeError(
                    f"Negative EPI variance for race {race_id}."
                )

            population_standard_deviation = (
                population_variance.sqrt()
            )

            minimum_epi = min(
                epi_values
            )

            maximum_epi = max(
                epi_values
            )

            epi_range = (
                maximum_epi
                - minimum_epi
            )

            population_count_text = str(
                population_count
            )

            epi_total_text = decimal_text(
                epi_total
            )

            epi_mean_text = decimal_text(
                epi_mean
            )

            population_variance_text = decimal_text(
                population_variance
            )

            population_standard_deviation_text = decimal_text(
                population_standard_deviation
            )

            minimum_epi_text = decimal_text(
                minimum_epi
            )

            maximum_epi_text = decimal_text(
                maximum_epi
            )

            epi_range_text = decimal_text(
                epi_range
            )

            population_evidence_parts: list[object] = []

            for record in population:
                population_evidence_parts.extend(
                    [
                        record[
                            "race_entry_id"
                        ],
                        record[
                            "race_entry_epi_id"
                        ],
                        record[
                            "epi_value_text"
                        ],
                        record[
                            "source_evidence"
                        ],
                    ]
                )

            source_population_sha256 = sha256_payload(
                population_evidence_parts
            )

            identity_hash = sha256_payload(
                [
                    CONTRACT_VERSION,
                    race_id,
                    race_date,
                    population_count_text,
                    source_population_sha256,
                    PUBLICATION_DECISION,
                ]
            )

            distribution_id = (
                f"REDIST1-"
                f"{identity_hash[:24].upper()}"
            )

            source_epi_ids = ",".join(
                text(
                    record[
                        "race_entry_epi_id"
                    ]
                )
                for record in population
            )

            source_lineage = (
                "edgeiq_race_entry_epi_fact_v1:"
                f"{source_epi_ids}"
            )

            distribution_evidence = sha256_payload(
                [
                    distribution_id,
                    race_id,
                    race_date,
                    population_count_text,
                    epi_total_text,
                    epi_mean_text,
                    population_variance_text,
                    population_standard_deviation_text,
                    minimum_epi_text,
                    maximum_epi_text,
                    epi_range_text,
                    source_population_sha256,
                    PUBLICATION_DECISION,
                    RECONCILIATION_DECISION,
                    GOVERNED_STATUS,
                    source_lineage,
                ]
            )

            output_rows.append(
                {
                    "race_epi_distribution_id": (
                        distribution_id
                    ),
                    "race_id": (
                        race_id
                    ),
                    "race_date": (
                        race_date
                    ),
                    "eligible_epi_population_count": (
                        population_count_text
                    ),
                    "field_epi_total": (
                        epi_total_text
                    ),
                    "field_epi_mean": (
                        epi_mean_text
                    ),
                    "field_epi_population_variance": (
                        population_variance_text
                    ),
                    "field_epi_population_standard_deviation": (
                        population_standard_deviation_text
                    ),
                    "minimum_epi": (
                        minimum_epi_text
                    ),
                    "maximum_epi": (
                        maximum_epi_text
                    ),
                    "epi_range": (
                        epi_range_text
                    ),
                    "source_population_sha256": (
                        source_population_sha256
                    ),
                    "race_epi_distribution_publication_decision": (
                        PUBLICATION_DECISION
                    ),
                    "race_epi_distribution_reconciliation_decision": (
                        RECONCILIATION_DECISION
                    ),
                    "race_epi_distribution_status": (
                        GOVERNED_STATUS
                    ),
                    "race_epi_distribution_evidence_sha256": (
                        distribution_evidence
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
        "EDGEIQ_RACE_EPI_DISTRIBUTION_FACT_V1_BUILD_PASS"
    )
    print(
        f"race_entry_epi_rows={len(source_rows)}"
    )
    print(
        f"race_epi_distribution_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
