from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

SOURCE_RESULTS = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

SOURCE_SECTIONALS = (
    ROOT
    / "public"
    / "data"
    / "racingcom_sectional_warehouse_v2.csv"
)

PHASE04_AUDIT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_4"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_5"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_5"
)

EDGEIQ_NAMESPACE = uuid.UUID(
    "ed91a5d8-e8e7-5b0f-a108-cd9c41c36901"
)

PROTOTYPE_VERSION = "0.1"
IDENTITY_VERSION = "PERFORMANCE_IDENTITY_PROTOTYPE_V0_1"
SOURCE_EVIDENCE_VERSION = "SOURCE_EVIDENCE_PROTOTYPE_V0_1"

PROGRESS_INTERVAL = 100_000
SAMPLE_LIMIT = 20

DATE_FIELDS = (
    "race_date",
    "meeting_date",
    "date",
)

TRACK_FIELDS = (
    "track",
    "venue_name",
    "track_name",
)

RACE_ID_FIELDS = (
    "race_id",
    "race_key",
)

RACE_NUMBER_FIELDS = (
    "race_no",
    "race_number",
)

RUNNER_ID_FIELDS = (
    "runner_id",
    "horse_code",
    "runner_code",
)

HORSE_NAME_FIELDS = (
    "horse",
    "horse_name",
    "runner_name",
)

MEETING_ID_FIELDS = (
    "meeting_id",
    "meet_code",
)

STATE_FIELDS = (
    "state",
    "jurisdiction",
)

SOURCE_PROVIDER = "RACING_COM_GRAPHQL"

QUALITY_COMPLETE = "COMPLETE"
QUALITY_PARTIAL = "PARTIAL"
QUALITY_IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
QUALITY_SOURCE_CONFLICT = "SOURCE_CONFLICT"

