from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PROD = DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"
CAND = DATA / "edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv"
MIXED = DATA / "edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv"
MIGRATE = ROOT / "scripts" / "migrate_edgeiq_racingcom_graphql_v2.py"
ROLLBACK = ROOT / "scripts" / "rollback_edgeiq_racingcom_graphql_v2.py"
MANIFEST_PREVIEW = DOCS / "edgeiq_racingcom_graphql_migration_manifest_preview_v1.json"
AUDIT = DOCS / "edgeiq_racingcom_graphql_v2_production_migration_preflight_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_graphql_v2_production_migration_preflight_summary_v1.json"
MANIFEST = DOCS / "edgeiq_racingcom_graphql_v2_production_migration_preflight_manifest_v1.json"
REPORT = DOCS / "edgeiq_racingcom_graphql_v2_production_migration_preflight_report_v1.md"

EXPECTED_PROD_SHA = "25ea33aba489bb8f318edcaa3d414c4f7da566573045041ad6ffbe5bff826859"
EXPECTED_CAND_SHA = "77803a32e3880598bb5fae3ba7aba49e1fb67931c2d729f567c36eeab873cfb8"
PROD_COLUMNS = [
    "warehouse_record_id", "race_id", "race_date", "track", "state", "race_no", "distance", "horse", "horse_key", "barrier",
    "last200", "last400", "last600", "last_200", "last_400", "last_600", "early_speed", "mid_speed", "late_speed",
    "peak_speed", "avg_speed", "race_time", "tempo_grade", "pace_profile", "sectional_source", "source_csv_url", "source_cache_path",
    "source_sha256", "acquisition_timestamp", "parser_version", "pipeline_version", "meeting_discovery_version", "race_discovery_version",
    "admission_version", "warehouse_built_utc",
]


def clean(v: object) -> str:
    return "" if v is None else str(v).strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def cols(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle).fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "value", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def run(script: str, *args: str) -> tuple[int, str]:
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], cwd=str(ROOT), capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()


def relevant_git_clean(paths: list[Path]) -> bool:
    rels = [str(p.relative_to(ROOT)).replace("/", "\\") for p in paths]
    out = subprocess.check_output(["git", "status", "--short", "--", *rels], cwd=str(ROOT), text=True)
    return not out.strip()


def no_secret_in_outputs() -> bool:
    secret = clean(os.environ.get("EDGEIQ_RACINGCOM_WIDGET_API_KEY") or os.environ.get("RACINGCOM_PUBLIC_WIDGET_API_KEY"))
    if not secret:
        return True
    for path in [*DOCS.glob("edgeiq_racingcom_*.csv"), *DOCS.glob("edgeiq_racingcom_*.json"), *DOCS.glob("edgeiq_racingcom_*.md"), CAND]:
        try:
            if secret and secret in path.read_text(encoding="utf-8", errors="ignore"):
                return False
        except Exception:
            continue
    return True


