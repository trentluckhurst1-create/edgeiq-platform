from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

EPI_PATH = (
    DATA
    / "edgeiq_race_entry_epi_fact_v1.csv"
)

DISTRIBUTION_PATH = (
    DATA
    / "edgeiq_race_epi_distribution_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_epi_relative_context_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_epi_relative_context_fact_v1.0.0"
)

EPI_PUBLICATION = "EPI_PUBLISHED"
EPI_RECONCILIATION = "EPI_RECONCILED"
EPI_STATUS = "GOVERNED_RACE_ENTRY_EPI"

DISTRIBUTION_PUBLICATION = (
    "RACE_EPI_DISTRIBUTION_PUBLISHED"
)

DISTRIBUTION_RECONCILIATION = (
    "RACE_EPI_DISTRIBUTION_RECONCILED"
)

DISTRIBUTION_STATUS = (
    "GOVERNED_RACE_EPI_DISTRIBUTION"
)

PUBLICATION_DECISION = (
    "EPI_RELATIVE_CONTEXT_PUBLISHED"
)

RECONCILIATION_DECISION = (
    "EPI_RELATIVE_CONTEXT_RECONCILED"
)

GOVERNED_STATUS = (
    "GOVERNED_RACE_ENTRY_EPI_RELATIVE_CONTEXT"
)

QUANTUM = Decimal("0.000001")

