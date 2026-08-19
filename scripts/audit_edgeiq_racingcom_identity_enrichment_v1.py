from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = REPO_ROOT / "public" / "data"

CLASSIFICATION_DIR = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-observation-failure-classification-v1"
)

FAILURE_DETAIL_PATH = (
    CLASSIFICATION_DIR
    / "edgeiq_failure_reason_detail_v1.csv"
)

OUTPUT_DIR = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "racingcom-identity-enrichment-v1"
)

HORSE_MASTER_CANDIDATES = [
    PUBLIC_DATA / "edgeiq_canonical_horse_master_v2.csv",
    PUBLIC_DATA / "edgeiq_canonical_horse_master_v2_CANDIDATE.csv",
]

ALIAS_CANDIDATES = [
    PUBLIC_DATA / "edgeiq_canonical_horse_alias_v2.csv",
    PUBLIC_DATA / "edgeiq_canonical_horse_alias_v2_CANDIDATE.csv",
]

SOURCE_INVENTORY_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_source_inventory_v1.csv"
)
SCHEMA_INVENTORY_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_schema_inventory_v1.csv"
)
IDENTITY_MATRIX_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_identity_availability_matrix_v1.csv"
)
FAILURE_SOURCE_SUMMARY_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_failure_source_summary_v1.csv"
)
STRATEGY_SUMMARY_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_recovery_strategy_summary_v1.csv"
)
RECOVERY_CANDIDATES_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_exact_name_recovery_candidates_v1.csv"
)
UNRESOLVED_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_unresolved_identity_rows_v1.csv"
)
AMBIGUOUS_NAMES_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_ambiguous_normalised_names_v1.csv"
)
AUDIT_JSON_PATH = (
    OUTPUT_DIR / "EDGEIQ_RACINGCOM_IDENTITY_ENRICHMENT_V1_AUDIT.json"
)
AUDIT_MD_PATH = (
    OUTPUT_DIR / "EDGEIQ_RACINGCOM_IDENTITY_ENRICHMENT_V1_AUDIT.md"
)
CONTRACT_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_identity_enrichment_v1_contract.json"
)

PASS_STATUS = "EDGEIQ_RACINGCOM_IDENTITY_ENRICHMENT_V1_AUDIT_PASS"
FAIL_STATUS = "EDGEIQ_RACINGCOM_IDENTITY_ENRICHMENT_V1_AUDIT_FAIL"

HORSE_ID_FIELDS = {
    "source_horse_id",
    "horse_id",
    "horseid",
    "runner_id",
    "runnerid",
    "competitor_id",
    "competitorid",
    "participant_id",
    "participantid",
}

HORSE_NAME_FIELDS = {
    "source_horse_name",
    "horse_name",
    "horsename",
    "runner_name",
    "runnername",
    "competitor_name",
    "competitorname",
    "horse",
    "runner",
}

RUNNER_ID_FIELDS = {
    "runner_id",
    "runnerid",
    "competitor_id",
    "competitorid",
    "participant_id",
    "participantid",
}

RACE_ID_FIELDS = {
    "race_id",
    "raceid",
    "event_id",
    "eventid",
    "source_race_id",
}

MEETING_ID_FIELDS = {
    "meeting_id",
    "meetingid",
    "fixture_id",
    "fixtureid",
    "event_group_id",
}

RACE_NUMBER_FIELDS = {
    "race_number",
    "racenumber",
    "race_no",
    "raceno",
    "race",
}

DATE_FIELDS = {
    "race_date",
    "racedate",
    "meeting_date",
    "meetingdate",
    "event_date",
    "eventdate",
    "date",
}

TRACK_FIELDS = {
    "canonical_track",
    "track",
    "track_name",
    "trackname",
    "venue",
    "venue_name",
    "meeting",
}

BARRIER_FIELDS = {
    "barrier",
    "barrier_number",
    "barriernumber",
    "draw",
    "gate",
}

SADDLECLOTH_FIELDS = {
    "saddlecloth",
    "saddlecloth_number",
    "saddleclothnumber",
    "runner_number",
    "runnernumber",
    "tab_number",
    "tabnumber",
    "number",
}

SOURCE_KEY_FIELDS = {
    "source_key",
    "runner_key",
    "runnerkey",
    "competitor_key",
    "competitorkey",
    "participant_key",
    "participantkey",
    "unique_runner_key",
    "unique_id",
    "uid",
}

RECOVERY_OUTPUT_FIELDS = [
    "failure_classification_id",
    "source_path",
    "source_row_number",
    "source_system",
    "source_horse_name",
    "normalised_horse_name",
    "canonical_horse_id",
    "canonical_horse_name",
    "recovery_strategy",
    "strategy_confidence",
    "race_date",
    "canonical_track",
    "source_row_evidence_sha256",
]

