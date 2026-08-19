from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTED_PATH = (
    DATA
    / "edgeiq_race_entry_projected_performance_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA
    / "edgeiq_race_eri_parameter_fact_v1.csv"
)

FACT_PATH = (
    DATA
    / "edgeiq_race_eri_fact_v1.csv"
)

AUDIT_PATH = (
    DATA
    / "edgeiq_race_eri_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_race_eri_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"

EXPECTED_METHODOLOGY = (
    "FIELD_MEAN_PROJECTED_PERFORMANCE"
)

EXPECTED_PUBLICATION = "ERI_PUBLISHED"
EXPECTED_RECONCILIATION = "ERI_METHOD_RECONCILED"
EXPECTED_STATUS = "GOVERNED_RACE_ERI"
EXPECTED_ROUNDING_MODE = "ROUND_HALF_EVEN"


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


def parse_date(
    value: object,
) -> date | None:
    raw = text(value)

    if not raw:
        return None

    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def decimal_text(
    value: Decimal,
) -> str:
    if value == 0:
        return "0"

    rendered = format(
        value.normalize(),
        "f",
    )

    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")

    return rendered


def governed_decimal_text(
    value: Decimal,
    decimal_places: int,
) -> str:
    quantum = Decimal(1).scaleb(
        -decimal_places
    )

    rounded = value.quantize(
        quantum,
        rounding=ROUND_HALF_EVEN,
    )

    return format(
        rounded,
        f".{decimal_places}f",
    )


def median_decimal(
    values: list[Decimal],
) -> Decimal:
    ordered = sorted(values)
    count = len(ordered)
    midpoint = count // 2

    if count % 2 == 1:
        return ordered[midpoint]

    return (
        ordered[midpoint - 1]
        + ordered[midpoint]
    ) / Decimal(2)


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
    temporary_path = Path(
        temporary_name
    )

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


def select_parameter(
    race_date_value: date,
    parameter_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    active: list[dict[str, str]] = []

    for parameter in parameter_rows:
        effective_from = parse_date(
            parameter[
                "effective_from_date"
            ]
        )

        effective_to_raw = text(
            parameter[
                "effective_to_date"
            ]
        )

        effective_to = (
            parse_date(
                effective_to_raw
            )
            if effective_to_raw
            else None
        )

        if effective_from is None:
            continue

        if race_date_value < effective_from:
            continue

        if (
            effective_to is not None
            and race_date_value > effective_to
        ):
            continue

        active.append(
            parameter
        )

    return active


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
        PROJECTED_PATH,
        PARAMETER_PATH,
        FACT_PATH,
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
                "edgeiq_race_eri_fact_v1"
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
            "EDGEIQ_RACE_ERI_FACT_V1_AUDIT_FAIL"
        )

    _, projected_rows = read_csv(
        PROJECTED_PATH
    )

    _, parameter_rows = read_csv(
        PARAMETER_PATH
    )

    fact_fields, fact_rows = read_csv(
        FACT_PATH
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

    projected_by_race: dict[
        str,
        list[dict[str, str]]
    ] = defaultdict(list)

    duplicate_projected_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_entry_projected_performance_id"
                ]
            )
            for row in projected_rows
        ).items()
        if value and count != 1
    )

    check(
        "projected_ids_unique",
        not duplicate_projected_ids,
        duplicate_projected_ids,
    )

    for row in projected_rows:
        projected_by_race[
            text(
                row[
                    "race_id"
                ]
            )
        ].append(
            row
        )

    duplicate_eri_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_eri_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    duplicate_race_ids = sorted(
        value
        for value, count
        in Counter(
            text(
                row[
                    "race_id"
                ]
            )
            for row in fact_rows
        ).items()
        if value and count != 1
    )

    check(
        "race_eri_ids_unique",
        not duplicate_eri_ids,
        duplicate_eri_ids,
    )

    check(
        "race_eri_natural_keys_unique",
        not duplicate_race_ids,
        duplicate_race_ids,
    )

    eligible_races: set[str] = set()
    below_minimum_races: set[str] = set()
    source_population_errors: list[str] = []
    source_state_errors: list[str] = []
    parameter_selection_errors: list[str] = []

    expected_by_race: dict[
        str,
        dict[str, object]
    ] = {}

    for race_id, rows in projected_by_race.items():
        if not race_id:
            source_population_errors.append(
                "BLANK_RACE_ID"
            )
            continue

        race_dates = {
            text(
                row[
                    "race_date"
                ]
            )
            for row in rows
        }

        if len(race_dates) != 1:
            source_population_errors.append(
                f"{race_id}:race_dates"
            )
            continue

        race_date_text = next(
            iter(race_dates)
        )

        race_date_value = parse_date(
            race_date_text
        )

        if race_date_value is None:
            source_population_errors.append(
                f"{race_id}:race_date"
            )
            continue

        active_parameters = select_parameter(
            race_date_value,
            parameter_rows,
        )

        if len(active_parameters) != 1:
            parameter_selection_errors.append(
                f"{race_id}:{len(active_parameters)}"
            )
            continue

        parameter = active_parameters[0]

        try:
            minimum_runner_count = int(
                text(
                    parameter[
                        "minimum_eligible_runner_count"
                    ]
                )
            )

            decimal_places = int(
                text(
                    parameter[
                        "eri_output_decimal_places"
                    ]
                )
            )
        except ValueError:
            parameter_selection_errors.append(
                f"{race_id}:parameter_integer"
            )
            continue

        if (
            text(
                parameter[
                    "eri_methodology_code"
                ]
            )
            != EXPECTED_METHODOLOGY
            or text(
                parameter[
                    "eri_rounding_mode"
                ]
            )
            != EXPECTED_ROUNDING_MODE
            or text(
                parameter[
                    "eri_parameter_scope"
                ]
            )
            != "GLOBAL"
            or text(
                parameter[
                    "eri_parameter_decision"
                ]
            )
            != "ERI_PARAMETER_AUTHORISED"
            or text(
                parameter[
                    "race_eri_parameter_status"
                ]
            )
            != "GOVERNED_ERI_PARAMETER"
        ):
            parameter_selection_errors.append(
                f"{race_id}:parameter_governance"
            )
            continue

        race_entry_ids = [
            text(
                row[
                    "race_entry_id"
                ]
            )
            for row in rows
        ]

        if (
            any(
                not value
                for value in race_entry_ids
            )
            or len(
                set(
                    race_entry_ids
                )
            )
            != len(
                race_entry_ids
            )
        ):
            source_population_errors.append(
                f"{race_id}:race_entry_ids"
            )
            continue

        projected_values: list[Decimal] = []
        projected_ids: list[str] = []
        projected_evidence: list[str] = []
        projected_builder_versions: set[str] = set()

        invalid_source = False

        for row in rows:
            projected_id = text(
                row[
                    "race_entry_projected_performance_id"
                ]
            )

            if (
                text(
                    row[
                        "projected_performance_publication_decision"
                    ]
                )
                != "PROJECTED_PERFORMANCE_PUBLISHED"
                or text(
                    row[
                        "projected_performance_reconciliation_decision"
                    ]
                )
                != "PROJECTED_PERFORMANCE_RECONCILED"
                or text(
                    row[
                        "race_entry_projected_performance_status"
                    ]
                )
                != "GOVERNED_PROJECTED_PERFORMANCE"
            ):
                source_state_errors.append(
                    projected_id
                )
                invalid_source = True
                continue

            value = parse_decimal(
                row[
                    "projected_performance_value"
                ]
            )

            evidence = text(
                row[
                    "race_entry_projected_performance_evidence_sha256"
                ]
            )

            builder_version = text(
                row[
                    "builder_version"
                ]
            )

            if (
                value is None
                or not projected_id
                or not evidence
                or not builder_version
            ):
                source_population_errors.append(
                    projected_id
                    or f"{race_id}:source"
                )
                invalid_source = True
                continue

            projected_values.append(
                value
            )

            projected_ids.append(
                projected_id
            )

            projected_evidence.append(
                evidence
            )

            projected_builder_versions.add(
                builder_version
            )

        if invalid_source:
            continue

        if len(
            projected_values
        ) < minimum_runner_count:
            below_minimum_races.add(
                race_id
            )
            continue

        eligible_races.add(
            race_id
        )

        projected_sum = sum(
            projected_values,
            Decimal(0),
        )

        mean_unrounded = (
            projected_sum
            / Decimal(
                len(
                    projected_values
                )
            )
        )

        median_value = median_decimal(
            projected_values
        )

        minimum_value = min(
            projected_values
        )

        maximum_value = max(
            projected_values
        )

        range_value = (
            maximum_value
            - minimum_value
        )

        expected_by_race[
            race_id
        ] = {
            "race_date": race_date_text,
            "parameter": parameter,
            "eligible_runner_count": len(
                projected_values
            ),
            "sum": decimal_text(
                projected_sum
            ),
            "mean_unrounded": decimal_text(
                mean_unrounded
            ),
            "mean": governed_decimal_text(
                mean_unrounded,
                decimal_places,
            ),
            "median": governed_decimal_text(
                median_value,
                decimal_places,
            ),
            "minimum": governed_decimal_text(
                minimum_value,
                decimal_places,
            ),
            "maximum": governed_decimal_text(
                maximum_value,
                decimal_places,
            ),
            "range": governed_decimal_text(
                range_value,
                decimal_places,
            ),
            "projected_id_set_sha256": sha256_payload(
                sorted(
                    projected_ids
                )
            ),
            "projected_evidence_set_sha256": sha256_payload(
                sorted(
                    projected_evidence
                )
            ),
            "projected_builder_version_set": "|".join(
                sorted(
                    projected_builder_versions
                )
            ),
            "decimal_places": decimal_places,
        }

    check(
        "source_population_valid",
        not source_population_errors,
        source_population_errors,
    )

    check(
        "source_states_governed",
        not source_state_errors,
        source_state_errors,
    )

    check(
        "parameter_selection_exact",
        not parameter_selection_errors,
        parameter_selection_errors,
    )

    published_race_ids = {
        text(
            row[
                "race_id"
            ]
        )
        for row in fact_rows
    }

    check(
        "published_population_exact",
        published_race_ids
        == eligible_races,
        {
            "expected": sorted(
                eligible_races
            ),
            "actual": sorted(
                published_race_ids
            ),
            "below_minimum": sorted(
                below_minimum_races
            ),
        },
    )

    arithmetic_errors: list[str] = []
    lineage_errors: list[str] = []
    governance_errors: list[str] = []
    identity_errors: list[str] = []
    evidence_errors: list[str] = []

    for row in fact_rows:
        race_id = text(
            row[
                "race_id"
            ]
        )

        race_eri_id = text(
            row[
                "race_eri_id"
            ]
        )

        expected = expected_by_race.get(
            race_id
        )

        if expected is None:
            arithmetic_errors.append(
                f"{race_id}:unexpected"
            )
            continue

        parameter = expected[
            "parameter"
        ]

        assert isinstance(
            parameter,
            dict,
        )

        expected_values = {
            "race_eri_parameter_id": text(
                parameter[
                    "race_eri_parameter_id"
                ]
            ),
            "eri_parameter_version": text(
                parameter[
                    "eri_parameter_version"
                ]
            ),
            "race_date": expected[
                "race_date"
            ],
            "eligible_runner_count": str(
                expected[
                    "eligible_runner_count"
                ]
            ),
            "projected_performance_sum": expected[
                "sum"
            ],
            "projected_performance_mean_unrounded": expected[
                "mean_unrounded"
            ],
            "projected_performance_mean": expected[
                "mean"
            ],
            "projected_performance_median": expected[
                "median"
            ],
            "projected_performance_minimum": expected[
                "minimum"
            ],
            "projected_performance_maximum": expected[
                "maximum"
            ],
            "projected_performance_range": expected[
                "range"
            ],
            "eri_value": expected[
                "mean"
            ],
            "eri_methodology_code": (
                EXPECTED_METHODOLOGY
            ),
            "eri_output_decimal_places": str(
                expected[
                    "decimal_places"
                ]
            ),
            "eri_rounding_mode": (
                EXPECTED_ROUNDING_MODE
            ),
            "eri_publication_decision": (
                EXPECTED_PUBLICATION
            ),
            "eri_method_reconciliation_decision": (
                EXPECTED_RECONCILIATION
            ),
            "race_eri_status": EXPECTED_STATUS,
            "source_projected_performance_id_set_sha256": (
                expected[
                    "projected_id_set_sha256"
                ]
            ),
            "source_projected_performance_evidence_set_sha256": (
                expected[
                    "projected_evidence_set_sha256"
                ]
            ),
            "source_eri_parameter_evidence_sha256": text(
                parameter[
                    "race_eri_parameter_evidence_sha256"
                ]
            ),
            "source_projected_performance_builder_version_set": (
                expected[
                    "projected_builder_version_set"
                ]
            ),
            "source_eri_parameter_builder_version": text(
                parameter[
                    "builder_version"
                ]
            ),
            "contract_version": CONTRACT_VERSION,
        }

        for field_name, expected_value in expected_values.items():
            if text(
                row[field_name]
            ) != text(
                expected_value
            ):
                arithmetic_errors.append(
                    f"{race_id}:{field_name}"
                )

        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_id,
                expected[
                    "race_date"
                ],
                text(
                    parameter[
                        "race_eri_parameter_id"
                    ]
                ),
                EXPECTED_PUBLICATION,
            ]
        )

        expected_eri_id = (
            f"ERI1-"
            f"{expected_identity_hash[:24].upper()}"
        )

        if race_eri_id != expected_eri_id:
            identity_errors.append(
                race_id
            )

        expected_evidence = sha256_payload(
            [
                race_eri_id,
                race_id,
                expected[
                    "race_date"
                ],
                text(
                    parameter[
                        "race_eri_parameter_id"
                    ]
                ),
                text(
                    parameter[
                        "eri_parameter_version"
                    ]
                ),
                text(
                    parameter[
                        "race_eri_parameter_evidence_sha256"
                    ]
                ),
                expected[
                    "projected_id_set_sha256"
                ],
                expected[
                    "projected_evidence_set_sha256"
                ],
                expected[
                    "eligible_runner_count"
                ],
                expected[
                    "sum"
                ],
                expected[
                    "mean_unrounded"
                ],
                expected[
                    "mean"
                ],
                expected[
                    "median"
                ],
                expected[
                    "minimum"
                ],
                expected[
                    "maximum"
                ],
                expected[
                    "range"
                ],
                expected[
                    "mean"
                ],
                EXPECTED_METHODOLOGY,
                EXPECTED_PUBLICATION,
                EXPECTED_RECONCILIATION,
                EXPECTED_STATUS,
            ]
        )

        if text(
            row[
                "race_eri_evidence_sha256"
            ]
        ) != expected_evidence:
            evidence_errors.append(
                race_id
            )

        required_lineage = [
            race_eri_id,
            text(
                row[
                    "race_eri_parameter_id"
                ]
            ),
            text(
                row[
                    "source_projected_performance_id_set_sha256"
                ]
            ),
            text(
                row[
                    "source_projected_performance_evidence_set_sha256"
                ]
            ),
            text(
                row[
                    "source_eri_parameter_evidence_sha256"
                ]
            ),
            text(
                row[
                    "race_eri_evidence_sha256"
                ]
            ),
            text(
                row[
                    "source_projected_performance_builder_version_set"
                ]
            ),
            text(
                row[
                    "source_eri_parameter_builder_version"
                ]
            ),
            text(
                row[
                    "builder_version"
                ]
            ),
            text(
                row[
                    "contract_version"
                ]
            ),
            text(
                row[
                    "built_at_utc"
                ]
            ),
        ]

        if any(
            not value
            for value in required_lineage
        ):
            lineage_errors.append(
                race_id
            )

        if (
            text(
                row[
                    "eri_publication_decision"
                ]
            )
            != EXPECTED_PUBLICATION
            or text(
                row[
                    "eri_method_reconciliation_decision"
                ]
            )
            != EXPECTED_RECONCILIATION
            or text(
                row[
                    "race_eri_status"
                ]
            )
            != EXPECTED_STATUS
        ):
            governance_errors.append(
                race_id
            )

    check(
        "eri_arithmetic_exact",
        not arithmetic_errors,
        arithmetic_errors,
    )

    check(
        "eri_lineage_complete",
        not lineage_errors,
        lineage_errors,
    )

    check(
        "eri_governance_complete",
        not governance_errors,
        governance_errors,
    )

    check(
        "deterministic_eri_identity",
        not identity_errors,
        identity_errors,
    )

    check(
        "deterministic_eri_evidence",
        not evidence_errors,
        evidence_errors,
    )

    forbidden_fields = set(
        contract[
            "forbidden_fields"
        ]
    )

    present_forbidden_fields = sorted(
        forbidden_fields.intersection(
            fact_fields
        )
    )

    check(
        "no_forbidden_fields",
        not present_forbidden_fields,
        present_forbidden_fields,
    )

    check(
        "current_population_expected",
        (
            len(projected_rows) == 0
            and len(parameter_rows) == 1
            and len(projected_by_race) == 0
            and len(below_minimum_races) == 0
            and len(fact_rows) == 0
        ),
        {
            "projected_performance_rows": (
                len(projected_rows)
            ),
            "eri_parameter_rows": (
                len(parameter_rows)
            ),
            "projected_race_count": (
                len(projected_by_race)
            ),
            "below_minimum_field_size_races": (
                len(below_minimum_races)
            ),
            "race_eri_rows": (
                len(fact_rows)
            ),
        },
    )

    failed_checks = [
        name
        for name, result
        in checks.items()
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
            "edgeiq_race_eri_fact_v1"
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
            "projected_performance_rows": (
                len(projected_rows)
            ),
            "eri_parameter_rows": (
                len(parameter_rows)
            ),
            "projected_race_count": (
                len(projected_by_race)
            ),
            "below_minimum_field_size_races": (
                len(below_minimum_races)
            ),
            "race_eri_rows": (
                len(fact_rows)
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
            "EDGEIQ_RACE_ERI_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_RACE_ERI_FACT_V1_AUDIT_PASS"
    )

    for name, value in payload[
        "counts"
    ].items():
        print(
            f"{name}={value}"
        )

    print(
        f"audit_output={AUDIT_PATH}"
    )


if __name__ == "__main__":
    main()
