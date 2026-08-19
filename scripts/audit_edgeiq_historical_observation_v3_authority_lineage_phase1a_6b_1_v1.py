from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = (
    "EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_LINEAGE_"
    "PHASE1A_6B_1_V1"
)

PASS_STATUS = f"{AUDIT_ID}_PASS"
FAIL_STATUS = f"{AUDIT_ID}_FAIL"

EXPECTED_ROWS = 879_784
EXPECTED_UNIQUE_KEYS = 879_695
EXPECTED_DUPLICATE_EXCESS = 89

ROOT = Path.cwd().absolute()

RAW_CANDIDATE = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
    / "eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e"
    / "canonical_performance_evidence.csv"
)

CORRECTED_CANDIDATE = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "performance-facts-corrected"
    / "eiq_performance_facts_v0_2_a0c3715ab506d19f9301d8a4"
    / "canonical_performance_facts_v0_2.csv"
)

RAW_ASSET_CATALOG = RAW_CANDIDATE.parent / "asset_catalog.csv"
RAW_CHECKS = RAW_CANDIDATE.parent / "materialisation_checks.csv"

CORRECTED_ROOT = CORRECTED_CANDIDATE.parent

OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "historical-observation-v3-authority-lineage"
)

REPORT_JSON = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "AUTHORITY_LINEAGE_REPORT.json"
)

REPORT_MD = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "AUTHORITY_LINEAGE_REPORT.md"
)

SCRIPT_MATRIX = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "AUTHORITY_LINEAGE_SCRIPT_MATRIX.csv"
)

SCHEMA_MATRIX = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "AUTHORITY_LINEAGE_SCHEMA_MATRIX.csv"
)

