from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_epi_relative_context_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_ordering_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_race_entry_epi_ordering_fact_v1.0.0"

SOURCE_PUBLICATION = "EPI_RELATIVE_CONTEXT_PUBLISHED"
SOURCE_RECONCILIATION = "EPI_RELATIVE_CONTEXT_RECONCILED"
SOURCE_STATUS = "GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT"

PUBLICATION_DECISION = "EPI_ORDERING_PUBLISHED"
RECONCILIATION_DECISION = "EPI_ORDERING_RECONCILED"
GOVERNED_STATUS = "GOVERNED_RACE_ENTRY_EPI_ORDERING"

OUTPUT_FIELDS = [
    "race_entry_epi_ordering_id",
    "race_entry_id",
    "race_entry_epi_relative_context_id",
    "race_id",
    "race_date",
    "runner_epi_value",
    "eligible_epi_population_count",
    "epi_display_order_position",
    "epi_competition_rank",
    "epi_dense_rank",
    "epi_tie_group_size",
    "epi_tie_group_position",
    "epi_tie_status",
    "race_entry_epi_relative_context_evidence_sha256",
    "epi_ordering_publication_decision",
    "epi_ordering_reconciliation_decision",
    "epi_ordering_status",
    "race_entry_epi_ordering_evidence_sha256",
    "source_lineage",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


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

    if parsed.as_tuple().exponent != -6:
        raise RuntimeError(
            f"Expected six-decimal governed EPI for {field_name}: {raw}"
        )

    return parsed


def integer_value(
    value: object,
    field_name: str,
) -> int:
    raw = text(value)

    if not raw:
        raise RuntimeError(
            f"Missing integer value: {field_name}"
        )

    try:
        parsed = int(raw)
    except ValueError as error:
        raise RuntimeError(
            f"Invalid integer value for {field_name}: {raw}"
        ) from error

    return parsed


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
        "race_entry_epi_relative_context_id",
        "race_entry_id",
        "race_id",
        "race_date",
        "runner_epi_value",
        "eligible_epi_population_count",
        "epi_relative_context_publication_decision",
        "epi_relative_context_reconciliation_decision",
        "epi_relative_context_status",
        "race_entry_epi_relative_context_evidence_sha256",
    }

    missing_fields = sorted(
        required_source_fields
        - set(source_fields)
    )

    if missing_fields:
        raise RuntimeError(
            f"Relative-context source is missing fields: {missing_fields}"
        )

    grouped: dict[
        tuple[str, str],
        list[dict[str, object]],
    ] = defaultdict(list)

    seen_context_ids: set[str] = set()
    seen_race_entry_ids: set[str] = set()

    for row in source_rows:
        context_id = text(
            row.get(
                "race_entry_epi_relative_context_id"
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
                "race_entry_epi_relative_context_evidence_sha256"
            )
        )

        if not context_id:
            raise RuntimeError(
                "Relative-context source row is missing its identity."
            )

        if context_id in seen_context_ids:
            raise RuntimeError(
                f"Duplicate relative-context ID: {context_id}"
            )

        seen_context_ids.add(
            context_id
        )

        if not race_entry_id:
            raise RuntimeError(
                f"Missing race_entry_id for {context_id}."
            )

        if race_entry_id in seen_race_entry_ids:
            raise RuntimeError(
                f"Duplicate race_entry_id: {race_entry_id}"
            )

        seen_race_entry_ids.add(
            race_entry_id
        )

        if not race_id or not race_date:
            raise RuntimeError(
                f"Incomplete race identity for {race_entry_id}."
            )

        if not source_evidence:
            raise RuntimeError(
                f"Missing source evidence for {race_entry_id}."
            )

        if text(
            row.get(
                "epi_relative_context_publication_decision"
            )
        ) != SOURCE_PUBLICATION:
            raise RuntimeError(
                f"Unpublished relative context: {race_entry_id}"
            )

        if text(
            row.get(
                "epi_relative_context_reconciliation_decision"
            )
        ) != SOURCE_RECONCILIATION:
            raise RuntimeError(
                f"Unreconciled relative context: {race_entry_id}"
            )

        if text(
            row.get(
                "epi_relative_context_status"
            )
        ) != SOURCE_STATUS:
            raise RuntimeError(
                f"Ungoverned relative context: {race_entry_id}"
            )

        runner_epi = decimal_value(
            row.get(
                "runner_epi_value"
            ),
            f"{race_entry_id}.runner_epi_value",
        )

        population_count = integer_value(
            row.get(
                "eligible_epi_population_count"
            ),
            f"{race_entry_id}.eligible_epi_population_count",
        )

        if population_count < 1:
            raise RuntimeError(
                f"Invalid source population count: {race_entry_id}"
            )

        grouped[
            (
                race_id,
                race_date,
            )
        ].append(
            {
                "context_id": context_id,
                "race_entry_id": race_entry_id,
                "race_id": race_id,
                "race_date": race_date,
                "runner_epi": runner_epi,
                "runner_epi_text": text(
                    row.get(
                        "runner_epi_value"
                    )
                ),
                "population_count": population_count,
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

    for race_key in sorted(
        grouped,
        key=lambda value: (
            value[1],
            value[0],
        ),
    ):
        population = grouped[
            race_key
        ]

        actual_population_count = len(
            population
        )

        declared_population_counts = {
            int(
                record[
                    "population_count"
                ]
            )
            for record in population
        }

        if declared_population_counts != {
            actual_population_count
        }:
            raise RuntimeError(
                f"Population count does not reconcile for race {race_key}: "
                f"declared={declared_population_counts}, "
                f"actual={actual_population_count}"
            )

        epi_frequency = Counter(
            record[
                "runner_epi_text"
            ]
            for record in population
        )

        sorted_population = sorted(
            population,
            key=lambda record: (
                -record[
                    "runner_epi"
                ],
                text(
                    record[
                        "race_entry_id"
                    ]
                ),
            ),
        )

        distinct_epi_descending = sorted(
            {
                record[
                    "runner_epi"
                ]
                for record in population
            },
            reverse=True,
        )

        dense_rank_by_epi = {
            epi_value: index
            for index, epi_value in enumerate(
                distinct_epi_descending,
                start=1,
            )
        }

        competition_rank_by_epi: dict[
            Decimal,
            int,
        ] = {}

        previous_epi: Decimal | None = None

        for display_position, record in enumerate(
            sorted_population,
            start=1,
        ):
            current_epi = record[
                "runner_epi"
            ]

            if previous_epi is None or current_epi != previous_epi:
                competition_rank_by_epi[
                    current_epi
                ] = display_position

            previous_epi = current_epi

        tie_group_position_counter: dict[
            str,
            int,
        ] = defaultdict(int)

        for display_position, record in enumerate(
            sorted_population,
            start=1,
        ):
            race_entry_id = text(
                record[
                    "race_entry_id"
                ]
            )

            context_id = text(
                record[
                    "context_id"
                ]
            )

            runner_epi = record[
                "runner_epi"
            ]

            runner_epi_text = text(
                record[
                    "runner_epi_text"
                ]
            )

            source_evidence = text(
                record[
                    "source_evidence"
                ]
            )

            tie_group_size = epi_frequency[
                runner_epi_text
            ]

            tie_group_position_counter[
                runner_epi_text
            ] += 1

            tie_group_position = (
                tie_group_position_counter[
                    runner_epi_text
                ]
            )

            competition_rank = (
                competition_rank_by_epi[
                    runner_epi
                ]
            )

            dense_rank = (
                dense_rank_by_epi[
                    runner_epi
                ]
            )

            tie_status = (
                "TIED_EPI"
                if tie_group_size > 1
                else "UNIQUE_EPI"
            )

            identity_hash = sha256_payload(
                [
                    CONTRACT_VERSION,
                    race_entry_id,
                    race_key[0],
                    race_key[1],
                    context_id,
                    runner_epi_text,
                    display_position,
                    competition_rank,
                    dense_rank,
                    PUBLICATION_DECISION,
                ]
            )

            ordering_id = (
                f"REEO1-"
                f"{identity_hash[:24].upper()}"
            )

            source_lineage = (
                "edgeiq_race_entry_epi_relative_context_fact_v1:"
                f"{context_id}"
            )

            evidence_hash = sha256_payload(
                [
                    ordering_id,
                    race_entry_id,
                    context_id,
                    race_key[0],
                    race_key[1],
                    runner_epi_text,
                    actual_population_count,
                    display_position,
                    competition_rank,
                    dense_rank,
                    tie_group_size,
                    tie_group_position,
                    tie_status,
                    source_evidence,
                    PUBLICATION_DECISION,
                    RECONCILIATION_DECISION,
                    GOVERNED_STATUS,
                    source_lineage,
                ]
            )

            output_rows.append(
                {
                    "race_entry_epi_ordering_id": (
                        ordering_id
                    ),
                    "race_entry_id": (
                        race_entry_id
                    ),
                    "race_entry_epi_relative_context_id": (
                        context_id
                    ),
                    "race_id": (
                        race_key[0]
                    ),
                    "race_date": (
                        race_key[1]
                    ),
                    "runner_epi_value": (
                        runner_epi_text
                    ),
                    "eligible_epi_population_count": (
                        str(
                            actual_population_count
                        )
                    ),
                    "epi_display_order_position": (
                        str(
                            display_position
                        )
                    ),
                    "epi_competition_rank": (
                        str(
                            competition_rank
                        )
                    ),
                    "epi_dense_rank": (
                        str(
                            dense_rank
                        )
                    ),
                    "epi_tie_group_size": (
                        str(
                            tie_group_size
                        )
                    ),
                    "epi_tie_group_position": (
                        str(
                            tie_group_position
                        )
                    ),
                    "epi_tie_status": (
                        tie_status
                    ),
                    "race_entry_epi_relative_context_evidence_sha256": (
                        source_evidence
                    ),
                    "epi_ordering_publication_decision": (
                        PUBLICATION_DECISION
                    ),
                    "epi_ordering_reconciliation_decision": (
                        RECONCILIATION_DECISION
                    ),
                    "epi_ordering_status": (
                        GOVERNED_STATUS
                    ),
                    "race_entry_epi_ordering_evidence_sha256": (
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
        "EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_BUILD_PASS"
    )
    print(
        f"relative_context_rows={len(source_rows)}"
    )
    print(
        f"source_race_count={len(grouped)}"
    )
    print(
        f"ordering_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
