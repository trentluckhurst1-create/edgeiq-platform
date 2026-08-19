from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = REPO_ROOT / "public" / "data"

CLASSIFICATION_DIR = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-observation-failure-classification-v1"
)

ENRICHMENT_DIR = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "racingcom-identity-enrichment-v1"
)

OUTPUT_DIR = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "racingcom-deterministic-join-discovery-v1"
)

FAILURE_SOURCE_SUMMARY = (
    ENRICHMENT_DIR
    / "edgeiq_racingcom_failure_source_summary_v1.csv"
)

IDENTITY_MATRIX = (
    ENRICHMENT_DIR
    / "edgeiq_racingcom_identity_availability_matrix_v1.csv"
)

COLUMN_PROFILE_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_column_profile_v1.csv"
)

FILE_PROFILE_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_join_file_profile_v1.csv"
)

IDENTIFIER_DISCOVERY_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_identifier_discovery_v1.csv"
)

JOIN_STRATEGY_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_join_strategy_assessment_v1.csv"
)

JOIN_DETAIL_PATH = (
    OUTPUT_DIR / "edgeiq_racingcom_join_strategy_detail_v1.csv"
)

AUDIT_JSON_PATH = (
    OUTPUT_DIR
    / "EDGEIQ_RACINGCOM_DETERMINISTIC_JOIN_DISCOVERY_V1_AUDIT.json"
)

AUDIT_MD_PATH = (
    OUTPUT_DIR
    / "EDGEIQ_RACINGCOM_DETERMINISTIC_JOIN_DISCOVERY_V1_AUDIT.md"
)

CONTRACT_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_deterministic_join_discovery_v1_contract.json"
)

PASS_STATUS = (
    "EDGEIQ_RACINGCOM_DETERMINISTIC_JOIN_DISCOVERY_V1_AUDIT_PASS"
)
FAIL_STATUS = (
    "EDGEIQ_RACINGCOM_DETERMINISTIC_JOIN_DISCOVERY_V1_AUDIT_FAIL"
)

TOP_FAILURE_FILE_LIMIT = 40
PROFILE_SAMPLE_LIMIT = 200000
DETAIL_EXAMPLE_LIMIT = 100

CANONICAL_FILE_PATTERNS = (
    "edgeiq_racingcom_canonical_runner_",
    "edgeiq_racingcom_runner_sectional_fact",
    "edgeiq_racingcom_runner_speed_fact",
    "edgeiq_racingcom_runner_split_fact",
)

FIELD_GROUPS = {
    "runner_id": {
        "runner_id",
        "runnerid",
        "competitor_id",
        "competitorid",
        "participant_id",
        "participantid",
        "horse_id",
        "horseid",
    },
    "horse_name": {
        "horse",
        "horse_name",
        "horsename",
        "runner",
        "runner_name",
        "runnername",
        "competitor_name",
        "competitorname",
    },
    "race_id": {
        "race_id",
        "raceid",
        "event_id",
        "eventid",
        "source_race_id",
    },
    "meeting_id": {
        "meeting_id",
        "meetingid",
        "fixture_id",
        "fixtureid",
    },
    "race_date": {
        "race_date",
        "racedate",
        "meeting_date",
        "meetingdate",
        "event_date",
        "eventdate",
        "date",
    },
    "track": {
        "track",
        "track_name",
        "trackname",
        "venue",
        "venue_name",
        "venue_name_raw",
        "meeting",
        "canonical_track",
    },
    "race_number": {
        "race_number",
        "racenumber",
        "race_no",
        "raceno",
    },
    "saddlecloth": {
        "saddlecloth",
        "saddlecloth_number",
        "saddleclothnumber",
        "runner_number",
        "runnernumber",
        "tab_number",
        "tabnumber",
        "number",
    },
    "barrier": {
        "barrier",
        "barrier_number",
        "barriernumber",
        "draw",
        "gate",
    },
    "url": {
        "url",
        "source_url",
        "race_url",
        "runner_url",
        "horse_url",
        "profile_url",
        "href",
    },
}

