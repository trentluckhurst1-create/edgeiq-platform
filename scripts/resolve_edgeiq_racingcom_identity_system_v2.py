from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = REPO_ROOT / "public" / "data"

WAREHOUSE_ROOT = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
)

FAILURE_CLASSIFICATION_DIR = (
    WAREHOUSE_ROOT
    / "historical-observation-failure-classification-v1"
)

FAILURE_DETAIL_PATH = (
    FAILURE_CLASSIFICATION_DIR
    / "edgeiq_failure_reason_detail_v1.csv"
)

OUTPUT_DIR = (
    WAREHOUSE_ROOT
    / "racingcom-identity-resolution-v2"
)

SOURCE_FILE_INVENTORY_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_identity_source_inventory_v2.csv"
)

HORSE_KEY_PROFILE_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_horse_key_profile_v2.csv"
)

HORSE_KEY_NAME_EVIDENCE_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_horse_key_name_evidence_v2.csv"
)

HORSE_KEY_COLLISION_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_horse_key_collision_ledger_v2.csv"
)

HORSE_KEY_CROSSWALK_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_horse_key_canonical_crosswalk_v2.csv"
)

HORSE_KEY_UNRESOLVED_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_horse_key_unresolved_v2.csv"
)

FAILURE_RECOVERY_SUMMARY_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_failure_recovery_summary_v2.csv"
)

FAILURE_RECOVERY_CANDIDATES_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_failure_recovery_candidates_v2.csv"
)

REGRESSION_MANIFEST_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_identity_regression_manifest_v2.json"
)

ROLLBACK_MANIFEST_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_identity_rollback_manifest_v2.json"
)

CONTRACT_PATH = (
    OUTPUT_DIR
    / "edgeiq_racingcom_identity_resolution_v2_contract.json"
)

IMPLEMENTATION_SCRIPT_PATH = (
    REPO_ROOT
    / "scripts"
    / "apply_edgeiq_racingcom_identity_resolution_v2.py"
)

AUDIT_JSON_PATH = (
    OUTPUT_DIR
    / "EDGEIQ_RACINGCOM_IDENTITY_RESOLUTION_V2_AUDIT.json"
)

AUDIT_MD_PATH = (
    OUTPUT_DIR
    / "EDGEIQ_RACINGCOM_IDENTITY_RESOLUTION_V2_AUDIT.md"
)

PASS_STATUS = (
    "EDGEIQ_RACINGCOM_IDENTITY_RESOLUTION_V2_AUDIT_PASS"
)

FAIL_STATUS = (
    "EDGEIQ_RACINGCOM_IDENTITY_RESOLUTION_V2_AUDIT_FAIL"
)

HORSE_MASTER_CANDIDATES = [
    PUBLIC_DATA / "edgeiq_canonical_horse_master_v2.csv",
    PUBLIC_DATA / "edgeiq_canonical_horse_master_v2_CANDIDATE.csv",
]

ALIAS_CANDIDATES = [
    PUBLIC_DATA / "edgeiq_canonical_horse_alias_v2.csv",
    PUBLIC_DATA / "edgeiq_canonical_horse_alias_v2_CANDIDATE.csv",
]

HORSE_KEY_FIELDS = {
    "horse_key",
    "horsekey",
    "source_horse_id",
    "sourcehorseid",
}

HORSE_NAME_FIELDS = {
    "source_horse_name",
    "sourcehorsename",
    "horse_name",
    "horsename",
    "horse",
    "runner_name",
    "runnername",
    "runner",
    "competitor_name",
    "competitorname",
}

SOURCE_URL_FIELDS = {
    "source_url",
    "sourceurl",
    "horse_url",
    "horseurl",
    "runner_url",
    "runnerurl",
    "profile_url",
    "profileurl",
    "url",
    "href",
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
    "canonicaltrack",
    "track",
    "track_name",
    "trackname",
    "venue",
    "venue_name",
    "venuename",
    "meeting",
}

RACE_NUMBER_FIELDS = {
    "race_number",
    "racenumber",
    "race_no",
    "raceno",
}

RUNNER_NUMBER_FIELDS = {
    "saddlecloth",
    "saddlecloth_number",
    "saddleclothnumber",
    "runner_number",
    "runnernumber",
    "tab_number",
    "tabnumber",
    "number",
}

FAILURE_KEY_FIELDS = {
    "horse_key",
    "source_horse_id",
    "raw_horse_key",
}

COUNTRY_SUFFIX_RE = re.compile(
    r"\s*\((AUS|NZ|IRE|GB|USA|FR|JPN|SAF|GER|CAN|ARG|BRZ|CHI|HK|UAE)\)\s*$",
    re.IGNORECASE,
)

LONG_NUMERIC_TOKEN_RE = re.compile(r"(?<!\d)(\d{4,})(?!\d)")

URL_ID_PATTERNS = [
    re.compile(
        r"/horse/[^/?#]*?(\d{4,})(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"/horses/[^/?#]*?(\d{4,})(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"[?&](?:horseId|horse_id|runnerId|runner_id)=(\d+)",
        re.IGNORECASE,
    ),
]

CROSSWALK_FIELDS = [
    "source_system",
    "source_horse_id",
    "horse_key",
    "canonical_horse_id",
    "canonical_horse_name",
    "canonical_match_method",
    "identity_status",
    "normalised_horse_name",
    "source_name_count",
    "source_row_count",
    "source_file_count",
    "source_url_count",
    "racingcom_numeric_id_count",
    "racingcom_numeric_ids",
    "first_observed_date",
    "last_observed_date",
    "evidence_sha256",
]

UNRESOLVED_FIELDS = [
    "source_system",
    "horse_key",
    "identity_status",
    "resolution_reason",
    "normalised_names",
    "source_row_count",
    "source_file_count",
    "source_url_count",
    "racingcom_numeric_ids",
    "first_observed_date",
    "last_observed_date",
    "evidence_sha256",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def normalise_field(value: object) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(value).lower(),
    ).strip("_")


def normalise_horse_name(value: object) -> str:
    text = clean(value).upper()
    text = COUNTRY_SUFFIX_RE.sub("", text)
    text = text.replace("&", " AND ")
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_date(value: object) -> str:
    text = clean(value)

    if not text:
        return ""

    match = re.match(
        r"^(\d{4})[-/](\d{2})[-/](\d{2})",
        text,
    )

    if match:
        return (
            f"{match.group(1)}-"
            f"{match.group(2)}-"
            f"{match.group(3)}"
        )

    match = re.match(
        r"^(\d{2})[-/](\d{2})[-/](\d{4})",
        text,
    )

    if match:
        return (
            f"{match.group(3)}-"
            f"{match.group(2)}-"
            f"{match.group(1)}"
        )

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


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def locate_first_existing(
    candidates: Sequence[Path],
    label: str,
) -> Path:
    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"No {label} found. Checked: "
        + ", ".join(str(path) for path in candidates)
    )


def is_racingcom_path(value: object) -> bool:
    text = clean(value).replace("\\", "/").lower()

    return any(
        token in text
        for token in (
            "racingcom",
            "racing.com",
            "racing_com",
        )
    )


