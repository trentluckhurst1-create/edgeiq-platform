from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjustment_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_context_adjusted_performance_fact_v1.0.0"
)

ADJUSTMENT_APPLIED = "ADJUSTMENT_APPLIED"
PARAMETER_NOT_AVAILABLE = "PARAMETER_NOT_AVAILABLE"
CONTEXT_INELIGIBLE = "CONTEXT_INELIGIBLE"

PERFORMANCE_ADJUSTED = "PERFORMANCE_ADJUSTED"

ADJUSTED_STATUS = (
    "GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE"
)

NOT_AVAILABLE_STATUS = (
    "GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE"
)

INELIGIBLE_STATUS = (
    "CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTED_PERFORMANCE"
)

OUTPUT_FIELDS = [
    "race_entry_context_adjusted_performance_id",
    "race_entry_context_adjustment_id",
    "race_entry_context_parameter_selection_id",
    "race_entry_context_eligibility_id",
    "race_entry_performance_context_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "historical_rating_value",
    "context_parameter_id",
    "total_context_adjustment",
    "context_adjusted_performance_value",
    "source_adjustment_decision",
    "context_adjusted_performance_decision",
    "race_entry_context_adjusted_performance_status",
    "source_adjustment_evidence_sha256",
    "race_entry_context_adjusted_performance_evidence_sha256",
    "source_adjustment_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


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


def parse_required_decimal(
    value: object,
    field_name: str,
) -> Decimal:
    raw = text(value)

    if not raw:
        fail(
            f"Blank required decimal: {field_name}"
        )

    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal {field_name}: {raw!r}"
        ) from exc

    if not parsed.is_finite():
        fail(
            f"Non-finite decimal {field_name}: {raw!r}"
        )

    return parsed


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


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(
            f"Missing canonical input: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(
                f"Missing CSV header: {path}"
            )

        return list(reader.fieldnames), list(reader)


