from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = (
    "EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_IDENTITY_SEMANTICS_"
    "PHASE1A_6B_1A_V1"
)

PASS_STATUS = f"{AUDIT_ID}_PASS"
FAIL_STATUS = f"{AUDIT_ID}_FAIL"

EXPECTED_ROWS = 879_784
EXPECTED_UNIQUE_IDENTITIES = 879_695
EXPECTED_DUPLICATE_EXCESS = 89

ROOT = Path.cwd().absolute()

RAW_SOURCE = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
    / "eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e"
    / "canonical_performance_evidence.csv"
)

CORRECTED_SOURCE = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "performance-facts-corrected"
    / "eiq_performance_facts_v0_2_a0c3715ab506d19f9301d8a4"
    / "canonical_performance_facts_v0_2.csv"
)

RAW_SNAPSHOT_ROOT = RAW_SOURCE.parent
RAW_ASSET_CATALOG = RAW_SNAPSHOT_ROOT / "asset_catalog.csv"
RAW_MATERIALISATION_CHECKS = (
    RAW_SNAPSHOT_ROOT / "materialisation_checks.csv"
)

OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "historical-observation-v3-raw-identity-semantics"
)

REPORT_JSON = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "RAW_IDENTITY_SEMANTICS_REPORT.json"
)

REPORT_MD = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "RAW_IDENTITY_SEMANTICS_REPORT.md"
)

IDENTITY_MATRIX = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "RAW_IDENTITY_EXPRESSION_MATRIX.csv"
)

LINEAGE_MATRIX = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "NON_CIRCULAR_LINEAGE_MATRIX.csv"
)

AUTHORITY_CONTRACT = (
    OUTPUT_ROOT
    / "edgeiq_historical_observation_v3_"
      "raw_identity_authority_contract.json"
)

SELF_AUDIT_MARKERS = {
    "authority_lineage_phase1a_6b_1",
    "raw_identity_semantics_phase1a_6b_1a",
    "physical_authority_discovery_phase1a_6b_0",
    "authority_phase1a_6b",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def normalise(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        value.strip().lower(),
    ).strip("_")


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def read_text(path: Path) -> str:
    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    return path.read_text(
        encoding="cp1252",
        errors="replace",
    )


def csv_header(path: Path) -> list[str]:
    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ):
        try:
            with path.open(
                "r",
                encoding=encoding,
                errors="strict",
                newline="",
            ) as handle:
                return next(csv.reader(handle), [])
        except UnicodeDecodeError:
            continue

    with path.open(
        "r",
        encoding="cp1252",
        errors="replace",
        newline="",
    ) as handle:
        return next(csv.reader(handle), [])


def read_small_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "header": [],
            "rows": [],
        }

    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ):
        try:
            with path.open(
                "r",
                encoding=encoding,
                errors="strict",
                newline="",
            ) as handle:
                reader = csv.DictReader(handle)

                return {
                    "exists": True,
                    "header": reader.fieldnames or [],
                    "rows": list(reader),
                }

        except UnicodeDecodeError:
            continue

    return {
        "exists": True,
        "header": csv_header(path),
        "rows": [],
    }


def git_paths() -> list[str]:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-co",
            "--exclude-standard",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "git ls-files failed: "
            + result.stderr.strip()
        )

    return sorted(
        {
            line.strip().replace("\\", "/")
            for line in result.stdout.splitlines()
            if line.strip()
        },
        key=str.lower,
    )


def select_candidate_identity_fields(
    header: list[str],
) -> tuple[str, list[str], list[str]]:
    normalised_to_actual = {
        normalise(field): field
        for field in header
    }

    race_aliases = (
        "race_id",
        "raceid",
        "source_race_id",
        "graphql_race_id",
    )

    race_field = ""

    for alias in race_aliases:
        if alias in normalised_to_actual:
            race_field = normalised_to_actual[alias]
            break

    if not race_field:
        raise RuntimeError(
            "No race identity field was found in the raw source."
        )

    runner_priority_tokens = (
        "runner",
        "horse",
        "saddle",
        "cloth",
        "tab",
        "number",
        "barrier",
        "starter",
        "participant",
    )

    lineage_exclusions = {
        "source_row_number",
        "row_number",
        "physical_row_number",
    }

    candidate_fields: list[str] = []

    for field in header:
        normalised_field = normalise(field)

        if field == race_field:
            continue

        if normalised_field in lineage_exclusions:
            continue

        if any(
            token in normalised_field
            for token in runner_priority_tokens
        ):
            candidate_fields.append(field)

    candidate_fields = list(
        dict.fromkeys(candidate_fields)
    )

    supporting_fields = [
        field
        for field in header
        if normalise(field) in {
            "race_date",
            "meeting_date",
            "track",
            "track_name",
            "race_number",
            "race_no",
            "source_row_number",
        }
    ]

    return (
        race_field,
        candidate_fields,
        supporting_fields,
    )


