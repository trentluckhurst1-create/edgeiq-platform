from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_AUDIT_V1"
PASS_STATUS = f"{AUDIT_ID}_PASS"
FAIL_STATUS = f"{AUDIT_ID}_FAIL"

ROOT = Path.cwd().absolute()

BUILDER = ROOT / "scripts" / "rebuild_edgeiq_historical_observation_warehouse_v3.py"

V3_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-observation-warehouse-v3"
)

EXISTING_AUDIT = (
    V3_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_WAREHOUSE_V3_AUDIT.json"
)

EXISTING_CONTRACT = (
    V3_ROOT
    / "edgeiq_historical_observation_warehouse_v3_contract.json"
)

SOURCE_SUMMARY = (
    V3_ROOT
    / "edgeiq_historical_observation_v3_source_summary.csv"
)

CANDIDATE = (
    V3_ROOT
    / "edgeiq_historical_observation_warehouse_v3_CANDIDATE.csv"
)

OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "historical-observation-v3-audit"
)

REPORT_JSON = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.json"
)

REPORT_MD = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_BUILDER_PHASE1A_6A_REPORT.md"
)

SOURCE_MATRIX = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_SOURCE_ADMISSION_MATRIX.csv"
)

GOVERNANCE_MATRIX = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_GOVERNANCE_MATRIX.csv"
)

RECOMMENDATION_MD = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_RECOMMENDATION.md"
)

EXPECTED_PHYSICAL_ROWS = 879_784
EXPECTED_UNIQUE_RAW_IDENTITIES = 879_695
EXPECTED_DUPLICATE_EXCESS = 89


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def relative(path: Path) -> str:
    try:
        return path.absolute().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="cp1252", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(read_text(path))
    except (json.JSONDecodeError, OSError):
        return {}

    return payload if isinstance(payload, dict) else {}


