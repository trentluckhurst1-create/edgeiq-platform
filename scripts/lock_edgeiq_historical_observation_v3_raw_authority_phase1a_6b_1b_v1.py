from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCK_ID = (
    "EDGEIQ_HISTORICAL_OBSERVATION_V3_RAW_AUTHORITY_"
    "SEMANTIC_LOCK_PHASE1A_6B_1B_V1"
)

PASS_STATUS = f"{LOCK_ID}_PASS"
FAIL_STATUS = f"{LOCK_ID}_FAIL"

EXPECTED_PHYSICAL_ROWS = 879_784
EXPECTED_UNIQUE_RAW_IDENTITIES = 879_695
EXPECTED_DUPLICATE_EXCESS = 89

ROOT = Path.cwd().absolute()

RAW_AUTHORITY = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
    / "eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e"
    / "canonical_performance_evidence.csv"
)

CORRECTED_FACTS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "performance-facts-corrected"
    / "eiq_performance_facts_v0_2_a0c3715ab506d19f9301d8a4"
    / "canonical_performance_facts_v0_2.csv"
)

IDENTITY_REPORT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "historical-observation-v3-raw-identity-semantics"
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "RAW_IDENTITY_SEMANTICS_REPORT.json"
)

ASSET_CATALOG = (
    RAW_AUTHORITY.parent
    / "asset_catalog.csv"
)

MATERIALISATION_CHECKS = (
    RAW_AUTHORITY.parent
    / "materialisation_checks.csv"
)

OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "historical-observation-v3-raw-authority-lock"
)

REPORT_JSON = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "RAW_AUTHORITY_SEMANTIC_LOCK_REPORT.json"
)

REPORT_MD = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "RAW_AUTHORITY_SEMANTIC_LOCK_REPORT.md"
)

EVIDENCE_CSV = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "RAW_AUTHORITY_SEMANTIC_EVIDENCE.csv"
)

AUTHORITY_CONTRACT = (
    OUTPUT_ROOT
    / "edgeiq_historical_observation_v3_"
      "physical_authority_contract_v1.json"
)

PROVIDER_IDENTITY_FIELDS = (
    "race_id",
    "provider_runner_id",
)

CANONICAL_IDENTITY_FIELDS = (
    "race_id",
    "horse_id",
)

REQUIRED_RAW_FIELDS = {
    "performance_id",
    "race_id",
    "horse_id",
    "source_evidence_id",
    "source_row_number",
    "provider_race_id",
    "provider_runner_id",
    "identity_method",
    "identity_quality_state",
    "identity_version",
    "performance_natural_key_version",
}

REQUIRED_CORRECTED_FIELDS = {
    "performance_fact_id",
    "benchmark_eligible",
    "quality_state",
}