def require_fields(
    actual: list[str],
    required: Iterable[str],
) -> None:
    missing = [
        field
        for field in required
        if field not in actual
    ]

    if missing:
        fail(
            f"{SOURCE_PATH.name} missing required fields: "
            f"{missing}"
        )


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
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
    source_fields, source_rows = read_csv(
        SOURCE_PATH
    )

    require_fields(
        source_fields,
        [
            "race_entry_context_adjustment_id",
            "race_entry_context_parameter_selection_id",
            "race_entry_context_eligibility_id",
            "race_entry_performance_context_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "historical_rating_value",
            "context_parameter_id",
            "total_context_adjustment",
            "context_adjustment_application_decision",
            "race_entry_context_adjustment_status",
            "race_entry_context_adjustment_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )

    if not source_rows:
        atomic_write_csv(
            OUTPUT_PATH,
            [],
        )

        print(
            "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_BUILD_PASS"
        )
        print("context_adjustment_rows=0")
        print("performance_adjusted_rows=0")
        print("parameter_not_available_rows=0")
        print("context_ineligible_rows=0")
        print("context_adjusted_performance_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []

    seen_adjustment_ids: set[str] = set()
    seen_output_ids: set[str] = set()

    adjusted_count = 0
    unavailable_count = 0
    ineligible_count = 0

    for source in source_rows:
        adjustment_id = text(
            source[
                "race_entry_context_adjustment_id"
            ]
        )

        if not adjustment_id:
            fail(
                "Blank race_entry_context_adjustment_id."
            )

        if adjustment_id in seen_adjustment_ids:
            fail(
                f"Duplicate context-adjustment ID: "
                f"{adjustment_id}"
            )

        seen_adjustment_ids.add(
            adjustment_id
        )

        historical_rating = parse_required_decimal(
            source["historical_rating_value"],
            "historical_rating_value",
        )

        historical_rating_value = decimal_text(
            historical_rating
        )

        source_decision = text(
            source[
                "context_adjustment_application_decision"
            ]
        )

        context_parameter_id = text(
            source["context_parameter_id"]
        )

        total_adjustment_text = text(
            source["total_context_adjustment"]
        )

        if source_decision == ADJUSTMENT_APPLIED:
            if not context_parameter_id:
                fail(
                    f"{adjustment_id}: applied adjustment has "
                    "blank context parameter ID."
                )

            total_adjustment = parse_required_decimal(
                total_adjustment_text,
                "total_context_adjustment",
            )

            total_adjustment_value = decimal_text(
                total_adjustment
            )

            adjusted_value = decimal_text(
                historical_rating
                + total_adjustment
            )

            output_decision = PERFORMANCE_ADJUSTED
            output_status = ADJUSTED_STATUS
            adjusted_count += 1

        elif source_decision == PARAMETER_NOT_AVAILABLE:
            if context_parameter_id:
                fail(
                    f"{adjustment_id}: unavailable adjustment "
                    "contains a context parameter ID."
                )

            if total_adjustment_text:
                fail(
                    f"{adjustment_id}: unavailable adjustment "
                    "contains a total adjustment."
                )

            total_adjustment_value = ""
            adjusted_value = ""
            output_decision = PARAMETER_NOT_AVAILABLE
            output_status = NOT_AVAILABLE_STATUS
            unavailable_count += 1

        elif source_decision == CONTEXT_INELIGIBLE:
            if context_parameter_id:
                fail(
                    f"{adjustment_id}: ineligible adjustment "
                    "contains a context parameter ID."
                )

            if total_adjustment_text:
                fail(
                    f"{adjustment_id}: ineligible adjustment "
                    "contains a total adjustment."
                )

            total_adjustment_value = ""
            adjusted_value = ""
            output_decision = CONTEXT_INELIGIBLE
            output_status = INELIGIBLE_STATUS
            ineligible_count += 1

        else:
            fail(
                f"{adjustment_id}: unsupported source "
                f"decision {source_decision!r}."
            )

        source_evidence = text(
            source[
                "race_entry_context_adjustment_evidence_sha256"
            ]
        )

        source_builder = text(
            source["builder_version"]
        )

        source_contract = text(
            source["contract_version"]
        )

        if (
            not source_evidence
            or not source_builder
            or not source_contract
        ):
            fail(
                f"{adjustment_id}: incomplete source lineage."
            )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                adjustment_id,
                output_decision,
            ]
        )

        output_id = (
            f"RECAP1-{identity_hash[:24].upper()}"
        )

        if output_id in seen_output_ids:
            fail(
                f"Duplicate deterministic adjusted "
                f"performance ID: {output_id}"
            )

        seen_output_ids.add(
            output_id
        )

        evidence_hash = sha256_payload(
            [
                output_id,
                source_evidence,
                historical_rating_value,
                total_adjustment_value,
                adjusted_value,
                output_decision,
                output_status,
            ]
        )

        output_rows.append(
            {
                "race_entry_context_adjusted_performance_id": (
                    output_id
                ),
                "race_entry_context_adjustment_id": (
                    adjustment_id
                ),
                "race_entry_context_parameter_selection_id": text(
                    source[
                        "race_entry_context_parameter_selection_id"
                    ]
                ),
                "race_entry_context_eligibility_id": text(
                    source[
                        "race_entry_context_eligibility_id"
                    ]
                ),
                "race_entry_performance_context_id": text(
                    source[
                        "race_entry_performance_context_id"
                    ]
                ),
                "race_entry_id": text(
                    source["race_entry_id"]
                ),
                "race_id": text(
                    source["race_id"]
                ),
                "race_date": text(
                    source["race_date"]
                ),
                "runner_id": text(
                    source["runner_id"]
                ),
                "canonical_horse_id": text(
                    source["canonical_horse_id"]
                ),
                "canonical_horse_name": text(
                    source["canonical_horse_name"]
                ),
                "historical_rating_value": (
                    historical_rating_value
                ),
                "context_parameter_id": (
                    context_parameter_id
                ),
                "total_context_adjustment": (
                    total_adjustment_value
                ),
                "context_adjusted_performance_value": (
                    adjusted_value
                ),
                "source_adjustment_decision": (
                    source_decision
                ),
                "context_adjusted_performance_decision": (
                    output_decision
                ),
                "race_entry_context_adjusted_performance_status": (
                    output_status
                ),
                "source_adjustment_evidence_sha256": (
                    source_evidence
                ),
                "race_entry_context_adjusted_performance_evidence_sha256": (
                    evidence_hash
                ),
                "source_adjustment_builder_version": (
                    source_builder
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(row["race_date"]),
            text(row["race_id"]),
            text(row["race_entry_id"]),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ENTRY_CONTEXT_ADJUSTED_PERFORMANCE_FACT_V1_BUILD_PASS"
    )
    print(
        f"context_adjustment_rows={len(source_rows)}"
    )
    print(
        f"performance_adjusted_rows={adjusted_count}"
    )
    print(
        f"parameter_not_available_rows={unavailable_count}"
    )
    print(
        f"context_ineligible_rows={ineligible_count}"
    )
    print(
        f"context_adjusted_performance_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
