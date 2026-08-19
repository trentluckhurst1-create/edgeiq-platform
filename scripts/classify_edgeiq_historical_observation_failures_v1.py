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

WAREHOUSE_DIR = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-run-observation"
)

OUTPUT_DIR = (
    REPO_ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-observation-failure-classification-v1"
)

IDENTITY_FAILURE_PATH = (
    WAREHOUSE_DIR
    / "edgeiq_historical_run_observation_v2_identity_failures.csv"
)

WAREHOUSE_AUDIT_PATH = (
    WAREHOUSE_DIR
    / "EDGEIQ_HISTORICAL_RUN_OBSERVATION_V2_AUDIT.json"
)

ALIAS_CANDIDATES = [
    REPO_ROOT / "public" / "data" / "edgeiq_canonical_horse_alias_v2.csv",
    REPO_ROOT / "public" / "data" / "edgeiq_canonical_horse_alias_v2_CANDIDATE.csv",
]

DETAIL_PATH = OUTPUT_DIR / "edgeiq_failure_reason_detail_v1.csv"
SUMMARY_PATH = OUTPUT_DIR / "edgeiq_failure_reason_summary_v1.csv"
SOURCE_BREAKDOWN_PATH = OUTPUT_DIR / "edgeiq_failure_source_breakdown_v1.csv"
YEAR_BREAKDOWN_PATH = OUTPUT_DIR / "edgeiq_failure_year_breakdown_v1.csv"
TRACK_BREAKDOWN_PATH = OUTPUT_DIR / "edgeiq_failure_track_breakdown_v1.csv"
SOURCE_FILE_BREAKDOWN_PATH = OUTPUT_DIR / "edgeiq_failure_source_file_breakdown_v1.csv"
RECOVERY_CANDIDATES_PATH = OUTPUT_DIR / "edgeiq_failure_recovery_candidates_v1.csv"
AUDIT_JSON_PATH = (
    OUTPUT_DIR
    / "EDGEIQ_HISTORICAL_OBSERVATION_FAILURE_CLASSIFICATION_V1.json"
)
AUDIT_MD_PATH = (
    OUTPUT_DIR
    / "EDGEIQ_HISTORICAL_OBSERVATION_FAILURE_CLASSIFICATION_V1.md"
)
CONTRACT_PATH = (
    OUTPUT_DIR
    / "edgeiq_historical_observation_failure_classification_v1_contract.json"
)

PASS_STATUS = (
    "EDGEIQ_HISTORICAL_OBSERVATION_FAILURE_CLASSIFICATION_V1_AUDIT_PASS"
)
FAIL_STATUS = (
    "EDGEIQ_HISTORICAL_OBSERVATION_FAILURE_CLASSIFICATION_V1_AUDIT_FAIL"
)

DETAIL_FIELDS = [
    "failure_classification_id",
    "source_path",
    "source_row_number",
    "source_system",
    "source_horse_id",
    "source_horse_name",
    "race_date",
    "race_year",
    "canonical_track",
    "original_rejection_reason_code",
    "governed_failure_code",
    "failure_gate",
    "recoverability",
    "recovery_requirement",
    "source_identity_registered",
    "source_identity_collision",
    "source_row_evidence_sha256",
]

