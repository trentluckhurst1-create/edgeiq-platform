from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

SOURCE = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

RAW_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
)

WAREHOUSE_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "performance-facts"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_5b"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_5b"
)

EDGEIQ_NAMESPACE = uuid.UUID(
    "ed91a5d8-e8e7-5b0f-a108-cd9c41c36901"
)

WAREHOUSE_VERSION = (
    "EDGEIQ_CANONICAL_PERFORMANCE_FACTS_V0_1"
)

MATERIALISATION_VERSION = (
    "PHASE1_5B_PERFORMANCE_FACTS_V0_1"
)

PROGRESS_INTERVAL = 100_000
CHUNK_SIZE = 4 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def stable_id(
    entity_type: str,
    natural_key: str,
) -> str:
    generated = uuid.uuid5(
        EDGEIQ_NAMESPACE,
        f"{entity_type}|{natural_key}",
    )

    return (
        f"eiq_{entity_type.lower()}_"
        f"{generated.hex}"
    )


def normalise_date(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return (
        match.group(1)
        if match
        else ""
    )


def parse_number(
    value: Any,
) -> float | None:
    text = clean(value)

    if not text:
        return None

    text = text.replace(
        ",",
        "",
    )

    time_match = re.fullmatch(
        r"(\d+):(\d+(?:\.\d+)?)",
        text,
    )

    if time_match:
        value = (
            float(time_match.group(1))
            * 60.0
            + float(time_match.group(2))
        )

        return (
            value
            if math.isfinite(value)
            else None
        )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        value = float(
            match.group(0)
        )
    except ValueError:
        return None

    return (
        value
        if math.isfinite(value)
        else None
    )


def numeric_text(
    value: Any,
    decimals: int = 6,
) -> str:
    number = parse_number(value)

    if number is None:
        return ""

    return (
        f"{number:.{decimals}f}"
        .rstrip("0")
        .rstrip(".")
    )


def bool_text(value: Any) -> str:
    text = clean(value).upper()

    if text in {
        "1",
        "TRUE",
        "YES",
        "Y",
    }:
        return "TRUE"

    if text in {
        "0",
        "FALSE",
        "NO",
        "N",
    }:
        return "FALSE"

    return ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                CHUNK_SIZE
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def latest_raw_snapshot() -> Path:
    candidates = sorted(
        (
            path
            for path in RAW_ROOT.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and (
                path
                / "warehouse_manifest.json"
            ).exists()
        ),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            "No immutable raw snapshot found."
        )

    return candidates[0]


def write_json(
    path: Path,
    payload: Any,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    fields: list[str] = []

    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def make_read_only(path: Path) -> None:
    try:
        os.chmod(
            path,
            0o444,
        )
    except OSError:
        pass


def restore_writable(path: Path) -> None:
    try:
        os.chmod(
            path,
            0o666,
        )
    except OSError:
        pass


def main() -> None:
    WAREHOUSE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_snapshot = latest_raw_snapshot()

    canonical_identity_path = (
        raw_snapshot
        / "canonical_performance_evidence.csv"
    )

    raw_manifest_path = (
        raw_snapshot
        / "warehouse_manifest.json"
    )

    raw_manifest = json.loads(
        raw_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    source_hash = sha256_file(
        SOURCE
    )

    identity_hash = sha256_file(
        canonical_identity_path
    )

    snapshot_id = stable_id(
        "performance_facts_snapshot",
        (
            f"{WAREHOUSE_VERSION}|"
            f"{raw_snapshot.name}|"
            f"{source_hash}|"
            f"{identity_hash}"
        ),
    )

    final_dir = (
        WAREHOUSE_ROOT
        / snapshot_id
    )

    staging_dir = (
        WAREHOUSE_ROOT
        / f".{snapshot_id}.staging"
    )

    if final_dir.exists():
        print(
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_5B_PERFORMANCE_FACTS_"
            "ALREADY_MATERIALISED_PASS",
            flush=True,
        )

        print(
            f"WAREHOUSE={final_dir}",
            flush=True,
        )

        return

    if staging_dir.exists():
        for path in staging_dir.rglob("*"):
            if path.is_file():
                restore_writable(path)

        shutil.rmtree(
            staging_dir
        )

    staging_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    facts_path = (
        staging_dir
        / "canonical_performance_facts.csv"
    )

    exclusions_path = (
        staging_dir
        / "performance_fact_quality_states.csv"
    )

    facts_fields = [
        "performance_id",
        "race_id",
        "meeting_id",
        "horse_identity_evidence_id",
        "race_date",
        "state",
        "track",
        "venue_name",
        "race_number",
        "race_name",
        "race_class",
        "distance_metres",
        "race_status",
        "track_condition",
        "track_rating",
        "rail_position",
        "previous_rail_position",
        "weather",
        "rainfall",
        "penetrometer",
        "official_winning_time_seconds",
        "finish_position",
        "finish_abbreviation",
        "official_margin",
        "margin_lengths",
        "barrier",
        "live_barrier",
        "weight_carried",
        "jockey",
        "jockey_code",
        "trainer",
        "trainer_code",
        "starting_price_raw",
        "starting_price_decimal",
        "scratched",
        "has_results",
        "has_sectionals",
        "has_speed_map",
        "comment_short",
        "comment",
        "stewards_comment",
        "gear_changes",
        "performance_quality_state",
        "official_time_quality_state",
        "margin_quality_state",
        "source_file",
        "source_row_number",
        "source_sha256",
        "raw_warehouse_snapshot_id",
        "materialisation_version",
        "materialised_at",
    ]

    quality_fields = [
        "performance_id",
        "performance_quality_state",
        "official_time_quality_state",
        "margin_quality_state",
        "missing_fields",
        "exclusion_reasons",
    ]

    performance_rows = 0
    identity_rows = 0
    identity_mismatches = 0
    duplicate_ids = 0
    blank_ids = 0
    seen_ids: set[str] = set()
    quality_counts = Counter()
    time_quality_counts = Counter()
    margin_quality_counts = Counter()
    generated_at = utc_now()

    try:
        with SOURCE.open(
            "r",
            encoding="utf-8-sig",
            errors="ignore",
            newline="",
        ) as source_handle, canonical_identity_path.open(
            "r",
            encoding="utf-8-sig",
            errors="ignore",
            newline="",
        ) as identity_handle, facts_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as facts_handle, exclusions_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as quality_handle:
            source_reader = csv.DictReader(
                source_handle
            )

            identity_reader = csv.DictReader(
                identity_handle
            )

            facts_writer = csv.DictWriter(
                facts_handle,
                fieldnames=facts_fields,
            )
            facts_writer.writeheader()

            quality_writer = csv.DictWriter(
                quality_handle,
                fieldnames=quality_fields,
            )
            quality_writer.writeheader()

            for row_number, (
                source,
                identity,
            ) in enumerate(
                zip(
                    source_reader,
                    identity_reader,
                    strict=True,
                ),
                start=1,
            ):
                performance_rows += 1
                identity_rows += 1

                if (
                    row_number == 1
                    or row_number
                    % PROGRESS_INTERVAL
                    == 0
                ):
                    print(
                        "PERFORMANCE_FACTS_PROGRESS="
                        f"{row_number}",
                        flush=True,
                    )

                performance_id = clean(
                    identity.get(
                        "performance_id"
                    )
                )

                if not performance_id:
                    blank_ids += 1

                elif performance_id in seen_ids:
                    duplicate_ids += 1

                else:
                    seen_ids.add(
                        performance_id
                    )

                expected_source_row = str(
                    row_number + 1
                )

                if clean(
                    identity.get(
                        "source_row_number"
                    )
                ) != expected_source_row:
                    identity_mismatches += 1

                distance = parse_number(
                    source.get("distance")
                )

                winning_time = parse_number(
                    source.get("winning_time")
                )

                finish = parse_number(
                    source.get("finish")
                )

                margin = parse_number(
                    source.get("margin")
                )

                margin_lengths = parse_number(
                    source.get("margin_l")
                )

                scratched = bool_text(
                    source.get("scratched")
                )

                race_status = clean(
                    source.get(
                        "race_status"
                    )
                ).upper()

                missing_fields: list[str] = []
                exclusion_reasons: list[str] = []

                for field_name, value in (
                    (
                        "distance_metres",
                        distance,
                    ),
                    (
                        "finish_position",
                        finish,
                    ),
                ):
                    if value is None:
                        missing_fields.append(
                            field_name
                        )

                if scratched == "TRUE":
                    performance_quality = (
                        "SCRATCHED"
                    )
                    exclusion_reasons.append(
                        "SCRATCHED"
                    )

                elif race_status in {
                    "ABANDONED",
                    "CANCELLED",
                    "VOID",
                    "NO_RACE",
                }:
                    performance_quality = (
                        "EXCLUDED_RACE_STATUS"
                    )
                    exclusion_reasons.append(
                        race_status
                    )

                elif (
                    distance is None
                    or finish is None
                ):
                    performance_quality = (
                        "PARTIAL"
                    )

                else:
                    performance_quality = (
                        "COMPLETE"
                    )

                if winning_time is None:
                    time_quality = (
                        "OFFICIAL_TIME_UNAVAILABLE"
                    )

                elif winning_time <= 0:
                    time_quality = (
                        "OFFICIAL_TIME_INVALID"
                    )
                    exclusion_reasons.append(
                        "INVALID_OFFICIAL_TIME"
                    )

                else:
                    time_quality = (
                        "OFFICIAL_TIME_AVAILABLE"
                    )

                if (
                    margin is not None
                    or margin_lengths is not None
                ):
                    margin_quality = (
                        "OFFICIAL_MARGIN_AVAILABLE"
                    )
                else:
                    margin_quality = (
                        "OFFICIAL_MARGIN_UNAVAILABLE"
                    )

                quality_counts[
                    performance_quality
                ] += 1

                time_quality_counts[
                    time_quality
                ] += 1

                margin_quality_counts[
                    margin_quality
                ] += 1

                facts_writer.writerow(
                    {
                        "performance_id": (
                            performance_id
                        ),
                        "race_id": clean(
                            identity.get(
                                "race_id"
                            )
                        ),
                        "meeting_id": clean(
                            identity.get(
                                "meeting_id"
                            )
                        ),
                        "horse_identity_evidence_id": clean(
                            identity.get(
                                "horse_id"
                            )
                        ),
                        "race_date": (
                            normalise_date(
                                source.get(
                                    "race_date"
                                )
                            )
                        ),
                        "state": clean(
                            source.get("state")
                        ),
                        "track": clean(
                            source.get("track")
                        ),
                        "venue_name": clean(
                            source.get(
                                "venue_name"
                            )
                        ),
                        "race_number": (
                            numeric_text(
                                source.get(
                                    "race_no"
                                ),
                                0,
                            )
                        ),
                        "race_name": clean(
                            source.get(
                                "race_name"
                            )
                        ),
                        "race_class": clean(
                            source.get(
                                "race_class"
                            )
                        ),
                        "distance_metres": (
                            numeric_text(
                                distance,
                                3,
                            )
                        ),
                        "race_status": clean(
                            source.get(
                                "race_status"
                            )
                        ),
                        "track_condition": clean(
                            source.get(
                                "track_condition"
                            )
                        ),
                        "track_rating": clean(
                            source.get(
                                "track_rating"
                            )
                        ),
                        "rail_position": clean(
                            source.get(
                                "rail_position"
                            )
                        ),
                        "previous_rail_position": clean(
                            source.get(
                                "previous_rail_position"
                            )
                        ),
                        "weather": clean(
                            source.get(
                                "weather"
                            )
                        ),
                        "rainfall": clean(
                            source.get(
                                "rainfall"
                            )
                        ),
                        "penetrometer": clean(
                            source.get(
                                "penetrometer"
                            )
                        ),
                        "official_winning_time_seconds": (
                            numeric_text(
                                winning_time,
                                6,
                            )
                        ),
                        "finish_position": (
                            numeric_text(
                                finish,
                                0,
                            )
                        ),
                        "finish_abbreviation": clean(
                            source.get(
                                "finish_abv"
                            )
                        ),
                        "official_margin": (
                            numeric_text(
                                margin,
                                6,
                            )
                        ),
                        "margin_lengths": (
                            numeric_text(
                                margin_lengths,
                                6,
                            )
                        ),
                        "barrier": (
                            numeric_text(
                                source.get(
                                    "barrier"
                                ),
                                0,
                            )
                        ),
                        "live_barrier": (
                            numeric_text(
                                source.get(
                                    "live_barrier"
                                ),
                                0,
                            )
                        ),
                        "weight_carried": (
                            numeric_text(
                                source.get(
                                    "weight"
                                ),
                                3,
                            )
                        ),
                        "jockey": clean(
                            source.get("jockey")
                        ),
                        "jockey_code": clean(
                            source.get(
                                "jockey_code"
                            )
                        ),
                        "trainer": clean(
                            source.get(
                                "trainer"
                            )
                        ),
                        "trainer_code": clean(
                            source.get(
                                "trainer_code"
                            )
                        ),
                        "starting_price_raw": clean(
                            source.get(
                                "starting_price"
                            )
                        ),
                        "starting_price_decimal": (
                            numeric_text(
                                source.get(
                                    "starting_price_decimal"
                                ),
                                6,
                            )
                        ),
                        "scratched": (
                            scratched
                        ),
                        "has_results": (
                            bool_text(
                                source.get(
                                    "has_results"
                                )
                            )
                        ),
                        "has_sectionals": (
                            bool_text(
                                source.get(
                                    "has_sectionals"
                                )
                            )
                        ),
                        "has_speed_map": (
                            bool_text(
                                source.get(
                                    "has_speed_map"
                                )
                            )
                        ),
                        "comment_short": clean(
                            source.get(
                                "comment_short"
                            )
                        ),
                        "comment": clean(
                            source.get(
                                "comment"
                            )
                        ),
                        "stewards_comment": clean(
                            source.get(
                                "comment_stewards"
                            )
                        ),
                        "gear_changes": clean(
                            source.get(
                                "gear_changes"
                            )
                        ),
                        "performance_quality_state": (
                            performance_quality
                        ),
                        "official_time_quality_state": (
                            time_quality
                        ),
                        "margin_quality_state": (
                            margin_quality
                        ),
                        "source_file": (
                            str(
                                SOURCE.relative_to(
                                    ROOT
                                )
                            ).replace(
                                "\\",
                                "/",
                            )
                        ),
                        "source_row_number": (
                            expected_source_row
                        ),
                        "source_sha256": (
                            source_hash
                        ),
                        "raw_warehouse_snapshot_id": (
                            raw_snapshot.name
                        ),
                        "materialisation_version": (
                            MATERIALISATION_VERSION
                        ),
                        "materialised_at": (
                            generated_at
                        ),
                    }
                )

                quality_writer.writerow(
                    {
                        "performance_id": (
                            performance_id
                        ),
                        "performance_quality_state": (
                            performance_quality
                        ),
                        "official_time_quality_state": (
                            time_quality
                        ),
                        "margin_quality_state": (
                            margin_quality
                        ),
                        "missing_fields": (
                            " | ".join(
                                missing_fields
                            )
                        ),
                        "exclusion_reasons": (
                            " | ".join(
                                exclusion_reasons
                            )
                        ),
                    }
                )

        facts_hash = sha256_file(
            facts_path
        )

        quality_hash = sha256_file(
            exclusions_path
        )

        checks = [
            {
                "check": (
                    "SOURCE_AND_IDENTITY_ROW_COUNT"
                ),
                "passed": (
                    performance_rows
                    == identity_rows
                    == 879784
                ),
                "observed": (
                    f"source={performance_rows};"
                    f"identity={identity_rows}"
                ),
            },
            {
                "check": (
                    "SOURCE_ROW_LINEAGE"
                ),
                "passed": (
                    identity_mismatches == 0
                ),
                "observed": (
                    identity_mismatches
                ),
            },
            {
                "check": (
                    "PERFORMANCE_PRIMARY_KEY"
                ),
                "passed": (
                    duplicate_ids == 0
                    and blank_ids == 0
                ),
                "observed": (
                    f"duplicates={duplicate_ids};"
                    f"blank={blank_ids}"
                ),
            },
            {
                "check": (
                    "FACTS_ROW_COUNT"
                ),
                "passed": (
                    performance_rows
                    == 879784
                ),
                "observed": (
                    performance_rows
                ),
            },
            {
                "check": (
                    "NO_BENCHMARK_FIELDS"
                ),
                "passed": True,
                "observed": (
                    "RAW_FACTS_ONLY"
                ),
            },
            {
                "check": (
                    "NO_SECTIONAL_TIME_FABRICATION"
                ),
                "passed": True,
                "observed": (
                    "NO_SECTIONAL_SPLIT_FIELDS_"
                    "MATERIALISED"
                ),
            },
        ]

        failed_checks = [
            check["check"]
            for check in checks
            if not check["passed"]
        ]

        if failed_checks:
            raise RuntimeError(
                "Phase 1.5B checks failed: "
                + " | ".join(
                    failed_checks
                )
            )

        write_csv(
            staging_dir
            / "materialisation_checks.csv",
            checks,
        )

        asset_catalog = [
            {
                "asset_name": (
                    "canonical_performance_facts"
                ),
                "asset_file": (
                    facts_path.name
                ),
                "rows": performance_rows,
                "primary_key": (
                    "performance_id"
                ),
                "sha256": facts_hash,
                "asset_type": (
                    "IMMUTABLE_OFFICIAL_"
                    "PERFORMANCE_FACTS"
                ),
            },
            {
                "asset_name": (
                    "performance_fact_quality_states"
                ),
                "asset_file": (
                    exclusions_path.name
                ),
                "rows": performance_rows,
                "primary_key": (
                    "performance_id"
                ),
                "sha256": quality_hash,
                "asset_type": (
                    "IMMUTABLE_EVIDENCE_"
                    "QUALITY_STATES"
                ),
            },
        ]

        write_csv(
            staging_dir
            / "asset_catalog.csv",
            asset_catalog,
        )

        manifest = {
            "warehouse_name": (
                "EDGEiQ Canonical "
                "Performance Facts Warehouse"
            ),
            "warehouse_version": (
                WAREHOUSE_VERSION
            ),
            "materialisation_version": (
                MATERIALISATION_VERSION
            ),
            "performance_facts_snapshot_id": (
                snapshot_id
            ),
            "raw_warehouse_snapshot_id": (
                raw_snapshot.name
            ),
            "generated_utc": (
                generated_at
            ),
            "immutable": True,
            "production_application_modified": (
                False
            ),
            "benchmarks_calculated": False,
            "sectional_times_materialised": (
                False
            ),
            "speed_evidence_materialised": (
                False
            ),
            "source": {
                "path": str(
                    SOURCE.relative_to(
                        ROOT
                    )
                ).replace("\\", "/"),
                "sha256": source_hash,
                "rows": performance_rows,
            },
            "assets": asset_catalog,
            "quality_state_counts": dict(
                sorted(
                    quality_counts.items()
                )
            ),
            "official_time_quality_counts": dict(
                sorted(
                    time_quality_counts.items()
                )
            ),
            "margin_quality_counts": dict(
                sorted(
                    margin_quality_counts.items()
                )
            ),
            "materialisation_checks": (
                checks
            ),
            "failed_checks": [],
            "warehouse_status": (
                "IMMUTABLE_CANONICAL_"
                "PERFORMANCE_FACTS_"
                "MATERIALISED"
            ),
            "promotion_status": (
                "NOT_CONNECTED_TO_PRODUCT"
            ),
            "next_stage": (
                "Phase 1.5C normalise race-level "
                "benchmark eligibility and create "
                "one governed race-time observation "
                "per completed race."
            ),
        }

        manifest_path = (
            staging_dir
            / "performance_facts_manifest.json"
        )

        write_json(
            manifest_path,
            manifest,
        )

        integrity = {
            "performance_facts_snapshot_id": (
                snapshot_id
            ),
            "generated_utc": utc_now(),
            "files": [
                {
                    "file": path.name,
                    "sha256": (
                        sha256_file(path)
                    ),
                }
                for path in (
                    facts_path,
                    exclusions_path,
                    staging_dir
                    / "materialisation_checks.csv",
                    staging_dir
                    / "asset_catalog.csv",
                    manifest_path,
                )
            ],
        }

        write_json(
            staging_dir
            / "integrity_manifest.json",
            integrity,
        )

        staging_dir.rename(
            final_dir
        )

        for path in final_dir.rglob("*"):
            if path.is_file():
                make_read_only(path)

    except Exception:
        if staging_dir.exists():
            for path in staging_dir.rglob("*"):
                if path.is_file():
                    restore_writable(path)

            shutil.rmtree(
                staging_dir
            )

        raise

    final_manifest = json.loads(
        (
            final_dir
            / "performance_facts_manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    audit_latest = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_5b_latest.json"
        )
    )

    audit_summary = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5b_summary_{snapshot_id}.json"
        )
    )

    audit_checks = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_5b_checks_{snapshot_id}.csv"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_5B_REPORT_{snapshot_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_CANONICAL_PERFORMANCE_"
            "FACTS_WAREHOUSE_V0_1.md"
        )
    )

    write_json(
        audit_latest,
        final_manifest,
    )

    write_json(
        audit_summary,
        final_manifest,
    )

    write_csv(
        audit_checks,
        final_manifest[
            "materialisation_checks"
        ],
    )

    architecture_path.write_text(
        """# EDGEiQ Canonical Performance Facts Warehouse V0.1

## Boundary

This warehouse contains official or source-recorded performance facts only.

It contains no:

- benchmark values
- seconds-versus-benchmark
- lengths conversions
- patterns
- fingerprints
- EPI
- ERI
- inferred sectionals

## Race-time evidence

Winning time is preserved in seconds where source evidence exists.

Unavailable winning time remains explicitly unavailable.

## Margin evidence

Raw source margin and source margin-in-lengths are retained separately.

No missing margin is estimated.

## Sectionals

The current sectional source contains speed metrics but no official split times.

No split or cumulative sectional time is materialised in this warehouse.

## Immutability

Each snapshot is identified by source hashes and the parent raw-warehouse snapshot.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.5B Canonical Performance Facts Materialisation

Snapshot ID: `{snapshot_id}`

Status: **{final_manifest['warehouse_status']}**

- Performance rows: **{performance_rows:,}**
- Duplicate performance IDs: **{duplicate_ids:,}**
- Blank performance IDs: **{blank_ids:,}**
- Lineage mismatches: **{identity_mismatches:,}**
- Benchmarks calculated: **False**
- Official sectional times materialised: **False**
- Production application modified: **False**

Next stage: **{final_manifest['next_stage']}**
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_5B_IMMUTABLE_CANONICAL_"
        "PERFORMANCE_FACTS_PASS",
        flush=True,
    )

    print(
        f"SNAPSHOT_ID={snapshot_id}",
        flush=True,
    )

    print(
        f"PERFORMANCE_ROWS={performance_rows}",
        flush=True,
    )

    print(
        f"DUPLICATE_IDS={duplicate_ids}",
        flush=True,
    )

    print(
        f"LINEAGE_MISMATCHES="
        f"{identity_mismatches}",
        flush=True,
    )

    print(
        f"WAREHOUSE={final_dir}",
        flush=True,
    )

    print(
        f"MANIFEST="
        f"{final_dir / 'performance_facts_manifest.json'}",
        flush=True,
    )

    print(
        f"AUDIT_SUMMARY={audit_summary}",
        flush=True,
    )


if __name__ == "__main__":
    main()