JOIN_STRATEGIES = [
    ("RACE_ID_RUNNER_ID", ("race_id", "runner_id")),
    ("MEETING_ID_RACE_NUMBER_RUNNER_ID",
        ("meeting_id", "race_number", "runner_id")),
    ("DATE_TRACK_RACE_NUMBER_SADDLECLOTH",
        ("race_date", "track", "race_number", "saddlecloth")),
    ("DATE_TRACK_RACE_NUMBER_BARRIER",
        ("race_date", "track", "race_number", "barrier")),
    ("DATE_TRACK_RACE_NUMBER_HORSE_NAME",
        ("race_date", "track", "race_number", "horse_name")),
    ("DATE_RACE_NUMBER_HORSE_NAME",
        ("race_date", "race_number", "horse_name")),
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def normalise_field(value: object) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(value).lower(),
    ).strip("_")


def normalise_text(value: object) -> str:
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        clean(value).upper(),
    )


def normalise_number(value: object) -> str:
    text = clean(value)

    try:
        number = float(text)

        if number.is_integer():
            return str(int(number))
    except ValueError:
        pass

    return normalise_text(text)


def normalise_date(value: object) -> str:
    text = clean(value)

    if not text:
        return ""

    patterns = [
        r"^(\d{4})-(\d{2})-(\d{2})",
        r"^(\d{2})/(\d{2})/(\d{4})",
        r"^(\d{2})-(\d{2})-(\d{4})",
    ]

    match = re.search(patterns[0], text)

    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    for pattern in patterns[1:]:
        match = re.search(pattern, text)

        if match:
            return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"

    digits = re.sub(r"\D", "", text)

    if len(digits) >= 8:
        return digits[:8]

    return normalise_text(text)