def main() -> int:
    reruns = {
        "runner_candidate_readiness": run("audit_edgeiq_racingcom_runner_candidate_readiness_v1.py"),
        "historical_regression": run("audit_edgeiq_racingcom_runner_candidate_historical_regression_v1.py"),
        "graphql_runner_validation": run("audit_edgeiq_racingcom_graphql_runner_aggregate_validation_v1.py"),
        "downstream_compatibility": run("audit_edgeiq_racingcom_runner_candidate_downstream_compatibility_v1.py"),
        "human_review_update": run("update_edgeiq_racingcom_human_review_runner_adapter_v1.py"),
        "migration_dry_run": run("migrate_edgeiq_racingcom_graphql_v2.py"),
        "rollback_dry_run": run("rollback_edgeiq_racingcom_graphql_v2.py", "--manifest", str(MANIFEST_PREVIEW.relative_to(ROOT))),
    }
    prod_rows = read_csv(PROD)
    cand_rows = read_csv(CAND)
    prod_sha = sha(PROD)
    cand_sha = sha(CAND)
    historical = sum(1 for row in cand_rows if clean(row.get("sectional_source")) == "RACING.COM_DIRECT_CSV_V2")
    graphql = sum(1 for row in cand_rows if clean(row.get("sectional_source")) == "RACING.COM_GRAPHQL_GETRACEFORM_V2")
    dup = len(cand_rows) - len({(row.get("race_id"), row.get("horse_key")) for row in cand_rows})
    future = sum(1 for row in cand_rows if clean(row.get("race_date")) > "2026-07-23")
    synthetic = sum(1 for row in cand_rows if "SYNTHETIC_FIXTURE" in json.dumps(row).upper())
    checks = [
        ("production_hash_expected", prod_sha == EXPECTED_PROD_SHA, prod_sha, "Current production hash must match approved pre-migration state."),
        ("candidate_hash_expected", cand_sha == EXPECTED_CAND_SHA, cand_sha, "Approved runner candidate hash must match."),
        ("production_rows_before", len(prod_rows) == 80, str(len(prod_rows)), "Production must have 80 rows before migration."),
        ("candidate_rows", len(cand_rows) == 138, str(len(cand_rows)), "Candidate must have 138 rows."),
        ("candidate_races", len({r.get("race_id") for r in cand_rows}) == 13, str(len({r.get("race_id") for r in cand_rows})), "Candidate must have 13 races."),
        ("candidate_columns", cols(CAND) == PROD_COLUMNS, str(len(cols(CAND))), "Candidate columns must match production contract."),
        ("historical_rows_retained", historical == 80, str(historical), "Historical CSV rows retained."),
        ("graphql_runner_rows", graphql == 58, str(graphql), "Fresh GraphQL runner rows present."),
        ("duplicate_runner_keys", dup == 0, str(dup), "No duplicate race-runner keys."),
        ("future_races", future == 0, str(future), "No future races."),
        ("synthetic_races", synthetic == 0, str(synthetic), "No synthetic fixture rows."),
        ("api_key_absent", no_secret_in_outputs(), "NO_SECRET_FOUND", "API key value absent from outputs."),
        ("relevant_worktree_clean", relevant_git_clean([PROD, CAND, MIGRATE, ROLLBACK]), "YES", "Relevant production migration files are not dirty."),
        ("rollback_script_available", ROLLBACK.exists(), str(ROLLBACK.exists()), "Rollback script exists."),
        ("migration_manifest_available", MANIFEST_PREVIEW.exists(), str(MANIFEST_PREVIEW.exists()), "Migration manifest exists."),
    ]
    for name, result in reruns.items():
        checks.append((f"rerun_{name}", result[0] == 0, str(result[0]), result[1][-500:]))
    audit_rows = [{"check": name, "status": "PASS" if ok else "FAIL", "value": value, "detail": detail} for name, ok, value, detail in checks]
    decision = "RACINGCOM_GRAPHQL_V2_PRODUCTION_MIGRATION_PREFLIGHT_PASS" if all(row["status"] == "PASS" for row in audit_rows) else "RACINGCOM_GRAPHQL_V2_PRODUCTION_MIGRATION_PREFLIGHT_BLOCKED"
    run_id = datetime.now(timezone.utc).strftime("racingcom_graphql_v2_migration_%Y%m%dT%H%M%SZ")
    backup_path = DOCS / "migration-backups" / f"edgeiq_racingcom_performance_warehouse_v2_{run_id}.csv"
    schema_hash = hashlib.sha256("|".join(cols(CAND)).encode("utf-8")).hexdigest()
    manifest = {
        "run_id": run_id,
        "decision": decision,
        "git_commit": git_commit(),
        "production_path": str(PROD.relative_to(ROOT)),
        "candidate_path": str(CAND.relative_to(ROOT)),
        "production_sha256": prod_sha,
        "candidate_sha256": cand_sha,
        "production_rows": len(prod_rows),
        "candidate_rows": len(cand_rows),
        "production_races": len({r.get("race_id") for r in prod_rows}),
        "candidate_races": len({r.get("race_id") for r in cand_rows}),
        "schema_hash": schema_hash,
        "backup_path": str(backup_path.relative_to(ROOT)),
        "rollback_script": str(ROLLBACK.relative_to(ROOT)),
        "prerequisite_audits": {name: {"exit_code": code} for name, (code, _out) in reruns.items()},
    }
    write_csv(AUDIT, audit_rows)
    SUMMARY.write_text(json.dumps({"decision": decision, "run_id": run_id, "pass": sum(1 for r in audit_rows if r["status"] == "PASS"), "fail": sum(1 for r in audit_rows if r["status"] == "FAIL"), "production_changed": "NO"}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Racing.com GraphQL V2 Production Migration Preflight\n\nDecision: `{decision}`\n\nRun ID: `{run_id}`\n\nProduction changed: `NO`\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "run_id": run_id, "production_changed": "NO"}, indent=2))
    return 0 if decision.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
