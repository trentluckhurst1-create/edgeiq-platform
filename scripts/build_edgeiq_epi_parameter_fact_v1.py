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
    / "edgeiq_epi_parameter_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_epi_parameter_fact_v1.0.0"

PARAMETER_VERSION = "EPI_V1_2026_01"
METHODOLOGY = "NORMALISED_WEIGHTED_ADDITIVE_EPI_V1"

EPI_BASE_VALUE = Decimal("100.000000")
HISTORICAL_PERFORMANCE_WEIGHT = Decimal("0.500000")
SUITABILITY_WEIGHT = Decimal("0.300000")
RACE_CONTEXT_WEIGHT = Decimal("0.200000")

DECIMAL_PLACES = 6
ROUNDING_MODE = "ROUND_HALF_EVEN"

EFFECTIVE_FROM_DATE = "2026-01-01"
EFFECTIVE_TO_DATE = ""

PUBLICATION_DECISION = "EPI_PARAMETER_AUTHORISED"
RECONCILIATION_DECISION = "EPI_PARAMETER_RECONCILED"
GOVERNED_STATUS = "GOVERNED_EPI_PARAMETER"

OUTPUT_FIELDS = [
    "epi_parameter_id",
    "epi_parameter_version",
    "epi_methodology",
    "epi_base_value",
    "historical_performance_weight",
    "suitability_weight",
    "race_context_weight",
    "total_component_weight",
    "historical_performance_required",
    "suitability_required",
    "race_context_required",
    "minimum_required_component_count",
    "epi_output_decimal_places",
    "epi_rounding_mode",
    "effective_from_date",
    "effective_to_date",
    "epi_parameter_publication_decision",
    "epi_parameter_reconciliation_decision",
    "epi_parameter_status",
    "epi_parameter_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(
        str(part if part is not None else "").strip()
        for part in parts
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def decimal_text(value: Decimal) -> str:
    quantum = Decimal(1).scaleb(-DECIMAL_PLACES)

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


def main() -> None:
    total_weight = (
        HISTORICAL_PERFORMANCE_WEIGHT
        + SUITABILITY_WEIGHT
        + RACE_CONTEXT_WEIGHT
    )

    if total_weight != Decimal("1.000000"):
        raise RuntimeError(
            "EPI component weights must total exactly 1.000000."
        )

    if any(
        value < Decimal("0")
        for value in [
            HISTORICAL_PERFORMANCE_WEIGHT,
            SUITABILITY_WEIGHT,
            RACE_CONTEXT_WEIGHT,
        ]
    ):
        raise RuntimeError(
            "EPI component weights cannot be negative."
        )

    identity_hash = sha256_payload(
        [
            CONTRACT_VERSION,
            PARAMETER_VERSION,
            METHODOLOGY,
            EFFECTIVE_FROM_DATE,
            PUBLICATION_DECISION,
        ]
    )

    epi_parameter_id = (
        f"EPIP1-{identity_hash[:24].upper()}"
    )

    base_value_text = decimal_text(
        EPI_BASE_VALUE
    )

    historical_weight_text = decimal_text(
        HISTORICAL_PERFORMANCE_WEIGHT
    )

    suitability_weight_text = decimal_text(
        SUITABILITY_WEIGHT
    )

    race_context_weight_text = decimal_text(
        RACE_CONTEXT_WEIGHT
    )

    total_weight_text = decimal_text(
        total_weight
    )

    evidence_hash = sha256_payload(
        [
            epi_parameter_id,
            PARAMETER_VERSION,
            METHODOLOGY,
            base_value_text,
            historical_weight_text,
            suitability_weight_text,
            race_context_weight_text,
            total_weight_text,
            "TRUE",
            "TRUE",
            "TRUE",
            "3",
            str(DECIMAL_PLACES),
            ROUNDING_MODE,
            EFFECTIVE_FROM_DATE,
            EFFECTIVE_TO_DATE,
            PUBLICATION_DECISION,
            RECONCILIATION_DECISION,
            GOVERNED_STATUS,
        ]
    )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    rows = [
        {
            "epi_parameter_id": epi_parameter_id,
            "epi_parameter_version": PARAMETER_VERSION,
            "epi_methodology": METHODOLOGY,
            "epi_base_value": base_value_text,
            "historical_performance_weight": historical_weight_text,
            "suitability_weight": suitability_weight_text,
            "race_context_weight": race_context_weight_text,
            "total_component_weight": total_weight_text,
            "historical_performance_required": "TRUE",
            "suitability_required": "TRUE",
            "race_context_required": "TRUE",
            "minimum_required_component_count": "3",
            "epi_output_decimal_places": str(
                DECIMAL_PLACES
            ),
            "epi_rounding_mode": ROUNDING_MODE,
            "effective_from_date": EFFECTIVE_FROM_DATE,
            "effective_to_date": EFFECTIVE_TO_DATE,
            "epi_parameter_publication_decision": (
                PUBLICATION_DECISION
            ),
            "epi_parameter_reconciliation_decision": (
                RECONCILIATION_DECISION
            ),
            "epi_parameter_status": GOVERNED_STATUS,
            "epi_parameter_evidence_sha256": evidence_hash,
            "builder_version": BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": built_at_utc,
        }
    ]

    atomic_write_csv(
        OUTPUT_PATH,
        rows,
    )

    print(
        "EDGEIQ_EPI_PARAMETER_FACT_V1_BUILD_PASS"
    )
    print(
        f"epi_parameter_rows={len(rows)}"
    )
    print(
        f"epi_parameter_id={epi_parameter_id}"
    )
    print(
        f"total_component_weight={total_weight_text}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
