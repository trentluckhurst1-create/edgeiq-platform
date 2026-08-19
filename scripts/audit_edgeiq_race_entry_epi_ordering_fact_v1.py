from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FACT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_ordering_fact_v1.csv"
)

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_epi_relative_context_fact_v1.csv"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_epi_ordering_fact_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_ordering_fact_v1_audit.json"
)

CONTRACT_VERSION = "1.0.0"

EXPECTED_PUBLICATION = "EPI_ORDERING_PUBLISHED"
EXPECTED_RECONCILIATION = "EPI_ORDERING_RECONCILED"
EXPECTED_STATUS = "GOVERNED_RACE_ENTRY_EPI_ORDERING"


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


def parse_decimal(
    value: object,
) -> Decimal | None:
    raw = text(value)

    if not raw:
        return None

    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return None

    if not parsed.is_finite():
        return None

    return parsed


def parse_integer(
    value: object,
) -> int | None:
    raw = text(value)

    if not raw:
        return None

    try:
        return int(raw)
    except ValueError:
        return None


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
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


def atomic_write_json(
    path: Path,
    payload: dict,
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
        temporary_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    checks: dict[str, dict[str, object]] = {}

    def check(
        name: str,
        passed: bool,
        detail: object,
    ) -> None:
        checks[name] = {
            "status": (
                "PASS"
                if passed
                else "FAIL"
            ),
            "detail": detail,
        }

    required_paths = [
        FACT_PATH,
        SOURCE_PATH,
        CONTRACT_PATH,
    ]

    missing_paths = [
        str(
            path.relative_to(ROOT)
        )
        for path in required_paths
        if not path.exists()
    ]

    check(
        "required_files_exist",
        not missing_paths,
        missing_paths,
    )

    if missing_paths:
        payload = {
            "audit_name": (
                "edgeiq_race_entry_epi_ordering_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(
            AUDIT_PATH,
            payload,
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, fact_rows = read_csv(
        FACT_PATH
    )

    source_fields, source_rows = read_csv(
        SOURCE_PATH
    )

    contract = json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    check(
        "contract_fields_exact",
        fact_fields
        == contract[
            "required_fields"
        ],
        {
            "actual": fact_fields,
            "expected": contract[
                "required_fields"
            ],
        },
    )

    forbidden_fields = sorted(
        set(
            contract[
                "forbidden_fields"
            ]
        ).intersection(
            fact_fields
        )
    )

    check(
        "no_forbidden_fields",
        not forbidden_fields,
        forbidden_fields,
    )

    source_by_entry = {
        text(
            row.get(
                "race_entry_id"
            )
        ): row
        for row in source_rows
    }

    fact_by_entry = {
        text(
            row.get(
                "race_entry_id"
            )
        ): row
        for row in fact_rows
    }

    check(
        "published_population_exact",
        set(
            fact_by_entry
        )
        == set(
            source_by_entry
        )
        and len(
            fact_rows
        )
        == len(
            source_rows
        ),
        {
            "source_rows": len(
                source_rows
            ),
            "fact_rows": len(
                fact_rows
            ),
        },
    )

    duplicate_primary_keys = sorted(
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_entry_epi_ordering_id"
                )
            )
            for row in fact_rows
        ).items()
        if value
        and count != 1
    )

    duplicate_natural_keys = sorted(
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_entry_id"
                )
            )
            for row in fact_rows
        ).items()
        if value
        and count != 1
    )

    check(
        "primary_keys_unique",
        not duplicate_primary_keys,
        duplicate_primary_keys,
    )

    check(
        "natural_keys_unique",
        not duplicate_natural_keys,
        duplicate_natural_keys,
    )

    grouped_source: dict[
        tuple[str, str],
        list[dict[str, str]],
    ] = defaultdict(list)

    grouped_fact: dict[
        tuple[str, str],
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in source_rows:
        grouped_source[
            (
                text(
                    row.get(
                        "race_id"
                    )
                ),
                text(
                    row.get(
                        "race_date"
                    )
                ),
            )
        ].append(
            row
        )

    for row in fact_rows:
        grouped_fact[
            (
                text(
                    row.get(
                        "race_id"
                    )
                ),
                text(
                    row.get(
                        "race_date"
                    )
                ),
            )
        ].append(
            row
        )

    check(
        "race_population_keys_exact",
        set(
            grouped_fact
        )
        == set(
            grouped_source
        ),
        {
            "source_races": len(
                grouped_source
            ),
            "fact_races": len(
                grouped_fact
            ),
        },
    )

    identity_errors: list[str] = []
    join_errors: list[str] = []
    ordering_errors: list[str] = []
    tie_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []

    for race_key, source_population in grouped_source.items():
        expected_population = sorted(
            source_population,
            key=lambda row: (
                -Decimal(
                    text(
                        row.get(
                            "runner_epi_value"
                        )
                    )
                ),
                text(
                    row.get(
                        "race_entry_id"
                    )
                ),
            ),
        )

        actual_population = grouped_fact.get(
            race_key,
            [],
        )

        expected_count = len(
            expected_population
        )

        actual_by_display = sorted(
            actual_population,
            key=lambda row: (
                parse_integer(
                    row.get(
                        "epi_display_order_position"
                    )
                )
                or 0
            ),
        )

        actual_display_positions = [
            parse_integer(
                row.get(
                    "epi_display_order_position"
                )
            )
            for row in actual_by_display
        ]

        if actual_display_positions != list(
            range(
                1,
                expected_count + 1,
            )
        ):
            ordering_errors.append(
                f"{race_key}:display_positions"
            )

        epi_frequency = Counter(
            text(
                row.get(
                    "runner_epi_value"
                )
            )
            for row in expected_population
        )

        distinct_epi_descending = sorted(
            {
                Decimal(
                    text(
                        row.get(
                            "runner_epi_value"
                        )
                    )
                )
                for row in expected_population
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

        for display_position, source_row in enumerate(
            expected_population,
            start=1,
        ):
            epi_value = Decimal(
                text(
                    source_row.get(
                        "runner_epi_value"
                    )
                )
            )

            if previous_epi is None or epi_value != previous_epi:
                competition_rank_by_epi[
                    epi_value
                ] = display_position

            previous_epi = epi_value

        tie_position_counter: dict[
            str,
            int,
        ] = defaultdict(int)

        for display_position, source_row in enumerate(
            expected_population,
            start=1,
        ):
            race_entry_id = text(
                source_row.get(
                    "race_entry_id"
                )
            )

            fact_row = fact_by_entry.get(
                race_entry_id
            )

            if fact_row is None:
                join_errors.append(
                    f"{race_entry_id}:missing_fact"
                )
                continue

            context_id = text(
                source_row.get(
                    "race_entry_epi_relative_context_id"
                )
            )

            runner_epi_text = text(
                source_row.get(
                    "runner_epi_value"
                )
            )

            runner_epi = Decimal(
                runner_epi_text
            )

            source_evidence = text(
                source_row.get(
                    "race_entry_epi_relative_context_evidence_sha256"
                )
            )

            tie_group_size = epi_frequency[
                runner_epi_text
            ]

            tie_position_counter[
                runner_epi_text
            ] += 1

            tie_group_position = (
                tie_position_counter[
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

            expected_identity_hash = sha256_payload(
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
                    text(
                        fact_row.get(
                            "epi_ordering_publication_decision"
                        )
                    ),
                ]
            )

            expected_ordering_id = (
                f"REEO1-"
                f"{expected_identity_hash[:24].upper()}"
            )

            ordering_id = text(
                fact_row.get(
                    "race_entry_epi_ordering_id"
                )
            )

            if ordering_id != expected_ordering_id:
                identity_errors.append(
                    race_entry_id
                )

            expected_join_fields = {
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
                        expected_count
                    )
                ),
                "race_entry_epi_relative_context_evidence_sha256": (
                    source_evidence
                ),
            }

            for field_name, expected_value in expected_join_fields.items():
                if text(
                    fact_row.get(
                        field_name
                    )
                ) != expected_value:
                    join_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

            expected_ordering_fields = {
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
            }

            for field_name, expected_value in expected_ordering_fields.items():
                if text(
                    fact_row.get(
                        field_name
                    )
                ) != expected_value:
                    ordering_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

            expected_tie_fields = {
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
            }

            for field_name, expected_value in expected_tie_fields.items():
                if text(
                    fact_row.get(
                        field_name
                    )
                ) != expected_value:
                    tie_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

            expected_governance = {
                "epi_ordering_publication_decision": (
                    EXPECTED_PUBLICATION
                ),
                "epi_ordering_reconciliation_decision": (
                    EXPECTED_RECONCILIATION
                ),
                "epi_ordering_status": (
                    EXPECTED_STATUS
                ),
                "contract_version": (
                    CONTRACT_VERSION
                ),
            }

            for field_name, expected_value in expected_governance.items():
                if text(
                    fact_row.get(
                        field_name
                    )
                ) != expected_value:
                    governance_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

            expected_source_lineage = (
                "edgeiq_race_entry_epi_relative_context_fact_v1:"
                f"{context_id}"
            )

            if text(
                fact_row.get(
                    "source_lineage"
                )
            ) != expected_source_lineage:
                lineage_errors.append(
                    f"{race_entry_id}:source_lineage"
                )

            expected_evidence = sha256_payload(
                [
                    ordering_id,
                    race_entry_id,
                    context_id,
                    race_key[0],
                    race_key[1],
                    runner_epi_text,
                    expected_count,
                    display_position,
                    competition_rank,
                    dense_rank,
                    tie_group_size,
                    tie_group_position,
                    tie_status,
                    source_evidence,
                    text(
                        fact_row.get(
                            "epi_ordering_publication_decision"
                        )
                    ),
                    text(
                        fact_row.get(
                            "epi_ordering_reconciliation_decision"
                        )
                    ),
                    text(
                        fact_row.get(
                            "epi_ordering_status"
                        )
                    ),
                    text(
                        fact_row.get(
                            "source_lineage"
                        )
                    ),
                ]
            )

            if text(
                fact_row.get(
                    "race_entry_epi_ordering_evidence_sha256"
                )
            ) != expected_evidence:
                evidence_errors.append(
                    race_entry_id
                )

            for field_name in [
                "race_entry_epi_ordering_id",
                "race_entry_id",
                "race_entry_epi_relative_context_id",
                "race_id",
                "race_date",
                "runner_epi_value",
                "race_entry_epi_relative_context_evidence_sha256",
                "race_entry_epi_ordering_evidence_sha256",
                "source_lineage",
                "builder_version",
                "contract_version",
                "built_at_utc",
            ]:
                if not text(
                    fact_row.get(
                        field_name
                    )
                ):
                    lineage_errors.append(
                        f"{race_entry_id}:{field_name}"
                    )

    check(
        "deterministic_ordering_identity",
        not identity_errors,
        identity_errors[:50],
    )

    check(
        "ordering_sources_reconciled",
        not join_errors,
        join_errors[:50],
    )

    check(
        "descending_epi_ordering_reconciled",
        not ordering_errors,
        ordering_errors[:50],
    )

    check(
        "explicit_tie_handling_reconciled",
        not tie_errors,
        tie_errors[:50],
    )

    check(
        "ordering_governance_exact",
        not governance_errors,
        governance_errors[:50],
    )

    check(
        "deterministic_ordering_evidence",
        not evidence_errors,
        evidence_errors[:50],
    )

    check(
        "ordering_lineage_complete",
        not lineage_errors,
        lineage_errors[:50],
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result[
            "status"
        ] != "PASS"
    ]

    status = (
        "PASS"
        if not failed_checks
        else "FAIL"
    )

    payload = {
        "audit_name": (
            "edgeiq_race_entry_epi_ordering_fact_v1"
        ),
        "audit_version": "1.0.0",
        "audited_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "status": status,
        "counts": {
            "relative_context_rows": len(
                source_rows
            ),
            "source_race_count": len(
                grouped_source
            ),
            "ordering_rows": len(
                fact_rows
            ),
            "tied_ordering_rows": sum(
                1
                for row in fact_rows
                if text(
                    row.get(
                        "epi_tie_status"
                    )
                )
                == "TIED_EPI"
            ),
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }

    atomic_write_json(
        AUDIT_PATH,
        payload,
    )

    if status != "PASS":
        print(
            json.dumps(
                payload,
                indent=2,
            )
        )

        raise SystemExit(
            "EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_EPI_ORDERING_FACT_V1_AUDIT_PASS"
    )
    print(
        f"relative_context_rows={len(source_rows)}"
    )
    print(
        f"source_race_count={len(grouped_source)}"
    )
    print(
        f"ordering_rows={len(fact_rows)}"
    )
    print(
        f"tied_ordering_rows={payload['counts']['tied_ordering_rows']}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