def discover_racingcom_csv_files() -> List[Path]:
    files: List[Path] = []

    for path in PUBLIC_DATA.rglob("*.csv"):
        relative = str(
            path.relative_to(REPO_ROOT)
        ).replace("\\", "/")

        if is_racingcom_path(relative):
            files.append(path)

    return sorted(
        set(files),
        key=lambda path: str(path).lower(),
    )


def read_header(
    path: Path,
) -> Tuple[List[str], str]:
    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ):
        try:
            with path.open(
                "r",
                encoding=encoding,
                newline="",
            ) as handle:
                reader = csv.reader(handle)
                return (
                    [clean(value) for value in next(reader, [])],
                    encoding,
                )
        except UnicodeDecodeError:
            continue

    raise UnicodeError(f"Unable to decode CSV: {path}")


def find_column(
    fieldnames: Sequence[str],
    candidates: Set[str],
) -> Optional[str]:
    for field in fieldnames:
        if normalise_field(field) in candidates:
            return field

    return None


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
                {
                    field: row.get(field, "")
                    for field in fields
                }
            )


def extract_numeric_ids(url: str) -> Set[str]:
    values: Set[str] = set()

    if not url:
        return values

    for pattern in URL_ID_PATTERNS:
        for match in pattern.findall(url):
            values.add(clean(match))

    if not values:
        for match in LONG_NUMERIC_TOKEN_RE.findall(url):
            values.add(clean(match))

    return values


def load_canonical_name_indexes(
    horse_master_path: Path,
    alias_path: Path,
) -> Tuple[
    Dict[str, Tuple[str, str]],
    Dict[str, Set[str]],
    Dict[str, Tuple[str, str]],
    Dict[str, Set[str]],
    int,
    int,
]:
    canonical_name_ids: Dict[str, Set[str]] = defaultdict(set)
    canonical_name_display: Dict[
        Tuple[str, str],
        str
    ] = {}

    horse_rows = 0

    with horse_master_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                f"No Horse Master header: {horse_master_path}"
            )

        required = {
            "canonical_horse_id",
            "canonical_horse_name",
        }

        missing = required.difference(reader.fieldnames)

        if missing:
            raise RuntimeError(
                "Horse Master missing required columns: "
                + ", ".join(sorted(missing))
            )

        for row in reader:
            horse_rows += 1

            canonical_id = clean(
                row.get("canonical_horse_id")
            )

            canonical_name = clean(
                row.get("canonical_horse_name")
            )

            normalised_name = normalise_horse_name(
                canonical_name
            )

            if not canonical_id or not normalised_name:
                continue

            canonical_name_ids[
                normalised_name
            ].add(canonical_id)

            canonical_name_display[
                (normalised_name, canonical_id)
            ] = canonical_name

    canonical_unique: Dict[
        str,
        Tuple[str, str]
    ] = {}

    canonical_ambiguous: Dict[
        str,
        Set[str]
    ] = {}

    for normalised_name, ids in canonical_name_ids.items():
        if len(ids) == 1:
            canonical_id = next(iter(ids))

            canonical_unique[normalised_name] = (
                canonical_id,
                canonical_name_display[
                    (normalised_name, canonical_id)
                ],
            )
        else:
            canonical_ambiguous[
                normalised_name
            ] = ids

    alias_name_ids: Dict[str, Set[str]] = defaultdict(set)
    alias_name_display: Dict[
        Tuple[str, str],
        str
    ] = {}

    alias_rows = 0

    with alias_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                f"No alias registry header: {alias_path}"
            )

        canonical_id_column = find_column(
            reader.fieldnames,
            {
                "canonical_horse_id",
                "canonicalhorseid",
            },
        )

        alias_column = find_column(
            reader.fieldnames,
            {
                "alias",
                "alias_name",
                "aliasname",
                "source_horse_name",
                "sourcehorsename",
                "horse_name",
                "horsename",
            },
        )

        if canonical_id_column and alias_column:
            for row in reader:
                alias_rows += 1

                canonical_id = clean(
                    row.get(canonical_id_column)
                )

                alias_name = clean(
                    row.get(alias_column)
                )

                normalised_alias = normalise_horse_name(
                    alias_name
                )

                if not canonical_id or not normalised_alias:
                    continue

                alias_name_ids[
                    normalised_alias
                ].add(canonical_id)

                alias_name_display[
                    (normalised_alias, canonical_id)
                ] = alias_name

    alias_unique: Dict[
        str,
        Tuple[str, str]
    ] = {}

    alias_ambiguous: Dict[
        str,
        Set[str]
    ] = {}

    for normalised_alias, ids in alias_name_ids.items():
        if len(ids) == 1:
            canonical_id = next(iter(ids))

            canonical_name = ""

            for (
                master_name,
                master_id
            ), display_name in canonical_name_display.items():
                if master_id == canonical_id:
                    canonical_name = display_name
                    break

            alias_unique[normalised_alias] = (
                canonical_id,
                canonical_name,
            )
        else:
            alias_ambiguous[
                normalised_alias
            ] = ids

    return (
        canonical_unique,
        canonical_ambiguous,
        alias_unique,
        alias_ambiguous,
        horse_rows,
        alias_rows,
    )


