from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RATING_PATH = (
    DATA / "edgeiq_performance_rating_base_fact_v1.csv"
)

IDENTITY_PATH = (
    ROOT
    / "config"
    / "performance-intelligence"
    / "edgeiq_horse_performance_identity_map_v1.csv"
)

OUTPUT_PATH = (
    DATA / "edgeiq_horse_performance_observation_fact_v1.csv"
)

REJECTION_PATH = (
    DATA / "edgeiq_horse_performance_observation_fact_v1_rejections.csv"
)

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = (
    "edgeiq_horse_performance_observation_fact_v1.0.0"
)
IDENTITY_METHOD = "EXACT_NORMALISED_NAME_APPROVED_MAP"
IDENTITY_STATUS = "IDENTIFIED_GOVERNED"
RATING_STATUS = "OBSERVED_NORMALISED_GOVERNED"

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

IDENTITY_FIELDS = [
    "source_horse_name",
    "canonical_horse_id",
    "canonical_horse_name",
    "identity_status",
    "evidence_reference",
    "evidence_sha256",
]

REJECTION_FIELDS = [
    "performance_rating_base_id",
    "performance_normalisation_id",
    "performance_intelligence_base_id",
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "source_horse_name",
    "rejection_reason",
    "policy_version",
    "built_at_utc",
]