def flatten_json(
    value: Any,
    prefix: str = "",
) -> dict[str, Any]:
    flattened: dict[str, Any] = {}

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_json(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            flattened.update(flatten_json(child, child_prefix))
    else:
        flattened[prefix] = value

    return flattened


def numeric_lookup(
    flattened: dict[str, Any],
    aliases: tuple[str, ...],
) -> tuple[str, int] | None:
    normalised_aliases = {
        re.sub(r"[^a-z0-9]+", "", alias.lower())
        for alias in aliases
    }

    for key, value in flattened.items():
        normalised_key = re.sub(r"[^a-z0-9]+", "", key.lower())

        if not any(alias in normalised_key for alias in normalised_aliases):
            continue

        if isinstance(value, bool):
            continue

        if isinstance(value, int):
            return key, value

        if isinstance(value, float) and value.is_integer():
            return key, int(value)

        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if re.fullmatch(r"-?\d+", cleaned):
                return key, int(cleaned)

    return None


def candidate_header() -> list[str]:
    if not CANDIDATE.exists():
        return []

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with CANDIDATE.open(
                "r",
                encoding=encoding,
                errors="strict",
                newline="",
            ) as handle:
                return next(csv.reader(handle), [])
        except UnicodeDecodeError:
            continue

    with CANDIDATE.open(
        "r",
        encoding="cp1252",
        errors="replace",
        newline="",
    ) as handle:
        return next(csv.reader(handle), [])


def load_source_summary() -> list[dict[str, str]]:
    if not SOURCE_SUMMARY.exists():
        return []

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with SOURCE_SUMMARY.open(
                "r",
                encoding=encoding,
                errors="strict",
                newline="",
            ) as handle:
                return list(csv.DictReader(handle))
        except UnicodeDecodeError:
            continue

    with SOURCE_SUMMARY.open(
        "r",
        encoding="cp1252",
        errors="replace",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def classify_source(source_path: str) -> tuple[str, str]:
    text = source_path.replace("\\", "/").lower()

    prohibited_rules = (
        ("monthly", "REJECT_MONTHLY"),
        ("legacy", "REJECT_LEGACY"),
        ("sectional", "REJECT_SECTIONAL"),
        ("sectionals", "REJECT_SECTIONAL"),
        ("speed", "REJECT_SPEED"),
        ("upcoming", "REJECT_LIVE_OR_UPCOMING"),
        ("live", "REJECT_LIVE_OR_UPCOMING"),
        ("checkpoint", "REJECT_CHECKPOINT"),
        ("backup", "REJECT_BACKUP"),
        ("candidate", "REJECT_CANDIDATE"),
        ("temporary", "REJECT_TEMPORARY"),
        ("/tmp/", "REJECT_TEMPORARY"),
        ("/temp/", "REJECT_TEMPORARY"),
    )

    for marker, classification in prohibited_rules:
        if marker in text:
            return classification, marker

    if "graphql" in text and "consolidated" in text:
        return "APPROVED_AUTHORITY_CANDIDATE", "graphql+consolidated"

    if "graphql" in text:
        return "UNAPPROVED_GRAPHQL_OR_UNKNOWN", "graphql without consolidated marker"

    if "racingcom" in text or "racing.com" in text or "racing_com" in text:
        return "UNAPPROVED_RACINGCOM_OR_UNKNOWN", "broad Racing.com source"

    return "UNKNOWN", "no governed authority classification"


def ast_findings(source: str) -> dict[str, Any]:
    tree = ast.parse(source, filename=str(BUILDER))

    calls: list[dict[str, Any]] = []
    function_names: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_names.append(node.name)

        if not isinstance(node, ast.Call):
            continue

        function_text = ast.unparse(node.func)

        calls.append(
            {
                "line": getattr(node, "lineno", None),
                "function": function_text,
                "expression": ast.unparse(node),
            }
        )

    recursive_globs = [
        item
        for item in calls
        if item["function"].endswith(".rglob")
    ]

    glob_calls = [
        item
        for item in calls
        if item["function"].endswith(".glob")
    ]

    observation_id_calls = [
        item
        for item in calls
        if item["function"] == "obs_id"
        or item["function"].endswith(".obs_id")
    ]

    return {
        "functions": sorted(set(function_names)),
        "recursive_glob_calls": recursive_globs,
        "glob_calls": glob_calls,
        "observation_id_calls": observation_id_calls,
    }


def add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    requirement: str,
    result: str,
    evidence: str,
    severity: str,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "requirement": requirement,
            "result": result,
            "severity": severity,
            "evidence": evidence,
        }
    )


