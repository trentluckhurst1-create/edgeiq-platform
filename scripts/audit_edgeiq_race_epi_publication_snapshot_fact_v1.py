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

FACT_PATH = (
    DATA
    / "edgeiq_race_epi_publication_snapshot_fact_v1.csv"
)

DISTRIBUTION_PATH = (
    DATA
    / "edgeiq_race_epi_distribution_fact_v1.csv"
)

SUMMARY_PATH = (
    DATA
    / "edgeiq_race_epi_ordering_summary_fact_v1.csv"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_epi_publication_snapshot_fact_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_epi_publication_snapshot_fact_v1_audit.json"
)

CONTRACT_VERSION = "1.0.0"

EXPECTED_PUBLICATION = (
    "RACE_EPI_SNAPSHOT_PUBLISHED"
)
EXPECTED_RECONCILIATION = (
    "RACE_EPI_SNAPSHOT_RECONCILED"
)
EXPECTED_STATUS = (
    "GOVERNED_RACE_EPI_PUBLICATION_SNAPSHOT"
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
    return sha256_text(
        "\x1f".join(
            text(part)
            for part in parts
        )
    )


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


def first_existing(
    fields: list[str],
    candidates: list[str],
) -> str:
    for candidate in candidates:
        if candidate in fields:
            return candidate

    return ""


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
        DISTRIBUTION_PATH,
        SUMMARY_PATH,
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
                "edgeiq_race_epi_publication_snapshot_fact_v1"
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
            "EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, fact_rows = read_csv(
        FACT_PATH
    )

    distribution_fields, distribution_rows = read_csv(
        DISTRIBUTION_PATH
    )

    _, summary_rows = read_csv(
        SUMMARY_PATH
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

    distribution_id_field = first_existing(
        distribution_fields,
        DISTRIBUTION_ID_CANDIDATES,
    )

    distribution_evidence_field = first_existing(
        distribution_fields,
        DISTRIBUTION_EVIDENCE_CANDIDATES,
    )

    check(
        "distribution_identity_field_resolved",
        bool(distribution_id_field),
        distribution_id_field,
    )

    check(
        "distribution_evidence_field_resolved",
        bool(distribution_evidence_field),
        distribution_evidence_field,
    )

    distribution_by_race = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        ): row
        for row in distribution_rows
    }

    summary_by_race = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        ): row
        for row in summary_rows
    }

    fact_by_race = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        ): row
        for row in fact_rows
    }

    duplicate_ids = [
        identity
        for identity, count in Counter(
            text(
                row.get(
                    "race_epi_publication_snapshot_id"
                )
            )
            for row in fact_rows
        ).items()
        if identity and count != 1
    ]

    check(
        "snapshot_primary_keys_unique",
        not duplicate_ids,
        duplicate_ids[:50],
    )

    check(
        "source_race_populations_exact",
        set(distribution_by_race)
        == set(summary_by_race)
        == set(fact_by_race)
        and len(distribution_rows)
        == len(summary_rows)
        == len(fact_rows),
        {
            "distribution_rows": len(
                distribution_rows
            ),
            "ordering_summary_rows": len(
                summary_rows
            ),
            "snapshot_rows": len(
                fact_rows
            ),
        },
    )

    identity_errors: list[str] = []
    field_errors: list[str] = []
    distribution_errors: list[str] = []
    population_errors: list[str] = []
    governance_errors: list[str] = []
    lineage_errors: list[str] = []
    evidence_errors: list[str] = []

    for race_key in sorted(
        set(distribution_by_race)
        & set(summary_by_race)
        & set(fact_by_race)
    ):
        distribution = distribution_by_race[
            race_key
        ]

        summary = summary_by_race[
            race_key
        ]

        snapshot = fact_by_race[
            race_key
        ]

        for field in SUMMARY_FIELDS:
            if text(
                snapshot.get(field)
            ) != text(
                summary.get(field)
            ):
                field_errors.append(
                    f"{race_key}:{field}"
                )

        distribution_record = {
            field: text(
                distribution.get(field)
            )
            for field in distribution_fields
        }

        expected_distribution_json = json.dumps(
            distribution_record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        actual_distribution_json = text(
            snapshot.get(
                "source_distribution_record_json"
            )
        )

        if (
            actual_distribution_json
            != expected_distribution_json
        ):
            distribution_errors.append(
                f"{race_key}:distribution_json"
            )

        try:
            reconstructed = json.loads(
                actual_distribution_json
            )
        except json.JSONDecodeError:
            reconstructed = None

        if reconstructed != distribution_record:
            distribution_errors.append(
                f"{race_key}:distribution_reconstruction"
            )

        expected_distribution_hash = sha256_text(
            expected_distribution_json
        )

        if text(
            snapshot.get(
                "source_distribution_record_sha256"
            )
        ) != expected_distribution_hash:
            distribution_errors.append(
                f"{race_key}:distribution_hash"
            )

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

        if text(
            snapshot.get(
                "source_distribution_id"
            )
        ) != distribution_id:
            field_errors.append(
                f"{race_key}:source_distribution_id"
            )

        if text(
            snapshot.get(
                "source_distribution_evidence_sha256"
            )
        ) != distribution_evidence:
            field_errors.append(
                f"{race_key}:source_distribution_evidence"
            )

        if text(
            snapshot.get(
                "source_ordering_summary_id"
            )
        ) != summary_id:
            field_errors.append(
                f"{race_key}:source_ordering_summary_id"
            )

        if text(
            snapshot.get(
                "source_ordering_summary_evidence_sha256"
            )
        ) != summary_evidence:
            field_errors.append(
                f"{race_key}:source_ordering_summary_evidence"
            )

        population_field = text(
            snapshot.get(
                "distribution_population_field"
            )
        )

        population_value = text(
            snapshot.get(
                "distribution_population_value"
            )
        )

        population_status = text(
            snapshot.get(
                "distribution_population_reconciliation_status"
            )
        )

        if population_field:
            if population_field not in distribution_fields:
                population_errors.append(
                    f"{race_key}:population_field_missing"
                )
            elif text(
                distribution.get(
                    population_field
                )
            ) != population_value:
                population_errors.append(
                    f"{race_key}:population_value"
                )
            else:
                try:
                    if int(
                        population_value
                    ) != int(
                        text(
                            summary.get(
                                "ordered_epi_population_count"
                            )
                        )
                    ):
                        population_errors.append(
                            f"{race_key}:population_mismatch"
                        )
                except ValueError:
                    population_errors.append(
                        f"{race_key}:population_invalid"
                    )

            if population_status != "RECONCILED":
                population_errors.append(
                    f"{race_key}:population_status"
                )

        else:
            if population_value:
                population_errors.append(
                    f"{race_key}:unexpected_population_value"
                )

            if (
                population_status
                != "NOT_EXPOSED_BY_SOURCE_CONTRACT"
            ):
                population_errors.append(
                    f"{race_key}:population_not_exposed_status"
                )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_key[0],
                race_key[1],
                distribution_id,
                summary_id,
                EXPECTED_PUBLICATION,
            ]
        )

        expected_snapshot_id = (
            "REPS1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        snapshot_id = text(
            snapshot.get(
                "race_epi_publication_snapshot_id"
            )
        )

        if snapshot_id != expected_snapshot_id:
            identity_errors.append(
                f"{race_key}:identity"
            )

        expected_governance = {
            "race_epi_snapshot_publication_decision": (
                EXPECTED_PUBLICATION
            ),
            "race_epi_snapshot_reconciliation_decision": (
                EXPECTED_RECONCILIATION
            ),
            "race_epi_snapshot_status": (
                EXPECTED_STATUS
            ),
            "contract_version": (
                CONTRACT_VERSION
            ),
        }

        for field, expected in expected_governance.items():
            if text(
                snapshot.get(field)
            ) != expected:
                governance_errors.append(
                    f"{race_key}:{field}"
                )

        expected_lineage = (
            "edgeiq_race_epi_distribution_fact_v1:"
            f"{distribution_id}|"
            "edgeiq_race_epi_ordering_summary_fact_v1:"
            f"{summary_id}"
        )

        lineage = text(
            snapshot.get("source_lineage")
        )

        if lineage != expected_lineage:
            lineage_errors.append(
                f"{race_key}:lineage"
            )

        expected_evidence = sha256_payload(
            [
                snapshot_id,
                race_key[0],
                race_key[1],
                *[
                    text(
                        snapshot.get(field)
                    )
                    for field in SUMMARY_FIELDS
                ],
                population_field,
                population_value,
                population_status,
                distribution_id,
                distribution_evidence,
                expected_distribution_hash,
                summary_id,
                summary_evidence,
                text(
                    snapshot.get(
                        "race_epi_snapshot_publication_decision"
                    )
                ),
                text(
                    snapshot.get(
                        "race_epi_snapshot_reconciliation_decision"
                    )
                ),
                text(
                    snapshot.get(
                        "race_epi_snapshot_status"
                    )
                ),
                lineage,
            ]
        )

        if text(
            snapshot.get(
                "race_epi_publication_snapshot_evidence_sha256"
            )
        ) != expected_evidence:
            evidence_errors.append(
                f"{race_key}:evidence"
            )

        for field in [
            "race_epi_publication_snapshot_id",
            "race_id",
            "race_date",
            "top_epi",
            "source_distribution_id",
            "source_distribution_evidence_sha256",
            "source_distribution_record_json",
            "source_distribution_record_sha256",
            "source_ordering_summary_id",
            "source_ordering_summary_evidence_sha256",
            "race_epi_publication_snapshot_evidence_sha256",
            "source_lineage",
            "builder_version",
            "contract_version",
            "built_at_utc",
        ]:
            if not text(
                snapshot.get(field)
            ):
                lineage_errors.append(
                    f"{race_key}:{field}"
                )

    check(
        "ordering_summary_fields_preserved",
        not field_errors,
        field_errors[:100],
    )

    check(
        "distribution_record_preserved_exactly",
        not distribution_errors,
        distribution_errors[:100],
    )

    check(
        "population_reconciliation_valid",
        not population_errors,
        population_errors[:100],
    )

    check(
        "deterministic_snapshot_identity",
        not identity_errors,
        identity_errors[:100],
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
        "deterministic_snapshot_evidence",
        not evidence_errors,
        evidence_errors[:100],
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
            "edgeiq_race_epi_publication_snapshot_fact_v1"
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
            "distribution_rows": len(
                distribution_rows
            ),
            "ordering_summary_rows": len(
                summary_rows
            ),
            "publication_snapshot_rows": len(
                fact_rows
            ),
            "population_reconciled_rows": sum(
                1
                for row in fact_rows
                if text(
                    row.get(
                        "distribution_population_reconciliation_status"
                    )
                )
                == "RECONCILED"
            ),
            "population_not_exposed_rows": sum(
                1
                for row in fact_rows
                if text(
                    row.get(
                        "distribution_population_reconciliation_status"
                    )
                )
                == "NOT_EXPOSED_BY_SOURCE_CONTRACT"
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
            "EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_EPI_PUBLICATION_SNAPSHOT_FACT_V1_AUDIT_PASS"
    )
    print(
        f"distribution_rows={len(distribution_rows)}"
    )
    print(
        f"ordering_summary_rows={len(summary_rows)}"
    )
    print(
        f"publication_snapshot_rows={len(fact_rows)}"
    )
    print(
        "population_reconciled_rows="
        f"{payload['counts']['population_reconciled_rows']}"
    )
    print(
        "population_not_exposed_rows="
        f"{payload['counts']['population_not_exposed_rows']}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
