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
    / "edgeiq_race_entry_epi_ordering_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_publication_snapshot_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_race_entry_epi_publication_snapshot_fact_v1.0.0"
)

SOURCE_PUBLICATION = "EPI_ORDERING_PUBLISHED"
SOURCE_RECONCILIATION = "EPI_ORDERING_RECONCILED"
SOURCE_STATUS = "GOVERNED_RACE_ENTRY_EPI_ORDERING"

PUBLICATION_DECISION = "RACE_ENTRY_EPI_SNAPSHOT_PUBLISHED"
RECONCILIATION_DECISION = "RACE_ENTRY_EPI_SNAPSHOT_RECONCILED"
GOVERNED_STATUS = (
    "GOVERNED_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT"
)

OUTPUT_FIELDS = [
    "race_entry_epi_publication_snapshot_id",
    "race_entry_id",
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
    "source_relative_context_evidence_sha256",
    "source_ordering_id",
    "source_ordering_evidence_sha256",
    "race_entry_epi_snapshot_publication_decision",
    "race_entry_epi_snapshot_reconciliation_decision",
    "race_entry_epi_snapshot_status",
    "race_entry_epi_publication_snapshot_evidence_sha256",
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

    if parsed.as_tuple().exponent != -6:
        raise RuntimeError(
            f"Expected six-decimal governed EPI for "
            f"{field_name}: {raw}"
        )

    return parsed


def integer_value(
    value: object,
    field_name: str,
) -> int:
    raw = text(value)

    try:
        parsed = int(raw)
    except ValueError as error:
        raise RuntimeError(
            f"Invalid integer for {field_name}: {raw}"
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
        "race_entry_epi_ordering_id",
        "race_entry_id",
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
    }

    missing_fields = sorted(
        required_source_fields
        - set(source_fields)
    )

    if missing_fields:
        raise RuntimeError(
            "Ordering source missing required fields: "
            f"{missing_fields}"
        )

    seen_ordering_ids: set[str] = set()
    seen_race_entry_ids: set[str] = set()

    grouped: dict[
        tuple[str, str],
        list[dict[str, object]],
    ] = defaultdict(list)

    validated_rows: list[dict[str, object]] = []

    for row in source_rows:
        ordering_id = text(
            row.get(
                "race_entry_epi_ordering_id"
            )
        )

        race_entry_id = text(
            row.get("race_entry_id")
        )

        race_id = text(
            row.get("race_id")
        )

        race_date = text(
            row.get("race_date")
        )

        relative_evidence = text(
            row.get(
                "race_entry_epi_relative_context_evidence_sha256"
            )
        )

        ordering_evidence = text(
            row.get(
                "race_entry_epi_ordering_evidence_sha256"
            )
        )

        if not ordering_id:
            raise RuntimeError(
                "Ordering row is missing its identity."
            )

        if ordering_id in seen_ordering_ids:
            raise RuntimeError(
                f"Duplicate ordering identity: {ordering_id}"
            )

        seen_ordering_ids.add(ordering_id)

        if not race_entry_id:
            raise RuntimeError(
                f"Missing race_entry_id for {ordering_id}."
            )

        if race_entry_id in seen_race_entry_ids:
            raise RuntimeError(
                f"Duplicate race_entry_id: {race_entry_id}"
            )

        seen_race_entry_ids.add(race_entry_id)

        if not race_id or not race_date:
            raise RuntimeError(
                f"Incomplete race identity for {race_entry_id}."
            )

        if not relative_evidence:
            raise RuntimeError(
                f"Missing relative-context evidence for "
                f"{race_entry_id}."
            )

        if not ordering_evidence:
            raise RuntimeError(
                f"Missing ordering evidence for {race_entry_id}."
            )

        if text(
            row.get(
                "epi_ordering_publication_decision"
            )
        ) != SOURCE_PUBLICATION:
            raise RuntimeError(
                f"Unpublished source ordering row: "
                f"{race_entry_id}"
            )

        if text(
            row.get(
                "epi_ordering_reconciliation_decision"
            )
        ) != SOURCE_RECONCILIATION:
            raise RuntimeError(
                f"Unreconciled source ordering row: "
                f"{race_entry_id}"
            )

        if text(
            row.get("epi_ordering_status")
        ) != SOURCE_STATUS:
            raise RuntimeError(
                f"Ungoverned source ordering row: "
                f"{race_entry_id}"
            )

        epi_text = text(
            row.get("runner_epi_value")
        )

        epi = decimal_value(
            epi_text,
            f"{race_entry_id}.runner_epi_value",
        )

        population_count = integer_value(
            row.get(
                "eligible_epi_population_count"
            ),
            (
                f"{race_entry_id}."
                "eligible_epi_population_count"
            ),
        )

        display_position = integer_value(
            row.get(
                "epi_display_order_position"
            ),
            (
                f"{race_entry_id}."
                "epi_display_order_position"
            ),
        )

        competition_rank = integer_value(
            row.get("epi_competition_rank"),
            f"{race_entry_id}.epi_competition_rank",
        )

        dense_rank = integer_value(
            row.get("epi_dense_rank"),
            f"{race_entry_id}.epi_dense_rank",
        )

        tie_group_size = integer_value(
            row.get("epi_tie_group_size"),
            f"{race_entry_id}.epi_tie_group_size",
        )

        tie_group_position = integer_value(
            row.get("epi_tie_group_position"),
            f"{race_entry_id}.epi_tie_group_position",
        )

        tie_status = text(
            row.get("epi_tie_status")
        )

        if population_count < 1:
            raise RuntimeError(
                f"Invalid population count for {race_entry_id}."
            )

        for field_name, value in [
            (
                "epi_display_order_position",
                display_position,
            ),
            (
                "epi_competition_rank",
                competition_rank,
            ),
            (
                "epi_dense_rank",
                dense_rank,
            ),
            (
                "epi_tie_group_size",
                tie_group_size,
            ),
            (
                "epi_tie_group_position",
                tie_group_position,
            ),
        ]:
            if value < 1:
                raise RuntimeError(
                    f"Invalid {field_name} for {race_entry_id}."
                )

        if tie_status not in {
            "EPI_UNIQUE",
            "EPI_TIED",
        }:
            raise RuntimeError(
                f"Invalid EPI tie status for {race_entry_id}: "
                f"{tie_status}"
            )

        if (
            tie_status == "EPI_UNIQUE"
            and tie_group_size != 1
        ):
            raise RuntimeError(
                f"Unique EPI row has invalid tie-group size: "
                f"{race_entry_id}"
            )

        if (
            tie_status == "EPI_TIED"
            and tie_group_size < 2
        ):
            raise RuntimeError(
                f"Tied EPI row has invalid tie-group size: "
                f"{race_entry_id}"
            )

        validated = {
            "ordering_id": ordering_id,
            "race_entry_id": race_entry_id,
            "race_id": race_id,
            "race_date": race_date,
            "epi": epi,
            "epi_text": epi_text,
            "population_count": population_count,
            "display_position": display_position,
            "competition_rank": competition_rank,
            "dense_rank": dense_rank,
            "tie_group_size": tie_group_size,
            "tie_group_position": tie_group_position,
            "tie_status": tie_status,
            "relative_evidence": relative_evidence,
            "ordering_evidence": ordering_evidence,
        }

        validated_rows.append(validated)
        grouped[(race_id, race_date)].append(
            validated
        )

    for race_key, population in grouped.items():
        race_population_count = len(
            population
        )

        declared_counts = {
            int(record["population_count"])
            for record in population
        }

        if declared_counts != {
            race_population_count
        }:
            raise RuntimeError(
                f"Population count mismatch for race {race_key}: "
                f"declared={declared_counts}, "
                f"actual={race_population_count}"
            )

        ordered = sorted(
            population,
            key=lambda record: int(
                record["display_position"]
            ),
        )

        display_positions = [
            int(record["display_position"])
            for record in ordered
        ]

        if display_positions != list(
            range(1, race_population_count + 1)
        ):
            raise RuntimeError(
                f"Display order does not reconcile for "
                f"race {race_key}."
            )

        epi_values = [
            record["epi"]
            for record in ordered
        ]

        if epi_values != sorted(
            epi_values,
            reverse=True,
        ):
            raise RuntimeError(
                f"EPI ordering is not descending for race "
                f"{race_key}."
            )

        epi_frequency = Counter(
            text(record["epi_text"])
            for record in population
        )

        distinct_epi = sorted(
            {
                record["epi"]
                for record in population
            },
            reverse=True,
        )

        expected_dense_rank = {
            value: index + 1
            for index, value in enumerate(
                distinct_epi
            )
        }

        greater_count_rank = {
            value: (
                sum(
                    1
                    for record in population
                    if record["epi"] > value
                )
                + 1
            )
            for value in distinct_epi
        }

        tie_positions: dict[
            str,
            list[int],
        ] = defaultdict(list)

        for record in population:
            tie_positions[
                text(record["epi_text"])
            ].append(
                int(record["tie_group_position"])
            )

            expected_frequency = epi_frequency[
                text(record["epi_text"])
            ]

            if (
                int(record["tie_group_size"])
                != expected_frequency
            ):
                raise RuntimeError(
                    f"Tie-group size mismatch for "
                    f"{record['race_entry_id']}."
                )

            expected_status = (
                "EPI_TIED"
                if expected_frequency > 1
                else "EPI_UNIQUE"
            )

            if record["tie_status"] != expected_status:
                raise RuntimeError(
                    f"Tie status mismatch for "
                    f"{record['race_entry_id']}."
                )

            if (
                int(record["competition_rank"])
                != greater_count_rank[
                    record["epi"]
                ]
            ):
                raise RuntimeError(
                    f"Competition rank mismatch for "
                    f"{record['race_entry_id']}."
                )

            if (
                int(record["dense_rank"])
                != expected_dense_rank[
                    record["epi"]
                ]
            ):
                raise RuntimeError(
                    f"Dense rank mismatch for "
                    f"{record['race_entry_id']}."
                )

        for epi_text, positions in tie_positions.items():
            expected_positions = list(
                range(
                    1,
                    epi_frequency[epi_text] + 1,
                )
            )

            if sorted(positions) != expected_positions:
                raise RuntimeError(
                    f"Tie-group positions do not reconcile "
                    f"for race {race_key}, EPI {epi_text}."
                )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, str]] = []

    for record in sorted(
        validated_rows,
        key=lambda item: (
            text(item["race_date"]),
            text(item["race_id"]),
            int(item["display_position"]),
        ),
    ):
        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                record["race_entry_id"],
                record["race_id"],
                record["race_date"],
                record["epi_text"],
                record["display_position"],
                record["competition_rank"],
                PUBLICATION_DECISION,
            ]
        )

        snapshot_id = (
            "REEPS1-"
            f"{identity_hash[:24].upper()}"
        )

        source_lineage = (
            "edgeiq_race_entry_epi_ordering_fact_v1:"
            f"{record['ordering_id']}"
        )

        evidence_hash = sha256_payload(
            [
                snapshot_id,
                record["race_entry_id"],
                record["race_id"],
                record["race_date"],
                record["epi_text"],
                record["population_count"],
                record["display_position"],
                record["competition_rank"],
                record["dense_rank"],
                record["tie_group_size"],
                record["tie_group_position"],
                record["tie_status"],
                record["relative_evidence"],
                record["ordering_id"],
                record["ordering_evidence"],
                PUBLICATION_DECISION,
                RECONCILIATION_DECISION,
                GOVERNED_STATUS,
                source_lineage,
            ]
        )

        output_rows.append(
            {
                "race_entry_epi_publication_snapshot_id": (
                    snapshot_id
                ),
                "race_entry_id": text(
                    record["race_entry_id"]
                ),
                "race_id": text(
                    record["race_id"]
                ),
                "race_date": text(
                    record["race_date"]
                ),
                "runner_epi_value": text(
                    record["epi_text"]
                ),
                "eligible_epi_population_count": str(
                    record["population_count"]
                ),
                "epi_display_order_position": str(
                    record["display_position"]
                ),
                "epi_competition_rank": str(
                    record["competition_rank"]
                ),
                "epi_dense_rank": str(
                    record["dense_rank"]
                ),
                "epi_tie_group_size": str(
                    record["tie_group_size"]
                ),
                "epi_tie_group_position": str(
                    record["tie_group_position"]
                ),
                "epi_tie_status": text(
                    record["tie_status"]
                ),
                "source_relative_context_evidence_sha256": (
                    text(record["relative_evidence"])
                ),
                "source_ordering_id": text(
                    record["ordering_id"]
                ),
                "source_ordering_evidence_sha256": (
                    text(record["ordering_evidence"])
                ),
                "race_entry_epi_snapshot_publication_decision": (
                    PUBLICATION_DECISION
                ),
                "race_entry_epi_snapshot_reconciliation_decision": (
                    RECONCILIATION_DECISION
                ),
                "race_entry_epi_snapshot_status": (
                    GOVERNED_STATUS
                ),
                "race_entry_epi_publication_snapshot_evidence_sha256": (
                    evidence_hash
                ),
                "source_lineage": source_lineage,
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_BUILD_PASS"
    )
    print(
        f"source_ordering_rows={len(source_rows)}"
    )
    print(
        f"publication_snapshot_rows={len(output_rows)}"
    )
    print(
        f"race_count={len(grouped)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