def main() -> int:
    print(AUDIT_ID)
    print("=" * len(AUDIT_ID))

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    if not BUILDER.exists():
        raise FileNotFoundError(BUILDER)

    source = read_text(BUILDER)
    findings = ast_findings(source)

    existing_audit = load_json(EXISTING_AUDIT)
    existing_contract = load_json(EXISTING_CONTRACT)
    flattened_audit = flatten_json(existing_audit)

    source_rows = load_source_summary()
    source_matrix_rows: list[dict[str, Any]] = []

    classification_counts: Counter[str] = Counter()

    for row in source_rows:
        source_path = (
            row.get("source_path")
            or row.get("path")
            or row.get("source_file")
            or ""
        ).strip()

        classification, evidence_marker = classify_source(source_path)
        classification_counts[classification] += 1

        source_matrix_rows.append(
            {
                "source_path": source_path,
                "classification": classification,
                "classification_evidence": evidence_marker,
                "rows_scanned": row.get("rows_scanned", ""),
                "resolved_rows": row.get("resolved_rows", ""),
                "collision_rows": row.get("collision_rows", ""),
                "unresolved_no_key_rows": row.get(
                    "unresolved_no_key_rows",
                    "",
                ),
                "unresolved_no_crosswalk_rows": row.get(
                    "unresolved_no_crosswalk_rows",
                    "",
                ),
            }
        )

    candidate_fields = candidate_header()
    checks: list[dict[str, Any]] = []

    recursive_source_scan = any(
        "PUBLIC.rglob" in item["expression"]
        or "public" in item["expression"].lower()
        for item in findings["recursive_glob_calls"]
    )

    explicit_consolidated_allowlist = bool(
        re.search(
            r"(consolidated).{0,120}(allow|admit|authority|source)",
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )
        or re.search(
            r"(allow|admit|authority|source).{0,120}(consolidated)",
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )

    explicit_prohibited_exclusions = {
        label: bool(re.search(pattern, source, flags=re.IGNORECASE))
        for label, pattern in {
            "monthly": r"monthly",
            "legacy": r"legacy",
            "speed": r"speed",
            "sectional": r"sectional",
            "live": r"\blive\b",
            "checkpoint": r"checkpoint",
        }.items()
    }

    prohibited_classifications = {
        key: count
        for key, count in classification_counts.items()
        if key.startswith("REJECT_")
    }

    unknown_or_unapproved = {
        key: count
        for key, count in classification_counts.items()
        if key.startswith("UNKNOWN")
        or key.startswith("UNAPPROVED")
    }

    add_check(
        checks,
        "A01",
        "Builder must exist and remain inspectable without execution.",
        "PASS",
        relative(BUILDER),
        "CRITICAL",
    )

    if recursive_source_scan and not explicit_consolidated_allowlist:
        add_check(
            checks,
            "A02",
            "Source admission must use the approved consolidated GraphQL authority only.",
            "FAIL",
            (
                "Builder uses a recursive public/data CSV discovery rule "
                "without an explicit consolidated-authority allow-list."
            ),
            "CRITICAL",
        )
    elif explicit_consolidated_allowlist:
        add_check(
            checks,
            "A02",
            "Source admission must use the approved consolidated GraphQL authority only.",
            "PASS",
            "Explicit consolidated source authority logic detected.",
            "CRITICAL",
        )
    else:
        add_check(
            checks,
            "A02",
            "Source admission must use the approved consolidated GraphQL authority only.",
            "PARTIAL",
            "No conclusive source authority rule was detected.",
            "CRITICAL",
        )

    exclusions_present = all(explicit_prohibited_exclusions.values())

    add_check(
        checks,
        "A03",
        "Monthly, legacy, speed, sectional, live and checkpoint sources must be explicitly excluded.",
        "PASS" if exclusions_present else "FAIL",
        json.dumps(
            explicit_prohibited_exclusions,
            sort_keys=True,
        ),
        "CRITICAL",
    )

    if source_rows:
        if prohibited_classifications:
            source_result = "FAIL"
        elif unknown_or_unapproved:
            source_result = "PARTIAL"
        else:
            source_result = "PASS"

        add_check(
            checks,
            "A04",
            "Previously admitted sources must conform to the approved source authority.",
            source_result,
            (
                f"Source files in summary: {len(source_rows)}; "
                f"classifications: {dict(sorted(classification_counts.items()))}"
            ),
            "CRITICAL",
        )
    else:
        add_check(
            checks,
            "A04",
            "Previously admitted sources must conform to the approved source authority.",
            "NOT_VERIFIED",
            "Existing source summary was not available or contained no rows.",
            "CRITICAL",
        )

    identity_fields_present = {
        "source_path",
        "source_row_number",
        "source_file_sha256",
        "horse_key",
        "canonical_horse_id",
        "identity_status",
        "identity_evidence_sha256",
    }.issubset(set(candidate_fields))

    add_check(
        checks,
        "A05",
        "Every admitted observation must preserve row-level source and identity lineage.",
        "PASS" if identity_fields_present else "FAIL",
        (
            "Candidate fields inspected from header only: "
            + ", ".join(candidate_fields)
        ),
        "HIGH",
    )

    no_fuzzy_matching = "no fuzzy matching" in source.lower()

    add_check(
        checks,
        "A06",
        "Identity resolution must remain deterministic and prohibit fuzzy matching.",
        "PASS" if no_fuzzy_matching else "PARTIAL",
        (
            "Builder contract declares no fuzzy matching."
            if no_fuzzy_matching
            else "No explicit no-fuzzy governance declaration detected."
        ),
        "HIGH",
    )

    observation_id_defined = bool(
        re.search(r"def\s+obs_id\s*\(", source)
    )
    observation_id_used = bool(findings["observation_id_calls"])

    add_check(
        checks,
        "A07",
        "Observation identifiers must be generated deterministically.",
        (
            "PASS"
            if observation_id_defined and observation_id_used
            else "FAIL"
        ),
        (
            f"obs_id defined={observation_id_defined}; "
            f"obs_id calls={len(findings['observation_id_calls'])}"
        ),
        "HIGH",
    )

    physical_result = numeric_lookup(
        flattened_audit,
        (
            "physical_rows",
            "candidate_rows",
            "rows_written",
            "admitted_rows",
            "total_rows",
            "rows_replayed",
        ),
    )

    unique_result = numeric_lookup(
        flattened_audit,
        (
            "unique_raw_identities",
            "unique_identities",
            "unique_observation_id",
            "unique_observations",
        ),
    )

    duplicate_result = numeric_lookup(
        flattened_audit,
        (
            "duplicate_excess",
            "duplicate_rows",
            "duplicate_identity_rows",
            "duplicate_groups",
        ),
    )

    if physical_result is None:
        add_check(
            checks,
            "A08",
            f"Physical population must equal {EXPECTED_PHYSICAL_ROWS:,} rows.",
            "NOT_VERIFIED",
            "No recognised physical-row metric found in existing audit JSON.",
            "CRITICAL",
        )
    else:
        key, value = physical_result
        add_check(
            checks,
            "A08",
            f"Physical population must equal {EXPECTED_PHYSICAL_ROWS:,} rows.",
            "PASS" if value == EXPECTED_PHYSICAL_ROWS else "FAIL",
            f"{key}={value:,}",
            "CRITICAL",
        )

    if unique_result is None:
        add_check(
            checks,
            "A09",
            (
                "Unique raw observation identities must equal "
                f"{EXPECTED_UNIQUE_RAW_IDENTITIES:,}."
            ),
            "NOT_VERIFIED",
            "No recognised unique-identity metric found in existing audit JSON.",
            "CRITICAL",
        )
    else:
        key, value = unique_result
        add_check(
            checks,
            "A09",
            (
                "Unique raw observation identities must equal "
                f"{EXPECTED_UNIQUE_RAW_IDENTITIES:,}."
            ),
            (
                "PASS"
                if value == EXPECTED_UNIQUE_RAW_IDENTITIES
                else "FAIL"
            ),
            f"{key}={value:,}",
            "CRITICAL",
        )

    if duplicate_result is None:
        add_check(
            checks,
            "A10",
            (
                "The governed duplicate excess must remain "
                f"{EXPECTED_DUPLICATE_EXCESS:,}."
            ),
            "NOT_VERIFIED",
            "No recognised duplicate metric found in existing audit JSON.",
            "CRITICAL",
        )
    else:
        key, value = duplicate_result
        add_check(
            checks,
            "A10",
            (
                "The governed duplicate excess must remain "
                f"{EXPECTED_DUPLICATE_EXCESS:,}."
            ),
            "PASS" if value == EXPECTED_DUPLICATE_EXCESS else "FAIL",
            f"{key}={value:,}",
            "CRITICAL",
        )

    source_fields_only = {
        "observation_id",
        "source_system",
        "source_path",
        "source_row_number",
        "source_file_sha256",
        "horse_key",
        "source_horse_name",
        "normalised_horse_name",
        "source_url",
        "race_date",
        "track",
        "race_number",
        "runner_number",
        "canonical_horse_id",
        "canonical_horse_name",
        "identity_status",
        "identity_resolution_method",
        "identity_evidence_sha256",
    }

    unexpected_candidate_fields = sorted(
        set(candidate_fields) - source_fields_only
    )

    add_check(
        checks,
        "A11",
        "Observation construction must remain separate from downstream performance enrichment.",
        "PASS" if not unexpected_candidate_fields else "PARTIAL",
        (
            "Candidate header contains identity and source-lineage fields only."
            if not unexpected_candidate_fields
            else (
                "Additional candidate fields detected: "
                + ", ".join(unexpected_candidate_fields)
            )
        ),
        "HIGH",
    )

    deterministic_rebuild_logic = bool(
        re.search(r"sha256", source, flags=re.IGNORECASE)
    ) and bool(
        re.search(
            r"determin|rebuild",
            source,
            flags=re.IGNORECASE,
        )
    )

    add_check(
        checks,
        "A12",
        "The builder must verify byte-identical deterministic rebuilds.",
        "PARTIAL" if deterministic_rebuild_logic else "NOT_IMPLEMENTED",
        (
            "SHA256/rebuild language exists, but this inspection phase "
            "did not execute two builds or establish byte-identical outputs."
            if deterministic_rebuild_logic
            else "No complete deterministic rebuild verification was detected."
        ),
        "HIGH",
    )

    result_counts = Counter(check["result"] for check in checks)
    critical_failures = [
        check
        for check in checks
        if check["severity"] == "CRITICAL"
        and check["result"] in {"FAIL", "NOT_IMPLEMENTED"}
    ]

    critical_unverified = [
        check
        for check in checks
        if check["severity"] == "CRITICAL"
        and check["result"] == "NOT_VERIFIED"
    ]

    if any(
        check["check_id"] == "A02"
        and check["result"] == "FAIL"
        for check in checks
    ):
        recommendation = "REPLACE"
        recommendation_reason = (
            "The existing builder's source-admission architecture is broad "
            "and does not enforce the locked consolidated GraphQL authority. "
            "Because source authority defines the warehouse population, this "
            "is a foundational divergence rather than a cosmetic defect."
        )
    elif critical_failures:
        recommendation = "PATCH"
        recommendation_reason = (
            "The builder contains reusable governed components, but one or "
            "more critical compliance requirements fail."
        )
    elif critical_unverified:
        recommendation = "PATCH"
        recommendation_reason = (
            "The builder may contain reusable components, but critical "
            "population requirements are not proven by the existing audit."
        )
    elif result_counts["PARTIAL"] or result_counts["NOT_VERIFIED"]:
        recommendation = "PATCH"
        recommendation_reason = (
            "No critical failure was established, but compliance is incomplete."
        )
    else:
        recommendation = "PROMOTE"
        recommendation_reason = (
            "All inspected governance requirements passed."
        )

    overall_status = (
        PASS_STATUS
        if recommendation == "PROMOTE"
        else FAIL_STATUS
    )

    with SOURCE_MATRIX.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "source_path",
            "classification",
            "classification_evidence",
            "rows_scanned",
            "resolved_rows",
            "collision_rows",
            "unresolved_no_key_rows",
            "unresolved_no_crosswalk_rows",
        ]
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(source_matrix_rows)

    with GOVERNANCE_MATRIX.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "check_id",
            "requirement",
            "result",
            "severity",
            "evidence",
        ]
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(checks)

    report = {
        "audit_id": AUDIT_ID,
        "status": overall_status,
        "generated_at_utc": utc_now(),
        "mode": "INSPECTION_ONLY",
        "builder": relative(BUILDER),
        "existing_outputs": {
            "audit": relative(EXISTING_AUDIT),
            "contract": relative(EXISTING_CONTRACT),
            "source_summary": relative(SOURCE_SUMMARY),
            "candidate": relative(CANDIDATE),
        },
        "expected_population_contract": {
            "physical_rows": EXPECTED_PHYSICAL_ROWS,
            "unique_raw_identities": EXPECTED_UNIQUE_RAW_IDENTITIES,
            "duplicate_excess": EXPECTED_DUPLICATE_EXCESS,
        },
        "builder_findings": findings,
        "candidate_header": candidate_fields,
        "source_classification_counts": dict(
            sorted(classification_counts.items())
        ),
        "existing_audit": existing_audit,
        "existing_contract": existing_contract,
        "governance_checks": checks,
        "result_counts": dict(sorted(result_counts.items())),
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
        "mutations_performed": [],
        "warehouse_rebuild_executed": False,
        "promotion_executed": False,
    }

    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    matrix_lines = [
        "| Check | Requirement | Result | Severity |",
        "|---|---|---:|---:|",
    ]

    for check in checks:
        requirement = check["requirement"].replace("|", "/")
        matrix_lines.append(
            f"| {check['check_id']} | {requirement} | "
            f"**{check['result']}** | {check['severity']} |"
        )

    report_md = "\n".join(
        [
            "# EDGEIQ Historical Observation V3 Builder — Phase 1A.6A Audit",
            "",
            f"**Status:** `{overall_status}`",
            "",
            f"**Decision:** `{recommendation}`",
            "",
            "## Scope",
            "",
            "This was an inspection-only audit.",
            "",
            "- No warehouse was rebuilt.",
            "- No candidate was promoted.",
            "- No existing V2 or V3 file was modified.",
            "- No recursive repository scan was performed.",
            "- The existing large CSV outputs were not processed.",
            "- Only the candidate header was inspected.",
            "",
            "## Decision rationale",
            "",
            recommendation_reason,
            "",
            "## Existing builder",
            "",
            f"- Builder: `{relative(BUILDER)}`",
            f"- Source-summary rows inspected: {len(source_rows):,}",
            (
                "- Recursive source discovery detected: "
                f"{recursive_source_scan}"
            ),
            (
                "- Explicit consolidated authority allow-list detected: "
                f"{explicit_consolidated_allowlist}"
            ),
            "",
            "## Source classification",
            "",
            "```json",
            json.dumps(
                dict(sorted(classification_counts.items())),
                indent=2,
            ),
            "```",
            "",
            "## Governance matrix",
            "",
            *matrix_lines,
            "",
            "## Population contract",
            "",
            f"- Expected physical rows: **{EXPECTED_PHYSICAL_ROWS:,}**",
            (
                "- Expected unique raw identities: "
                f"**{EXPECTED_UNIQUE_RAW_IDENTITIES:,}**"
            ),
            (
                "- Expected duplicate excess: "
                f"**{EXPECTED_DUPLICATE_EXCESS:,}**"
            ),
            "",
            "The existing audit was inspected for these values. No large",
            "warehouse file was recounted during this phase.",
            "",
            "## Deliverables",
            "",
            f"- `{relative(REPORT_JSON)}`",
            f"- `{relative(REPORT_MD)}`",
            f"- `{relative(SOURCE_MATRIX)}`",
            f"- `{relative(GOVERNANCE_MATRIX)}`",
            f"- `{relative(RECOMMENDATION_MD)}`",
            "",
        ]
    )

    REPORT_MD.write_text(report_md, encoding="utf-8")

    recommendation_md = "\n".join(
        [
            "# EDGEIQ Historical Observation V3 Recommendation",
            "",
            f"## Decision: {recommendation}",
            "",
            recommendation_reason,
            "",
            "## Required next action",
            "",
            (
                "Create a new governed Phase 1A.6B builder that admits only "
                "the approved consolidated GraphQL authority, preserves the "
                "locked physical and identity populations, explicitly "
                "excludes prohibited source classes, and leaves the existing "
                "untracked V3 implementation untouched as forensic evidence."
                if recommendation == "REPLACE"
                else (
                    "Produce a targeted governed patch specification before "
                    "changing the existing builder."
                    if recommendation == "PATCH"
                    else (
                        "Perform the deterministic two-build acceptance test "
                        "before promotion."
                    )
                )
            ),
            "",
        ]
    )

    RECOMMENDATION_MD.write_text(
        recommendation_md,
        encoding="utf-8",
    )

    print()
    print(f"STATUS: {overall_status}")
    print(f"DECISION: {recommendation}")
    print(f"CHECKS: {dict(sorted(result_counts.items()))}")
    print(f"REPORT: {relative(REPORT_MD)}")
    print(f"MATRIX: {relative(GOVERNANCE_MATRIX)}")
    print()
    print("PHASE 1A.6A AUDIT COMPLETE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