def generate_implementation_script() -> None:
    script = r'''from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

WAREHOUSE_ROOT = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
)

RESOLUTION_DIR = (
    WAREHOUSE_ROOT
    / "racingcom-identity-resolution-v2"
)

CROSSWALK_PATH = (
    RESOLUTION_DIR
    / "edgeiq_racingcom_horse_key_canonical_crosswalk_v2.csv"
)

FAILURE_DETAIL_PATH = (
    WAREHOUSE_ROOT
    / "historical-observation-failure-classification-v1"
    / "edgeiq_failure_reason_detail_v1.csv"
)

OUTPUT_PATH = (
    RESOLUTION_DIR
    / "edgeiq_racingcom_recovered_failure_rows_v2.csv"
)

UNRESOLVED_OUTPUT_PATH = (
    RESOLUTION_DIR
    / "edgeiq_racingcom_still_unresolved_failure_rows_v2.csv"
)

AUDIT_PATH = (
    RESOLUTION_DIR
    / "EDGEIQ_RACINGCOM_IDENTITY_APPLICATION_V2_AUDIT.json"
)

PASS_STATUS = (
    "EDGEIQ_RACINGCOM_IDENTITY_APPLICATION_V2_AUDIT_PASS"
)

FAIL_STATUS = (
    "EDGEIQ_RACINGCOM_IDENTITY_APPLICATION_V2_AUDIT_FAIL"
)


def clean(value):
    return "" if value is None else str(value).strip()


def normalise_field(value):
    import re

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(value).lower(),
    ).strip("_")


def find_column(fieldnames, candidates):
    for field in fieldnames or []:
        if normalise_field(field) in candidates:
            return field

    return None


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def main():
    if not CROSSWALK_PATH.exists():
        raise FileNotFoundError(CROSSWALK_PATH)

    if not FAILURE_DETAIL_PATH.exists():
        raise FileNotFoundError(FAILURE_DETAIL_PATH)

    crosswalk = {}

    with CROSSWALK_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            horse_key = clean(row.get("horse_key"))
            canonical_id = clean(
                row.get("canonical_horse_id")
            )

            if not horse_key or not canonical_id:
                continue

            crosswalk[horse_key] = row

    recovered = 0
    unresolved = 0
    excluded_non_racingcom = 0
    duplicate_recovery_keys = Counter()

    with (
        FAILURE_DETAIL_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as source_handle,
        OUTPUT_PATH.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as recovered_handle,
        UNRESOLVED_OUTPUT_PATH.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as unresolved_handle,
    ):
        reader = csv.DictReader(source_handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                "Failure ledger has no header."
            )

        horse_key_column = find_column(
            reader.fieldnames,
            {
                "horse_key",
                "source_horse_id",
                "raw_horse_key",
            },
        )

        if horse_key_column is None:
            raise RuntimeError(
                "Failure ledger contains no horse_key or "
                "source_horse_id column. The original source-row "
                "replay must be used before applying this crosswalk."
            )

        recovered_fields = list(reader.fieldnames)

        for field in (
            "resolved_canonical_horse_id",
            "resolved_canonical_horse_name",
            "identity_resolution_method",
            "identity_resolution_version",
        ):
            if field not in recovered_fields:
                recovered_fields.append(field)

        recovered_writer = csv.DictWriter(
            recovered_handle,
            fieldnames=recovered_fields,
            extrasaction="ignore",
            lineterminator="\n",
        )

        unresolved_writer = csv.DictWriter(
            unresolved_handle,
            fieldnames=reader.fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )

        recovered_writer.writeheader()
        unresolved_writer.writeheader()

        for row in reader:
            source_path = clean(
                row.get("source_path")
            ).replace("\\", "/").lower()

            if not any(
                token in source_path
                for token in (
                    "racingcom",
                    "racing.com",
                    "racing_com",
                )
            ):
                excluded_non_racingcom += 1
                continue

            horse_key = clean(
                row.get(horse_key_column)
            )

            mapping = crosswalk.get(horse_key)

            if mapping is None:
                unresolved += 1
                unresolved_writer.writerow(row)
                continue

            canonical_id = clean(
                mapping.get("canonical_horse_id")
            )

            duplicate_recovery_keys[
                canonical_id + "|" + horse_key
            ] += 1

            output_row = dict(row)
            output_row[
                "resolved_canonical_horse_id"
            ] = canonical_id
            output_row[
                "resolved_canonical_horse_name"
            ] = clean(
                mapping.get("canonical_horse_name")
            )
            output_row[
                "identity_resolution_method"
            ] = clean(
                mapping.get("canonical_match_method")
            )
            output_row[
                "identity_resolution_version"
            ] = "RACINGCOM_IDENTITY_RESOLUTION_V2"

            recovered_writer.writerow(output_row)
            recovered += 1

    checks = {
        "crosswalk_loaded": bool(crosswalk),
        "recovered_output_exists": OUTPUT_PATH.exists(),
        "unresolved_output_exists": (
            UNRESOLVED_OUTPUT_PATH.exists()
        ),
        "recovery_counts_nonnegative": (
            recovered >= 0 and unresolved >= 0
        ),
        "production_warehouse_not_mutated": True,
    }

    status = (
        PASS_STATUS
        if all(checks.values())
        else FAIL_STATUS
    )

    audit = {
        "status": status,
        "generated_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        ),
        "crosswalk_rows_loaded": len(crosswalk),
        "racingcom_failure_rows_recovered": recovered,
        "racingcom_failure_rows_still_unresolved": (
            unresolved
        ),
        "non_racingcom_rows_excluded": (
            excluded_non_racingcom
        ),
        "crosswalk_sha256": sha256_file(
            CROSSWALK_PATH
        ),
        "failure_detail_sha256": sha256_file(
            FAILURE_DETAIL_PATH
        ),
        "recovered_output_sha256": sha256_file(
            OUTPUT_PATH
        ),
        "unresolved_output_sha256": sha256_file(
            UNRESOLVED_OUTPUT_PATH
        ),
        "checks": checks,
    }

    AUDIT_PATH.write_text(
        json.dumps(
            audit,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(audit, indent=2))

    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"EDGEIQ RACINGCOM IDENTITY APPLICATION ERROR: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
'''

    IMPLEMENTATION_SCRIPT_PATH.write_text(
        script,
        encoding="utf-8",
    )


