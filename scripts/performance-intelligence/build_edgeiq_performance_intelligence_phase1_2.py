from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

RAW_WAREHOUSE_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
)

DIMENSION_WAREHOUSE_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "dimensions"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_2"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_2"
)

EDGEIQ_NAMESPACE = uuid.UUID(
    "ed91a5d8-e8e7-5b0f-a108-cd9c41c36901"
)

DIMENSION_VERSION = (
    "EDGEIQ_IDENTITY_DIMENSIONS_V0_1"
)

MATERIALISATION_VERSION = (
    "PHASE1_2_IDENTITY_DIMENSION_"
    "MATERIALISATION_V0_1"
)

PROGRESS_INTERVAL = 100_000
CHUNK_SIZE = 4 * 1024 * 1024


TRACK_ALIAS_MAP = {
    "VALLEY": "MOONEEVALLEY",
    "THEVALLEY": "MOONEEVALLEY",
    "MOONEEVALLEY": "MOONEEVALLEY",

    "PARKHILLSIDE": "SANDOWNHILLSIDE",
    "SANDOWNHILLSIDE": "SANDOWNHILLSIDE",
    "LADBROKESPARKHILLSIDE": "SANDOWNHILLSIDE",
    "SANDOWNPARKHILLSIDE": "SANDOWNHILLSIDE",

    "PARKLAKESIDE": "SANDOWNLAKESIDE",
    "SANDOWNLAKESIDE": "SANDOWNLAKESIDE",
    "LADBROKESPARKLAKESIDE": "SANDOWNLAKESIDE",
    "SANDOWNPARKLAKESIDE": "SANDOWNLAKESIDE",

    "PARKKILMORE": "KILMORE",
    "KILMORE": "KILMORE",
    "BET365PARKKILMORE": "KILMORE",

    "APIAMBENDIGO": "BENDIGO",
    "BET365BENDIGO": "BENDIGO",
    "BENDIGO": "BENDIGO",

    "PAKENHAMSYN": "PAKENHAMSYNTHETIC",
    "PAKENHAMSYNTH": "PAKENHAMSYNTHETIC",
    "PAKENHAMSYNTHETIC": "PAKENHAMSYNTHETIC",

    "BALLARATSYN": "BALLARATSYNTHETIC",
    "BALLARATSYNTH": "BALLARATSYNTHETIC",
    "BALLARATSYNTHETIC": "BALLARATSYNTHETIC",

    "GEELONGSYN": "GEELONGSYNTHETIC",
    "GEELONGSYNTH": "GEELONGSYNTHETIC",
    "GEELONGSYNTHETIC": "GEELONGSYNTHETIC",
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_text(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        clean(value).upper(),
    )


def compact_key(value: Any) -> str:
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        normalise_text(value),
    )


def normalise_date(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    )

    for date_format in formats:
        try:
            return datetime.strptime(
                text[:10],
                date_format,
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return match.group(1) if match else ""


def normalise_integer(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    try:
        number = float(text)
    except ValueError:
        match = re.search(
            r"\d+",
            text,
        )
        return (
            match.group(0)
            if match
            else ""
        )

    if not number.is_integer():
        return ""

    return str(int(number))


def normalise_track(value: Any) -> str:
    key = compact_key(value)

    if key in TRACK_ALIAS_MAP:
        return TRACK_ALIAS_MAP[key]

    for prefix in (
        "BET365",
        "LADBROKES",
        "SPORTSBET",
        "APIAM",
        "TAB",
    ):
        if key.startswith(prefix):
            stripped = key[
                len(prefix):
            ]

            if stripped in TRACK_ALIAS_MAP:
                return TRACK_ALIAS_MAP[
                    stripped
                ]

            key = stripped
            break

    return TRACK_ALIAS_MAP.get(
        key,
        key,
    )


def normalise_horse_name(value: Any) -> str:
    text = normalise_text(value)

    text = re.sub(
        r"\s*\((?:AUS|NZ|IRE|GB|USA|FR|JPN|SAF|ARG|BRZ|GER|CAN|CHI|URU|ITY|SWE|DEN|SIN|HK)\)\s*$",
        "",
        text,
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )


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
            for path in RAW_WAREHOUSE_ROOT.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
        ),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            "No canonical raw warehouse snapshot exists."
        )

    return candidates[0]