OUTPUT_FIELDS = [
    "race_entry_epi_relative_context_id",
    "race_entry_id",
    "race_entry_epi_id",
    "race_id",
    "race_date",
    "race_epi_distribution_id",
    "runner_epi_value",
    "eligible_epi_population_count",
    "field_epi_mean",
    "epi_minus_field_mean",
    "field_epi_population_standard_deviation",
    "epi_population_z_score",
    "minimum_epi",
    "maximum_epi",
    "epi_range",
    "distance_above_minimum_epi",
    "distance_below_maximum_epi",
    "race_entry_epi_evidence_sha256",
    "race_epi_distribution_evidence_sha256",
    "epi_relative_context_publication_decision",
    "epi_relative_context_reconciliation_decision",
    "epi_relative_context_status",
    "race_entry_epi_relative_context_evidence_sha256",
    "source_lineage",
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


def decimal_value(
    value: object,
    field_name: str,
) -> Decimal:
    raw = text(value)

    if not raw:
        raise RuntimeError(
            f"Missing decimal value: {field_name}"
        )

    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise RuntimeError(
            f"Invalid decimal value for {field_name}: {raw}"
        ) from error

    if not parsed.is_finite():
        raise RuntimeError(
            f"Non-finite decimal value for {field_name}: {raw}"
        )

    return parsed


def integer_value(
    value: object,
    field_name: str,
) -> int:
    raw = text(value)

    if not raw:
        raise RuntimeError(
            f"Missing integer value: {field_name}"
        )

    try:
        parsed = int(raw)
    except ValueError as error:
        raise RuntimeError(
            f"Invalid integer value for {field_name}: {raw}"
        ) from error

    return parsed


def decimal_text(
    value: Decimal,
) -> str:
    return format(
        value.quantize(
            QUANTUM,
            rounding=ROUND_HALF_EVEN,
        ),
        ".6f",
    )


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise RuntimeError(
            f"Required governed source does not exist: {path}"
        )

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
    epi_fields, epi_rows = read_csv(
        EPI_PATH
    )

    distribution_fields, distribution_rows = read_csv(
        DISTRIBUTION_PATH
    )

    if bool(epi_rows) != bool(distribution_rows):
        raise RuntimeError(
            "Race Entry EPI and Race EPI Distribution populations "
            "must both be empty or both be populated."
        )

    required_epi_fields = {
        "race_entry_epi_id",
        "race_entry_id",
        "race_id",
        "race_date",
        "epi_value",
        "epi_publication_decision",
        "epi_reconciliation_decision",
        "epi_status",
        "race_entry_epi_evidence_sha256",
    }

    required_distribution_fields = {
        "race_epi_distribution_id",
        "race_id",
        "race_date",
        "eligible_epi_population_count",
        "field_epi_mean",
        "field_epi_population_standard_deviation",
        "minimum_epi",
        "maximum_epi",
        "epi_range",
        "race_epi_distribution_publication_decision",
        "race_epi_distribution_reconciliation_decision",
        "race_epi_distribution_status",
        "race_epi_distribution_evidence_sha256",
    }

    missing_epi_fields = sorted(
        required_epi_fields
        - set(epi_fields)
    )

    missing_distribution_fields = sorted(
        required_distribution_fields
        - set(distribution_fields)
    )

    if missing_epi_fields:
        raise RuntimeError(
            f"Race Entry EPI source missing fields: {missing_epi_fields}"
        )

    if missing_distribution_fields:
        raise RuntimeError(
            "Race EPI Distribution source missing fields: "
            f"{missing_distribution_fields}"
        )

    distribution_by_race: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    seen_distribution_ids: set[str] = set()

    for row in distribution_rows:
        distribution_id = text(
            row.get(
                "race_epi_distribution_id"
            )
        )

        race_id = text(
            row.get(
                "race_id"
            )
        )

        race_date = text(
            row.get(
                "race_date"
            )
        )

        evidence = text(
            row.get(
                "race_epi_distribution_evidence_sha256"
            )
        )

        if not distribution_id:
            raise RuntimeError(
                "Distribution row is missing race_epi_distribution_id."
            )

        if distribution_id in seen_distribution_ids:
            raise RuntimeError(
                f"Duplicate race distribution ID: {distribution_id}"
            )

        seen_distribution_ids.add(
            distribution_id
        )

        if not race_id or not race_date:
            raise RuntimeError(
                f"Incomplete race identity for distribution {distribution_id}."
            )

        race_key = (
            race_id,
            race_date,
        )

        if race_key in distribution_by_race:
            raise RuntimeError(
                f"Duplicate distribution natural key: {race_key}"
            )

        if not evidence:
            raise RuntimeError(
                f"Missing distribution evidence: {distribution_id}"
            )

        if text(
            row.get(
                "race_epi_distribution_publication_decision"
            )
        ) != DISTRIBUTION_PUBLICATION:
            raise RuntimeError(
                f"Unpublished distribution: {distribution_id}"
            )

        if text(
            row.get(
                "race_epi_distribution_reconciliation_decision"
            )
        ) != DISTRIBUTION_RECONCILIATION:
            raise RuntimeError(
                f"Unreconciled distribution: {distribution_id}"
            )

        if text(
            row.get(
                "race_epi_distribution_status"
            )
        ) != DISTRIBUTION_STATUS:
            raise RuntimeError(
                f"Ungoverned distribution: {distribution_id}"
            )

        population_count = integer_value(
            row.get(
                "eligible_epi_population_count"
            ),
            f"{distribution_id}.eligible_epi_population_count",
        )

        if population_count < 1:
            raise RuntimeError(
                f"Invalid distribution population: {distribution_id}"
            )

        field_mean = decimal_value(
            row.get(
                "field_epi_mean"
            ),
            f"{distribution_id}.field_epi_mean",
        )

        standard_deviation = decimal_value(
            row.get(
                "field_epi_population_standard_deviation"
            ),
            f"{distribution_id}.standard_deviation",
        )

        minimum_epi = decimal_value(
            row.get(
                "minimum_epi"
            ),
            f"{distribution_id}.minimum_epi",
        )

        maximum_epi = decimal_value(
            row.get(
                "maximum_epi"
            ),
            f"{distribution_id}.maximum_epi",
        )

        epi_range = decimal_value(
            row.get(
                "epi_range"
            ),
            f"{distribution_id}.epi_range",
        )

        if standard_deviation < Decimal("0"):
            raise RuntimeError(
                f"Negative standard deviation: {distribution_id}"
            )

        if minimum_epi > maximum_epi:
            raise RuntimeError(
                f"Minimum exceeds maximum: {distribution_id}"
            )

        if epi_range < Decimal("0"):
            raise RuntimeError(
                f"Negative EPI range: {distribution_id}"
            )

        if (
            epi_range.quantize(
                QUANTUM,
                rounding=ROUND_HALF_EVEN,
            )
            != (
                maximum_epi - minimum_epi
            ).quantize(
                QUANTUM,
                rounding=ROUND_HALF_EVEN,
            )
        ):
            raise RuntimeError(
                f"Distribution range does not reconcile: {distribution_id}"
            )

        distribution_by_race[
            race_key
        ] = row

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, str]] = []

    seen_epi_ids: set[str] = set()
    seen_race_entry_ids: set[str] = set()
    joined_population_count: dict[
        tuple[str, str],
        int,
    ] = {}

    with localcontext() as context:
        context.prec = 50

        for epi_row in sorted(
            epi_rows,
            key=lambda row: (
                text(
                    row.get(
                        "race_date"
                    )
                ),
                text(
                    row.get(
                        "race_id"
                    )
                ),
                text(
                    row.get(
                        "race_entry_id"
                    )
                ),
            ),
        ):
            race_entry_epi_id = text(
                epi_row.get(
                    "race_entry_epi_id"
                )
            )

            race_entry_id = text(
                epi_row.get(
                    "race_entry_id"
                )
            )

            race_id = text(
                epi_row.get(
                    "race_id"
                )
            )

            race_date = text(
                epi_row.get(
                    "race_date"
                )
            )

            epi_evidence = text(
                epi_row.get(
                    "race_entry_epi_evidence_sha256"
                )
            )

            if not race_entry_epi_id:
                raise RuntimeError(
                    "EPI source row is missing race_entry_epi_id."
                )

            if race_entry_epi_id in seen_epi_ids:
                raise RuntimeError(
                    f"Duplicate Race Entry EPI ID: {race_entry_epi_id}"
                )

            seen_epi_ids.add(
                race_entry_epi_id
            )

            if not race_entry_id:
                raise RuntimeError(
                    f"Missing race_entry_id for {race_entry_epi_id}."
                )

            if race_entry_id in seen_race_entry_ids:
                raise RuntimeError(
                    f"Duplicate race_entry_id: {race_entry_id}"
                )

            seen_race_entry_ids.add(
                race_entry_id
            )

            if not race_id or not race_date:
                raise RuntimeError(
                    f"Incomplete race identity for {race_entry_id}."
                )

            if not epi_evidence:
                raise RuntimeError(
                    f"Missing EPI evidence for {race_entry_id}."
                )

            if text(
                epi_row.get(
                    "epi_publication_decision"
                )
            ) != EPI_PUBLICATION:
                raise RuntimeError(
                    f"Unpublished EPI source for {race_entry_id}."
                )

            if text(
                epi_row.get(
                    "epi_reconciliation_decision"
                )
            ) != EPI_RECONCILIATION:
                raise RuntimeError(
                    f"Unreconciled EPI source for {race_entry_id}."
                )

            if text(
                epi_row.get(
                    "epi_status"
                )
            ) != EPI_STATUS:
                raise RuntimeError(
                    f"Ungoverned EPI source for {race_entry_id}."
                )

            race_key = (
                race_id,
                race_date,
            )

            distribution = distribution_by_race.get(
                race_key
            )

            if distribution is None:
                raise RuntimeError(
                    f"No governed distribution for race entry {race_entry_id}."
                )

            joined_population_count[
                race_key
            ] = (
                joined_population_count.get(
                    race_key,
                    0,
                )
                + 1
            )

            distribution_id = text(
                distribution[
                    "race_epi_distribution_id"
                ]
            )

            distribution_evidence = text(
                distribution[
                    "race_epi_distribution_evidence_sha256"
                ]
            )

            runner_epi = decimal_value(
                epi_row.get(
                    "epi_value"
                ),
                f"{race_entry_id}.epi_value",
            )

            population_count = integer_value(
                distribution.get(
                    "eligible_epi_population_count"
                ),
                f"{distribution_id}.population_count",
            )

            field_mean = decimal_value(
                distribution.get(
                    "field_epi_mean"
                ),
                f"{distribution_id}.field_mean",
            )

            standard_deviation = decimal_value(
                distribution.get(
                    "field_epi_population_standard_deviation"
                ),
                f"{distribution_id}.standard_deviation",
            )

            minimum_epi = decimal_value(
                distribution.get(
                    "minimum_epi"
                ),
                f"{distribution_id}.minimum_epi",
            )

            maximum_epi = decimal_value(
                distribution.get(
                    "maximum_epi"
                ),
                f"{distribution_id}.maximum_epi",
            )

            epi_range = decimal_value(
                distribution.get(
                    "epi_range"
                ),
                f"{distribution_id}.epi_range",
            )

            if runner_epi < minimum_epi or runner_epi > maximum_epi:
                raise RuntimeError(
                    f"Runner EPI lies outside distribution boundaries: "
                    f"{race_entry_id}"
                )

            epi_minus_mean = (
                runner_epi
                - field_mean
            )

            if standard_deviation == Decimal("0"):
                epi_z_score = Decimal("0")
            else:
                epi_z_score = (
                    epi_minus_mean
                    / standard_deviation
                )

            distance_above_minimum = (
                runner_epi
                - minimum_epi
            )

            distance_below_maximum = (
                maximum_epi
                - runner_epi
            )

            if (
                distance_above_minimum < Decimal("0")
                or distance_below_maximum < Decimal("0")
            ):
                raise RuntimeError(
                    f"Negative distribution distance for {race_entry_id}."
                )

            if (
                (
                    distance_above_minimum
                    + distance_below_maximum
                ).quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
                != epi_range.quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_EVEN,
                )
            ):
                raise RuntimeError(
                    f"Relative EPI distances do not reconcile: "
                    f"{race_entry_id}"
                )

            runner_epi_text = decimal_text(
                runner_epi
            )

            field_mean_text = decimal_text(
                field_mean
            )

            epi_minus_mean_text = decimal_text(
                epi_minus_mean
            )

            standard_deviation_text = decimal_text(
                standard_deviation
            )

            epi_z_score_text = decimal_text(
                epi_z_score
            )

            minimum_epi_text = decimal_text(
                minimum_epi
            )

            maximum_epi_text = decimal_text(
                maximum_epi
            )

            epi_range_text = decimal_text(
                epi_range
            )

            distance_above_minimum_text = decimal_text(
                distance_above_minimum
            )

            distance_below_maximum_text = decimal_text(
                distance_below_maximum
            )

            identity_hash = sha256_payload(
                [
                    CONTRACT_VERSION,
                    race_entry_id,
                    race_entry_epi_id,
                    race_id,
                    race_date,
                    distribution_id,
                    PUBLICATION_DECISION,
                ]
            )

            relative_context_id = (
                f"REERC1-"
                f"{identity_hash[:24].upper()}"
            )

            source_lineage = (
                "edgeiq_race_entry_epi_fact_v1:"
                f"{race_entry_epi_id}"
                "|edgeiq_race_epi_distribution_fact_v1:"
                f"{distribution_id}"
            )

            evidence_hash = sha256_payload(
                [
                    relative_context_id,
                    race_entry_id,
                    race_entry_epi_id,
                    race_id,
                    race_date,
                    distribution_id,
                    runner_epi_text,
                    str(
                        population_count
                    ),
                    field_mean_text,
                    epi_minus_mean_text,
                    standard_deviation_text,
                    epi_z_score_text,
                    minimum_epi_text,
                    maximum_epi_text,
                    epi_range_text,
                    distance_above_minimum_text,
                    distance_below_maximum_text,
                    epi_evidence,
                    distribution_evidence,
                    PUBLICATION_DECISION,
                    RECONCILIATION_DECISION,
                    GOVERNED_STATUS,
                    source_lineage,
                ]
            )

            output_rows.append(
                {
                    "race_entry_epi_relative_context_id": (
                        relative_context_id
                    ),
                    "race_entry_id": (
                        race_entry_id
                    ),
                    "race_entry_epi_id": (
                        race_entry_epi_id
                    ),
                    "race_id": (
                        race_id
                    ),
                    "race_date": (
                        race_date
                    ),
                    "race_epi_distribution_id": (
                        distribution_id
                    ),
                    "runner_epi_value": (
                        runner_epi_text
                    ),
                    "eligible_epi_population_count": (
                        str(
                            population_count
                        )
                    ),
                    "field_epi_mean": (
                        field_mean_text
                    ),
                    "epi_minus_field_mean": (
                        epi_minus_mean_text
                    ),
                    "field_epi_population_standard_deviation": (
                        standard_deviation_text
                    ),
                    "epi_population_z_score": (
                        epi_z_score_text
                    ),
                    "minimum_epi": (
                        minimum_epi_text
                    ),
                    "maximum_epi": (
                        maximum_epi_text
                    ),
                    "epi_range": (
                        epi_range_text
                    ),
                    "distance_above_minimum_epi": (
                        distance_above_minimum_text
                    ),
                    "distance_below_maximum_epi": (
                        distance_below_maximum_text
                    ),
                    "race_entry_epi_evidence_sha256": (
                        epi_evidence
                    ),
                    "race_epi_distribution_evidence_sha256": (
                        distribution_evidence
                    ),
                    "epi_relative_context_publication_decision": (
                        PUBLICATION_DECISION
                    ),
                    "epi_relative_context_reconciliation_decision": (
                        RECONCILIATION_DECISION
                    ),
                    "epi_relative_context_status": (
                        GOVERNED_STATUS
                    ),
                    "race_entry_epi_relative_context_evidence_sha256": (
                        evidence_hash
                    ),
                    "source_lineage": (
                        source_lineage
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

    for race_key, distribution in distribution_by_race.items():
        expected_count = integer_value(
            distribution.get(
                "eligible_epi_population_count"
            ),
            "eligible_epi_population_count",
        )

        actual_count = joined_population_count.get(
            race_key,
            0,
        )

        if actual_count != expected_count:
            raise RuntimeError(
                f"Joined population does not reconcile for race "
                f"{race_key}: expected={expected_count}, "
                f"actual={actual_count}"
            )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ENTRY_EPI_RELATIVE_CONTEXT_FACT_V1_BUILD_PASS"
    )
    print(
        f"race_entry_epi_rows={len(epi_rows)}"
    )
    print(
        f"race_epi_distribution_rows={len(distribution_rows)}"
    )
    print(
        f"relative_context_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
