from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

HORSES_MASTER = (
    ROOT
    / "public"
    / "data"
    / "horses_master.csv"
)

HISTORICAL_RESULTS = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_4_1"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_4_1"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_4_1"
)

AUDIT_VERSION = (
    "DURABLE_HORSE_IDENTITY_"
    "SOURCE_VALIDATION_V0_1"
)

PROGRESS_INTERVAL = 100_000
SAMPLE_LIMIT = 250

COUNTRY_SUFFIX_PATTERN = re.compile(
    r"\s*(?:\((?:AUS|NZ|IRE|GB|USA|FR|JPN|SAF|ARG|BRZ|GER|CAN|CHI|URU|ITY|SWE|DEN|SIN|HK)\)\s*)+$",
    re.IGNORECASE,
)


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


def normalise_horse_name(
    value: Any,
) -> str:
    text = normalise_text(value)

    text = COUNTRY_SUFFIX_PATTERN.sub(
        "",
        text,
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
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
        "%d/%m/%y",
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

    return (
        match.group(1)
        if match
        else ""
    )


def sha256_file(
    path: Path,
) -> str:
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
    fields = list(
        fieldnames or []
    )

    if not fields:
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)

    if not fields:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

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


def detect_columns(
    columns: list[str],
) -> dict[str, str]:
    lower_map = {
        column.lower(): column
        for column in columns
    }

    candidates = {
        "horse_code": (
            "horse_code",
            "horsecode",
            "registration_id",
        ),
        "horse_name": (
            "horse_name",
            "horse",
            "name",
        ),
        "dob": (
            "dob",
            "date_of_birth",
            "foaling_date",
        ),
        "sire": (
            "sire",
            "sire_name",
        ),
        "dam": (
            "dam",
            "dam_name",
        ),
        "sex": (
            "sex",
            "horse_sex",
            "gender",
        ),
        "country": (
            "country",
            "country_code",
            "country_suffix",
        ),
    }

    detected: dict[str, str] = {}

    for semantic, options in (
        candidates.items()
    ):
        detected[semantic] = ""

        for option in options:
            if option in lower_map:
                detected[
                    semantic
                ] = lower_map[
                    option
                ]
                break

    return detected


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not HORSES_MASTER.exists():
        raise FileNotFoundError(
            HORSES_MASTER
        )

    if not HISTORICAL_RESULTS.exists():
        raise FileNotFoundError(
            HISTORICAL_RESULTS
        )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    source_profile_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_horses_master_"
            f"profile_v0_1_{run_id}.csv"
        )
    )

    code_conflicts_path = (
        AUDIT_DIR
        / (
            "edgeiq_horse_code_"
            f"conflicts_v0_1_{run_id}.csv"
        )
    )

    name_conflicts_path = (
        AUDIT_DIR
        / (
            "edgeiq_horse_name_"
            f"ambiguity_v0_1_{run_id}.csv"
        )
    )

    result_linkage_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_horse_code_"
            f"result_linkage_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_1_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_1_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_4_1_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_4_1_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_DURABLE_HORSE_"
            "IDENTITY_SOURCE_VALIDATION_V0_1.md"
        )
    )

    code_records: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    name_to_codes: dict[
        str,
        set[str],
    ] = defaultdict(set)

    source_rows = 0
    blank_code_rows = 0
    blank_name_rows = 0
    invalid_dob_rows = 0
    complete_core_rows = 0

    with HORSES_MASTER.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        columns = list(
            reader.fieldnames or []
        )

        detected = detect_columns(
            columns
        )

        required = (
            "horse_code",
            "horse_name",
            "dob",
            "sire",
            "dam",
        )

        missing_required = [
            semantic
            for semantic in required
            if not detected.get(
                semantic
            )
        ]

        if missing_required:
            raise RuntimeError(
                "horses_master.csv is missing "
                "required semantics: "
                + " | ".join(
                    missing_required
                )
            )

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            source_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "HORSES_MASTER_PROFILE_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            horse_code = clean(
                row.get(
                    detected[
                        "horse_code"
                    ]
                )
            )

            horse_name = clean(
                row.get(
                    detected[
                        "horse_name"
                    ]
                )
            )

            normalised_name = (
                normalise_horse_name(
                    horse_name
                )
            )

            raw_dob = clean(
                row.get(
                    detected["dob"]
                )
            )

            dob = normalise_date(
                raw_dob
            )

            sire = clean(
                row.get(
                    detected["sire"]
                )
            )

            dam = clean(
                row.get(
                    detected["dam"]
                )
            )

            sex = (
                clean(
                    row.get(
                        detected["sex"]
                    )
                )
                if detected.get(
                    "sex"
                )
                else ""
            )

            country = (
                clean(
                    row.get(
                        detected["country"]
                    )
                )
                if detected.get(
                    "country"
                )
                else ""
            )

            if not horse_code:
                blank_code_rows += 1

            if not normalised_name:
                blank_name_rows += 1

            if raw_dob and not dob:
                invalid_dob_rows += 1

            if all(
                (
                    horse_code,
                    normalised_name,
                    dob,
                    sire,
                    dam,
                )
            ):
                complete_core_rows += 1

            profile_record = {
                "horse_code": (
                    horse_code
                ),
                "horse_name": (
                    horse_name
                ),
                "normalised_horse_name": (
                    normalised_name
                ),
                "dob": dob,
                "raw_dob": raw_dob,
                "sire": sire,
                "normalised_sire": (
                    normalise_horse_name(
                        sire
                    )
                ),
                "dam": dam,
                "normalised_dam": (
                    normalise_horse_name(
                        dam
                    )
                ),
                "sex": sex,
                "country": country,
                "source_row_number": (
                    row_number + 1
                ),
            }

            if horse_code:
                code_records[
                    horse_code
                ].append(
                    profile_record
                )

            if (
                normalised_name
                and horse_code
            ):
                name_to_codes[
                    normalised_name
                ].add(
                    horse_code
                )

    code_profile_rows: list[
        dict[str, Any]
    ] = []

    code_conflict_rows: list[
        dict[str, Any]
    ] = []

    exact_duplicate_code_groups = 0
    conflicting_code_groups = 0
    unique_code_groups = 0

    for horse_code, records in sorted(
        code_records.items()
    ):
        identity_signatures = {
            (
                record[
                    "normalised_horse_name"
                ],
                record["dob"],
                record[
                    "normalised_sire"
                ],
                record[
                    "normalised_dam"
                ],
                normalise_text(
                    record["sex"]
                ),
                normalise_text(
                    record["country"]
                ),
            )
            for record in records
        }

        if len(records) == 1:
            classification = (
                "UNIQUE_HORSE_CODE"
            )
            unique_code_groups += 1

        elif len(
            identity_signatures
        ) == 1:
            classification = (
                "EXACT_DUPLICATE_"
                "REGISTRATION_EVIDENCE"
            )
            exact_duplicate_code_groups += 1

        else:
            classification = (
                "HORSE_CODE_IDENTITY_"
                "CONFLICT"
            )
            conflicting_code_groups += 1

        profile = {
            "horse_code": horse_code,
            "source_row_count": (
                len(records)
            ),
            "distinct_identity_signature_count": (
                len(
                    identity_signatures
                )
            ),
            "horse_names": (
                " | ".join(
                    sorted({
                        record[
                            "horse_name"
                        ]
                        for record in records
                    })
                )
            ),
            "normalised_horse_names": (
                " | ".join(
                    sorted({
                        record[
                            "normalised_horse_name"
                        ]
                        for record in records
                    })
                )
            ),
            "dobs": (
                " | ".join(
                    sorted({
                        record["dob"]
                        for record in records
                        if record["dob"]
                    })
                )
            ),
            "sires": (
                " | ".join(
                    sorted({
                        record["sire"]
                        for record in records
                        if record["sire"]
                    })
                )
            ),
            "dams": (
                " | ".join(
                    sorted({
                        record["dam"]
                        for record in records
                        if record["dam"]
                    })
                )
            ),
            "sexes": (
                " | ".join(
                    sorted({
                        record["sex"]
                        for record in records
                        if record["sex"]
                    })
                )
            ),
            "countries": (
                " | ".join(
                    sorted({
                        record["country"]
                        for record in records
                        if record["country"]
                    })
                )
            ),
            "source_rows": (
                " | ".join(
                    str(
                        record[
                            "source_row_number"
                        ]
                    )
                    for record in records
                )
            ),
            "classification": (
                classification
            ),
            "canonical_horse_id": "",
            "automatic_promotion_allowed": (
                False
            ),
        }

        code_profile_rows.append(
            profile
        )

        if classification == (
            "HORSE_CODE_IDENTITY_CONFLICT"
        ):
            code_conflict_rows.append(
                profile
            )

    write_csv(
        source_profile_path,
        code_profile_rows,
    )

    write_csv(
        code_conflicts_path,
        code_conflict_rows,
    )

    name_ambiguity_rows: list[
        dict[str, Any]
    ] = []

    ambiguous_name_count = 0

    for normalised_name, codes in sorted(
        name_to_codes.items()
    ):
        if len(codes) <= 1:
            continue

        ambiguous_name_count += 1

        name_ambiguity_rows.append(
            {
                "normalised_horse_name": (
                    normalised_name
                ),
                "horse_code_count": (
                    len(codes)
                ),
                "horse_codes": (
                    " | ".join(
                        sorted(codes)
                    )
                ),
                "classification": (
                    "NAME_SHARED_BY_MULTIPLE_"
                    "REGISTRATION_CODES"
                ),
                "automatic_merge_allowed": (
                    False
                ),
            }
        )

    write_csv(
        name_conflicts_path,
        name_ambiguity_rows,
    )

    valid_codes = {
        row["horse_code"]
        for row in code_profile_rows
        if row["classification"]
        in {
            "UNIQUE_HORSE_CODE",
            "EXACT_DUPLICATE_"
            "REGISTRATION_EVIDENCE",
        }
    }

    result_rows = 0
    result_rows_with_code = 0
    result_rows_without_code = 0
    matched_result_rows = 0
    unmatched_result_rows = 0

    result_code_counts = Counter()
    unmatched_code_counts = Counter()

    linkage_fields = [
        "horse_code",
        "result_performance_rows",
        "master_identity_present",
        "identity_classification",
        "linkage_state",
    ]

    with HISTORICAL_RESULTS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        columns = list(
            reader.fieldnames or []
        )

        lower_map = {
            column.lower(): column
            for column in columns
        }

        result_horse_code_field = (
            lower_map.get(
                "horse_code",
                "",
            )
        )

        if not result_horse_code_field:
            raise RuntimeError(
                "Historical results do not "
                "contain horse_code."
            )

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            result_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "RESULT_HORSE_CODE_LINK_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            horse_code = clean(
                row.get(
                    result_horse_code_field
                )
            )

            if not horse_code:
                result_rows_without_code += 1
                continue

            result_rows_with_code += 1
            result_code_counts[
                horse_code
            ] += 1

            if horse_code in valid_codes:
                matched_result_rows += 1
            else:
                unmatched_result_rows += 1
                unmatched_code_counts[
                    horse_code
                ] += 1

    linkage_rows: list[
        dict[str, Any]
    ] = []

    classification_by_code = {
        row["horse_code"]: row[
            "classification"
        ]
        for row in code_profile_rows
    }

    for horse_code, count in sorted(
        result_code_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        identity_classification = (
            classification_by_code.get(
                horse_code,
                "NOT_PRESENT_IN_HORSES_MASTER",
            )
        )

        master_present = (
            horse_code
            in classification_by_code
        )

        linkage_state = (
            "LINKED_TO_VALIDATED_"
            "REGISTRATION_EVIDENCE"
            if horse_code in valid_codes
            else
            "BLOCKED_MASTER_CONFLICT"
            if identity_classification
            == "HORSE_CODE_IDENTITY_CONFLICT"
            else
            "HORSE_CODE_NOT_PRESENT_"
            "IN_MASTER"
        )

        linkage_rows.append(
            {
                "horse_code": (
                    horse_code
                ),
                "result_performance_rows": (
                    count
                ),
                "master_identity_present": (
                    master_present
                ),
                "identity_classification": (
                    identity_classification
                ),
                "linkage_state": (
                    linkage_state
                ),
            }
        )

    write_csv(
        result_linkage_path,
        linkage_rows,
        linkage_fields,
    )

    master_code_count = len(
        code_profile_rows
    )

    valid_master_codes = len(
        valid_codes
    )

    master_conflict_codes = len(
        code_conflict_rows
    )

    result_distinct_codes = len(
        result_code_counts
    )

    matched_result_codes = sum(
        1
        for code in result_code_counts
        if code in valid_codes
    )

    unmatched_result_codes = (
        result_distinct_codes
        - matched_result_codes
    )

    performance_coverage_pct = (
        round(
            matched_result_rows
            / result_rows
            * 100,
            6,
        )
        if result_rows
        else 0.0
    )

    coded_performance_coverage_pct = (
        round(
            matched_result_rows
            / result_rows_with_code
            * 100,
            6,
        )
        if result_rows_with_code
        else 0.0
    )

    checks = [
        {
            "check": (
                "HORSES_MASTER_REQUIRED_SCHEMA"
            ),
            "passed": True,
            "observed": (
                "horse_code|horse_name|"
                "dob|sire|dam"
            ),
        },
        {
            "check": (
                "HORSE_CODE_NOT_BLANK"
            ),
            "passed": (
                blank_code_rows == 0
            ),
            "observed": (
                blank_code_rows
            ),
        },
        {
            "check": (
                "HORSE_NAME_NOT_BLANK"
            ),
            "passed": (
                blank_name_rows == 0
            ),
            "observed": (
                blank_name_rows
            ),
        },
        {
            "check": (
                "DOB_PARSE_VALID"
            ),
            "passed": (
                invalid_dob_rows == 0
            ),
            "observed": (
                invalid_dob_rows
            ),
        },
        {
            "check": (
                "HORSE_CODE_CONFLICTS"
            ),
            "passed": (
                conflicting_code_groups == 0
            ),
            "observed": (
                conflicting_code_groups
            ),
        },
        {
            "check": (
                "CANONICAL_HORSE_NOT_"
                "YET_MATERIALISED"
            ),
            "passed": all(
                not row[
                    "canonical_horse_id"
                ]
                for row
                in code_profile_rows
            ),
            "observed": (
                "ALL_CANONICAL_HORSE_IDS_BLANK"
            ),
        },
        {
            "check": (
                "AUTOMATIC_PROMOTION_DISABLED"
            ),
            "passed": all(
                not row[
                    "automatic_promotion_allowed"
                ]
                for row
                in code_profile_rows
            ),
            "observed": (
                "NO_AUTOMATIC_PROMOTION"
            ),
        },
    ]

    failed_checks = [
        check["check"]
        for check in checks
        if not check["passed"]
    ]

    if (
        conflicting_code_groups == 0
        and blank_code_rows == 0
        and invalid_dob_rows == 0
    ):
        identity_decision = (
            "HORSE_CODE_VALIDATED_AS_"
            "DURABLE_REGISTRATION_"
            "IDENTITY_CANDIDATE"
        )

        canonical_horse_status = (
            "ELIGIBLE_FOR_GOVERNED_"
            "CANONICAL_MATERIALISATION_"
            "PROTOTYPE"
        )

        next_stage = (
            "Phase 1.4.2 build canonical horse "
            "dimension prototype for validated "
            "horse codes and preserve unresolved "
            "coverage separately."
        )

    else:
        identity_decision = (
            "DURABLE_HORSE_IDENTITY_"
            "SOURCE_REQUIRES_CONFLICT_"
            "RESOLUTION"
        )

        canonical_horse_status = (
            "BLOCKED"
        )

        next_stage = (
            "Resolve horse-code identity "
            "conflicts before canonical horse "
            "materialisation."
        )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.4.1 Durable Horse Identity "
            "Source Validation"
        ),
        "generated_utc": utc_now(),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": (
            "DURABLE_HORSE_IDENTITY_"
            "SOURCE_VALIDATION_PASS"
            if not failed_checks
            else
            "DURABLE_HORSE_IDENTITY_"
            "SOURCE_VALIDATION_PASS_"
            "WITH_BLOCKERS"
        ),
        "production_data_modified": False,
        "canonical_horse_ids_generated": 0,
        "source": (
            "public/data/horses_master.csv"
        ),
        "source_sha256": (
            sha256_file(
                HORSES_MASTER
            )
        ),
        "source_rows": (
            source_rows
        ),
        "complete_core_identity_rows": (
            complete_core_rows
        ),
        "blank_code_rows": (
            blank_code_rows
        ),
        "blank_name_rows": (
            blank_name_rows
        ),
        "invalid_dob_rows": (
            invalid_dob_rows
        ),
        "master_horse_codes": (
            master_code_count
        ),
        "valid_master_horse_codes": (
            valid_master_codes
        ),
        "unique_code_groups": (
            unique_code_groups
        ),
        "exact_duplicate_code_groups": (
            exact_duplicate_code_groups
        ),
        "conflicting_code_groups": (
            conflicting_code_groups
        ),
        "ambiguous_normalised_names": (
            ambiguous_name_count
        ),
        "historical_result_rows": (
            result_rows
        ),
        "historical_rows_with_horse_code": (
            result_rows_with_code
        ),
        "historical_rows_without_horse_code": (
            result_rows_without_code
        ),
        "historical_distinct_horse_codes": (
            result_distinct_codes
        ),
        "historical_matched_horse_codes": (
            matched_result_codes
        ),
        "historical_unmatched_horse_codes": (
            unmatched_result_codes
        ),
        "historical_matched_rows": (
            matched_result_rows
        ),
        "historical_unmatched_rows": (
            unmatched_result_rows
        ),
        "performance_coverage_pct": (
            performance_coverage_pct
        ),
        "coded_performance_coverage_pct": (
            coded_performance_coverage_pct
        ),
        "checks": checks,
        "failed_checks": (
            failed_checks
        ),
        "identity_decision": (
            identity_decision
        ),
        "canonical_horse_status": (
            canonical_horse_status
        ),
        "next_stage": (
            next_stage
        ),
        "outputs": {
            "master_profile": str(
                source_profile_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "code_conflicts": str(
                code_conflicts_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "name_ambiguity": str(
                name_conflicts_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "result_linkage": str(
                result_linkage_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
    }

    write_csv(
        checks_path,
        checks,
    )

    write_json(
        summary_path,
        summary,
    )

    write_json(
        latest_path,
        summary,
    )

    architecture_path.write_text(
        """# EDGEiQ Durable Horse Identity Source Validation V0.1

## Candidate source

`public/data/horses_master.csv`

## Required durable evidence

A valid registration identity record contains:

- horse code
- horse name
- date of birth
- sire
- dam

Sex and country are retained where available.

## Validation rules

A horse code may be promoted only when:

1. The horse code is non-empty.
2. All rows for the horse code describe the same identity.
3. Horse name, DOB, sire and dam do not conflict.
4. Duplicate source rows are exact identity duplicates only.
5. The source row remains preserved.
6. Historical result linkage is deterministic by horse code.

## Name rule

Horse names are descriptive attributes, not primary identities.

One normalised horse name may legitimately map to multiple horse codes.

No name-only merge is permitted.

## Current phase boundary

Phase 1.4.1 validates the source.

It does not create canonical horse IDs.

Canonical horse materialisation requires a separate audited phase.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.4.1 Durable Horse Identity Source Validation

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['status']}**

- Horses-master rows: **{source_rows:,}**
- Distinct horse codes: **{master_code_count:,}**
- Valid horse codes: **{valid_master_codes:,}**
- Horse-code conflicts: **{conflicting_code_groups:,}**
- Exact duplicate code groups: **{exact_duplicate_code_groups:,}**
- Ambiguous normalised names: **{ambiguous_name_count:,}**
- Historical performance rows: **{result_rows:,}**
- Historical rows linked to validated horse codes: **{matched_result_rows:,}**
- Overall historical coverage: **{performance_coverage_pct}%**
- Coverage among coded rows: **{coded_performance_coverage_pct}%**
- Canonical horse IDs created: **0**

Decision: **{identity_decision}**

Production data was not modified.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_4_1_DURABLE_HORSE_IDENTITY_"
        "SOURCE_VALIDATION_PASS",
        flush=True,
    )

    print(
        f"HORSES_MASTER_ROWS="
        f"{source_rows}",
        flush=True,
    )

    print(
        f"MASTER_HORSE_CODES="
        f"{master_code_count}",
        flush=True,
    )

    print(
        f"VALID_MASTER_HORSE_CODES="
        f"{valid_master_codes}",
        flush=True,
    )

    print(
        f"HORSE_CODE_CONFLICTS="
        f"{conflicting_code_groups}",
        flush=True,
    )

    print(
        f"HISTORICAL_MATCHED_ROWS="
        f"{matched_result_rows}",
        flush=True,
    )

    print(
        f"HISTORICAL_COVERAGE_PCT="
        f"{performance_coverage_pct}",
        flush=True,
    )

    print(
        f"MASTER_PROFILE="
        f"{source_profile_path}",
        flush=True,
    )

    print(
        f"CODE_CONFLICTS="
        f"{code_conflicts_path}",
        flush=True,
    )

    print(
        f"NAME_AMBIGUITY="
        f"{name_conflicts_path}",
        flush=True,
    )

    print(
        f"RESULT_LINKAGE="
        f"{result_linkage_path}",
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
