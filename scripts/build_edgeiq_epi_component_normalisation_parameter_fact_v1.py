from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_epi_component_normalisation_parameter_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_epi_component_normalisation_parameter_fact_v1.0.0"
)

PARAMETER_VERSION = "EPI_NORMALISATION_V1_2026_01"

METHODOLOGY = (
    "WITHIN_RACE_POPULATION_Z_SCORE_CAPPED_V1"
)

POPULATION_SCOPE = (
    "COMPLETE_GOVERNED_ELIGIBLE_RACE_FIELD"
)

STANDARD_DEVIATION_BASIS = "POPULATION_N"
MINIMUM_POPULATION_COUNT = 2

LOWER_CAP = Decimal("-3.000000")
UPPER_CAP = Decimal("3.000000")

ZERO_VARIANCE_POLICY = "FAIL_CLOSED"

DECIMAL_PLACES = 6
ROUNDING_MODE = "ROUND_HALF_EVEN"

EFFECTIVE_FROM_DATE = "2026-01-01"
EFFECTIVE_TO_DATE = ""

PUBLICATION_DECISION = (
    "EPI_NORMALISATION_PARAMETER_AUTHORISED"
)

RECONCILIATION_DECISION = (
    "EPI_NORMALISATION_PARAMETER_RECONCILED"
)

GOVERNED_STATUS = (
    "GOVERNED_EPI_NORMALISATION_PARAMETER"
)

COMPONENT_CODES = [
    "HISTORICAL_PERFORMANCE",
    "SUITABILITY",
    "RACE_CONTEXT",
]

OUTPUT_FIELDS = [
    "epi_component_normalisation_parameter_id",
    "normalisation_parameter_version",
    "epi_component_code",
    "normalisation_methodology",
    "normalisation_population_scope",
    "standard_deviation_basis",
    "minimum_population_count",
    "normalised_lower_cap",
    "normalised_upper_cap",
    "zero_variance_policy",
    "normalisation_output_decimal_places",
    "normalisation_rounding_mode",
    "effective_from_date",
    "effective_to_date",
    "normalisation_parameter_publication_decision",
    "normalisation_parameter_reconciliation_decision",
    "normalisation_parameter_status",
    "normalisation_parameter_evidence_sha256",
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


def decimal_text(
    value: Decimal,
) -> str:
    quantum = Decimal(1).scaleb(
        -DECIMAL_PLACES
    )

    rounded = value.quantize(
        quantum,
        rounding=ROUND_HALF_EVEN,
    )

    return format(
        rounded,
        f".{DECIMAL_PLACES}f",
    )


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
    temporary_path = Path(
        temporary_name
    )

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
    if LOWER_CAP >= UPPER_CAP:
        raise RuntimeError(
            "Normalisation lower cap must be less than upper cap."
        )

    if MINIMUM_POPULATION_COUNT < 2:
        raise RuntimeError(
            "Minimum normalisation population must be at least two."
        )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    lower_cap_text = decimal_text(
        LOWER_CAP
    )

    upper_cap_text = decimal_text(
        UPPER_CAP
    )

    rows: list[dict[str, str]] = []

    for component_code in COMPONENT_CODES:
        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                PARAMETER_VERSION,
                component_code,
                METHODOLOGY,
                EFFECTIVE_FROM_DATE,
                PUBLICATION_DECISION,
            ]
        )

        parameter_id = (
            f"EPINP1-{identity_hash[:24].upper()}"
        )

        evidence_hash = sha256_payload(
            [
                parameter_id,
                PARAMETER_VERSION,
                component_code,
                METHODOLOGY,
                POPULATION_SCOPE,
                STANDARD_DEVIATION_BASIS,
                str(
                    MINIMUM_POPULATION_COUNT
                ),
                lower_cap_text,
                upper_cap_text,
                ZERO_VARIANCE_POLICY,
                str(
                    DECIMAL_PLACES
                ),
                ROUNDING_MODE,
                EFFECTIVE_FROM_DATE,
                EFFECTIVE_TO_DATE,
                PUBLICATION_DECISION,
                RECONCILIATION_DECISION,
                GOVERNED_STATUS,
            ]
        )

        rows.append(
            {
                "epi_component_normalisation_parameter_id": (
                    parameter_id
                ),
                "normalisation_parameter_version": (
                    PARAMETER_VERSION
                ),
                "epi_component_code": component_code,
                "normalisation_methodology": (
                    METHODOLOGY
                ),
                "normalisation_population_scope": (
                    POPULATION_SCOPE
                ),
                "standard_deviation_basis": (
                    STANDARD_DEVIATION_BASIS
                ),
                "minimum_population_count": str(
                    MINIMUM_POPULATION_COUNT
                ),
                "normalised_lower_cap": (
                    lower_cap_text
                ),
                "normalised_upper_cap": (
                    upper_cap_text
                ),
                "zero_variance_policy": (
                    ZERO_VARIANCE_POLICY
                ),
                "normalisation_output_decimal_places": str(
                    DECIMAL_PLACES
                ),
                "normalisation_rounding_mode": (
                    ROUNDING_MODE
                ),
                "effective_from_date": (
                    EFFECTIVE_FROM_DATE
                ),
                "effective_to_date": (
                    EFFECTIVE_TO_DATE
                ),
                "normalisation_parameter_publication_decision": (
                    PUBLICATION_DECISION
                ),
                "normalisation_parameter_reconciliation_decision": (
                    RECONCILIATION_DECISION
                ),
                "normalisation_parameter_status": (
                    GOVERNED_STATUS
                ),
                "normalisation_parameter_evidence_sha256": (
                    evidence_hash
                ),
                "builder_version": (
                    BUILDER_VERSION
                ),
                "contract_version": (
                    CONTRACT_VERSION
                ),
                "built_at_utc": (
                    built_at_utc
                ),
            }
        )

    rows.sort(
        key=lambda row: row[
            "epi_component_code"
        ]
    )

    atomic_write_csv(
        OUTPUT_PATH,
        rows,
    )

    print(
        "EDGEIQ_EPI_COMPONENT_NORMALISATION_PARAMETER_FACT_V1_BUILD_PASS"
    )
    print(
        f"normalisation_parameter_rows={len(rows)}"
    )
    print(
        f"normalisation_methodology={METHODOLOGY}"
    )
    print(
        f"normalised_lower_cap={lower_cap_text}"
    )
    print(
        f"normalised_upper_cap={upper_cap_text}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
