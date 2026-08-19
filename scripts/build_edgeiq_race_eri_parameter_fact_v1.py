from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_eri_parameter_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_race_eri_parameter_fact_v1.0.0"

PARAMETER_VERSION = "ERI-V1.0.0"
METHODOLOGY_CODE = "FIELD_MEAN_PROJECTED_PERFORMANCE"
METHODOLOGY_NAME = "Field Mean Projected Performance"

POPULATION_RULE = (
    "ALL_GOVERNED_RECONCILED_PROJECTED_PERFORMANCE_ROWS_PER_RACE"
)

COMPLETE_FIELD_REQUIRED = "TRUE"
MINIMUM_ELIGIBLE_RUNNER_COUNT = "2"
OUTPUT_DECIMAL_PLACES = "6"
ROUNDING_MODE = "ROUND_HALF_EVEN"
PARAMETER_SCOPE = "GLOBAL"
EFFECTIVE_FROM_DATE = "2026-07-22"
EFFECTIVE_TO_DATE = ""

PARAMETER_DECISION = "ERI_PARAMETER_AUTHORISED"
PARAMETER_STATUS = "GOVERNED_ERI_PARAMETER"

OUTPUT_FIELDS = [
    "race_eri_parameter_id",
    "eri_parameter_version",
    "eri_methodology_code",
    "eri_methodology_name",
    "eri_input_population_rule",
    "eri_complete_field_required",
    "minimum_eligible_runner_count",
    "eri_output_decimal_places",
    "eri_rounding_mode",
    "eri_parameter_scope",
    "effective_from_date",
    "effective_to_date",
    "eri_parameter_decision",
    "race_eri_parameter_status",
    "race_eri_parameter_evidence_sha256",
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
    identity_hash = sha256_payload(
        [
            CONTRACT_VERSION,
            PARAMETER_VERSION,
            METHODOLOGY_CODE,
            EFFECTIVE_FROM_DATE,
            PARAMETER_SCOPE,
        ]
    )

    parameter_id = (
        f"ERIP1-{identity_hash[:24].upper()}"
    )

    evidence_hash = sha256_payload(
        [
            parameter_id,
            PARAMETER_VERSION,
            METHODOLOGY_CODE,
            METHODOLOGY_NAME,
            POPULATION_RULE,
            COMPLETE_FIELD_REQUIRED,
            MINIMUM_ELIGIBLE_RUNNER_COUNT,
            OUTPUT_DECIMAL_PLACES,
            ROUNDING_MODE,
            PARAMETER_SCOPE,
            EFFECTIVE_FROM_DATE,
            EFFECTIVE_TO_DATE,
            PARAMETER_DECISION,
            PARAMETER_STATUS,
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
            "race_eri_parameter_id": parameter_id,
            "eri_parameter_version": PARAMETER_VERSION,
            "eri_methodology_code": METHODOLOGY_CODE,
            "eri_methodology_name": METHODOLOGY_NAME,
            "eri_input_population_rule": POPULATION_RULE,
            "eri_complete_field_required": (
                COMPLETE_FIELD_REQUIRED
            ),
            "minimum_eligible_runner_count": (
                MINIMUM_ELIGIBLE_RUNNER_COUNT
            ),
            "eri_output_decimal_places": (
                OUTPUT_DECIMAL_PLACES
            ),
            "eri_rounding_mode": ROUNDING_MODE,
            "eri_parameter_scope": PARAMETER_SCOPE,
            "effective_from_date": EFFECTIVE_FROM_DATE,
            "effective_to_date": EFFECTIVE_TO_DATE,
            "eri_parameter_decision": PARAMETER_DECISION,
            "race_eri_parameter_status": PARAMETER_STATUS,
            "race_eri_parameter_evidence_sha256": (
                evidence_hash
            ),
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
        "EDGEIQ_RACE_ERI_PARAMETER_FACT_V1_BUILD_PASS"
    )
    print("eri_parameter_rows=1")
    print(f"race_eri_parameter_id={parameter_id}")
    print(f"eri_parameter_version={PARAMETER_VERSION}")
    print(f"eri_methodology_code={METHODOLOGY_CODE}")
    print(
        "minimum_eligible_runner_count="
        f"{MINIMUM_ELIGIBLE_RUNNER_COUNT}"
    )
    print(
        "eri_output_decimal_places="
        f"{OUTPUT_DECIMAL_PLACES}"
    )
    print(f"eri_rounding_mode={ROUNDING_MODE}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
