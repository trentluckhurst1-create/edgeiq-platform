from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FACT_PATH = (
    DATA
    / "edgeiq_race_epi_ordering_summary_fact_v1.csv"
)

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_epi_ordering_fact_v1.csv"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_epi_ordering_summary_fact_v1_contract.json"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_epi_ordering_summary_fact_v1_audit.json"
)

CONTRACT_VERSION = "1.0.0"
QUANTUM = Decimal("0.000001")

EXPECTED_PUBLICATION = (
    "RACE_EPI_ORDERING_SUMMARY_PUBLISHED"
)

EXPECTED_RECONCILIATION = (
    "RACE_EPI_ORDERING_SUMMARY_RECONCILED"
)

EXPECTED_STATUS = (
    "GOVERNED_RACE_EPI_ORDERING_SUMMARY"
)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def decimal_text(value: Decimal) -> str:
    return format(
        value.quantize(
            QUANTUM,
            rounding=ROUND_HALF_EVEN,
        ),
        ".6f",
    )


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
    path.parent.mkdir(parents=True, exist_ok=True)

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

        os.replace(temporary_path, path)

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
            "status": "PASS" if passed else "FAIL",
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
                "edgeiq_race_epi_ordering_summary_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_RACE_EPI_ORDERING_SUMMARY_FACT_V1_AUDIT_FAIL"
        )

    fact_fields, fact_rows = read_csv(
        FACT_PATH
    )

    _, source_rows = read_csv(
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
        set(contract["forbidden_fields"]).intersection(
            fact_fields
        )
    )

    check(
        "no_forbidden_fields",
        not forbidden_fields,
        forbidden_fields,
    )

    grouped_source: dict[
        tuple[str, str],
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in source_rows:
        grouped_source[
            (
                text(row.get("race_id")),
                text(row.get("race_date")),
            )
        ].append(row)

    fact_by_race = {
        (
            text(row.get("race_id")),
            text(row.get("race_date")),
        ): row
        for row in fact_rows
    }

    check(
        "published_race_population_exact",
        set(fact_by_race)
        == set(grouped_source)
        and len(fact_rows)
        == len(grouped_source),
        {
            "source_races": len(grouped_source),
            "fact_races": len(fact_rows),
        },
    )

    duplicate_ids = [
        value
        for value, count in Counter(
            text(
                row.get(
                    "race_epi_ordering_summary_id"
                )
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    ]

    duplicate_natural_keys = [
        f"{key[0]}|{key[1]}"
        for key, count in Counter(
            (
                text(row.get("race_id")),
                text(row.get("race_date")),
            )
            for row in fact_rows
        ).items()
        if key[0]
        and key[1]
        and count != 1
    ]

    check(
        "primary_keys_unique",
        not duplicate_ids,
        duplicate_ids,
    )

    check(
        "natural_keys_unique",
        not duplicate_natural_keys,
        duplicate_natural_keys,
    )

    identity_errors: list[str] = []
    metric_errors: list[str] = []
    source_errors: list[str] = []
    governance_errors: list[str] = []
    evidence_errors: list[str] = []
    lineage_errors: list[str] = []

    for race_key, population in grouped_source.items():
        row = fact_by_race.get(race_key)

        if row is None:
            source_errors.append(
                f"{race_key}:missing_summary"
            )
            continue

        ordered_population = sorted(
            population,
            key=lambda item: int(
                text(
                    item.get(
                        "epi_display_order_position"
                    )
                )
            ),
        )

        population_count = len(
            ordered_population
        )

        display_positions = [
            int(
                text(
                    item.get(
                        "epi_display_order_position"
                    )
                )
            )
            for item in ordered_population
        ]

        if display_positions != list(
            range(1, population_count + 1)
        ):
            source_errors.append(
                f"{race_key}:display_positions"
            )

        epi_text_values = [
            text(
                item.get(
                    "runner_epi_value"
                )
            )
            for item in ordered_population
        ]

        epi_values = [
            Decimal(value)
            for value in epi_text_values
        ]

        frequencies = Counter(
            epi_text_values
        )

        distinct_values = sorted(
            set(epi_values),
            reverse=True,
        )

        distinct_count = len(
            distinct_values
        )

        unique_count = sum(
            count
            for count in frequencies.values()
            if count == 1
        )

        tied_count = sum(
            count
            for count in frequencies.values()
            if count > 1
        )

        tie_group_count = sum(
            1
            for count in frequencies.values()
            if count > 1
        )

        largest_tie_group_size = max(
            frequencies.values()
        )

        top_epi = distinct_values[0]
        top_epi_text = decimal_text(
            top_epi
        )

        top_tie_size = frequencies[
            top_epi_text
        ]

        top_tie_status = (
            "TOP_EPI_TIED"
            if top_tie_size > 1
            else "TOP_EPI_UNIQUE"
        )

        if distinct_count >= 2:
            second_available = "YES"
            second_text = decimal_text(
                distinct_values[1]
            )
            gap_available = "YES"
            gap_text = decimal_text(
                top_epi - distinct_values[1]
            )
        else:
            second_available = "NO"
            second_text = ""
            gap_available = "NO"
            gap_text = ""

        ordered_source_ids = [
            text(
                item.get(
                    "race_entry_epi_ordering_id"
                )
            )
            for item in ordered_population
        ]

        ordered_source_evidence = [
            text(
                item.get(
                    "race_entry_epi_ordering_evidence_sha256"
                )
            )
            for item in ordered_population
        ]

        source_identity_hash = sha256_payload(
            ordered_source_ids
        )

        source_evidence_hash = sha256_payload(
            ordered_source_evidence
        )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_key[0],
                race_key[1],
                population_count,
                distinct_count,
                top_epi_text,
                text(
                    row.get(
                        "race_epi_ordering_summary_publication_decision"
                    )
                ),
            ]
        )

        expected_summary_id = (
            f"REOS1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        summary_id = text(
            row.get(
                "race_epi_ordering_summary_id"
            )
        )

        if summary_id != expected_summary_id:
            identity_errors.append(
                f"{race_key}:identity"
            )

        expected_metrics = {
            "ordered_epi_population_count": str(
                population_count
            ),
            "distinct_epi_count": str(
                distinct_count
            ),
            "unique_epi_entry_count": str(
                unique_count
            ),
            "tied_epi_entry_count": str(
                tied_count
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
            "second_distinct_epi": second_text,
            "top_to_second_epi_gap_available": (
                gap_available
            ),
            "top_to_second_epi_gap": gap_text,
            "top_epi_tie_group_size": str(
                top_tie_size
            ),
            "top_epi_tie_status": (
                top_tie_status
            ),
        }

        for field_name, expected_value in expected_metrics.items():
            if text(row.get(field_name)) != expected_value:
                metric_errors.append(
                    f"{race_key}:{field_name}"
                )

        if text(
            row.get(
                "source_ordering_identity_sha256"
            )
        ) != source_identity_hash:
            source_errors.append(
                f"{race_key}:source_identity"
            )

        if text(
            row.get(
                "source_ordering_evidence_sha256"
            )
        ) != source_evidence_hash:
            source_errors.append(
                f"{race_key}:source_evidence"
            )

        expected_governance = {
            "race_epi_ordering_summary_publication_decision": (
                EXPECTED_PUBLICATION
            ),
            "race_epi_ordering_summary_reconciliation_decision": (
                EXPECTED_RECONCILIATION
            ),
            "race_epi_ordering_summary_status": (
                EXPECTED_STATUS
            ),
            "contract_version": (
                CONTRACT_VERSION
            ),
        }

        for field_name, expected_value in expected_governance.items():
            if text(row.get(field_name)) != expected_value:
                governance_errors.append(
                    f"{race_key}:{field_name}"
                )

        expected_lineage = (
            "edgeiq_race_entry_epi_ordering_fact_v1:"
            f"{source_identity_hash}"
        )

        if text(
            row.get("source_lineage")
        ) != expected_lineage:
            lineage_errors.append(
                f"{race_key}:source_lineage"
            )

        expected_evidence = sha256_payload(
            [
                summary_id,
                race_key[0],
                race_key[1],
                population_count,
                distinct_count,
                unique_count,
                tied_count,
                tie_group_count,
                largest_tie_group_size,
                top_epi_text,
                second_available,
                second_text,
                gap_available,
                gap_text,
                top_tie_size,
                top_tie_status,
                source_identity_hash,
                source_evidence_hash,
                text(
                    row.get(
                        "race_epi_ordering_summary_publication_decision"
                    )
                ),
                text(
                    row.get(
                        "race_epi_ordering_summary_reconciliation_decision"
                    )
                ),
                text(
                    row.get(
                        "race_epi_ordering_summary_status"
                    )
                ),
                text(
                    row.get("source_lineage")
                ),
            ]
        )

        if text(
            row.get(
                "race_epi_ordering_summary_evidence_sha256"
            )
        ) != expected_evidence:
            evidence_errors.append(
                f"{race_key}:evidence"
            )

        for field_name in [
            "race_epi_ordering_summary_id",
            "race_id",
            "race_date",
            "top_epi",
            "source_ordering_identity_sha256",
            "source_ordering_evidence_sha256",
            "race_epi_ordering_summary_evidence_sha256",
            "source_lineage",
            "builder_version",
            "contract_version",
            "built_at_utc",
        ]:
            if not text(row.get(field_name)):
                lineage_errors.append(
                    f"{race_key}:{field_name}"
                )

    check(
        "deterministic_summary_identity",
        not identity_errors,
        identity_errors[:50],
    )

    check(
        "ordering_summary_metrics_reconciled",
        not metric_errors,
        metric_errors[:50],
    )

    check(
        "ordering_summary_sources_reconciled",
        not source_errors,
        source_errors[:50],
    )

    check(
        "ordering_summary_governance_exact",
        not governance_errors,
        governance_errors[:50],
    )

    check(
        "deterministic_summary_evidence",
        not evidence_errors,
        evidence_errors[:50],
    )

    check(
        "ordering_summary_lineage_complete",
        not lineage_errors,
        lineage_errors[:50],
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
            "edgeiq_race_epi_ordering_summary_fact_v1"
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
            "ordering_rows": len(source_rows),
            "source_race_count": len(
                grouped_source
            ),
            "summary_rows": len(fact_rows),
            "top_epi_tied_races": sum(
                1
                for row in fact_rows
                if text(
                    row.get(
                        "top_epi_tie_status"
                    )
                )
                == "TOP_EPI_TIED"
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
            "EDGEIQ_RACE_EPI_ORDERING_SUMMARY_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_EPI_ORDERING_SUMMARY_FACT_V1_AUDIT_PASS"
    )
    print(
        f"ordering_rows={len(source_rows)}"
    )
    print(
        f"source_race_count={len(grouped_source)}"
    )
    print(
        f"summary_rows={len(fact_rows)}"
    )
    print(
        f"top_epi_tied_races="
        f"{payload['counts']['top_epi_tied_races']}"
    )
    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
