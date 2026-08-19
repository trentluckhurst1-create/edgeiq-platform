from __future__ import annotations
import csv
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "parse-failure-auditor-v1"
CLASSIFICATION_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_CLASSIFICATION_V1.csv"
DIRECTORY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_DIRECTORY_PROFILE_V1.csv"
ERROR_TYPES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_ERROR_TYPES_V1.csv"
REMEDIATION_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_REMEDIATION_QUEUE_V1.csv"
SUMMARY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_SUMMARY_V1.json"
REPORT_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_REPORT_V1.md"
REQUIRED = [CLASSIFICATION_PATH, DIRECTORY_PATH, ERROR_TYPES_PATH, REMEDIATION_PATH, SUMMARY_PATH, REPORT_PATH]
VALID_CLASSIFICATIONS = {"ACTIVE_CODE", "GENERATED", "CHECKPOINT", "ARCHIVED", "TRUNCATED", "POWERSHELL_WRAPPER", "EMBEDDED_SOURCE", "NONCANONICAL", "UNKNOWN"}
VALID_ACTIONS = {"REPAIR", "EXCLUDE", "ARCHIVE", "DELETE", "INVESTIGATE", "NONE"}

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def fail(message):
    print("AUDIT_VERDICT=FAIL")
    print(f"AUDIT_FAILURE={message}")
    return 1

def main():
    for path in REQUIRED:
        if not path.exists() or path.stat().st_size == 0:
            return fail(f"Missing or empty required output: {path}")
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    classifications = read_csv(CLASSIFICATION_PATH)
    directories = read_csv(DIRECTORY_PATH)
    errors = read_csv(ERROR_TYPES_PATH)
    remediation = read_csv(REMEDIATION_PATH)
    if summary.get("verdict") != "PASS":
        return fail(f"Builder summary verdict is {summary.get('verdict')}")
    total = int(summary["canonical_parse_failure_count"])
    if len(classifications) != total or len(remediation) != total:
        return fail("Classification/remediation totals do not reconcile")
    ids = [row.get("builder_id", "") for row in classifications]
    if not all(ids) or len(ids) != len(set(ids)):
        return fail("Missing or duplicate builder_id values")
    if any(row.get("classification", "") not in VALID_CLASSIFICATIONS for row in classifications):
        return fail("Invalid classification detected")
    if any(row.get("governance_action", "") not in VALID_ACTIONS for row in classifications):
        return fail("Invalid governance action detected")
    if sum(int(row["failure_count"]) for row in directories) != total:
        return fail("Directory profile totals do not reconcile")
    if sum(int(row["failure_count"]) for row in errors) != total:
        return fail("Error type totals do not reconcile")
    if sum(int(v) for v in summary["classification_counts"].values()) != total:
        return fail("Summary classifications do not reconcile")
    if sum(int(v) for v in summary["governance_action_counts"].values()) != total:
        return fail("Summary actions do not reconcile")
    report = REPORT_PATH.read_text(encoding="utf-8")
    for fragment in ["# EDGEIQ Canonical Parse Failure Auditor V1", "## Executive Summary", "## Classification Analysis", "## Governance Actions", "## Leading Directories", "## Error Analysis", "## Remediation Plan", "## Governance Recommendation"]:
        if fragment not in report:
            return fail(f"Report missing section: {fragment}")
    print("EDGEIQ CANONICAL PARSE FAILURE AUDITOR V1 AUDIT")
    print("AUDIT_VERDICT=PASS")
    print(f"CLASSIFICATION_ROWS={len(classifications)}")
    print(f"DIRECTORY_ROWS={len(directories)}")
    print(f"ERROR_TYPE_ROWS={len(errors)}")
    print(f"REMEDIATION_ROWS={len(remediation)}")
    print(f"ESTIMATED_CANONICAL_HEALTH_PERCENT={summary['estimated_canonical_platform_health_percentage']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