DECISION_CONTRACT = (
    OUTPUT_ROOT
    / "edgeiq_historical_observation_v3_"
      "authority_lineage_contract.json"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def repository_paths() -> list[str]:
    result = run_git(
        "ls-files",
        "-co",
        "--exclude-standard",
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


def read_text(path: Path) -> str:
    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ):
        try:
            return path.read_text(
                encoding=encoding
            )
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
                return next(
                    csv.reader(handle),
                    [],
                )
        except UnicodeDecodeError:
            continue

    with path.open(
        "r",
        encoding="cp1252",
        errors="replace",
        newline="",
    ) as handle:
        return next(
            csv.reader(handle),
            [],
        )


def count_rows(path: Path) -> int:
    count = 0

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.reader(handle)
        next(reader, None)

        for _ in reader:
            count += 1

            if count % 250_000 == 0:
                print(
                    f"  counted {count:,} rows: "
                    f"{relative(path)}",
                    flush=True,
                )

    return count


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def normalise(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        value.strip().lower(),
    ).strip("_")


def schema_classification(
    path: Path,
    header: list[str],
) -> dict[str, Any]:
    fields = {
        normalise(field): field
        for field in header
    }

    source_lineage_aliases = {
        "source_file",
        "source_path",
        "source_row_number",
        "source_record_id",
        "source_system",
        "source_type",
        "source_url",
        "source_race_id",
        "source_runner_id",
        "graphql_race_id",
        "graphql_runner_id",
    }

    derived_aliases = {
        "corrected_time_seconds",
        "corrected_seconds",
        "quality_state",
        "quality_reason",
        "canonical_horse_id",
        "performance_fact_id",
        "time_unit_state",
        "normalised_time",
        "benchmark_eligible",
    }

    raw_identity_aliases = {
        "race_id",
        "runner_id",
    }

    lineage_fields = sorted(
        fields[name]
        for name in source_lineage_aliases
        if name in fields
    )

    derived_fields = sorted(
        fields[name]
        for name in derived_aliases
        if name in fields
    )

    identity_fields = sorted(
        fields[name]
        for name in raw_identity_aliases
        if name in fields
    )

    path_text = relative(path).lower()

    raw_path_class = (
        "/warehouse/raw/" in f"/{path_text}"
    )

    corrected_path_class = (
        "/performance-facts-corrected/"
        in f"/{path_text}"
    )

    return {
        "field_count": len(header),
        "header": header,
        "source_lineage_fields": lineage_fields,
        "derived_fields": derived_fields,
        "raw_identity_fields": identity_fields,
        "raw_identity_pair_present": (
            "race_id" in fields
            and "runner_id" in fields
        ),
        "raw_path_class": raw_path_class,
        "corrected_path_class": corrected_path_class,
    }


def inspect_small_csv(path: Path) -> dict[str, Any]:
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
                rows = list(csv.DictReader(handle))

            return {
                "exists": True,
                "header": (
                    list(rows[0].keys())
                    if rows
                    else csv_header(path)
                ),
                "rows": rows,
            }

        except UnicodeDecodeError:
            continue

    return {
        "exists": True,
        "header": csv_header(path),
        "rows": [],
    }


def classify_script_reference(
    script_path: Path,
    text: str,
) -> dict[str, Any]:
    raw_name = RAW_CANDIDATE.name
    corrected_name = CORRECTED_CANDIDATE.name

    raw_full = relative(RAW_CANDIDATE)
    corrected_full = relative(CORRECTED_CANDIDATE)

    references_raw = (
        raw_name in text
        or raw_full in text.replace("\\", "/")
    )

    references_corrected = (
        corrected_name in text
        or corrected_full in text.replace("\\", "/")
    )

    lower = text.lower()

    write_markers = (
        "csv.writer",
        "dictwriter",
        "writerow",
        "write_text",
        "to_csv",
        "replace(",
        "shutil.copy",
        "copyfile",
    )

    read_markers = (
        "csv.reader",
        "dictreader",
        "read_csv",
        "open(",
    )

    writes_files = any(
        marker in lower
        for marker in write_markers
    )

    reads_files = any(
        marker in lower
        for marker in read_markers
    )

    raw_position = min(
        (
            position
            for position in (
                text.find(raw_name),
                text.find(raw_full),
            )
            if position >= 0
        ),
        default=-1,
    )

    corrected_position = min(
        (
            position
            for position in (
                text.find(corrected_name),
                text.find(corrected_full),
            )
            if position >= 0
        ),
        default=-1,
    )

    raw_before_corrected = (
        raw_position >= 0
        and corrected_position >= 0
        and raw_position < corrected_position
    )

    correction_language = bool(
        re.search(
            r"\b(correct|corrected|normalis|quality|"
            r"unit semantics|time unit)\b",
            lower,
        )
    )

    raw_language = bool(
        re.search(
            r"\b(raw evidence|source evidence|"
            r"materialis|graphql|source row)\b",
            lower,
        )
    )

    return {
        "script_path": relative(script_path),
        "references_raw_candidate": references_raw,
        "references_corrected_candidate": references_corrected,
        "references_both": (
            references_raw
            and references_corrected
        ),
        "raw_reference_before_corrected": (
            raw_before_corrected
        ),
        "contains_read_markers": reads_files,
        "contains_write_markers": writes_files,
        "contains_raw_language": raw_language,
        "contains_correction_language": (
            correction_language
        ),
    }


def main() -> int:
    print(AUDIT_ID)
    print("=" * len(AUDIT_ID))
    print()

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    missing = [
        relative(path)
        for path in (
            RAW_CANDIDATE,
            CORRECTED_CANDIDATE,
        )
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Required candidate files missing: "
            + ", ".join(missing)
        )

    print("Inspecting candidate schemas...", flush=True)

    raw_header = csv_header(RAW_CANDIDATE)
    corrected_header = csv_header(
        CORRECTED_CANDIDATE
    )

    raw_schema = schema_classification(
        RAW_CANDIDATE,
        raw_header,
    )

    corrected_schema = schema_classification(
        CORRECTED_CANDIDATE,
        corrected_header,
    )

    print("Verifying physical row counts...", flush=True)

    raw_rows = count_rows(RAW_CANDIDATE)
    corrected_rows = count_rows(
        CORRECTED_CANDIDATE
    )

    print("Calculating file hashes...", flush=True)

    raw_hash = file_sha256(RAW_CANDIDATE)
    corrected_hash = file_sha256(
        CORRECTED_CANDIDATE
    )

    asset_catalog = inspect_small_csv(
        RAW_ASSET_CATALOG
    )

    materialisation_checks = inspect_small_csv(
        RAW_CHECKS
    )

    repository = repository_paths()
    script_rows: list[dict[str, Any]] = []

    print("Tracing producer and consumer scripts...", flush=True)

    for repository_path in repository:
        path = ROOT / repository_path

        if (
            not path.exists()
            or path.suffix.lower()
            not in {".py", ".ps1"}
        ):
            continue

        text = read_text(path)

        if (
            RAW_CANDIDATE.name not in text
            and CORRECTED_CANDIDATE.name
            not in text
            and relative(RAW_CANDIDATE)
            not in text.replace("\\", "/")
            and relative(CORRECTED_CANDIDATE)
            not in text.replace("\\", "/")
        ):
            continue

        script_rows.append(
            classify_script_reference(
                path,
                text,
            )
        )

    script_rows.sort(
        key=lambda item: item[
            "script_path"
        ].lower()
    )

    dual_reference_scripts = [
        item
        for item in script_rows
        if item["references_both"]
    ]

    correction_pipeline_scripts = [
        item
        for item in dual_reference_scripts
        if item[
            "contains_correction_language"
        ]
        and item[
            "contains_read_markers"
        ]
        and item[
            "contains_write_markers"
        ]
    ]

    raw_catalog_text = json.dumps(
        asset_catalog,
        sort_keys=True,
    ).lower()

    raw_checks_text = json.dumps(
        materialisation_checks,
        sort_keys=True,
    ).lower()

    raw_catalog_proven = (
        RAW_CANDIDATE.name.lower()
        in raw_catalog_text
    )

    raw_materialisation_proven = (
        RAW_CANDIDATE.name.lower()
        in raw_checks_text
        or str(EXPECTED_ROWS)
        in raw_checks_text
    )

    raw_population_match = (
        raw_rows == EXPECTED_ROWS
    )

    corrected_population_match = (
        corrected_rows == EXPECTED_ROWS
    )

    raw_is_distinct_file = (
        raw_hash != corrected_hash
    )

    raw_identity_present = raw_schema[
        "raw_identity_pair_present"
    ]

    raw_has_lineage = bool(
        raw_schema[
            "source_lineage_fields"
        ]
    )

    corrected_has_derived_fields = bool(
        corrected_schema[
            "derived_fields"
        ]
    )

    checks = [
        {
            "check": "RAW_PATH_CLASSIFICATION",
            "result": (
                "PASS"
                if raw_schema["raw_path_class"]
                else "FAIL"
            ),
            "detail": relative(RAW_CANDIDATE),
        },
        {
            "check": "CORRECTED_PATH_CLASSIFICATION",
            "result": (
                "PASS"
                if corrected_schema[
                    "corrected_path_class"
                ]
                else "FAIL"
            ),
            "detail": relative(
                CORRECTED_CANDIDATE
            ),
        },
        {
            "check": "RAW_POPULATION_MATCH",
            "result": (
                "PASS"
                if raw_population_match
                else "FAIL"
            ),
            "detail": (
                f"actual={raw_rows}; "
                f"expected={EXPECTED_ROWS}"
            ),
        },
        {
            "check": "CORRECTED_POPULATION_MATCH",
            "result": (
                "PASS"
                if corrected_population_match
                else "FAIL"
            ),
            "detail": (
                f"actual={corrected_rows}; "
                f"expected={EXPECTED_ROWS}"
            ),
        },
        {
            "check": "RAW_IDENTITY_PRESENT",
            "result": (
                "PASS"
                if raw_identity_present
                else "FAIL"
            ),
            "detail": "|".join(
                raw_schema[
                    "raw_identity_fields"
                ]
            ),
        },
        {
            "check": "RAW_LINEAGE_PRESENT",
            "result": (
                "PASS"
                if raw_has_lineage
                else "FAIL"
            ),
            "detail": "|".join(
                raw_schema[
                    "source_lineage_fields"
                ]
            ),
        },
        {
            "check": "CORRECTED_DERIVATION_PRESENT",
            "result": (
                "PASS"
                if corrected_has_derived_fields
                else "NOT_VERIFIED"
            ),
            "detail": "|".join(
                corrected_schema[
                    "derived_fields"
                ]
            ),
        },
        {
            "check": "RAW_ASSET_CATALOG_REFERENCE",
            "result": (
                "PASS"
                if raw_catalog_proven
                else "NOT_VERIFIED"
            ),
            "detail": relative(
                RAW_ASSET_CATALOG
            ),
        },
        {
            "check": "RAW_MATERIALISATION_REFERENCE",
            "result": (
                "PASS"
                if raw_materialisation_proven
                else "NOT_VERIFIED"
            ),
            "detail": relative(
                RAW_CHECKS
            ),
        },
        {
            "check": "PIPELINE_LINEAGE_SCRIPT",
            "result": (
                "PASS"
                if correction_pipeline_scripts
                else "NOT_VERIFIED"
            ),
            "detail": "|".join(
                item["script_path"]
                for item in correction_pipeline_scripts
            ),
        },
        {
            "check": "FILES_ARE_NOT_BYTE_IDENTICAL",
            "result": (
                "PASS"
                if raw_is_distinct_file
                else "FAIL"
            ),
            "detail": (
                f"raw_sha256={raw_hash}; "
                f"corrected_sha256={corrected_hash}"
            ),
        },
    ]

    critical_failures = [
        check
        for check in checks
        if check["result"] == "FAIL"
    ]

    authority_proven = bool(
        not critical_failures
        and raw_population_match
        and corrected_population_match
        and raw_identity_present
        and raw_has_lineage
        and raw_schema["raw_path_class"]
        and corrected_schema[
            "corrected_path_class"
        ]
        and raw_is_distinct_file
        and (
            raw_catalog_proven
            or raw_materialisation_proven
            or correction_pipeline_scripts
        )
    )

    if authority_proven:
        status = PASS_STATUS
        decision = "LOCK_RAW_EVIDENCE_AS_AUTHORITY"
        selected_authority = relative(
            RAW_CANDIDATE
        )

        rationale = (
            "The raw canonical performance evidence dataset "
            "matches the governed population, preserves raw "
            "identity and lineage, and is architecturally "
            "upstream of the corrected performance-fact "
            "dataset. The corrected dataset is downstream "
            "enrichment and cannot be the observation source "
            "authority."
        )

    else:
        status = FAIL_STATUS
        decision = "LINEAGE_NOT_YET_PROVEN"
        selected_authority = None

        rationale = (
            "The two population-matching datasets could not "
            "be distinguished with sufficient physical "
            "lineage evidence. No authority has been locked."
        )

    with SCRIPT_MATRIX.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "script_path",
            "references_raw_candidate",
            "references_corrected_candidate",
            "references_both",
            "raw_reference_before_corrected",
            "contains_read_markers",
            "contains_write_markers",
            "contains_raw_language",
            "contains_correction_language",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(script_rows)

    with SCHEMA_MATRIX.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "candidate_class",
            "repository_path",
            "physical_rows",
            "size_bytes",
            "sha256",
            "field_count",
            "raw_identity_pair_present",
            "source_lineage_fields",
            "derived_fields",
            "raw_path_class",
            "corrected_path_class",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()

        writer.writerow(
            {
                "candidate_class": "RAW_EVIDENCE",
                "repository_path": relative(
                    RAW_CANDIDATE
                ),
                "physical_rows": raw_rows,
                "size_bytes": (
                    RAW_CANDIDATE.stat().st_size
                ),
                "sha256": raw_hash,
                "field_count": raw_schema[
                    "field_count"
                ],
                "raw_identity_pair_present": (
                    raw_schema[
                        "raw_identity_pair_present"
                    ]
                ),
                "source_lineage_fields": "|".join(
                    raw_schema[
                        "source_lineage_fields"
                    ]
                ),
                "derived_fields": "|".join(
                    raw_schema[
                        "derived_fields"
                    ]
                ),
                "raw_path_class": raw_schema[
                    "raw_path_class"
                ],
                "corrected_path_class": (
                    raw_schema[
                        "corrected_path_class"
                    ]
                ),
            }
        )

        writer.writerow(
            {
                "candidate_class": (
                    "CORRECTED_PERFORMANCE_FACT"
                ),
                "repository_path": relative(
                    CORRECTED_CANDIDATE
                ),
                "physical_rows": corrected_rows,
                "size_bytes": (
                    CORRECTED_CANDIDATE.stat().st_size
                ),
                "sha256": corrected_hash,
                "field_count": corrected_schema[
                    "field_count"
                ],
                "raw_identity_pair_present": (
                    corrected_schema[
                        "raw_identity_pair_present"
                    ]
                ),
                "source_lineage_fields": "|".join(
                    corrected_schema[
                        "source_lineage_fields"
                    ]
                ),
                "derived_fields": "|".join(
                    corrected_schema[
                        "derived_fields"
                    ]
                ),
                "raw_path_class": corrected_schema[
                    "raw_path_class"
                ],
                "corrected_path_class": (
                    corrected_schema[
                        "corrected_path_class"
                    ]
                ),
            }
        )

    contract = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
            "PHYSICAL_AUTHORITY_CONTRACT_V1"
        ),
        "status": status,
        "decision": decision,
        "generated_at_utc": now_utc(),
        "selected_authority": (
            selected_authority
        ),
        "rejected_as_source_authority": (
            relative(CORRECTED_CANDIDATE)
            if authority_proven
            else None
        ),
        "population_contract": {
            "physical_rows": EXPECTED_ROWS,
            "unique_raw_identities": (
                EXPECTED_UNIQUE_KEYS
            ),
            "duplicate_excess": (
                EXPECTED_DUPLICATE_EXCESS
            ),
        },
        "warehouse_build_authorised": (
            authority_proven
        ),
        "checks": checks,
    }

    DECISION_CONTRACT.write_text(
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
        "decision_rationale": rationale,
        "generated_at_utc": now_utc(),
        "selected_authority": (
            selected_authority
        ),
        "raw_candidate": {
            "repository_path": relative(
                RAW_CANDIDATE
            ),
            "rows": raw_rows,
            "size_bytes": (
                RAW_CANDIDATE.stat().st_size
            ),
            "sha256": raw_hash,
            "schema": raw_schema,
        },
        "corrected_candidate": {
            "repository_path": relative(
                CORRECTED_CANDIDATE
            ),
            "rows": corrected_rows,
            "size_bytes": (
                CORRECTED_CANDIDATE.stat().st_size
            ),
            "sha256": corrected_hash,
            "schema": corrected_schema,
        },
        "asset_catalog": asset_catalog,
        "materialisation_checks": (
            materialisation_checks
        ),
        "script_references": script_rows,
        "correction_pipeline_scripts": (
            correction_pipeline_scripts
        ),
        "checks": checks,
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

    check_lines = [
        "| Check | Result | Detail |",
        "|---|---:|---|",
    ]

    for check in checks:
        detail = (
            str(check["detail"])
            .replace("|", ", ")
            .replace("\n", " ")
        )

        check_lines.append(
            f"| `{check['check']}` | "
            f"**{check['result']}** | "
            f"{detail} |"
        )

    report_md = "\n".join(
        [
            (
                "# EDGEIQ Historical Observation V3 "
                "Authority Lineage Audit"
            ),
            "",
            f"**Status:** `{status}`",
            "",
            f"**Decision:** `{decision}`",
            "",
            (
                "**Selected physical authority:** "
                + (
                    f"`{selected_authority}`"
                    if selected_authority
                    else "None"
                )
            ),
            "",
            "## Decision rationale",
            "",
            rationale,
            "",
            "## Candidate classification",
            "",
            (
                f"- Raw evidence candidate: "
                f"`{relative(RAW_CANDIDATE)}`"
            ),
            (
                f"- Corrected fact candidate: "
                f"`{relative(CORRECTED_CANDIDATE)}`"
            ),
            "",
            "## Population",
            "",
            f"- Raw evidence rows: **{raw_rows:,}**",
            (
                f"- Corrected fact rows: "
                f"**{corrected_rows:,}**"
            ),
            (
                f"- Governed expected rows: "
                f"**{EXPECTED_ROWS:,}**"
            ),
            "",
            "## Governance checks",
            "",
            *check_lines,
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
            f"- `{relative(SCRIPT_MATRIX)}`",
            f"- `{relative(SCHEMA_MATRIX)}`",
            f"- `{relative(DECISION_CONTRACT)}`",
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
            selected_authority
            if selected_authority
            else "NONE"
        )
    )
    print(
        f"RAW ROWS: {raw_rows:,}"
    )
    print(
        f"CORRECTED ROWS: {corrected_rows:,}"
    )
    print(
        f"PIPELINE SCRIPTS: "
        f"{len(correction_pipeline_scripts)}"
    )
    print(
        f"REPORT: {relative(REPORT_MD)}"
    )
    print()
    print(
        "PHASE 1A.6B.1 AUTHORITY LINEAGE "
        "AUDIT COMPLETE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
