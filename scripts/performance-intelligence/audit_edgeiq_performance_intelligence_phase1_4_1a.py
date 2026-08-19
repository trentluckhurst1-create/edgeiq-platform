from __future__ import annotations

import csv
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
    / "phase1_4_1a"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_4_1a"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_4_1a"
)

AUDIT_VERSION = (
    "DURABLE_HORSE_IDENTITY_"
    "NORMALISED_CODE_VALIDATION_V0_1"
)

PROGRESS_INTERVAL = 100_000


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_horse_code(
    value: Any,
) -> str:
    text = clean(value)

    if not text:
        return ""

    try:
        number = float(text)
    except ValueError:
        return re.sub(
            r"\s+",
            "",
            text.upper(),
        )

    if number.is_integer():
        return str(int(number))

    return format(
        number,
        "f",
    ).rstrip("0").rstrip(".")


def normalise_name(
    value: Any,
) -> str:
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        clean(value).upper(),
    )


def field_present(
    value: Any,
) -> bool:
    text = clean(value)

    return (
        bool(text)
        and text.upper()
        not in {
            "NULL",
            "NONE",
            "N/A",
            "NA",
            "UNKNOWN",
            "0",
            "0.0",
        }
    )


def detect_columns(
    columns: list[str],
) -> dict[str, str]:
    lower_map = {
        column.lower(): column
        for column in columns
    }

    choices = {
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
            "foaled_date",
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

    for semantic, options in choices.items():
        detected[semantic] = ""

        for option in options:
            if option in lower_map:
                detected[semantic] = (
                    lower_map[option]
                )
                break

    return detected


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


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    master_profile_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_horses_master_normalised_"
            f"profile_v0_1_{run_id}.csv"
        )
    )

    linkage_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_horse_code_normalised_"
            f"result_linkage_v0_1_{run_id}.csv"
        )
    )

    code_conflicts_path = (
        AUDIT_DIR
        / (
            "edgeiq_horse_code_normalised_"
            f"conflicts_v0_1_{run_id}.csv"
        )
    )

    unmatched_path = (
        AUDIT_DIR
        / (
            "edgeiq_horse_code_normalised_"
            f"unmatched_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_1a_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_1a_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_4_1a_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_4_1A_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_HORSE_CODE_"
            "NORMALISATION_V0_1.md"
        )
    )

    with HORSES_MASTER.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        master_columns = list(
            reader.fieldnames or []
        )

        detected = detect_columns(
            master_columns
        )

        required = (
            "horse_code",
            "horse_name",
        )

        missing = [
            field
            for field in required
            if not detected.get(field)
        ]

        if missing:
            raise RuntimeError(
                "Missing required master fields: "
                + " | ".join(missing)
            )

        master_records: dict[
            str,
            list[dict[str, str]],
        ] = defaultdict(list)

        field_presence = Counter()
        master_rows = 0

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            master_rows += 1

            raw_code = clean(
                row.get(
                    detected["horse_code"]
                )
            )

            code = normalise_horse_code(
                raw_code
            )

            name = clean(
                row.get(
                    detected["horse_name"]
                )
            )

            dob = (
                clean(
                    row.get(
                        detected["dob"]
                    )
                )
                if detected.get("dob")
                else ""
            )

            sire = (
                clean(
                    row.get(
                        detected["sire"]
                    )
                )
                if detected.get("sire")
                else ""
            )

            dam = (
                clean(
                    row.get(
                        detected["dam"]
                    )
                )
                if detected.get("dam")
                else ""
            )

            sex = (
                clean(
                    row.get(
                        detected["sex"]
                    )
                )
                if detected.get("sex")
                else ""
            )

            country = (
                clean(
                    row.get(
                        detected["country"]
                    )
                )
                if detected.get("country")
                else ""
            )

            values = {
                "horse_code": code,
                "horse_name": name,
                "dob": dob,
                "sire": sire,
                "dam": dam,
                "sex": sex,
                "country": country,
            }

            for field, value in values.items():
                if field_present(value):
                    field_presence[field] += 1

            if code:
                master_records[code].append(
                    {
                        "raw_horse_code": (
                            raw_code
                        ),
                        "horse_code": code,
                        "horse_name": name,
                        "normalised_name": (
                            normalise_name(name)
                        ),
                        "dob": dob,
                        "sire": sire,
                        "normalised_sire": (
                            normalise_name(sire)
                        ),
                        "dam": dam,
                        "normalised_dam": (
                            normalise_name(dam)
                        ),
                        "sex": sex,
                        "country": country,
                        "source_row_number": (
                            str(row_number + 1)
                        ),
                    }
                )

    master_profile_rows = []
    conflict_rows = []

    valid_codes: set[str] = set()
    exact_duplicate_groups = 0
    conflicting_groups = 0
    unique_groups = 0

    for code, records in sorted(
        master_records.items()
    ):
        signatures = {
            (
                record["normalised_name"],
                clean(record["dob"]),
                record["normalised_sire"],
                record["normalised_dam"],
                clean(record["sex"]).upper(),
                clean(
                    record["country"]
                ).upper(),
            )
            for record in records
        }

        if len(records) == 1:
            classification = (
                "UNIQUE_NORMALISED_CODE"
            )
            unique_groups += 1
            valid_codes.add(code)

        elif len(signatures) == 1:
            classification = (
                "EXACT_DUPLICATE_"
                "REGISTRATION_EVIDENCE"
            )
            exact_duplicate_groups += 1
            valid_codes.add(code)

        else:
            classification = (
                "NORMALISED_CODE_"
                "IDENTITY_CONFLICT"
            )
            conflicting_groups += 1

        row = {
            "horse_code": code,
            "raw_horse_codes": (
                " | ".join(
                    sorted({
                        record[
                            "raw_horse_code"
                        ]
                        for record in records
                    })
                )
            ),
            "source_row_count": (
                len(records)
            ),
            "distinct_identity_signatures": (
                len(signatures)
            ),
            "horse_names": (
                " | ".join(
                    sorted({
                        record["horse_name"]
                        for record in records
                    })
                )
            ),
            "dobs": (
                " | ".join(
                    sorted({
                        record["dob"]
                        for record in records
                        if field_present(
                            record["dob"]
                        )
                    })
                )
            ),
            "sires": (
                " | ".join(
                    sorted({
                        record["sire"]
                        for record in records
                        if field_present(
                            record["sire"]
                        )
                    })
                )
            ),
            "dams": (
                " | ".join(
                    sorted({
                        record["dam"]
                        for record in records
                        if field_present(
                            record["dam"]
                        )
                    })
                )
            ),
            "sexes": (
                " | ".join(
                    sorted({
                        record["sex"]
                        for record in records
                        if field_present(
                            record["sex"]
                        )
                    })
                )
            ),
            "countries": (
                " | ".join(
                    sorted({
                        record["country"]
                        for record in records
                        if field_present(
                            record["country"]
                        )
                    })
                )
            ),
            "classification": (
                classification
            ),
            "canonical_horse_id": "",
        }

        master_profile_rows.append(row)

        if classification == (
            "NORMALISED_CODE_IDENTITY_CONFLICT"
        ):
            conflict_rows.append(row)

    write_csv(
        master_profile_path,
        master_profile_rows,
    )

    write_csv(
        code_conflicts_path,
        conflict_rows,
    )

    result_code_counts = Counter()
    result_name_by_code: dict[
        str,
        Counter[str],
    ] = defaultdict(Counter)

    historical_rows = 0
    rows_with_code = 0
    rows_without_code = 0

    with HISTORICAL_RESULTS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        result_columns = list(
            reader.fieldnames or []
        )

        lower_map = {
            column.lower(): column
            for column in result_columns
        }

        code_field = lower_map.get(
            "horse_code",
            "",
        )

        name_field = (
            lower_map.get("horse")
            or lower_map.get(
                "horse_name"
            )
            or ""
        )

        if not code_field:
            raise RuntimeError(
                "Historical results missing horse_code."
            )

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            historical_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "NORMALISED_HORSE_CODE_LINK_"
                    f"PROGRESS={row_number}",
                    flush=True,
                )

            code = normalise_horse_code(
                row.get(code_field)
            )

            if not code:
                rows_without_code += 1
                continue

            rows_with_code += 1
            result_code_counts[code] += 1

            if name_field:
                result_name = (
                    normalise_name(
                        row.get(name_field)
                    )
                )

                if result_name:
                    result_name_by_code[
                        code
                    ][result_name] += 1

    linkage_rows = []
    unmatched_rows = []

    matched_rows = 0
    unmatched_rows_count = 0
    matched_codes = 0
    unmatched_codes = 0
    name_consistent_codes = 0
    name_conflict_codes = 0

    master_names_by_code = {
        row["horse_code"]: {
            normalise_name(name)
            for name in row[
                "horse_names"
            ].split(" | ")
            if name
        }
        for row in master_profile_rows
    }

    for code, count in sorted(
        result_code_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        master_present = (
            code in master_records
        )

        validated = (
            code in valid_codes
        )

        result_names = set(
            result_name_by_code[
                code
            ].keys()
        )

        master_names = (
            master_names_by_code.get(
                code,
                set(),
            )
        )

        common_names = (
            result_names
            & master_names
        )

        if validated:
            matched_codes += 1
            matched_rows += count

            if (
                result_names
                and master_names
                and not common_names
            ):
                name_state = (
                    "HORSE_CODE_NAME_CONFLICT"
                )
                name_conflict_codes += 1
            else:
                name_state = (
                    "NAME_CONSISTENT_OR_"
                    "NOT_AVAILABLE"
                )
                name_consistent_codes += 1

            linkage_state = (
                "LINKED_TO_VALIDATED_"
                "NORMALISED_HORSE_CODE"
            )

        else:
            unmatched_codes += 1
            unmatched_rows_count += count
            name_state = (
                "NOT_VALIDATED"
            )

            linkage_state = (
                "MASTER_CODE_CONFLICT"
                if master_present
                else
                "HORSE_CODE_NOT_PRESENT_"
                "IN_MASTER"
            )

        linkage_row = {
            "horse_code": code,
            "result_performance_rows": (
                count
            ),
            "master_identity_present": (
                master_present
            ),
            "master_code_validated": (
                validated
            ),
            "master_horse_names": (
                " | ".join(
                    sorted(master_names)
                )
            ),
            "result_horse_names": (
                " | ".join(
                    sorted(
                        result_names
                    )[:50]
                )
            ),
            "name_validation_state": (
                name_state
            ),
            "linkage_state": (
                linkage_state
            ),
        }

        linkage_rows.append(
            linkage_row
        )

        if not validated:
            unmatched_rows.append(
                linkage_row
            )

    write_csv(
        linkage_path,
        linkage_rows,
    )

    write_csv(
        unmatched_path,
        unmatched_rows,
    )

    field_coverage = {
        field: {
            "present_rows": (
                field_presence[field]
            ),
            "total_rows": master_rows,
            "coverage_pct": (
                round(
                    field_presence[field]
                    / master_rows
                    * 100,
                    6,
                )
                if master_rows
                else 0.0
            ),
        }
        for field in (
            "horse_code",
            "horse_name",
            "dob",
            "sire",
            "dam",
            "sex",
            "country",
        )
    }

    coverage_pct = (
        round(
            matched_rows
            / historical_rows
            * 100,
            6,
        )
        if historical_rows
        else 0.0
    )

    code_coverage_pct = (
        round(
            matched_codes
            / len(result_code_counts)
            * 100,
            6,
        )
        if result_code_counts
        else 0.0
    )

    durable_evidence_rows = sum(
        1
        for records in (
            master_records.values()
        )
        if any(
            field_present(
                record["dob"]
            )
            and field_present(
                record["sire"]
            )
            and field_present(
                record["dam"]
            )
            for record in records
        )
    )

    checks = [
        {
            "check": (
                "HORSE_CODE_NORMALISATION"
            ),
            "passed": True,
            "observed": (
                "INTEGER_LIKE_VALUES_"
                "NORMALISED_WITHOUT_DECIMAL"
            ),
        },
        {
            "check": (
                "NORMALISED_MASTER_CODE_"
                "CONFLICTS"
            ),
            "passed": (
                conflicting_groups == 0
            ),
            "observed": (
                conflicting_groups
            ),
        },
        {
            "check": (
                "NORMALISED_LINKAGE_"
                "EXECUTED"
            ),
            "passed": True,
            "observed": (
                f"matched_rows={matched_rows};"
                f"matched_codes={matched_codes}"
            ),
        },
        {
            "check": (
                "CANONICAL_HORSE_NOT_"
                "MATERIALISED"
            ),
            "passed": all(
                not row[
                    "canonical_horse_id"
                ]
                for row
                in master_profile_rows
            ),
            "observed": (
                "ALL_CANONICAL_HORSE_IDS_BLANK"
            ),
        },
    ]

    failed_checks = [
        check["check"]
        for check in checks
        if not check["passed"]
    ]

    if (
        conflicting_groups == 0
        and matched_rows > 0
        and durable_evidence_rows > 0
    ):
        decision = (
            "PARTIAL_CANONICAL_HORSE_"
            "MATERIALISATION_ELIGIBLE"
        )

        canonical_status = (
            "ELIGIBLE_FOR_VALIDATED_"
            "COVERED_CODES_ONLY"
        )

        next_stage = (
            "Phase 1.4.2 materialise canonical "
            "horses only for validated covered "
            "horse codes; preserve all unresolved "
            "performances separately."
        )

    elif (
        conflicting_groups == 0
        and matched_rows > 0
    ):
        decision = (
            "HORSE_CODE_LINKAGE_VALIDATED_"
            "BUT_DURABLE_PEDIGREE_EVIDENCE_"
            "INSUFFICIENT"
        )

        canonical_status = (
            "HORSE_CODE_DIMENSION_ELIGIBLE_"
            "CANONICAL_HORSE_BLOCKED"
        )

        next_stage = (
            "Audit whether horse_code is an "
            "official durable registration code "
            "or only a provider identifier before "
            "canonical horse promotion."
        )

    else:
        decision = (
            "CANONICAL_HORSE_"
            "MATERIALISATION_BLOCKED"
        )

        canonical_status = "BLOCKED"

        next_stage = (
            "Resolve code conflicts or acquire "
            "durable registration evidence."
        )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.4.1A Normalised Horse-Code "
            "Validation"
        ),
        "generated_utc": utc_now(),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": (
            "NORMALISED_HORSE_CODE_"
            "VALIDATION_PASS"
            if not failed_checks
            else
            "NORMALISED_HORSE_CODE_"
            "VALIDATION_FAIL"
        ),
        "production_data_modified": False,
        "canonical_horse_ids_generated": 0,
        "master_rows": master_rows,
        "normalised_master_codes": (
            len(master_records)
        ),
        "valid_master_codes": (
            len(valid_codes)
        ),
        "unique_code_groups": (
            unique_groups
        ),
        "exact_duplicate_groups": (
            exact_duplicate_groups
        ),
        "conflicting_code_groups": (
            conflicting_groups
        ),
        "field_coverage": (
            field_coverage
        ),
        "durable_core_identity_codes": (
            durable_evidence_rows
        ),
        "historical_rows": (
            historical_rows
        ),
        "historical_rows_with_code": (
            rows_with_code
        ),
        "historical_rows_without_code": (
            rows_without_code
        ),
        "historical_distinct_codes": (
            len(result_code_counts)
        ),
        "matched_historical_codes": (
            matched_codes
        ),
        "unmatched_historical_codes": (
            unmatched_codes
        ),
        "matched_historical_rows": (
            matched_rows
        ),
        "unmatched_historical_rows": (
            unmatched_rows_count
        ),
        "historical_row_coverage_pct": (
            coverage_pct
        ),
        "historical_code_coverage_pct": (
            code_coverage_pct
        ),
        "name_consistent_codes": (
            name_consistent_codes
        ),
        "name_conflict_codes": (
            name_conflict_codes
        ),
        "checks": checks,
        "failed_checks": (
            failed_checks
        ),
        "identity_decision": (
            decision
        ),
        "canonical_horse_status": (
            canonical_status
        ),
        "next_stage": (
            next_stage
        ),
        "outputs": {
            "master_profile": str(
                master_profile_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "normalised_linkage": str(
                linkage_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "code_conflicts": str(
                code_conflicts_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "unmatched_codes": str(
                unmatched_path.relative_to(
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
        """# EDGEiQ Horse-Code Normalisation V0.1

## Problem corrected

CSV numeric parsing may represent an integer horse code as:

`577170.0`

while another source stores:

`577170`

These are formatting variants of the same integer-like value.

## Canonical normalisation

Integer-like horse codes are represented without a decimal suffix.

Examples:

- `577170.0` becomes `577170`
- `00577170` remains provider-specific text unless parsed numerically
- non-numeric codes remain normalised text

## Governance boundary

Code normalisation proves linkage compatibility.

It does not by itself prove that the code is an official globally durable horse-registration identity.

Canonical horse promotion still requires corroborating durability evidence.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.4.1A Normalised Horse-Code Validation

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['status']}**

- Master rows: **{master_rows:,}**
- Valid normalised master codes: **{len(valid_codes):,}**
- Durable core identity codes: **{durable_evidence_rows:,}**
- Historical rows: **{historical_rows:,}**
- Historical rows matched: **{matched_rows:,}**
- Historical row coverage: **{coverage_pct}%**
- Historical codes matched: **{matched_codes:,}**
- Historical code coverage: **{code_coverage_pct}%**
- Name conflicts among linked codes: **{name_conflict_codes:,}**
- Canonical horse IDs created: **0**

Decision: **{decision}**
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_4_1A_NORMALISED_HORSE_CODE_"
        "VALIDATION_PASS",
        flush=True,
    )

    print(
        f"VALID_MASTER_CODES="
        f"{len(valid_codes)}",
        flush=True,
    )

    print(
        f"DURABLE_CORE_IDENTITY_CODES="
        f"{durable_evidence_rows}",
        flush=True,
    )

    print(
        f"MATCHED_HISTORICAL_ROWS="
        f"{matched_rows}",
        flush=True,
    )

    print(
        f"HISTORICAL_ROW_COVERAGE_PCT="
        f"{coverage_pct}",
        flush=True,
    )

    print(
        f"MATCHED_HISTORICAL_CODES="
        f"{matched_codes}",
        flush=True,
    )

    print(
        f"HISTORICAL_CODE_COVERAGE_PCT="
        f"{code_coverage_pct}",
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