BOM_AUDIT_SCRIPTS = [
    "scripts/build_edgeiq_canonical_results_truth_v1.py",
    "scripts/build_edgeiq_historical_performance_rating_v6_1_research.py",
    "scripts/build_edgeiq_historical_results_warehouse_v2_graphql.py",
    "scripts/build_edgeiq_race_strength_history_v1.py",
    "scripts/build_edgeiq_race_strength_v3.py",
    "scripts/build_edgeiq_racingcom_results_warehouse_all_v1.py",
    "scripts/build_edgeiq_results_warehouse_full_consolidation_v1.py",
    "scripts/build_edgeiq_runner_history_detail_v1.py",
    "scripts/build_edgeiq_trusted_sectional_universe_v2.py",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_text(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\s+", " ", text)
    return text


def normalise_key_text(value: Any) -> str:
    text = normalise_text(value)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def first_value(
    row: dict[str, str],
    fields: tuple[str, ...],
) -> str:
    for field in fields:
        value = clean(row.get(field))
        if value:
            return value
    return ""


def normalise_date(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    )

    for date_format in formats:
        try:
            parsed = datetime.strptime(
                text[:19],
                date_format,
            )
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return match.group(1) if match else ""


def stable_id(
    entity_type: str,
    natural_key: str,
) -> str:
    payload = (
        f"{entity_type}|{natural_key}"
    )
    generated = uuid.uuid5(
        EDGEIQ_NAMESPACE,
        payload,
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
                4 * 1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def source_evidence_id(
    path: Path,
    file_hash: str,
) -> str:
    natural_key = (
        f"{path.name}|{file_hash}"
    )
    return stable_id(
        "source_evidence",
        natural_key,
    )


def canonical_meeting_natural_key(
    row: dict[str, str],
) -> str:
    provider_meeting_id = first_value(
        row,
        MEETING_ID_FIELDS,
    )

    if provider_meeting_id:
        return (
            f"{SOURCE_PROVIDER}|"
            f"{provider_meeting_id}"
        )

    race_date = normalise_date(
        first_value(
            row,
            DATE_FIELDS,
        )
    )
    track = normalise_key_text(
        first_value(
            row,
            TRACK_FIELDS,
        )
    )
    state = normalise_key_text(
        first_value(
            row,
            STATE_FIELDS,
        )
    )

    if race_date and track:
        return (
            f"{state}|{race_date}|{track}"
        )

    return ""


def canonical_race_natural_key(
    row: dict[str, str],
) -> str:
    provider_race_id = first_value(
        row,
        RACE_ID_FIELDS,
    )

    if provider_race_id:
        return (
            f"{SOURCE_PROVIDER}|"
            f"{provider_race_id}"
        )

    meeting_key = (
        canonical_meeting_natural_key(
            row
        )
    )
    race_number = first_value(
        row,
        RACE_NUMBER_FIELDS,
    )

    if meeting_key and race_number:
        return (
            f"{meeting_key}|"
            f"R{race_number}"
        )

    return ""


def canonical_horse_natural_key(
    row: dict[str, str],
) -> tuple[str, str]:
    provider_runner_id = first_value(
        row,
        RUNNER_ID_FIELDS,
    )

    if provider_runner_id:
        return (
            (
                f"{SOURCE_PROVIDER}|"
                f"{provider_runner_id}"
            ),
            "PROVIDER_RUNNER_ID",
        )

    horse_name = normalise_text(
        first_value(
            row,
            HORSE_NAME_FIELDS,
        )
    )

    if horse_name:
        return (
            f"NAME_ONLY|{horse_name}",
            "NAME_ONLY_UNVERIFIED",
        )

    return "", "UNRESOLVED"


def create_quality_state(
    race_key: str,
    horse_key: str,
    horse_method: str,
) -> str:
    if not race_key or not horse_key:
        return QUALITY_IDENTITY_UNRESOLVED

    if horse_method == "NAME_ONLY_UNVERIFIED":
        return QUALITY_PARTIAL

    return QUALITY_COMPLETE


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


def audit_bom_scripts() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for relative_path in BOM_AUDIT_SCRIPTS:
        path = ROOT / relative_path

        row: dict[str, Any] = {
            "path": relative_path,
            "exists": path.exists(),
            "has_utf8_bom": False,
            "parse_utf8_status": "",
            "parse_utf8_sig_status": "",
            "true_syntax_status": "",
            "error": "",
        }

        if not path.exists():
            row["true_syntax_status"] = (
                "FILE_NOT_FOUND"
            )
            rows.append(row)
            continue

        raw = path.read_bytes()
        row["has_utf8_bom"] = raw.startswith(
            b"\xef\xbb\xbf"
        )

        try:
            utf8_text = raw.decode("utf-8")
            ast.parse(utf8_text)
            row["parse_utf8_status"] = "PASS"
        except Exception as exc:
            row["parse_utf8_status"] = (
                f"FAIL: {exc}"
            )

        try:
            sig_text = raw.decode(
                "utf-8-sig"
            )
            ast.parse(sig_text)
            row["parse_utf8_sig_status"] = (
                "PASS"
            )
            row["true_syntax_status"] = (
                "VALID_PYTHON_WITH_UTF8_BOM"
                if row["has_utf8_bom"]
                else "VALID_PYTHON"
            )
        except Exception as exc:
            row["parse_utf8_sig_status"] = (
                f"FAIL: {exc}"
            )
            row["true_syntax_status"] = (
                "TRUE_SYNTAX_ERROR"
            )
            row["error"] = str(exc)

        rows.append(row)

    return rows


def build_source_evidence_records(
    generated_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for path, provider, evidence_type in (
        (
            SOURCE_RESULTS,
            SOURCE_PROVIDER,
            "OFFICIAL_RESULTS_GRAPHQL_WAREHOUSE",
        ),
        (
            SOURCE_SECTIONALS,
            "RACING_COM_SECTIONALS",
            "RUNNER_SECTIONAL_WAREHOUSE",
        ),
    ):
        if not path.exists():
            continue

        file_hash = sha256_file(path)

        rows.append(
            {
                "source_evidence_id": (
                    source_evidence_id(
                        path,
                        file_hash,
                    )
                ),
                "provider_code": provider,
                "provider_record_id": "",
                "source_url": "",
                "source_file": str(
                    path.relative_to(ROOT)
                ).replace("\\", "/"),
                "source_sha256": file_hash,
                "source_published_at": "",
                "ingested_at": (
                    datetime.fromtimestamp(
                        path.stat().st_mtime,
                        tz=timezone.utc,
                    ).isoformat()
                ),
                "evidence_version": 1,
                "supersedes_source_evidence_id": "",
                "is_current_version": True,
                "raw_payload_location": str(
                    path.relative_to(ROOT)
                ).replace("\\", "/"),
                "evidence_type": evidence_type,
                "prototype_version": (
                    SOURCE_EVIDENCE_VERSION
                ),
                "prototype_generated_at": (
                    generated_at
                ),
            }
        )

    return rows


def build_performance_identity_index(
    generated_at: str,
    results_source_evidence_id: str,
    output_path: Path,
    duplicate_path: Path,
    unresolved_path: Path,
) -> dict[str, Any]:
    row_count = 0
    unique_performance_ids: set[str] = set()
    duplicate_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()
    identity_method_counts: Counter[str] = Counter()
    unresolved_rows: list[dict[str, Any]] = []
    duplicate_samples: list[dict[str, Any]] = []
    horse_ids: set[str] = set()
    race_ids: set[str] = set()
    meeting_ids: set[str] = set()
    dates: list[str] = []

    with SOURCE_RESULTS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_handle:
        reader = csv.DictReader(
            source_handle
        )

        fields = [
            "performance_id",
            "race_id",
            "meeting_id",
            "horse_id",
            "source_evidence_id",
            "source_row_number",
            "provider_race_id",
            "provider_runner_id",
            "race_date",
            "state",
            "track",
            "race_number",
            "horse_name",
            "identity_method",
            "identity_quality_state",
            "identity_version",
            "evidence_version",
            "generated_at",
        ]

        writer = csv.DictWriter(
            output_handle,
            fieldnames=fields,
        )
        writer.writeheader()

        for source_row_number, row in enumerate(
            reader,
            start=2,
        ):
            row_count += 1

            if (
                row_count == 1
                or row_count
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "PERFORMANCE_ID_PROGRESS="
                    f"{row_count}",
                    flush=True,
                )

            meeting_key = (
                canonical_meeting_natural_key(
                    row
                )
            )
            race_key = (
                canonical_race_natural_key(
                    row
                )
            )
            (
                horse_key,
                horse_method,
            ) = canonical_horse_natural_key(
                row
            )

            quality_state = (
                create_quality_state(
                    race_key,
                    horse_key,
                    horse_method,
                )
            )

            meeting_id = (
                stable_id(
                    "meeting",
                    meeting_key,
                )
                if meeting_key
                else ""
            )
            race_id = (
                stable_id(
                    "race",
                    race_key,
                )
                if race_key
                else ""
            )
            horse_id = (
                stable_id(
                    "horse",
                    horse_key,
                )
                if horse_key
                else ""
            )

            performance_id = ""

            if race_id and horse_id:
                performance_id = stable_id(
                    "performance",
                    (
                        f"{race_id}|"
                        f"{horse_id}"
                    ),
                )

            if performance_id:
                duplicate_counts[
                    performance_id
                ] += 1

                if (
                    duplicate_counts[
                        performance_id
                    ]
                    > 1
                    and len(
                        duplicate_samples
                    )
                    < 500
                ):
                    duplicate_samples.append(
                        {
                            "performance_id": (
                                performance_id
                            ),
                            "source_row_number": (
                                source_row_number
                            ),
                            "provider_race_id": (
                                first_value(
                                    row,
                                    RACE_ID_FIELDS,
                                )
                            ),
                            "provider_runner_id": (
                                first_value(
                                    row,
                                    RUNNER_ID_FIELDS,
                                )
                            ),
                            "horse_name": (
                                first_value(
                                    row,
                                    HORSE_NAME_FIELDS,
                                )
                            ),
                            "reason": (
                                "MULTIPLE_SOURCE_ROWS_"
                                "FOR_SAME_CANONICAL_"
                                "PERFORMANCE"
                            ),
                        }
                    )

                unique_performance_ids.add(
                    performance_id
                )

            race_date = normalise_date(
                first_value(
                    row,
                    DATE_FIELDS,
                )
            )

            if race_date:
                dates.append(race_date)

            if meeting_id:
                meeting_ids.add(
                    meeting_id
                )
            if race_id:
                race_ids.add(race_id)
            if horse_id:
                horse_ids.add(horse_id)

            quality_counts[
                quality_state
            ] += 1
            identity_method_counts[
                horse_method
            ] += 1

            if (
                quality_state
                == QUALITY_IDENTITY_UNRESOLVED
                and len(
                    unresolved_rows
                )
                < 10_000
            ):
                unresolved_rows.append(
                    {
                        "source_row_number": (
                            source_row_number
                        ),
                        "provider_race_id": (
                            first_value(
                                row,
                                RACE_ID_FIELDS,
                            )
                        ),
                        "provider_runner_id": (
                            first_value(
                                row,
                                RUNNER_ID_FIELDS,
                            )
                        ),
                        "race_date": race_date,
                        "track": first_value(
                            row,
                            TRACK_FIELDS,
                        ),
                        "race_number": (
                            first_value(
                                row,
                                RACE_NUMBER_FIELDS,
                            )
                        ),
                        "horse_name": (
                            first_value(
                                row,
                                HORSE_NAME_FIELDS,
                            )
                        ),
                        "missing_race_identity": (
                            not bool(race_key)
                        ),
                        "missing_horse_identity": (
                            not bool(horse_key)
                        ),
                    }
                )

            writer.writerow(
                {
                    "performance_id": (
                        performance_id
                    ),
                    "race_id": race_id,
                    "meeting_id": meeting_id,
                    "horse_id": horse_id,
                    "source_evidence_id": (
                        results_source_evidence_id
                    ),
                    "source_row_number": (
                        source_row_number
                    ),
                    "provider_race_id": (
                        first_value(
                            row,
                            RACE_ID_FIELDS,
                        )
                    ),
                    "provider_runner_id": (
                        first_value(
                            row,
                            RUNNER_ID_FIELDS,
                        )
                    ),
                    "race_date": race_date,
                    "state": first_value(
                        row,
                        STATE_FIELDS,
                    ),
                    "track": first_value(
                        row,
                        TRACK_FIELDS,
                    ),
                    "race_number": (
                        first_value(
                            row,
                            RACE_NUMBER_FIELDS,
                        )
                    ),
                    "horse_name": (
                        first_value(
                            row,
                            HORSE_NAME_FIELDS,
                        )
                    ),
                    "identity_method": (
                        horse_method
                    ),
                    "identity_quality_state": (
                        quality_state
                    ),
                    "identity_version": (
                        IDENTITY_VERSION
                    ),
                    "evidence_version": 1,
                    "generated_at": (
                        generated_at
                    ),
                }
            )

    duplicates = [
        {
            "performance_id": key,
            "source_row_count": count,
            "duplicate_row_count": (
                count - 1
            ),
        }
        for key, count
        in duplicate_counts.items()
        if count > 1
    ]

    write_csv(
        duplicate_path,
        sorted(
            duplicates,
            key=lambda item: (
                -item[
                    "source_row_count"
                ],
                item[
                    "performance_id"
                ],
            ),
        ),
    )

    write_csv(
        unresolved_path,
        unresolved_rows,
    )

    return {
        "source_rows": row_count,
        "unique_meetings": len(
            meeting_ids
        ),
        "unique_races": len(
            race_ids
        ),
        "unique_horses": len(
            horse_ids
        ),
        "unique_performances": len(
            unique_performance_ids
        ),
        "duplicate_performance_ids": len(
            duplicates
        ),
        "duplicate_source_rows": sum(
            item[
                "duplicate_row_count"
            ]
            for item in duplicates
        ),
        "unresolved_rows": (
            quality_counts[
                QUALITY_IDENTITY_UNRESOLVED
            ]
        ),
        "quality_counts": dict(
            sorted(
                quality_counts.items()
            )
        ),
        "identity_method_counts": dict(
            sorted(
                identity_method_counts.items()
            )
        ),
        "min_race_date": (
            min(dates)
            if dates
            else ""
        ),
        "max_race_date": (
            max(dates)
            if dates
            else ""
        ),
        "duplicate_samples": (
            duplicate_samples[
                :SAMPLE_LIMIT
            ]
        ),
    }


def build_sectional_linkage_audit(
    performance_index_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    performance_by_provider: dict[
        tuple[str, str],
        str,
    ] = {}

    performance_by_race_horse: dict[
        tuple[str, str, str, str],
        list[str],
    ] = defaultdict(list)

    with performance_index_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            performance_id = clean(
                row.get("performance_id")
            )
            provider_race_id = clean(
                row.get("provider_race_id")
            )
            provider_runner_id = clean(
                row.get("provider_runner_id")
            )

            if (
                performance_id
                and provider_race_id
                and provider_runner_id
            ):
                performance_by_provider[
                    (
                        provider_race_id,
                        provider_runner_id,
                    )
                ] = performance_id

            race_date = clean(
                row.get("race_date")
            )
            track = normalise_key_text(
                row.get("track")
            )
            race_number = clean(
                row.get("race_number")
            )
            horse_name = normalise_text(
                row.get("horse_name")
            )

            if (
                performance_id
                and race_date
                and track
                and race_number
                and horse_name
            ):
                performance_by_race_horse[
                    (
                        race_date,
                        track,
                        race_number,
                        horse_name,
                    )
                ].append(
                    performance_id
                )

    source_rows = 0
    linked_rows = 0
    provider_id_links = 0
    composite_links = 0
    ambiguous_rows = 0
    unlinked_rows = 0
    status_counts: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []

    with SOURCE_SECTIONALS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_handle:
        reader = csv.DictReader(
            source_handle
        )

        fields = [
            "sectional_source_row",
            "performance_id",
            "link_status",
            "link_method",
            "provider_race_id",
            "provider_runner_id",
            "race_date",
            "track",
            "race_number",
            "horse_name",
        ]

        writer = csv.DictWriter(
            output_handle,
            fieldnames=fields,
        )
        writer.writeheader()

        for source_row_number, row in enumerate(
            reader,
            start=2,
        ):
            source_rows += 1

            if (
                source_rows == 1
                or source_rows
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "SECTIONAL_LINK_PROGRESS="
                    f"{source_rows}",
                    flush=True,
                )

            provider_race_id = first_value(
                row,
                (
                    "race_id",
                    "provider_race_id",
                    "race_key",
                ),
            )
            provider_runner_id = first_value(
                row,
                (
                    "runner_id",
                    "provider_runner_id",
                    "horse_code",
                ),
            )

            performance_id = ""
            link_status = "UNLINKED"
            link_method = "NONE"

            if (
                provider_race_id
                and provider_runner_id
            ):
                performance_id = (
                    performance_by_provider.get(
                        (
                            provider_race_id,
                            provider_runner_id,
                        ),
                        "",
                    )
                )

                if performance_id:
                    link_status = "LINKED"
                    link_method = (
                        "PROVIDER_RACE_RUNNER_ID"
                    )
                    provider_id_links += 1

            race_date = normalise_date(
                first_value(
                    row,
                    DATE_FIELDS,
                )
            )
            track = first_value(
                row,
                TRACK_FIELDS,
            )
            race_number = first_value(
                row,
                RACE_NUMBER_FIELDS,
            )
            horse_name = first_value(
                row,
                HORSE_NAME_FIELDS,
            )

            if not performance_id:
                candidates = (
                    performance_by_race_horse.get(
                        (
                            race_date,
                            normalise_key_text(
                                track
                            ),
                            race_number,
                            normalise_text(
                                horse_name
                            ),
                        ),
                        [],
                    )
                )

                unique_candidates = sorted(
                    set(candidates)
                )

                if len(unique_candidates) == 1:
                    performance_id = (
                        unique_candidates[0]
                    )
                    link_status = "LINKED"
                    link_method = (
                        "DATE_TRACK_RACE_HORSE"
                    )
                    composite_links += 1
                elif len(unique_candidates) > 1:
                    link_status = "AMBIGUOUS"
                    link_method = (
                        "MULTIPLE_COMPOSITE_"
                        "CANDIDATES"
                    )
                    ambiguous_rows += 1
                else:
                    unlinked_rows += 1

            if performance_id:
                linked_rows += 1

            status_counts[
                link_status
            ] += 1

            writer.writerow(
                {
                    "sectional_source_row": (
                        source_row_number
                    ),
                    "performance_id": (
                        performance_id
                    ),
                    "link_status": link_status,
                    "link_method": link_method,
                    "provider_race_id": (
                        provider_race_id
                    ),
                    "provider_runner_id": (
                        provider_runner_id
                    ),
                    "race_date": race_date,
                    "track": track,
                    "race_number": (
                        race_number
                    ),
                    "horse_name": (
                        horse_name
                    ),
                }
            )

            if (
                link_status != "LINKED"
                and len(samples)
                < SAMPLE_LIMIT
            ):
                samples.append(
                    {
                        "source_row_number": (
                            source_row_number
                        ),
                        "link_status": (
                            link_status
                        ),
                        "provider_race_id": (
                            provider_race_id
                        ),
                        "provider_runner_id": (
                            provider_runner_id
                        ),
                        "race_date": race_date,
                        "track": track,
                        "race_number": (
                            race_number
                        ),
                        "horse_name": (
                            horse_name
                        ),
                    }
                )

    return {
        "sectional_source_rows": source_rows,
        "linked_rows": linked_rows,
        "linkage_pct": (
            round(
                linked_rows
                / source_rows
                * 100,
                4,
            )
            if source_rows
            else 0.0
        ),
        "provider_id_links": (
            provider_id_links
        ),
        "composite_links": (
            composite_links
        ),
        "ambiguous_rows": ambiguous_rows,
        "unlinked_rows": unlinked_rows,
        "status_counts": dict(
            sorted(
                status_counts.items()
            )
        ),
        "unlinked_samples": samples,
    }


def report_markdown(
    summary: dict[str, Any],
) -> str:
    performance = summary[
        "performance_identity"
    ]
    sectional = summary[
        "sectional_linkage"
    ]
    bom = summary[
        "bom_syntax_correction"
    ]

    return f"""# EDGEiQ Performance Intelligence
## Phase 0.5 Canonical Identity and Source-Evidence Prototype

Generated UTC: `{summary["generated_utc"]}`

## Status

**{summary["status"]}**

This prototype does not modify any production result, sectional, rating or frontend feed.

## Source evidence

- Source evidence records: **{summary["source_evidence_records"]}**
- Results source: `{summary["results_source"]}`
- Sectional source: `{summary["sectional_source"]}`

## Canonical performance identity

- Source result rows: **{performance["source_rows"]:,}**
- Canonical meetings: **{performance["unique_meetings"]:,}**
- Canonical races: **{performance["unique_races"]:,}**
- Canonical horses: **{performance["unique_horses"]:,}**
- Canonical performances: **{performance["unique_performances"]:,}**
- Duplicate performance IDs: **{performance["duplicate_performance_ids"]:,}**
- Duplicate source rows: **{performance["duplicate_source_rows"]:,}**
- Identity-unresolved rows: **{performance["unresolved_rows"]:,}**
- Date coverage: **{performance["min_race_date"]} to {performance["max_race_date"]}**

## Sectional linkage

- Sectional source rows: **{sectional["sectional_source_rows"]:,}**
- Linked rows: **{sectional["linked_rows"]:,}**
- Linkage: **{sectional["linkage_pct"]}%**
- Provider-ID links: **{sectional["provider_id_links"]:,}**
- Composite links: **{sectional["composite_links"]:,}**
- Ambiguous rows: **{sectional["ambiguous_rows"]:,}**
- Unlinked rows: **{sectional["unlinked_rows"]:,}**

## UTF-8 BOM correction

- Scripts rechecked: **{bom["scripts_checked"]}**
- Valid Python with UTF-8 BOM: **{bom["valid_with_bom"]}**
- True syntax errors: **{bom["true_syntax_errors"]}**

The previous Phase 0.4 syntax report treated UTF-8 BOM markers as syntax errors because the files were parsed after plain UTF-8 decoding. This prototype rechecks them using `utf-8-sig`.

## Governance state

The prototype establishes deterministic IDs and immutable source-evidence records, but it is not yet the production warehouse.

Required before promotion:

1. Confirm provider runner IDs represent horses consistently through time.
2. Resolve duplicate performance evidence without deleting any source row.
3. Add formal horse alias and provider-identifier tables.
4. Validate sectional linkage quality.
5. Build evidence-version and supersession tests.
6. Create canonical migration audits before writing any production warehouse.
"""


def main() -> None:
    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not SOURCE_RESULTS.exists():
        raise FileNotFoundError(
            SOURCE_RESULTS
        )

    if not SOURCE_SECTIONALS.exists():
        raise FileNotFoundError(
            SOURCE_SECTIONALS
        )

    generated_at = utc_now()
    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    source_evidence_path = (
        PROTOTYPE_DIR
        / f"edgeiq_source_evidence_prototype_v0_1_{run_id}.csv"
    )
    performance_index_path = (
        PROTOTYPE_DIR
        / f"edgeiq_canonical_performance_identity_prototype_v0_1_{run_id}.csv"
    )
    duplicates_path = (
        AUDIT_DIR
        / f"edgeiq_performance_identity_duplicates_v0_1_{run_id}.csv"
    )
    unresolved_path = (
        AUDIT_DIR
        / f"edgeiq_performance_identity_unresolved_v0_1_{run_id}.csv"
    )
    sectional_linkage_path = (
        PROTOTYPE_DIR
        / f"edgeiq_sectional_performance_linkage_prototype_v0_1_{run_id}.csv"
    )
    bom_audit_path = (
        AUDIT_DIR
        / f"edgeiq_phase0_5_bom_syntax_correction_{run_id}.csv"
    )
    summary_path = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_5_summary_{run_id}.json"
    )
    latest_path = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase0_5_latest.json"
    )
    report_path = (
        AUDIT_DIR
        / f"EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE0_5_REPORT_{run_id}.md"
    )

    source_records = (
        build_source_evidence_records(
            generated_at
        )
    )
    write_csv(
        source_evidence_path,
        source_records,
    )

    results_record = next(
        row
        for row in source_records
        if row["source_file"]
        == str(
            SOURCE_RESULTS.relative_to(
                ROOT
            )
        ).replace("\\", "/")
    )

    print(
        "PHASE0_5_PERFORMANCE_IDENTITY_START",
        flush=True,
    )

    performance_summary = (
        build_performance_identity_index(
            generated_at,
            results_record[
                "source_evidence_id"
            ],
            performance_index_path,
            duplicates_path,
            unresolved_path,
        )
    )

    print(
        "PHASE0_5_SECTIONAL_LINKAGE_START",
        flush=True,
    )

    sectional_summary = (
        build_sectional_linkage_audit(
            performance_index_path,
            sectional_linkage_path,
        )
    )

    bom_rows = audit_bom_scripts()
    write_csv(
        bom_audit_path,
        bom_rows,
    )

    valid_with_bom = sum(
        1
        for row in bom_rows
        if row["true_syntax_status"]
        == "VALID_PYTHON_WITH_UTF8_BOM"
    )
    true_syntax_errors = sum(
        1
        for row in bom_rows
        if row["true_syntax_status"]
        == "TRUE_SYNTAX_ERROR"
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 0.5 Canonical Identity and "
            "Source-Evidence Prototype"
        ),
        "generated_utc": generated_at,
        "prototype_version": (
            PROTOTYPE_VERSION
        ),
        "status": (
            "PROTOTYPE_PASS"
            if true_syntax_errors == 0
            else "PROTOTYPE_PASS_WITH_"
            "TRUE_SYNTAX_ERRORS"
        ),
        "production_data_modified": False,
        "results_source": str(
            SOURCE_RESULTS.relative_to(
                ROOT
            )
        ).replace("\\", "/"),
        "sectional_source": str(
            SOURCE_SECTIONALS.relative_to(
                ROOT
            )
        ).replace("\\", "/"),
        "source_evidence_records": len(
            source_records
        ),
        "performance_identity": (
            performance_summary
        ),
        "sectional_linkage": (
            sectional_summary
        ),
        "bom_syntax_correction": {
            "scripts_checked": len(
                bom_rows
            ),
            "valid_with_bom": (
                valid_with_bom
            ),
            "true_syntax_errors": (
                true_syntax_errors
            ),
            "corrected_interpretation": (
                "UTF8_BOM_IS_NOT_A_TRUE_"
                "PYTHON_SYNTAX_ERROR"
            ),
        },
        "outputs": {
            "source_evidence": str(
                source_evidence_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "performance_identity": str(
                performance_index_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "performance_duplicates": str(
                duplicates_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "performance_unresolved": str(
                unresolved_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "sectional_linkage": str(
                sectional_linkage_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "bom_syntax_audit": str(
                bom_audit_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
        "canonical_status": (
            "PROTOTYPE_ONLY_NOT_PROMOTED"
        ),
        "next_stage": (
            "Phase 0.6 duplicate evidence, "
            "horse identity and sectional "
            "linkage resolution design"
        ),
    }

    write_json(
        summary_path,
        summary,
    )
    write_json(
        latest_path,
        summary,
    )

    report_path.write_text(
        report_markdown(summary),
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_5_CANONICAL_IDENTITY_"
        "PROTOTYPE_PASS",
        flush=True,
    )
    print(
        f"SOURCE_EVIDENCE={source_evidence_path}",
        flush=True,
    )
    print(
        f"PERFORMANCE_IDENTITY={performance_index_path}",
        flush=True,
    )
    print(
        f"DUPLICATES={duplicates_path}",
        flush=True,
    )
    print(
        f"UNRESOLVED={unresolved_path}",
        flush=True,
    )
    print(
        f"SECTIONAL_LINKAGE={sectional_linkage_path}",
        flush=True,
    )
    print(
        f"BOM_AUDIT={bom_audit_path}",
        flush=True,
    )
    print(
        f"SUMMARY={summary_path}",
        flush=True,
    )
    print(
        f"REPORT={report_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
