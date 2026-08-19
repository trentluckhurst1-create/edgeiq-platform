from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DISTRIBUTION_PATH = (
    DATA
    / "edgeiq_race_epi_distribution_fact_v1.csv"
)

ORDERING_SUMMARY_PATH = (
    DATA
    / "edgeiq_race_epi_ordering_summary_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_epi_publication_snapshot_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_race_epi_publication_snapshot_fact_v1.0.0"
)

PUBLICATION_DECISION = "RACE_EPI_SNAPSHOT_PUBLISHED"
RECONCILIATION_DECISION = "RACE_EPI_SNAPSHOT_RECONCILED"
GOVERNED_STATUS = "GOVERNED_RACE_EPI_PUBLICATION_SNAPSHOT"

SUMMARY_PUBLICATION = (
    "RACE_EPI_ORDERING_SUMMARY_PUBLISHED"
)
SUMMARY_RECONCILIATION = (
    "RACE_EPI_ORDERING_SUMMARY_RECONCILED"
)
SUMMARY_STATUS = (
    "GOVERNED_RACE_EPI_ORDERING_SUMMARY"
)

DISTRIBUTION_ID_CANDIDATES = [
    "race_epi_distribution_id",
    "race_epi_distribution_fact_id",
    "distribution_id",
]

DISTRIBUTION_EVIDENCE_CANDIDATES = [
    "race_epi_distribution_evidence_sha256",
    "race_epi_distribution_fact_evidence_sha256",
    "distribution_evidence_sha256",
    "evidence_sha256",
]

DISTRIBUTION_POPULATION_CANDIDATES = [
    "eligible_epi_population_count",
    "epi_population_count",
    "race_epi_population_count",
    "distribution_population_count",
    "runner_count",
    "entry_count",
]

SUMMARY_FIELDS = [
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
]

