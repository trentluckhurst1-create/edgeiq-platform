from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "builder-registry-v1-1"
AUDITOR_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "parse-failure-auditor-v1"
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "canonical-scope-refiner-v1"

REGISTRY_PATH = REGISTRY_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_1.csv"
SUMMARY_PATH = REGISTRY_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_1_SUMMARY.json"
CLASSIFICATION_PATH = AUDITOR_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_CLASSIFICATION_V1.csv"

REFINED_REGISTRY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_REFINED_V1.csv"
EXCLUSIONS_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_SCOPE_EXCLUSIONS_V1.csv"
RETAINED_FAILURES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_SCOPE_RETAINED_PARSE_FAILURES_V1.csv"
SUMMARY_OUT_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_SCOPE_REFINER_SUMMARY_V1.json"
REPORT_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_SCOPE_REFINER_REPORT_V1.md"

EXCLUDABLE = {
    "GENERATED",
    "CHECKPOINT",
    "ARCHIVED",
    "POWERSHELL_WRAPPER",
    "EMBEDDED_SOURCE",
    "NONCANONICAL",
}
RETAINED = {
    "ACTIVE_CODE",
    "TRUNCATED",
    "UNKNOWN",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def first(row: dict[str, str], *names: str) -> str:
    lowered = {str(k).strip().lower(): (v or "") for k, v in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None and value.strip():
            return value.strip()
    return ""


def main() -> int:
    registry_rows = read_csv(REGISTRY_PATH)
    classification_rows = read_csv(CLASSIFICATION_PATH)
    registry_summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    by_builder = {
        first(row, "builder_id", "id"): row
        for row in classification_rows
        if first(row, "builder_id", "id")
    }

    refined_rows: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    retained_failures: list[dict[str, object]] = []

    canonical_before = 0

    for row in registry_rows:
        builder_id = first(row, "builder_id", "id")
        classification = first(row, "classification", "builder_classification").upper()
        if classification == "CANONICAL":
            canonical_before += 1

        failure = by_builder.get(builder_id)
        scope_status = "UNCHANGED"
        scope_reason = ""
        refined_classification = classification

        if classification == "CANONICAL" and failure:
            failure_class = first(failure, "classification").upper()
            action = first(failure, "governance_action").upper()
            evidence = first(failure, "evidence")
            relative_path = first(failure, "relative_path")

            if failure_class in EXCLUDABLE and action in {"EXCLUDE", "ARCHIVE", "DELETE"}:
                refined_classification = "HISTORICAL"
                scope_status = "EXCLUDED_FROM_CANONICAL"
                scope_reason = f"{failure_class}: {evidence}"
                exclusions.append(
                    {
                        "builder_id": builder_id,
                        "relative_path": relative_path,
                        "previous_classification": "CANONICAL",
                        "refined_classification": refined_classification,
                        "failure_classification": failure_class,
                        "governance_action": action,
                        "confidence": first(failure, "confidence"),
                        "scope_reason": scope_reason,
                    }
                )
            elif failure_class in RETAINED:
                scope_status = "RETAINED_CANONICAL_FAILURE"
                scope_reason = f"{failure_class}: {evidence}"
                retained_failures.append(
                    {
                        "builder_id": builder_id,
                        "relative_path": relative_path,
                        "failure_classification": failure_class,
                        "governance_action": action,
                        "confidence": first(failure, "confidence"),
                        "observed_error_type": first(failure, "observed_error_type"),
                        "observed_error_line": first(failure, "observed_error_line"),
                        "observed_error_message": first(failure, "observed_error_message"),
                        "scope_reason": scope_reason,
                    }
                )

        output_row = dict(row)
        output_row["original_classification"] = classification
        output_row["classification"] = refined_classification
        output_row["scope_status"] = scope_status
        output_row["scope_reason"] = scope_reason
        refined_rows.append(output_row)

    canonical_after = sum(
        1 for row in refined_rows if str(row.get("classification", "")).upper() == "CANONICAL"
    )
    historical_after = sum(
        1 for row in refined_rows if str(row.get("classification", "")).upper() == "HISTORICAL"
    )

    refined_fieldnames = list(registry_rows[0].keys()) if registry_rows else []
    for extra in ["original_classification", "scope_status", "scope_reason"]:
        if extra not in refined_fieldnames:
            refined_fieldnames.append(extra)

    write_csv(REFINED_REGISTRY_PATH, refined_rows, refined_fieldnames)
    write_csv(
        EXCLUSIONS_PATH,
        exclusions,
        [
            "builder_id",
            "relative_path",
            "previous_classification",
            "refined_classification",
            "failure_classification",
            "governance_action",
            "confidence",
            "scope_reason",
        ],
    )
    write_csv(
        RETAINED_FAILURES_PATH,
        retained_failures,
        [
            "builder_id",
            "relative_path",
            "failure_classification",
            "governance_action",
            "confidence",
            "observed_error_type",
            "observed_error_line",
            "observed_error_message",
            "scope_reason",
        ],
    )

    failure_class_counts = Counter(
        first(row, "failure_classification") for row in exclusions
    )
    retained_class_counts = Counter(
        first(row, "failure_classification") for row in retained_failures
    )

    expected_failures = int(registry_summary["canonical_parse_failure_count"])
    reconciled_failures = len(exclusions) + len(retained_failures)

    verdict = "PASS"
    if reconciled_failures != expected_failures:
        verdict = "FAIL_FAILURE_RECONCILIATION"
    elif canonical_before - len(exclusions) != canonical_after:
        verdict = "FAIL_CANONICAL_COUNT_RECONCILIATION"
    elif not retained_failures:
        verdict = "FAIL_NO_RETAINED_FAILURES"

    summary = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "canonical_builder_count_before": canonical_before,
        "canonical_builder_count_after": canonical_after,
        "historical_builder_count_after": historical_after,
        "canonical_scope_exclusion_count": len(exclusions),
        "retained_canonical_parse_failure_count": len(retained_failures),
        "input_canonical_parse_failure_count": expected_failures,
        "reconciled_failure_count": reconciled_failures,
        "exclusion_classification_counts": dict(sorted(failure_class_counts.items())),
        "retained_failure_classification_counts": dict(sorted(retained_class_counts.items())),
        "canonical_scope_reduction_percentage": round(
            (len(exclusions) / canonical_before) * 100.0, 4
        ) if canonical_before else 0.0,
        "estimated_refined_canonical_parse_health_percentage": round(
            ((canonical_after - len(retained_failures)) / canonical_after) * 100.0, 4
        ) if canonical_after else 0.0,
        "outputs": {
            "refined_registry_csv": str(REFINED_REGISTRY_PATH),
            "scope_exclusions_csv": str(EXCLUSIONS_PATH),
            "retained_parse_failures_csv": str(RETAINED_FAILURES_PATH),
            "report_md": str(REPORT_PATH),
        },
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# EDGEIQ Canonical Scope Refiner V1",
        "",
        "## Executive Summary",
        "",
        f"- Verdict: **{verdict}**",
        f"- Canonical builders before refinement: **{canonical_before}**",
        f"- Canonical builders after refinement: **{canonical_after}**",
        f"- Deterministic scope exclusions: **{len(exclusions)}**",
        f"- Retained canonical parse failures: **{len(retained_failures)}**",
        f"- Estimated refined canonical parse health: "
        f"**{summary['estimated_refined_canonical_parse_health_percentage']}%**",
        "",
        "## Scope Policy",
        "",
        "The refiner excludes only records whose forensic classification provides "
        "deterministic evidence that they are generated, checkpoint, archived, "
        "PowerShell wrappers, embedded-source wrappers, or otherwise noncanonical.",
        "",
        "`ACTIVE_CODE`, `TRUNCATED`, and `UNKNOWN` records remain canonical and are "
        "carried into the remediation queue.",
        "",
        "## Exclusions by Classification",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    for name, count in sorted(failure_class_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {name} | {count} |")

    lines.extend([
        "",
        "## Retained Failures by Classification",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ])
    for name, count in sorted(retained_class_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {name} | {count} |")

    lines.extend([
        "",
        "## Governance Result",
        "",
        "This unit refines classification evidence only. It does not modify or delete "
        "any source builder. The refined registry is a governed derivative output "
        "for the next dependency-graph phase.",
        "",
    ])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("EDGEIQ CANONICAL SCOPE REFINER V1")
    print(f"VERDICT={verdict}")
    print(f"CANONICAL_BEFORE={canonical_before}")
    print(f"CANONICAL_AFTER={canonical_after}")
    print(f"SCOPE_EXCLUSIONS={len(exclusions)}")
    print(f"RETAINED_CANONICAL_FAILURES={len(retained_failures)}")
    print(
        "REFINED_CANONICAL_PARSE_HEALTH_PERCENT="
        f"{summary['estimated_refined_canonical_parse_health_percentage']}"
    )
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