def main() -> int:
    started_at = utc_now_iso()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not FAILURE_DETAIL_PATH.exists():
        raise FileNotFoundError(
            f"Failure ledger not found: "
            f"{FAILURE_DETAIL_PATH}"
        )

    horse_master_path = locate_first_existing(
        HORSE_MASTER_CANDIDATES,
        "canonical Horse Master",
    )

    alias_path = locate_first_existing(
        ALIAS_CANDIDATES,
        "canonical alias registry",
    )

    racingcom_files = discover_racingcom_csv_files()

    if not racingcom_files:
        raise RuntimeError(
            "No Racing.com CSV files were discovered."
        )

    print(
        f"Racing.com CSV files discovered: "
        f"{len(racingcom_files):,}",
        flush=True,
    )

    (
        canonical_unique,
        canonical_ambiguous,
        alias_unique,
        alias_ambiguous,
        horse_master_rows,
        alias_rows,
    ) = load_canonical_name_indexes(
        horse_master_path,
        alias_path,
    )

    print(
        f"Horse Master rows: {horse_master_rows:,}",
        flush=True,
    )

    print(
        f"Unique canonical names: "
        f"{len(canonical_unique):,}",
        flush=True,
    )

    print(
        f"Ambiguous canonical names: "
        f"{len(canonical_ambiguous):,}",
        flush=True,
    )

    print(
        f"Alias registry rows: {alias_rows:,}",
        flush=True,
    )

    horse_key_rows: Counter = Counter()
    horse_key_names: Dict[
        str,
        Counter
    ] = defaultdict(Counter)

    horse_key_display_names: Dict[
        Tuple[str, str],
        Counter
    ] = defaultdict(Counter)

    horse_key_files: Dict[
        str,
        Set[str]
    ] = defaultdict(set)

    horse_key_urls: Dict[
        str,
        Set[str]
    ] = defaultdict(set)

    horse_key_numeric_ids: Dict[
        str,
        Set[str]
    ] = defaultdict(set)

    horse_key_dates: Dict[
        str,
        Set[str]
    ] = defaultdict(set)

    horse_key_tracks: Dict[
        str,
        Set[str]
    ] = defaultdict(set)

    horse_key_race_numbers: Dict[
        str,
        Set[str]
    ] = defaultdict(set)

    horse_key_runner_numbers: Dict[
        str,
        Set[str]
    ] = defaultdict(set)

    source_inventory_rows: List[
        Dict[str, object]
    ] = []

    total_racingcom_rows = 0
    total_rows_with_horse_key = 0
    unreadable_files = 0
    files_with_horse_key = 0
    files_with_horse_name = 0
    files_with_url = 0

    for file_index, path in enumerate(
        racingcom_files,
        start=1,
    ):
        relative = str(
            path.relative_to(REPO_ROOT)
        ).replace("\\", "/")

        print(
            f"[{file_index:,}/{len(racingcom_files):,}] "
            f"Scanning {relative}",
            flush=True,
        )

        try:
            header, encoding = read_header(path)

            horse_key_column = find_column(
                header,
                HORSE_KEY_FIELDS,
            )

            horse_name_column = find_column(
                header,
                HORSE_NAME_FIELDS,
            )

            source_url_column = find_column(
                header,
                SOURCE_URL_FIELDS,
            )

            date_column = find_column(
                header,
                DATE_FIELDS,
            )

            track_column = find_column(
                header,
                TRACK_FIELDS,
            )

            race_number_column = find_column(
                header,
                RACE_NUMBER_FIELDS,
            )

            runner_number_column = find_column(
                header,
                RUNNER_NUMBER_FIELDS,
            )

            if horse_key_column:
                files_with_horse_key += 1

            if horse_name_column:
                files_with_horse_name += 1

            if source_url_column:
                files_with_url += 1

            file_rows = 0
            file_key_rows = 0
            file_unique_keys: Set[str] = set()

            with path.open(
                "r",
                encoding=encoding,
                errors="replace",
                newline="",
            ) as handle:
                reader = csv.DictReader(handle)

                for row in reader:
                    file_rows += 1
                    total_racingcom_rows += 1

                    horse_key = (
                        clean(row.get(horse_key_column))
                        if horse_key_column
                        else ""
                    )

                    if not horse_key:
                        continue

                    file_key_rows += 1
                    total_rows_with_horse_key += 1
                    file_unique_keys.add(horse_key)

                    horse_key_rows[horse_key] += 1
                    horse_key_files[horse_key].add(
                        relative
                    )

                    horse_name = (
                        clean(row.get(horse_name_column))
                        if horse_name_column
                        else ""
                    )

                    normalised_name = normalise_horse_name(
                        horse_name
                    )

                    if normalised_name:
                        horse_key_names[
                            horse_key
                        ][normalised_name] += 1

                        horse_key_display_names[
                            (horse_key, normalised_name)
                        ][horse_name] += 1

                    source_url = (
                        clean(row.get(source_url_column))
                        if source_url_column
                        else ""
                    )

                    if source_url:
                        if len(
                            horse_key_urls[horse_key]
                        ) < 100:
                            horse_key_urls[
                                horse_key
                            ].add(source_url)

                        horse_key_numeric_ids[
                            horse_key
                        ].update(
                            extract_numeric_ids(source_url)
                        )

                    race_date = (
                        normalise_date(
                            row.get(date_column)
                        )
                        if date_column
                        else ""
                    )

                    if race_date:
                        horse_key_dates[
                            horse_key
                        ].add(race_date)

                    track = (
                        clean(row.get(track_column))
                        if track_column
                        else ""
                    )

                    if track:
                        horse_key_tracks[
                            horse_key
                        ].add(track)

                    race_number = (
                        clean(
                            row.get(race_number_column)
                        )
                        if race_number_column
                        else ""
                    )

                    if race_number:
                        horse_key_race_numbers[
                            horse_key
                        ].add(race_number)

                    runner_number = (
                        clean(
                            row.get(runner_number_column)
                        )
                        if runner_number_column
                        else ""
                    )

                    if runner_number:
                        horse_key_runner_numbers[
                            horse_key
                        ].add(runner_number)

            source_inventory_rows.append(
                {
                    "source_path": relative,
                    "file_size_bytes": path.stat().st_size,
                    "data_rows": file_rows,
                    "rows_with_horse_key": file_key_rows,
                    "unique_horse_keys": len(
                        file_unique_keys
                    ),
                    "horse_key_column": (
                        horse_key_column or ""
                    ),
                    "horse_name_column": (
                        horse_name_column or ""
                    ),
                    "source_url_column": (
                        source_url_column or ""
                    ),
                    "race_date_column": (
                        date_column or ""
                    ),
                    "track_column": (
                        track_column or ""
                    ),
                    "race_number_column": (
                        race_number_column or ""
                    ),
                    "runner_number_column": (
                        runner_number_column or ""
                    ),
                    "sha256": sha256_file(path),
                    "status": "READABLE",
                }
            )

        except Exception as exc:
            unreadable_files += 1

            source_inventory_rows.append(
                {
                    "source_path": relative,
                    "file_size_bytes": (
                        path.stat().st_size
                        if path.exists()
                        else 0
                    ),
                    "data_rows": "",
                    "rows_with_horse_key": "",
                    "unique_horse_keys": "",
                    "horse_key_column": "",
                    "horse_name_column": "",
                    "source_url_column": "",
                    "race_date_column": "",
                    "track_column": "",
                    "race_number_column": "",
                    "runner_number_column": "",
                    "sha256": "",
                    "status": (
                        f"UNREADABLE:"
                        f"{type(exc).__name__}:"
                        f"{exc}"
                    ),
                }
            )

    print(
        f"Rows scanned: {total_racingcom_rows:,}",
        flush=True,
    )

    print(
        f"Rows with horse_key: "
        f"{total_rows_with_horse_key:,}",
        flush=True,
    )

    print(
        f"Unique horse_key values: "
        f"{len(horse_key_rows):,}",
        flush=True,
    )

    profile_rows: List[Dict[str, object]] = []
    name_evidence_rows: List[
        Dict[str, object]
    ] = []
    collision_rows: List[
        Dict[str, object]
    ] = []
    crosswalk_rows: List[
        Dict[str, object]
    ] = []
    unresolved_rows: List[
        Dict[str, object]
    ] = []

    stable_single_name_keys = 0
    multi_name_keys = 0
    blank_name_keys = 0
    canonical_master_resolved_keys = 0
    alias_resolved_keys = 0
    unresolved_unique_name_keys = 0
    canonical_ambiguous_keys = 0
    alias_ambiguous_keys = 0
    conflicting_mapping_keys = 0

    crosswalk_by_horse_key: Dict[
        str,
        Dict[str, object]
    ] = {}

    for horse_key in sorted(horse_key_rows):
        name_counter = horse_key_names.get(
            horse_key,
            Counter(),
        )

        normalised_names = sorted(
            name_counter.keys()
        )

        source_files = sorted(
            horse_key_files.get(
                horse_key,
                set(),
            )
        )

        source_urls = sorted(
            horse_key_urls.get(
                horse_key,
                set(),
            )
        )

        numeric_ids = sorted(
            horse_key_numeric_ids.get(
                horse_key,
                set(),
            )
        )

        observed_dates = sorted(
            horse_key_dates.get(
                horse_key,
                set(),
            )
        )

        first_date = (
            observed_dates[0]
            if observed_dates
            else ""
        )

        last_date = (
            observed_dates[-1]
            if observed_dates
            else ""
        )

        evidence_payload = {
            "horse_key": horse_key,
            "normalised_names": normalised_names,
            "source_files": source_files,
            "numeric_ids": numeric_ids,
            "first_date": first_date,
            "last_date": last_date,
            "row_count": horse_key_rows[horse_key],
        }

        evidence_sha256 = sha256_text(
            json.dumps(
                evidence_payload,
                sort_keys=True,
                ensure_ascii=False,
            )
        )

        if len(normalised_names) == 0:
            stability_status = "NO_NAME_EVIDENCE"
            blank_name_keys += 1
        elif len(normalised_names) == 1:
            stability_status = (
                "STABLE_SINGLE_NORMALISED_NAME"
            )
            stable_single_name_keys += 1
        else:
            stability_status = (
                "MULTIPLE_NORMALISED_NAMES"
            )
            multi_name_keys += 1

        profile_rows.append(
            {
                "source_system": "RACINGCOM",
                "horse_key": horse_key,
                "source_row_count": (
                    horse_key_rows[horse_key]
                ),
                "normalised_name_count": len(
                    normalised_names
                ),
                "normalised_names": "|".join(
                    normalised_names
                ),
                "source_file_count": len(
                    source_files
                ),
                "source_url_count": len(
                    source_urls
                ),
                "racingcom_numeric_id_count": len(
                    numeric_ids
                ),
                "racingcom_numeric_ids": "|".join(
                    numeric_ids
                ),
                "observed_date_count": len(
                    observed_dates
                ),
                "first_observed_date": first_date,
                "last_observed_date": last_date,
                "track_count": len(
                    horse_key_tracks.get(
                        horse_key,
                        set(),
                    )
                ),
                "race_number_count": len(
                    horse_key_race_numbers.get(
                        horse_key,
                        set(),
                    )
                ),
                "runner_number_count": len(
                    horse_key_runner_numbers.get(
                        horse_key,
                        set(),
                    )
                ),
                "stability_status": stability_status,
                "evidence_sha256": evidence_sha256,
            }
        )

        for normalised_name in normalised_names:
            display_counter = (
                horse_key_display_names.get(
                    (horse_key, normalised_name),
                    Counter(),
                )
            )

            display_names = [
                name
                for name, _ in display_counter.most_common()
            ]

            name_evidence_rows.append(
                {
                    "source_system": "RACINGCOM",
                    "horse_key": horse_key,
                    "normalised_horse_name": (
                        normalised_name
                    ),
                    "observed_row_count": (
                        name_counter[normalised_name]
                    ),
                    "display_name_count": len(
                        display_names
                    ),
                    "display_names": "|".join(
                        display_names
                    ),
                    "source_row_count": (
                        horse_key_rows[horse_key]
                    ),
                    "source_file_count": len(
                        source_files
                    ),
                    "evidence_sha256": (
                        evidence_sha256
                    ),
                }
            )

        if len(normalised_names) > 1:
            collision_rows.append(
                {
                    "source_system": "RACINGCOM",
                    "horse_key": horse_key,
                    "collision_type": (
                        "HORSE_KEY_MULTIPLE_NAMES"
                    ),
                    "normalised_name_count": len(
                        normalised_names
                    ),
                    "normalised_names": "|".join(
                        normalised_names
                    ),
                    "source_row_count": (
                        horse_key_rows[horse_key]
                    ),
                    "source_file_count": len(
                        source_files
                    ),
                    "source_files": "|".join(
                        source_files
                    ),
                    "first_observed_date": first_date,
                    "last_observed_date": last_date,
                    "racingcom_numeric_ids": "|".join(
                        numeric_ids
                    ),
                    "evidence_sha256": (
                        evidence_sha256
                    ),
                }
            )

            unresolved_rows.append(
                {
                    "source_system": "RACINGCOM",
                    "horse_key": horse_key,
                    "identity_status": (
                        "REJECTED_COLLISION"
                    ),
                    "resolution_reason": (
                        "One horse_key maps to multiple "
                        "normalised horse names."
                    ),
                    "normalised_names": "|".join(
                        normalised_names
                    ),
                    "source_row_count": (
                        horse_key_rows[horse_key]
                    ),
                    "source_file_count": len(
                        source_files
                    ),
                    "source_url_count": len(
                        source_urls
                    ),
                    "racingcom_numeric_ids": "|".join(
                        numeric_ids
                    ),
                    "first_observed_date": first_date,
                    "last_observed_date": last_date,
                    "evidence_sha256": (
                        evidence_sha256
                    ),
                }
            )

            continue

        if not normalised_names:
            unresolved_rows.append(
                {
                    "source_system": "RACINGCOM",
                    "horse_key": horse_key,
                    "identity_status": (
                        "UNRESOLVED_NO_NAME"
                    ),
                    "resolution_reason": (
                        "No usable horse-name evidence."
                    ),
                    "normalised_names": "",
                    "source_row_count": (
                        horse_key_rows[horse_key]
                    ),
                    "source_file_count": len(
                        source_files
                    ),
                    "source_url_count": len(
                        source_urls
                    ),
                    "racingcom_numeric_ids": "|".join(
                        numeric_ids
                    ),
                    "first_observed_date": first_date,
                    "last_observed_date": last_date,
                    "evidence_sha256": (
                        evidence_sha256
                    ),
                }
            )

            continue

        normalised_name = normalised_names[0]

        master_match = canonical_unique.get(
            normalised_name
        )

        alias_match = alias_unique.get(
            normalised_name
        )

        master_ambiguous = (
            normalised_name
            in canonical_ambiguous
        )

        alias_is_ambiguous = (
            normalised_name
            in alias_ambiguous
        )

        canonical_id = ""
        canonical_name = ""
        match_method = ""
        resolution_reason = ""

        if (
            master_match
            and alias_match
            and master_match[0] != alias_match[0]
        ):
            conflicting_mapping_keys += 1
            resolution_reason = (
                "Canonical master and alias registry "
                "resolve the same name to different IDs."
            )

        elif master_match:
            canonical_id = master_match[0]
            canonical_name = master_match[1]
            match_method = (
                "EXACT_UNIQUE_CANONICAL_NAME"
            )
            canonical_master_resolved_keys += 1

        elif alias_match:
            canonical_id = alias_match[0]
            canonical_name = alias_match[1]
            match_method = (
                "EXACT_UNIQUE_ALIAS_NAME"
            )
            alias_resolved_keys += 1

        elif master_ambiguous:
            canonical_ambiguous_keys += 1
            resolution_reason = (
                "Exact canonical name is ambiguous."
            )

        elif alias_is_ambiguous:
            alias_ambiguous_keys += 1
            resolution_reason = (
                "Exact alias name is ambiguous."
            )

        else:
            unresolved_unique_name_keys += 1
            resolution_reason = (
                "No exact canonical or alias match."
            )

        if canonical_id:
            selected_display_names = (
                horse_key_display_names.get(
                    (horse_key, normalised_name),
                    Counter(),
                ).most_common()
            )

            source_display_name = (
                selected_display_names[0][0]
                if selected_display_names
                else ""
            )

            crosswalk_row = {
                "source_system": "RACINGCOM",
                "source_horse_id": horse_key,
                "horse_key": horse_key,
                "canonical_horse_id": canonical_id,
                "canonical_horse_name": canonical_name,
                "canonical_match_method": match_method,
                "identity_status": (
                    "DETERMINISTIC_CANDIDATE"
                ),
                "normalised_horse_name": (
                    normalised_name
                ),
                "source_name_count": len(
                    normalised_names
                ),
                "source_row_count": (
                    horse_key_rows[horse_key]
                ),
                "source_file_count": len(
                    source_files
                ),
                "source_url_count": len(
                    source_urls
                ),
                "racingcom_numeric_id_count": len(
                    numeric_ids
                ),
                "racingcom_numeric_ids": "|".join(
                    numeric_ids
                ),
                "first_observed_date": first_date,
                "last_observed_date": last_date,
                "evidence_sha256": evidence_sha256,
            }

            crosswalk_rows.append(
                crosswalk_row
            )

            crosswalk_by_horse_key[
                horse_key
            ] = crosswalk_row

        else:
            unresolved_rows.append(
                {
                    "source_system": "RACINGCOM",
                    "horse_key": horse_key,
                    "identity_status": (
                        "UNRESOLVED_UNIQUE_NAME"
                    ),
                    "resolution_reason": (
                        resolution_reason
                    ),
                    "normalised_names": (
                        normalised_name
                    ),
                    "source_row_count": (
                        horse_key_rows[horse_key]
                    ),
                    "source_file_count": len(
                        source_files
                    ),
                    "source_url_count": len(
                        source_urls
                    ),
                    "racingcom_numeric_ids": "|".join(
                        numeric_ids
                    ),
                    "first_observed_date": first_date,
                    "last_observed_date": last_date,
                    "evidence_sha256": (
                        evidence_sha256
                    ),
                }
            )

    write_csv(
        SOURCE_FILE_INVENTORY_PATH,
        [
            "source_path",
            "file_size_bytes",
            "data_rows",
            "rows_with_horse_key",
            "unique_horse_keys",
            "horse_key_column",
            "horse_name_column",
            "source_url_column",
            "race_date_column",
            "track_column",
            "race_number_column",
            "runner_number_column",
            "sha256",
            "status",
        ],
        source_inventory_rows,
    )

    write_csv(
        HORSE_KEY_PROFILE_PATH,
        [
            "source_system",
            "horse_key",
            "source_row_count",
            "normalised_name_count",
            "normalised_names",
            "source_file_count",
            "source_url_count",
            "racingcom_numeric_id_count",
            "racingcom_numeric_ids",
            "observed_date_count",
            "first_observed_date",
            "last_observed_date",
            "track_count",
            "race_number_count",
            "runner_number_count",
            "stability_status",
            "evidence_sha256",
        ],
        profile_rows,
    )

    write_csv(
        HORSE_KEY_NAME_EVIDENCE_PATH,
        [
            "source_system",
            "horse_key",
            "normalised_horse_name",
            "observed_row_count",
            "display_name_count",
            "display_names",
            "source_row_count",
            "source_file_count",
            "evidence_sha256",
        ],
        name_evidence_rows,
    )

    write_csv(
        HORSE_KEY_COLLISION_PATH,
        [
            "source_system",
            "horse_key",
            "collision_type",
            "normalised_name_count",
            "normalised_names",
            "source_row_count",
            "source_file_count",
            "source_files",
            "first_observed_date",
            "last_observed_date",
            "racingcom_numeric_ids",
            "evidence_sha256",
        ],
        collision_rows,
    )

    write_csv(
        HORSE_KEY_CROSSWALK_PATH,
        CROSSWALK_FIELDS,
        crosswalk_rows,
    )

    write_csv(
        HORSE_KEY_UNRESOLVED_PATH,
        UNRESOLVED_FIELDS,
        unresolved_rows,
    )

    failure_rows_scanned = 0
    racingcom_failure_rows = 0
    failure_rows_with_key = 0
    recoverable_failure_rows = 0
    unresolved_failure_rows = 0
    no_failure_key_column = False

    recovery_reason_counts: Counter = Counter()
    recovery_source_counts: Counter = Counter()

    failure_candidate_rows: List[
        Dict[str, object]
    ] = []

    with FAILURE_DETAIL_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                "Failure detail ledger has no header."
            )

        failure_horse_key_column = find_column(
            reader.fieldnames,
            FAILURE_KEY_FIELDS,
        )

        if failure_horse_key_column is None:
            no_failure_key_column = True

        for row in reader:
            failure_rows_scanned += 1

            source_path = clean(
                row.get("source_path")
            )

            if not is_racingcom_path(source_path):
                continue

            racingcom_failure_rows += 1

            horse_key = (
                clean(
                    row.get(
                        failure_horse_key_column
                    )
                )
                if failure_horse_key_column
                else ""
            )

            if horse_key:
                failure_rows_with_key += 1

            mapping = (
                crosswalk_by_horse_key.get(
                    horse_key
                )
                if horse_key
                else None
            )

            if mapping:
                recoverable_failure_rows += 1
                recovery_reason_counts[
                    "CROSSWALK_MATCH"
                ] += 1
                recovery_source_counts[
                    source_path
                ] += 1

                failure_candidate_rows.append(
                    {
                        "failure_classification_id": clean(
                            row.get(
                                "failure_classification_id"
                            )
                        ),
                        "source_path": source_path,
                        "source_row_number": clean(
                            row.get(
                                "source_row_number"
                            )
                        ),
                        "horse_key": horse_key,
                        "canonical_horse_id": clean(
                            mapping.get(
                                "canonical_horse_id"
                            )
                        ),
                        "canonical_horse_name": clean(
                            mapping.get(
                                "canonical_horse_name"
                            )
                        ),
                        "resolution_method": clean(
                            mapping.get(
                                "canonical_match_method"
                            )
                        ),
                        "identity_resolution_version": (
                            "RACINGCOM_IDENTITY_RESOLUTION_V2"
                        ),
                        "evidence_sha256": clean(
                            mapping.get(
                                "evidence_sha256"
                            )
                        ),
                    }
                )
            else:
                unresolved_failure_rows += 1

                if no_failure_key_column:
                    recovery_reason_counts[
                        "FAILURE_LEDGER_HAS_NO_HORSE_KEY"
                    ] += 1
                elif not horse_key:
                    recovery_reason_counts[
                        "FAILURE_ROW_HAS_NO_HORSE_KEY"
                    ] += 1
                else:
                    recovery_reason_counts[
                        "HORSE_KEY_NOT_IN_APPROVED_CROSSWALK"
                    ] += 1

    write_csv(
        FAILURE_RECOVERY_CANDIDATES_PATH,
        [
            "failure_classification_id",
            "source_path",
            "source_row_number",
            "horse_key",
            "canonical_horse_id",
            "canonical_horse_name",
            "resolution_method",
            "identity_resolution_version",
            "evidence_sha256",
        ],
        failure_candidate_rows,
    )

    recovery_summary_rows = [
        {
            "metric": "failure_rows_scanned",
            "value": failure_rows_scanned,
        },
        {
            "metric": "racingcom_failure_rows",
            "value": racingcom_failure_rows,
        },
        {
            "metric": "racingcom_failure_rows_with_horse_key",
            "value": failure_rows_with_key,
        },
        {
            "metric": "recoverable_failure_rows",
            "value": recoverable_failure_rows,
        },
        {
            "metric": "unresolved_failure_rows",
            "value": unresolved_failure_rows,
        },
        {
            "metric": "failure_ledger_has_horse_key_column",
            "value": (
                "false"
                if no_failure_key_column
                else "true"
            ),
        },
    ]

    for reason, count in sorted(
        recovery_reason_counts.items()
    ):
        recovery_summary_rows.append(
            {
                "metric": (
                    f"reason_{reason}"
                ),
                "value": count,
            }
        )

    write_csv(
        FAILURE_RECOVERY_SUMMARY_PATH,
        [
            "metric",
            "value",
        ],
        recovery_summary_rows,
    )

    generate_implementation_script()

    checks = {
        "horse_master_exists": (
            horse_master_path.exists()
        ),
        "alias_registry_exists": (
            alias_path.exists()
        ),
        "failure_detail_exists": (
            FAILURE_DETAIL_PATH.exists()
        ),
        "racingcom_files_discovered": (
            len(racingcom_files) > 0
        ),
        "all_discovered_files_accounted_for": (
            len(source_inventory_rows)
            == len(racingcom_files)
        ),
        "horse_key_population_nonzero": (
            len(horse_key_rows) > 0
        ),
        "horse_key_profile_reconciles": (
            len(profile_rows)
            == len(horse_key_rows)
        ),
        "crosswalk_and_unresolved_reconcile": (
            len(crosswalk_rows)
            + len(unresolved_rows)
            == len(horse_key_rows)
        ),
        "collision_keys_excluded_from_crosswalk": (
            all(
                clean(row["horse_key"])
                not in crosswalk_by_horse_key
                for row in collision_rows
            )
        ),
        "only_single_name_keys_in_crosswalk": (
            all(
                clean(row["source_name_count"])
                == "1"
                for row in crosswalk_rows
            )
        ),
        "no_fuzzy_matching_used": True,
        "no_production_warehouse_mutated": True,
        "no_alias_registry_mutated": True,
        "implementation_script_generated": (
            IMPLEMENTATION_SCRIPT_PATH.exists()
        ),
        "source_inventory_generated": (
            SOURCE_FILE_INVENTORY_PATH.exists()
        ),
        "crosswalk_generated": (
            HORSE_KEY_CROSSWALK_PATH.exists()
        ),
        "unresolved_ledger_generated": (
            HORSE_KEY_UNRESOLVED_PATH.exists()
        ),
    }

    status = (
        PASS_STATUS
        if all(checks.values())
        else FAIL_STATUS
    )

    crosswalk_row_coverage = sum(
        int(row["source_row_count"])
        for row in crosswalk_rows
    )

    crosswalk_key_percentage = (
        len(crosswalk_rows)
        / len(horse_key_rows)
        * 100
        if horse_key_rows
        else 0
    )

    crosswalk_row_percentage = (
        crosswalk_row_coverage
        / total_rows_with_horse_key
        * 100
        if total_rows_with_horse_key
        else 0
    )

    failure_recovery_percentage = (
        recoverable_failure_rows
        / racingcom_failure_rows
        * 100
        if racingcom_failure_rows
        else 0
    )

    contract = {
        "contract_id": (
            "EDGEIQ_RACINGCOM_IDENTITY_RESOLUTION_V2_CONTRACT"
        ),
        "version": "2.0.0",
        "purpose": (
            "Resolve stable Racing.com horse_key values to "
            "canonical horse identities through deterministic "
            "exact evidence only."
        ),
        "source_identity": {
            "source_system": "RACINGCOM",
            "source_horse_id_field": "horse_key",
        },
        "approved_candidate_methods": [
            "EXACT_UNIQUE_CANONICAL_NAME",
            "EXACT_UNIQUE_ALIAS_NAME",
        ],
        "prohibited_methods": [
            "FUZZY_NAME_MATCH",
            "EDIT_DISTANCE_MATCH",
            "MANUAL_GUESS",
            "AMBIGUOUS_NAME_MATCH",
            "MULTI_NAME_HORSE_KEY",
        ],
        "implementation_boundary": (
            "This unit generates candidate crosswalks and an "
            "application script but does not mutate production "
            "warehouse outputs."
        ),
        "outputs": [
            str(path.relative_to(REPO_ROOT)).replace(
                "\\",
                "/",
            )
            for path in (
                SOURCE_FILE_INVENTORY_PATH,
                HORSE_KEY_PROFILE_PATH,
                HORSE_KEY_NAME_EVIDENCE_PATH,
                HORSE_KEY_COLLISION_PATH,
                HORSE_KEY_CROSSWALK_PATH,
                HORSE_KEY_UNRESOLVED_PATH,
                FAILURE_RECOVERY_SUMMARY_PATH,
                FAILURE_RECOVERY_CANDIDATES_PATH,
                IMPLEMENTATION_SCRIPT_PATH,
                REGRESSION_MANIFEST_PATH,
                ROLLBACK_MANIFEST_PATH,
                AUDIT_JSON_PATH,
                AUDIT_MD_PATH,
            )
        ],
    }

    CONTRACT_PATH.write_text(
        json.dumps(
            contract,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    regression_manifest = {
        "manifest_id": (
            "EDGEIQ_RACINGCOM_IDENTITY_REGRESSION_MANIFEST_V2"
        ),
        "generated_at_utc": utc_now_iso(),
        "required_invariants": {
            "horse_key_count": len(
                horse_key_rows
            ),
            "collision_key_count": len(
                collision_rows
            ),
            "crosswalk_key_count": len(
                crosswalk_rows
            ),
            "unresolved_key_count": len(
                unresolved_rows
            ),
            "total_rows_with_horse_key": (
                total_rows_with_horse_key
            ),
            "crosswalk_row_coverage": (
                crosswalk_row_coverage
            ),
        },
        "required_rules": {
            "one_crosswalk_row_per_horse_key": True,
            "collision_keys_never_resolved": True,
            "fuzzy_matching_forbidden": True,
            "canonical_id_required": True,
            "evidence_hash_required": True,
        },
    }

    REGRESSION_MANIFEST_PATH.write_text(
        json.dumps(
            regression_manifest,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    rollback_manifest = {
        "manifest_id": (
            "EDGEIQ_RACINGCOM_IDENTITY_ROLLBACK_MANIFEST_V2"
        ),
        "generated_at_utc": utc_now_iso(),
        "production_mutation_performed": False,
        "rollback_required": False,
        "generated_candidate_outputs": [
            str(path.relative_to(REPO_ROOT)).replace(
                "\\",
                "/",
            )
            for path in (
                HORSE_KEY_CROSSWALK_PATH,
                FAILURE_RECOVERY_CANDIDATES_PATH,
            )
        ],
        "rollback_instruction": (
            "Delete the generated V2 candidate directory "
            "and implementation script if this governed unit "
            "is rejected. No production warehouse restoration "
            "is required because this run performs no mutation."
        ),
    }

    ROLLBACK_MANIFEST_PATH.write_text(
        json.dumps(
            rollback_manifest,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    audit = {
        "status": status,
        "started_at_utc": started_at,
        "generated_at_utc": utc_now_iso(),
        "racingcom_source_files_discovered": (
            len(racingcom_files)
        ),
        "racingcom_source_files_unreadable": (
            unreadable_files
        ),
        "racingcom_rows_scanned": (
            total_racingcom_rows
        ),
        "racingcom_rows_with_horse_key": (
            total_rows_with_horse_key
        ),
        "unique_horse_keys": len(
            horse_key_rows
        ),
        "stable_single_name_keys": (
            stable_single_name_keys
        ),
        "multi_name_collision_keys": (
            multi_name_keys
        ),
        "blank_name_keys": blank_name_keys,
        "canonical_master_resolved_keys": (
            canonical_master_resolved_keys
        ),
        "alias_resolved_keys": (
            alias_resolved_keys
        ),
        "resolved_crosswalk_keys": (
            len(crosswalk_rows)
        ),
        "unresolved_keys": (
            len(unresolved_rows)
        ),
        "unresolved_unique_name_keys": (
            unresolved_unique_name_keys
        ),
        "canonical_ambiguous_keys": (
            canonical_ambiguous_keys
        ),
        "alias_ambiguous_keys": (
            alias_ambiguous_keys
        ),
        "conflicting_mapping_keys": (
            conflicting_mapping_keys
        ),
        "crosswalk_key_percentage": round(
            crosswalk_key_percentage,
            6,
        ),
        "crosswalk_row_coverage": (
            crosswalk_row_coverage
        ),
        "crosswalk_row_percentage": round(
            crosswalk_row_percentage,
            6,
        ),
        "racingcom_failure_rows": (
            racingcom_failure_rows
        ),
        "failure_rows_with_horse_key": (
            failure_rows_with_key
        ),
        "recoverable_failure_rows": (
            recoverable_failure_rows
        ),
        "unresolved_failure_rows": (
            unresolved_failure_rows
        ),
        "failure_recovery_percentage": round(
            failure_recovery_percentage,
            6,
        ),
        "failure_ledger_has_horse_key_column": (
            not no_failure_key_column
        ),
        "horse_master_rows": (
            horse_master_rows
        ),
        "alias_registry_rows": (
            alias_rows
        ),
        "checks": checks,
        "recommended_next_action": (
            "Review the collision ledger and crosswalk. "
            "If coverage is material and all checks pass, run "
            "apply_edgeiq_racingcom_identity_resolution_v2.py "
            "to create recovered candidate failure rows. Then "
            "rebuild the historical observation warehouse from "
            "the governed recovered identity ledger."
        ),
    }

    audit["input_sha256"] = {
        "horse_master": sha256_file(
            horse_master_path
        ),
        "alias_registry": sha256_file(
            alias_path
        ),
        "failure_detail": sha256_file(
            FAILURE_DETAIL_PATH
        ),
    }

    audit["output_sha256"] = {
        "source_inventory": sha256_file(
            SOURCE_FILE_INVENTORY_PATH
        ),
        "horse_key_profile": sha256_file(
            HORSE_KEY_PROFILE_PATH
        ),
        "name_evidence": sha256_file(
            HORSE_KEY_NAME_EVIDENCE_PATH
        ),
        "collision_ledger": sha256_file(
            HORSE_KEY_COLLISION_PATH
        ),
        "crosswalk": sha256_file(
            HORSE_KEY_CROSSWALK_PATH
        ),
        "unresolved": sha256_file(
            HORSE_KEY_UNRESOLVED_PATH
        ),
        "failure_recovery_summary": sha256_file(
            FAILURE_RECOVERY_SUMMARY_PATH
        ),
        "failure_recovery_candidates": sha256_file(
            FAILURE_RECOVERY_CANDIDATES_PATH
        ),
        "implementation_script": sha256_file(
            IMPLEMENTATION_SCRIPT_PATH
        ),
        "contract": sha256_file(
            CONTRACT_PATH
        ),
        "regression_manifest": sha256_file(
            REGRESSION_MANIFEST_PATH
        ),
        "rollback_manifest": sha256_file(
            ROLLBACK_MANIFEST_PATH
        ),
    }

    AUDIT_JSON_PATH.write_text(
        json.dumps(
            audit,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    markdown = f"""# EDGEIQ Racing.com Identity Resolution V2

## Status

**{status}**

## Scope

This governed unit scanned every Racing.com CSV under `public/data`,
profiled every available `horse_key`, reconciled name evidence, extracted
numeric URL identifiers, matched stable keys against Horse Master and the
canonical alias registry, classified collisions, and generated a candidate
canonical identity crosswalk.

No production warehouse files were changed.

## Source Results

| Metric | Result |
|---|---:|
| Racing.com files discovered | {len(racingcom_files):,} |
| Unreadable files | {unreadable_files:,} |
| Racing.com rows scanned | {total_racingcom_rows:,} |
| Rows with `horse_key` | {total_rows_with_horse_key:,} |
| Unique `horse_key` values | {len(horse_key_rows):,} |
| Files with `horse_key` | {files_with_horse_key:,} |
| Files with horse names | {files_with_horse_name:,} |
| Files with source URLs | {files_with_url:,} |

## Identity Results

| Metric | Result |
|---|---:|
| Stable single-name keys | {stable_single_name_keys:,} |
| Multi-name collision keys | {multi_name_keys:,} |
| Keys with no usable name | {blank_name_keys:,} |
| Exact Horse Master resolutions | {canonical_master_resolved_keys:,} |
| Exact alias resolutions | {alias_resolved_keys:,} |
| Crosswalk keys generated | {len(crosswalk_rows):,} |
| Unresolved keys | {len(unresolved_rows):,} |
| Crosswalk key coverage | {crosswalk_key_percentage:.6f}% |
| Crosswalk source-row coverage | {crosswalk_row_coverage:,} |
| Source-row coverage percentage | {crosswalk_row_percentage:.6f}% |

## Historical Failure Recovery Potential

| Metric | Result |
|---|---:|
| Racing.com failure rows | {racingcom_failure_rows:,} |
| Failure rows containing `horse_key` | {failure_rows_with_key:,} |
| Recoverable candidate rows | {recoverable_failure_rows:,} |
| Still unresolved rows | {unresolved_failure_rows:,} |
| Potential failure recovery | {failure_recovery_percentage:.6f}% |
| Failure ledger has key field | {"YES" if not no_failure_key_column else "NO"} |

## Governance Rules

- `horse_key` is treated as the Racing.com source identity candidate.
- Only stable one-name keys are eligible.
- Exact unique Horse Master or alias matches only.
- Multi-name keys are rejected.
- Ambiguous names are rejected.
- Fuzzy matching is prohibited.
- No production warehouse or alias registry mutation occurs in this run.

## Generated Implementation

`{IMPLEMENTATION_SCRIPT_PATH.relative_to(REPO_ROOT)}`

The implementation script is generated but not executed automatically.

## Checks

| Check | Result |
|---|---|
{chr(10).join(f"| `{name}` | {'PASS' if value else 'FAIL'} |" for name, value in checks.items())}

## Next Action

Review the audit totals. If the V2 audit passes and recovery coverage is
material, execute the generated implementation script to produce recovered
candidate rows, then run the governed historical warehouse rebuild.
"""

    AUDIT_MD_PATH.write_text(
        markdown,
        encoding="utf-8",
    )

    print(
        json.dumps(
            audit,
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )

    return (
        0
        if status == PASS_STATUS
        else 1
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "EDGEIQ RACINGCOM IDENTITY RESOLUTION V2 ERROR: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