OUTPUT_FIELDS = [
    "race_epi_publication_snapshot_id",
    "race_id",
    "race_date",
    *SUMMARY_FIELDS,
    "distribution_population_field",
    "distribution_population_value",
    "distribution_population_reconciliation_status",
    "source_distribution_id",
    "source_distribution_evidence_sha256",
    "source_distribution_record_json",
    "source_distribution_record_sha256",
    "source_ordering_summary_id",
    "source_ordering_summary_evidence_sha256",
    "race_epi_snapshot_publication_decision",
    "race_epi_snapshot_reconciliation_decision",
    "race_epi_snapshot_status",
    "race_epi_publication_snapshot_evidence_sha256",
    "source_lineage",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_payload(
    parts: Iterable[object],
) -> str:
    payload = "\x1f".join(
        text(part)
        for part in parts
    )

    return sha256_text(payload)


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


def first_existing_field(
    fields: list[str],
    candidates: list[str],
    description: str,
) -> str:
    for candidate in candidates:
        if candidate in fields:
            return candidate

    raise RuntimeError(
        f"Distribution source does not expose a recognised "
        f"{description}. Available fields: {fields}"
    )


def validate_distribution_governance(
    row: dict[str, str],
    race_key: tuple[str, str],
) -> None:
    governance_fields = [
        field
        for field in row
        if (
            field.endswith(
                "_publication_decision"
            )
            or field.endswith(
                "_reconciliation_decision"
            )
            or field.endswith("_status")
        )
    ]

    if not governance_fields:
        raise RuntimeError(
            f"Distribution source exposes no governance "
            f"fields for race {race_key}."
        )

    for field in governance_fields:
        value = text(row.get(field))

        if not value:
            raise RuntimeError(
                f"Blank distribution governance field "
                f"{field} for race {race_key}."
            )

        if field.endswith(
            "_publication_decision"
        ) and "PUBLISHED" not in value:
            raise RuntimeError(
                f"Distribution row is not published for "
                f"race {race_key}: {field}={value}"
            )

        if field.endswith(
            "_reconciliation_decision"
        ) and "RECONCILED" not in value:
            raise RuntimeError(
                f"Distribution row is not reconciled for "
                f"race {race_key}: {field}={value}"
            )

        if field.endswith(
            "_status"
        ) and "GOVERNED" not in value:
            raise RuntimeError(
                f"Distribution row is not governed for "
                f"race {race_key}: {field}={value}"
            )


def main() -> None:
    distribution_fields, distribution_rows = read_csv(
        DISTRIBUTION_PATH
    )

    summary_fields, summary_rows = read_csv(
        ORDERING_SUMMARY_PATH
    )

    if (
        bool(distribution_rows)
        != bool(summary_rows)
    ):
        raise RuntimeError(
            "Distribution and ordering-summary sources "
            "must both be empty or both contain governed rows."
        )

    required_common = {
        "race_id",
        "race_date",
    }

    missing_distribution = sorted(
        required_common
        - set(distribution_fields)
    )

    if missing_distribution:
        raise RuntimeError(
            "Distribution source missing fields: "
            f"{missing_distribution}"
        )

    required_summary = {
        "race_epi_ordering_summary_id",
        "race_id",
        "race_date",
        *SUMMARY_FIELDS,
        "race_epi_ordering_summary_publication_decision",
        "race_epi_ordering_summary_reconciliation_decision",
        "race_epi_ordering_summary_status",
        "race_epi_ordering_summary_evidence_sha256",
    }

    missing_summary = sorted(
        required_summary
        - set(summary_fields)
    )

    if missing_summary:
        raise RuntimeError(
            "Ordering-summary source missing fields: "
            f"{missing_summary}"
        )

    distribution_id_field = first_existing_field(
        distribution_fields,
        DISTRIBUTION_ID_CANDIDATES,
        "distribution identity",
    )

    distribution_evidence_field = first_existing_field(
        distribution_fields,
        DISTRIBUTION_EVIDENCE_CANDIDATES,
        "distribution evidence hash",
    )

    population_field = next(
        (
            candidate
            for candidate in DISTRIBUTION_POPULATION_CANDIDATES
            if candidate in distribution_fields
        ),
        "",
    )

    distribution_by_race: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    for row in distribution_rows:
        race_key = (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )

        if not all(race_key):
            raise RuntimeError(
                "Distribution row has incomplete race identity."
            )

        if race_key in distribution_by_race:
            raise RuntimeError(
                f"Duplicate distribution race: {race_key}"
            )

        distribution_id = text(
            row.get(distribution_id_field)
        )

        distribution_evidence = text(
            row.get(
                distribution_evidence_field
            )
        )

        if not distribution_id:
            raise RuntimeError(
                f"Missing distribution identity for race "
                f"{race_key}."
            )

        if not distribution_evidence:
            raise RuntimeError(
                f"Missing distribution evidence for race "
                f"{race_key}."
            )

        validate_distribution_governance(
            row,
            race_key,
        )

        distribution_by_race[race_key] = row

    summary_by_race: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    for row in summary_rows:
        race_key = (
            text(row.get("race_id")),
            text(row.get("race_date")),
        )

        if not all(race_key):
            raise RuntimeError(
                "Ordering-summary row has incomplete race identity."
            )

        if race_key in summary_by_race:
            raise RuntimeError(
                f"Duplicate ordering-summary race: {race_key}"
            )

        if text(
            row.get(
                "race_epi_ordering_summary_publication_decision"
            )
        ) != SUMMARY_PUBLICATION:
            raise RuntimeError(
                f"Unpublished ordering summary for race "
                f"{race_key}."
            )

        if text(
            row.get(
                "race_epi_ordering_summary_reconciliation_decision"
            )
        ) != SUMMARY_RECONCILIATION:
            raise RuntimeError(
                f"Unreconciled ordering summary for race "
                f"{race_key}."
            )

        if text(
            row.get(
                "race_epi_ordering_summary_status"
            )
        ) != SUMMARY_STATUS:
            raise RuntimeError(
                f"Ungoverned ordering summary for race "
                f"{race_key}."
            )

        summary_by_race[race_key] = row

    if set(distribution_by_race) != set(
        summary_by_race
    ):
        missing_distribution_races = sorted(
            set(summary_by_race)
            - set(distribution_by_race)
        )

        missing_summary_races = sorted(
            set(distribution_by_race)
            - set(summary_by_race)
        )

        raise RuntimeError(
            "Race populations do not reconcile. "
            f"missing_distribution={missing_distribution_races[:20]}, "
            f"missing_summary={missing_summary_races[:20]}"
        )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, str]] = []

    for race_key in sorted(
        summary_by_race,
        key=lambda value: (
            value[1],
            value[0],
        ),
    ):
        distribution = distribution_by_race[
            race_key
        ]

        summary = summary_by_race[
            race_key
        ]

        distribution_id = text(
            distribution.get(
                distribution_id_field
            )
        )

        distribution_evidence = text(
            distribution.get(
                distribution_evidence_field
            )
        )

        summary_id = text(
            summary.get(
                "race_epi_ordering_summary_id"
            )
        )

        summary_evidence = text(
            summary.get(
                "race_epi_ordering_summary_evidence_sha256"
            )
        )

        if not summary_id or not summary_evidence:
            raise RuntimeError(
                f"Incomplete ordering-summary provenance "
                f"for race {race_key}."
            )

        distribution_record = {
            field: text(
                distribution.get(field)
            )
            for field in distribution_fields
        }

        distribution_json = json.dumps(
            distribution_record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        distribution_record_hash = sha256_text(
            distribution_json
        )

        ordered_population = text(
            summary.get(
                "ordered_epi_population_count"
            )
        )

        if population_field:
            distribution_population_value = text(
                distribution.get(
                    population_field
                )
            )

            try:
                distribution_population_int = int(
                    distribution_population_value
                )

                ordered_population_int = int(
                    ordered_population
                )
            except ValueError as error:
                raise RuntimeError(
                    f"Invalid population count for race "
                    f"{race_key}."
                ) from error

            if (
                distribution_population_int
                != ordered_population_int
            ):
                raise RuntimeError(
                    f"Distribution and ordering populations "
                    f"do not reconcile for race {race_key}: "
                    f"{distribution_population_int} != "
                    f"{ordered_population_int}"
                )

            population_status = "RECONCILED"

        else:
            distribution_population_value = ""
            population_status = (
                "NOT_EXPOSED_BY_SOURCE_CONTRACT"
            )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_key[0],
                race_key[1],
                distribution_id,
                summary_id,
                PUBLICATION_DECISION,
            ]
        )

        snapshot_id = (
            "REPS1-"
            f"{identity_hash[:24].upper()}"
        )

        source_lineage = (
            "edgeiq_race_epi_distribution_fact_v1:"
            f"{distribution_id}|"
            "edgeiq_race_epi_ordering_summary_fact_v1:"
            f"{summary_id}"
        )

        evidence_hash = sha256_payload(
            [
                snapshot_id,
                race_key[0],
                race_key[1],
                *[
                    text(summary.get(field))
                    for field in SUMMARY_FIELDS
                ],
                population_field,
                distribution_population_value,
                population_status,
                distribution_id,
                distribution_evidence,
                distribution_record_hash,
                summary_id,
                summary_evidence,
                PUBLICATION_DECISION,
                RECONCILIATION_DECISION,
                GOVERNED_STATUS,
                source_lineage,
            ]
        )

        output_row = {
            "race_epi_publication_snapshot_id": (
                snapshot_id
            ),
            "race_id": race_key[0],
            "race_date": race_key[1],
            **{
                field: text(
                    summary.get(field)
                )
                for field in SUMMARY_FIELDS
            },
            "distribution_population_field": (
                population_field
            ),
            "distribution_population_value": (
                distribution_population_value
            ),
            "distribution_population_reconciliation_status": (
                population_status
            ),
            "source_distribution_id": (
                distribution_id
            ),
            "source_distribution_evidence_sha256": (
                distribution_evidence
            ),
            "source_distribution_record_json": (
                distribution_json
            ),
            "source_distribution_record_sha256": (
                distribution_record_hash
            ),
            "source_ordering_summary_id": (
                summary_id
            ),
            "source_ordering_summary_evidence_sha256": (
                summary_evidence
            ),
            "race_epi_snapshot_publication_decision": (
                PUBLICATION_DECISION
            ),
            "race_epi_snapshot_reconciliation_decision": (
                RECONCILIATION_DECISION
            ),
            "race_epi_snapshot_status": (
                GOVERNED_STATUS
            ),
            "race_epi_publication_snapshot_evidence_sha256": (
                evidence_hash
            ),
            "source_lineage": source_lineage,
            "builder_version": BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": built_at_utc,
        }

        output_rows.append(output_row)

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_BUILD_PASS"
    )
    print(
        f"distribution_rows={len(distribution_rows)}"
    )
    print(
        f"ordering_summary_rows={len(summary_rows)}"
    )
    print(
        f"publication_snapshot_rows={len(output_rows)}"
    )
    print(
        f"distribution_id_field={distribution_id_field}"
    )
    print(
        f"distribution_evidence_field={distribution_evidence_field}"
    )
    print(
        "distribution_population_field="
        f"{population_field or 'NOT_EXPOSED'}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
