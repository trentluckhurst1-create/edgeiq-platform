from __future__ import annotations

import base64
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

MASTER = (
    ROOT
    / "public"
    / "data"
    / "horses_master.csv"
)

RESULTS = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_historical_results_warehouse_v2_graphql.csv"
)

PHASE141B = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_4_1b"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_4_1c"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_4_1c"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_4_1c"
)

AUDIT_VERSION = (
    "RACING_AUSTRALIA_IDENTITY_"
    "DEDUPLICATION_AND_TEMPORAL_AUDIT_V0_1"
)

PROGRESS_INTERVAL = 100_000

COUNTRY_SUFFIX_PATTERN = re.compile(
    r"\s*\((AUS|NZ|IRE|GB|USA|FR|JPN|SAF|ARG|BRZ|GER|CAN|CHI|URU|ITY|SWE|DEN|SIN|HK)\)\s*$",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_name(value: Any) -> str:
    text = clean(value).upper()

    text = COUNTRY_SUFFIX_PATTERN.sub(
        "",
        text,
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )


def normalise_code(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    try:
        number = float(text)

        if number.is_integer():
            return str(int(number))

    except ValueError:
        pass

    return text.upper()


def decode_ra_id(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    try:
        return (
            base64.b64decode(
                text,
                validate=True,
            )
            .decode("utf-8")
            .strip()
        )

    except Exception:
        return ""


def parse_date(value: Any) -> datetime | None:
    text = clean(value)[:10]

    if not text:
        return None

    try:
        return datetime.strptime(
            text,
            "%Y-%m-%d",
        )

    except ValueError:
        return None


def latest_file(
    directory: Path,
    pattern: str,
) -> Path:
    candidates = sorted(
        directory.glob(pattern),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            f"No file matched {pattern}"
        )

    return candidates[0]


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

    crosswalk_path = latest_file(
        PHASE141B,
        (
            "edgeiq_cross_provider_horse_"
            "identity_candidates_v0_1_*.csv"
        ),
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    identity_profile_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_racing_australia_horse_"
            f"identity_profile_v0_1_{run_id}.csv"
        )
    )

    membership_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_racing_australia_horse_"
            f"source_membership_v0_1_{run_id}.csv"
        )
    )

    conflicts_path = (
        AUDIT_DIR
        / (
            "edgeiq_racing_australia_horse_"
            f"identity_conflicts_v0_1_{run_id}.csv"
        )
    )

    temporal_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_cross_provider_horse_"
            f"temporal_candidates_v0_1_{run_id}.csv"
        )
    )

    ambiguous_path = (
        AUDIT_DIR
        / (
            "edgeiq_cross_provider_horse_"
            f"unresolved_ambiguities_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_1c_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_1c_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_4_1c_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_4_1C_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_RACING_AUSTRALIA_"
            "HORSE_IDENTITY_GOVERNANCE_V0_1.md"
        )
    )

    grouped_master: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    source_rows = 0
    invalid_id_rows = 0

    with MASTER.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for source_row, row in enumerate(
            reader,
            start=2,
        ):
            source_rows += 1

            encoded = clean(
                row.get("horse_code")
            )

            decoded = decode_ra_id(
                encoded
            )

            if not decoded:
                invalid_id_rows += 1
                continue

            horse_name = clean(
                row.get("horse_name")
            )

            grouped_master[
                decoded
            ].append(
                {
                    "source_row_number": (
                        str(source_row)
                    ),
                    "encoded_horse_code": (
                        encoded
                    ),
                    "racing_australia_horse_id": (
                        decoded
                    ),
                    "horse_name": (
                        horse_name
                    ),
                    "normalised_horse_name": (
                        normalise_name(
                            horse_name
                        )
                    ),
                    "source_url": clean(
                        row.get("source_url")
                    ),
                    "race_entry": clean(
                        row.get("race_entry")
                    ),
                }
            )

    profile_rows: list[
        dict[str, Any]
    ] = []

    membership_rows: list[
        dict[str, Any]
    ] = []

    conflict_rows: list[
        dict[str, Any]
    ] = []

    unique_identity_ids = 0
    repeated_identity_ids = 0
    exact_duplicate_groups = 0
    name_conflict_groups = 0

    for horse_id, records in sorted(
        grouped_master.items()
    ):
        names = sorted({
            record[
                "normalised_horse_name"
            ]
            for record in records
            if record[
                "normalised_horse_name"
            ]
        })

        encoded_values = sorted({
            record[
                "encoded_horse_code"
            ]
            for record in records
        })

        raw_names = sorted({
            record["horse_name"]
            for record in records
            if record["horse_name"]
        })

        if len(records) == 1:
            classification = (
                "UNIQUE_RACING_AUSTRALIA_"
                "HORSE_ID"
            )
            unique_identity_ids += 1

        elif len(names) == 1:
            classification = (
                "REPEATED_RACE_ENTRY_"
                "EVIDENCE_NAME_STABLE"
            )
            repeated_identity_ids += 1
            exact_duplicate_groups += 1

        else:
            classification = (
                "RACING_AUSTRALIA_ID_"
                "NAME_CONFLICT"
            )
            repeated_identity_ids += 1
            name_conflict_groups += 1

        profile_row = {
            "racing_australia_horse_id": (
                horse_id
            ),
            "source_row_count": (
                len(records)
            ),
            "encoded_value_count": (
                len(encoded_values)
            ),
            "encoded_horse_codes": (
                " | ".join(
                    encoded_values
                )
            ),
            "distinct_name_count": (
                len(names)
            ),
            "horse_names": (
                " | ".join(
                    raw_names
                )
            ),
            "normalised_horse_names": (
                " | ".join(
                    names
                )
            ),
            "source_rows": (
                " | ".join(
                    record[
                        "source_row_number"
                    ]
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

        profile_rows.append(
            profile_row
        )

        for record in records:
            membership_rows.append(
                {
                    "racing_australia_horse_id": (
                        horse_id
                    ),
                    "source_row_number": (
                        record[
                            "source_row_number"
                        ]
                    ),
                    "encoded_horse_code": (
                        record[
                            "encoded_horse_code"
                        ]
                    ),
                    "horse_name": (
                        record["horse_name"]
                    ),
                    "normalised_horse_name": (
                        record[
                            "normalised_horse_name"
                        ]
                    ),
                    "source_url": (
                        record["source_url"]
                    ),
                    "race_entry": (
                        record["race_entry"]
                    ),
                    "membership_state": (
                        classification
                    ),
                }
            )

        if classification == (
            "RACING_AUSTRALIA_ID_NAME_CONFLICT"
        ):
            conflict_rows.append(
                profile_row
            )

    write_csv(
        identity_profile_path,
        profile_rows,
    )

    write_csv(
        membership_path,
        membership_rows,
    )

    write_csv(
        conflicts_path,
        conflict_rows,
    )

    ambiguous_names: set[str] = set()
    crosswalk_by_ra_id: dict[
        str,
        dict[str, str],
    ] = {}

    with crosswalk_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            ra_id = clean(
                row.get(
                    "racing_australia_horse_id"
                )
            )

            if ra_id:
                crosswalk_by_ra_id[
                    ra_id
                ] = row

            if clean(
                row.get("classification")
            ) == (
                "EXACT_NAME_MULTIPLE_"
                "HISTORICAL_CODES_AMBIGUOUS"
            ):
                name = clean(
                    row.get(
                        "normalised_horse_name"
                    )
                )

                if name:
                    ambiguous_names.add(
                        name
                    )

    historical_detail: dict[
        tuple[str, str],
        dict[str, Any],
    ] = defaultdict(
        lambda: {
            "performance_rows": 0,
            "min_date": "",
            "max_date": "",
            "raw_names": set(),
        }
    )

    print(
        "PHASE1_4_1C_TEMPORAL_AUDIT_START",
        flush=True,
    )

    with RESULTS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "TEMPORAL_AUDIT_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            name = normalise_name(
                row.get("horse")
            )

            if name not in ambiguous_names:
                continue

            code = normalise_code(
                row.get("horse_code")
            )

            if not code:
                continue

            key = (
                name,
                code,
            )

            detail = historical_detail[
                key
            ]

            detail[
                "performance_rows"
            ] += 1

            raw_name = clean(
                row.get("horse")
            )

            if raw_name:
                detail[
                    "raw_names"
                ].add(raw_name)

            race_date = clean(
                row.get("race_date")
            )[:10]

            if race_date:
                if (
                    not detail["min_date"]
                    or race_date
                    < detail["min_date"]
                ):
                    detail[
                        "min_date"
                    ] = race_date

                if (
                    not detail["max_date"]
                    or race_date
                    > detail["max_date"]
                ):
                    detail[
                        "max_date"
                    ] = race_date

    temporal_rows: list[
        dict[str, Any]
    ] = []

    unresolved_rows: list[
        dict[str, Any]
    ] = []

    temporal_class_counts = Counter()

    ra_ids_by_name: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for profile in profile_rows:
        for name in clean(
            profile[
                "normalised_horse_names"
            ]
        ).split(" | "):
            if name:
                ra_ids_by_name[
                    name
                ].add(
                    profile[
                        "racing_australia_horse_id"
                    ]
                )

    for name in sorted(
        ambiguous_names
    ):
        code_details = []

        for (
            detail_name,
            historical_code,
        ), detail in historical_detail.items():
            if detail_name != name:
                continue

            code_details.append(
                {
                    "historical_horse_code": (
                        historical_code
                    ),
                    "performance_rows": (
                        detail[
                            "performance_rows"
                        ]
                    ),
                    "min_date": (
                        detail["min_date"]
                    ),
                    "max_date": (
                        detail["max_date"]
                    ),
                    "raw_names": (
                        " | ".join(
                            sorted(
                                detail[
                                    "raw_names"
                                ]
                            )
                        )
                    ),
                }
            )

        code_details.sort(
            key=lambda item: (
                item["max_date"],
                item[
                    "performance_rows"
                ],
            ),
            reverse=True,
        )

        current_candidates = []

        if code_details:
            latest_date = parse_date(
                code_details[0][
                    "max_date"
                ]
            )

            if latest_date:
                for item in code_details:
                    item_date = parse_date(
                        item["max_date"]
                    )

                    if not item_date:
                        continue

                    gap_days = (
                        latest_date
                        - item_date
                    ).days

                    if gap_days <= 365:
                        current_candidates.append(
                            item[
                                "historical_horse_code"
                            ]
                        )

        if len(code_details) <= 1:
            classification = (
                "SINGLE_HISTORICAL_CODE"
            )

        elif len(
            current_candidates
        ) == 1:
            classification = (
                "ONE_RECENT_HISTORICAL_CODE_"
                "OLDER_NAMESAKES_EXIST"
            )

        else:
            classification = (
                "TEMPORALLY_UNRESOLVED_"
                "MULTIPLE_HISTORICAL_CODES"
            )

        temporal_class_counts[
            classification
        ] += 1

        ra_ids = sorted(
            ra_ids_by_name.get(
                name,
                set(),
            )
        )

        row = {
            "normalised_horse_name": (
                name
            ),
            "racing_australia_horse_ids": (
                " | ".join(
                    ra_ids
                )
            ),
            "historical_code_count": (
                len(code_details)
            ),
            "historical_codes": (
                " | ".join(
                    item[
                        "historical_horse_code"
                    ]
                    for item in code_details
                )
            ),
            "historical_code_date_ranges": (
                " | ".join(
                    (
                        f"{item['historical_horse_code']}:"
                        f"{item['min_date']}.."
                        f"{item['max_date']}"
                    )
                    for item in code_details
                )
            ),
            "historical_code_performance_rows": (
                " | ".join(
                    (
                        f"{item['historical_horse_code']}:"
                        f"{item['performance_rows']}"
                    )
                    for item in code_details
                )
            ),
            "recent_candidate_codes": (
                " | ".join(
                    current_candidates
                )
            ),
            "classification": (
                classification
            ),
            "automatic_merge_allowed": (
                False
            ),
            "canonical_horse_id": "",
        }

        temporal_rows.append(
            row
        )

        if classification == (
            "TEMPORALLY_UNRESOLVED_"
            "MULTIPLE_HISTORICAL_CODES"
        ):
            unresolved_rows.append(
                row
            )

    write_csv(
        temporal_path,
        temporal_rows,
    )

    write_csv(
        ambiguous_path,
        unresolved_rows,
    )

    crosswalk_single_rows = sum(
        1
        for row
        in crosswalk_by_ra_id.values()
        if clean(
            row.get("classification")
        ) == (
            "EXACT_NAME_SINGLE_"
            "HISTORICAL_CODE_CANDIDATE"
        )
    )

    crosswalk_ambiguous_rows = sum(
        1
        for row
        in crosswalk_by_ra_id.values()
        if clean(
            row.get("classification")
        ) == (
            "EXACT_NAME_MULTIPLE_"
            "HISTORICAL_CODES_AMBIGUOUS"
        )
    )

    checks = [
        {
            "check": (
                "BASE64_IDS_VALID"
            ),
            "passed": (
                invalid_id_rows == 0
            ),
            "observed": (
                f"invalid_rows="
                f"{invalid_id_rows}"
            ),
        },
        {
            "check": (
                "REPEATED_RA_IDS_"
                "CLASSIFIED"
            ),
            "passed": (
                repeated_identity_ids
                == (
                    exact_duplicate_groups
                    + name_conflict_groups
                )
            ),
            "observed": (
                f"repeated_ids="
                f"{repeated_identity_ids};"
                f"name_stable="
                f"{exact_duplicate_groups};"
                f"name_conflicts="
                f"{name_conflict_groups}"
            ),
        },
        {
            "check": (
                "RA_ID_NAME_CONFLICTS"
            ),
            "passed": (
                name_conflict_groups == 0
            ),
            "observed": (
                name_conflict_groups
            ),
        },
        {
            "check": (
                "SOURCE_ROWS_PRESERVED"
            ),
            "passed": (
                len(
                    membership_rows
                )
                == source_rows
            ),
            "observed": (
                f"source_rows="
                f"{source_rows};"
                f"membership_rows="
                f"{len(membership_rows)}"
            ),
        },
        {
            "check": (
                "NO_AUTOMATIC_"
                "CROSS_PROVIDER_MERGE"
            ),
            "passed": all(
                not row[
                    "automatic_merge_allowed"
                ]
                for row in temporal_rows
            ),
            "observed": (
                "ALL_MERGES_DISABLED"
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
                for row in profile_rows
            )
            and all(
                not row[
                    "canonical_horse_id"
                ]
                for row in temporal_rows
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

    if name_conflict_groups == 0:
        status = (
            "RACING_AUSTRALIA_IDENTITY_"
            "DEDUPLICATION_AUDIT_PASS"
        )
    else:
        status = (
            "RACING_AUSTRALIA_IDENTITY_"
            "DEDUPLICATION_AUDIT_FAIL"
        )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.4.1C Racing Australia "
            "Identity Deduplication and "
            "Temporal Ambiguity Audit"
        ),
        "generated_utc": (
            utc_now()
        ),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": status,
        "production_data_modified": False,
        "canonical_horse_ids_generated": 0,
        "source_rows": (
            source_rows
        ),
        "distinct_racing_australia_ids": (
            len(grouped_master)
        ),
        "unique_identity_ids": (
            unique_identity_ids
        ),
        "repeated_identity_ids": (
            repeated_identity_ids
        ),
        "repeated_name_stable_ids": (
            exact_duplicate_groups
        ),
        "identity_name_conflicts": (
            name_conflict_groups
        ),
        "crosswalk_single_code_rows": (
            crosswalk_single_rows
        ),
        "crosswalk_ambiguous_rows": (
            crosswalk_ambiguous_rows
        ),
        "temporal_class_counts": dict(
            sorted(
                temporal_class_counts.items()
            )
        ),
        "temporally_unresolved_names": (
            len(unresolved_rows)
        ),
        "checks": checks,
        "failed_checks": (
            failed_checks
        ),
        "identity_decision": (
            "RACING_AUSTRALIA_IDS_VALIDATED_"
            "AS_PROVIDER_HORSE_IDENTITIES_"
            "CROSS_PROVIDER_LINKS_REMAIN_"
            "CANDIDATE_EVIDENCE_ONLY"
            if not failed_checks
            else
            "RACING_AUSTRALIA_IDENTITY_"
            "CONFLICTS_REQUIRE_RESOLUTION"
        ),
        "canonical_horse_status": (
            "NOT_MATERIALISED"
        ),
        "next_stage": (
            "Begin Benchmark Engine Phase 1.5 "
            "while durable cross-provider horse "
            "corroboration remains a parallel "
            "identity workstream."
        ),
        "outputs": {
            "identity_profile": str(
                identity_profile_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "source_membership": str(
                membership_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "identity_conflicts": str(
                conflicts_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "temporal_candidates": str(
                temporal_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "unresolved_ambiguities": str(
                ambiguous_path.relative_to(
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
        """# EDGEiQ Racing Australia Horse Identity Governance V0.1

## Racing Australia identity

The Base64 HorseCode decodes into a numeric Racing Australia horse identifier.

Repeated source rows do not automatically indicate duplicate horses.

They may represent the same horse appearing in multiple current race entries.

## Duplicate-source rule

When one decoded Racing Australia ID has one stable normalised name:

- preserve every source row
- materialise one provider identity candidate
- retain source membership and lineage
- do not treat repeat rows as an identity failure

When one decoded ID has multiple names:

- classify as an identity conflict
- block promotion
- preserve every conflicting row

## Historical crosswalk rule

Exact-name equality creates candidate evidence only.

Temporal separation may identify an older namesake and one currently active horse, but it still does not authorise an automatic cross-provider merge.

## Canonical boundary

No canonical horse ID is created in this phase.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.4.1C Racing Australia Identity Deduplication and Temporal Audit

Generated UTC: `{summary['generated_utc']}`

Status: **{status}**

- Source race-entry rows: **{source_rows:,}**
- Distinct Racing Australia IDs: **{len(grouped_master):,}**
- Unique IDs: **{unique_identity_ids:,}**
- Repeated IDs: **{repeated_identity_ids:,}**
- Repeated IDs with stable names: **{exact_duplicate_groups:,}**
- Racing Australia ID/name conflicts: **{name_conflict_groups:,}**
- Exact-name single historical-code rows: **{crosswalk_single_rows:,}**
- Exact-name ambiguous rows: **{crosswalk_ambiguous_rows:,}**
- Temporally unresolved names: **{len(unresolved_rows):,}**
- Canonical horse IDs created: **0**

Production data was not modified.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_4_1C_RACING_AUSTRALIA_"
        "IDENTITY_DEDUPLICATION_AUDIT_PASS"
        if not failed_checks
        else
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_4_1C_RACING_AUSTRALIA_"
        "IDENTITY_DEDUPLICATION_AUDIT_FAIL",
        flush=True,
    )

    print(
        f"DISTINCT_RA_IDS="
        f"{len(grouped_master)}",
        flush=True,
    )

    print(
        f"REPEATED_RA_IDS="
        f"{repeated_identity_ids}",
        flush=True,
    )

    print(
        f"REPEATED_NAME_STABLE_IDS="
        f"{exact_duplicate_groups}",
        flush=True,
    )

    print(
        f"RA_ID_NAME_CONFLICTS="
        f"{name_conflict_groups}",
        flush=True,
    )

    print(
        f"TEMPORALLY_UNRESOLVED_NAMES="
        f"{len(unresolved_rows)}",
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

    if failed_checks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
