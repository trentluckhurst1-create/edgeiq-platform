from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE_PATH = (
    DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
)

PARAMETER_PATH = (
    DATA / "edgeiq_performance_normalisation_parameter_fact_v1.csv"
)

OUTPUT_PATH = (
    DATA / "edgeiq_performance_normalisation_fact_v1.csv"
)
REJECTION_PATH = (
    DATA / "edgeiq_performance_normalisation_fact_v1_rejections.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_performance_normalisation_fact_v1.0.0"
)
METHOD = "LINEAR_CENTRE_AND_SCALE"
STATUS = "NORMALISED_GOVERNED"

OUTPUT_FIELDS = [
    "performance_normalisation_id",
    "performance_intelligence_base_id",
    "normalisation_parameter_id",
    "lengths_versus_standard_id",
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "winner_canonical_horse_id",
    "winner_horse_name",
    "raw_performance_lengths",
    "centre_value",
    "scale_value",
    "normalised_performance_value",
    "normalisation_method",
    "normalisation_status",
    "normalisation_model_version",
    "source_performance_base_evidence_sha256",
    "source_normalisation_parameter_evidence_sha256",
    "performance_normalisation_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

REJECTION_FIELDS = [
    "performance_intelligence_base_id",
    "lengths_versus_standard_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "winner_canonical_horse_id",
    "winner_horse_name",
    "rejection_reason",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(f"Missing canonical input: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(f"Missing CSV header: {path}")

        return list(reader.fieldnames), list(reader)


def require_fields(
    path: Path,
    actual: list[str],
    required: Iterable[str],
) -> None:
    missing = [field for field in required if field not in actual]

    if missing:
        fail(f"{path.name} missing required fields: {missing}")


def decimal_value(
    value: object,
    field: str,
    positive_only: bool = False,
) -> Decimal:
    raw = text(value)

    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal value for {field}: {raw!r}"
        ) from exc

    if not parsed.is_finite():
        fail(f"Non-finite decimal value for {field}: {raw!r}")

    if positive_only and parsed <= 0:
        fail(f"Non-positive decimal value for {field}: {raw!r}")

    return parsed


def date_value(value: object, field: str) -> date:
    raw = text(value)

    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid date value for {field}: {raw!r}"
        ) from exc


def optional_date_value(value: object) -> date | None:
    raw = text(value)

    if not raw:
        return None

    return date.fromisoformat(raw)


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(file_descriptor)

    temporary_path = Path(temporary_name)

    try:
        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames or OUTPUT_FIELDS,
                extrasaction="raise",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    base_fields, base_rows = read_csv(BASE_PATH)

    require_fields(
        BASE_PATH,
        base_fields,
        [
            "performance_intelligence_base_id",
            "lengths_versus_standard_id",
            "benchmark_observation_id",
            "race_key",
            "race_date",
            "track_name",
            "official_distance_metres",
            "winner_canonical_horse_id",
            "winner_horse_name",
            "raw_performance_lengths",
            "performance_intelligence_base_evidence_sha256",
        ],
    )

    if not base_rows:
        atomic_write_csv(OUTPUT_PATH, [])
        atomic_write_csv(REJECTION_PATH, [], REJECTION_FIELDS)

        print(
            "EDGEIQ_PERFORMANCE_NORMALISATION_FACT_V1_BUILD_PASS"
        )
        print("performance_base_rows=0")
        print("normalisation_parameter_rows=NOT_REQUIRED")
        print("performance_normalisation_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    parameter_fields, parameter_rows = read_csv(PARAMETER_PATH)

    require_fields(
        PARAMETER_PATH,
        parameter_fields,
        [
            "normalisation_parameter_id",
            "normalisation_method",
            "centre_value",
            "scale_value",
            "normalisation_model_version",
            "parameter_status",
            "effective_from_date",
            "effective_to_date",
            "parameter_evidence_sha256",
        ],
    )

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []
    rejection_rows: list[dict[str, object]] = []
    seen_base_ids: set[str] = set()

    for base in base_rows:
        base_id = text(
            base["performance_intelligence_base_id"]
        )

        if not base_id:
            fail("Blank performance_intelligence_base_id.")

        if base_id in seen_base_ids:
            fail(f"Duplicate performance base row: {base_id}")

        seen_base_ids.add(base_id)

        race_date = date_value(base["race_date"], "race_date")

        matches: list[dict[str, str]] = []

        for parameter in parameter_rows:
            if (
                text(parameter["normalisation_method"]) != METHOD
                or text(parameter["parameter_status"]) != "AVAILABLE"
            ):
                continue

            effective_from = date_value(
                parameter["effective_from_date"],
                "effective_from_date",
            )
            effective_to = optional_date_value(
                parameter["effective_to_date"]
            )

            if race_date < effective_from:
                continue

            if effective_to is not None and race_date > effective_to:
                continue

            matches.append(parameter)

        if not matches:
            rejection_rows.append(
                {
                    "performance_intelligence_base_id": base_id,
                    "lengths_versus_standard_id": text(
                        base["lengths_versus_standard_id"]
                    ),
                    "race_key": text(base["race_key"]),
                    "race_date": text(base["race_date"]),
                    "track_name": text(base["track_name"]),
                    "official_distance_metres": text(
                        base["official_distance_metres"]
                    ),
                    "winner_canonical_horse_id": text(
                        base["winner_canonical_horse_id"]
                    ),
                    "winner_horse_name": text(
                        base["winner_horse_name"]
                    ),
                    "rejection_reason": (
                        "NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE"
                    ),
                }
            )
            continue

        if len(matches) > 1:
            rejection_rows.append(
                {
                    "performance_intelligence_base_id": base_id,
                    "lengths_versus_standard_id": text(
                        base["lengths_versus_standard_id"]
                    ),
                    "race_key": text(base["race_key"]),
                    "race_date": text(base["race_date"]),
                    "track_name": text(base["track_name"]),
                    "official_distance_metres": text(
                        base["official_distance_metres"]
                    ),
                    "winner_canonical_horse_id": text(
                        base["winner_canonical_horse_id"]
                    ),
                    "winner_horse_name": text(
                        base["winner_horse_name"]
                    ),
                    "rejection_reason": (
                        "AMBIGUOUS_GOVERNED_NORMALISATION_PARAMETER"
                    ),
                }
            )
            continue

        parameter = matches[0]

        raw_value = decimal_value(
            base["raw_performance_lengths"],
            "raw_performance_lengths",
        )
        centre = decimal_value(
            parameter["centre_value"],
            "centre_value",
        )
        scale = decimal_value(
            parameter["scale_value"],
            "scale_value",
            positive_only=True,
        )

        normalised_value = (raw_value - centre) / scale

        parameter_id = text(
            parameter["normalisation_parameter_id"]
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                base_id,
                parameter_id,
                METHOD,
            ]
        )

        normalisation_id = (
            f"PNF1-{identity_hash[:24].upper()}"
        )

        evidence_hash = sha256_payload(
            [
                normalisation_id,
                format_decimal(raw_value),
                format_decimal(centre),
                format_decimal(scale),
                format_decimal(normalised_value),
            ]
        )

        output_rows.append(
            {
                "performance_normalisation_id": (
                    normalisation_id
                ),
                "performance_intelligence_base_id": base_id,
                "normalisation_parameter_id": parameter_id,
                "lengths_versus_standard_id": text(
                    base["lengths_versus_standard_id"]
                ),
                "benchmark_observation_id": text(
                    base["benchmark_observation_id"]
                ),
                "race_key": text(base["race_key"]),
                "race_date": text(base["race_date"]),
                "track_name": text(base["track_name"]),
                "official_distance_metres": text(
                    base["official_distance_metres"]
                ),
                "winner_canonical_horse_id": text(
                    base["winner_canonical_horse_id"]
                ),
                "winner_horse_name": text(
                    base["winner_horse_name"]
                ),
                "raw_performance_lengths": format_decimal(
                    raw_value
                ),
                "centre_value": format_decimal(centre),
                "scale_value": format_decimal(scale),
                "normalised_performance_value": format_decimal(
                    normalised_value
                ),
                "normalisation_method": METHOD,
                "normalisation_status": STATUS,
                "normalisation_model_version": text(
                    parameter["normalisation_model_version"]
                ),
                "source_performance_base_evidence_sha256": (
                    text(
                        base[
                            "performance_intelligence_base_evidence_sha256"
                        ]
                    )
                ),
                "source_normalisation_parameter_evidence_sha256": (
                    text(parameter["parameter_evidence_sha256"])
                ),
                "performance_normalisation_evidence_sha256": (
                    evidence_hash
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(row["race_date"]),
            text(row["track_name"]).casefold(),
            int(text(row["official_distance_metres"])),
            text(row["benchmark_observation_id"]),
        )
    )

    atomic_write_csv(OUTPUT_PATH, output_rows)
    atomic_write_csv(
        REJECTION_PATH,
        rejection_rows,
        REJECTION_FIELDS,
    )

    print(
        "EDGEIQ_PERFORMANCE_NORMALISATION_FACT_V1_BUILD_PASS"
    )
    print(f"performance_base_rows={len(base_rows)}")
    print(
        f"normalisation_parameter_rows={len(parameter_rows)}"
    )
    print(
        f"performance_normalisation_rows={len(output_rows)}"
    )
    print(f"rejected_base_rows={len(rejection_rows)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
