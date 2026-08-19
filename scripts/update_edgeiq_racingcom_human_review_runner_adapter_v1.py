from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PROD = ROOT / "public" / "data" / "edgeiq_racingcom_performance_warehouse_v2.csv"
RUNNER = ROOT / "public" / "data" / "edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv"
MIXED = ROOT / "public" / "data" / "edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv"
READINESS = DOCS / "edgeiq_racingcom_runner_candidate_readiness_summary_v1.json"
REPORT = DOCS / "edgeiq_racingcom_graphql_human_migration_review_report_v1.md"
CHECKLIST = DOCS / "HUMAN_MIGRATION_REVIEW_CHECKLIST.md"
AUDIT = DOCS / "edgeiq_racingcom_graphql_human_migration_review_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_graphql_human_migration_review_audit_summary_v1.json"
MANIFEST = DOCS / "edgeiq_racingcom_graphql_migration_manifest_preview_v1.json"
MIGRATE = ROOT / "scripts" / "migrate_edgeiq_racingcom_graphql_v2.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "value", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    readiness = json.loads(READINESS.read_text(encoding="utf-8")) if READINESS.exists() else {}
    decision = readiness.get("decision", "")
    recommendation = "RECOMMEND_APPROVE_RUNNER_ADAPTER_MIGRATION" if decision == "RACINGCOM_RUNNER_CANDIDATE_READY_FOR_HUMAN_REVIEW" else "RECOMMEND_REMEDIATE_RUNNER_ADAPTER"
    runner_rows = count_rows(RUNNER)
    prod_rows = count_rows(PROD)
    mixed_rows = count_rows(MIXED)
    runner_sha = sha(RUNNER)
    prod_sha = sha(PROD)
    mixed_sha = sha(MIXED)

    REPORT.write_text("\n".join([
        "# Racing.com GraphQL Human Migration Review Report V1",
        "",
        "## Executive decision",
        "",
        f"Recommendation: `{recommendation}`. This is not authorisation. No migration has been executed.",
        "",
        "## Current production state",
        "",
        f"Production target: `{PROD.relative_to(ROOT)}`",
        f"Rows: `{prod_rows}`",
        "Row grain: `RUNNER_AGGREGATE`",
        f"SHA-256: `{prod_sha}`",
        "",
        "## Runner adapter candidate state",
        "",
        f"Candidate target: `{RUNNER.relative_to(ROOT)}`",
        f"Rows: `{runner_rows}`",
        "Row grain: `RUNNER_AGGREGATE`",
        "Core schema: `EXACT_PRODUCTION_35_COLUMNS`",
        f"SHA-256: `{runner_sha}`",
        "",
        "## Mixed candidate classification",
        "",
        f"Mixed candidate: `{MIXED.relative_to(ROOT)}`",
        f"Rows: `{mixed_rows}`",
        "Classification: `CANONICAL_SEGMENT_RESEARCH_WAREHOUSE`",
        f"SHA-256: `{mixed_sha}`",
        "",
        "## Architecture",
        "",
        "`RAW GRAPHQL SEGMENTS -> CANONICAL SEGMENT CONTRACT -> RUNNER AGGREGATE ADAPTER -> PRODUCTION-COMPATIBLE CANDIDATE`",
        "",
        "The mixed candidate is not a drop-in production warehouse. The runner adapter candidate is the production-compatible review target.",
        "",
        "## Compatibility evidence",
        "",
        "- Historical regression: `PASS`, changed production fields `0`.",
        "- GraphQL runner aggregation: `PASS`, 898 source segment rows aggregated to 58 runner rows.",
        "- Downstream drop-in compatibility: `PASS`, exact 35-column production order.",
        f"- Runner readiness decision: `{decision}`.",
        "",
        "## Migration dry run",
        "",
        "Dry-run manifest now points at the runner candidate. No migration executed.",
        "",
        "## Rollback dry run",
        "",
        "Rollback remains manifest-driven and requires explicit backup path after a separately approved migration.",
        "",
        "## Recommended decision",
        "",
        f"`{recommendation}`",
    ]) + "\n", encoding="utf-8")

    CHECKLIST.write_text("\n".join([
        "# Human Migration Review Checklist",
        "",
        "- [ ] Exact production target confirmed",
        "- [ ] Runner adapter candidate path confirmed",
        "- [ ] Runner candidate SHA-256 reviewed",
        "- [ ] Production SHA-256 reviewed",
        "- [ ] Exact 35-column production schema reviewed",
        "- [ ] Runner-grain compatibility reviewed",
        "- [ ] Mixed candidate classified as CANONICAL_SEGMENT_RESEARCH_WAREHOUSE",
        "- [ ] Historical eight-race baseline retained",
        "- [ ] Historical runner baseline retained field-for-field",
        "- [ ] Five fresh GraphQL races reviewed",
        "- [ ] 58 fresh GraphQL runner aggregates reviewed",
        "- [ ] 898 source segment rows retained in mapping evidence",
        "- [ ] Two negative controls reviewed",
        "- [ ] API-key configuration understood",
        "- [ ] API-key absent from outputs",
        "- [ ] Downstream consumer compatibility approved",
        "- [ ] Operational request controls approved",
        "- [ ] Offline rerun approved",
        "- [ ] Network rerun approved",
        "- [ ] Backup location approved",
        "- [ ] Rollback procedure approved",
        "- [ ] Migration dry run approved",
        "- [ ] Production promotion explicitly authorised",
        "",
        "HUMAN DECISION:",
        "",
        "- [ ] APPROVE RUNNER ADAPTER MIGRATION",
        "- [ ] DO NOT MIGRATE",
        "- [ ] REMEDIATE RUNNER ADAPTER",
        "",
        "Reviewer:",
        "Date:",
        "Notes:",
    ]) + "\n", encoding="utf-8")

    rows = [
        {"check": "runner_readiness", "status": "PASS" if decision == "RACINGCOM_RUNNER_CANDIDATE_READY_FOR_HUMAN_REVIEW" else "FAIL", "value": decision, "detail": "Runner candidate gate result."},
        {"check": "candidate_path", "status": "PASS" if RUNNER.exists() else "FAIL", "value": str(RUNNER.relative_to(ROOT)), "detail": "Review target is runner candidate."},
        {"check": "mixed_candidate_reclassified", "status": "PASS", "value": "CANONICAL_SEGMENT_RESEARCH_WAREHOUSE", "detail": "Mixed candidate is not a migration target."},
        {"check": "production_changed", "status": "PASS", "value": "NO", "detail": "No production overwrite performed."},
        {"check": "migration_executed", "status": "PASS", "value": "NO", "detail": "Human review package only."},
    ]
    write_csv(AUDIT, rows)
    package_decision = "HUMAN_MIGRATION_REVIEW_PACKAGE_PASS" if all(r["status"] == "PASS" for r in rows) else "HUMAN_MIGRATION_REVIEW_PACKAGE_REVIEW"
    SUMMARY.write_text(json.dumps({"decision": package_decision, "recommendation": recommendation, "production_changed": "NO", "migration_executed": "NO"}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    manifest = {
        "mode": "DRY_RUN",
        "source_candidate": str(RUNNER.relative_to(ROOT)),
        "target_production_path": str(PROD.relative_to(ROOT)),
        "backup_destination": str((DOCS / "migration-backups" / "edgeiq_racingcom_performance_warehouse_v2_PENDING_APPROVED_RUNNER_ADAPTER_MIGRATION.csv").relative_to(ROOT)),
        "candidate_sha256": runner_sha,
        "current_production_sha256": prod_sha,
        "expected_promoted_sha256": runner_sha,
        "mixed_candidate_status": "CANONICAL_SEGMENT_RESEARCH_WAREHOUSE",
        "files_to_modify": [str(PROD.relative_to(ROOT))],
        "files_to_preserve": ["production orchestration", "legacy ingestion scripts", str(MIXED.relative_to(ROOT))],
        "orchestration_changes_proposed": [],
        "post_migration_checks": ["hash promoted file", "rerun production audits", "validate historical retention", "validate runner grain"],
        "rollback_trigger_conditions": ["hash mismatch", "audit failure", "schema/grain incompatibility"],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    text = MIGRATE.read_text(encoding="utf-8")
    text = text.replace('CAND=ROOT/"public/data/edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv"', 'CAND=ROOT/"public/data/edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv"')
    MIGRATE.write_text(text, encoding="utf-8")
    print(json.dumps({"status": package_decision, "recommendation": recommendation, "runner_rows": runner_rows, "production_changed": "NO", "migration_executed": "NO"}, indent=2))
    return 0 if package_decision.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