EXCLUDED_SCRIPT_MARKERS = {
    "historical_observation_v3_authority_lineage",
    "historical_observation_v3_raw_identity_semantics",
    "historical_observation_v3_raw_authority",
    "historical_observation_v3_physical_authority_discovery",
    "historical_observation_v3_authority_phase1a_6b",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def csv_header(path: Path) -> list[str]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        return next(csv.reader(handle), [])


def read_small_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


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


def collect_repository_semantic_evidence() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    patterns = {
        "PROVIDER_RUNNER_ID": re.compile(
            r"\bprovider_runner_id\b",
            re.IGNORECASE,
        ),
        "CANONICAL_HORSE_ID": re.compile(
            r"\bhorse_id\b",
            re.IGNORECASE,
        ),
        "RAW_IDENTITY_LANGUAGE": re.compile(
            r"\b(raw identity|raw observation|"
            r"provider identity|provider runner|"
            r"source identity)\b",
            re.IGNORECASE,
        ),
        "CANONICAL_IDENTITY_LANGUAGE": re.compile(
            r"\b(canonical horse|canonical identity|"
            r"identity resolution|resolved horse|"
            r"horse resolution)\b",
            re.IGNORECASE,
        ),
    }

    for repository_path in git_paths():
        path = ROOT / repository_path

        if not path.exists():
            continue

        suffix = path.suffix.lower()

        if suffix not in {
            ".py",
            ".ps1",
            ".json",
            ".md",
            ".csv",
            ".txt",
        }:
            continue

        # Governance wording does not need to be searched
        # inside warehouse-sized CSV datasets.
        if (
            suffix == ".csv"
            and path.stat().st_size > 5_000_000
        ):
            continue

        lower_path = repository_path.lower()

        if any(
            marker in lower_path
            for marker in EXCLUDED_SCRIPT_MARKERS
        ):
            continue

        text = read_text(path)

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            classifications = [
                name
                for name, pattern in patterns.items()
                if pattern.search(line)
            ]

            if not classifications:
                continue

            if (
                "PROVIDER_RUNNER_ID"
                not in classifications
                and "CANONICAL_HORSE_ID"
                not in classifications
            ):
                continue

            rows.append(
                {
                    "repository_path": repository_path,
                    "line_number": line_number,
                    "classifications": "|".join(
                        classifications
                    ),
                    "line": line.strip()[:1000],
                }
            )

    return rows


def inspect_raw_semantics() -> dict[str, Any]:
    physical_rows = 0

    identity_method_counts: Counter[str] = Counter()
    identity_quality_counts: Counter[str] = Counter()
    identity_version_counts: Counter[str] = Counter()
    natural_key_version_counts: Counter[str] = Counter()

    provider_runner_blank = 0
    horse_id_blank = 0
    provider_horse_equal = 0
    provider_horse_different = 0

    with RAW_AUTHORITY.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            physical_rows += 1

            provider_runner_id = str(
                row.get(
                    "provider_runner_id",
                    "",
                )
            ).strip()

            horse_id = str(
                row.get(
                    "horse_id",
                    "",
                )
            ).strip()

            if not provider_runner_id:
                provider_runner_blank += 1

            if not horse_id:
                horse_id_blank += 1

            if (
                provider_runner_id
                and horse_id
            ):
                if provider_runner_id == horse_id:
                    provider_horse_equal += 1
                else:
                    provider_horse_different += 1

            identity_method_counts[
                str(
                    row.get(
                        "identity_method",
                        "",
                    )
                ).strip()
            ] += 1

            identity_quality_counts[
                str(
                    row.get(
                        "identity_quality_state",
                        "",
                    )
                ).strip()
            ] += 1

            identity_version_counts[
                str(
                    row.get(
                        "identity_version",
                        "",
                    )
                ).strip()
            ] += 1

            natural_key_version_counts[
                str(
                    row.get(
                        "performance_natural_key_version",
                        "",
                    )
                ).strip()
            ] += 1

            if physical_rows % 250_000 == 0:
                print(
                    f"  inspected {physical_rows:,} raw rows",
                    flush=True,
                )

    return {
        "physical_rows": physical_rows,
        "provider_runner_blank": provider_runner_blank,
        "horse_id_blank": horse_id_blank,
        "provider_horse_equal": (
            provider_horse_equal
        ),
        "provider_horse_different": (
            provider_horse_different
        ),
        "identity_method_counts": dict(
            identity_method_counts
        ),
        "identity_quality_counts": dict(
            identity_quality_counts
        ),
        "identity_version_counts": dict(
            identity_version_counts
        ),
        "natural_key_version_counts": dict(
            natural_key_version_counts
        ),
    }


def identity_expression(
    report: dict[str, Any],
    fields: tuple[str, str],
) -> dict[str, Any] | None:
    for expression in report.get(
        "identity_expressions",
        [],
    ):
        if expression.get("fields") == list(fields):
            return expression

    return None


def main() -> int:
    print(LOCK_ID)
    print("=" * len(LOCK_ID))
    print()

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    required_paths = (
        RAW_AUTHORITY,
        CORRECTED_FACTS,
        IDENTITY_REPORT,
        ASSET_CATALOG,
        MATERIALISATION_CHECKS,
    )

    missing = [
        relative(path)
        for path in required_paths
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Required evidence missing: "
            + ", ".join(missing)
        )

    raw_header = csv_header(
        RAW_AUTHORITY
    )

    corrected_header = csv_header(
        CORRECTED_FACTS
    )

    raw_header_set = set(raw_header)
    corrected_header_set = set(
        corrected_header
    )

    identity_report = load_json(
        IDENTITY_REPORT
    )

    provider_expression = identity_expression(
        identity_report,
        PROVIDER_IDENTITY_FIELDS,
    )

    canonical_expression = identity_expression(
        identity_report,
        CANONICAL_IDENTITY_FIELDS,
    )

    print("Inspecting raw semantic fields...", flush=True)

    raw_semantics = inspect_raw_semantics()

    print("Collecting non-circular repository evidence...", flush=True)

    semantic_evidence = (
        collect_repository_semantic_evidence()
    )

    asset_catalog = read_small_csv(
        ASSET_CATALOG
    )

    materialisation_checks = (
        read_small_csv(
            MATERIALISATION_CHECKS
        )
    )

    asset_text = json.dumps(
        asset_catalog,
        sort_keys=True,
    ).lower()

    materialisation_text = json.dumps(
        materialisation_checks,
        sort_keys=True,
    ).lower()

    provider_contract_match = bool(
        provider_expression
        and provider_expression.get(
            "complete_rows"
        ) == EXPECTED_PHYSICAL_ROWS
        and provider_expression.get(
            "unique_identities"
        ) == EXPECTED_UNIQUE_RAW_IDENTITIES
        and provider_expression.get(
            "duplicate_excess"
        ) == EXPECTED_DUPLICATE_EXCESS
        and provider_expression.get(
            "incomplete_rows"
        ) == 0
    )

    canonical_numeric_match = bool(
        canonical_expression
        and canonical_expression.get(
            "complete_rows"
        ) == EXPECTED_PHYSICAL_ROWS
        and canonical_expression.get(
            "unique_identities"
        ) == EXPECTED_UNIQUE_RAW_IDENTITIES
        and canonical_expression.get(
            "duplicate_excess"
        ) == EXPECTED_DUPLICATE_EXCESS
    )

    raw_schema_complete = (
        REQUIRED_RAW_FIELDS
        <= raw_header_set
    )

    corrected_schema_is_downstream = (
        REQUIRED_CORRECTED_FIELDS
        <= corrected_header_set
    )

    provider_identity_complete = (
        raw_semantics[
            "provider_runner_blank"
        ] == 0
    )

    canonical_identity_complete = (
        raw_semantics[
            "horse_id_blank"
        ] == 0
    )

    identity_processing_proven = bool(
        any(
            key.strip()
            for key in raw_semantics[
                "identity_method_counts"
            ]
        )
        and any(
            key.strip()
            for key in raw_semantics[
                "identity_version_counts"
            ]
        )
        and any(
            key.strip()
            for key in raw_semantics[
                "natural_key_version_counts"
            ]
        )
    )

    asset_registration_proven = (
        RAW_AUTHORITY.name.lower()
        in asset_text
    )

    materialisation_proven = bool(
        RAW_AUTHORITY.name.lower()
        in materialisation_text
        or str(EXPECTED_PHYSICAL_ROWS)
        in materialisation_text
    )

    semantic_field_distinction = bool(
        "provider_runner_id"
        in raw_header_set
        and "horse_id" in raw_header_set
        and "identity_method"
        in raw_header_set
        and "identity_version"
        in raw_header_set
    )

    checks = [
        {
            "check": "RAW_SOURCE_EXISTS",
            "result": "PASS",
            "detail": relative(
                RAW_AUTHORITY
            ),
        },
        {
            "check": "RAW_SCHEMA_COMPLETE",
            "result": (
                "PASS"
                if raw_schema_complete
                else "FAIL"
            ),
            "detail": (
                f"required={len(REQUIRED_RAW_FIELDS)}; "
                f"present={len(REQUIRED_RAW_FIELDS & raw_header_set)}"
            ),
        },
        {
            "check": "RAW_PHYSICAL_POPULATION",
            "result": (
                "PASS"
                if raw_semantics[
                    "physical_rows"
                ] == EXPECTED_PHYSICAL_ROWS
                else "FAIL"
            ),
            "detail": (
                f"actual={raw_semantics['physical_rows']}; "
                f"expected={EXPECTED_PHYSICAL_ROWS}"
            ),
        },
        {
            "check": "PROVIDER_RAW_KEY_CONTRACT",
            "result": (
                "PASS"
                if provider_contract_match
                else "FAIL"
            ),
            "detail": (
                "race_id + provider_runner_id; "
                f"unique={provider_expression.get('unique_identities') if provider_expression else None}; "
                f"duplicates={provider_expression.get('duplicate_excess') if provider_expression else None}"
            ),
        },
        {
            "check": "PROVIDER_IDENTITY_COMPLETE",
            "result": (
                "PASS"
                if provider_identity_complete
                else "FAIL"
            ),
            "detail": (
                f"blank_provider_runner_id="
                f"{raw_semantics['provider_runner_blank']}"
            ),
        },
        {
            "check": "CANONICAL_HORSE_ID_COMPLETE",
            "result": (
                "PASS"
                if canonical_identity_complete
                else "FAIL"
            ),
            "detail": (
                f"blank_horse_id="
                f"{raw_semantics['horse_id_blank']}"
            ),
        },
        {
            "check": "CANONICAL_KEY_NUMERIC_EQUIVALENCE",
            "result": (
                "PASS"
                if canonical_numeric_match
                else "FAIL"
            ),
            "detail": (
                "race_id + horse_id reproduces population "
                "but is classified as canonical rather than raw"
            ),
        },
        {
            "check": "PROVIDER_CANONICAL_FIELD_DISTINCTION",
            "result": (
                "PASS"
                if semantic_field_distinction
                else "FAIL"
            ),
            "detail": (
                "provider_runner_id and horse_id are stored "
                "as separate governed fields"
            ),
        },
        {
            "check": "IDENTITY_PROCESSING_METADATA",
            "result": (
                "PASS"
                if identity_processing_proven
                else "FAIL"
            ),
            "detail": (
                "identity_method, identity_version and "
                "performance_natural_key_version populated"
            ),
        },
        {
            "check": "RAW_ASSET_REGISTRATION",
            "result": (
                "PASS"
                if asset_registration_proven
                else "FAIL"
            ),
            "detail": relative(
                ASSET_CATALOG
            ),
        },
        {
            "check": "RAW_MATERIALISATION",
            "result": (
                "PASS"
                if materialisation_proven
                else "FAIL"
            ),
            "detail": relative(
                MATERIALISATION_CHECKS
            ),
        },
        {
            "check": "CORRECTED_FACTS_DOWNSTREAM_SCHEMA",
            "result": (
                "PASS"
                if corrected_schema_is_downstream
                else "FAIL"
            ),
            "detail": "|".join(
                sorted(
                    REQUIRED_CORRECTED_FIELDS
                    & corrected_header_set
                )
            ),
        },
    ]

    failures = [
        check
        for check in checks
        if check["result"] != "PASS"
    ]

    authority_locked = (
        not failures
    )

    if authority_locked:
        status = PASS_STATUS
        decision = (
            "LOCK_CANONICAL_PERFORMANCE_EVIDENCE_"
            "AS_PHYSICAL_AUTHORITY"
        )

        selected_authority = relative(
            RAW_AUTHORITY
        )

        selected_raw_identity = {
            "expression": (
                "race_id + provider_runner_id"
            ),
            "fields": [
                "race_id",
                "provider_runner_id",
            ],
            "physical_rows": (
                EXPECTED_PHYSICAL_ROWS
            ),
            "unique_raw_identities": (
                EXPECTED_UNIQUE_RAW_IDENTITIES
            ),
            "duplicate_excess": (
                EXPECTED_DUPLICATE_EXCESS
            ),
        }

        canonical_identity_note = {
            "expression": (
                "race_id + horse_id"
            ),
            "classification": (
                "CANONICAL_RESOLVED_IDENTITY"
            ),
            "source_authority_key": False,
            "numeric_population_equivalent": True,
        }

        rationale = (
            "The canonical performance evidence dataset is "
            "the registered and materialised raw warehouse "
            "asset. Its provider-side identity expression "
            "`race_id + provider_runner_id` exactly reproduces "
            "the governed 879,695 unique raw identities and "
            "duplicate excess of 89. `horse_id` is retained as "
            "EDGEIQ's canonical resolved horse identity and is "
            "not substituted for the provider raw key."
        )

    else:
        status = FAIL_STATUS
        decision = (
            "RAW_AUTHORITY_SEMANTIC_LOCK_FAILED"
        )
        selected_authority = None
        selected_raw_identity = None
        canonical_identity_note = None

        rationale = (
            "One or more required physical, population, "
            "identity, registration, materialisation or "
            "downstream-classification checks failed. "
            "No authority was locked."
        )

    with EVIDENCE_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "repository_path",
            "line_number",
            "classifications",
            "line",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            semantic_evidence
        )

    contract = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
            "PHYSICAL_AUTHORITY_CONTRACT_V1"
        ),
        "status": status,
        "decision": decision,
        "generated_at_utc": now_utc(),
        "selected_physical_authority": (
            selected_authority
        ),
        "selected_raw_identity": (
            selected_raw_identity
        ),
        "canonical_identity_semantics": (
            canonical_identity_note
        ),
        "rejected_as_source_authority": (
            relative(CORRECTED_FACTS)
            if authority_locked
            else None
        ),
        "population_contract": {
            "physical_rows": (
                EXPECTED_PHYSICAL_ROWS
            ),
            "unique_raw_identities": (
                EXPECTED_UNIQUE_RAW_IDENTITIES
            ),
            "duplicate_excess": (
                EXPECTED_DUPLICATE_EXCESS
            ),
        },
        "warehouse_build_authorised": (
            authority_locked
        ),
        "checks": checks,
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
        "lock_id": LOCK_ID,
        "status": status,
        "decision": decision,
        "decision_rationale": rationale,
        "generated_at_utc": now_utc(),
        "selected_physical_authority": (
            selected_authority
        ),
        "selected_raw_identity": (
            selected_raw_identity
        ),
        "canonical_identity_semantics": (
            canonical_identity_note
        ),
        "raw_semantics": raw_semantics,
        "provider_expression": (
            provider_expression
        ),
        "canonical_expression": (
            canonical_expression
        ),
        "raw_header": raw_header,
        "corrected_header": (
            corrected_header
        ),
        "asset_catalog": asset_catalog,
        "materialisation_checks": (
            materialisation_checks
        ),
        "semantic_evidence_count": (
            len(semantic_evidence)
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
        check_lines.append(
            f"| `{check['check']}` | "
            f"**{check['result']}** | "
            f"{str(check['detail']).replace('|', ', ')} |"
        )

    report_md = "\n".join(
        [
            (
                "# EDGEIQ Historical Observation V3 "
                "Raw Authority Semantic Lock"
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
            (
                "**Selected raw identity:** "
                + (
                    "`race_id + provider_runner_id`"
                    if selected_raw_identity
                    else "None"
                )
            ),
            "",
            "## Decision rationale",
            "",
            rationale,
            "",
            "## Identity semantics",
            "",
            (
                "- `provider_runner_id`: upstream provider "
                "runner identity."
            ),
            (
                "- `horse_id`: EDGEIQ canonical resolved "
                "horse identity."
            ),
            (
                "- The provider raw key and canonical key "
                "are numerically population-equivalent in "
                "this snapshot, but they are not "
                "semantically interchangeable."
            ),
            "",
            "## Governed population",
            "",
            (
                f"- Physical rows: "
                f"**{EXPECTED_PHYSICAL_ROWS:,}**"
            ),
            (
                f"- Unique raw identities: "
                f"**{EXPECTED_UNIQUE_RAW_IDENTITIES:,}**"
            ),
            (
                f"- Duplicate excess: "
                f"**{EXPECTED_DUPLICATE_EXCESS:,}**"
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
            "## Build authority",
            "",
            (
                "Phase 1A.6B replacement warehouse "
                + (
                    "construction is **authorised**."
                    if authority_locked
                    else "construction is **not authorised**."
                )
            ),
            "",
            "## Deliverables",
            "",
            f"- `{relative(REPORT_JSON)}`",
            f"- `{relative(REPORT_MD)}`",
            f"- `{relative(EVIDENCE_CSV)}`",
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
            selected_authority
            if selected_authority
            else "NONE"
        )
    )
    print(
        "SELECTED RAW IDENTITY: "
        + (
            "race_id + provider_runner_id"
            if selected_raw_identity
            else "NONE"
        )
    )
    print(
        "CANONICAL IDENTITY: "
        "race_id + horse_id"
    )
    print(
        f"PHYSICAL ROWS: "
        f"{raw_semantics['physical_rows']:,}"
    )
    print(
        f"UNIQUE RAW IDENTITIES: "
        f"{provider_expression.get('unique_identities') if provider_expression else None}"
    )
    print(
        f"DUPLICATE EXCESS: "
        f"{provider_expression.get('duplicate_excess') if provider_expression else None}"
    )
    print(
        f"SEMANTIC EVIDENCE LINES: "
        f"{len(semantic_evidence):,}"
    )
    print(
        "WAREHOUSE BUILD AUTHORISED: "
        f"{authority_locked}"
    )
    print(
        f"REPORT: {relative(REPORT_MD)}"
    )
    print()
    print(
        "PHASE 1A.6B.1B RAW AUTHORITY "
        "SEMANTIC LOCK COMPLETE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