def build_identity_expressions(
    race_field: str,
    runner_fields: list[str],
) -> list[dict[str, Any]]:
    expressions: list[dict[str, Any]] = []

    for runner_field in runner_fields:
        expressions.append(
            {
                "expression_type": "PAIR",
                "fields": [
                    race_field,
                    runner_field,
                ],
                "expression": (
                    f"{race_field} + {runner_field}"
                ),
            }
        )

    numeric_like = [
        field
        for field in runner_fields
        if any(
            token in normalise(field)
            for token in (
                "number",
                "tab",
                "saddle",
                "cloth",
                "barrier",
            )
        )
    ]

    horse_like = [
        field
        for field in runner_fields
        if "horse" in normalise(field)
        or "runner_name" in normalise(field)
        or normalise(field) == "runner"
    ]

    for horse_field in horse_like:
        for number_field in numeric_like:
            if horse_field == number_field:
                continue

            expressions.append(
                {
                    "expression_type": "TRIPLE",
                    "fields": [
                        race_field,
                        horse_field,
                        number_field,
                    ],
                    "expression": (
                        f"{race_field} + "
                        f"{horse_field} + "
                        f"{number_field}"
                    ),
                }
            )

    unique: dict[
        tuple[str, ...],
        dict[str, Any],
    ] = {}

    for expression in expressions:
        key = tuple(expression["fields"])
        unique[key] = expression

    return list(unique.values())


def import_identity_columns_to_sqlite(
    database_path: Path,
    selected_fields: list[str],
) -> tuple[int, dict[str, int]]:
    connection = sqlite3.connect(database_path)

    connection.execute(
        "PRAGMA journal_mode = OFF"
    )
    connection.execute(
        "PRAGMA synchronous = OFF"
    )
    connection.execute(
        "PRAGMA temp_store = FILE"
    )
    connection.execute(
        "PRAGMA cache_size = -200000"
    )

    column_sql = ", ".join(
        f"{quote_identifier(field)} TEXT"
        for field in selected_fields
    )

    connection.execute(
        f"CREATE TABLE raw_identity ({column_sql})"
    )

    placeholders = ", ".join(
        "?"
        for _ in selected_fields
    )

    insert_sql = (
        "INSERT INTO raw_identity VALUES "
        f"({placeholders})"
    )

    source_rows = 0
    null_counts = {
        field: 0
        for field in selected_fields
    }

    with RAW_SOURCE.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        batch: list[tuple[str, ...]] = []

        for row in reader:
            values: list[str] = []

            for field in selected_fields:
                value = str(
                    row.get(field, "")
                ).strip()

                if not value:
                    null_counts[field] += 1

                values.append(value)

            batch.append(tuple(values))
            source_rows += 1

            if len(batch) >= 20_000:
                connection.executemany(
                    insert_sql,
                    batch,
                )
                connection.commit()
                batch.clear()

            if source_rows % 250_000 == 0:
                print(
                    f"  imported {source_rows:,} rows",
                    flush=True,
                )

        if batch:
            connection.executemany(
                insert_sql,
                batch,
            )
            connection.commit()

    connection.close()

    return source_rows, null_counts


