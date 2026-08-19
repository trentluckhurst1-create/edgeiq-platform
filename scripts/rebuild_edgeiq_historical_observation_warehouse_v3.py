from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BUILDER_ID = (
    "EDGEIQ_HISTORICAL_OBSERVATION_WAREHOUSE_V3_"
    "GOVERNED_REPLACEMENT_PHASE1A_7_V1"
)

PASS_STATUS = f"{BUILDER_ID}_PASS"
FAIL_STATUS = f"{BUILDER_ID}_FAIL"

EXPECTED_PHYSICAL_ROWS = 879_784
EXPECTED_UNIQUE_RAW_IDENTITIES = 879_695
EXPECTED_DUPLICATE_EXCESS = 89

RAW_IDENTITY_FIELDS = (
    "race_id",
    "provider_runner_id",
)

CANONICAL_IDENTITY_FIELDS = (
    "race_id",
    "horse_id",
)

REQUIRED_SOURCE_FIELDS = (
    "performance_id",
    "race_id",
    "meeting_id",
    "horse_id",
    "source_evidence_id",
    "source_row_number",
    "provider_race_id",
    "provider_runner_id",
    "race_date",
    "state",
    "track",
    "race_number",
    "horse_name",
    "identity_method",
    "identity_quality_state",
    "identity_version",
    "evidence_version",
    "generated_at",
    "legacy_performance_id",
    "performance_natural_key_version",
    "rekeyed_at",
)

OUTPUT_FIELDS = (
    "historical_observation_id",
    "raw_observation_key",
    "raw_observation_duplicate_ordinal",
    "raw_observation_duplicate_count",
    "performance_id",
    "race_id",
    "meeting_id",
    "horse_id",
    "source_evidence_id",
    "source_row_number",
    "provider_race_id",
    "provider_runner_id",
    "race_date",
    "state",
    "track",
    "race_number",
    "horse_name",
    "identity_method",
    "identity_quality_state",
    "identity_version",
    "evidence_version",
    "generated_at",
    "legacy_performance_id",
    "performance_natural_key_version",
    "rekeyed_at",
)

ROOT = Path.cwd().absolute()

RAW_AUTHORITY = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
    / "eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e"
    / "canonical_performance_evidence.csv"
)

AUTHORITY_CONTRACT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "historical-observation-v3-raw-authority-lock"
    / "edgeiq_historical_observation_v3_"
      "physical_authority_contract_v1.json"
)

WAREHOUSE_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-observation-warehouse-v3"
)

LATEST_POINTER = (
    WAREHOUSE_ROOT
    / "latest.json"
)

