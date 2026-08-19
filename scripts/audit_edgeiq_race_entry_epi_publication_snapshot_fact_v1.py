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
    / "edgeiq_race_entry_epi_publication_snapshot_fact_v1.csv"
)

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_epi_ordering_fact_v1.csv"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_entry_epi_publication_snapshot_fact_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_publication_snapshot_fact_v1_audit.json"
)

CONTRACT_VERSION = "1.0.0"

EXPECTED_PUBLICATION = (
    "RACE_ENTRY_EPI_SNAPSHOT_PUBLISHED"
)

EXPECTED_RECONCILIATION = (
    "RACE_ENTRY_EPI_SNAPSHOT_RECONCILED"
)

EXPECTED_STATUS = (
    "GOVERNED_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT"
)


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
    try:
        return int(text(value))
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
        str(path.relative_to(ROOT))
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
                "edgeiq_race_entry_epi_publication_snapshot_fact_v1"
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
            "EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_FAIL"
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
        == contract["required_fields"],
        {
            "actual": fact_fields,
            "expected": contract[
                "required_fields"
            ],
        },
    )

    forbidden_fields = sorted(
        set(
            contract["forbidden_fields"]
        ).intersection(fact_fields)
    )

    check(
        "no_forbidden_fields",
        not forbidden_fields,
        forbidden_fields,
    )

    source_by_entry = {
        text(row.get("race_entry_id")): row
        for row in source_rows
    }

    fact_by_entry = {
        text(row.get("race_entry_id")): row
        for row in fact_rows
    }

    check(
        "source_population_exact",
        set(source_by_entry)
        == set(fact_by_entry)
        and len(source_rows)
        == len(fact_rows),
        {
            "source_rows": len(source_rows),
            "fact_rows": len(fact_rows),
            "source_unique_entries": len(
                source_by_entry
            ),
            "fact_unique_entries": len(
                fact_by_entry
            ),
        },
    )

    duplicate_snapshot_ids = [
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_entry_epi_publication_snapshot_id"
                )
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    ]

    duplicate_entries = [
        value
        for value, count in Counter(
            text(row.get("race_entry_id"))
            for row in fact_rows
        ).items()
        if value and count != 1
    ]

    check(
        "snapshot_primary_keys_unique",
        not duplicate_snapshot_ids,
        duplicate_snapshot_ids[:50],
    )

    check(
        "snapshot_natural_keys_unique",
        not duplicate_entries,
        duplicate_entries[:50],
    )

    field_errors: list[str] = []
    identity_errors: list[str] = []
    evidence_errors: list[str] = []
    governance_errors: list[str] = []
    lineage_errors: list[str] = []
    source_errors: list[str] = []

    source_to_snapshot_fields = {
        "race_entry_id": "race_entry_id",
        "race_id": "race_id",
        "race_date": "race_date",
        "runner_epi_value": "runner_epi_value",
        "eligible_epi_population_count": (
            "eligible_epi_population_count"
        ),
        "epi_display_order_position": (
            "epi_display_order_position"
        ),
        "epi_competition_rank": (
            "epi_competition_rank"
        ),
        "epi_dense_rank": "epi_dense_rank",
        "epi_tie_group_size": (
            "epi_tie_group_size"
        ),
        "epi_tie_group_position": (
            "epi_tie_group_position"
        ),
        "epi_tie_status": "epi_tie_status",
        "race_entry_epi_relative_context_evidence_sha256": (
            "source_relative_context_evidence_sha256"
        ),
        "race_entry_epi_ordering_id": (
            "source_ordering_id"
        ),
        "race_entry_epi_ordering_evidence_sha256": (
            "source_ordering_evidence_sha256"
        ),
    }

    for race_entry_id, source in source_by_entry.items():
        snapshot = fact_by_entry.get(
            race_entry_id
        )

        if snapshot is None:
            source_errors.append(
                f"{race_entry_id}:missing_snapshot"
            )
            continue

        for (
            source_field,
            snapshot_field,
        ) in source_to_snapshot_fields.items():
            if text(
                source.get(source_field)
            ) != text(
                snapshot.get(snapshot_field)
            ):
                field_errors.append(
                    f"{race_entry_id}:"
                    f"{snapshot_field}"
                )

        epi_raw = text(
            snapshot.get("runner_epi_value")
        )

        epi = parse_decimal(epi_raw)

        if (
            epi is None
            or epi.as_tuple().exponent != -6
        ):
            field_errors.append(
                f"{race_entry_id}:runner_epi_value_format"
            )

        integer_fields = [
            "eligible_epi_population_count",
            "epi_display_order_position",
            "epi_competition_rank",
            "epi_dense_rank",
            "epi_tie_group_size",
            "epi_tie_group_position",
        ]

        for field_name in integer_fields:
            value = parse_integer(
                snapshot.get(field_name)
            )

            if value is None or value < 1:
                field_errors.append(
                    f"{race_entry_id}:{field_name}"
                )

        tie_size = parse_integer(
            snapshot.get(
                "epi_tie_group_size"
            )
        )

        tie_position = parse_integer(
            snapshot.get(
                "epi_tie_group_position"
            )
        )

        tie_status = text(
            snapshot.get("epi_tie_status")
        )

        if (
            tie_size is not None
            and tie_position is not None
            and tie_position > tie_size
        ):
            field_errors.append(
                f"{race_entry_id}:tie_position_gt_size"
            )

        if (
            tie_status == "EPI_UNIQUE"
            and tie_size != 1
        ):
            field_errors.append(
                f"{race_entry_id}:unique_tie_size"
            )

        if (
            tie_status == "EPI_TIED"
            and (
                tie_size is None
                or tie_size < 2
            )
        ):
            field_errors.append(
                f"{race_entry_id}:tied_tie_size"
            )

        expected_publication = (
            EXPECTED_PUBLICATION
        )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_entry_id,
                text(
                    snapshot.get("race_id")
                ),
                text(
                    snapshot.get("race_date")
                ),
                epi_raw,
                text(
                    snapshot.get(
                        "epi_display_order_position"
                    )
                ),
                text(
                    snapshot.get(
                        "epi_competition_rank"
                    )
                ),
                expected_publication,
            ]
        )

        expected_snapshot_id = (
            "REEPS1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        snapshot_id = text(
            snapshot.get(
                "race_entry_epi_publication_snapshot_id"
            )
        )

        if snapshot_id != expected_snapshot_id:
            identity_errors.append(
                f"{race_entry_id}:identity"
            )

        expected_governance = {
            "race_entry_epi_snapshot_publication_decision": (
                EXPECTED_PUBLICATION
            ),
            "race_entry_epi_snapshot_reconciliation_decision": (
                EXPECTED_RECONCILIATION
            ),
            "race_entry_epi_snapshot_status": (
                EXPECTED_STATUS
            ),
            "contract_version": (
                CONTRACT_VERSION
            ),
        }

        for (
            field_name,
            expected_value,
        ) in expected_governance.items():
            if text(
                snapshot.get(field_name)
            ) != expected_value:
                governance_errors.append(
                    f"{race_entry_id}:{field_name}"
                )

        source_ordering_id = text(
            snapshot.get(
                "source_ordering_id"
            )
        )

        expected_lineage = (
            "edgeiq_race_entry_epi_ordering_fact_v1:"
            f"{source_ordering_id}"
        )

        source_lineage = text(
            snapshot.get("source_lineage")
        )

        if source_lineage != expected_lineage:
            lineage_errors.append(
                f"{race_entry_id}:source_lineage"
            )

        expected_evidence = sha256_payload(
            [
                snapshot_id,
                race_entry_id,
                text(
                    snapshot.get("race_id")
                ),
                text(
                    snapshot.get("race_date")
                ),
                epi_raw,
                text(
                    snapshot.get(
                        "eligible_epi_population_count"
                    )
                ),
                text(
                    snapshot.get(
                        "epi_display_order_position"
                    )
                ),
                text(
                    snapshot.get(
                        "epi_competition_rank"
                    )
                ),
                text(
                    snapshot.get(
                        "epi_dense_rank"
                    )
                ),
                text(
                    snapshot.get(
                        "epi_tie_group_size"
                    )
                ),
                text(
                    snapshot.get(
                        "epi_tie_group_position"
                    )
                ),
                tie_status,
                text(
                    snapshot.get(
                        "source_relative_context_evidence_sha256"
                    )
                ),
                source_ordering_id,
                text(
                    snapshot.get(
                        "source_ordering_evidence_sha256"
                    )
                ),
                text(
                    snapshot.get(
                        "race_entry_epi_snapshot_publication_decision"
                    )
                ),
                text(
                    snapshot.get(
                        "race_entry_epi_snapshot_reconciliation_decision"
                    )
                ),
                text(
                    snapshot.get(
                        "race_entry_epi_snapshot_status"
                    )
                ),
                source_lineage,
            ]
        )

        if text(
            snapshot.get(
                "race_entry_epi_publication_snapshot_evidence_sha256"
            )
        ) != expected_evidence:
            evidence_errors.append(
                f"{race_entry_id}:evidence"
            )

        for field_name in [
            "race_entry_epi_publication_snapshot_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_epi_value",
            "source_relative_context_evidence_sha256",
            "source_ordering_id",
            "source_ordering_evidence_sha256",
            "race_entry_epi_publication_snapshot_evidence_sha256",
            "source_lineage",
            "builder_version",
            "contract_version",
            "built_at_utc",
        ]:
            if not text(
                snapshot.get(field_name)
            ):
                lineage_errors.append(
                    f"{race_entry_id}:{field_name}"
                )

    grouped_fact: dict[
        tuple[str, str],
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in fact_rows:
        grouped_fact[
            (
                text(row.get("race_id")),
                text(row.get("race_date")),
            )
        ].append(row)

    race_order_errors: list[str] = []

    for race_key, population in grouped_fact.items():
        ordered = sorted(
            population,
            key=lambda row: int(
                text(
                    row.get(
                        "epi_display_order_position"
                    )
                )
            ),
        )

        population_count = len(
            ordered
        )

        positions = [
            int(
                text(
                    row.get(
                        "epi_display_order_position"
                    )
                )
            )
            for row in ordered
        ]

        if positions != list(
            range(1, population_count + 1)
        ):
            race_order_errors.append(
                f"{race_key}:display_positions"
            )

        declared_population_counts = {
            text(
                row.get(
                    "eligible_epi_population_count"
                )
            )
            for row in ordered
        }

        if declared_population_counts != {
            str(population_count)
        }:
            race_order_errors.append(
                f"{race_key}:population_count"
            )

        epi_values = [
            Decimal(
                text(
                    row.get(
                        "runner_epi_value"
                    )
                )
            )
            for row in ordered
        ]

        if epi_values != sorted(
            epi_values,
            reverse=True,
        ):
            race_order_errors.append(
                f"{race_key}:epi_descending"
            )

        frequencies = Counter(
            text(
                row.get(
                    "runner_epi_value"
                )
            )
            for row in population
        )

        distinct_values = sorted(
            {
                Decimal(
                    text(
                        row.get(
                            "runner_epi_value"
                        )
                    )
                )
                for row in population
            },
            reverse=True,
        )

        expected_dense = {
            value: index + 1
            for index, value in enumerate(
                distinct_values
            )
        }

        for row in population:
            epi = Decimal(
                text(
                    row.get(
                        "runner_epi_value"
                    )
                )
            )

            expected_competition = (
                sum(
                    1
                    for candidate in population
                    if Decimal(
                        text(
                            candidate.get(
                                "runner_epi_value"
                            )
                        )
                    )
                    > epi
                )
                + 1
            )

            if int(
                text(
                    row.get(
                        "epi_competition_rank"
                    )
                )
            ) != expected_competition:
                race_order_errors.append(
                    f"{race_key}:competition_rank:"
                    f"{text(row.get('race_entry_id'))}"
                )

            if int(
                text(
                    row.get(
                        "epi_dense_rank"
                    )
                )
            ) != expected_dense[epi]:
                race_order_errors.append(
                    f"{race_key}:dense_rank:"
                    f"{text(row.get('race_entry_id'))}"
                )

            expected_tie_size = frequencies[
                text(
                    row.get(
                        "runner_epi_value"
                    )
                )
            ]

            if int(
                text(
                    row.get(
                        "epi_tie_group_size"
                    )
                )
            ) != expected_tie_size:
                race_order_errors.append(
                    f"{race_key}:tie_size:"
                    f"{text(row.get('race_entry_id'))}"
                )

    check(
        "source_fields_preserved_exactly",
        not field_errors,
        field_errors[:100],
    )

    check(
        "deterministic_snapshot_identity",
        not identity_errors,
        identity_errors[:100],
    )

    check(
        "deterministic_snapshot_evidence",
        not evidence_errors,
        evidence_errors[:100],
    )

    check(
        "snapshot_governance_exact",
        not governance_errors,
        governance_errors[:100],
    )

    check(
        "snapshot_lineage_complete",
        not lineage_errors,
        lineage_errors[:100],
    )

    check(
        "source_reconciliation_complete",
        not source_errors,
        source_errors[:100],
    )

    check(
        "race_ordering_reconciled",
        not race_order_errors,
        race_order_errors[:100],
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result["status"] != "PASS"
    ]

    status = (
        "PASS"
        if not failed_checks
        else "FAIL"
    )

    payload = {
        "audit_name": (
            "edgeiq_race_entry_epi_publication_snapshot_fact_v1"
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
            "source_ordering_rows": len(
                source_rows
            ),
            "publication_snapshot_rows": len(
                fact_rows
            ),
            "race_count": len(
                grouped_fact
            ),
            "unique_epi_rows": sum(
                1
                for row in fact_rows
                if text(
                    row.get("epi_tie_status")
                )
                == "EPI_UNIQUE"
            ),
            "tied_epi_rows": sum(
                1
                for row in fact_rows
                if text(
                    row.get("epi_tie_status")
                )
                == "EPI_TIED"
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
            "EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ENTRY_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_PASS"
    )
    print(
        f"source_ordering_rows={len(source_rows)}"
    )
    print(
        f"publication_snapshot_rows={len(fact_rows)}"
    )
    print(
        f"race_count={len(grouped_fact)}"
    )
    print(
        f"unique_epi_rows="
        f"{payload['counts']['unique_epi_rows']}"
    )
    print(
        f"tied_epi_rows="
        f"{payload['counts']['tied_epi_rows']}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
