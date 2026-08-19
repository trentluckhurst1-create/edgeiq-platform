from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from collections import defaultdict
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

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_eri_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_race_eri_fact_v1.0.0"

EXPECTED_PROJECTED_PUBLICATION = (
    "PROJECTED_PERFORMANCE_PUBLISHED"
)

EXPECTED_PROJECTED_RECONCILIATION = (
    "PROJECTED_PERFORMANCE_RECONCILED"
)

EXPECTED_PROJECTED_STATUS = (
    "GOVERNED_PROJECTED_PERFORMANCE"
)

EXPECTED_PARAMETER_METHODOLOGY = (
    "FIELD_MEAN_PROJECTED_PERFORMANCE"
)

EXPECTED_PARAMETER_SCOPE = "GLOBAL"
EXPECTED_PARAMETER_DECISION = "ERI_PARAMETER_AUTHORISED"
EXPECTED_PARAMETER_STATUS = "GOVERNED_ERI_PARAMETER"
EXPECTED_ROUNDING_MODE = "ROUND_HALF_EVEN"

ERI_PUBLICATION_DECISION = "ERI_PUBLISHED"
ERI_RECONCILIATION_DECISION = "ERI_METHOD_RECONCILED"
ERI_STATUS = "GOVERNED_RACE_ERI"

OUTPUT_FIELDS = [
    "race_eri_id",
    "race_eri_parameter_id",
    "eri_parameter_version",
    "race_id",
    "race_date",
    "eligible_runner_count",
    "projected_performance_sum",
    "projected_performance_mean_unrounded",
    "projected_performance_mean",
    "projected_performance_median",
    "projected_performance_minimum",
    "projected_performance_maximum",
    "projected_performance_range",
    "eri_value",
    "eri_methodology_code",
    "eri_output_decimal_places",
    "eri_rounding_mode",
    "eri_publication_decision",
    "eri_method_reconciliation_decision",
    "race_eri_status",
    "source_projected_performance_id_set_sha256",
    "source_projected_performance_evidence_set_sha256",
    "source_eri_parameter_evidence_sha256",
    "race_eri_evidence_sha256",
    "source_projected_performance_builder_version_set",
    "source_eri_parameter_builder_version",
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


def parse_required_date(
    value: object,
    field_name: str,
) -> date:
    raw = text(value)

    if not raw:
        fail(
            f"Blank required date: {field_name}"
        )

    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid date {field_name}: {raw!r}"
        ) from exc


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


def select_parameter(
    race_date: date,
    parameter_rows: list[dict[str, str]],
) -> dict[str, str]:
    active: list[dict[str, str]] = []

    for row in parameter_rows:
        effective_from = parse_required_date(
            row["effective_from_date"],
            "effective_from_date",
        )

        effective_to_raw = text(
            row["effective_to_date"]
        )

        effective_to = (
            parse_required_date(
                effective_to_raw,
                "effective_to_date",
            )
            if effective_to_raw
            else None
        )

        if race_date < effective_from:
            continue

        if (
            effective_to is not None
            and race_date > effective_to
        ):
            continue

        active.append(row)

    if len(active) != 1:
        fail(
            f"Race date {race_date.isoformat()} resolved "
            f"{len(active)} active ERI parameters; expected 1."
        )

    selected = active[0]

    if text(
        selected[
            "eri_methodology_code"
        ]
    ) != EXPECTED_PARAMETER_METHODOLOGY:
        fail(
            "Unsupported ERI methodology."
        )

    if text(
        selected[
            "eri_parameter_scope"
        ]
    ) != EXPECTED_PARAMETER_SCOPE:
        fail(
            "Unsupported ERI parameter scope."
        )

    if text(
        selected[
            "eri_parameter_decision"
        ]
    ) != EXPECTED_PARAMETER_DECISION:
        fail(
            "ERI parameter is not authorised."
        )

    if text(
        selected[
            "race_eri_parameter_status"
        ]
    ) != EXPECTED_PARAMETER_STATUS:
        fail(
            "ERI parameter status is not governed."
        )

    if text(
        selected[
            "eri_rounding_mode"
        ]
    ) != EXPECTED_ROUNDING_MODE:
        fail(
            "Unsupported ERI rounding mode."
        )

    return selected