EXPECTED_AUTHORITY_DECISION = (
    "LOCK_CANONICAL_PERFORMANCE_EVIDENCE_"
    "AS_PHYSICAL_AUTHORITY"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def normalise_cell(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def stable_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8 * 1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def raw_key(
    race_id: str,
    provider_runner_id: str,
) -> str:
    return (
        f"race_id={race_id}"
        f"|provider_runner_id={provider_runner_id}"
    )


def historical_observation_id(
    race_id: str,
    provider_runner_id: str,
    duplicate_ordinal: int,
) -> str:
    material = (
        f"edgeiq-historical-observation-v3"
        f"|race_id={race_id}"
        f"|provider_runner_id={provider_runner_id}"
        f"|duplicate_ordinal={duplicate_ordinal}"
    )

    return (
        "eho3_"
        + sha256_text(material)[:32]
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def validate_authority_contract() -> dict[str, Any]:
    if not AUTHORITY_CONTRACT.exists():
        raise RuntimeError(
            "Locked physical authority contract is missing: "
            f"{relative(AUTHORITY_CONTRACT)}"
        )

    contract = load_json(
        AUTHORITY_CONTRACT
    )

    checks = {
        "status_pass": str(
            contract.get("status", "")
        ).endswith("_PASS"),
        "decision_locked": (
            contract.get("decision")
            == EXPECTED_AUTHORITY_DECISION
        ),
        "selected_authority_matches": (
            contract.get(
                "selected_physical_authority"
            )
            == relative(RAW_AUTHORITY)
        ),
        "raw_identity_matches": (
            contract.get(
                "selected_raw_identity",
                {},
            ).get("fields")
            == list(RAW_IDENTITY_FIELDS)
        ),
        "physical_rows_match": (
            contract.get(
                "population_contract",
                {},
            ).get("physical_rows")
            == EXPECTED_PHYSICAL_ROWS
        ),
        "unique_identity_match": (
            contract.get(
                "population_contract",
                {},
            ).get("unique_raw_identities")
            == EXPECTED_UNIQUE_RAW_IDENTITIES
        ),
        "duplicate_excess_match": (
            contract.get(
                "population_contract",
                {},
            ).get("duplicate_excess")
            == EXPECTED_DUPLICATE_EXCESS
        ),
        "warehouse_authorised": (
            contract.get(
                "warehouse_build_authorised"
            )
            is True
        ),
    }

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    if failed:
        raise RuntimeError(
            "Physical authority contract validation failed: "
            + ", ".join(failed)
        )

    return {
        "contract": contract,
        "checks": checks,
    }


def inspect_source_header() -> list[str]:
    if not RAW_AUTHORITY.exists():
        raise FileNotFoundError(
            relative(RAW_AUTHORITY)
        )

    with RAW_AUTHORITY.open(
        "r",
        encoding="utf-8-sig",
        errors="strict",
        newline="",
    ) as handle:
        header = next(
            csv.reader(handle),
            [],
        )

    missing = [
        field
        for field in REQUIRED_SOURCE_FIELDS
        if field not in header
    ]

    if missing:
        raise RuntimeError(
            "Raw authority schema is missing required fields: "
            + ", ".join(missing)
        )

    return header


def create_identity_index(
    database_path: Path,
) -> dict[str, Any]:
    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        "PRAGMA journal_mode = OFF"
    )
    connection.execute(
        "PRAGMA synchronous = OFF"
    )
    connection.execute(
        "PRAGMA temp_store = FILE"
    )
    connection.execute(
        "PRAGMA cache_size = -200000"
    )

    connection.execute(
        """
        CREATE TABLE identity_population (
            source_sequence INTEGER NOT NULL,
            race_id TEXT NOT NULL,
            provider_runner_id TEXT NOT NULL
        )
        """
    )

    insert_sql = (
        "INSERT INTO identity_population "
        "(source_sequence, race_id, provider_runner_id) "
        "VALUES (?, ?, ?)"
    )

    physical_rows = 0
    blank_race_id = 0
    blank_provider_runner_id = 0
    batch: list[tuple[int, str, str]] = []

    with RAW_AUTHORITY.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for source_sequence, row in enumerate(
            reader,
            start=1,
        ):
            race_id = normalise_cell(
                row.get("race_id")
            )

            provider_runner_id = normalise_cell(
                row.get("provider_runner_id")
            )

            if not race_id:
                blank_race_id += 1

            if not provider_runner_id:
                blank_provider_runner_id += 1

            batch.append(
                (
                    source_sequence,
                    race_id,
                    provider_runner_id,
                )
            )

            physical_rows += 1

            if len(batch) >= 20_000:
                connection.executemany(
                    insert_sql,
                    batch,
                )
                connection.commit()
                batch.clear()

            if physical_rows % 250_000 == 0:
                print(
                    "  indexed "
                    f"{physical_rows:,} source rows",
                    flush=True,
                )

        if batch:
            connection.executemany(
                insert_sql,
                batch,
            )
            connection.commit()

    unique_raw_identities = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT race_id, provider_runner_id
            FROM identity_population
            GROUP BY race_id, provider_runner_id
        )
        """
    ).fetchone()[0]

    duplicate_excess = (
        physical_rows
        - unique_raw_identities
    )

    duplicate_identity_groups = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT race_id, provider_runner_id
            FROM identity_population
            GROUP BY race_id, provider_runner_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    maximum_duplicate_count = connection.execute(
        """
        SELECT MAX(identity_count)
        FROM (
            SELECT COUNT(*) AS identity_count
            FROM identity_population
            GROUP BY race_id, provider_runner_id
        )
        """
    ).fetchone()[0]

    connection.execute(
        """
        CREATE INDEX idx_identity_population_key
        ON identity_population (
            race_id,
            provider_runner_id,
            source_sequence
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE identity_counts AS
        SELECT
            race_id,
            provider_runner_id,
            COUNT(*) AS duplicate_count
        FROM identity_population
        GROUP BY
            race_id,
            provider_runner_id
        """
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX idx_identity_counts_key
        ON identity_counts (
            race_id,
            provider_runner_id
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE identity_ordinals AS
        SELECT
            source_sequence,
            race_id,
            provider_runner_id,
            ROW_NUMBER() OVER (
                PARTITION BY
                    race_id,
                    provider_runner_id
                ORDER BY
                    source_sequence
            ) AS duplicate_ordinal
        FROM identity_population
        """
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX idx_identity_ordinals_sequence
        ON identity_ordinals (
            source_sequence
        )
        """
    )

    connection.commit()
    connection.close()

    return {
        "physical_rows": physical_rows,
        "unique_raw_identities": (
            unique_raw_identities
        ),
        "duplicate_excess": (
            duplicate_excess
        ),
        "duplicate_identity_groups": (
            duplicate_identity_groups
        ),
        "maximum_duplicate_count": (
            maximum_duplicate_count
        ),
        "blank_race_id": blank_race_id,
        "blank_provider_runner_id": (
            blank_provider_runner_id
        ),
    }


def validate_source_population(
    population: dict[str, Any],
) -> None:
    checks = {
        "physical_rows": (
            population["physical_rows"]
            == EXPECTED_PHYSICAL_ROWS
        ),
        "unique_raw_identities": (
            population[
                "unique_raw_identities"
            ]
            == EXPECTED_UNIQUE_RAW_IDENTITIES
        ),
        "duplicate_excess": (
            population[
                "duplicate_excess"
            ]
            == EXPECTED_DUPLICATE_EXCESS
        ),
        "blank_race_id": (
            population["blank_race_id"]
            == 0
        ),
        "blank_provider_runner_id": (
            population[
                "blank_provider_runner_id"
            ]
            == 0
        ),
    }

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    if failed:
        raise RuntimeError(
            "Raw authority population contract failed: "
            + ", ".join(failed)
            + "; population="
            + json.dumps(
                population,
                sort_keys=True,
            )
        )


def create_output_database(
    database_path: Path,
) -> sqlite3.Connection:
    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        "PRAGMA journal_mode = OFF"
    )
    connection.execute(
        "PRAGMA synchronous = OFF"
    )
    connection.execute(
        "PRAGMA temp_store = FILE"
    )
    connection.execute(
        "PRAGMA cache_size = -200000"
    )

    connection.execute(
        """
        CREATE TABLE historical_observation_v3 (
            source_sequence INTEGER NOT NULL,
            historical_observation_id TEXT NOT NULL,
            raw_observation_key TEXT NOT NULL,
            raw_observation_duplicate_ordinal INTEGER NOT NULL,
            raw_observation_duplicate_count INTEGER NOT NULL,
            performance_id TEXT NOT NULL,
            race_id TEXT NOT NULL,
            meeting_id TEXT NOT NULL,
            horse_id TEXT NOT NULL,
            source_evidence_id TEXT NOT NULL,
            source_row_number TEXT NOT NULL,
            provider_race_id TEXT NOT NULL,
            provider_runner_id TEXT NOT NULL,
            race_date TEXT NOT NULL,
            state TEXT NOT NULL,
            track TEXT NOT NULL,
            race_number TEXT NOT NULL,
            horse_name TEXT NOT NULL,
            identity_method TEXT NOT NULL,
            identity_quality_state TEXT NOT NULL,
            identity_version TEXT NOT NULL,
            evidence_version TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            legacy_performance_id TEXT NOT NULL,
            performance_natural_key_version TEXT NOT NULL,
            rekeyed_at TEXT NOT NULL
        )
        """
    )

    return connection


def build_warehouse_csv(
    identity_database_path: Path,
    output_database_path: Path,
    output_csv: Path,
) -> dict[str, Any]:
    identity_connection = sqlite3.connect(
        identity_database_path
    )

    output_connection = create_output_database(
        output_database_path
    )

    ordinal_cursor = identity_connection.cursor()

    insert_sql = """
        INSERT INTO historical_observation_v3 (
            source_sequence,
            historical_observation_id,
            raw_observation_key,
            raw_observation_duplicate_ordinal,
            raw_observation_duplicate_count,
            performance_id,
            race_id,
            meeting_id,
            horse_id,
            source_evidence_id,
            source_row_number,
            provider_race_id,
            provider_runner_id,
            race_date,
            state,
            track,
            race_number,
            horse_name,
            identity_method,
            identity_quality_state,
            identity_version,
            evidence_version,
            generated_at,
            legacy_performance_id,
            performance_natural_key_version,
            rekeyed_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """

    built_rows = 0
    batch: list[tuple[Any, ...]] = []

    with RAW_AUTHORITY.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for source_sequence, row in enumerate(
            reader,
            start=1,
        ):
            race_id = normalise_cell(
                row.get("race_id")
            )

            provider_runner_id = normalise_cell(
                row.get("provider_runner_id")
            )

            ordinal_row = ordinal_cursor.execute(
                """
                SELECT
                    o.duplicate_ordinal,
                    c.duplicate_count
                FROM identity_ordinals AS o
                JOIN identity_counts AS c
                  ON c.race_id = o.race_id
                 AND c.provider_runner_id =
                     o.provider_runner_id
                WHERE o.source_sequence = ?
                """,
                (source_sequence,),
            ).fetchone()

            if ordinal_row is None:
                raise RuntimeError(
                    "Identity ordinal missing for "
                    f"source_sequence={source_sequence}"
                )

            duplicate_ordinal = int(
                ordinal_row[0]
            )

            duplicate_count = int(
                ordinal_row[1]
            )

            observation_key = raw_key(
                race_id,
                provider_runner_id,
            )

            observation_id = (
                historical_observation_id(
                    race_id,
                    provider_runner_id,
                    duplicate_ordinal,
                )
            )

            batch.append(
                (
                    source_sequence,
                    observation_id,
                    observation_key,
                    duplicate_ordinal,
                    duplicate_count,
                    normalise_cell(
                        row.get("performance_id")
                    ),
                    race_id,
                    normalise_cell(
                        row.get("meeting_id")
                    ),
                    normalise_cell(
                        row.get("horse_id")
                    ),
                    normalise_cell(
                        row.get("source_evidence_id")
                    ),
                    normalise_cell(
                        row.get("source_row_number")
                    ),
                    normalise_cell(
                        row.get("provider_race_id")
                    ),
                    provider_runner_id,
                    normalise_cell(
                        row.get("race_date")
                    ),
                    normalise_cell(
                        row.get("state")
                    ),
                    normalise_cell(
                        row.get("track")
                    ),
                    normalise_cell(
                        row.get("race_number")
                    ),
                    normalise_cell(
                        row.get("horse_name")
                    ),
                    normalise_cell(
                        row.get("identity_method")
                    ),
                    normalise_cell(
                        row.get("identity_quality_state")
                    ),
                    normalise_cell(
                        row.get("identity_version")
                    ),
                    normalise_cell(
                        row.get("evidence_version")
                    ),
                    normalise_cell(
                        row.get("generated_at")
                    ),
                    normalise_cell(
                        row.get("legacy_performance_id")
                    ),
                    normalise_cell(
                        row.get(
                            "performance_natural_key_version"
                        )
                    ),
                    normalise_cell(
                        row.get("rekeyed_at")
                    ),
                )
            )

            built_rows += 1

            if len(batch) >= 20_000:
                output_connection.executemany(
                    insert_sql,
                    batch,
                )
                output_connection.commit()
                batch.clear()

            if built_rows % 250_000 == 0:
                print(
                    "  constructed "
                    f"{built_rows:,} warehouse rows",
                    flush=True,
                )

        if batch:
            output_connection.executemany(
                insert_sql,
                batch,
            )
            output_connection.commit()

    output_connection.execute(
        """
        CREATE UNIQUE INDEX idx_historical_observation_v3_id
        ON historical_observation_v3 (
            historical_observation_id
        )
        """
    )

    output_connection.execute(
        """
        CREATE INDEX idx_historical_observation_v3_raw_key
        ON historical_observation_v3 (
            race_id,
            provider_runner_id,
            raw_observation_duplicate_ordinal
        )
        """
    )

    output_connection.execute(
        """
        CREATE INDEX idx_historical_observation_v3_canonical
        ON historical_observation_v3 (
            race_id,
            horse_id
        )
        """
    )

    output_connection.commit()

    duplicate_rows = output_connection.execute(
        """
        SELECT COUNT(*)
        FROM historical_observation_v3
        WHERE raw_observation_duplicate_count > 1
        """
    ).fetchone()[0]

    output_connection.close()
    identity_connection.close()

    export_warehouse_csv(
        output_database_path,
        output_csv,
    )

    return {
        "built_rows": built_rows,
        "rows_in_duplicate_groups": (
            duplicate_rows
        ),
    }


def export_warehouse_csv(
    output_database_path: Path,
    output_csv: Path,
) -> None:
    connection = sqlite3.connect(
        output_database_path
    )

    query_fields = ", ".join(
        f'"{field}"'
        for field in OUTPUT_FIELDS
    )

    cursor = connection.execute(
        f"""
        SELECT {query_fields}
        FROM historical_observation_v3
        ORDER BY
            race_id,
            provider_runner_id,
            raw_observation_duplicate_ordinal,
            source_sequence
        """
    )

    with output_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(
            handle,
            lineterminator="\n",
        )

        writer.writerow(
            OUTPUT_FIELDS
        )

        exported_rows = 0

        while True:
            rows = cursor.fetchmany(
                20_000
            )

            if not rows:
                break

            writer.writerows(rows)
            exported_rows += len(rows)

            if exported_rows % 250_000 == 0:
                print(
                    "  exported "
                    f"{exported_rows:,} warehouse rows",
                    flush=True,
                )

    connection.close()


def audit_output_database(
    output_database_path: Path,
    output_csv: Path,
) -> dict[str, Any]:
    connection = sqlite3.connect(
        output_database_path
    )

    physical_rows = connection.execute(
        """
        SELECT COUNT(*)
        FROM historical_observation_v3
        """
    ).fetchone()[0]

    unique_raw_identities = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT race_id, provider_runner_id
            FROM historical_observation_v3
            GROUP BY
                race_id,
                provider_runner_id
        )
        """
    ).fetchone()[0]

    duplicate_excess = (
        physical_rows
        - unique_raw_identities
    )

    unique_historical_observation_ids = (
        connection.execute(
            """
            SELECT COUNT(
                DISTINCT historical_observation_id
            )
            FROM historical_observation_v3
            """
        ).fetchone()[0]
    )

    invalid_ordinals = connection.execute(
        """
        SELECT COUNT(*)
        FROM historical_observation_v3
        WHERE raw_observation_duplicate_ordinal < 1
           OR raw_observation_duplicate_ordinal
              > raw_observation_duplicate_count
        """
    ).fetchone()[0]

    blank_raw_identity = connection.execute(
        """
        SELECT COUNT(*)
        FROM historical_observation_v3
        WHERE TRIM(race_id) = ''
           OR TRIM(provider_runner_id) = ''
        """
    ).fetchone()[0]

    blank_lineage = connection.execute(
        """
        SELECT COUNT(*)
        FROM historical_observation_v3
        WHERE TRIM(source_row_number) = ''
           OR TRIM(source_evidence_id) = ''
        """
    ).fetchone()[0]

    duplicate_ordinal_contract_failures = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    race_id,
                    provider_runner_id,
                    COUNT(*) AS physical_count,
                    MAX(
                        raw_observation_duplicate_count
                    ) AS declared_count,
                    MIN(
                        raw_observation_duplicate_ordinal
                    ) AS minimum_ordinal,
                    MAX(
                        raw_observation_duplicate_ordinal
                    ) AS maximum_ordinal,
                    COUNT(
                        DISTINCT
                        raw_observation_duplicate_ordinal
                    ) AS distinct_ordinals
                FROM historical_observation_v3
                GROUP BY
                    race_id,
                    provider_runner_id
                HAVING
                    physical_count <> declared_count
                    OR minimum_ordinal <> 1
                    OR maximum_ordinal <> declared_count
                    OR distinct_ordinals <> declared_count
            )
            """
        ).fetchone()[0]
    )

    connection.close()

    with output_csv.open(
        "r",
        encoding="utf-8-sig",
        errors="strict",
        newline="",
    ) as handle:
        reader = csv.reader(handle)
        csv_header = next(reader, [])
        csv_rows = sum(1 for _ in reader)

    checks = {
        "physical_rows": (
            physical_rows
            == EXPECTED_PHYSICAL_ROWS
        ),
        "unique_raw_identities": (
            unique_raw_identities
            == EXPECTED_UNIQUE_RAW_IDENTITIES
        ),
        "duplicate_excess": (
            duplicate_excess
            == EXPECTED_DUPLICATE_EXCESS
        ),
        "historical_observation_id_unique": (
            unique_historical_observation_ids
            == EXPECTED_PHYSICAL_ROWS
        ),
        "invalid_ordinals_zero": (
            invalid_ordinals == 0
        ),
        "blank_raw_identity_zero": (
            blank_raw_identity == 0
        ),
        "blank_lineage_zero": (
            blank_lineage == 0
        ),
        "duplicate_ordinal_contract": (
            duplicate_ordinal_contract_failures
            == 0
        ),
        "csv_header_contract": (
            csv_header == list(OUTPUT_FIELDS)
        ),
        "csv_population_contract": (
            csv_rows
            == EXPECTED_PHYSICAL_ROWS
        ),
    }

    failed = [
        name
        for name, passed in checks.items()
        if not passed
    ]

    return {
        "status": (
            "PASS"
            if not failed
            else "FAIL"
        ),
        "checks": checks,
        "failed_checks": failed,
        "physical_rows": physical_rows,
        "unique_raw_identities": (
            unique_raw_identities
        ),
        "duplicate_excess": (
            duplicate_excess
        ),
        "unique_historical_observation_ids": (
            unique_historical_observation_ids
        ),
        "invalid_ordinals": (
            invalid_ordinals
        ),
        "blank_raw_identity": (
            blank_raw_identity
        ),
        "blank_lineage": (
            blank_lineage
        ),
        "duplicate_ordinal_contract_failures": (
            duplicate_ordinal_contract_failures
        ),
        "csv_rows": csv_rows,
        "csv_header": csv_header,
    }


def write_governance_files(
    snapshot_root: Path,
    authority_validation: dict[str, Any],
    source_header: list[str],
    source_population: dict[str, Any],
    build_result: dict[str, Any],
    audit: dict[str, Any],
    warehouse_csv: Path,
    warehouse_sqlite: Path,
) -> dict[str, Path]:
    schema_contract_path = (
        snapshot_root
        / "historical_observation_warehouse_v3_"
          "schema_contract.json"
    )

    lineage_contract_path = (
        snapshot_root
        / "historical_observation_warehouse_v3_"
          "lineage_contract.json"
    )

    population_contract_path = (
        snapshot_root
        / "historical_observation_warehouse_v3_"
          "population_contract.json"
    )

    audit_json_path = (
        snapshot_root
        / "EDGEIQ_HISTORICAL_OBSERVATION_"
          "WAREHOUSE_V3_AUDIT.json"
    )

    audit_md_path = (
        snapshot_root
        / "EDGEIQ_HISTORICAL_OBSERVATION_"
          "WAREHOUSE_V3_AUDIT.md"
    )

    build_report_json_path = (
        snapshot_root
        / "EDGEIQ_HISTORICAL_OBSERVATION_"
          "WAREHOUSE_V3_BUILD_REPORT.json"
    )

    build_report_md_path = (
        snapshot_root
        / "EDGEIQ_HISTORICAL_OBSERVATION_"
          "WAREHOUSE_V3_BUILD_REPORT.md"
    )

    manifest_path = (
        snapshot_root
        / "manifest.json"
    )

    schema_contract = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_"
            "WAREHOUSE_V3_SCHEMA_CONTRACT_V1"
        ),
        "warehouse_version": "v3",
        "source_fields": source_header,
        "output_fields": list(
            OUTPUT_FIELDS
        ),
        "raw_identity_fields": list(
            RAW_IDENTITY_FIELDS
        ),
        "canonical_identity_fields": list(
            CANONICAL_IDENTITY_FIELDS
        ),
        "deterministic_sort": [
            "race_id",
            "provider_runner_id",
            "raw_observation_duplicate_ordinal",
            "source_sequence",
        ],
        "generated_fields": {
            "historical_observation_id": (
                "SHA256-derived deterministic ID from "
                "race_id, provider_runner_id and "
                "duplicate ordinal"
            ),
            "raw_observation_key": (
                "race_id + provider_runner_id"
            ),
            "raw_observation_duplicate_ordinal": (
                "1-based ordinal within each raw "
                "identity group, ordered by physical "
                "source sequence"
            ),
            "raw_observation_duplicate_count": (
                "physical row count within each raw "
                "identity group"
            ),
        },
    }

    lineage_contract = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_"
            "WAREHOUSE_V3_LINEAGE_CONTRACT_V1"
        ),
        "physical_authority": relative(
            RAW_AUTHORITY
        ),
        "authority_contract": relative(
            AUTHORITY_CONTRACT
        ),
        "authority_decision": (
            EXPECTED_AUTHORITY_DECISION
        ),
        "source_class": (
            "CANONICAL_PERFORMANCE_EVIDENCE"
        ),
        "forbidden_source_classes": [
            "CORRECTED_PERFORMANCE_FACTS",
            "STANDARD_TIME_FACTS",
            "EPI_FACTS",
            "UI_FEEDS",
            "MANUAL_DATA",
            "FABRICATED_DATA",
        ],
        "lineage_fields_preserved": [
            "source_evidence_id",
            "source_row_number",
            "provider_race_id",
            "provider_runner_id",
            "legacy_performance_id",
        ],
        "authority_contract_checks": (
            authority_validation["checks"]
        ),
    }

    population_contract = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_"
            "WAREHOUSE_V3_POPULATION_CONTRACT_V1"
        ),
        "physical_rows": (
            EXPECTED_PHYSICAL_ROWS
        ),
        "unique_raw_identities": (
            EXPECTED_UNIQUE_RAW_IDENTITIES
        ),
        "duplicate_excess": (
            EXPECTED_DUPLICATE_EXCESS
        ),
        "actual": {
            "physical_rows": (
                audit["physical_rows"]
            ),
            "unique_raw_identities": (
                audit[
                    "unique_raw_identities"
                ]
            ),
            "duplicate_excess": (
                audit["duplicate_excess"]
            ),
        },
    }

    audit_payload = {
        "audit_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_"
            "WAREHOUSE_V3_AUDIT_V1"
        ),
        "status": audit["status"],
        "generated_at_utc": now_utc(),
        "warehouse_csv": (
            warehouse_csv.name
        ),
        "warehouse_sqlite": (
            warehouse_sqlite.name
        ),
        **audit,
    }

    build_payload = {
        "builder_id": BUILDER_ID,
        "status": (
            PASS_STATUS
            if audit["status"] == "PASS"
            else FAIL_STATUS
        ),
        "generated_at_utc": now_utc(),
        "physical_authority": relative(
            RAW_AUTHORITY
        ),
        "authority_contract": relative(
            AUTHORITY_CONTRACT
        ),
        "raw_identity": (
            "race_id + provider_runner_id"
        ),
        "canonical_identity": (
            "race_id + horse_id"
        ),
        "source_population": (
            source_population
        ),
        "build_result": (
            build_result
        ),
        "audit": audit,
        "safety": {
            "existing_v2_modified": False,
            "corrected_facts_used": False,
            "thresholds_reduced": False,
            "rows_fabricated": False,
            "source_rows_discarded": False,
        },
    }

    schema_contract_path.write_bytes(
        stable_json_bytes(
            schema_contract
        )
    )

    lineage_contract_path.write_bytes(
        stable_json_bytes(
            lineage_contract
        )
    )

    population_contract_path.write_bytes(
        stable_json_bytes(
            population_contract
        )
    )

    audit_json_path.write_bytes(
        stable_json_bytes(
            audit_payload
        )
    )

    build_report_json_path.write_bytes(
        stable_json_bytes(
            build_payload
        )
    )

    check_lines = [
        "| Check | Result |",
        "|---|---:|",
    ]

    for name, passed in sorted(
        audit["checks"].items()
    ):
        check_lines.append(
            f"| `{name}` | "
            f"**{'PASS' if passed else 'FAIL'}** |"
        )

    audit_md_path.write_text(
        "\n".join(
            [
                (
                    "# EDGEIQ Historical Observation "
                    "Warehouse V3 Audit"
                ),
                "",
                (
                    f"**Status:** "
                    f"`{audit['status']}`"
                ),
                "",
                "## Population",
                "",
                (
                    f"- Physical rows: "
                    f"**{audit['physical_rows']:,}**"
                ),
                (
                    f"- Unique raw identities: "
                    f"**{audit['unique_raw_identities']:,}**"
                ),
                (
                    f"- Duplicate excess: "
                    f"**{audit['duplicate_excess']:,}**"
                ),
                "",
                "## Checks",
                "",
                *check_lines,
                "",
                "## Authority",
                "",
                f"`{relative(RAW_AUTHORITY)}`",
                "",
                "## Raw identity",
                "",
                "`race_id + provider_runner_id`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    build_report_md_path.write_text(
        "\n".join(
            [
                (
                    "# EDGEIQ Historical Observation "
                    "Warehouse V3 Build Report"
                ),
                "",
                (
                    f"**Status:** "
                    f"`{build_payload['status']}`"
                ),
                "",
                (
                    "**Physical authority:** "
                    f"`{relative(RAW_AUTHORITY)}`"
                ),
                "",
                (
                    "**Raw observation identity:** "
                    "`race_id + provider_runner_id`"
                ),
                "",
                (
                    "**Canonical horse identity:** "
                    "`race_id + horse_id`"
                ),
                "",
                "## Governed population",
                "",
                (
                    f"- Physical rows: "
                    f"**{audit['physical_rows']:,}**"
                ),
                (
                    f"- Unique raw identities: "
                    f"**{audit['unique_raw_identities']:,}**"
                ),
                (
                    f"- Duplicate excess: "
                    f"**{audit['duplicate_excess']:,}**"
                ),
                "",
                "## Safety",
                "",
                "- Existing V2 was not modified.",
                (
                    "- Corrected performance facts were "
                    "not used as source authority."
                ),
                "- No thresholds were reduced.",
                "- No rows were fabricated.",
                "- No physical source rows were discarded.",
                "",
                "## Audit",
                "",
                (
                    f"Warehouse audit: "
                    f"**{audit['status']}**"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest_files = [
        warehouse_csv,
        warehouse_sqlite,
        schema_contract_path,
        lineage_contract_path,
        population_contract_path,
        audit_json_path,
        audit_md_path,
        build_report_json_path,
        build_report_md_path,
    ]

    manifest = {
        "manifest_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_"
            "WAREHOUSE_V3_MANIFEST_V1"
        ),
        "builder_id": BUILDER_ID,
        "status": (
            PASS_STATUS
            if audit["status"] == "PASS"
            else FAIL_STATUS
        ),
        "generated_at_utc": now_utc(),
        "files": [
            {
                "name": path.name,
                "size_bytes": (
                    path.stat().st_size
                ),
                "sha256": sha256_file(
                    path
                ),
            }
            for path in manifest_files
        ],
    }

    manifest_path.write_bytes(
        stable_json_bytes(
            manifest
        )
    )

    return {
        "schema_contract": (
            schema_contract_path
        ),
        "lineage_contract": (
            lineage_contract_path
        ),
        "population_contract": (
            population_contract_path
        ),
        "audit_json": audit_json_path,
        "audit_md": audit_md_path,
        "build_report_json": (
            build_report_json_path
        ),
        "build_report_md": (
            build_report_md_path
        ),
        "manifest": manifest_path,
    }


def snapshot_identity(
    warehouse_csv: Path,
    schema_contract: Path,
    population_contract: Path,
) -> str:
    digest = hashlib.sha256()

    for path in (
        warehouse_csv,
        schema_contract,
        population_contract,
    ):
        digest.update(
            sha256_file(path).encode(
                "ascii"
            )
        )

    return digest.hexdigest()[:24]


def publish_snapshot(
    temporary_snapshot_root: Path,
    governance_paths: dict[str, Path],
) -> Path:
    snapshot_id = snapshot_identity(
        temporary_snapshot_root
        / "historical_observation_warehouse_v3.csv",
        governance_paths[
            "schema_contract"
        ],
        governance_paths[
            "population_contract"
        ],
    )

    final_snapshot_root = (
        WAREHOUSE_ROOT
        / f"eiq_historical_observation_v3_{snapshot_id}"
    )

    if final_snapshot_root.exists():
        # The snapshot identity is derived only from deterministic
        # warehouse and contract content. Timestamped reports and the
        # manifest may legitimately differ between equivalent reruns,
        # so they must not determine idempotent equivalence.
        deterministic_files = (
            "historical_observation_warehouse_v3.csv",
            "historical_observation_warehouse_v3_schema_contract.json",
            "historical_observation_warehouse_v3_lineage_contract.json",
            "historical_observation_warehouse_v3_population_contract.json",
        )

        comparison_failures = []

        for filename in deterministic_files:
            existing_file = (
                final_snapshot_root
                / filename
            )

            candidate_file = (
                temporary_snapshot_root
                / filename
            )

            if (
                not existing_file.exists()
                or not candidate_file.exists()
            ):
                comparison_failures.append(
                    f"{filename}:missing"
                )
                continue

            if (
                sha256_file(existing_file)
                != sha256_file(candidate_file)
            ):
                comparison_failures.append(
                    f"{filename}:hash_mismatch"
                )

        if not comparison_failures:
            shutil.rmtree(
                temporary_snapshot_root
            )

            return final_snapshot_root

        raise RuntimeError(
            "Deterministic snapshot path already exists "
            "with different governed content: "
            f"{relative(final_snapshot_root)}; "
            + ", ".join(comparison_failures)
        )

    os.replace(
        temporary_snapshot_root,
        final_snapshot_root,
    )

    latest_payload = {
        "warehouse_version": "v3",
        "snapshot_id": snapshot_id,
        "snapshot_path": relative(
            final_snapshot_root
        ),
        "warehouse_csv": relative(
            final_snapshot_root
            / "historical_observation_warehouse_v3.csv"
        ),
        "warehouse_sqlite": relative(
            final_snapshot_root
            / "historical_observation_warehouse_v3.sqlite"
        ),
        "manifest": relative(
            final_snapshot_root
            / "manifest.json"
        ),
        "status": PASS_STATUS,
    }

    WAREHOUSE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_latest = (
        WAREHOUSE_ROOT
        / ".latest.json.tmp"
    )

    temporary_latest.write_bytes(
        stable_json_bytes(
            latest_payload
        )
    )

    os.replace(
        temporary_latest,
        LATEST_POINTER,
    )

    return final_snapshot_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the governed EDGEIQ Historical "
            "Observation Warehouse V3 replacement."
        )
    )

    parser.add_argument(
        "--audit-only",
        action="store_true",
        help=(
            "Audit the latest published V3 warehouse "
            "without rebuilding it."
        ),
    )

    args = parser.parse_args()

    print(BUILDER_ID)
    print("=" * len(BUILDER_ID))
    print()

    if args.audit_only:
        return audit_latest()

    authority_validation = (
        validate_authority_contract()
    )

    source_header = (
        inspect_source_header()
    )

    WAREHOUSE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_parent = Path(
        tempfile.mkdtemp(
            prefix=(
                ".edgeiq_historical_observation_v3_"
            ),
            dir=WAREHOUSE_ROOT,
        )
    )

    temporary_snapshot_root = (
        temporary_parent
        / "snapshot"
    )

    temporary_snapshot_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    identity_database_path = (
        temporary_parent
        / "identity_index.sqlite"
    )

    output_database_path = (
        temporary_snapshot_root
        / "historical_observation_warehouse_v3.sqlite"
    )

    output_csv_path = (
        temporary_snapshot_root
        / "historical_observation_warehouse_v3.csv"
    )

    try:
        print(
            "Indexing locked raw identity population...",
            flush=True,
        )

        source_population = (
            create_identity_index(
                identity_database_path
            )
        )

        validate_source_population(
            source_population
        )

        print()
        print(
            "Constructing governed V3 warehouse...",
            flush=True,
        )

        build_result = build_warehouse_csv(
            identity_database_path,
            output_database_path,
            output_csv_path,
        )

        print()
        print(
            "Auditing temporary V3 warehouse...",
            flush=True,
        )

        audit = audit_output_database(
            output_database_path,
            output_csv_path,
        )

        if audit["status"] != "PASS":
            raise RuntimeError(
                "Temporary V3 warehouse audit failed: "
                + ", ".join(
                    audit["failed_checks"]
                )
            )

        governance_paths = (
            write_governance_files(
                temporary_snapshot_root,
                authority_validation,
                source_header,
                source_population,
                build_result,
                audit,
                output_csv_path,
                output_database_path,
            )
        )

        final_snapshot_root = (
            publish_snapshot(
                temporary_snapshot_root,
                governance_paths,
            )
        )

        if temporary_parent.exists():
            shutil.rmtree(
                temporary_parent
            )

        print()
        print(f"STATUS: {PASS_STATUS}")
        print(
            "DECISION: "
            "PUBLISH_GOVERNED_HISTORICAL_"
            "OBSERVATION_WAREHOUSE_V3"
        )
        print(
            "PHYSICAL AUTHORITY: "
            f"{relative(RAW_AUTHORITY)}"
        )
        print(
            "RAW IDENTITY: "
            "race_id + provider_runner_id"
        )
        print(
            "CANONICAL IDENTITY: "
            "race_id + horse_id"
        )
        print(
            "PHYSICAL ROWS: "
            f"{audit['physical_rows']:,}"
        )
        print(
            "UNIQUE RAW IDENTITIES: "
            f"{audit['unique_raw_identities']:,}"
        )
        print(
            "DUPLICATE EXCESS: "
            f"{audit['duplicate_excess']:,}"
        )
        print(
            "WAREHOUSE AUDIT: PASS"
        )
        print(
            "PUBLISHED SNAPSHOT: "
            f"{relative(final_snapshot_root)}"
        )
        print(
            "LATEST POINTER: "
            f"{relative(LATEST_POINTER)}"
        )
        print()
        print(
            "PHASE 1A.7 GOVERNED V3 "
            "REPLACEMENT COMPLETE"
        )

        return 0

    except Exception:
        if temporary_parent.exists():
            failure_marker = (
                temporary_parent
                / "BUILD_FAILED.txt"
            )

            failure_marker.write_text(
                (
                    f"{FAIL_STATUS}\n"
                    "The temporary build was not published.\n"
                ),
                encoding="utf-8",
            )

        raise


def audit_latest() -> int:
    if not LATEST_POINTER.exists():
        raise FileNotFoundError(
            "No published V3 latest pointer exists."
        )

    latest = load_json(
        LATEST_POINTER
    )

    snapshot_root = (
        ROOT
        / latest["snapshot_path"]
    )

    warehouse_csv = (
        snapshot_root
        / "historical_observation_warehouse_v3.csv"
    )

    warehouse_sqlite = (
        snapshot_root
        / "historical_observation_warehouse_v3.sqlite"
    )

    audit = audit_output_database(
        warehouse_sqlite,
        warehouse_csv,
    )

    print(
        "LATEST SNAPSHOT: "
        f"{relative(snapshot_root)}"
    )
    print(
        f"AUDIT STATUS: {audit['status']}"
    )
    print(
        "PHYSICAL ROWS: "
        f"{audit['physical_rows']:,}"
    )
    print(
        "UNIQUE RAW IDENTITIES: "
        f"{audit['unique_raw_identities']:,}"
    )
    print(
        "DUPLICATE EXCESS: "
        f"{audit['duplicate_excess']:,}"
    )

    if audit["status"] != "PASS":
        print(
            "FAILED CHECKS: "
            + ", ".join(
                audit["failed_checks"]
            )
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
