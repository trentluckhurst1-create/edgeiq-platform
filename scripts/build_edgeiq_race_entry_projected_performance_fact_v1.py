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

ADJUSTED_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv"
)

AGGREGATE_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_aggregate_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_projected_performance_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_projected_performance_fact_v1.0.0"
)

PUBLICATION_DECISION = (
    "PROJECTED_PERFORMANCE_PUBLISHED"
)

RECONCILIATION_DECISION = (
    "PROJECTED_PERFORMANCE_RECONCILED"
)

PROJECTED_STATUS = (
    "GOVERNED_PROJECTED_PERFORMANCE"
)

EXPECTED_ADJUSTED_DECISION = (
    "PERFORMANCE_ADJUSTED"
)

EXPECTED_ADJUSTED_STATUS = (
    "GOVERNED_CONTEXT_ADJUSTED_PERFORMANCE"
)

EXPECTED_AGGREGATE_DECISION = (
    "SUITABILITY_AGGREGATED"
)

EXPECTED_AGGREGATE_STATUS = (
    "GOVERNED_SUITABILITY_AGGREGATE"
)

IDENTITY_FIELDS = [
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
]

OUTPUT_FIELDS = [
    "race_entry_projected_performance_id",
    "race_entry_suitability_aggregate_id",
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
    "aggregate_suitability_value",
    "context_adjusted_performance_value",
    "projected_performance_value",
    "projected_performance_delta_from_historical",
    "projected_performance_publication_decision",
    "projected_performance_reconciliation_decision",
    "race_entry_projected_performance_status",
    "source_adjusted_performance_evidence_sha256",
    "source_suitability_aggregate_evidence_sha256",
    "race_entry_projected_performance_evidence_sha256",
    "source_adjusted_performance_builder_version",
    "source_suitability_aggregate_builder_version",
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
    path: Path,
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
            f"{path.name} missing required fields: {missing}"
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
    aggregate_fields, aggregate_rows = read_csv(
        AGGREGATE_PATH
    )

    require_fields(
        AGGREGATE_PATH,
        aggregate_fields,
        [
            "race_entry_suitability_aggregate_id",
            "race_entry_context_adjusted_performance_id",
            *IDENTITY_FIELDS,
            "aggregate_suitability_value",
            "suitability_aggregate_decision",
            "race_entry_suitability_aggregate_status",
            "race_entry_suitability_aggregate_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )

    if not aggregate_rows:
        atomic_write_csv(
            OUTPUT_PATH,
            [],
        )

        print(
            "EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_BUILD_PASS"
        )
        print("suitability_aggregate_rows=0")
        print("context_adjusted_performance_rows=NOT_REQUIRED")
        print("projected_performance_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    adjusted_fields, adjusted_rows = read_csv(
        ADJUSTED_PATH
    )

    require_fields(
        ADJUSTED_PATH,
        adjusted_fields,
        [
            "race_entry_context_adjusted_performance_id",
            *IDENTITY_FIELDS,
            "context_adjusted_performance_decision",
            "race_entry_context_adjusted_performance_status",
            "race_entry_context_adjusted_performance_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )

    adjusted_by_id: dict[str, dict[str, str]] = {}

    for row in adjusted_rows:
        adjusted_id = text(
            row[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        if not adjusted_id:
            fail(
                "Blank context-adjusted performance ID."
            )

        if adjusted_id in adjusted_by_id:
            fail(
                f"Duplicate context-adjusted performance ID: "
                f"{adjusted_id}"
            )

        adjusted_by_id[adjusted_id] = row

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []

    seen_aggregate_ids: set[str] = set()
    seen_projected_ids: set[str] = set()

    for aggregate in aggregate_rows:
        aggregate_id = text(
            aggregate[
                "race_entry_suitability_aggregate_id"
            ]
        )

        adjusted_id = text(
            aggregate[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        if not aggregate_id:
            fail(
                "Blank suitability aggregate ID."
            )

        if aggregate_id in seen_aggregate_ids:
            fail(
                f"Duplicate suitability aggregate ID: "
                f"{aggregate_id}"
            )

        seen_aggregate_ids.add(
            aggregate_id
        )

        adjusted = adjusted_by_id.get(
            adjusted_id
        )

        if adjusted is None:
            fail(
                f"{aggregate_id}: missing adjusted-performance "
                f"source {adjusted_id}."
            )

        if text(
            aggregate[
                "suitability_aggregate_decision"
            ]
        ) != EXPECTED_AGGREGATE_DECISION:
            fail(
                f"{aggregate_id}: unsupported aggregate "
                "decision."
            )

        if text(
            aggregate[
                "race_entry_suitability_aggregate_status"
            ]
        ) != EXPECTED_AGGREGATE_STATUS:
            fail(
                f"{aggregate_id}: unsupported aggregate "
                "status."
            )

        if text(
            adjusted[
                "context_adjusted_performance_decision"
            ]
        ) != EXPECTED_ADJUSTED_DECISION:
            fail(
                f"{aggregate_id}: adjusted-performance source "
                "is not eligible."
            )

        if text(
            adjusted[
                "race_entry_context_adjusted_performance_status"
            ]
        ) != EXPECTED_ADJUSTED_STATUS:
            fail(
                f"{aggregate_id}: adjusted-performance source "
                "status is not governed."
            )

        for field_name in IDENTITY_FIELDS:
            if text(
                aggregate[field_name]
            ) != text(
                adjusted[field_name]
            ):
                fail(
                    f"{aggregate_id}: source mismatch for "
                    f"{field_name}."
                )

        historical_rating = parse_required_decimal(
            aggregate[
                "historical_rating_value"
            ],
            "historical_rating_value",
        )

        aggregate_suitability = parse_required_decimal(
            aggregate[
                "aggregate_suitability_value"
            ],
            "aggregate_suitability_value",
        )

        total_context_adjustment = (
            parse_required_decimal(
                aggregate[
                    "total_context_adjustment"
                ],
                "total_context_adjustment",
            )
        )

        context_adjusted_performance = (
            parse_required_decimal(
                aggregate[
                    "context_adjusted_performance_value"
                ],
                "context_adjusted_performance_value",
            )
        )

        if (
            aggregate_suitability
            != total_context_adjustment
        ):
            fail(
                f"{aggregate_id}: aggregate suitability "
                "does not reconcile to total context "
                "adjustment."
            )

        projected_performance = (
            historical_rating
            + aggregate_suitability
        )

        if (
            projected_performance
            != context_adjusted_performance
        ):
            fail(
                f"{aggregate_id}: projected performance "
                "does not reconcile to context-adjusted "
                "performance."
            )

        adjusted_evidence = text(
            adjusted[
                "race_entry_context_adjusted_performance_evidence_sha256"
            ]
        )

        aggregate_evidence = text(
            aggregate[
                "race_entry_suitability_aggregate_evidence_sha256"
            ]
        )

        adjusted_builder = text(
            adjusted[
                "builder_version"
            ]
        )

        aggregate_builder = text(
            aggregate[
                "builder_version"
            ]
        )

        if (
            not adjusted_evidence
            or not aggregate_evidence
            or not adjusted_builder
            or not aggregate_builder
        ):
            fail(
                f"{aggregate_id}: incomplete source lineage."
            )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                aggregate_id,
                PUBLICATION_DECISION,
            ]
        )

        projected_id = (
            f"REPP1-"
            f"{identity_hash[:24].upper()}"
        )

        if projected_id in seen_projected_ids:
            fail(
                f"Duplicate deterministic projected "
                f"performance ID: {projected_id}"
            )

        seen_projected_ids.add(
            projected_id
        )

        historical_text = decimal_text(
            historical_rating
        )

        aggregate_text = decimal_text(
            aggregate_suitability
        )

        total_adjustment_text = decimal_text(
            total_context_adjustment
        )

        context_adjusted_text = decimal_text(
            context_adjusted_performance
        )

        projected_text = decimal_text(
            projected_performance
        )

        projected_delta_text = decimal_text(
            projected_performance
            - historical_rating
        )

        evidence_hash = sha256_payload(
            [
                projected_id,
                adjusted_evidence,
                aggregate_evidence,
                historical_text,
                aggregate_text,
                total_adjustment_text,
                context_adjusted_text,
                projected_text,
                PUBLICATION_DECISION,
                RECONCILIATION_DECISION,
                PROJECTED_STATUS,
            ]
        )

        output_rows.append(
            {
                "race_entry_projected_performance_id": (
                    projected_id
                ),
                "race_entry_suitability_aggregate_id": (
                    aggregate_id
                ),
                "race_entry_context_adjusted_performance_id": (
                    adjusted_id
                ),
                "race_entry_context_adjustment_id": text(
                    aggregate[
                        "race_entry_context_adjustment_id"
                    ]
                ),
                "race_entry_context_parameter_selection_id": text(
                    aggregate[
                        "race_entry_context_parameter_selection_id"
                    ]
                ),
                "race_entry_context_eligibility_id": text(
                    aggregate[
                        "race_entry_context_eligibility_id"
                    ]
                ),
                "race_entry_performance_context_id": text(
                    aggregate[
                        "race_entry_performance_context_id"
                    ]
                ),
                "race_entry_id": text(
                    aggregate[
                        "race_entry_id"
                    ]
                ),
                "race_id": text(
                    aggregate[
                        "race_id"
                    ]
                ),
                "race_date": text(
                    aggregate[
                        "race_date"
                    ]
                ),
                "runner_id": text(
                    aggregate[
                        "runner_id"
                    ]
                ),
                "canonical_horse_id": text(
                    aggregate[
                        "canonical_horse_id"
                    ]
                ),
                "canonical_horse_name": text(
                    aggregate[
                        "canonical_horse_name"
                    ]
                ),
                "historical_rating_value": (
                    historical_text
                ),
                "context_parameter_id": text(
                    aggregate[
                        "context_parameter_id"
                    ]
                ),
                "total_context_adjustment": (
                    total_adjustment_text
                ),
                "aggregate_suitability_value": (
                    aggregate_text
                ),
                "context_adjusted_performance_value": (
                    context_adjusted_text
                ),
                "projected_performance_value": (
                    projected_text
                ),
                "projected_performance_delta_from_historical": (
                    projected_delta_text
                ),
                "projected_performance_publication_decision": (
                    PUBLICATION_DECISION
                ),
                "projected_performance_reconciliation_decision": (
                    RECONCILIATION_DECISION
                ),
                "race_entry_projected_performance_status": (
                    PROJECTED_STATUS
                ),
                "source_adjusted_performance_evidence_sha256": (
                    adjusted_evidence
                ),
                "source_suitability_aggregate_evidence_sha256": (
                    aggregate_evidence
                ),
                "race_entry_projected_performance_evidence_sha256": (
                    evidence_hash
                ),
                "source_adjusted_performance_builder_version": (
                    adjusted_builder
                ),
                "source_suitability_aggregate_builder_version": (
                    aggregate_builder
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
        "EDGEIQ_RACE_ENTRY_PROJECTED_PERFORMANCE_FACT_V1_BUILD_PASS"
    )
    print(
        f"suitability_aggregate_rows={len(aggregate_rows)}"
    )
    print(
        f"context_adjusted_performance_rows={len(adjusted_rows)}"
    )
    print(
        f"projected_performance_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