def main() -> None:
    projected_fields, projected_rows = read_csv(
        PROJECTED_PATH
    )

    parameter_fields, parameter_rows = read_csv(
        PARAMETER_PATH
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
        PARAMETER_PATH,
        parameter_fields,
        [
            "race_eri_parameter_id",
            "eri_parameter_version",
            "eri_methodology_code",
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
        ],
    )

    if not parameter_rows:
        fail(
            "No governed ERI parameter rows available."
        )

    seen_parameter_ids: set[str] = set()
    seen_parameter_versions: set[str] = set()

    for parameter in parameter_rows:
        parameter_id = text(
            parameter[
                "race_eri_parameter_id"
            ]
        )

        parameter_version = text(
            parameter[
                "eri_parameter_version"
            ]
        )

        if not parameter_id:
            fail(
                "Blank ERI parameter ID."
            )

        if not parameter_version:
            fail(
                "Blank ERI parameter version."
            )

        if parameter_id in seen_parameter_ids:
            fail(
                f"Duplicate ERI parameter ID: {parameter_id}"
            )

        if parameter_version in seen_parameter_versions:
            fail(
                "Duplicate ERI parameter version: "
                f"{parameter_version}"
            )

        seen_parameter_ids.add(
            parameter_id
        )

        seen_parameter_versions.add(
            parameter_version
        )

    grouped_rows: dict[
        str,
        list[dict[str, str]]
    ] = defaultdict(list)

    seen_projected_ids: set[str] = set()

    for row in projected_rows:
        projected_id = text(
            row[
                "race_entry_projected_performance_id"
            ]
        )

        race_id = text(
            row[
                "race_id"
            ]
        )

        if not projected_id:
            fail(
                "Blank projected-performance ID."
            )

        if projected_id in seen_projected_ids:
            fail(
                "Duplicate projected-performance ID: "
                f"{projected_id}"
            )

        seen_projected_ids.add(
            projected_id
        )

        if not race_id:
            fail(
                f"{projected_id}: blank race ID."
            )

        if text(
            row[
                "projected_performance_publication_decision"
            ]
        ) != EXPECTED_PROJECTED_PUBLICATION:
            fail(
                f"{projected_id}: unsupported publication "
                "decision."
            )

        if text(
            row[
                "projected_performance_reconciliation_decision"
            ]
        ) != EXPECTED_PROJECTED_RECONCILIATION:
            fail(
                f"{projected_id}: unsupported reconciliation "
                "decision."
            )

        if text(
            row[
                "race_entry_projected_performance_status"
            ]
        ) != EXPECTED_PROJECTED_STATUS:
            fail(
                f"{projected_id}: unsupported projected "
                "performance status."
            )

        parse_required_date(
            row["race_date"],
            "race_date",
        )

        parse_required_decimal(
            row[
                "projected_performance_value"
            ],
            "projected_performance_value",
        )

        if not text(
            row[
                "race_entry_projected_performance_evidence_sha256"
            ]
        ):
            fail(
                f"{projected_id}: missing evidence SHA-256."
            )

        if not text(
            row[
                "builder_version"
            ]
        ):
            fail(
                f"{projected_id}: missing builder lineage."
            )

        grouped_rows[race_id].append(
            row
        )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []
    below_minimum_race_count = 0
    seen_eri_ids: set[str] = set()

    for race_id in sorted(grouped_rows):
        race_rows = grouped_rows[
            race_id
        ]

        race_dates = {
            text(
                row[
                    "race_date"
                ]
            )
            for row in race_rows
        }

        if len(race_dates) != 1:
            fail(
                f"{race_id}: conflicting race dates."
            )

        race_date_text = next(
            iter(race_dates)
        )

        race_date_value = parse_required_date(
            race_date_text,
            "race_date",
        )

        selected_parameter = select_parameter(
            race_date_value,
            parameter_rows,
        )

        parameter_id = text(
            selected_parameter[
                "race_eri_parameter_id"
            ]
        )

        parameter_version = text(
            selected_parameter[
                "eri_parameter_version"
            ]
        )

        parameter_evidence = text(
            selected_parameter[
                "race_eri_parameter_evidence_sha256"
            ]
        )

        parameter_builder = text(
            selected_parameter[
                "builder_version"
            ]
        )

        if (
            not parameter_evidence
            or not parameter_builder
        ):
            fail(
                f"{race_id}: incomplete ERI parameter lineage."
            )

        try:
            minimum_runner_count = int(
                text(
                    selected_parameter[
                        "minimum_eligible_runner_count"
                    ]
                )
            )

            decimal_places = int(
                text(
                    selected_parameter[
                        "eri_output_decimal_places"
                    ]
                )
            )
        except ValueError as exc:
            raise RuntimeError(
                f"{race_id}: invalid ERI parameter integers."
            ) from exc

        if minimum_runner_count < 2:
            fail(
                f"{race_id}: governed minimum runner count "
                "must be at least 2."
            )

        if decimal_places < 0:
            fail(
                f"{race_id}: decimal places cannot be negative."
            )

        race_entry_ids: set[str] = set()
        projected_ids: list[str] = []
        projected_evidence: list[str] = []
        projected_builder_versions: set[str] = set()
        projected_values: list[Decimal] = []

        for row in race_rows:
            projected_id = text(
                row[
                    "race_entry_projected_performance_id"
                ]
            )

            race_entry_id = text(
                row[
                    "race_entry_id"
                ]
            )

            if not race_entry_id:
                fail(
                    f"{projected_id}: blank race-entry ID."
                )

            if race_entry_id in race_entry_ids:
                fail(
                    f"{race_id}: duplicate race-entry ID "
                    f"{race_entry_id}."
                )

            race_entry_ids.add(
                race_entry_id
            )

            projected_ids.append(
                projected_id
            )

            projected_evidence.append(
                text(
                    row[
                        "race_entry_projected_performance_evidence_sha256"
                    ]
                )
            )

            projected_builder_versions.add(
                text(
                    row[
                        "builder_version"
                    ]
                )
            )

            projected_values.append(
                parse_required_decimal(
                    row[
                        "projected_performance_value"
                    ],
                    "projected_performance_value",
                )
            )

        eligible_runner_count = len(
            projected_values
        )

        if (
            eligible_runner_count
            < minimum_runner_count
        ):
            below_minimum_race_count += 1
            continue

        projected_sum = sum(
            projected_values,
            Decimal(0),
        )

        projected_mean_unrounded = (
            projected_sum
            / Decimal(
                eligible_runner_count
            )
        )

        projected_median = median_decimal(
            projected_values
        )

        projected_minimum = min(
            projected_values
        )

        projected_maximum = max(
            projected_values
        )

        projected_range = (
            projected_maximum
            - projected_minimum
        )

        projected_sum_text = decimal_text(
            projected_sum
        )

        projected_mean_unrounded_text = (
            decimal_text(
                projected_mean_unrounded
            )
        )

        projected_mean_text = (
            governed_decimal_text(
                projected_mean_unrounded,
                decimal_places,
            )
        )

        projected_median_text = (
            governed_decimal_text(
                projected_median,
                decimal_places,
            )
        )

        projected_minimum_text = (
            governed_decimal_text(
                projected_minimum,
                decimal_places,
            )
        )

        projected_maximum_text = (
            governed_decimal_text(
                projected_maximum,
                decimal_places,
            )
        )

        projected_range_text = (
            governed_decimal_text(
                projected_range,
                decimal_places,
            )
        )

        eri_value_text = projected_mean_text

        projected_id_set_hash = sha256_payload(
            sorted(
                projected_ids
            )
        )

        projected_evidence_set_hash = sha256_payload(
            sorted(
                projected_evidence
            )
        )

        projected_builder_version_set = "|".join(
            sorted(
                projected_builder_versions
            )
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                race_id,
                race_date_text,
                parameter_id,
                ERI_PUBLICATION_DECISION,
            ]
        )

        race_eri_id = (
            f"ERI1-{identity_hash[:24].upper()}"
        )

        if race_eri_id in seen_eri_ids:
            fail(
                f"Duplicate deterministic ERI ID: "
                f"{race_eri_id}"
            )

        seen_eri_ids.add(
            race_eri_id
        )

        evidence_hash = sha256_payload(
            [
                race_eri_id,
                race_id,
                race_date_text,
                parameter_id,
                parameter_version,
                parameter_evidence,
                projected_id_set_hash,
                projected_evidence_set_hash,
                eligible_runner_count,
                projected_sum_text,
                projected_mean_unrounded_text,
                projected_mean_text,
                projected_median_text,
                projected_minimum_text,
                projected_maximum_text,
                projected_range_text,
                eri_value_text,
                EXPECTED_PARAMETER_METHODOLOGY,
                ERI_PUBLICATION_DECISION,
                ERI_RECONCILIATION_DECISION,
                ERI_STATUS,
            ]
        )

        output_rows.append(
            {
                "race_eri_id": race_eri_id,
                "race_eri_parameter_id": parameter_id,
                "eri_parameter_version": parameter_version,
                "race_id": race_id,
                "race_date": race_date_text,
                "eligible_runner_count": (
                    str(
                        eligible_runner_count
                    )
                ),
                "projected_performance_sum": (
                    projected_sum_text
                ),
                "projected_performance_mean_unrounded": (
                    projected_mean_unrounded_text
                ),
                "projected_performance_mean": (
                    projected_mean_text
                ),
                "projected_performance_median": (
                    projected_median_text
                ),
                "projected_performance_minimum": (
                    projected_minimum_text
                ),
                "projected_performance_maximum": (
                    projected_maximum_text
                ),
                "projected_performance_range": (
                    projected_range_text
                ),
                "eri_value": eri_value_text,
                "eri_methodology_code": (
                    EXPECTED_PARAMETER_METHODOLOGY
                ),
                "eri_output_decimal_places": (
                    str(
                        decimal_places
                    )
                ),
                "eri_rounding_mode": (
                    EXPECTED_ROUNDING_MODE
                ),
                "eri_publication_decision": (
                    ERI_PUBLICATION_DECISION
                ),
                "eri_method_reconciliation_decision": (
                    ERI_RECONCILIATION_DECISION
                ),
                "race_eri_status": ERI_STATUS,
                "source_projected_performance_id_set_sha256": (
                    projected_id_set_hash
                ),
                "source_projected_performance_evidence_set_sha256": (
                    projected_evidence_set_hash
                ),
                "source_eri_parameter_evidence_sha256": (
                    parameter_evidence
                ),
                "race_eri_evidence_sha256": (
                    evidence_hash
                ),
                "source_projected_performance_builder_version_set": (
                    projected_builder_version_set
                ),
                "source_eri_parameter_builder_version": (
                    parameter_builder
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(
                row[
                    "race_date"
                ]
            ),
            text(
                row[
                    "race_id"
                ]
            ),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ERI_FACT_V1_BUILD_PASS"
    )
    print(
        f"projected_performance_rows={len(projected_rows)}"
    )
    print(
        f"eri_parameter_rows={len(parameter_rows)}"
    )
    print(
        f"projected_race_count={len(grouped_rows)}"
    )
    print(
        "below_minimum_field_size_races="
        f"{below_minimum_race_count}"
    )
    print(
        f"race_eri_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
