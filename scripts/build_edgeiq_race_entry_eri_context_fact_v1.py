from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTED_PATH = (
    DATA
    / "edgeiq_race_entry_projected_performance_fact_v1.csv"
)

ERI_PATH = (
    DATA
    / "edgeiq_race_eri_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_eri_context_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_race_entry_eri_context_fact_v1.0.0"

DECIMAL_PLACES = 6
ROUNDING_MODE = "ROUND_HALF_EVEN"

EXPECTED_PROJECTED_PUBLICATION = (
    "PROJECTED_PERFORMANCE_PUBLISHED"
)

EXPECTED_PROJECTED_RECONCILIATION = (
    "PROJECTED_PERFORMANCE_RECONCILED"
)

EXPECTED_PROJECTED_STATUS = (
    "GOVERNED_PROJECTED_PERFORMANCE"
)

EXPECTED_ERI_PUBLICATION = "ERI_PUBLISHED"
EXPECTED_ERI_RECONCILIATION = "ERI_METHOD_RECONCILED"
EXPECTED_ERI_STATUS = "GOVERNED_RACE_ERI"

CONTEXT_PUBLICATION = "ERI_CONTEXT_PUBLISHED"
CONTEXT_RECONCILIATION = "ERI_CONTEXT_RECONCILED"
CONTEXT_STATUS = "GOVERNED_RACE_ENTRY_ERI_CONTEXT"

OUTPUT_FIELDS = [
    "race_entry_eri_context_id",
    "race_entry_projected_performance_id",
    "race_eri_id",
    "race_eri_parameter_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "projected_performance_value",
    "eri_value",
    "projected_performance_vs_eri",
    "context_output_decimal_places",
    "context_rounding_mode",
    "eri_context_publication_decision",
    "eri_context_reconciliation_decision",
    "race_entry_eri_context_status",
    "source_projected_performance_evidence_sha256",
    "source_race_eri_evidence_sha256",
    "source_eri_parameter_evidence_sha256",
    "race_entry_eri_context_evidence_sha256",
    "source_projected_performance_builder_version",
    "source_race_eri_builder_version",
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


def parse_decimal(
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


def governed_decimal_text(
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
    actual_fields: list[str],
    required_fields: Iterable[str],
) -> None:
    missing = [
        field
        for field in required_fields
        if field not in actual_fields
    ]

    if missing:
        fail(
            f"{path.name} missing required fields: {missing}"
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
    projected_fields, projected_rows = read_csv(
        PROJECTED_PATH
    )

    eri_fields, eri_rows = read_csv(
        ERI_PATH
    )

    require_fields(
        PROJECTED_PATH,
        projected_fields,
        [
            "race_entry_projected_performance_id",
            "race_entry_id",
            "race_id",
            "race_date",
            "projected_performance_value",
            "projected_performance_publication_decision",
            "projected_performance_reconciliation_decision",
            "race_entry_projected_performance_status",
            "race_entry_projected_performance_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )

    require_fields(
        ERI_PATH,
        eri_fields,
        [
            "race_eri_id",
            "race_eri_parameter_id",
            "race_id",
            "race_date",
            "eri_value",
            "eri_output_decimal_places",
            "eri_rounding_mode",
            "eri_publication_decision",
            "eri_method_reconciliation_decision",
            "race_eri_status",
            "source_eri_parameter_evidence_sha256",
            "race_eri_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )

    projected_id_counts = Counter(
        text(
            row[
                "race_entry_projected_performance_id"
            ]
        )
        for row in projected_rows
    )

    duplicate_projected_ids = sorted(
        value
        for value, count in projected_id_counts.items()
        if value and count != 1
    )

    if duplicate_projected_ids:
        fail(
            "Duplicate projected-performance IDs: "
            f"{duplicate_projected_ids[:20]}"
        )

    eri_id_counts = Counter(
        text(
            row[
                "race_eri_id"
            ]
        )
        for row in eri_rows
    )

    duplicate_eri_ids = sorted(
        value
        for value, count in eri_id_counts.items()
        if value and count != 1
    )

    if duplicate_eri_ids:
        fail(
            f"Duplicate Race ERI IDs: {duplicate_eri_ids[:20]}"
        )

    eri_key_counts = Counter(
        (
            text(
                row[
                    "race_id"
                ]
            ),
            text(
                row[
                    "race_date"
                ]
            ),
        )
        for row in eri_rows
    )

    duplicate_eri_keys = sorted(
        key
        for key, count in eri_key_counts.items()
        if count != 1
    )

    if duplicate_eri_keys:
        fail(
            f"Duplicate Race ERI join keys: {duplicate_eri_keys[:20]}"
        )

    eri_by_key: dict[
        tuple[str, str],
        dict[str, str]
    ] = {}

    for row in eri_rows:
        eri_id = text(
            row[
                "race_eri_id"
            ]
        )

        race_id = text(
            row[
                "race_id"
            ]
        )

        race_date = text(
            row[
                "race_date"
            ]
        )

        if not eri_id or not race_id or not race_date:
            fail(
                "Race ERI row has blank identity or join key."
            )

        if text(
            row[
                "eri_publication_decision"
            ]
        ) != EXPECTED_ERI_PUBLICATION:
            fail(
                f"{eri_id}: unsupported ERI publication state."
            )

        if text(
            row[
                "eri_method_reconciliation_decision"
            ]
        ) != EXPECTED_ERI_RECONCILIATION:
            fail(
                f"{eri_id}: unsupported ERI reconciliation state."
            )

        if text(
            row[
                "race_eri_status"
            ]
        ) != EXPECTED_ERI_STATUS:
            fail(
                f"{eri_id}: unsupported ERI status."
            )

        if text(
            row[
                "eri_rounding_mode"
            ]
        ) != ROUNDING_MODE:
            fail(
                f"{eri_id}: unsupported ERI rounding mode."
            )

        if text(
            row[
                "eri_output_decimal_places"
            ]
        ) != str(
            DECIMAL_PLACES
        ):
            fail(
                f"{eri_id}: unsupported ERI decimal scale."
            )

        parse_decimal(
            row[
                "eri_value"
            ],
            "eri_value",
        )

        required_eri_lineage = [
            "race_eri_parameter_id",
            "source_eri_parameter_evidence_sha256",
            "race_eri_evidence_sha256",
            "builder_version",
            "contract_version",
        ]

        for field_name in required_eri_lineage:
            if not text(
                row[field_name]
            ):
                fail(
                    f"{eri_id}: missing {field_name}."
                )

        eri_by_key[
            (
                race_id,
                race_date,
            )
        ] = row

    projected_races: dict[
        tuple[str, str],
        int
    ] = defaultdict(int)

    output_rows: list[dict[str, str]] = []
    seen_context_ids: set[str] = set()

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    for projected in projected_rows:
        projected_id = text(
            projected[
                "race_entry_projected_performance_id"
            ]
        )

        race_entry_id = text(
            projected[
                "race_entry_id"
            ]
        )

        race_id = text(
            projected[
                "race_id"
            ]
        )

        race_date = text(
            projected[
                "race_date"
            ]
        )

        if (
            not projected_id
            or not race_entry_id
            or not race_id
            or not race_date
        ):
            fail(
                "Projected-performance row has blank identity "
                "or join key."
            )

        if text(
            projected[
                "projected_performance_publication_decision"
            ]
        ) != EXPECTED_PROJECTED_PUBLICATION:
            fail(
                f"{projected_id}: unsupported publication state."
            )

        if text(
            projected[
                "projected_performance_reconciliation_decision"
            ]
        ) != EXPECTED_PROJECTED_RECONCILIATION:
            fail(
                f"{projected_id}: unsupported reconciliation state."
            )

        if text(
            projected[
                "race_entry_projected_performance_status"
            ]
        ) != EXPECTED_PROJECTED_STATUS:
            fail(
                f"{projected_id}: unsupported status."
            )

        projected_evidence = text(
            projected[
                "race_entry_projected_performance_evidence_sha256"
            ]
        )

        projected_builder = text(
            projected[
                "builder_version"
            ]
        )

        if not projected_evidence or not projected_builder:
            fail(
                f"{projected_id}: incomplete projected-performance "
                "lineage."
            )

        join_key = (
            race_id,
            race_date,
        )

        eri = eri_by_key.get(
            join_key
        )

        if eri is None:
            fail(
                f"{projected_id}: no matching Race ERI for "
                f"{race_id} on {race_date}."
            )

        projected_races[
            join_key
        ] += 1

        projected_value = parse_decimal(
            projected[
                "projected_performance_value"
            ],
            "projected_performance_value",
        )

        eri_value = parse_decimal(
            eri[
                "eri_value"
            ],
            "eri_value",
        )

        context_value = (
            projected_value
            - eri_value
        )

        projected_value_text = governed_decimal_text(
            projected_value
        )

        eri_value_text = governed_decimal_text(
            eri_value
        )

        context_value_text = governed_decimal_text(
            context_value
        )

        race_eri_id = text(
            eri[
                "race_eri_id"
            ]
        )

        race_eri_parameter_id = text(
            eri[
                "race_eri_parameter_id"
            ]
        )

        eri_evidence = text(
            eri[
                "race_eri_evidence_sha256"
            ]
        )

        parameter_evidence = text(
            eri[
                "source_eri_parameter_evidence_sha256"
            ]
        )

        eri_builder = text(
            eri[
                "builder_version"
            ]
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                projected_id,
                race_eri_id,
                CONTEXT_PUBLICATION,
            ]
        )

        context_id = (
            f"ERIC1-{identity_hash[:24].upper()}"
        )

        if context_id in seen_context_ids:
            fail(
                f"Duplicate deterministic context ID: {context_id}"
            )

        seen_context_ids.add(
            context_id
        )

        evidence_hash = sha256_payload(
            [
                context_id,
                projected_id,
                projected_evidence,
                race_eri_id,
                race_eri_parameter_id,
                eri_evidence,
                race_entry_id,
                race_id,
                race_date,
                projected_value_text,
                eri_value_text,
                context_value_text,
                CONTEXT_PUBLICATION,
                CONTEXT_RECONCILIATION,
                CONTEXT_STATUS,
            ]
        )

        output_rows.append(
            {
                "race_entry_eri_context_id": context_id,
                "race_entry_projected_performance_id": (
                    projected_id
                ),
                "race_eri_id": race_eri_id,
                "race_eri_parameter_id": race_eri_parameter_id,
                "race_entry_id": race_entry_id,
                "race_id": race_id,
                "race_date": race_date,
                "projected_performance_value": (
                    projected_value_text
                ),
                "eri_value": eri_value_text,
                "projected_performance_vs_eri": (
                    context_value_text
                ),
                "context_output_decimal_places": str(
                    DECIMAL_PLACES
                ),
                "context_rounding_mode": ROUNDING_MODE,
                "eri_context_publication_decision": (
                    CONTEXT_PUBLICATION
                ),
                "eri_context_reconciliation_decision": (
                    CONTEXT_RECONCILIATION
                ),
                "race_entry_eri_context_status": (
                    CONTEXT_STATUS
                ),
                "source_projected_performance_evidence_sha256": (
                    projected_evidence
                ),
                "source_race_eri_evidence_sha256": (
                    eri_evidence
                ),
                "source_eri_parameter_evidence_sha256": (
                    parameter_evidence
                ),
                "race_entry_eri_context_evidence_sha256": (
                    evidence_hash
                ),
                "source_projected_performance_builder_version": (
                    projected_builder
                ),
                "source_race_eri_builder_version": (
                    eri_builder
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    orphan_eri_keys = sorted(
        key
        for key in eri_by_key
        if projected_races.get(
            key,
            0,
        ) == 0
    )

    if orphan_eri_keys:
        fail(
            "Race ERI rows without projected-performance rows: "
            f"{orphan_eri_keys[:20]}"
        )

    output_rows.sort(
        key=lambda row: (
            row[
                "race_date"
            ],
            row[
                "race_id"
            ],
            row[
                "race_entry_id"
            ],
            row[
                "race_entry_projected_performance_id"
            ],
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ENTRY_ERI_CONTEXT_FACT_V1_BUILD_PASS"
    )
    print(
        f"projected_performance_rows={len(projected_rows)}"
    )
    print(
        f"race_eri_rows={len(eri_rows)}"
    )
    print(
        f"race_entry_eri_context_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
