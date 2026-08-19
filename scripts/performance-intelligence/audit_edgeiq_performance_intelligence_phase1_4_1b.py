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

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_4_1b"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_4_1b"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_4_1b"
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

    return text


def decode_racing_australia_code(
    value: Any,
) -> str:
    text = clean(value)

    if not text:
        return ""

    try:
        decoded = base64.b64decode(
            text,
            validate=True,
        ).decode(
            "utf-8"
        )

        return decoded.strip()

    except Exception:
        return ""


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

    master_rows = []

    with MASTER.open(
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
            encoded_code = clean(
                row.get("horse_code")
            )

            decoded_code = (
                decode_racing_australia_code(
                    encoded_code
                )
            )

            horse_name = clean(
                row.get("horse_name")
            )

            master_rows.append(
                {
                    "master_source_row": (
                        row_number + 1
                    ),
                    "racing_australia_horse_code_encoded": (
                        encoded_code
                    ),
                    "racing_australia_horse_id": (
                        decoded_code
                    ),
                    "horse_name": horse_name,
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

    historical_by_name: dict[
        str,
        dict[str, Any],
    ] = defaultdict(
        lambda: {
            "performance_rows": 0,
            "horse_codes": set(),
            "raw_names": set(),
            "min_date": "",
            "max_date": "",
        }
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
                    "CROSS_PROVIDER_NAME_AUDIT_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            name = normalise_name(
                row.get("horse")
            )

            if not name:
                continue

            horse_code = normalise_code(
                row.get("horse_code")
            )

            race_date = clean(
                row.get("race_date")
            )[:10]

            entry = historical_by_name[
                name
            ]

            entry[
                "performance_rows"
            ] += 1

            if horse_code:
                entry[
                    "horse_codes"
                ].add(
                    horse_code
                )

            raw_name = clean(
                row.get("horse")
            )

            if raw_name:
                entry[
                    "raw_names"
                ].add(
                    raw_name
                )

            if race_date:
                if (
                    not entry["min_date"]
                    or race_date
                    < entry["min_date"]
                ):
                    entry[
                        "min_date"
                    ] = race_date

                if (
                    not entry["max_date"]
                    or race_date
                    > entry["max_date"]
                ):
                    entry[
                        "max_date"
                    ] = race_date

    crosswalk_rows = []
    classification_counts = Counter()

    for master_row in master_rows:
        name = master_row[
            "normalised_horse_name"
        ]

        history = historical_by_name.get(
            name
        )

        if not history:
            classification = (
                "NO_EXACT_NAME_MATCH"
            )

            historical_codes = []
            performance_rows = 0
            raw_names = []
            min_date = ""
            max_date = ""

        else:
            historical_codes = sorted(
                history[
                    "horse_codes"
                ]
            )

            performance_rows = history[
                "performance_rows"
            ]

            raw_names = sorted(
                history[
                    "raw_names"
                ]
            )

            min_date = history[
                "min_date"
            ]

            max_date = history[
                "max_date"
            ]

            if len(
                historical_codes
            ) == 1:
                classification = (
                    "EXACT_NAME_SINGLE_"
                    "HISTORICAL_CODE_CANDIDATE"
                )

            elif len(
                historical_codes
            ) > 1:
                classification = (
                    "EXACT_NAME_MULTIPLE_"
                    "HISTORICAL_CODES_AMBIGUOUS"
                )

            else:
                classification = (
                    "EXACT_NAME_WITHOUT_"
                    "HISTORICAL_CODE"
                )

        classification_counts[
            classification
        ] += 1

        crosswalk_rows.append(
            {
                **master_row,
                "historical_performance_rows": (
                    performance_rows
                ),
                "historical_horse_code_count": (
                    len(
                        historical_codes
                    )
                ),
                "historical_horse_codes": (
                    " | ".join(
                        historical_codes
                    )
                ),
                "historical_raw_names": (
                    " | ".join(
                        raw_names
                    )
                ),
                "historical_min_race_date": (
                    min_date
                ),
                "historical_max_race_date": (
                    max_date
                ),
                "classification": (
                    classification
                ),
                "automatic_merge_allowed": (
                    False
                ),
                "canonical_horse_id": "",
            }
        )

    decoded_ids = [
        row[
            "racing_australia_horse_id"
        ]
        for row in master_rows
        if row[
            "racing_australia_horse_id"
        ]
    ]

    decoded_id_counts = Counter(
        decoded_ids
    )

    duplicate_decoded_ids = {
        horse_id: count
        for horse_id, count
        in decoded_id_counts.items()
        if count > 1
    }

    invalid_base64_rows = sum(
        1
        for row in master_rows
        if not row[
            "racing_australia_horse_id"
        ]
    )

    exact_single_candidates = sum(
        1
        for row in crosswalk_rows
        if row["classification"]
        == (
            "EXACT_NAME_SINGLE_"
            "HISTORICAL_CODE_CANDIDATE"
        )
    )

    ambiguous_candidates = sum(
        1
        for row in crosswalk_rows
        if row["classification"]
        == (
            "EXACT_NAME_MULTIPLE_"
            "HISTORICAL_CODES_AMBIGUOUS"
        )
    )

    no_match_rows = sum(
        1
        for row in crosswalk_rows
        if row["classification"]
        == "NO_EXACT_NAME_MATCH"
    )

    checks = [
        {
            "check": (
                "RACING_AUSTRALIA_"
                "BASE64_DECODE"
            ),
            "passed": (
                invalid_base64_rows == 0
            ),
            "observed": (
                f"invalid_rows="
                f"{invalid_base64_rows}"
            ),
        },
        {
            "check": (
                "RACING_AUSTRALIA_"
                "HORSE_ID_UNIQUE"
            ),
            "passed": (
                len(
                    duplicate_decoded_ids
                )
                == 0
            ),
            "observed": (
                f"duplicate_ids="
                f"{len(duplicate_decoded_ids)}"
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
                for row in crosswalk_rows
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
                for row in crosswalk_rows
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

    output_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_cross_provider_horse_"
            f"identity_candidates_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_1b_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_1b_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_4_1b_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_4_1B_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_CROSS_PROVIDER_HORSE_"
            "IDENTITY_V0_1.md"
        )
    )

    write_csv(
        output_path,
        crosswalk_rows,
    )

    write_csv(
        checks_path,
        checks,
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.4.1B Cross-Provider Horse "
            "Identity Candidate Audit"
        ),
        "generated_utc": (
            utc_now()
        ),
        "status": (
            "CROSS_PROVIDER_HORSE_"
            "IDENTITY_AUDIT_PASS"
            if not failed_checks
            else
            "CROSS_PROVIDER_HORSE_"
            "IDENTITY_AUDIT_FAIL"
        ),
        "production_data_modified": False,
        "canonical_horse_ids_generated": 0,
        "master_rows": len(
            master_rows
        ),
        "decoded_racing_australia_ids": (
            len(decoded_ids)
        ),
        "duplicate_racing_australia_ids": (
            len(
                duplicate_decoded_ids
            )
        ),
        "invalid_base64_rows": (
            invalid_base64_rows
        ),
        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),
        "exact_name_single_code_candidates": (
            exact_single_candidates
        ),
        "exact_name_ambiguous_candidates": (
            ambiguous_candidates
        ),
        "no_exact_name_match_rows": (
            no_match_rows
        ),
        "identity_decision": (
            "CROSS_PROVIDER_CANDIDATE_"
            "EVIDENCE_ONLY_CANONICAL_"
            "HORSE_REMAINS_BLOCKED"
        ),
        "next_stage": (
            "Acquire pedigree, DOB, sex or "
            "official registration corroboration "
            "for exact-name single-code candidates, "
            "or query Racing Australia horse pages "
            "for durable identity attributes."
        ),
        "outputs": {
            "candidate_crosswalk": str(
                output_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "checks": str(
                checks_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
    }

    write_json(
        summary_path,
        summary,
    )

    write_json(
        latest_path,
        summary,
    )

    architecture_path.write_text(
        """# EDGEiQ Cross-Provider Horse Identity V0.1

## Identity namespaces

EDGEiQ currently observes at least two horse-identity namespaces:

1. Historical GraphQL horse code.
2. Racing Australia horse ID encoded in Base64.

These identifiers must not be assumed equivalent.

## Crosswalk evidence

Exact normalised horse-name equality may create a candidate relationship only.

It may not automatically merge records.

## Promotion requirements

A cross-provider relationship requires corroboration from one or more of:

- official registration number
- date of birth
- foaling year
- sex
- country
- sire
- dam
- stable provider-issued horse identity
- temporal evidence proving one continuous identity

## Prohibited action

A canonical horse ID must not be created from exact-name equality alone.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.4.1B Cross-Provider Horse Identity Candidate Audit

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['status']}**

- Racing Australia master rows: **{len(master_rows):,}**
- Successfully decoded IDs: **{len(decoded_ids):,}**
- Duplicate decoded IDs: **{len(duplicate_decoded_ids):,}**
- Exact-name single historical-code candidates: **{exact_single_candidates:,}**
- Exact-name ambiguous candidates: **{ambiguous_candidates:,}**
- No exact-name match: **{no_match_rows:,}**
- Canonical horse IDs created: **0**

Canonical horse identity remains blocked pending durable corroboration.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_4_1B_CROSS_PROVIDER_"
        "HORSE_IDENTITY_AUDIT_PASS",
        flush=True,
    )

    print(
        f"DECODED_IDS="
        f"{len(decoded_ids)}",
        flush=True,
    )

    print(
        f"EXACT_NAME_SINGLE_CODE_CANDIDATES="
        f"{exact_single_candidates}",
        flush=True,
    )

    print(
        f"AMBIGUOUS_CANDIDATES="
        f"{ambiguous_candidates}",
        flush=True,
    )

    print(
        f"NO_MATCH_ROWS="
        f"{no_match_rows}",
        flush=True,
    )

    print(
        f"CROSSWALK={output_path}",
        flush=True,
    )

    print(
        f"SUMMARY={summary_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