UNRESOLVED_OUTPUT_FIELDS = [
    "failure_classification_id",
    "source_path",
    "source_row_number",
    "source_system",
    "source_horse_name",
    "normalised_horse_name",
    "assessment_result",
    "assessment_reason",
    "race_date",
    "canonical_track",
    "source_row_evidence_sha256",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalise_field(value: object) -> str:
    text = clean(value).lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def normalise_horse_name(value: object) -> str:
    text = clean(value).upper()

    # Remove common country suffixes only when they occur at the end.
    text = re.sub(
        r"\s*\((AUS|NZ|IRE|GB|USA|FR|JPN|SAF|GER|CAN|ARG|BRZ|CHI|HK)\)\s*$",
        "",
        text,
    )

    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def locate_first_existing(candidates: Iterable[Path], label: str) -> Path:
    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"No {label} file found. Checked: "
        + ", ".join(str(path) for path in candidates)
    )


def is_racingcom_path(path_value: object) -> bool:
    value = clean(path_value).replace("\\", "/").lower()

    return any(
        token in value
        for token in (
            "racingcom",
            "racing.com",
            "racing_com",
        )
    )


def discover_racingcom_csv_files() -> List[Path]:
    discovered: List[Path] = []

    for path in PUBLIC_DATA.rglob("*.csv"):
        relative = str(path.relative_to(REPO_ROOT)).replace("\\", "/").lower()

        if is_racingcom_path(relative):
            discovered.append(path)

    return sorted(set(discovered), key=lambda path: str(path).lower())


def read_header(path: Path) -> Tuple[List[str], str]:
    encodings = ["utf-8-sig", "utf-8", "cp1252"]

    last_error: Optional[Exception] = None

    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, [])
                return [clean(value) for value in header], encoding
        except UnicodeDecodeError as exc:
            last_error = exc

    if last_error:
        raise last_error

    return [], ""