def read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )


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
    fieldnames: list[str] | None = None,
) -> None:
    if not rows and not fieldnames:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    fields = list(
        fieldnames or []
    )

    if not fields:
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)

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
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    DIMENSION_WAREHOUSE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_snapshot_dir = (
        latest_raw_snapshot()
    )

    raw_manifest_path = (
        raw_snapshot_dir
        / "warehouse_manifest.json"
    )

    raw_manifest = read_json(
        raw_manifest_path
    )

    if (
        raw_manifest.get(
            "warehouse_status"
        )
        !=
        "IMMUTABLE_CANONICAL_RAW_"
        "WAREHOUSE_MATERIALISED"
    ):
        raise RuntimeError(
            "Raw warehouse has not passed materialisation."
        )

    raw_snapshot_id = (
        raw_manifest[
            "warehouse_snapshot_id"
        ]
    )

    performance_path = (
        raw_snapshot_dir
        / "canonical_performance_evidence.csv"
    )

    sectional_path = (
        raw_snapshot_dir
        / "canonical_sectional_evidence.csv"
    )

    raw_performance_hash = (
        sha256_file(
            performance_path
        )
    )

    raw_sectional_hash = (
        sha256_file(
            sectional_path
        )
    )

    dimension_snapshot_id = stable_id(
        "dimension_snapshot",
        (
            f"{DIMENSION_VERSION}|"
            f"{raw_snapshot_id}|"
            f"{raw_performance_hash}|"
            f"{raw_sectional_hash}"
        ),
    )

    final_dir = (
        DIMENSION_WAREHOUSE_ROOT
        / dimension_snapshot_id
    )

    staging_dir = (
        DIMENSION_WAREHOUSE_ROOT
        / f".{dimension_snapshot_id}.staging"
    )

    if final_dir.exists():
        print(
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_2_DIMENSIONS_ALREADY_"
            "MATERIALISED_PASS",
            flush=True,
        )
        print(
            f"DIMENSION_WAREHOUSE={final_dir}",
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

    track_rows: dict[
        str,
        dict[str, Any],
    ] = {}

    meeting_rows: dict[
        str,
        dict[str, Any],
    ] = {}

    race_rows: dict[
        str,
        dict[str, Any],
    ] = {}

    horse_evidence_rows: dict[
        str,
        dict[str, Any],
    ] = {}

    track_conflicts = Counter()
    meeting_conflicts = Counter()
    race_conflicts = Counter()
    horse_evidence_conflicts = Counter()

    performance_map_path = (
        staging_dir
        / "performance_dimension_map.csv"
    )

    performance_map_fields = [
        "performance_id",
        "track_id",
        "meeting_id_v0_2",
        "race_id_v0_2",
        "horse_identity_evidence_id",
        "legacy_meeting_id",
        "legacy_race_id",
        "legacy_horse_id",
        "dimension_version",
        "raw_warehouse_snapshot_id",
    ]

    generated_at = utc_now()
    performance_rows = 0

    print(
        "PHASE1_2_BUILD_DIMENSIONS_START",
        flush=True,
    )

    with performance_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, performance_map_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as map_handle:
        reader = csv.DictReader(
            source_handle
        )

        map_writer = csv.DictWriter(
            map_handle,
            fieldnames=performance_map_fields,
        )
        map_writer.writeheader()

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            performance_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "DIMENSION_BUILD_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )
            race_date = normalise_date(
                row.get("race_date")
            )
            state = normalise_text(
                row.get("state")
            )
            canonical_track = (
                normalise_track(
                    row.get("track")
                )
            )
            race_number = (
                normalise_integer(
                    row.get("race_number")
                )
            )
            provider_race_id = clean(
                row.get(
                    "provider_race_id"
                )
            )
            provider_runner_id = clean(
                row.get(
                    "provider_runner_id"
                )
            )
            horse_name = normalise_text(
                row.get("horse_name")
            )
            canonical_horse_name = (
                normalise_horse_name(
                    row.get("horse_name")
                )
            )

            required = (
                performance_id,
                race_date,
                state,
                canonical_track,
                race_number,
                provider_race_id,
                provider_runner_id,
                horse_name,
                canonical_horse_name,
            )

            if not all(required):
                raise RuntimeError(
                    "Incomplete dimension evidence "
                    f"at performance row {row_number}."
                )

            track_natural_key = (
                f"{state}|{canonical_track}"
            )

            track_id = stable_id(
                "track",
                track_natural_key,
            )

            track_record = {
                "track_id": track_id,
                "jurisdiction_code": state,
                "canonical_track_name": (
                    canonical_track
                ),
                "identity_status": (
                    "CANONICAL_CONTEXT_ID"
                ),
                "dimension_version": (
                    DIMENSION_VERSION
                ),
                "generated_at": (
                    generated_at
                ),
            }

            existing_track = (
                track_rows.get(track_id)
            )

            if (
                existing_track
                and existing_track
                != track_record
            ):
                track_conflicts[
                    track_id
                ] += 1
            else:
                track_rows[
                    track_id
                ] = track_record

            meeting_natural_key = (
                f"{race_date}|"
                f"{state}|"
                f"{track_id}"
            )

            meeting_id_v0_2 = stable_id(
                "meeting",
                meeting_natural_key,
            )

            meeting_record = {
                "meeting_id": (
                    meeting_id_v0_2
                ),
                "meeting_date": race_date,
                "jurisdiction_code": (
                    state
                ),
                "track_id": track_id,
                "identity_status": (
                    "CANONICAL_CONTEXT_ID"
                ),
                "dimension_version": (
                    DIMENSION_VERSION
                ),
                "generated_at": (
                    generated_at
                ),
            }

            existing_meeting = (
                meeting_rows.get(
                    meeting_id_v0_2
                )
            )

            if (
                existing_meeting
                and existing_meeting
                != meeting_record
            ):
                meeting_conflicts[
                    meeting_id_v0_2
                ] += 1
            else:
                meeting_rows[
                    meeting_id_v0_2
                ] = meeting_record

            race_natural_key = (
                f"{meeting_id_v0_2}|"
                f"{race_number}|"
                f"{provider_race_id}"
            )

            race_id_v0_2 = stable_id(
                "race",
                race_natural_key,
            )

            race_record = {
                "race_id": race_id_v0_2,
                "meeting_id": (
                    meeting_id_v0_2
                ),
                "race_number": race_number,
                "provider_code": (
                    "RACING_COM_GRAPHQL"
                ),
                "provider_race_id": (
                    provider_race_id
                ),
                "identity_status": (
                    "CANONICAL_CONTEXT_ID"
                ),
                "dimension_version": (
                    DIMENSION_VERSION
                ),
                "generated_at": (
                    generated_at
                ),
            }

            existing_race = (
                race_rows.get(
                    race_id_v0_2
                )
            )

            if (
                existing_race
                and existing_race
                != race_record
            ):
                race_conflicts[
                    race_id_v0_2
                ] += 1
            else:
                race_rows[
                    race_id_v0_2
                ] = race_record

            horse_evidence_natural_key = (
                f"RACING_COM_GRAPHQL|"
                f"{provider_runner_id}|"
                f"{canonical_horse_name}"
            )

            horse_identity_evidence_id = (
                stable_id(
                    "horse_identity_evidence",
                    horse_evidence_natural_key,
                )
            )

            horse_evidence_record = {
                "horse_identity_evidence_id": (
                    horse_identity_evidence_id
                ),
                "provider_code": (
                    "RACING_COM_GRAPHQL"
                ),
                "provider_runner_id": (
                    provider_runner_id
                ),
                "raw_horse_name": (
                    horse_name
                ),
                "normalised_horse_name": (
                    canonical_horse_name
                ),
                "identity_status": (
                    "PROVIDER_RUNNER_ID_"
                    "UNVERIFIED_AS_DURABLE_"
                    "HORSE_ID"
                ),
                "canonical_horse_id": "",
                "dimension_version": (
                    DIMENSION_VERSION
                ),
                "generated_at": (
                    generated_at
                ),
            }

            existing_horse_evidence = (
                horse_evidence_rows.get(
                    horse_identity_evidence_id
                )
            )

            if (
                existing_horse_evidence
                and existing_horse_evidence
                != horse_evidence_record
            ):
                horse_evidence_conflicts[
                    horse_identity_evidence_id
                ] += 1
            else:
                horse_evidence_rows[
                    horse_identity_evidence_id
                ] = horse_evidence_record

            map_writer.writerow(
                {
                    "performance_id": (
                        performance_id
                    ),
                    "track_id": track_id,
                    "meeting_id_v0_2": (
                        meeting_id_v0_2
                    ),
                    "race_id_v0_2": (
                        race_id_v0_2
                    ),
                    "horse_identity_evidence_id": (
                        horse_identity_evidence_id
                    ),
                    "legacy_meeting_id": clean(
                        row.get("meeting_id")
                    ),
                    "legacy_race_id": clean(
                        row.get("race_id")
                    ),
                    "legacy_horse_id": clean(
                        row.get("horse_id")
                    ),
                    "dimension_version": (
                        DIMENSION_VERSION
                    ),
                    "raw_warehouse_snapshot_id": (
                        raw_snapshot_id
                    ),
                }
            )

    track_path = (
        staging_dir
        / "track_dimension.csv"
    )

    meeting_path = (
        staging_dir
        / "meeting_dimension.csv"
    )

    race_path = (
        staging_dir
        / "race_dimension.csv"
    )

    horse_evidence_path = (
        staging_dir
        / "horse_identity_evidence_dimension.csv"
    )

    write_csv(
        track_path,
        sorted(
            track_rows.values(),
            key=lambda row: (
                row[
                    "jurisdiction_code"
                ],
                row[
                    "canonical_track_name"
                ],
            ),
        ),
    )

    write_csv(
        meeting_path,
        sorted(
            meeting_rows.values(),
            key=lambda row: (
                row["meeting_date"],
                row["meeting_id"],
            ),
        ),
    )

    write_csv(
        race_path,
        sorted(
            race_rows.values(),
            key=lambda row: (
                row["meeting_id"],
                int(
                    row["race_number"]
                ),
            ),
        ),
    )

    write_csv(
        horse_evidence_path,
        sorted(
            horse_evidence_rows.values(),
            key=lambda row: (
                row[
                    "normalised_horse_name"
                ],
                row[
                    "provider_runner_id"
                ],
            ),
        ),
    )

    performance_map_hash = (
        sha256_file(
            performance_map_path
        )
    )

    sectional_map_path = (
        staging_dir
        / "sectional_dimension_map.csv"
    )

    performance_dimension_lookup: dict[
        str,
        dict[str, str],
    ] = {}

    with performance_map_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            performance_dimension_lookup[
                clean(
                    row.get(
                        "performance_id"
                    )
                )
            ] = row

    sectional_rows = 0
    missing_sectional_performance = 0

    sectional_map_fields = [
        "performance_sectional_id",
        "performance_id",
        "track_id",
        "meeting_id_v0_2",
        "race_id_v0_2",
        "horse_identity_evidence_id",
        "dimension_version",
        "raw_warehouse_snapshot_id",
    ]

    print(
        "PHASE1_2_BUILD_SECTIONAL_MAP_START",
        flush=True,
    )

    with sectional_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, sectional_map_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_handle:
        reader = csv.DictReader(
            source_handle
        )

        writer = csv.DictWriter(
            output_handle,
            fieldnames=sectional_map_fields,
        )
        writer.writeheader()

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            sectional_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "SECTIONAL_DIMENSION_MAP_"
                    f"PROGRESS={row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )

            dimension = (
                performance_dimension_lookup.get(
                    performance_id
                )
            )

            if not dimension:
                missing_sectional_performance += 1
                continue

            writer.writerow(
                {
                    "performance_sectional_id": (
                        clean(
                            row.get(
                                "performance_sectional_id"
                            )
                        )
                    ),
                    "performance_id": (
                        performance_id
                    ),
                    "track_id": (
                        dimension["track_id"]
                    ),
                    "meeting_id_v0_2": (
                        dimension[
                            "meeting_id_v0_2"
                        ]
                    ),
                    "race_id_v0_2": (
                        dimension[
                            "race_id_v0_2"
                        ]
                    ),
                    "horse_identity_evidence_id": (
                        dimension[
                            "horse_identity_evidence_id"
                        ]
                    ),
                    "dimension_version": (
                        DIMENSION_VERSION
                    ),
                    "raw_warehouse_snapshot_id": (
                        raw_snapshot_id
                    ),
                }
            )

    checks = [
        {
            "check": (
                "RAW_WAREHOUSE_STATUS"
            ),
            "passed": True,
            "observed": (
                raw_manifest[
                    "warehouse_status"
                ]
            ),
        },
        {
            "check": (
                "PERFORMANCE_MAP_ROW_COUNT"
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
                "SECTIONAL_MAP_ROW_COUNT"
            ),
            "passed": (
                sectional_rows
                == 103766
                and
                missing_sectional_performance
                == 0
            ),
            "observed": (
                f"rows={sectional_rows};"
                f"missing_performance="
                f"{missing_sectional_performance}"
            ),
        },
        {
            "check": (
                "TRACK_DIMENSION_CONFLICTS"
            ),
            "passed": (
                not track_conflicts
            ),
            "observed": (
                sum(
                    track_conflicts.values()
                )
            ),
        },
        {
            "check": (
                "MEETING_DIMENSION_CONFLICTS"
            ),
            "passed": (
                not meeting_conflicts
            ),
            "observed": (
                sum(
                    meeting_conflicts.values()
                )
            ),
        },
        {
            "check": (
                "RACE_DIMENSION_CONFLICTS"
            ),
            "passed": (
                not race_conflicts
            ),
            "observed": (
                sum(
                    race_conflicts.values()
                )
            ),
        },
        {
            "check": (
                "HORSE_IDENTITY_EVIDENCE_"
                "CONFLICTS"
            ),
            "passed": (
                not horse_evidence_conflicts
            ),
            "observed": (
                sum(
                    horse_evidence_conflicts.values()
                )
            ),
        },
        {
            "check": (
                "CANONICAL_HORSE_NOT_"
                "FABRICATED"
            ),
            "passed": all(
                not row[
                    "canonical_horse_id"
                ]
                for row
                in horse_evidence_rows.values()
            ),
            "observed": (
                "ALL_CANONICAL_HORSE_IDS_"
                "REMAIN_UNASSIGNED"
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
            "Phase 1.2 checks failed: "
            + " | ".join(
                failed_checks
            )
        )

    asset_catalog = [
        {
            "asset_name": (
                "track_dimension"
            ),
            "asset_file": (
                track_path.name
            ),
            "rows": len(
                track_rows
            ),
            "primary_key": "track_id",
            "identity_status": (
                "CANONICAL_CONTEXT_ID"
            ),
            "sha256": (
                sha256_file(track_path)
            ),
        },
        {
            "asset_name": (
                "meeting_dimension"
            ),
            "asset_file": (
                meeting_path.name
            ),
            "rows": len(
                meeting_rows
            ),
            "primary_key": "meeting_id",
            "identity_status": (
                "CANONICAL_CONTEXT_ID"
            ),
            "sha256": (
                sha256_file(meeting_path)
            ),
        },
        {
            "asset_name": (
                "race_dimension"
            ),
            "asset_file": race_path.name,
            "rows": len(race_rows),
            "primary_key": "race_id",
            "identity_status": (
                "CANONICAL_CONTEXT_ID"
            ),
            "sha256": (
                sha256_file(race_path)
            ),
        },
        {
            "asset_name": (
                "horse_identity_evidence_dimension"
            ),
            "asset_file": (
                horse_evidence_path.name
            ),
            "rows": len(
                horse_evidence_rows
            ),
            "primary_key": (
                "horse_identity_evidence_id"
            ),
            "identity_status": (
                "PROVIDER_IDENTITY_EVIDENCE_"
                "NOT_CANONICAL_HORSE"
            ),
            "sha256": (
                sha256_file(
                    horse_evidence_path
                )
            ),
        },
        {
            "asset_name": (
                "performance_dimension_map"
            ),
            "asset_file": (
                performance_map_path.name
            ),
            "rows": performance_rows,
            "primary_key": (
                "performance_id"
            ),
            "identity_status": (
                "CANONICAL_MAPPING"
            ),
            "sha256": (
                performance_map_hash
            ),
        },
        {
            "asset_name": (
                "sectional_dimension_map"
            ),
            "asset_file": (
                sectional_map_path.name
            ),
            "rows": sectional_rows,
            "primary_key": (
                "performance_sectional_id"
            ),
            "identity_status": (
                "CANONICAL_MAPPING"
            ),
            "sha256": (
                sha256_file(
                    sectional_map_path
                )
            ),
        },
    ]

    catalog_path = (
        staging_dir
        / "asset_catalog.csv"
    )

    checks_path = (
        staging_dir
        / "materialisation_checks.csv"
    )

    write_csv(
        catalog_path,
        asset_catalog,
    )

    write_csv(
        checks_path,
        checks,
    )

    manifest = {
        "warehouse_name": (
            "EDGEiQ Canonical Identity "
            "Dimension Warehouse"
        ),
        "dimension_version": (
            DIMENSION_VERSION
        ),
        "materialisation_version": (
            MATERIALISATION_VERSION
        ),
        "dimension_snapshot_id": (
            dimension_snapshot_id
        ),
        "raw_warehouse_snapshot_id": (
            raw_snapshot_id
        ),
        "generated_utc": (
            generated_at
        ),
        "immutable": True,
        "production_application_modified": (
            False
        ),
        "canonical_horse_dimension_status": (
            "NOT_YET_MATERIALISED"
        ),
        "horse_identity_rule": (
            "Provider runner identifiers are "
            "preserved as evidence and are not "
            "declared durable canonical horse IDs."
        ),
        "assets": asset_catalog,
        "materialisation_checks": (
            checks
        ),
        "failed_checks": [],
        "warehouse_status": (
            "IMMUTABLE_IDENTITY_DIMENSIONS_"
            "MATERIALISED"
        ),
        "promotion_status": (
            "NOT_CONNECTED_TO_PRODUCT"
        ),
        "next_stage": (
            "Phase 1.3 canonical horse identity "
            "resolution architecture and evidence "
            "linkage audit."
        ),
    }

    manifest_path = (
        staging_dir
        / "dimension_manifest.json"
    )

    write_json(
        manifest_path,
        manifest,
    )

    integrity_manifest = {
        "dimension_snapshot_id": (
            dimension_snapshot_id
        ),
        "raw_warehouse_snapshot_id": (
            raw_snapshot_id
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
                track_path,
                meeting_path,
                race_path,
                horse_evidence_path,
                performance_map_path,
                sectional_map_path,
                catalog_path,
                checks_path,
                manifest_path,
            )
        ],
    }

    integrity_path = (
        staging_dir
        / "integrity_manifest.json"
    )

    write_json(
        integrity_path,
        integrity_manifest,
    )

    staging_dir.rename(
        final_dir
    )

    for path in final_dir.rglob("*"):
        if path.is_file():
            make_read_only(path)

    audit_summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_2_summary_{dimension_snapshot_id}.json"
        )
    )

    audit_latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_2_latest.json"
        )
    )

    audit_checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_2_checks_{dimension_snapshot_id}.csv"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_2_REPORT_{dimension_snapshot_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_CANONICAL_IDENTITY_"
            "DIMENSIONS_V0_1.md"
        )
    )

    write_json(
        audit_summary_path,
        manifest,
    )

    write_json(
        audit_latest_path,
        manifest,
    )

    write_csv(
        audit_checks_path,
        checks,
    )

    architecture_path.write_text(
        """# EDGEiQ Canonical Identity Dimensions V0.1

## Materialised canonical dimensions

- Track
- Meeting
- Race

These identities are derived from complete race context and deterministic UUID identities.

## Horse identity boundary

A provider runner identifier is not assumed to represent one durable horse through its entire career.

Phase 1.2 therefore materialises:

`horse_identity_evidence_dimension`

It does not yet materialise:

`canonical_horse_dimension`

## Canonical horse promotion requirements

A durable horse identity requires governed corroboration using evidence such as:

- provider horse registration identity
- jurisdiction horse code
- country suffix
- foaling year
- sex
- pedigree
- historical trainer continuity
- temporal name history
- validated entity-graph evidence

Name-only matching is insufficient.

## Product boundary

These dimensions remain disconnected from the production application.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.2 Canonical Identity Dimension Materialisation

Generated UTC: `{generated_at}`

Dimension snapshot ID: `{dimension_snapshot_id}`

Status: **IMMUTABLE_IDENTITY_DIMENSIONS_MATERIALISED**

- Tracks: **{len(track_rows):,}**
- Meetings: **{len(meeting_rows):,}**
- Races: **{len(race_rows):,}**
- Horse identity-evidence records: **{len(horse_evidence_rows):,}**
- Performance mappings: **{performance_rows:,}**
- Sectional mappings: **{sectional_rows:,}**
- Failed checks: **0**
- Canonical horses fabricated: **0**

Production data was not modified.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_2_CANONICAL_IDENTITY_"
        "DIMENSIONS_MATERIALISATION_PASS",
        flush=True,
    )

    print(
        f"DIMENSION_SNAPSHOT_ID="
        f"{dimension_snapshot_id}",
        flush=True,
    )

    print(
        f"DIMENSION_WAREHOUSE="
        f"{final_dir}",
        flush=True,
    )

    print(
        f"MANIFEST="
        f"{final_dir / 'dimension_manifest.json'}",
        flush=True,
    )

    print(
        f"INTEGRITY_MANIFEST="
        f"{final_dir / 'integrity_manifest.json'}",
        flush=True,
    )

    print(
        f"AUDIT_SUMMARY="
        f"{audit_summary_path}",
        flush=True,
    )

    print(
        f"REPORT={report_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
