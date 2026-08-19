from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OBSERVATION_PATH = (
    DATA / "edgeiq_horse_performance_observation_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA
    / "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv"
)

FACT_PATH = (
    DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv"
)

AUDIT_PATH = (
    DATA / "edgeiq_horse_performance_aggregate_fact_v1_audit.json"
)

CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_horse_performance_aggregate_fact_v1_contract.json"
)

CONTRACT_VERSION = "1.0.0"
AGGREGATE_STATUS = "HISTORICAL_AGGREGATE_GOVERNED"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


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
            raise RuntimeError(f"Missing CSV header: {path}")

        return list(reader.fieldnames), list(reader)


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(file_descriptor)

    temporary_path = Path(temporary_name)

    try:
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
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
        OBSERVATION_PATH,
        FACT_PATH,
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
                "edgeiq_horse_performance_aggregate_fact_v1"
            ),
            "audit_version": "1.0.0",
            "status": "FAIL",
            "checks": checks,
        }

        atomic_write_json(AUDIT_PATH, payload)

        raise SystemExit(
            "EDGEIQ_HORSE_PERFORMANCE_AGGREGATE_FACT_V1_AUDIT_FAIL"
        )

    _, observation_rows = read_csv(OBSERVATION_PATH)
    fact_fields, fact_rows = read_csv(FACT_PATH)

    contract = json.loads(
        CONTRACT_PATH.read_text(encoding="utf-8")
    )

    check(
        "contract_fields_exact",
        fact_fields == contract["required_fields"],
        {
            "actual": fact_fields,
            "expected": contract["required_fields"],
        },
    )

    if observation_rows and not PARAMETER_PATH.exists():
        check(
            "parameter_fact_required_when_observations_exist",
            False,
            "Aggregation parameter fact is missing.",
        )
        parameter_rows = []
    elif PARAMETER_PATH.exists():
        _, parameter_rows = read_csv(PARAMETER_PATH)

        check(
            "parameter_fact_available",
            True,
            {
                "aggregation_parameter_rows": len(
                    parameter_rows
                )
            },
        )
    else:
        parameter_rows = []

        check(
            "parameter_fact_not_required_for_empty_observations",
            not observation_rows,
            {
                "horse_performance_observation_rows": len(
                    observation_rows
                ),
                "parameter_fact_exists": False,
            },
        )

    aggregate_ids = [
        text(row["horse_performance_aggregate_id"])
        for row in fact_rows
    ]

    duplicate_aggregate_ids = sorted(
        value
        for value, count in Counter(aggregate_ids).items()
        if value and count != 1
    )

    check(
        "unique_aggregate_ids",
        not duplicate_aggregate_ids,
        duplicate_aggregate_ids,
    )

    duplicate_grains = sorted(
        grain
        for grain, count in Counter(
            (
                text(row["canonical_horse_id"]),
                text(row["aggregate_as_of_date"]),
                text(
                    row[
                        "horse_performance_aggregation_parameter_id"
                    ]
                ),
            )
            for row in fact_rows
        ).items()
        if count != 1
    )

    check(
        "unique_aggregate_grain",
        not duplicate_grains,
        duplicate_grains,
    )

    governance_errors: list[str] = []
    population_errors: list[str] = []
    method_errors: list[str] = []

    parameter_ids = {
        text(
            row[
                "horse_performance_aggregation_parameter_id"
            ]
        )
        for row in parameter_rows
    }

    for row in fact_rows:
        aggregate_id = text(
            row["horse_performance_aggregate_id"]
        )

        try:
            maximum_observations = int(
                text(row["maximum_observations"])
            )
            minimum_observations = int(
                text(row["minimum_observations"])
            )
            eligible_count = int(
                text(row["eligible_observation_count"])
            )
            included_count = int(
                text(row["included_observation_count"])
            )
            total_weight = Decimal(
                text(row["total_weight"])
            )
            aggregate_value = Decimal(
                text(row["aggregate_rating_value"])
            )
        except Exception as exc:
            governance_errors.append(
                f"{aggregate_id}:{type(exc).__name__}"
            )
            continue

        if (
            not text(row["canonical_horse_id"])
            or not text(row["canonical_horse_name"])
            or text(row["aggregate_status"])
            != AGGREGATE_STATUS
            or text(row["contract_version"])
            != CONTRACT_VERSION
            or maximum_observations <= 0
            or minimum_observations <= 0
            or included_count < minimum_observations
            or included_count > maximum_observations
            or eligible_count < included_count
            or not total_weight.is_finite()
            or total_weight <= 0
            or not aggregate_value.is_finite()
            or not text(
                row["included_observation_ids_sha256"]
            )
            or not text(
                row["source_parameter_evidence_sha256"]
            )
            or not text(
                row["source_observation_evidence_sha256"]
            )
            or not text(
                row[
                    "horse_performance_aggregate_evidence_sha256"
                ]
            )
        ):
            governance_errors.append(aggregate_id)

        parameter_id = text(
            row[
                "horse_performance_aggregation_parameter_id"
            ]
        )

        if parameter_id not in parameter_ids:
            population_errors.append(
                f"{aggregate_id}: unknown parameter"
            )

        method_pair = (
            text(row["aggregation_method"]),
            text(row["recency_weighting_method"]),
        )

        if method_pair == ("ARITHMETIC_MEAN", "NONE"):
            if text(row["recency_half_life_days"]):
                method_errors.append(aggregate_id)
        elif method_pair == (
            "WEIGHTED_ARITHMETIC_MEAN",
            "EXPONENTIAL_HALF_LIFE",
        ):
            try:
                half_life = Decimal(
                    text(row["recency_half_life_days"])
                )

                if (
                    not half_life.is_finite()
                    or half_life <= 0
                ):
                    method_errors.append(aggregate_id)
            except Exception:
                method_errors.append(aggregate_id)
        else:
            method_errors.append(aggregate_id)

    check(
        "aggregate_governance",
        not governance_errors,
        governance_errors,
    )

    check(
        "parameter_lineage",
        not population_errors,
        population_errors,
    )

    check(
        "aggregation_method_coherence",
        not method_errors,
        method_errors,
    )

    forbidden_fields = set(contract["forbidden_fields"])
    present_forbidden_fields = sorted(
        forbidden_fields.intersection(fact_fields)
    )

    check(
        "no_forbidden_fields",
        not present_forbidden_fields,
        present_forbidden_fields,
    )

    available_minimums = []
    for parameter in parameter_rows:
        if text(parameter.get("parameter_status")) == "AVAILABLE":
            try:
                available_minimums.append(
                    int(text(parameter.get("minimum_observations")))
                )
            except ValueError:
                pass
    minimum_required = min(available_minimums) if available_minimums else 1
    observations_by_horse = Counter(
        text(row.get("canonical_horse_id"))
        for row in observation_rows
        if text(row.get("canonical_horse_id"))
    )
    all_observed_horses_below_minimum = (
        bool(observation_rows)
        and len(fact_rows) == 0
        and all(count < minimum_required for count in observations_by_horse.values())
    )
    current_population_expected = (
        (len(observation_rows) == 0 and len(fact_rows) == 0)
        or len(fact_rows) > 0
        or all_observed_horses_below_minimum
    )

    check(
        "current_population_expected",
        current_population_expected,
        {
            "horse_performance_observation_rows": len(
                observation_rows
            ),
            "aggregation_parameter_rows": len(
                parameter_rows
            ),
            "horse_performance_aggregate_rows": len(
                fact_rows
            ),
            "minimum_observations_required": minimum_required,
            "observed_horses_below_minimum": all_observed_horses_below_minimum,
        },
    )

    failed_checks = [
        name
        for name, result in checks.items()
        if result["status"] != "PASS"
    ]

    status = "PASS" if not failed_checks else "FAIL"

    payload = {
        "audit_name": (
            "edgeiq_horse_performance_aggregate_fact_v1"
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
            "horse_performance_observation_rows": len(
                observation_rows
            ),
            "aggregation_parameter_rows": len(
                parameter_rows
            ),
            "horse_performance_aggregate_rows": len(
                fact_rows
            ),
            "minimum_observations_required": minimum_required,
            "observed_horses_below_minimum": all_observed_horses_below_minimum,
        },
        "failed_checks": failed_checks,
        "checks": checks,
    }

    atomic_write_json(AUDIT_PATH, payload)

    if status != "PASS":
        print(json.dumps(payload, indent=2))

        raise SystemExit(
            "EDGEIQ_HORSE_PERFORMANCE_AGGREGATE_FACT_V1_AUDIT_FAIL"
        )

    print(
        "EDGEIQ_HORSE_PERFORMANCE_AGGREGATE_FACT_V1_AUDIT_PASS"
    )

    for name, value in payload["counts"].items():
        print(f"{name}={value}")

    print(f"audit_output={AUDIT_PATH}")


if __name__ == "__main__":
    main()