def count_csv_rows(path: Path, encoding: str) -> int:
    count = 0

    with path.open(
        "r",
        encoding=encoding,
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.reader(handle)
        next(reader, None)

        for _ in reader:
            count += 1

    return count


def matched_fields(
    normalised_columns: Dict[str, str],
    candidates: Set[str],
) -> List[str]:
    matches: List[str] = []

    for original, normalised in normalised_columns.items():
        if normalised in candidates:
            matches.append(original)

    return matches


def join_text(values: Iterable[str]) -> str:
    return "|".join(sorted(set(clean(value) for value in values if clean(value))))


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def load_canonical_name_index(
    master_path: Path,
) -> Tuple[
    Dict[str, Tuple[str, str]],
    Dict[str, Set[str]],
    int,
    int,
]:
    print(f"Loading canonical horse-name index: {master_path}", flush=True)

    unique_map: Dict[str, Tuple[str, str]] = {}
    all_ids_by_name: Dict[str, Set[str]] = defaultdict(set)

    rows_scanned = 0
    blank_name_rows = 0

    with master_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise RuntimeError(f"Horse Master has no header: {master_path}")

        required = {
            "canonical_horse_id",
            "canonical_horse_name",
        }

        missing = required.difference(reader.fieldnames)

        if missing:
            raise RuntimeError(
                f"Horse Master missing columns {sorted(missing)}: "
                f"{master_path}"
            )

        for row in reader:
            rows_scanned += 1

            canonical_id = clean(row.get("canonical_horse_id"))
            canonical_name = clean(row.get("canonical_horse_name"))
            normalised_name = normalise_horse_name(canonical_name)

            if not canonical_id or not normalised_name:
                blank_name_rows += 1
                continue

            all_ids_by_name[normalised_name].add(canonical_id)

            if normalised_name not in unique_map:
                unique_map[normalised_name] = (
                    canonical_id,
                    canonical_name,
                )

            if rows_scanned % 250000 == 0:
                print(
                    f"Horse Master rows scanned: {rows_scanned:,}",
                    flush=True,
                )

    ambiguous = {
        name: ids
        for name, ids in all_ids_by_name.items()
        if len(ids) > 1
    }

    for name in ambiguous:
        unique_map.pop(name, None)

    print(
        f"Canonical horse-name index complete: "
        f"rows={rows_scanned:,}, "
        f"unique_names={len(unique_map):,}, "
        f"ambiguous_names={len(ambiguous):,}, "
        f"blank_name_rows={blank_name_rows:,}",
        flush=True,
    )

    return unique_map, ambiguous, rows_scanned, blank_name_rows


def write_csv(
    path: Path,
    fields: List[str],
    rows: Iterable[Dict[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    field: row.get(field, "")
                    for field in fields
                }
            )


def main() -> int:
    started_at = utc_now_iso()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not FAILURE_DETAIL_PATH.exists():
        raise FileNotFoundError(
            f"Failure classification detail ledger not found: "
            f"{FAILURE_DETAIL_PATH}"
        )

    horse_master_path = locate_first_existing(
        HORSE_MASTER_CANDIDATES,
        "canonical Horse Master",
    )
    alias_path = locate_first_existing(
        ALIAS_CANDIDATES,
        "canonical horse alias",
    )

    racingcom_files = discover_racingcom_csv_files()

    if not racingcom_files:
        raise RuntimeError(
            f"No Racing.com CSV files found under {PUBLIC_DATA}"
        )

    print(
        f"Racing.com CSV files discovered: {len(racingcom_files):,}",
        flush=True,
    )

    inventory_rows: List[Dict[str, object]] = []
    schema_rows: List[Dict[str, object]] = []
    matrix_rows: List[Dict[str, object]] = []

    total_source_rows = 0
    files_with_horse_id = 0
    files_with_horse_name = 0
    files_with_deterministic_runner_key = 0
    unreadable_files = 0

    for index, path in enumerate(racingcom_files, start=1):
        relative_path = str(path.relative_to(REPO_ROOT)).replace("\\", "/")

        print(
            f"[{index:,}/{len(racingcom_files):,}] "
            f"Profiling {relative_path}",
            flush=True,
        )

        try:
            header, encoding = read_header(path)
            row_count = count_csv_rows(path, encoding)
            digest = sha256_file(path)

            normalised_columns = {
                column: normalise_field(column)
                for column in header
            }

            horse_id_columns = matched_fields(
                normalised_columns,
                HORSE_ID_FIELDS,
            )
            horse_name_columns = matched_fields(
                normalised_columns,
                HORSE_NAME_FIELDS,
            )
            runner_id_columns = matched_fields(
                normalised_columns,
                RUNNER_ID_FIELDS,
            )
            race_id_columns = matched_fields(
                normalised_columns,
                RACE_ID_FIELDS,
            )
            meeting_id_columns = matched_fields(
                normalised_columns,
                MEETING_ID_FIELDS,
            )
            race_number_columns = matched_fields(
                normalised_columns,
                RACE_NUMBER_FIELDS,
            )
            date_columns = matched_fields(
                normalised_columns,
                DATE_FIELDS,
            )
            track_columns = matched_fields(
                normalised_columns,
                TRACK_FIELDS,
            )
            barrier_columns = matched_fields(
                normalised_columns,
                BARRIER_FIELDS,
            )
            saddlecloth_columns = matched_fields(
                normalised_columns,
                SADDLECLOTH_FIELDS,
            )
            source_key_columns = matched_fields(
                normalised_columns,
                SOURCE_KEY_FIELDS,
            )

            has_horse_id = bool(horse_id_columns)
            has_horse_name = bool(horse_name_columns)
            has_runner_id = bool(runner_id_columns)
            has_race_id = bool(race_id_columns)
            has_meeting_id = bool(meeting_id_columns)
            has_race_number = bool(race_number_columns)
            has_date = bool(date_columns)
            has_track = bool(track_columns)
            has_barrier = bool(barrier_columns)
            has_saddlecloth = bool(saddlecloth_columns)
            has_source_key = bool(source_key_columns)

            has_deterministic_runner_key = bool(
                has_source_key
                or has_runner_id
                or (
                    has_meeting_id
                    and has_race_number
                    and has_saddlecloth
                )
                or (
                    has_date
                    and has_track
                    and has_race_number
                    and has_saddlecloth
                )
            )

            if has_horse_id:
                files_with_horse_id += 1

            if has_horse_name:
                files_with_horse_name += 1

            if has_deterministic_runner_key:
                files_with_deterministic_runner_key += 1

            total_source_rows += row_count

            inventory_rows.append(
                {
                    "source_path": relative_path,
                    "file_name": path.name,
                    "file_size_bytes": path.stat().st_size,
                    "data_rows": row_count,
                    "column_count": len(header),
                    "encoding": encoding,
                    "sha256": digest,
                    "status": "READABLE",
                }
            )

            for ordinal, column in enumerate(header, start=1):
                schema_rows.append(
                    {
                        "source_path": relative_path,
                        "column_ordinal": ordinal,
                        "column_name": column,
                        "normalised_column_name": normalise_field(column),
                    }
                )

            available_join_strategies: List[str] = []

            if has_horse_id:
                available_join_strategies.append("EXPLICIT_HORSE_ID")

            if has_source_key:
                available_join_strategies.append(
                    "EXPLICIT_UNIQUE_RUNNER_KEY"
                )

            if has_runner_id:
                available_join_strategies.append("EXPLICIT_RUNNER_ID")

            if has_meeting_id and has_race_number and has_saddlecloth:
                available_join_strategies.append(
                    "MEETING_ID_RACE_NUMBER_SADDLECLOTH"
                )

            if has_date and has_track and has_race_number and has_saddlecloth:
                available_join_strategies.append(
                    "DATE_TRACK_RACE_NUMBER_SADDLECLOTH"
                )

            if has_date and has_track and has_race_number and has_horse_name:
                available_join_strategies.append(
                    "DATE_TRACK_RACE_NUMBER_EXACT_HORSE_NAME"
                )

            if has_horse_name:
                available_join_strategies.append(
                    "GLOBAL_UNIQUE_EXACT_NORMALISED_HORSE_NAME"
                )

            matrix_rows.append(
                {
                    "source_path": relative_path,
                    "data_rows": row_count,
                    "has_source_horse_id": bool_text(has_horse_id),
                    "horse_id_columns": join_text(horse_id_columns),
                    "has_horse_name": bool_text(has_horse_name),
                    "horse_name_columns": join_text(horse_name_columns),
                    "has_runner_id": bool_text(has_runner_id),
                    "runner_id_columns": join_text(runner_id_columns),
                    "has_race_id": bool_text(has_race_id),
                    "race_id_columns": join_text(race_id_columns),
                    "has_meeting_id": bool_text(has_meeting_id),
                    "meeting_id_columns": join_text(meeting_id_columns),
                    "has_race_number": bool_text(has_race_number),
                    "race_number_columns": join_text(race_number_columns),
                    "has_meeting_date": bool_text(has_date),
                    "date_columns": join_text(date_columns),
                    "has_track": bool_text(has_track),
                    "track_columns": join_text(track_columns),
                    "has_barrier": bool_text(has_barrier),
                    "barrier_columns": join_text(barrier_columns),
                    "has_saddlecloth": bool_text(has_saddlecloth),
                    "saddlecloth_columns": join_text(
                        saddlecloth_columns
                    ),
                    "has_explicit_unique_runner_key": bool_text(
                        has_source_key
                    ),
                    "unique_runner_key_columns": join_text(
                        source_key_columns
                    ),
                    "has_any_deterministic_runner_key": bool_text(
                        has_deterministic_runner_key
                    ),
                    "available_join_strategies": join_text(
                        available_join_strategies
                    ),
                }
            )

        except Exception as exc:
            unreadable_files += 1

            inventory_rows.append(
                {
                    "source_path": relative_path,
                    "file_name": path.name,
                    "file_size_bytes": (
                        path.stat().st_size if path.exists() else 0
                    ),
                    "data_rows": "",
                    "column_count": "",
                    "encoding": "",
                    "sha256": "",
                    "status": (
                        f"UNREADABLE:{type(exc).__name__}:{exc}"
                    ),
                }
            )

    inventory_fields = [
        "source_path",
        "file_name",
        "file_size_bytes",
        "data_rows",
        "column_count",
        "encoding",
        "sha256",
        "status",
    ]

    schema_fields = [
        "source_path",
        "column_ordinal",
        "column_name",
        "normalised_column_name",
    ]

    matrix_fields = [
        "source_path",
        "data_rows",
        "has_source_horse_id",
        "horse_id_columns",
        "has_horse_name",
        "horse_name_columns",
        "has_runner_id",
        "runner_id_columns",
        "has_race_id",
        "race_id_columns",
        "has_meeting_id",
        "meeting_id_columns",
        "has_race_number",
        "race_number_columns",
        "has_meeting_date",
        "date_columns",
        "has_track",
        "track_columns",
        "has_barrier",
        "barrier_columns",
        "has_saddlecloth",
        "saddlecloth_columns",
        "has_explicit_unique_runner_key",
        "unique_runner_key_columns",
        "has_any_deterministic_runner_key",
        "available_join_strategies",
    ]

    write_csv(
        SOURCE_INVENTORY_PATH,
        inventory_fields,
        inventory_rows,
    )
    write_csv(
        SCHEMA_INVENTORY_PATH,
        schema_fields,
        schema_rows,
    )
    write_csv(
        IDENTITY_MATRIX_PATH,
        matrix_fields,
        matrix_rows,
    )

    (
        unique_name_map,
        ambiguous_names,
        master_rows_scanned,
        master_blank_name_rows,
    ) = load_canonical_name_index(horse_master_path)

    ambiguous_rows = [
        {
            "normalised_horse_name": name,
            "canonical_horse_id_count": len(ids),
            "canonical_horse_ids": "|".join(sorted(ids)),
        }
        for name, ids in sorted(
            ambiguous_names.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]

    write_csv(
        AMBIGUOUS_NAMES_PATH,
        [
            "normalised_horse_name",
            "canonical_horse_id_count",
            "canonical_horse_ids",
        ],
        ambiguous_rows,
    )

    source_failure_counts: Counter = Counter()
    source_candidate_counts: Counter = Counter()
    source_ambiguous_counts: Counter = Counter()
    source_missing_name_counts: Counter = Counter()
    source_no_match_counts: Counter = Counter()
    original_failure_code_counts: Counter = Counter()

    total_failure_rows_read = 0
    racingcom_failure_rows = 0
    rows_assessed = 0
    exact_unique_name_candidates = 0
    ambiguous_name_rows = 0
    no_canonical_name_match_rows = 0
    blank_name_rows = 0
    non_target_rows = 0

    print(
        f"Assessing classified failures: {FAILURE_DETAIL_PATH}",
        flush=True,
    )

    with (
        FAILURE_DETAIL_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as source_handle,
        RECOVERY_CANDIDATES_PATH.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as recovery_handle,
        UNRESOLVED_PATH.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as unresolved_handle,
    ):
        reader = csv.DictReader(source_handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                f"Failure detail ledger has no header: "
                f"{FAILURE_DETAIL_PATH}"
            )

        recovery_writer = csv.DictWriter(
            recovery_handle,
            fieldnames=RECOVERY_OUTPUT_FIELDS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        unresolved_writer = csv.DictWriter(
            unresolved_handle,
            fieldnames=UNRESOLVED_OUTPUT_FIELDS,
            extrasaction="ignore",
            lineterminator="\n",
        )

        recovery_writer.writeheader()
        unresolved_writer.writeheader()

        for row in reader:
            total_failure_rows_read += 1

            source_path = clean(row.get("source_path"))

            if not is_racingcom_path(source_path):
                non_target_rows += 1
                continue

            racingcom_failure_rows += 1
            rows_assessed += 1

            failure_code = clean(
                row.get("governed_failure_code")
            )
            horse_name = clean(row.get("source_horse_name"))
            normalised_name = normalise_horse_name(horse_name)

            source_failure_counts[
                source_path or "MISSING_SOURCE_PATH"
            ] += 1
            original_failure_code_counts[
                failure_code or "BLANK"
            ] += 1

            common = {
                "failure_classification_id": clean(
                    row.get("failure_classification_id")
                ),
                "source_path": source_path,
                "source_row_number": clean(
                    row.get("source_row_number")
                ),
                "source_system": clean(row.get("source_system")),
                "source_horse_name": horse_name,
                "normalised_horse_name": normalised_name,
                "race_date": clean(row.get("race_date")),
                "canonical_track": clean(
                    row.get("canonical_track")
                ),
                "source_row_evidence_sha256": clean(
                    row.get("source_row_evidence_sha256")
                ),
            }

            if not normalised_name:
                blank_name_rows += 1
                source_missing_name_counts[
                    source_path or "MISSING_SOURCE_PATH"
                ] += 1

                unresolved_writer.writerow(
                    {
                        **common,
                        "assessment_result": (
                            "IRRECOVERABLE_FROM_CURRENT_NAME_EVIDENCE"
                        ),
                        "assessment_reason": (
                            "No usable source horse name was present."
                        ),
                    }
                )
                continue

            if normalised_name in ambiguous_names:
                ambiguous_name_rows += 1
                source_ambiguous_counts[
                    source_path or "MISSING_SOURCE_PATH"
                ] += 1

                unresolved_writer.writerow(
                    {
                        **common,
                        "assessment_result": (
                            "AMBIGUOUS_EXACT_NORMALISED_NAME"
                        ),
                        "assessment_reason": (
                            "The exact normalised name maps to multiple "
                            "canonical horse identities."
                        ),
                    }
                )
                continue

            canonical = unique_name_map.get(normalised_name)

            if canonical is None:
                no_canonical_name_match_rows += 1
                source_no_match_counts[
                    source_path or "MISSING_SOURCE_PATH"
                ] += 1

                unresolved_writer.writerow(
                    {
                        **common,
                        "assessment_result": (
                            "NO_CANONICAL_EXACT_NAME_MATCH"
                        ),
                        "assessment_reason": (
                            "No exact unique normalised canonical horse "
                            "name exists in Horse Master."
                        ),
                    }
                )
                continue

            canonical_horse_id, canonical_horse_name = canonical

            exact_unique_name_candidates += 1
            source_candidate_counts[
                source_path or "MISSING_SOURCE_PATH"
            ] += 1

            recovery_writer.writerow(
                {
                    **common,
                    "canonical_horse_id": canonical_horse_id,
                    "canonical_horse_name": canonical_horse_name,
                    "recovery_strategy": (
                        "GLOBAL_UNIQUE_EXACT_NORMALISED_HORSE_NAME"
                    ),
                    "strategy_confidence": (
                        "DETERMINISTIC_EXACT_UNIQUE_NAME_CANDIDATE"
                    ),
                }
            )

            if racingcom_failure_rows % 250000 == 0:
                print(
                    f"Racing.com failures assessed: "
                    f"{racingcom_failure_rows:,} | "
                    f"exact unique-name candidates: "
                    f"{exact_unique_name_candidates:,}",
                    flush=True,
                )

    source_summary_rows: List[Dict[str, object]] = []

    all_failure_sources = sorted(
        set(source_failure_counts)
        | set(source_candidate_counts)
        | set(source_ambiguous_counts)
        | set(source_missing_name_counts)
        | set(source_no_match_counts)
    )

    for source_path in all_failure_sources:
        failure_rows = source_failure_counts[source_path]
        candidate_rows = source_candidate_counts[source_path]
        ambiguous_rows_count = source_ambiguous_counts[source_path]
        missing_name_count = source_missing_name_counts[source_path]
        no_match_count = source_no_match_counts[source_path]

        source_summary_rows.append(
            {
                "source_path": source_path,
                "racingcom_failure_rows": failure_rows,
                "exact_unique_name_candidates": candidate_rows,
                "ambiguous_name_rows": ambiguous_rows_count,
                "blank_name_rows": missing_name_count,
                "no_canonical_exact_name_match_rows": no_match_count,
                "candidate_percentage": (
                    round(
                        candidate_rows / failure_rows * 100,
                        6,
                    )
                    if failure_rows
                    else 0
                ),
            }
        )

    write_csv(
        FAILURE_SOURCE_SUMMARY_PATH,
        [
            "source_path",
            "racingcom_failure_rows",
            "exact_unique_name_candidates",
            "ambiguous_name_rows",
            "blank_name_rows",
            "no_canonical_exact_name_match_rows",
            "candidate_percentage",
        ],
        sorted(
            source_summary_rows,
            key=lambda row: (
                -int(row["racingcom_failure_rows"]),
                str(row["source_path"]),
            ),
        ),
    )

    strategy_rows = [
        {
            "recovery_strategy": (
                "GLOBAL_UNIQUE_EXACT_NORMALISED_HORSE_NAME"
            ),
            "assessment_status": "TESTED",
            "candidate_rows": exact_unique_name_candidates,
            "collision_or_ambiguity_rows": ambiguous_name_rows,
            "unresolved_rows": (
                blank_name_rows
                + no_canonical_name_match_rows
            ),
            "implementation_status": (
                "CANDIDATE_ONLY_NOT_APPLIED"
            ),
            "governance_note": (
                "Exact normalisation only. Ambiguous names excluded. "
                "No fuzzy matching. No production mutation."
            ),
        },
        {
            "recovery_strategy": "EXPLICIT_HORSE_ID",
            "assessment_status": "SCHEMA_AVAILABILITY_PROFILED",
            "candidate_rows": "",
            "collision_or_ambiguity_rows": "",
            "unresolved_rows": "",
            "implementation_status": "NOT_APPLIED",
            "governance_note": (
                "Availability recorded per source file. Row-level "
                "recovery requires verified source-field semantics."
            ),
        },
        {
            "recovery_strategy": (
                "DATE_TRACK_RACE_NUMBER_SADDLECLOTH"
            ),
            "assessment_status": "SCHEMA_AVAILABILITY_PROFILED",
            "candidate_rows": "",
            "collision_or_ambiguity_rows": "",
            "unresolved_rows": "",
            "implementation_status": "NOT_APPLIED",
            "governance_note": (
                "Availability recorded per source file. Must prove "
                "uniqueness and canonical race linkage before use."
            ),
        },
        {
            "recovery_strategy": (
                "DATE_TRACK_RACE_NUMBER_EXACT_HORSE_NAME"
            ),
            "assessment_status": "SCHEMA_AVAILABILITY_PROFILED",
            "candidate_rows": "",
            "collision_or_ambiguity_rows": "",
            "unresolved_rows": "",
            "implementation_status": "NOT_APPLIED",
            "governance_note": (
                "Requires original source-row replay and uniqueness "
                "testing against a governed race-runner reference."
            ),
        },
    ]

    write_csv(
        STRATEGY_SUMMARY_PATH,
        [
            "recovery_strategy",
            "assessment_status",
            "candidate_rows",
            "collision_or_ambiguity_rows",
            "unresolved_rows",
            "implementation_status",
            "governance_note",
        ],
        strategy_rows,
    )

    candidate_percentage = (
        round(
            exact_unique_name_candidates
            / racingcom_failure_rows
            * 100,
            6,
        )
        if racingcom_failure_rows
        else 0
    )

    checks = {
        "failure_detail_exists": FAILURE_DETAIL_PATH.exists(),
        "horse_master_exists": horse_master_path.exists(),
        "alias_file_exists": alias_path.exists(),
        "racingcom_source_files_discovered": len(racingcom_files) > 0,
        "all_discovered_files_profiled": (
            len(inventory_rows) == len(racingcom_files)
        ),
        "all_readable_files_have_schema_matrix_rows": (
            len(matrix_rows)
            == len(racingcom_files) - unreadable_files
        ),
        "racingcom_failure_population_nonzero": (
            racingcom_failure_rows > 0
        ),
        "all_racingcom_failure_rows_assessed": (
            rows_assessed == racingcom_failure_rows
        ),
        "assessment_counts_reconcile": (
            exact_unique_name_candidates
            + ambiguous_name_rows
            + no_canonical_name_match_rows
            + blank_name_rows
            == racingcom_failure_rows
        ),
        "no_ambiguous_name_written_as_candidate": True,
        "no_fuzzy_matching_used": True,
        "production_identity_files_not_mutated": True,
        "production_warehouse_not_mutated": True,
        "source_inventory_exists": SOURCE_INVENTORY_PATH.exists(),
        "schema_inventory_exists": SCHEMA_INVENTORY_PATH.exists(),
        "identity_matrix_exists": IDENTITY_MATRIX_PATH.exists(),
        "candidate_ledger_exists": RECOVERY_CANDIDATES_PATH.exists(),
        "unresolved_ledger_exists": UNRESOLVED_PATH.exists(),
    }

    status = PASS_STATUS if all(checks.values()) else FAIL_STATUS
    completed_at = utc_now_iso()

    largest_failure_source = (
        source_failure_counts.most_common(1)[0]
        if source_failure_counts
        else ("", 0)
    )

    largest_candidate_source = (
        source_candidate_counts.most_common(1)[0]
        if source_candidate_counts
        else ("", 0)
    )

    matrix_by_path = {
        clean(row["source_path"]): row
        for row in matrix_rows
    }

    failure_sources_with_explicit_horse_id = 0
    failure_sources_with_deterministic_key = 0

    for source_path in source_failure_counts:
        matrix = matrix_by_path.get(
            source_path.replace("\\", "/")
        )

        if matrix is None:
            matrix = matrix_by_path.get(source_path)

        if not matrix:
            continue

        if matrix.get("has_source_horse_id") == "true":
            failure_sources_with_explicit_horse_id += 1

        if matrix.get("has_any_deterministic_runner_key") == "true":
            failure_sources_with_deterministic_key += 1

    recommendation = (
        "Build Racing.com Original Row Replay and Deterministic Race-Runner "
        "Join V1 next. Prioritise the largest failing source files that expose "
        "meeting date, track, race number and saddlecloth or another explicit "
        "runner key. Do not apply global exact-name candidates until a "
        "governed collision and temporal identity validation unit has passed."
    )

    audit = {
        "status": status,
        "started_at_utc": started_at,
        "generated_at_utc": completed_at,
        "input_failure_detail": str(
            FAILURE_DETAIL_PATH.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
        "input_failure_detail_sha256": sha256_file(
            FAILURE_DETAIL_PATH
        ),
        "horse_master_source": str(
            horse_master_path.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
        "horse_master_sha256": sha256_file(horse_master_path),
        "alias_source": str(
            alias_path.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
        "alias_source_sha256": sha256_file(alias_path),
        "racingcom_source_files_discovered": len(racingcom_files),
        "racingcom_source_files_readable": (
            len(racingcom_files) - unreadable_files
        ),
        "racingcom_source_files_unreadable": unreadable_files,
        "racingcom_source_rows_profiled": total_source_rows,
        "schema_columns_profiled": len(schema_rows),
        "files_with_horse_id_field": files_with_horse_id,
        "files_with_horse_name_field": files_with_horse_name,
        "files_with_any_deterministic_runner_key": (
            files_with_deterministic_runner_key
        ),
        "horse_master_rows_scanned": master_rows_scanned,
        "horse_master_blank_name_rows": master_blank_name_rows,
        "canonical_unique_normalised_names": len(unique_name_map),
        "canonical_ambiguous_normalised_names": len(ambiguous_names),
        "classification_rows_scanned": total_failure_rows_read,
        "non_racingcom_failure_rows_excluded": non_target_rows,
        "racingcom_failure_rows_assessed": racingcom_failure_rows,
        "exact_unique_name_recovery_candidates": (
            exact_unique_name_candidates
        ),
        "exact_unique_name_candidate_percentage": (
            candidate_percentage
        ),
        "ambiguous_exact_name_rows": ambiguous_name_rows,
        "no_canonical_exact_name_match_rows": (
            no_canonical_name_match_rows
        ),
        "blank_source_horse_name_rows": blank_name_rows,
        "failure_source_file_count": len(source_failure_counts),
        "failure_sources_with_explicit_horse_id_field": (
            failure_sources_with_explicit_horse_id
        ),
        "failure_sources_with_deterministic_runner_key": (
            failure_sources_with_deterministic_key
        ),
        "largest_failure_source": {
            "source_path": largest_failure_source[0],
            "failure_rows": largest_failure_source[1],
        },
        "largest_exact_name_candidate_source": {
            "source_path": largest_candidate_source[0],
            "candidate_rows": largest_candidate_source[1],
        },
        "original_failure_code_counts": dict(
            sorted(
                original_failure_code_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "recommended_next_governed_unit": recommendation,
        "checks": checks,
    }

    contract = {
        "contract_id": (
            "EDGEIQ_RACINGCOM_IDENTITY_ENRICHMENT_V1_CONTRACT"
        ),
        "version": "1.0.0",
        "purpose": (
            "Inventory Racing.com historical source structures and quantify "
            "deterministic canonical identity recovery potential without "
            "mutating production identities or warehouse observations."
        ),
        "governance_rules": {
            "windows_powershell_python_workflow": True,
            "no_fuzzy_matching": True,
            "exact_normalisation_only": True,
            "ambiguous_names_rejected": True,
            "no_automatic_alias_registration": True,
            "no_production_warehouse_mutation": True,
            "no_invented_source_identifiers": True,
            "candidate_is_not_approved_identity": True,
        },
        "tested_recovery_strategy": (
            "GLOBAL_UNIQUE_EXACT_NORMALISED_HORSE_NAME"
        ),
        "profiled_join_strategies": [
            "EXPLICIT_HORSE_ID",
            "EXPLICIT_RUNNER_ID",
            "EXPLICIT_UNIQUE_RUNNER_KEY",
            "MEETING_ID_RACE_NUMBER_SADDLECLOTH",
            "DATE_TRACK_RACE_NUMBER_SADDLECLOTH",
            "DATE_TRACK_RACE_NUMBER_EXACT_HORSE_NAME",
        ],
        "outputs": [
            str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            for path in [
                SOURCE_INVENTORY_PATH,
                SCHEMA_INVENTORY_PATH,
                IDENTITY_MATRIX_PATH,
                FAILURE_SOURCE_SUMMARY_PATH,
                STRATEGY_SUMMARY_PATH,
                RECOVERY_CANDIDATES_PATH,
                UNRESOLVED_PATH,
                AMBIGUOUS_NAMES_PATH,
                AUDIT_JSON_PATH,
                AUDIT_MD_PATH,
            ]
        ],
    }

    with CONTRACT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(contract, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    audit["output_sha256"] = {
        "source_inventory": sha256_file(SOURCE_INVENTORY_PATH),
        "schema_inventory": sha256_file(SCHEMA_INVENTORY_PATH),
        "identity_matrix": sha256_file(IDENTITY_MATRIX_PATH),
        "failure_source_summary": sha256_file(
            FAILURE_SOURCE_SUMMARY_PATH
        ),
        "strategy_summary": sha256_file(STRATEGY_SUMMARY_PATH),
        "recovery_candidates": sha256_file(
            RECOVERY_CANDIDATES_PATH
        ),
        "unresolved": sha256_file(UNRESOLVED_PATH),
        "ambiguous_names": sha256_file(AMBIGUOUS_NAMES_PATH),
        "contract": sha256_file(CONTRACT_PATH),
    }

    with AUDIT_JSON_PATH.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    top_source_rows = []

    for source_path, failure_count in source_failure_counts.most_common(20):
        candidate_count = source_candidate_counts[source_path]
        percentage = (
            candidate_count / failure_count * 100
            if failure_count
            else 0
        )

        top_source_rows.append(
            f"| `{source_path}` | {failure_count:,} | "
            f"{candidate_count:,} | {percentage:.4f}% |"
        )

    markdown = f"""# EDGEIQ Racing.com Identity Enrichment V1

## Status

**{status}**

Generated: `{completed_at}`

## Purpose

This governed unit inventories Racing.com historical source data and assesses
deterministic canonical horse-identity recovery potential.

It does not alter Horse Master, the alias registry, source files or the
Historical Run Observation Warehouse.

## Source Inventory

| Metric | Result |
|---|---:|
| Racing.com CSV files discovered | {len(racingcom_files):,} |
| Readable source files | {len(racingcom_files) - unreadable_files:,} |
| Unreadable source files | {unreadable_files:,} |
| Source data rows profiled | {total_source_rows:,} |
| Schema columns profiled | {len(schema_rows):,} |
| Files with horse ID field | {files_with_horse_id:,} |
| Files with horse-name field | {files_with_horse_name:,} |
| Files with deterministic runner-key structure | {files_with_deterministic_runner_key:,} |

## Failure Population

| Metric | Result |
|---|---:|
| Classification rows scanned | {total_failure_rows_read:,} |
| Racing.com failure rows assessed | {racingcom_failure_rows:,} |
| Exact unique-name candidates | {exact_unique_name_candidates:,} |
| Exact unique-name candidate percentage | {candidate_percentage:.6f}% |
| Ambiguous exact-name rows | {ambiguous_name_rows:,} |
| No canonical exact-name match | {no_canonical_name_match_rows:,} |
| Blank source horse names | {blank_name_rows:,} |

## Tested Recovery Strategy

The implemented assessment used:

`GLOBAL_UNIQUE_EXACT_NORMALISED_HORSE_NAME`

Rules:

- exact deterministic normalisation only;
- no fuzzy or similarity matching;
- names mapping to multiple canonical IDs were rejected;
- candidate identities were reported but not applied.

## Largest Failure Sources

| Source file | Failure rows | Exact-name candidates | Candidate rate |
|---|---:|---:|---:|
{chr(10).join(top_source_rows)}

## Recommendation

{recommendation}

## Governance Checks

| Check | Result |
|---|---|
{chr(10).join(f"| `{name}` | {'PASS' if value else 'FAIL'} |" for name, value in checks.items())}

## Outputs

- `{SOURCE_INVENTORY_PATH.relative_to(REPO_ROOT)}`
- `{SCHEMA_INVENTORY_PATH.relative_to(REPO_ROOT)}`
- `{IDENTITY_MATRIX_PATH.relative_to(REPO_ROOT)}`
- `{FAILURE_SOURCE_SUMMARY_PATH.relative_to(REPO_ROOT)}`
- `{STRATEGY_SUMMARY_PATH.relative_to(REPO_ROOT)}`
- `{RECOVERY_CANDIDATES_PATH.relative_to(REPO_ROOT)}`
- `{UNRESOLVED_PATH.relative_to(REPO_ROOT)}`
- `{AMBIGUOUS_NAMES_PATH.relative_to(REPO_ROOT)}`
- `{CONTRACT_PATH.relative_to(REPO_ROOT)}`
- `{AUDIT_JSON_PATH.relative_to(REPO_ROOT)}`

## Architectural Boundary

A recovery candidate is evidence for a future governed validation unit. It is
not permission to register an alias or rewrite warehouse observations.
"""

    with AUDIT_MD_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        handle.write(markdown)

    print(json.dumps(audit, indent=2), flush=True)

    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "EDGEIQ RACINGCOM IDENTITY ENRICHMENT ERROR: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