OUTPUT_FIELDS = [
    "horse_performance_observation_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "source_horse_name",
    "performance_rating_base_id",
    "performance_normalisation_id",
    "performance_intelligence_base_id",
    "benchmark_observation_id",
    "race_key",
    "race_date",
    "track_name",
    "official_distance_metres",
    "raw_performance_lengths",
    "normalised_performance_value",
    "rating_base_value",
    "rating_status",
    "identity_method",
    "identity_status",
    "identity_evidence_reference",
    "source_identity_evidence_sha256",
    "source_performance_rating_base_evidence_sha256",
    "horse_performance_observation_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def normalized_name(value: object) -> str:
    return " ".join(text(value).split()).casefold()


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "\x1f".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def decimal_value(value: object, field_name: str) -> Decimal:
    raw = text(value)

    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal field {field_name}: {raw!r}"
        ) from exc

    if not parsed.is_finite():
        fail(f"Non-finite decimal field {field_name}: {raw!r}")

    return parsed


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(f"Missing canonical input: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(f"Missing CSV header: {path}")

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
        fail(f"{path.name} missing required fields: {missing}")


def atomic_write_csv_with_fields(
    path: Path,
    rows: list[dict[str, object]],
    fields: list[str],
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
                fieldnames=fields,
                extrasaction="raise",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    atomic_write_csv_with_fields(path, rows, OUTPUT_FIELDS)


def main() -> None:
    rating_fields, rating_rows = read_csv(RATING_PATH)

    require_fields(
        RATING_PATH,
        rating_fields,
        [
            "performance_rating_base_id",
            "performance_normalisation_id",
            "performance_intelligence_base_id",
            "benchmark_observation_id",
            "race_key",
            "race_date",
            "track_name",
            "official_distance_metres",
            "winner_horse_name",
            "raw_performance_lengths",
            "normalised_performance_value",
            "rating_base_value",
            "rating_status",
            "performance_rating_base_evidence_sha256",
        ],
    )

    if not rating_rows:
        atomic_write_csv(OUTPUT_PATH, [])
        atomic_write_csv_with_fields(REJECTION_PATH, [], REJECTION_FIELDS)

        print(
            "EDGEIQ_HORSE_PERFORMANCE_OBSERVATION_FACT_V1_BUILD_PASS"
        )
        print("performance_rating_base_rows=0")
        print("identity_map_rows=NOT_REQUIRED")
        print("horse_performance_observation_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    identity_fields, identity_rows = read_csv(IDENTITY_PATH)

    missing_identity_fields = [field for field in IDENTITY_FIELDS if field not in identity_fields]
    if missing_identity_fields:
        fail(
            "Horse identity-map missing governed fields: "
            f"{missing_identity_fields}. Actual: {identity_fields}"
        )

    approved_identity_by_name: dict[str, dict[str, str]] = {}

    for ordinal, identity in enumerate(identity_rows, start=1):
        if text(identity["identity_status"]) != "APPROVED":
            continue

        source_name = text(identity["source_horse_name"])
        canonical_id = text(identity["canonical_horse_id"])
        canonical_name = text(identity["canonical_horse_name"])
        evidence_reference = text(identity["evidence_reference"])
        evidence_sha256 = text(identity["evidence_sha256"]).lower()

        if not source_name:
            fail(f"Identity row {ordinal}: blank source_horse_name.")

        if not canonical_id:
            fail(f"Identity row {ordinal}: blank canonical_horse_id.")

        if not canonical_name:
            fail(f"Identity row {ordinal}: blank canonical_horse_name.")

        if not evidence_reference:
            fail(f"Identity row {ordinal}: blank evidence_reference.")

        if not SHA256_PATTERN.fullmatch(evidence_sha256):
            fail(
                f"Identity row {ordinal}: invalid evidence_sha256."
            )

        normalized = normalized_name(source_name)

        if normalized in approved_identity_by_name:
            fail(
                "Multiple approved identities exist for normalized "
                f"horse name {normalized!r}."
            )

        approved_identity_by_name[normalized] = identity

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []
    rejection_rows: list[dict[str, object]] = []
    seen_rating_ids: set[str] = set()
    seen_output_ids: set[str] = set()

    for rating in rating_rows:
        rating_id = text(rating["performance_rating_base_id"])

        if not rating_id:
            fail("Blank performance_rating_base_id.")

        if rating_id in seen_rating_ids:
            fail(f"Duplicate rating-base row: {rating_id}")

        seen_rating_ids.add(rating_id)

        if text(rating["rating_status"]) != RATING_STATUS:
            fail(f"{rating_id}: rating status is not governed.")

        source_horse_name = text(rating["winner_horse_name"])
        identity = approved_identity_by_name.get(
            normalized_name(source_horse_name)
        )

        if identity is None:
            rejection_rows.append({
                "performance_rating_base_id": rating_id,
                "performance_normalisation_id": text(rating["performance_normalisation_id"]),
                "performance_intelligence_base_id": text(rating["performance_intelligence_base_id"]),
                "benchmark_observation_id": text(rating["benchmark_observation_id"]),
                "race_key": text(rating["race_key"]),
                "race_date": text(rating["race_date"]),
                "track_name": text(rating["track_name"]),
                "official_distance_metres": text(rating["official_distance_metres"]),
                "source_horse_name": source_horse_name,
                "rejection_reason": "NO_APPROVED_EXACT_HORSE_IDENTITY",
                "policy_version": "RA-HORSE-ID-GOV-V4",
                "built_at_utc": built_at_utc,
            })
            continue

        canonical_horse_id = text(identity["canonical_horse_id"])
        canonical_horse_name = text(identity["canonical_horse_name"])
        identity_evidence_reference = text(
            identity["evidence_reference"]
        )
        identity_evidence_sha256 = text(
            identity["evidence_sha256"]
        ).lower()

        raw_value = decimal_value(
            rating["raw_performance_lengths"],
            "raw_performance_lengths",
        )
        normalized_value = decimal_value(
            rating["normalised_performance_value"],
            "normalised_performance_value",
        )
        rating_value = decimal_value(
            rating["rating_base_value"],
            "rating_base_value",
        )

        identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                rating_id,
                canonical_horse_id,
                IDENTITY_METHOD,
            ]
        )

        observation_id = (
            f"HPO1-{identity_hash[:24].upper()}"
        )

        if observation_id in seen_output_ids:
            fail(
                f"Duplicate deterministic observation ID: "
                f"{observation_id}"
            )

        seen_output_ids.add(observation_id)

        rating_evidence_hash = text(
            rating["performance_rating_base_evidence_sha256"]
        )

        if not rating_evidence_hash:
            fail(f"{rating_id}: blank rating-base evidence hash.")

        observation_evidence_hash = sha256_payload(
            [
                observation_id,
                canonical_horse_id,
                identity_evidence_sha256,
                rating_evidence_hash,
                format_decimal(rating_value),
            ]
        )

        output_rows.append(
            {
                "horse_performance_observation_id": observation_id,
                "canonical_horse_id": canonical_horse_id,
                "canonical_horse_name": canonical_horse_name,
                "source_horse_name": source_horse_name,
                "performance_rating_base_id": rating_id,
                "performance_normalisation_id": text(
                    rating["performance_normalisation_id"]
                ),
                "performance_intelligence_base_id": text(
                    rating["performance_intelligence_base_id"]
                ),
                "benchmark_observation_id": text(
                    rating["benchmark_observation_id"]
                ),
                "race_key": text(rating["race_key"]),
                "race_date": text(rating["race_date"]),
                "track_name": text(rating["track_name"]),
                "official_distance_metres": text(
                    rating["official_distance_metres"]
                ),
                "raw_performance_lengths": format_decimal(raw_value),
                "normalised_performance_value": format_decimal(
                    normalized_value
                ),
                "rating_base_value": format_decimal(rating_value),
                "rating_status": RATING_STATUS,
                "identity_method": IDENTITY_METHOD,
                "identity_status": IDENTITY_STATUS,
                "identity_evidence_reference": (
                    identity_evidence_reference
                ),
                "source_identity_evidence_sha256": (
                    identity_evidence_sha256
                ),
                "source_performance_rating_base_evidence_sha256": (
                    rating_evidence_hash
                ),
                "horse_performance_observation_evidence_sha256": (
                    observation_evidence_hash
                ),
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at_utc,
            }
        )

    output_rows.sort(
        key=lambda row: (
            text(row["canonical_horse_id"]),
            text(row["race_date"]),
            text(row["performance_rating_base_id"]),
        )
    )

    atomic_write_csv(OUTPUT_PATH, output_rows)
    atomic_write_csv_with_fields(REJECTION_PATH, rejection_rows, REJECTION_FIELDS)

    print(
        "EDGEIQ_HORSE_PERFORMANCE_OBSERVATION_FACT_V1_BUILD_PASS"
    )
    print(f"performance_rating_base_rows={len(rating_rows)}")
    print(f"identity_map_rows={len(identity_rows)}")
    print(
        "horse_performance_observation_rows="
        f"{len(output_rows)}"
    )
    print(f"identity_rejection_rows={len(rejection_rows)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