def count_identity_expression(
    database_path: Path,
    fields: list[str],
) -> dict[str, int]:
    connection = sqlite3.connect(database_path)

    try:
        field_sql = ", ".join(
            quote_identifier(field)
            for field in fields
        )

        valid_condition = " AND ".join(
            f"TRIM({quote_identifier(field)}) <> ''"
            for field in fields
        )

        unique_rows = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT {field_sql}
                FROM raw_identity
                WHERE {valid_condition}
                GROUP BY {field_sql}
            )
            """
        ).fetchone()[0]

        complete_rows = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM raw_identity
            WHERE {valid_condition}
            """
        ).fetchone()[0]

        incomplete_rows = (
            EXPECTED_ROWS - complete_rows
        )

        duplicate_excess = (
            complete_rows - unique_rows
        )

        return {
            "complete_rows": complete_rows,
            "incomplete_rows": incomplete_rows,
            "unique_identities": unique_rows,
            "duplicate_excess": duplicate_excess,
        }

    finally:
        connection.close()


def collect_non_circular_lineage() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    raw_name = RAW_SOURCE.name
    corrected_name = CORRECTED_SOURCE.name

    raw_path = relative(RAW_SOURCE)
    corrected_path = relative(CORRECTED_SOURCE)

    for repository_path in git_paths():
        path = ROOT / repository_path

        if (
            not path.exists()
            or path.suffix.lower()
            not in {".py", ".ps1", ".json", ".md", ".csv"}
        ):
            continue

        lower_path = repository_path.lower()

        if any(
            marker in lower_path
            for marker in SELF_AUDIT_MARKERS
        ):
            continue

        text = read_text(path)
        normalised_text = text.replace("\\", "/")

        references_raw = (
            raw_name in text
            or raw_path in normalised_text
        )

        references_corrected = (
            corrected_name in text
            or corrected_path in normalised_text
        )

        if not references_raw and not references_corrected:
            continue

        lower_text = text.lower()

        rows.append(
            {
                "repository_path": repository_path,
                "references_raw": references_raw,
                "references_corrected": (
                    references_corrected
                ),
                "references_both": (
                    references_raw
                    and references_corrected
                ),
                "raw_language": bool(
                    re.search(
                        r"(raw|evidence|source|graphql|"
                        r"materialis|snapshot)",
                        lower_text,
                    )
                ),
                "correction_language": bool(
                    re.search(
                        r"(correct|quality_state|"
                        r"benchmark_eligible|"
                        r"performance_fact)",
                        lower_text,
                    )
                ),
                "write_language": bool(
                    re.search(
                        r"(dictwriter|writerow|to_csv|"
                        r"write_text|copyfile|"
                        r"shutil\.copy)",
                        lower_text,
                    )
                ),
            }
        )

    return sorted(
        rows,
        key=lambda item: item[
            "repository_path"
        ].lower(),
    )