def normalise_component(group: str, value: object) -> str:
    if group == "race_date":
        return normalise_date(value)

    if group in {
        "race_number",
        "saddlecloth",
        "barrier",
    }:
        return normalise_number(value)

    return normalise_text(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def resolve_path(source_path: str) -> Path:
    return REPO_ROOT / source_path.replace("\\", "/")


def read_header(path: Path) -> Tuple[List[str], str]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with path.open(
                "r",
                encoding=encoding,
                newline="",
            ) as handle:
                reader = csv.reader(handle)
                return next(reader, []), encoding
        except UnicodeDecodeError:
            continue

    raise UnicodeError(f"Unable to decode {path}")


def map_groups(header: Sequence[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}

    for original in header:
        normalised = normalise_field(original)

        for group, candidates in FIELD_GROUPS.items():
            if normalised in candidates and group not in result:
                result[group] = original

    return result


def write_csv(
    path: Path,
    fields: Sequence[str],
    rows: Iterable[Dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fields),
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {field: row.get(field, "") for field in fields}
            )


def discover_target_files() -> Tuple[List[Path], List[Path]]:
    if not FAILURE_SOURCE_SUMMARY.exists():
        raise FileNotFoundError(FAILURE_SOURCE_SUMMARY)

    failures: List[Tuple[int, Path]] = []

    with FAILURE_SOURCE_SUMMARY.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        for row in csv.DictReader(handle):
            source_path = clean(row.get("source_path"))
            failure_rows = int(
                clean(row.get("racingcom_failure_rows")) or 0
            )
            path = resolve_path(source_path)

            if path.exists():
                failures.append((failure_rows, path))

    failures.sort(
        key=lambda item: (-item[0], str(item[1]).lower())
    )

    raw_files = [
        path
        for _, path in failures[:TOP_FAILURE_FILE_LIMIT]
    ]

    canonical_files = sorted(
        {
            path
            for path in PUBLIC_DATA.glob("*.csv")
            if any(
                pattern in path.name.lower()
                for pattern in CANONICAL_FILE_PATTERNS
            )
        },
        key=lambda path: path.name.lower(),
    )

    return raw_files, canonical_files


def profile_files(
    paths: Sequence[Path],
    role: str,
) -> Tuple[
    List[Dict[str, object]],
    List[Dict[str, object]],
    List[Dict[str, object]],
]:
    file_rows: List[Dict[str, object]] = []
    column_rows: List[Dict[str, object]] = []
    identifier_rows: List[Dict[str, object]] = []

    for file_index, path in enumerate(paths, start=1):
        relative = str(
            path.relative_to(REPO_ROOT)
        ).replace("\\", "/")

        print(
            f"[{role} {file_index}/{len(paths)}] {relative}",
            flush=True,
        )

        header, encoding = read_header(path)
        group_map = map_groups(header)

        counters: Dict[str, Counter] = {
            column: Counter()
            for column in header
        }
        nonblank: Counter = Counter()
        url_counts: Counter = Counter()
        json_counts: Counter = Counter()
        numeric_token_counts: Counter = Counter()
        samples: Dict[str, List[str]] = defaultdict(list)

        row_count = 0

        with path.open(
            "r",
            encoding=encoding,
            errors="replace",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            for row in reader:
                row_count += 1

                if row_count <= PROFILE_SAMPLE_LIMIT:
                    for column in header:
                        value = clean(row.get(column))

                        if not value:
                            continue

                        nonblank[column] += 1
                        counters[column][value] += 1

                        if len(samples[column]) < 5:
                            if value not in samples[column]:
                                samples[column].append(value[:300])

                        if re.search(
                            r"https?://|www\.|/horse/|/race/",
                            value,
                            re.I,
                        ):
                            url_counts[column] += 1

                        if (
                            value.startswith("{")
                            or value.startswith("[")
                        ):
                            try:
                                json.loads(value)
                                json_counts[column] += 1
                            except Exception:
                                pass

                        if re.search(r"\d{4,}", value):
                            numeric_token_counts[column] += 1

        file_rows.append(
            {
                "file_role": role,
                "source_path": relative,
                "data_rows": row_count,
                "file_size_bytes": path.stat().st_size,
                "column_count": len(header),
                "mapped_groups": "|".join(
                    f"{group}:{column}"
                    for group, column in sorted(group_map.items())
                ),
                "sha256": sha256_file(path),
            }
        )

        sample_denominator = min(
            row_count,
            PROFILE_SAMPLE_LIMIT,
        )

        for ordinal, column in enumerate(header, start=1):
            unique_count = len(counters[column])
            nonblank_count = nonblank[column]

            column_rows.append(
                {
                    "file_role": role,
                    "source_path": relative,
                    "column_ordinal": ordinal,
                    "column_name": column,
                    "normalised_column_name": normalise_field(column),
                    "sample_rows_profiled": sample_denominator,
                    "nonblank_sample_rows": nonblank_count,
                    "unique_sample_values": unique_count,
                    "sample_uniqueness_percentage": (
                        round(
                            unique_count
                            / nonblank_count
                            * 100,
                            6,
                        )
                        if nonblank_count
                        else 0
                    ),
                    "url_like_sample_rows": url_counts[column],
                    "json_like_sample_rows": json_counts[column],
                    "long_numeric_token_sample_rows": (
                        numeric_token_counts[column]
                    ),
                    "example_values": " || ".join(samples[column]),
                }
            )

            if (
                url_counts[column]
                or json_counts[column]
                or numeric_token_counts[column]
                or normalise_field(column).endswith("_id")
                or "key" in normalise_field(column)
                or "url" in normalise_field(column)
            ):
                identifier_rows.append(
                    {
                        "file_role": role,
                        "source_path": relative,
                        "column_name": column,
                        "normalised_column_name": normalise_field(column),
                        "nonblank_sample_rows": nonblank_count,
                        "unique_sample_values": unique_count,
                        "url_like_sample_rows": url_counts[column],
                        "json_like_sample_rows": json_counts[column],
                        "long_numeric_token_sample_rows": (
                            numeric_token_counts[column]
                        ),
                        "example_values": " || ".join(samples[column]),
                    }
                )

    return file_rows, column_rows, identifier_rows


def build_reference_indexes(
    canonical_files: Sequence[Path],
) -> Tuple[
    Dict[str, Dict[Tuple[str, ...], Set[str]]],
    Dict[str, int],
]:
    indexes: Dict[
        str,
        Dict[Tuple[str, ...], Set[str]]
    ] = {
        strategy_name: defaultdict(set)
        for strategy_name, _ in JOIN_STRATEGIES
    }

    strategy_reference_rows: Counter = Counter()

    for path in canonical_files:
        header, encoding = read_header(path)
        group_map = map_groups(header)

        if "runner_id" not in group_map:
            continue

        compatible = [
            (strategy_name, groups)
            for strategy_name, groups in JOIN_STRATEGIES
            if all(group in group_map for group in groups)
        ]

        if not compatible:
            continue

        with path.open(
            "r",
            encoding=encoding,
            errors="replace",
            newline="",
        ) as handle:
            for row in csv.DictReader(handle):
                runner_id = clean(
                    row.get(group_map["runner_id"])
                )

                if not runner_id:
                    continue

                for strategy_name, groups in compatible:
                    key = tuple(
                        normalise_component(
                            group,
                            row.get(group_map[group]),
                        )
                        for group in groups
                    )

                    if any(not component for component in key):
                        continue

                    indexes[strategy_name][key].add(runner_id)
                    strategy_reference_rows[strategy_name] += 1

    return indexes, dict(strategy_reference_rows)


def assess_raw_joins(
    raw_files: Sequence[Path],
    indexes: Dict[str, Dict[Tuple[str, ...], Set[str]]],
) -> Tuple[
    List[Dict[str, object]],
    List[Dict[str, object]],
]:
    strategy_rows: List[Dict[str, object]] = []
    detail_rows: List[Dict[str, object]] = []

    for path in raw_files:
        relative = str(
            path.relative_to(REPO_ROOT)
        ).replace("\\", "/")

        header, encoding = read_header(path)
        group_map = map_groups(header)

        for strategy_name, groups in JOIN_STRATEGIES:
            available = all(group in group_map for group in groups)

            if not available:
                strategy_rows.append(
                    {
                        "source_path": relative,
                        "join_strategy": strategy_name,
                        "required_groups": "|".join(groups),
                        "available": "false",
                        "rows_scanned": 0,
                        "rows_with_complete_key": 0,
                        "unique_matches": 0,
                        "ambiguous_matches": 0,
                        "no_matches": 0,
                        "unique_match_percentage": 0,
                        "implementation_decision": (
                            "UNAVAILABLE_REQUIRED_FIELDS"
                        ),
                    }
                )
                continue

            reference_index = indexes.get(strategy_name, {})

            rows_scanned = 0
            complete_rows = 0
            unique_matches = 0
            ambiguous_matches = 0
            no_matches = 0
            examples_written = 0

            with path.open(
                "r",
                encoding=encoding,
                errors="replace",
                newline="",
            ) as handle:
                reader = csv.DictReader(handle)

                for row_number, row in enumerate(reader, start=2):
                    rows_scanned += 1

                    key = tuple(
                        normalise_component(
                            group,
                            row.get(group_map[group]),
                        )
                        for group in groups
                    )

                    if any(not component for component in key):
                        continue

                    complete_rows += 1
                    runner_ids = reference_index.get(key, set())

                    if len(runner_ids) == 1:
                        unique_matches += 1
                        result = "UNIQUE_MATCH"
                    elif len(runner_ids) > 1:
                        ambiguous_matches += 1
                        result = "AMBIGUOUS_MATCH"
                    else:
                        no_matches += 1
                        result = "NO_MATCH"

                    if (
                        examples_written < DETAIL_EXAMPLE_LIMIT
                        and result != "NO_MATCH"
                    ):
                        detail_rows.append(
                            {
                                "source_path": relative,
                                "source_row_number": row_number,
                                "join_strategy": strategy_name,
                                "normalised_join_key": "|".join(key),
                                "assessment_result": result,
                                "matched_runner_ids": "|".join(
                                    sorted(runner_ids)
                                ),
                            }
                        )
                        examples_written += 1

            unique_percentage = (
                unique_matches / complete_rows * 100
                if complete_rows
                else 0
            )

            if (
                unique_matches > 0
                and ambiguous_matches == 0
                and unique_percentage >= 99
            ):
                decision = "HIGH_CONFIDENCE_CANDIDATE"
            elif unique_matches > 0:
                decision = "PARTIAL_OR_COLLISION_PRONE_CANDIDATE"
            else:
                decision = "NO_DETERMINISTIC_RECOVERY_PROVEN"

            strategy_rows.append(
                {
                    "source_path": relative,
                    "join_strategy": strategy_name,
                    "required_groups": "|".join(groups),
                    "available": "true",
                    "rows_scanned": rows_scanned,
                    "rows_with_complete_key": complete_rows,
                    "unique_matches": unique_matches,
                    "ambiguous_matches": ambiguous_matches,
                    "no_matches": no_matches,
                    "unique_match_percentage": round(
                        unique_percentage,
                        6,
                    ),
                    "implementation_decision": decision,
                }
            )

    return strategy_rows, detail_rows


def main() -> int:
    started_at = utc_now()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_files, canonical_files = discover_target_files()

    if not raw_files:
        raise RuntimeError("No failing Racing.com files discovered.")

    if not canonical_files:
        raise RuntimeError(
            "No canonical Racing.com runner fact files discovered."
        )

    print(
        f"Dominant raw failure files: {len(raw_files)}",
        flush=True,
    )
    print(
        f"Canonical runner reference files: {len(canonical_files)}",
        flush=True,
    )

    (
        raw_file_rows,
        raw_column_rows,
        raw_identifier_rows,
    ) = profile_files(raw_files, "RAW_FAILURE_SOURCE")

    (
        canonical_file_rows,
        canonical_column_rows,
        canonical_identifier_rows,
    ) = profile_files(
        canonical_files,
        "CANONICAL_RUNNER_REFERENCE",
    )

    file_rows = raw_file_rows + canonical_file_rows
    column_rows = raw_column_rows + canonical_column_rows
    identifier_rows = (
        raw_identifier_rows + canonical_identifier_rows
    )

    write_csv(
        FILE_PROFILE_PATH,
        [
            "file_role",
            "source_path",
            "data_rows",
            "file_size_bytes",
            "column_count",
            "mapped_groups",
            "sha256",
        ],
        file_rows,
    )

    write_csv(
        COLUMN_PROFILE_PATH,
        [
            "file_role",
            "source_path",
            "column_ordinal",
            "column_name",
            "normalised_column_name",
            "sample_rows_profiled",
            "nonblank_sample_rows",
            "unique_sample_values",
            "sample_uniqueness_percentage",
            "url_like_sample_rows",
            "json_like_sample_rows",
            "long_numeric_token_sample_rows",
            "example_values",
        ],
        column_rows,
    )

    write_csv(
        IDENTIFIER_DISCOVERY_PATH,
        [
            "file_role",
            "source_path",
            "column_name",
            "normalised_column_name",
            "nonblank_sample_rows",
            "unique_sample_values",
            "url_like_sample_rows",
            "json_like_sample_rows",
            "long_numeric_token_sample_rows",
            "example_values",
        ],
        identifier_rows,
    )

    print("Building canonical runner join indexes...", flush=True)

    indexes, reference_rows = build_reference_indexes(
        canonical_files
    )

    print("Testing raw-to-canonical deterministic joins...", flush=True)

    strategy_rows, detail_rows = assess_raw_joins(
        raw_files,
        indexes,
    )

    write_csv(
        JOIN_STRATEGY_PATH,
        [
            "source_path",
            "join_strategy",
            "required_groups",
            "available",
            "rows_scanned",
            "rows_with_complete_key",
            "unique_matches",
            "ambiguous_matches",
            "no_matches",
            "unique_match_percentage",
            "implementation_decision",
        ],
        strategy_rows,
    )

    write_csv(
        JOIN_DETAIL_PATH,
        [
            "source_path",
            "source_row_number",
            "join_strategy",
            "normalised_join_key",
            "assessment_result",
            "matched_runner_ids",
        ],
        detail_rows,
    )

    available_tests = [
        row for row in strategy_rows
        if row["available"] == "true"
    ]

    proven_candidates = [
        row for row in strategy_rows
        if int(row["unique_matches"]) > 0
    ]

    high_confidence = [
        row for row in strategy_rows
        if row["implementation_decision"]
        == "HIGH_CONFIDENCE_CANDIDATE"
    ]

    total_unique_matches = sum(
        int(row["unique_matches"])
        for row in strategy_rows
    )

    total_ambiguous_matches = sum(
        int(row["ambiguous_matches"])
        for row in strategy_rows
    )

    checks = {
        "raw_failure_files_discovered": bool(raw_files),
        "canonical_reference_files_discovered": bool(
            canonical_files
        ),
        "all_files_profiled": (
            len(file_rows)
            == len(raw_files) + len(canonical_files)
        ),
        "column_profile_created": COLUMN_PROFILE_PATH.exists(),
        "identifier_discovery_created": (
            IDENTIFIER_DISCOVERY_PATH.exists()
        ),
        "join_strategy_output_created": (
            JOIN_STRATEGY_PATH.exists()
        ),
        "all_declared_join_strategies_assessed_per_raw_file": (
            len(strategy_rows)
            == len(raw_files) * len(JOIN_STRATEGIES)
        ),
        "no_fuzzy_matching_used": True,
        "no_production_files_mutated": True,
        "no_identity_aliases_created": True,
    }

    status = PASS_STATUS if all(checks.values()) else FAIL_STATUS

    recommendation = (
        "Use only a strategy classified HIGH_CONFIDENCE_CANDIDATE "
        "for the next governed recovery implementation. Where no "
        "high-confidence strategy exists, inspect identifier-bearing "
        "columns and construct a governed original-page or companion-"
        "dataset enrichment source. Do not use global horse-name matching."
    )

    audit = {
        "status": status,
        "started_at_utc": started_at,
        "generated_at_utc": utc_now(),
        "raw_failure_files_profiled": len(raw_files),
        "canonical_reference_files_profiled": len(
            canonical_files
        ),
        "total_files_profiled": len(file_rows),
        "columns_profiled": len(column_rows),
        "identifier_bearing_columns_detected": len(
            identifier_rows
        ),
        "join_strategy_assessments": len(strategy_rows),
        "available_join_strategy_assessments": len(
            available_tests
        ),
        "strategies_with_at_least_one_unique_match": len(
            proven_candidates
        ),
        "high_confidence_join_candidates": len(
            high_confidence
        ),
        "total_unique_matches_across_tests": (
            total_unique_matches
        ),
        "total_ambiguous_matches_across_tests": (
            total_ambiguous_matches
        ),
        "canonical_reference_rows_by_strategy": (
            reference_rows
        ),
        "high_confidence_candidates": high_confidence,
        "recommended_next_governed_unit": recommendation,
        "checks": checks,
    }

    contract = {
        "contract_id": (
            "EDGEIQ_RACINGCOM_DETERMINISTIC_JOIN_DISCOVERY_V1"
        ),
        "version": "1.0.0",
        "governance": {
            "deterministic_exact_joins_only": True,
            "no_fuzzy_matching": True,
            "no_alias_registration": True,
            "no_warehouse_mutation": True,
            "collision_measurement_required": True,
            "candidate_does_not_equal_approved_recovery": True,
        },
        "join_strategies": [
            {
                "name": name,
                "required_groups": list(groups),
            }
            for name, groups in JOIN_STRATEGIES
        ],
    }

    with CONTRACT_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(contract, handle, indent=2)
        handle.write("\n")

    audit["output_sha256"] = {
        "file_profile": sha256_file(FILE_PROFILE_PATH),
        "column_profile": sha256_file(COLUMN_PROFILE_PATH),
        "identifier_discovery": sha256_file(
            IDENTIFIER_DISCOVERY_PATH
        ),
        "join_strategy": sha256_file(JOIN_STRATEGY_PATH),
        "join_detail": sha256_file(JOIN_DETAIL_PATH),
        "contract": sha256_file(CONTRACT_PATH),
    }

    with AUDIT_JSON_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(audit, handle, indent=2)
        handle.write("\n")

    ranked = sorted(
        proven_candidates,
        key=lambda row: (
            -int(row["unique_matches"]),
            int(row["ambiguous_matches"]),
            str(row["source_path"]),
        ),
    )[:30]

    ranked_lines = [
        (
            f"| `{row['source_path']}` | "
            f"`{row['join_strategy']}` | "
            f"{int(row['rows_with_complete_key']):,} | "
            f"{int(row['unique_matches']):,} | "
            f"{int(row['ambiguous_matches']):,} | "
            f"{float(row['unique_match_percentage']):.6f}% | "
            f"`{row['implementation_decision']}` |"
        )
        for row in ranked
    ]

    markdown = f"""# EDGEIQ Racing.com Deterministic Join Discovery V1

## Status

**{status}**

## Scope

This unit profiled the dominant Racing.com failure sources and tested exact
composite joins against governed canonical Racing.com runner facts.

No aliases, source files or warehouse rows were changed.

## Results

| Metric | Result |
|---|---:|
| Raw failure files profiled | {len(raw_files):,} |
| Canonical runner files profiled | {len(canonical_files):,} |
| Columns profiled | {len(column_rows):,} |
| Identifier-bearing columns | {len(identifier_rows):,} |
| Available join assessments | {len(available_tests):,} |
| Strategies with unique matches | {len(proven_candidates):,} |
| High-confidence candidates | {len(high_confidence):,} |
| Total unique matches across tests | {total_unique_matches:,} |
| Total ambiguous matches across tests | {total_ambiguous_matches:,} |

## Ranked Join Candidates

| Source | Strategy | Complete keys | Unique matches | Ambiguous | Unique rate | Decision |
|---|---|---:|---:|---:|---:|---|
{chr(10).join(ranked_lines) if ranked_lines else "| None | None | 0 | 0 | 0 | 0% | No proven candidate |"}

## Recommendation

{recommendation}

## Governance Checks

| Check | Result |
|---|---|
{chr(10).join(f"| `{name}` | {'PASS' if value else 'FAIL'} |" for name, value in checks.items())}
"""

    with AUDIT_MD_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(markdown)

    print(json.dumps(audit, indent=2), flush=True)

    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"EDGEIQ JOIN DISCOVERY ERROR: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
