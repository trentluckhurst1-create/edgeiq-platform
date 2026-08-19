from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
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
    / "edgeiq_race_epi_ordering_summary_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_race_epi_ordering_summary_fact_v1.0.0"

SOURCE_PUBLICATION = "EPI_ORDERING_PUBLISHED"
SOURCE_RECONCILIATION = "EPI_ORDERING_RECONCILED"
SOURCE_STATUS = "GOVERNED_RACE_ENTRY_EPI_ORDERING"

PUBLICATION_DECISION = "RACE_EPI_ORDERING_SUMMARY_PUBLISHED"
RECONCILIATION_DECISION = "RACE_EPI_ORDERING_SUMMARY_RECONCILED"
GOVERNED_STATUS = "GOVERNED_RACE_EPI_ORDERING_SUMMARY"

QUANTUM = Decimal("0.000001")

OUTPUT_FIELDS = [
    "race_epi_ordering_summary_id",
    "race_id",
    "race_date",
    "ordered_epi_population_count",
    "distinct_epi_count",
    "unique_epi_entry_count",
    "tied_epi_entry_count",
    "tie_group_count",
    "largest_tie_group_size",
    "top_epi",
    "second_distinct_epi_available",
    "second_distinct_epi",
    "top_to_second_epi_gap_available",
    "top_to_second_epi_gap",
    "top_epi_tie_group_size",
    "top_epi_tie_status",
    "source_ordering_identity_sha256",
    "source_ordering_evidence_sha256",
    "race_epi_ordering_summary_publication_decision",
    "race_epi_ordering_summary_reconciliation_decision",
    "race_epi_ordering_summary_status",
    "race_epi_ordering_summary_evidence_sha256",
    "source_lineage",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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

    try:
        parsed = int(raw)
    except ValueError as error:
        raise RuntimeError(
            f"Invalid integer value for {field_name}: {raw}"
        ) from error

    return parsed


def decimal_text(value: Decimal) -> str:
    return format(
        value.quantize(
            QUANTUM,
            rounding=ROUND_HALF_EVEN,
        ),
        ".6f",
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
    path.parent.mkdir(parents=True, exist_ok=True)

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

        os.replace(temporary_path, path)

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    source_fields, source_rows = read_csv(
        SOURCE_PATH
    )

    required_fields = {
        "race_entry_epi_ordering_id",
        "race_entry_id",
        "race_id",
        "race_date",
        "runner_epi_value",
        "eligible_epi_population_count",
        "epi_display_order_position",
        "epi_tie_group_size",
        "epi_tie_status",
        "race_entry_epi_relative_context_evidence_sha256",
        "epi_ordering_publication_decision",
        "epi_ordering_reconciliation_decision",
        "epi_ordering_status",
        "race_entry_epi_ordering_evidence_sha256",
    }

    missing_fields = sorted(
        required_fields - set(source_fields)
    )

    if missing_fields:
        raise RuntimeError(
            f"Ordering source missing fields: {missing_fields}"
        )

    grouped: dict[
        tuple[str, str],
        list[dict[str, object]],
    ] = defaultdict(list)

    seen_ordering_ids: set[str] = set()
    seen_race_entry_ids: set[str] = set()

    for row in source_rows:
        ordering_id = text(
            row.get("race_entry_epi_ordering_id")
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

        source_evidence = text(
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
                f"Duplicate ordering ID: {ordering_id}"
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

        if not source_evidence:
            raise RuntimeError(
                f"Missing ordering evidence for {race_entry_id}."
            )

        if text(
            row.get(
                "epi_ordering_publication_decision"
            )
        ) != SOURCE_PUBLICATION:
            raise RuntimeError(
                f"Unpublished ordering row: {race_entry_id}"
            )

        if text(
            row.get(
                "epi_ordering_reconciliation_decision"
            )
        ) != SOURCE_RECONCILIATION:
            raise RuntimeError(
                f"Unreconciled ordering row: {race_entry_id}"
            )

        if text(
            row.get(
                "epi_ordering_status"
            )
        ) != SOURCE_STATUS:
            raise RuntimeError(
                f"Ungoverned ordering row: {race_entry_id}"
            )

        epi = decimal_value(
            row.get("runner_epi_value"),
            f"{race_entry_id}.runner_epi_value",
        )

        display_position = integer_value(
            row.get("epi_display_order_position"),
            f"{race_entry_id}.epi_display_order_position",
        )

        population_count = integer_value(
            row.get("eligible_epi_population_count"),
            f"{race_entry_id}.eligible_epi_population_count",
        )

        tie_group_size = integer_value(
            row.get("epi_tie_group_size"),
            f"{race_entry_id}.epi_tie_group_size",
        )

        if (
            display_position < 1
            or population_count < 1
            or tie_group_size < 1
        ):
            raise RuntimeError(
                f"Invalid ordering integers for {race_entry_id}."
            )

        grouped[(race_id, race_date)].append(
            {
                "ordering_id": ordering_id,
                "race_entry_id": race_entry_id,
                "race_id": race_id,
                "race_date": race_date,
                "epi": epi,
                "epi_text": text(
                    row.get("runner_epi_value")
                ),
                "display_position": display_position,
                "population_count": population_count,
                "tie_group_size": tie_group_size,
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
        population = grouped[race_key]

        ordered_population = sorted(
            population,
            key=lambda record: int(
                record["display_position"]
            ),
        )

        population_count = len(
            ordered_population
        )

        declared_population_counts = {
            int(record["population_count"])
            for record in ordered_population
        }

        if declared_population_counts != {
            population_count
        }:
            raise RuntimeError(
                f"Population count mismatch for race {race_key}: "
                f"declared={declared_population_counts}, "
                f"actual={population_count}"
            )

        display_positions = [
            int(record["display_position"])
            for record in ordered_population
        ]

        if display_positions != list(
            range(1, population_count + 1)
        ):
            raise RuntimeError(
                f"Display positions do not reconcile for race {race_key}."
            )

        epi_frequency = Counter(
            text(record["epi_text"])
            for record in ordered_population
        )

        distinct_epi_values = sorted(
            {
                record["epi"]
                for record in ordered_population
            },
            reverse=True,
        )

        distinct_epi_count = len(
            distinct_epi_values
        )

        unique_epi_entry_count = sum(
            count
            for count in epi_frequency.values()
            if count == 1
        )

        tied_epi_entry_count = sum(
            count
            for count in epi_frequency.values()
            if count > 1
        )

        tie_group_count = sum(
            1
            for count in epi_frequency.values()
            if count > 1
        )

        largest_tie_group_size = max(
            epi_frequency.values()
        )

        top_epi = distinct_epi_values[0]
        top_epi_text = decimal_text(top_epi)

        top_epi_tie_group_size = epi_frequency[
            top_epi_text
        ]

        top_epi_tie_status = (
            "TOP_EPI_TIED"
            if top_epi_tie_group_size > 1
            else "TOP_EPI_UNIQUE"
        )

        if distinct_epi_count >= 2:
            second_available = "YES"
            second_epi = distinct_epi_values[1]
            second_epi_text = decimal_text(
                second_epi
            )

            gap_available = "YES"
            gap_text = decimal_text(
                top_epi - second_epi
            )

            if Decimal(gap_text) <= Decimal("0"):
                raise RuntimeError(
                    f"Non-positive top-to-second gap for race {race_key}."
                )

        else:
            second_available = "NO"
            second_epi_text = ""
            gap_available = "NO"
            gap_text = ""

        if (
            unique_epi_entry_count
            + tied_epi_entry_count
            != population_count
        ):
            raise RuntimeError(
                f"Unique/tied population does not reconcile for race {race_key}."
            )

        ordered_source_ids = [
            text(record["ordering_id"])
            for record in ordered_population
        ]

        ordered_source_evidence = [
            text(record["source_evidence"])
            for record in ordered_population
        ]

        source_identity_hash = sha256_payload(
            ordered_source_ids
        )

        source_evidence_hash = sha256_payload(
            ordered_source_evidence
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_key[0],
                race_key[1],
                population_count,
                distinct_epi_count,
                top_epi_text,
                PUBLICATION_DECISION,
            ]
        )

        summary_id = (
            f"REOS1-{identity_hash[:24].upper()}"
        )

        source_lineage = (
            "edgeiq_race_entry_epi_ordering_fact_v1:"
            f"{source_identity_hash}"
        )

        evidence_hash = sha256_payload(
            [
                summary_id,
                race_key[0],
                race_key[1],
                population_count,
                distinct_epi_count,
                unique_epi_entry_count,
                tied_epi_entry_count,
                tie_group_count,
                largest_tie_group_size,
                top_epi_text,
                second_available,
                second_epi_text,
                gap_available,
                gap_text,
                top_epi_tie_group_size,
                top_epi_tie_status,
                source_identity_hash,
                source_evidence_hash,
                PUBLICATION_DECISION,
                RECONCILIATION_DECISION,
                GOVERNED_STATUS,
                source_lineage,
            ]
        )

        output_rows.append(
            {
                "race_epi_ordering_summary_id": summary_id,
                "race_id": race_key[0],
                "race_date": race_key[1],
                "ordered_epi_population_count": str(
                    population_count
                ),
                "distinct_epi_count": str(
                    distinct_epi_count
                ),
                "unique_epi_entry_count": str(
                    unique_epi_entry_count
                ),
                "tied_epi_entry_count": str(
                    tied_epi_entry_count
                ),
                "tie_group_count": str(
                    tie_group_count
                ),
                "largest_tie_group_size": str(
                    largest_tie_group_size
                ),
                "top_epi": top_epi_text,
                "second_distinct_epi_available": (
                    second_available
                ),
                "second_distinct_epi": (
                    second_epi_text
                ),
                "top_to_second_epi_gap_available": (
                    gap_available
                ),
                "top_to_second_epi_gap": (
                    gap_text
                ),
                "top_epi_tie_group_size": str(
                    top_epi_tie_group_size
                ),
                "top_epi_tie_status": (
                    top_epi_tie_status
                ),
                "source_ordering_identity_sha256": (
                    source_identity_hash
                ),
                "source_ordering_evidence_sha256": (
                    source_evidence_hash
                ),
                "race_epi_ordering_summary_publication_decision": (
                    PUBLICATION_DECISION
                ),
                "race_epi_ordering_summary_reconciliation_decision": (
                    RECONCILIATION_DECISION
                ),
                "race_epi_ordering_summary_status": (
                    GOVERNED_STATUS
                ),
                "race_epi_ordering_summary_evidence_sha256": (
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
        "EDGEIQ_RACE_EPI_ORDERING_SUMMARY_FACT_V1_BUILD_PASS"
    )
    print(
        f"ordering_rows={len(source_rows)}"
    )
    print(
        f"race_summary_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