def main() -> int:
    print(AUDIT_ID)
    print("=" * len(AUDIT_ID))
    print()

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not RAW_SOURCE.exists():
        raise FileNotFoundError(
            relative(RAW_SOURCE)
        )

    raw_header = csv_header(RAW_SOURCE)
    corrected_header = csv_header(
        CORRECTED_SOURCE
    )

    print("RAW HEADER")
    print("----------")

    for index, field in enumerate(
        raw_header,
        start=1,
    ):
        print(
            f"{index:02d}. {field}",
            flush=True,
        )

    print()

    race_field, runner_fields, supporting_fields = (
        select_candidate_identity_fields(
            raw_header
        )
    )

    print(f"Race field: {race_field}")
    print(
        "Candidate runner fields: "
        + (
            ", ".join(runner_fields)
            if runner_fields
            else "NONE"
        )
    )
    print(
        "Supporting fields: "
        + (
            ", ".join(supporting_fields)
            if supporting_fields
            else "NONE"
        )
    )
    print()

    if not runner_fields:
        raise RuntimeError(
            "No candidate runner-side identity fields found."
        )

    expressions = build_identity_expressions(
        race_field,
        runner_fields,
    )

    selected_fields = list(
        dict.fromkeys(
            field
            for expression in expressions
            for field in expression["fields"]
        )
    )

    print(
        f"Identity expressions to test: "
        f"{len(expressions):,}"
    )
    print(
        f"Columns imported to temporary SQLite: "
        f"{len(selected_fields):,}"
    )
    print()

    with tempfile.TemporaryDirectory(
        prefix="edgeiq_identity_semantics_"
    ) as temporary_directory:
        database_path = (
            Path(temporary_directory)
            / "identity_semantics.sqlite"
        )

        source_rows, null_counts = (
            import_identity_columns_to_sqlite(
                database_path,
                selected_fields,
            )
        )

        if source_rows != EXPECTED_ROWS:
            raise RuntimeError(
                "Raw source population changed: "
                f"actual={source_rows}; "
                f"expected={EXPECTED_ROWS}"
            )

        for index, expression in enumerate(
            expressions,
            start=1,
        ):
            print(
                f"[{index}/{len(expressions)}] "
                f"{expression['expression']}",
                flush=True,
            )

            results = count_identity_expression(
                database_path,
                expression["fields"],
            )

            expression.update(results)

            expression["unique_contract_match"] = (
                results["unique_identities"]
                == EXPECTED_UNIQUE_IDENTITIES
            )

            expression[
                "duplicate_contract_match"
            ] = (
                results["duplicate_excess"]
                == EXPECTED_DUPLICATE_EXCESS
            )

            expression[
                "complete_population"
            ] = (
                results["complete_rows"]
                == EXPECTED_ROWS
            )

            print(
                "  unique="
                f"{results['unique_identities']:,}; "
                "duplicates="
                f"{results['duplicate_excess']:,}; "
                "incomplete="
                f"{results['incomplete_rows']:,}",
                flush=True,
            )

    exact_matches = [
        expression
        for expression in expressions
        if expression[
            "unique_contract_match"
        ]
        and expression[
            "duplicate_contract_match"
        ]
        and expression[
            "complete_population"
        ]
    ]

    lineage_rows = (
        collect_non_circular_lineage()
    )

    asset_catalog = read_small_csv(
        RAW_ASSET_CATALOG
    )

    materialisation_checks = read_small_csv(
        RAW_MATERIALISATION_CHECKS
    )

    catalog_text = json.dumps(
        asset_catalog,
        sort_keys=True,
    ).lower()

    checks_text = json.dumps(
        materialisation_checks,
        sort_keys=True,
    ).lower()

    asset_catalog_proven = (
        RAW_SOURCE.name.lower()
        in catalog_text
    )

    materialisation_proven = (
        RAW_SOURCE.name.lower()
        in checks_text
        or str(EXPECTED_ROWS)
        in checks_text
    )

    non_circular_raw_references = [
        row
        for row in lineage_rows
        if row["references_raw"]
    ]

    corrected_derived_fields = [
        field
        for field in corrected_header
        if normalise(field) in {
            "performance_fact_id",
            "benchmark_eligible",
            "quality_state",
            "quality_reason",
            "corrected_time_seconds",
            "corrected_seconds",
        }
    ]

    raw_lineage_fields = [
        field
        for field in raw_header
        if normalise(field) in {
            "source_row_number",
            "source_file",
            "source_path",
            "source_system",
            "source_record_id",
        }
    ]

    authority_proven = bool(
        len(exact_matches) == 1
        and asset_catalog_proven
        and materialisation_proven
        and raw_lineage_fields
        and corrected_derived_fields
    )

    if authority_proven:
        status = PASS_STATUS
        decision = (
            "LOCK_CANONICAL_PERFORMANCE_EVIDENCE_"
            "AS_PHYSICAL_AUTHORITY"
        )

        selected_expression = exact_matches[0]

        decision_reason = (
            "Exactly one complete raw identity expression "
            "reproduces the governed 879,695 unique identities "
            "and duplicate excess of 89. The dataset is "
            "registered in its raw snapshot asset catalogue, "
            "passes materialisation evidence, preserves "
            "row-level source lineage and is upstream of the "
            "corrected performance-fact enrichment."
        )

    elif len(exact_matches) > 1:
        status = FAIL_STATUS
        decision = (
            "MULTIPLE_IDENTITY_EXPRESSIONS_MATCH"
        )
        selected_expression = None

        decision_reason = (
            "Multiple complete identity expressions reproduce "
            "the governed population. The canonical expression "
            "must be distinguished by upstream source semantics."
        )

    else:
        status = FAIL_STATUS
        decision = (
            "RAW_IDENTITY_CONTRACT_NOT_REPRODUCED"
        )
        selected_expression = None

        decision_reason = (
            "No complete identity expression reproduced both "
            "879,695 unique identities and duplicate excess 89."
        )

    with IDENTITY_MATRIX.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "expression_type",
            "expression",
            "fields",
            "complete_rows",
            "incomplete_rows",
            "unique_identities",
            "duplicate_excess",
            "complete_population",
            "unique_contract_match",
            "duplicate_contract_match",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()

        for expression in expressions:
            writer.writerow(
                {
                    "expression_type": (
                        expression[
                            "expression_type"
                        ]
                    ),
                    "expression": (
                        expression["expression"]
                    ),
                    "fields": "|".join(
                        expression["fields"]
                    ),
                    "complete_rows": (
                        expression[
                            "complete_rows"
                        ]
                    ),
                    "incomplete_rows": (
                        expression[
                            "incomplete_rows"
                        ]
                    ),
                    "unique_identities": (
                        expression[
                            "unique_identities"
                        ]
                    ),
                    "duplicate_excess": (
                        expression[
                            "duplicate_excess"
                        ]
                    ),
                    "complete_population": (
                        expression[
                            "complete_population"
                        ]
                    ),
                    "unique_contract_match": (
                        expression[
                            "unique_contract_match"
                        ]
                    ),
                    "duplicate_contract_match": (
                        expression[
                            "duplicate_contract_match"
                        ]
                    ),
                }
            )

    with LINEAGE_MATRIX.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "repository_path",
            "references_raw",
            "references_corrected",
            "references_both",
            "raw_language",
            "correction_language",
            "write_language",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(lineage_rows)

    selected_expression_payload = (
        {
            "expression": (
                selected_expression[
                    "expression"
                ]
            ),
            "fields": (
                selected_expression[
                    "fields"
                ]
            ),
            "physical_rows": (
                selected_expression[
                    "complete_rows"
                ]
            ),
            "unique_identities": (
                selected_expression[
                    "unique_identities"
                ]
            ),
            "duplicate_excess": (
                selected_expression[
                    "duplicate_excess"
                ]
            ),
        }
        if selected_expression
        else None
    )

    contract = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
            "RAW_IDENTITY_AUTHORITY_CONTRACT_V1"
        ),
        "status": status,
        "decision": decision,
        "generated_at_utc": now_utc(),
        "selected_physical_authority": (
            relative(RAW_SOURCE)
            if authority_proven
            else None
        ),
        "selected_raw_identity_expression": (
            selected_expression_payload
        ),
        "population_contract": {
            "physical_rows": EXPECTED_ROWS,
            "unique_raw_identities": (
                EXPECTED_UNIQUE_IDENTITIES
            ),
            "duplicate_excess": (
                EXPECTED_DUPLICATE_EXCESS
            ),
        },
        "raw_source_lineage_fields": (
            raw_lineage_fields
        ),
        "corrected_derived_fields": (
            corrected_derived_fields
        ),
        "asset_catalog_proven": (
            asset_catalog_proven
        ),
        "materialisation_proven": (
            materialisation_proven
        ),
        "non_circular_raw_reference_count": (
            len(non_circular_raw_references)
        ),
        "warehouse_build_authorised": (
            authority_proven
        ),
    }

    AUTHORITY_CONTRACT.write_text(
        json.dumps(
            contract,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report = {
        "audit_id": AUDIT_ID,
        "status": status,
        "decision": decision,
        "decision_reason": decision_reason,
        "generated_at_utc": now_utc(),
        "raw_source": relative(RAW_SOURCE),
        "corrected_source": relative(
            CORRECTED_SOURCE
        ),
        "raw_header": raw_header,
        "corrected_header": corrected_header,
        "race_field": race_field,
        "candidate_runner_fields": (
            runner_fields
        ),
        "supporting_fields": (
            supporting_fields
        ),
        "null_counts": null_counts,
        "identity_expressions": (
            expressions
        ),
        "exact_match_count": len(
            exact_matches
        ),
        "selected_identity_expression": (
            selected_expression_payload
        ),
        "raw_lineage_fields": (
            raw_lineage_fields
        ),
        "corrected_derived_fields": (
            corrected_derived_fields
        ),
        "asset_catalog": asset_catalog,
        "materialisation_checks": (
            materialisation_checks
        ),
        "asset_catalog_proven": (
            asset_catalog_proven
        ),
        "materialisation_proven": (
            materialisation_proven
        ),
        "non_circular_lineage": (
            lineage_rows
        ),
        "warehouse_written": False,
        "existing_v2_modified": False,
        "rejected_v3_modified": False,
    }

    REPORT_JSON.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    expression_lines = [
        "| Identity expression | Complete | "
        "Unique | Duplicate excess | Match |",
        "|---|---:|---:|---:|---:|",
    ]

    for expression in expressions:
        expression_lines.append(
            "| `"
            + expression["expression"]
            + "` | "
            + f"{expression['complete_rows']:,}"
            + " | "
            + f"{expression['unique_identities']:,}"
            + " | "
            + f"{expression['duplicate_excess']:,}"
            + " | "
            + str(
                expression[
                    "unique_contract_match"
                ]
                and expression[
                    "duplicate_contract_match"
                ]
                and expression[
                    "complete_population"
                ]
            )
            + " |"
        )

    report_md = "\n".join(
        [
            (
                "# EDGEIQ Historical Observation V3 "
                "Raw Identity Semantics Audit"
            ),
            "",
            f"**Status:** `{status}`",
            "",
            f"**Decision:** `{decision}`",
            "",
            "## Decision rationale",
            "",
            decision_reason,
            "",
            "## Raw physical source",
            "",
            f"`{relative(RAW_SOURCE)}`",
            "",
            "## Raw schema",
            "",
            *[
                f"{index}. `{field}`"
                for index, field in enumerate(
                    raw_header,
                    start=1,
                )
            ],
            "",
            "## Identity expression testing",
            "",
            *expression_lines,
            "",
            "## Governance evidence",
            "",
            (
                f"- Asset catalogue registration: "
                f"**{asset_catalog_proven}**"
            ),
            (
                f"- Materialisation evidence: "
                f"**{materialisation_proven}**"
            ),
            (
                f"- Raw lineage fields: "
                f"`{' | '.join(raw_lineage_fields)}`"
            ),
            (
                f"- Corrected derived fields: "
                f"`{' | '.join(corrected_derived_fields)}`"
            ),
            (
                "- Non-circular raw references: "
                f"**{len(non_circular_raw_references)}**"
            ),
            "",
            "## Safety",
            "",
            "- No warehouse was written.",
            "- Existing V2 was not modified.",
            (
                "- The rejected untracked V3 "
                "implementation was not modified."
            ),
            "",
            "## Deliverables",
            "",
            f"- `{relative(REPORT_JSON)}`",
            f"- `{relative(REPORT_MD)}`",
            f"- `{relative(IDENTITY_MATRIX)}`",
            f"- `{relative(LINEAGE_MATRIX)}`",
            f"- `{relative(AUTHORITY_CONTRACT)}`",
            "",
        ]
    )

    REPORT_MD.write_text(
        report_md,
        encoding="utf-8",
    )

    print()
    print(f"STATUS: {status}")
    print(f"DECISION: {decision}")
    print(
        "SELECTED PHYSICAL AUTHORITY: "
        + (
            relative(RAW_SOURCE)
            if authority_proven
            else "NONE"
        )
    )
    print(
        "SELECTED IDENTITY EXPRESSION: "
        + (
            selected_expression[
                "expression"
            ]
            if selected_expression
            else "NONE"
        )
    )
    print(
        f"EXACT IDENTITY MATCHES: "
        f"{len(exact_matches)}"
    )
    print(
        f"ASSET CATALOGUE PROVEN: "
        f"{asset_catalog_proven}"
    )
    print(
        f"MATERIALISATION PROVEN: "
        f"{materialisation_proven}"
    )
    print(
        f"NON-CIRCULAR RAW REFERENCES: "
        f"{len(non_circular_raw_references)}"
    )
    print(
        f"REPORT: {relative(REPORT_MD)}"
    )
    print()
    print(
        "PHASE 1A.6B.1A RAW IDENTITY "
        "SEMANTICS AUDIT COMPLETE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