RECOVERY_FIELDS = [
    "failure_classification_id",
    "source_path",
    "source_row_number",
    "source_system",
    "source_horse_id",
    "source_horse_name",
    "race_date",
    "canonical_track",
    "governed_failure_code",
    "recoverability",
    "recovery_requirement",
    "source_row_evidence_sha256",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_token(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_")


def first_value(row: Dict[str, str], names: Iterable[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def parse_year(value: str) -> str:
    text = clean(value)
    match = re.match(r"^(\d{4})[-/]", text)
    if not match:
        return ""
    year = int(match.group(1))
    if 1800 <= year <= 2100:
        return str(year)
    return ""


def valid_date(value: str) -> bool:
    text = clean(value)
    if not text:
        return False

    candidates = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]

    for fmt in candidates:
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue

    if re.match(r"^\d{4}-\d{2}-\d{2}T", text):
        try:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    return False


def infer_source_system(source_path: str, explicit: str = "") -> str:
    explicit_token = normalise_token(explicit)
    if explicit_token:
        return explicit_token

    path = clean(source_path).replace("\\", "/").lower()

    ordered_patterns = [
        ("RACING_COM", ("racing.com", "racing_com", "racingcom")),
        ("RACING_AND_SPORTS", ("racingandsports", "racing_and_sports")),
        ("RACING_AUSTRALIA", ("racingaustralia", "racing_australia")),
        ("RACENET", ("racenet",)),
        ("PUNTERS", ("punters",)),
        ("TAB", ("/tab/", "tab.com", "tab_")),
        ("SPORTSBET", ("sportsbet",)),
        ("BETFAIR", ("betfair",)),
        ("SKY_RACING", ("skyracing", "sky_racing")),
        ("RV", ("racingvictoria", "racing_victoria")),
        ("RNSW", ("racingnsw", "racing_nsw")),
        ("RQLD", ("racingqueensland", "racing_queensland")),
        ("TRSA", ("theracessa", "racing_sa")),
        ("RWWA", ("rwwa", "racingwa", "racing_wa")),
        ("TASRACING", ("tasracing",)),
        ("DARWIN_TURF_CLUB", ("darwinturfclub",)),
        ("EDGEIQ", ("edgeiq",)),
    ]

    for source_system, patterns in ordered_patterns:
        if any(pattern in path for pattern in patterns):
            return source_system

    parts = [
        normalise_token(part)
        for part in Path(path).parts
        if normalise_token(part)
    ]

    ignored = {
        "C",
        "USERS",
        "TRENT",
        "ONEDRIVE",
        "DOCUMENTS",
        "EDGEIQ_PLATFORM",
        "PUBLIC",
        "DATA",
        "DOCS",
        "OUTPUTS",
        "PERFORMANCE_INTELLIGENCE",
        "RAW",
        "CACHE",
        "CSV",
        "JSON",
    }

    for part in reversed(parts[:-1]):
        if part not in ignored and len(part) >= 3:
            return part

    return ""


def locate_alias_path() -> Path:
    for path in ALIAS_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "No canonical horse alias file found. Checked: "
        + ", ".join(str(path) for path in ALIAS_CANDIDATES)
    )


def alias_key(source_system: str, source_horse_id: str) -> Tuple[str, str]:
    return normalise_token(source_system), clean(source_horse_id)


def load_alias_index(
    path: Path,
) -> Tuple[Dict[Tuple[str, str], str], Set[Tuple[str, str]], int]:
    print(f"Loading alias index: {path}", flush=True)

    identity_to_canonical: Dict[Tuple[str, str], str] = {}
    collisions: Set[Tuple[str, str]] = set()
    row_count = 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"Alias file has no header: {path}")

        required = {
            "canonical_horse_id",
            "source_system",
            "source_horse_id",
        }
        missing = required.difference(reader.fieldnames)
        if missing:
            raise RuntimeError(
                f"Alias file missing columns {sorted(missing)}: {path}"
            )

        for row in reader:
            row_count += 1

            source_system = clean(row.get("source_system"))
            source_horse_id = clean(row.get("source_horse_id"))
            canonical_horse_id = clean(row.get("canonical_horse_id"))

            if not source_system or not source_horse_id or not canonical_horse_id:
                continue

            key = alias_key(source_system, source_horse_id)
            previous = identity_to_canonical.get(key)

            if previous and previous != canonical_horse_id:
                collisions.add(key)
            else:
                identity_to_canonical[key] = canonical_horse_id

            if row_count % 250000 == 0:
                print(
                    f"Alias rows scanned: {row_count:,} | "
                    f"indexed: {len(identity_to_canonical):,} | "
                    f"collisions: {len(collisions):,}",
                    flush=True,
                )

    print(
        f"Alias index complete: rows={row_count:,}, "
        f"identities={len(identity_to_canonical):,}, "
        f"collisions={len(collisions):,}",
        flush=True,
    )

    return identity_to_canonical, collisions, row_count


def make_classification_id(
    source_path: str,
    source_row_number: str,
    source_evidence_sha256: str,
    source_horse_id: str,
    race_date: str,
) -> str:
    payload = "\x1f".join(
        [
            clean(source_path),
            clean(source_row_number),
            clean(source_evidence_sha256),
            clean(source_horse_id),
            clean(race_date),
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"HFCV1-{digest[:24].upper()}"


def classify(
    *,
    source_path: str,
    source_system: str,
    source_horse_id: str,
    source_horse_name: str,
    race_date: str,
    canonical_track: str,
    original_reason: str,
    identity_registered: bool,
    identity_collision: bool,
) -> Tuple[str, str, str, str]:
    """
    Returns:
        governed_failure_code,
        failure_gate,
        recoverability,
        recovery_requirement
    """

    # Gate 1: source evidence and schema-level identity fields.
    if not source_horse_id:
        if source_horse_name and source_system:
            return (
                "NO_SOURCE_HORSE_ID_NAME_AVAILABLE",
                "IDENTITY_REQUIRED_FIELDS",
                "CONDITIONALLY_RECOVERABLE",
                "Obtain a deterministic source horse ID or prove a unique "
                "source-system plus normalised-name identity.",
            )

        if source_horse_name and not source_system:
            return (
                "NO_SOURCE_HORSE_ID_OR_SYSTEM_NAME_AVAILABLE",
                "IDENTITY_REQUIRED_FIELDS",
                "CONDITIONALLY_RECOVERABLE",
                "Resolve the source system and obtain a deterministic source "
                "horse ID before canonical registration.",
            )

        return (
            "NO_SOURCE_HORSE_ID",
            "IDENTITY_REQUIRED_FIELDS",
            "IRRECOVERABLE_FROM_CURRENT_EVIDENCE",
            "Required source horse identity evidence is absent.",
        )

    # Gate 2: source-system attribution.
    if not source_system:
        return (
            "NO_SOURCE_SYSTEM",
            "SOURCE_SYSTEM_RESOLUTION",
            "CONDITIONALLY_RECOVERABLE",
            "Resolve the originating source system from governed source "
            "metadata before identity lookup.",
        )

    if source_system in {"UNKNOWN", "UNCLASSIFIED", "OTHER", "NA", "N_A"}:
        return (
            "UNKNOWN_SOURCE_SYSTEM",
            "SOURCE_SYSTEM_RESOLUTION",
            "CONDITIONALLY_RECOVERABLE",
            "Map the source path to a governed source-system identifier.",
        )

    # Gate 3: canonical identity lookup.
    if identity_collision:
        return (
            "SOURCE_IDENTITY_COLLISION",
            "CANONICAL_IDENTITY_RESOLUTION",
            "MANUAL_GOVERNED_REVIEW",
            "The same source-system and source-horse-ID key maps to more than "
            "one canonical horse identity.",
        )

    if not identity_registered:
        if source_horse_name:
            return (
                "SOURCE_ID_NOT_REGISTERED_NAME_AVAILABLE",
                "CANONICAL_IDENTITY_RESOLUTION",
                "AUTOMATICALLY_RECOVERABLE",
                "Register the exact source-system and source-horse-ID alias "
                "after confirming the source identity evidence.",
            )

        return (
            "SOURCE_ID_NOT_REGISTERED",
            "CANONICAL_IDENTITY_RESOLUTION",
            "AUTOMATICALLY_RECOVERABLE",
            "Register the exact source-system and source-horse-ID alias. "
            "Do not invent a horse name.",
        )

    # A row appearing in the identity failure ledger despite a registered
    # exact identity indicates a pipeline-classifier or lookup inconsistency.
    if not race_date:
        return (
            "MISSING_RACE_DATE_AFTER_IDENTITY_MATCH",
            "RACE_IDENTITY_VALIDATION",
            "CONDITIONALLY_RECOVERABLE",
            "Recover race date from the source row or governed race metadata.",
        )

    if not valid_date(race_date):
        return (
            "INVALID_RACE_DATE_AFTER_IDENTITY_MATCH",
            "RACE_IDENTITY_VALIDATION",
            "CONDITIONALLY_RECOVERABLE",
            "Normalise the source date only when its semantics are provable.",
        )

    if not canonical_track:
        return (
            "MISSING_TRACK_AFTER_IDENTITY_MATCH",
            "RACE_IDENTITY_VALIDATION",
            "CONDITIONALLY_RECOVERABLE",
            "Recover and canonically map the race track from source evidence.",
        )

    if original_reason and normalise_token(original_reason) not in {
        "IDENTITY_FAILURE",
        "CANONICAL_IDENTITY_NOT_RESOLVED",
        "UNRESOLVED_HORSE_IDENTITY",
    }:
        return (
            f"UPSTREAM_{normalise_token(original_reason)}",
            "UPSTREAM_REJECTION_ATTRIBUTION",
            "MANUAL_GOVERNED_REVIEW",
            "Review the original upstream rejection reason against the "
            "warehouse admission contract.",
        )

    return (
        "REGISTERED_IDENTITY_LOOKUP_INCONSISTENCY",
        "CANONICAL_IDENTITY_RESOLUTION",
        "AUTOMATICALLY_RECOVERABLE",
        "Reconcile the warehouse source-system classifier and alias lookup "
        "normalisation so the registered exact identity resolves consistently.",
    )


def write_csv(path: Path, fields: List[str], rows: Iterable[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_counter_table(
    path: Path,
    dimension_name: str,
    counter: Counter,
    total: int,
) -> None:
    fields = [dimension_name, "failure_rows", "percentage_of_failures"]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
        )
        writer.writeheader()

        for key, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], str(item[0])),
        ):
            writer.writerow(
                {
                    dimension_name: key or "BLANK",
                    "failure_rows": count,
                    "percentage_of_failures": (
                        round((count / total) * 100, 6) if total else 0
                    ),
                }
            )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    started_at = utc_now_iso()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not IDENTITY_FAILURE_PATH.exists():
        raise FileNotFoundError(
            f"Identity failure ledger not found: {IDENTITY_FAILURE_PATH}"
        )

    if not WAREHOUSE_AUDIT_PATH.exists():
        raise FileNotFoundError(
            f"Warehouse audit not found: {WAREHOUSE_AUDIT_PATH}"
        )

    alias_path = locate_alias_path()
    alias_index, alias_collisions, alias_rows_scanned = load_alias_index(alias_path)

    with WAREHOUSE_AUDIT_PATH.open("r", encoding="utf-8-sig") as handle:
        warehouse_audit = json.load(handle)

    expected_failure_rows = int(
        warehouse_audit.get("identity_failure_rows", 0)
    )

    reason_counts: Counter = Counter()
    gate_counts: Counter = Counter()
    recoverability_counts: Counter = Counter()
    source_counts: Counter = Counter()
    source_file_counts: Counter = Counter()
    year_counts: Counter = Counter()
    track_counts: Counter = Counter()
    original_reason_counts: Counter = Counter()

    source_reason_counts: Counter = Counter()
    reason_recoverability: Dict[str, str] = {}
    reason_gate: Dict[str, str] = {}
    reason_requirement: Dict[str, str] = {}

    total_rows = 0
    classified_rows = 0
    recovery_candidate_rows = 0
    blank_classification_codes = 0
    duplicate_classification_ids = 0

    classification_ids: Set[str] = set()

    print(f"Reading failure ledger: {IDENTITY_FAILURE_PATH}", flush=True)

    with (
        IDENTITY_FAILURE_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as source_handle,
        DETAIL_PATH.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as detail_handle,
        RECOVERY_CANDIDATES_PATH.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as recovery_handle,
    ):
        reader = csv.DictReader(source_handle)

        if reader.fieldnames is None:
            raise RuntimeError(
                f"Failure ledger has no header: {IDENTITY_FAILURE_PATH}"
            )

        detail_writer = csv.DictWriter(
            detail_handle,
            fieldnames=DETAIL_FIELDS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        recovery_writer = csv.DictWriter(
            recovery_handle,
            fieldnames=RECOVERY_FIELDS,
            extrasaction="ignore",
            lineterminator="\n",
        )

        detail_writer.writeheader()
        recovery_writer.writeheader()

        for row in reader:
            total_rows += 1

            source_path = first_value(
                row,
                [
                    "source_path",
                    "source_file",
                    "file_path",
                    "input_path",
                ],
            )
            source_row_number = first_value(
                row,
                [
                    "source_row_number",
                    "row_number",
                    "source_record_number",
                ],
            )
            explicit_source_system = first_value(
                row,
                [
                    "source_system",
                    "source",
                    "provider",
                ],
            )
            source_system = infer_source_system(
                source_path,
                explicit_source_system,
            )
            source_horse_id = first_value(
                row,
                [
                    "source_horse_id",
                    "horse_id",
                    "runner_id",
                    "competitor_id",
                ],
            )
            source_horse_name = first_value(
                row,
                [
                    "source_horse_name",
                    "horse_name",
                    "runner_name",
                    "competitor_name",
                ],
            )
            race_date = first_value(
                row,
                [
                    "race_date",
                    "meeting_date",
                    "event_date",
                    "date",
                ],
            )
            canonical_track = first_value(
                row,
                [
                    "canonical_track",
                    "track",
                    "venue",
                    "meeting",
                ],
            )
            original_reason = first_value(
                row,
                [
                    "rejection_reason_code",
                    "failure_reason",
                    "reason_code",
                    "rejection_reason",
                ],
            )
            source_evidence_sha256 = first_value(
                row,
                [
                    "source_row_evidence_sha256",
                    "source_evidence_sha256",
                    "evidence_sha256",
                ],
            )

            identity_key = alias_key(source_system, source_horse_id)
            identity_registered = (
                bool(source_system)
                and bool(source_horse_id)
                and identity_key in alias_index
            )
            identity_collision = identity_key in alias_collisions

            (
                governed_failure_code,
                failure_gate,
                recoverability,
                recovery_requirement,
            ) = classify(
                source_path=source_path,
                source_system=source_system,
                source_horse_id=source_horse_id,
                source_horse_name=source_horse_name,
                race_date=race_date,
                canonical_track=canonical_track,
                original_reason=original_reason,
                identity_registered=identity_registered,
                identity_collision=identity_collision,
            )

            classification_id = make_classification_id(
                source_path,
                source_row_number,
                source_evidence_sha256,
                source_horse_id,
                race_date,
            )

            if classification_id in classification_ids:
                duplicate_classification_ids += 1
            else:
                classification_ids.add(classification_id)

            if governed_failure_code:
                classified_rows += 1
            else:
                blank_classification_codes += 1

            race_year = parse_year(race_date)

            detail_row = {
                "failure_classification_id": classification_id,
                "source_path": source_path,
                "source_row_number": source_row_number,
                "source_system": source_system,
                "source_horse_id": source_horse_id,
                "source_horse_name": source_horse_name,
                "race_date": race_date,
                "race_year": race_year,
                "canonical_track": canonical_track,
                "original_rejection_reason_code": original_reason,
                "governed_failure_code": governed_failure_code,
                "failure_gate": failure_gate,
                "recoverability": recoverability,
                "recovery_requirement": recovery_requirement,
                "source_identity_registered": str(identity_registered).lower(),
                "source_identity_collision": str(identity_collision).lower(),
                "source_row_evidence_sha256": source_evidence_sha256,
            }

            detail_writer.writerow(detail_row)

            reason_counts[governed_failure_code] += 1
            gate_counts[failure_gate] += 1
            recoverability_counts[recoverability] += 1
            source_counts[source_system or "UNRESOLVED_SOURCE_SYSTEM"] += 1
            source_file_counts[source_path or "MISSING_SOURCE_PATH"] += 1
            year_counts[race_year or "UNKNOWN_YEAR"] += 1
            track_counts[canonical_track or "MISSING_TRACK"] += 1
            original_reason_counts[original_reason or "BLANK"] += 1
            source_reason_counts[
                (
                    source_system or "UNRESOLVED_SOURCE_SYSTEM",
                    governed_failure_code,
                )
            ] += 1

            reason_recoverability[governed_failure_code] = recoverability
            reason_gate[governed_failure_code] = failure_gate
            reason_requirement[governed_failure_code] = recovery_requirement

            if recoverability != "IRRECOVERABLE_FROM_CURRENT_EVIDENCE":
                recovery_writer.writerow(detail_row)
                recovery_candidate_rows += 1

            if total_rows % 250000 == 0:
                print(
                    f"Failure rows classified: {total_rows:,} | "
                    f"recovery candidates: {recovery_candidate_rows:,}",
                    flush=True,
                )

    print(
        f"Failure classification complete: {total_rows:,} rows",
        flush=True,
    )

    summary_fields = [
        "governed_failure_code",
        "failure_gate",
        "recoverability",
        "failure_rows",
        "percentage_of_failures",
        "recovery_requirement",
    ]

    with SUMMARY_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=summary_fields,
            lineterminator="\n",
        )
        writer.writeheader()

        for reason, count in sorted(
            reason_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            writer.writerow(
                {
                    "governed_failure_code": reason,
                    "failure_gate": reason_gate.get(reason, ""),
                    "recoverability": reason_recoverability.get(reason, ""),
                    "failure_rows": count,
                    "percentage_of_failures": (
                        round((count / total_rows) * 100, 6)
                        if total_rows
                        else 0
                    ),
                    "recovery_requirement": reason_requirement.get(reason, ""),
                }
            )

    source_breakdown_fields = [
        "source_system",
        "governed_failure_code",
        "failure_rows",
        "percentage_of_source_failures",
        "percentage_of_all_failures",
    ]

    source_totals = Counter()
    for (source_system, _reason), count in source_reason_counts.items():
        source_totals[source_system] += count

    with SOURCE_BREAKDOWN_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=source_breakdown_fields,
            lineterminator="\n",
        )
        writer.writeheader()

        for (source_system, reason), count in sorted(
            source_reason_counts.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        ):
            source_total = source_totals[source_system]

            writer.writerow(
                {
                    "source_system": source_system,
                    "governed_failure_code": reason,
                    "failure_rows": count,
                    "percentage_of_source_failures": (
                        round((count / source_total) * 100, 6)
                        if source_total
                        else 0
                    ),
                    "percentage_of_all_failures": (
                        round((count / total_rows) * 100, 6)
                        if total_rows
                        else 0
                    ),
                }
            )

    write_counter_table(
        SOURCE_FILE_BREAKDOWN_PATH,
        "source_path",
        source_file_counts,
        total_rows,
    )
    write_counter_table(
        YEAR_BREAKDOWN_PATH,
        "race_year",
        year_counts,
        total_rows,
    )
    write_counter_table(
        TRACK_BREAKDOWN_PATH,
        "canonical_track",
        track_counts,
        total_rows,
    )

    largest_reason = reason_counts.most_common(1)
    largest_source = source_counts.most_common(1)

    recoverable_reason_counts = Counter(
        {
            reason: count
            for reason, count in reason_counts.items()
            if reason_recoverability.get(reason)
            != "IRRECOVERABLE_FROM_CURRENT_EVIDENCE"
        }
    )
    irrecoverable_reason_counts = Counter(
        {
            reason: count
            for reason, count in reason_counts.items()
            if reason_recoverability.get(reason)
            == "IRRECOVERABLE_FROM_CURRENT_EVIDENCE"
        }
    )

    largest_recoverable_reason = recoverable_reason_counts.most_common(1)
    largest_irrecoverable_reason = irrecoverable_reason_counts.most_common(1)

    automatic_rows = recoverability_counts.get(
        "AUTOMATICALLY_RECOVERABLE",
        0,
    )
    conditional_rows = recoverability_counts.get(
        "CONDITIONALLY_RECOVERABLE",
        0,
    )
    manual_review_rows = recoverability_counts.get(
        "MANUAL_GOVERNED_REVIEW",
        0,
    )
    irrecoverable_rows = recoverability_counts.get(
        "IRRECOVERABLE_FROM_CURRENT_EVIDENCE",
        0,
    )

    recoverable_rows = (
        automatic_rows
        + conditional_rows
        + manual_review_rows
    )

    checks = {
        "failure_ledger_exists": IDENTITY_FAILURE_PATH.exists(),
        "warehouse_audit_exists": WAREHOUSE_AUDIT_PATH.exists(),
        "failure_population_nonzero": total_rows > 0,
        "all_rows_classified": classified_rows == total_rows,
        "no_blank_failure_codes": blank_classification_codes == 0,
        "classification_count_matches_input": (
            classified_rows == total_rows
        ),
        "classification_count_matches_warehouse_audit": (
            expected_failure_rows == 0
            or total_rows == expected_failure_rows
        ),
        "reason_counts_reconcile": sum(reason_counts.values()) == total_rows,
        "recoverability_counts_reconcile": (
            sum(recoverability_counts.values()) == total_rows
        ),
        "source_counts_reconcile": sum(source_counts.values()) == total_rows,
        "source_file_counts_reconcile": sum(source_file_counts.values()) == total_rows,
        "year_counts_reconcile": sum(year_counts.values()) == total_rows,
        "track_counts_reconcile": sum(track_counts.values()) == total_rows,
        "every_row_has_exactly_one_failure_code": (
            sum(reason_counts.values()) == total_rows
            and blank_classification_codes == 0
        ),
        "detail_output_exists": DETAIL_PATH.exists(),
        "summary_output_exists": SUMMARY_PATH.exists(),
        "source_breakdown_output_exists": SOURCE_BREAKDOWN_PATH.exists(),
        "recovery_candidate_output_exists": RECOVERY_CANDIDATES_PATH.exists(),
    }

    status = PASS_STATUS if all(checks.values()) else FAIL_STATUS

    completed_at = utc_now_iso()

    audit = {
        "status": status,
        "generated_at_utc": completed_at,
        "started_at_utc": started_at,
        "input_failure_ledger": str(
            IDENTITY_FAILURE_PATH.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
        "input_failure_ledger_sha256": sha256_file(
            IDENTITY_FAILURE_PATH
        ),
        "warehouse_audit": str(
            WAREHOUSE_AUDIT_PATH.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
        "alias_source": str(alias_path.relative_to(REPO_ROOT)).replace(
            "\\",
            "/",
        ),
        "alias_rows_scanned": alias_rows_scanned,
        "alias_identities_indexed": len(alias_index),
        "alias_identity_collisions": len(alias_collisions),
        "warehouse_audit_identity_failure_rows": expected_failure_rows,
        "remaining_failures_analysed": total_rows,
        "classified_rows": classified_rows,
        "classification_coverage_percentage": (
            round((classified_rows / total_rows) * 100, 6)
            if total_rows
            else 0
        ),
        "reason_category_count": len(reason_counts),
        "failure_gate_count": len(gate_counts),
        "source_system_count": len(source_counts),
        "source_file_count": len(source_file_counts),
        "race_year_count": len(year_counts),
        "track_count": len(track_counts),
        "automatically_recoverable_rows": automatic_rows,
        "conditionally_recoverable_rows": conditional_rows,
        "manual_governed_review_rows": manual_review_rows,
        "recoverable_rows_total": recoverable_rows,
        "irrecoverable_rows": irrecoverable_rows,
        "recoverable_percentage": (
            round((recoverable_rows / total_rows) * 100, 6)
            if total_rows
            else 0
        ),
        "irrecoverable_percentage": (
            round((irrecoverable_rows / total_rows) * 100, 6)
            if total_rows
            else 0
        ),
        "recovery_candidate_ledger_rows": recovery_candidate_rows,
        "duplicate_classification_ids": duplicate_classification_ids,
        "blank_classification_codes": blank_classification_codes,
        "largest_failure_category": (
            {
                "governed_failure_code": largest_reason[0][0],
                "failure_rows": largest_reason[0][1],
            }
            if largest_reason
            else {}
        ),
        "largest_failure_source": (
            {
                "source_system": largest_source[0][0],
                "failure_rows": largest_source[0][1],
            }
            if largest_source
            else {}
        ),
        "largest_recoverable_category": (
            {
                "governed_failure_code": largest_recoverable_reason[0][0],
                "failure_rows": largest_recoverable_reason[0][1],
            }
            if largest_recoverable_reason
            else {}
        ),
        "largest_irrecoverable_category": (
            {
                "governed_failure_code": largest_irrecoverable_reason[0][0],
                "failure_rows": largest_irrecoverable_reason[0][1],
            }
            if largest_irrecoverable_reason
            else {}
        ),
        "failure_reason_counts": dict(
            sorted(
                reason_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "failure_gate_counts": dict(
            sorted(
                gate_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "recoverability_counts": dict(
            sorted(
                recoverability_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "checks": checks,
        "output_sha256": {
            "detail": sha256_file(DETAIL_PATH),
            "summary": sha256_file(SUMMARY_PATH),
            "source_breakdown": sha256_file(SOURCE_BREAKDOWN_PATH),
            "source_file_breakdown": sha256_file(SOURCE_FILE_BREAKDOWN_PATH),
            "year_breakdown": sha256_file(YEAR_BREAKDOWN_PATH),
            "track_breakdown": sha256_file(TRACK_BREAKDOWN_PATH),
            "recovery_candidates": sha256_file(
                RECOVERY_CANDIDATES_PATH
            ),
        },
    }

    contract = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_FAILURE_"
            "CLASSIFICATION_V1_CONTRACT"
        ),
        "version": "1.0.0",
        "purpose": (
            "Governed first-failure attribution and recoverability "
            "classification for remaining Historical Run Observation "
            "Warehouse V2 identity failures."
        ),
        "input": str(
            IDENTITY_FAILURE_PATH.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
        "classification_policy": {
            "one_row_one_governed_failure_code": True,
            "first_failure_gate_wins": True,
            "no_fuzzy_identity_matching": True,
            "no_invented_horse_names": True,
            "no_calculated_performance_values": True,
            "source_evidence_preserved": True,
        },
        "failure_gate_order": [
            "IDENTITY_REQUIRED_FIELDS",
            "SOURCE_SYSTEM_RESOLUTION",
            "CANONICAL_IDENTITY_RESOLUTION",
            "RACE_IDENTITY_VALIDATION",
            "UPSTREAM_REJECTION_ATTRIBUTION",
        ],
        "recoverability_classes": [
            "AUTOMATICALLY_RECOVERABLE",
            "CONDITIONALLY_RECOVERABLE",
            "MANUAL_GOVERNED_REVIEW",
            "IRRECOVERABLE_FROM_CURRENT_EVIDENCE",
        ],
        "outputs": [
            str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            for path in [
                DETAIL_PATH,
                SUMMARY_PATH,
                SOURCE_BREAKDOWN_PATH,
                SOURCE_FILE_BREAKDOWN_PATH,
                YEAR_BREAKDOWN_PATH,
                TRACK_BREAKDOWN_PATH,
                RECOVERY_CANDIDATES_PATH,
                AUDIT_JSON_PATH,
                AUDIT_MD_PATH,
            ]
        ],
    }

    with CONTRACT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(contract, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    audit["output_sha256"]["contract"] = sha256_file(CONTRACT_PATH)

    with AUDIT_JSON_PATH.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    top_reason_lines = []
    for reason, count in reason_counts.most_common(15):
        percentage = (
            round((count / total_rows) * 100, 4)
            if total_rows
            else 0
        )
        top_reason_lines.append(
            f"| `{reason}` | {count:,} | {percentage:.4f}% | "
            f"{reason_recoverability.get(reason, '')} |"
        )

    markdown = f"""# EDGEIQ Historical Observation Failure Classification V1

## Status

**{status}**

Generated: `{completed_at}`

## Purpose

This governed unit classifies every remaining Historical Run Observation
Warehouse V2 identity failure using one first-failure code per source row.

It does not perform fuzzy identity matching, invent horse names, calculate
performance values, or alter the production warehouse.

## Population

| Metric | Result |
|---|---:|
| Remaining failures analysed | {total_rows:,} |
| Rows classified | {classified_rows:,} |
| Classification coverage | {audit["classification_coverage_percentage"]:.6f}% |
| Governed reason categories | {len(reason_counts):,} |
| Source systems represented | {len(source_counts):,} |
| Recovery candidate rows | {recovery_candidate_rows:,} |

## Recoverability

| Classification | Rows |
|---|---:|
| Automatically recoverable | {automatic_rows:,} |
| Conditionally recoverable | {conditional_rows:,} |
| Manual governed review | {manual_review_rows:,} |
| Total recoverable/review candidates | {recoverable_rows:,} |
| Irrecoverable from current evidence | {irrecoverable_rows:,} |
| Recoverable percentage | {audit["recoverable_percentage"]:.6f}% |

## Largest Categories

- Largest failure category: `{audit["largest_failure_category"].get("governed_failure_code", "")}` — {audit["largest_failure_category"].get("failure_rows", 0):,}
- Largest failure source: `{audit["largest_failure_source"].get("source_system", "")}` — {audit["largest_failure_source"].get("failure_rows", 0):,}
- Largest recoverable category: `{audit["largest_recoverable_category"].get("governed_failure_code", "")}` — {audit["largest_recoverable_category"].get("failure_rows", 0):,}
- Largest irrecoverable category: `{audit["largest_irrecoverable_category"].get("governed_failure_code", "")}` — {audit["largest_irrecoverable_category"].get("failure_rows", 0):,}

## Top Failure Reasons

| Governed failure code | Rows | Percentage | Recoverability |
|---|---:|---:|---|
{chr(10).join(top_reason_lines)}

## Governance Checks

| Check | Result |
|---|---|
{chr(10).join(f"| `{name}` | {'PASS' if value else 'FAIL'} |" for name, value in checks.items())}

## Outputs

- `{DETAIL_PATH.relative_to(REPO_ROOT)}`
- `{SUMMARY_PATH.relative_to(REPO_ROOT)}`
- `{SOURCE_BREAKDOWN_PATH.relative_to(REPO_ROOT)}`
- `{SOURCE_FILE_BREAKDOWN_PATH.relative_to(REPO_ROOT)}`
- `{YEAR_BREAKDOWN_PATH.relative_to(REPO_ROOT)}`
- `{TRACK_BREAKDOWN_PATH.relative_to(REPO_ROOT)}`
- `{RECOVERY_CANDIDATES_PATH.relative_to(REPO_ROOT)}`
- `{AUDIT_JSON_PATH.relative_to(REPO_ROOT)}`
- `{CONTRACT_PATH.relative_to(REPO_ROOT)}`

## Interpretation Rule

A recoverable classification identifies a technically plausible next governed
unit. It does not authorise automatic mutation of canonical identities without
the evidence and validation required by that recovery class.
"""

    with AUDIT_MD_PATH.open("w", encoding="utf-8", newline="") as handle:
        handle.write(markdown)

    print(json.dumps(audit, indent=2), flush=True)

    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"EDGEIQ HISTORICAL FAILURE CLASSIFICATION ERROR: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
