from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PROD = DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"
CAND = DATA / "edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv"
BACKUP_SUMMARY = DOCS / "edgeiq_racingcom_graphql_v2_production_backup_summary_v1.json"
AUDIT = DOCS / "edgeiq_racingcom_graphql_v2_post_migration_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_graphql_v2_post_migration_summary_v1.json"
REPORT = DOCS / "edgeiq_racingcom_graphql_v2_post_migration_report_v1.md"
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
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def cols(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle).fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "value", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def restore_backup() -> tuple[str, str]:
    manifest = json.loads(BACKUP_SUMMARY.read_text(encoding="utf-8"))
    backup = ROOT / manifest["backup_path"]
    shutil.copy2(backup, PROD)
    return manifest["backup_path"], sha(PROD)


def main() -> int:
    prod_rows = read_csv(PROD)
    cand_rows = read_csv(CAND)
    prod_sha = sha(PROD)
    cand_sha = sha(CAND)
    historical = sum(1 for row in prod_rows if clean(row.get("sectional_source")) == "RACING.COM_DIRECT_CSV_V2")
    graphql = sum(1 for row in prod_rows if clean(row.get("sectional_source")) == "RACING.COM_GRAPHQL_GETRACEFORM_V2")
    dup = len(prod_rows) - len({(r.get("race_id"), r.get("horse_key")) for r in prod_rows})
    segment_rows = sum(1 for row in prod_rows if clean(row.get("fact_grain")).upper() == "SEGMENT" or clean(row.get("row_type")).upper() in {"SECTIONAL", "SPLIT"})
    candidate_by_key = {(r.get("race_id"), r.get("horse_key")): r for r in cand_rows if clean(r.get("sectional_source")) == "RACING.COM_DIRECT_CSV_V2"}
    changed_historical = 0
    for row in prod_rows:
        if clean(row.get("sectional_source")) != "RACING.COM_DIRECT_CSV_V2":
            continue
        expected = candidate_by_key.get((row.get("race_id"), row.get("horse_key")))
        if not expected or any(clean(row.get(c)) != clean(expected.get(c)) for c in PROD_COLUMNS):
            changed_historical += 1
    checks = [
        ("production_sha_equals_candidate", prod_sha == EXPECTED_CAND_SHA == cand_sha, prod_sha, "Production SHA equals approved runner candidate SHA."),
        ("production_rows", len(prod_rows) == 138, str(len(prod_rows)), "Promoted production row count."),
        ("production_races", len({r.get("race_id") for r in prod_rows}) == 13, str(len({r.get("race_id") for r in prod_rows})), "Promoted production race count."),
        ("historical_rows", historical == 80, str(historical), "Historical CSV rows retained."),
        ("fresh_graphql_rows", graphql == 58, str(graphql), "Fresh GraphQL runner rows promoted."),
        ("historical_value_changes", changed_historical == 0, str(changed_historical), "Historical runner rows retained field-for-field."),
        ("duplicate_runner_keys", dup == 0, str(dup), "No duplicate runner keys."),
        ("schema_exact", cols(PROD) == PROD_COLUMNS, str(len(cols(PROD))), "Exact production schema."),
        ("runner_grain", segment_rows == 0, str(segment_rows), "No segment rows in production runner warehouse."),
    ]
    audit_rows = [{"check": n, "status": "PASS" if ok else "FAIL", "value": v, "detail": d} for n, ok, v, d in checks]
    decision = "RACINGCOM_GRAPHQL_V2_POST_MIGRATION_PASS" if all(r["status"] == "PASS" for r in audit_rows) else "RACINGCOM_GRAPHQL_V2_POST_MIGRATION_FAIL"
    rollback = {"executed": "NO", "backup_path": "", "restored_sha256": ""}
    if decision.endswith("_FAIL"):
        backup_path, restored_sha = restore_backup()
        rollback = {"executed": "YES", "backup_path": backup_path, "restored_sha256": restored_sha}
    write_csv(AUDIT, audit_rows)
    SUMMARY.write_text(json.dumps({"decision": decision, "rollback": rollback, "production_sha256": sha(PROD), "production_rows": len(read_csv(PROD))}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Racing.com GraphQL V2 Post-Migration Validation\n\nDecision: `{decision}`\n\nRollback executed: `{rollback['executed']}`\n\nProduction SHA: `{sha(PROD)}`\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "rollback": rollback, "production_sha256": sha(PROD)}, indent=2))
    return 0 if decision.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
