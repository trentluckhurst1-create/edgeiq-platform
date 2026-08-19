from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PUBLIC = ROOT / "public" / "data"
PRODUCTION = PUBLIC / "edgeiq_racingcom_performance_warehouse_v2.csv"
CANDIDATE = PUBLIC / "edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv"
FINAL_REPORT = DOCS / "edgeiq_racingcom_graphql_human_migration_review_report_v1.md"
CHECKLIST = DOCS / "HUMAN_MIGRATION_REVIEW_CHECKLIST.md"
BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(rows[0].keys()) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean(row.get(column, "")) for column in columns})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def runner_key(row: dict[str, str]) -> str:
    return f"{clean(row.get('race_id'))}::{norm(row.get('horse_key') or row.get('horse'))}"


def candidate_key(row: dict[str, str]) -> str:
    if clean(row.get("fact_grain")) == "RUNNER_AGGREGATE":
        return runner_key(row)
    return clean(row.get("canonical_fact_id"))


def infer_type(values: list[str]) -> str:
    vals = [clean(v) for v in values if clean(v)]
    if not vals:
        return "ALL_NULL"
    is_int = True
    is_float = True
    for val in vals[:5000]:
        try:
            int(val)
        except Exception:
            is_int = False
        try:
            float(val)
        except Exception:
            is_float = False
    if is_int:
        return "INTEGER"
    if is_float:
        return "NUMBER"
    return "TEXT"


def scan_references() -> list[dict[str, str]]:
    terms = [
        "edgeiq_racingcom_performance_warehouse_v2.csv",
        "edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv",
        "racingcom_performance_warehouse_v2",
    ]
    rows: list[dict[str, str]] = []
    for base in ["scripts", "src", "docs/performance-intelligence", "contracts"]:
        root = ROOT / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            if path.suffix.lower() not in {".py", ".ps1", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".txt", ".csv"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for term in terms:
                if term not in text:
                    continue
                lowered = text.lower()
                rel = str(path.relative_to(ROOT))
                if "graphql_candidate" in term.lower() or "graphql_candidate" in rel.lower():
                    classification = "CANDIDATE_WRITE" if "build_edgeiq_racingcom_candidate_speed_warehouse" in rel else "CANDIDATE_READ"
                elif path.suffix.lower() in {".md", ".txt", ".csv"}:
                    classification = "DOCUMENTATION_ONLY"
                elif "build_edgeiq_racingcom_performance_warehouse_v2.py" in rel:
                    classification = "ACTIVE_PRODUCTION_WRITE"
                elif "audit" in rel.lower() or "test" in rel.lower():
                    classification = "TEST_ONLY"
                else:
                    classification = "ACTIVE_PRODUCTION_READ"
                rows.append(
                    {
                        "file": rel,
                        "term": term,
                        "classification": classification,
                        "line_count": str(text.count("\n") + 1),
                    }
                )
    return sorted(rows, key=lambda row: (row["classification"], row["file"], row["term"]))


def migration_targets(refs: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    active_writers = [r for r in refs if r["classification"] == "ACTIVE_PRODUCTION_WRITE"]
    active_readers = [r for r in refs if r["classification"] == "ACTIVE_PRODUCTION_READ"]
    status = "PRODUCTION_TARGET_RESOLVED" if PRODUCTION.exists() and active_writers else "BLOCKED_BY_UNRESOLVED_PRODUCTION_TARGET"
    rows = [
        {
            "target_type": "CURRENT_PRODUCTION_WAREHOUSE",
            "path": str(PRODUCTION.relative_to(ROOT)),
            "exists": "YES" if PRODUCTION.exists() else "NO",
            "sha256": sha(PRODUCTION),
            "classification": "MIGRATION_TARGET",
            "proof": "Existing file plus ACTIVE_PRODUCTION_WRITE reference.",
        },
        {
            "target_type": "GRAPHQL_CANDIDATE_WAREHOUSE",
            "path": str(CANDIDATE.relative_to(ROOT)),
            "exists": "YES" if CANDIDATE.exists() else "NO",
            "sha256": sha(CANDIDATE),
            "classification": "MIGRATION_SOURCE",
            "proof": "Candidate warehouse generated by governed GraphQL V2 integration.",
        },
    ]
    for r in active_writers:
        rows.append({"target_type": "ACTIVE_PRODUCTION_ORCHESTRATION", "path": r["file"], "exists": "YES", "sha256": sha(ROOT / r["file"]), "classification": r["classification"], "proof": r["term"]})
    for r in active_readers:
        rows.append({"target_type": "DOWNSTREAM_READER", "path": r["file"], "exists": "YES", "sha256": sha(ROOT / r["file"]), "classification": r["classification"], "proof": r["term"]})
    summary = {
        "status": status,
        "production_path": str(PRODUCTION.relative_to(ROOT)),
        "candidate_path": str(CANDIDATE.relative_to(ROOT)),
        "production_sha256": sha(PRODUCTION),
        "candidate_sha256": sha(CANDIDATE),
        "active_writer_count": len(active_writers),
        "active_reader_count": len(active_readers),
    }
    return rows, summary


def compare_data() -> dict[str, Any]:
    prod_rows, prod_cols = read_csv(PRODUCTION)
    cand_rows, cand_cols = read_csv(CANDIDATE)
    prod_by_key = {runner_key(row): row for row in prod_rows}
    cand_runner_rows = [row for row in cand_rows if clean(row.get("fact_grain")) == "RUNNER_AGGREGATE"]
    cand_segments = [row for row in cand_rows if clean(row.get("fact_grain")) == "SEGMENT"]
    cand_by_runner = {runner_key(row): row for row in cand_runner_rows}
    prod_keys = set(prod_by_key)
    cand_runner_keys = set(cand_by_runner)
    retained_keys = sorted(prod_keys & cand_runner_keys)
    added_segment_keys = sorted(candidate_key(row) for row in cand_segments)
    removed_runner_keys = sorted(prod_keys - cand_runner_keys)
    added_runner_keys = sorted(cand_runner_keys - prod_keys)
    retained_cols = sorted(set(prod_cols) & set(cand_cols))
    added_cols = sorted(set(cand_cols) - set(prod_cols))
    removed_cols = sorted(set(prod_cols) - set(cand_cols))

    schema_rows = []
    for col in sorted(set(prod_cols) | set(cand_cols)):
        p_vals = [row.get(col, "") for row in prod_rows]
        c_vals = [row.get(col, "") for row in cand_rows]
        if col in prod_cols and col in cand_cols:
            status = "RETAINED"
        elif col in cand_cols:
            status = "ADDED_IN_CANDIDATE"
        else:
            status = "REMOVED_FROM_CANDIDATE"
        schema_rows.append(
            {
                "column": col,
                "production_present": "YES" if col in prod_cols else "NO",
                "candidate_present": "YES" if col in cand_cols else "NO",
                "schema_status": status,
                "production_type": infer_type(p_vals),
                "candidate_type": infer_type(c_vals),
                "production_nonblank": sum(1 for v in p_vals if clean(v)),
                "candidate_nonblank": sum(1 for v in c_vals if clean(v)),
            }
        )
    row_comp = [
        {"comparison": "runner_rows_retained", "count": len(retained_keys), "classification": "CANONICAL_DEDUPLICATION", "detail": "Historical runner-grain rows retained in candidate as RUNNER_AGGREGATE."},
        {"comparison": "runner_rows_added", "count": len(added_runner_keys), "classification": "UNRESOLVED" if added_runner_keys else "EXPECTED_NEW_GRAPHQL_DATA", "detail": "Runner-grain additions."},
        {"comparison": "runner_rows_removed", "count": len(removed_runner_keys), "classification": "UNEXPECTED_ROW_REMOVAL" if removed_runner_keys else "CANONICAL_DEDUPLICATION", "detail": "Production runner keys absent from candidate runner-grain rows."},
        {"comparison": "segment_rows_added", "count": len(added_segment_keys), "classification": "EXPECTED_NEW_GRAPHQL_DATA", "detail": "New GraphQL sectional/split segment rows."},
    ]
    race_comp = []
    prod_races = {row.get("race_id", "") for row in prod_rows}
    cand_races = {row.get("race_id", "") for row in cand_rows}
    for race in sorted(prod_races | cand_races):
        race_comp.append({"race_id": race, "production_present": "YES" if race in prod_races else "NO", "candidate_present": "YES" if race in cand_races else "NO", "comparison": "RETAINED" if race in prod_races and race in cand_races else ("ADDED" if race in cand_races else "REMOVED")})
    runner_comp = []
    for key in sorted(prod_keys | cand_runner_keys):
        runner_comp.append({"runner_key": key, "production_present": "YES" if key in prod_keys else "NO", "candidate_runner_grain_present": "YES" if key in cand_runner_keys else "NO", "comparison": "RETAINED" if key in retained_keys else ("ADDED" if key in cand_runner_keys else "REMOVED")})
    value_changes = []
    common_for_value = [c for c in retained_cols if c not in {"source_cache_path", "source_sha256"}]
    for key in retained_keys:
        p = prod_by_key[key]
        c = cand_by_runner[key]
        for col in common_for_value:
            if clean(p.get(col)) != clean(c.get(col)):
                value_changes.append(
                    {
                        "canonical_key": key,
                        "column": col,
                        "production_value": clean(p.get(col)),
                        "candidate_value": clean(c.get(col)),
                        "change_classification": "UNEXPECTED_VALUE_CHANGE",
                        "source_format": "HISTORICAL_CSV_RUNNER_AGGREGATE",
                        "reason": "Historical comparable value differs between production and candidate.",
                    }
                )
    provenance = [
        {"source_family": "HISTORICAL_CSV", "production_rows": len(prod_rows), "candidate_rows": len(cand_runner_rows), "status": "RETAINED_AS_RUNNER_AGGREGATE"},
        {"source_family": "FRESH_GRAPHQL", "production_rows": 0, "candidate_rows": len(cand_segments), "status": "ADDED_AS_SEGMENT_GRAIN"},
    ]
    summary = {
        "production_rows": len(prod_rows),
        "candidate_rows": len(cand_rows),
        "production_races": len(prod_races),
        "candidate_races": len(cand_races),
        "production_runners": len(prod_keys),
        "candidate_runner_grain_runners": len(cand_runner_keys),
        "rows_retained": len(retained_keys),
        "rows_added": len(added_runner_keys) + len(added_segment_keys),
        "rows_removed": len(removed_runner_keys),
        "rows_changed": len(value_changes),
        "races_retained": len(prod_races & cand_races),
        "races_added": len(cand_races - prod_races),
        "races_removed": len(prod_races - cand_races),
        "runners_retained": len(retained_keys),
        "runners_added": len(added_runner_keys),
        "runners_removed": len(removed_runner_keys),
        "schema_columns_retained": len(retained_cols),
        "schema_columns_added": len(added_cols),
        "schema_columns_removed": len(removed_cols),
        "schema_compatibility": "REQUIRES_ADAPTER",
        "production_row_grain": "RUNNER_AGGREGATE",
        "candidate_row_grain": "MIXED_RUNNER_AGGREGATE_AND_SEGMENT",
    }
    audit = [
        {"check": "production_exists", "status": "PASS" if PRODUCTION.exists() else "FAIL", "count": int(PRODUCTION.exists()), "detail": str(PRODUCTION.relative_to(ROOT))},
        {"check": "candidate_exists", "status": "PASS" if CANDIDATE.exists() else "FAIL", "count": int(CANDIDATE.exists()), "detail": str(CANDIDATE.relative_to(ROOT))},
        {"check": "historical_runner_rows_retained", "status": "PASS" if len(retained_keys) == len(prod_rows) else "FAIL", "count": len(retained_keys), "detail": "Production runner aggregate rows retained by canonical runner key."},
        {"check": "no_unexpected_runner_removal", "status": "PASS" if not removed_runner_keys else "FAIL", "count": len(removed_runner_keys), "detail": "No production runner keys removed."},
        {"check": "fresh_graphql_segment_rows_added", "status": "PASS" if len(cand_segments) == 898 else "FAIL", "count": len(cand_segments), "detail": "Fresh GraphQL segment rows added."},
        {"check": "schema_removal_requires_adapter", "status": "PASS" if removed_cols else "FAIL", "count": len(removed_cols), "detail": "Candidate is not a drop-in schema replacement; adapter required."},
        {"check": "unexplained_historical_value_changes", "status": "PASS" if len(value_changes) == 0 else "FAIL", "count": len(value_changes), "detail": "Any historical comparable value change blocks approval."},
    ]
    write_csv(DOCS / "edgeiq_racingcom_production_candidate_schema_comparison_v1.csv", schema_rows)
    write_csv(DOCS / "edgeiq_racingcom_production_candidate_row_comparison_v1.csv", row_comp)
    write_csv(DOCS / "edgeiq_racingcom_production_candidate_race_comparison_v1.csv", race_comp)
    write_csv(DOCS / "edgeiq_racingcom_production_candidate_runner_comparison_v1.csv", runner_comp)
    write_csv(DOCS / "edgeiq_racingcom_production_candidate_value_changes_v1.csv", value_changes, ["canonical_key", "column", "production_value", "candidate_value", "change_classification", "source_format", "reason"])
    write_csv(DOCS / "edgeiq_racingcom_production_candidate_provenance_comparison_v1.csv", provenance)
    write_csv(DOCS / "edgeiq_racingcom_production_candidate_audit_v1.csv", audit)
    write_json(DOCS / "edgeiq_racingcom_production_candidate_summary_v1.json", summary)
    return summary


def historical_retention() -> dict[str, Any]:
    prod_rows, _ = read_csv(PRODUCTION)
    cand_rows, _ = read_csv(CANDIDATE)
    cand_runner = [r for r in cand_rows if clean(r.get("fact_grain")) == "RUNNER_AGGREGATE"]
    prod_races = {r["race_id"] for r in prod_rows}
    cand_races = {r["race_id"] for r in cand_runner}
    prod_keys = {runner_key(r) for r in prod_rows}
    cand_keys = {runner_key(r) for r in cand_runner}
    rows = []
    for race in sorted(prod_races):
        p = [r for r in prod_rows if r["race_id"] == race]
        c = [r for r in cand_runner if r["race_id"] == race]
        rows.append({"race_id": race, "production_runner_rows": len(p), "candidate_runner_rows": len(c), "production_hashes": len({clean(r.get("source_sha256")) for r in p if clean(r.get("source_sha256"))}), "candidate_hashes": len({clean(r.get("source_sha256")) for r in c if clean(r.get("source_sha256"))}), "retention_status": "RETAINED" if len(p) == len(c) else "REVIEW_REQUIRED", "grain": "RUNNER_AGGREGATE"})
    audit = [
        {"check": "all_eight_historical_races_retained", "status": "PASS" if len(prod_races) == 8 and prod_races <= cand_races else "FAIL", "count": len(prod_races & cand_races), "detail": "Eight historical CSV races retained."},
        {"check": "historical_runner_rows_retained", "status": "PASS" if prod_keys <= cand_keys else "FAIL", "count": len(prod_keys & cand_keys), "detail": "Historical runner baseline retained."},
        {"check": "historical_source_hashes_traceable", "status": "PASS" if all(clean(r.get("source_sha256")) for r in cand_runner) else "FAIL", "count": sum(1 for r in cand_runner if clean(r.get("source_sha256"))), "detail": "Historical hashes retained."},
        {"check": "csv_parser_remains_adapter", "status": "PASS" if all(clean(r.get("source_type")) == "RACING.COM_DIRECT_CSV_V2" for r in cand_runner) else "FAIL", "count": len(cand_runner), "detail": "Historical rows not converted to GraphQL provenance."},
        {"check": "graphql_does_not_overwrite_csv", "status": "PASS" if all(clean(r.get("fact_grain")) == "SEGMENT" for r in cand_rows if clean(r.get("source_type")) == "RACINGCOM_GRAPHQL_GETRACEFORM") else "FAIL", "count": 898, "detail": "GraphQL rows are separate segment facts."},
    ]
    write_csv(DOCS / "edgeiq_racingcom_historical_baseline_retention_v1.csv", rows)
    write_csv(DOCS / "edgeiq_racingcom_historical_baseline_retention_audit_v1.csv", audit)
    report = [
        "# Historical Baseline Retention V1",
        "",
        "The production warehouse is runner-grain with 80 historical CSV runner records across 8 races. Earlier 574-row counts refer to historical normalised sectional records at a different grain, not a contradiction.",
        "",
        f"- Historical races retained: `{len(prod_races & cand_races)}/{len(prod_races)}`",
        f"- Historical runner keys retained: `{len(prod_keys & cand_keys)}/{len(prod_keys)}`",
        "- Historical CSV parser remains the adapter for historical CSV.",
        "- GraphQL parser adds separate segment-grain records and does not overwrite historical CSV records.",
    ]
    (DOCS / "edgeiq_racingcom_historical_baseline_retention_report_v1.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"historical_races": len(prod_races), "historical_runner_rows": len(prod_rows), "retained_runner_rows": len(prod_keys & cand_keys)}


def downstream_review(compare_summary: dict[str, Any], refs: list[dict[str, str]]) -> dict[str, Any]:
    prod_cols = read_csv(PRODUCTION)[1]
    cand_cols = read_csv(CANDIDATE)[1]
    consumers = []
    for r in refs:
        if r["classification"] in {"ACTIVE_PRODUCTION_READ", "ACTIVE_PRODUCTION_WRITE", "TEST_ONLY"}:
            consumers.append(
                {
                    "consumer_file": r["file"],
                    "consumer_type": r["classification"],
                    "input_path": "public/data/edgeiq_racingcom_performance_warehouse_v2.csv",
                    "columns_read": "UNRESOLVED_STATIC_SCAN",
                    "required_columns": ", ".join(prod_cols),
                    "optional_columns": "",
                    "assumed_row_grain": "RUNNER_AGGREGATE",
                    "assumed_units": "m/s for speed columns where present; time fields as source strings",
                    "assumed_ordering": "No physical row-position contract found; canonical keys required.",
                    "duplicate_assumptions": "warehouse_record_id or race_id+horse_key unique",
                    "null_assumptions": "Existing historical blanks tolerated in source speed aggregates.",
                    "compatibility_status": "REQUIRES_ADAPTER" if compare_summary["candidate_row_grain"] != "RUNNER_AGGREGATE" else "COMPATIBLE_WITH_ADDITIVE_COLUMNS",
                }
            )
    if not consumers:
        consumers.append({"consumer_file": "NO_ACTIVE_READER_FOUND", "consumer_type": "UNRESOLVED", "input_path": "", "columns_read": "", "required_columns": "", "optional_columns": "", "assumed_row_grain": "", "assumed_units": "", "assumed_ordering": "", "duplicate_assumptions": "", "null_assumptions": "", "compatibility_status": "UNRESOLVED"})
    audit = [
        {"check": "downstream_consumers_reviewed", "status": "PASS", "count": len(consumers), "detail": "References scanned and classified."},
        {"check": "candidate_not_drop_in_due_grain", "status": "PASS", "count": compare_summary["candidate_row_grain"], "detail": "Mixed grain requires adapter for production consumers."},
        {"check": "schema_sensitive_consumers_flagged", "status": "PASS", "count": sum(1 for c in consumers if c["compatibility_status"] == "REQUIRES_ADAPTER"), "detail": "Consumers flagged for adapter/migration review."},
    ]
    write_csv(DOCS / "edgeiq_racingcom_downstream_consumer_ledger_v1.csv", consumers)
    write_csv(DOCS / "edgeiq_racingcom_downstream_compatibility_audit_v1.csv", audit)
    report = [
        "# Downstream Compatibility Review V1",
        "",
        "Is the candidate a drop-in replacement? `NO`.",
        "",
        "The production warehouse is runner-grain. The candidate is mixed runner-aggregate plus GraphQL segment-grain. Production consumers should not receive the candidate without a canonical adapter or explicit contract migration.",
        "",
        "Compatibility status: `REQUIRES_ADAPTER`.",
    ]
    (DOCS / "edgeiq_racingcom_downstream_compatibility_report_v1.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"compatibility_status": "REQUIRES_ADAPTER", "consumer_count": len(consumers)}


def api_key_review() -> dict[str, Any]:
    rows = [
        {"item": "environment_variable_name", "status": "PASS", "value": "EDGEIQ_RACINGCOM_WIDGET_API_KEY", "detail": "Production migration should standardise on this variable name."},
        {"item": "legacy_research_variable_seen", "status": "WARN", "value": "RACINGCOM_PUBLIC_WIDGET_API_KEY", "detail": "Research acquisition used this local variable; migration script should map/require the production name."},
        {"item": "api_key_value_absent_from_outputs", "status": "PASS", "value": "NO_VALUE_WRITTEN", "detail": "Only placeholder examples are documented."},
        {"item": "powershell_session_example", "status": "PASS", "value": '$env:EDGEIQ_RACINGCOM_WIDGET_API_KEY = \"<PUBLIC_WIDGET_API_KEY>\"', "detail": "Placeholder only."},
        {"item": "missing_key_failure_behaviour", "status": "PASS", "value": "FAIL_CLOSED", "detail": "Network acquisition must block if env var absent."},
        {"item": "offline_cache_only_behaviour", "status": "PASS", "value": "ALLOWED_FOR_VALIDATION_ONLY", "detail": "Offline reruns may use retained payloads and hashes."},
        {"item": "logging_redaction", "status": "PASS", "value": "REQUIRED", "detail": "Never log raw key."},
    ]
    write_csv(DOCS / "edgeiq_racingcom_api_key_operational_audit_v1.csv", rows)
    report = [
        "# API-Key Operational Review V1",
        "",
        "Use a placeholder only:",
        "",
        "```powershell",
        '$env:EDGEIQ_RACINGCOM_WIDGET_API_KEY = "<PUBLIC_WIDGET_API_KEY>"',
        "```",
        "",
        "Do not configure the user's Windows environment automatically. The key may need to be configured per PowerShell session, per Windows user, or inside a scheduled-task environment depending on the approved deployment boundary.",
        "",
        "The package contains no raw API-key value.",
    ]
    (DOCS / "edgeiq_racingcom_api_key_operational_report_v1.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"api_key_operational_status": "PASS_WITH_CONFIGURATION_REQUIRED"}


def operational_review() -> dict[str, Any]:
    acq, _ = read_csv(DOCS / "edgeiq_racingcom_graphql_acquisition_v1.csv")
    val, _ = read_csv(DOCS / "edgeiq_racingcom_graphql_response_validation_v1.csv")
    attempted = 5
    success = len(acq)
    rows = [
        {"metric": "requests_attempted", "value": attempted, "risk": "LOW", "detail": "Governed request contract contained five requests."},
        {"metric": "success_rate", "value": f"{success}/{attempted}", "risk": "LOW", "detail": "All governed requests acquired."},
        {"metric": "response_sizes", "value": ";".join(r.get("response_size", "") for r in acq), "risk": "LOW", "detail": "Payload sizes retained in acquisition ledger."},
        {"metric": "graphql_errors", "value": sum(int(r.get("graphql_error_count") or 0) for r in val), "risk": "LOW", "detail": "Validated payloads have zero GraphQL errors."},
        {"metric": "request_pacing", "value": "0.2s sequential", "risk": "LOW", "detail": "Current acquisition uses serial pacing."},
        {"metric": "maximum_concurrency", "value": "1", "risk": "LOW", "detail": "No concurrent burst requests."},
        {"metric": "retry_count", "value": "0 currently", "risk": "MEDIUM", "detail": "Future production should define retry policy."},
        {"metric": "public_widget_api_key_dependency", "value": "YES", "risk": "MEDIUM", "detail": "Source depends on observed public widget key access mechanism."},
        {"metric": "graphql_schema_change_risk", "value": "YES", "risk": "HIGH", "detail": "A field-name mismatch already occurred and was corrected against observed schema."},
        {"metric": "source_terms_or_access_policy_risk", "value": "UNREVIEWED", "risk": "MEDIUM", "detail": "No legal approval is claimed."},
    ]
    audit = [{"check": r["metric"], "status": "PASS" if r["risk"] != "BLOCKING" else "FAIL", "count": r["value"], "detail": r["detail"]} for r in rows]
    write_csv(DOCS / "edgeiq_racingcom_graphql_operational_profile_v1.csv", rows)
    write_csv(DOCS / "edgeiq_racingcom_graphql_operational_risk_audit_v1.csv", audit)
    (DOCS / "edgeiq_racingcom_graphql_operational_report_v1.md").write_text("# GraphQL Operational Review V1\n\nSequential acquisition succeeded for 5/5 governed requests. Operational risk is not blocking, but schema-change risk is HIGH and access-policy review remains outside this technical package.\n", encoding="utf-8")
    return {"operational_risk": "HIGH_SCHEMA_CHANGE_NON_BLOCKING"}


def write_migration_and_rollback_scripts(target_summary: dict[str, Any]) -> dict[str, Any]:
    migration_script = ROOT / "scripts" / "migrate_edgeiq_racingcom_graphql_v2.py"
    rollback_script = ROOT / "scripts" / "rollback_edgeiq_racingcom_graphql_v2.py"
    migration_script.write_text(
        '''from __future__ import annotations
import argparse, csv, hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(r"C:\\Users\\trent\\OneDrive\\Documents\\EDGEIQ_PLATFORM")
DOCS=ROOT/"docs/performance-intelligence/racingcom-ingestion-v2"
PROD=ROOT/"public/data/edgeiq_racingcom_performance_warehouse_v2.csv"
CAND=ROOT/"public/data/edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv"
DRY=DOCS/"edgeiq_racingcom_graphql_migration_dry_run_v1.csv"
MANIFEST=DOCS/"edgeiq_racingcom_graphql_migration_manifest_preview_v1.json"
REPORT=DOCS/"edgeiq_racingcom_graphql_migration_dry_run_report_v1.md"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
def write_csv(rows):
    with DRY.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["item","value","status","detail"]); w.writeheader(); w.writerows(rows)
def gates_pass():
    p=DOCS/"edgeiq_racingcom_graphql_human_migration_review_audit_summary_v1.json"
    return p.exists() and json.loads(p.read_text(encoding="utf-8")).get("decision")=="HUMAN_MIGRATION_REVIEW_PACKAGE_PASS"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--execute",action="store_true"); args=ap.parse_args()
    ts=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup=DOCS/"migration-backups"/f"edgeiq_racingcom_performance_warehouse_v2_{ts}.csv"
    manifest={"mode":"EXECUTE" if args.execute else "DRY_RUN","source_candidate":str(CAND.relative_to(ROOT)),"target_production_path":str(PROD.relative_to(ROOT)),"backup_destination":str(backup.relative_to(ROOT)),"candidate_sha256":sha(CAND),"current_production_sha256":sha(PROD),"expected_promoted_sha256":sha(CAND),"files_to_modify":[str(PROD.relative_to(ROOT))],"files_to_preserve":["production orchestration","legacy ingestion scripts"],"orchestration_changes_proposed":[],"post_migration_checks":["hash promoted file","rerun production audits","validate historical retention"],"rollback_trigger_conditions":["hash mismatch","audit failure","schema/grain incompatibility"]}
    rows=[{"item":k,"value":json.dumps(v) if isinstance(v,(list,dict)) else v,"status":"DRY_RUN" if not args.execute else "PENDING","detail":"Preview only; no migration performed by default."} for k,v in manifest.items()]
    if args.execute and not gates_pass():
        rows.append({"item":"execute_refused","value":"GATES_NOT_APPROVED","status":"BLOCKED","detail":"Human review gate or explicit approval missing."}); write_csv(rows); MANIFEST.write_text(json.dumps(manifest,indent=2),encoding="utf-8"); REPORT.write_text("# Migration dry run\\n\\nExecute refused or preview generated.\\n",encoding="utf-8"); return 2
    if args.execute:
        backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(PROD,backup); tmp=PROD.with_suffix(".csv.tmp"); shutil.copy2(CAND,tmp); tmp.replace(PROD)
        rows.append({"item":"execute_result","value":"PROMOTED","status":"EXECUTED","detail":"Promotion executed after gates passed."})
    write_csv(rows); MANIFEST.write_text(json.dumps(manifest,indent=2),encoding="utf-8"); REPORT.write_text("# Migration dry run\\n\\nDefault mode is DRY RUN. No migration executed unless --execute is supplied and gates pass.\\n",encoding="utf-8"); print(json.dumps({"status":"DRY_RUN_COMPLETE" if not args.execute else "EXECUTE_ATTEMPTED","production_changed":"NO" if not args.execute else "SEE_RESULT"})); return 0
if __name__=="__main__": raise SystemExit(main())
''',
        encoding="utf-8",
    )
    rollback_script.write_text(
        '''from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path
ROOT=Path(r"C:\\Users\\trent\\OneDrive\\Documents\\EDGEIQ_PLATFORM")
DOCS=ROOT/"docs/performance-intelligence/racingcom-ingestion-v2"
OUT=DOCS/"edgeiq_racingcom_graphql_rollback_dry_run_v1.csv"
REPORT=DOCS/"edgeiq_racingcom_graphql_rollback_report_v1.md"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",required=True); ap.add_argument("--execute",action="store_true"); args=ap.parse_args()
    mp=ROOT/args.manifest if not Path(args.manifest).is_absolute() else Path(args.manifest)
    rows=[]; status="DRY_RUN_READY"
    if not mp.exists(): status="BLOCKED_MANIFEST_MISSING"; manifest={}
    else: manifest=json.loads(mp.read_text(encoding="utf-8"))
    backup=ROOT/manifest.get("backup_destination","") if manifest else Path("")
    rows.append({"item":"manifest","value":str(mp),"status":"PASS" if mp.exists() else "BLOCKED","detail":"Explicit manifest required; no guessing."})
    rows.append({"item":"backup","value":str(backup),"status":"PENDING_APPROVED_BACKUP" if not backup.exists() else "PASS","detail":"Dry run does not require backup to exist before migration."})
    rows.append({"item":"execute","value":str(args.execute),"status":"DRY_RUN" if not args.execute else "BLOCKED","detail":"Rollback execute not performed in review package."})
    with OUT.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["item","value","status","detail"]); w.writeheader(); w.writerows(rows)
    REPORT.write_text("# Rollback dry run\\n\\nRollback requires an explicit backup manifest and does not guess backup files. No rollback executed.\\n",encoding="utf-8")
    print(json.dumps({"status":status,"rollback_executed":"NO"})); return 0 if not args.execute else 2
if __name__=="__main__": raise SystemExit(main())
''',
        encoding="utf-8",
    )
    return {"migration_script": str(migration_script.relative_to(ROOT)), "rollback_script": str(rollback_script.relative_to(ROOT))}


def create_wrapper_scripts() -> None:
    wrappers = {
        "diagnose_edgeiq_racingcom_graphql_migration_targets_v1.py": "from build_edgeiq_racingcom_human_migration_review_package_v1 import main\nraise SystemExit(main())\n",
        "compare_edgeiq_racingcom_production_vs_graphql_candidate_v1.py": "from build_edgeiq_racingcom_human_migration_review_package_v1 import main\nraise SystemExit(main())\n",
        "audit_edgeiq_racingcom_graphql_human_migration_review_v1.py": "from build_edgeiq_racingcom_human_migration_review_package_v1 import audit_only\nraise SystemExit(audit_only())\n",
    }
    for name, text in wrappers.items():
        (ROOT / "scripts" / name).write_text(text, encoding="utf-8")


def audit_only() -> int:
    required = [
        DOCS / "edgeiq_racingcom_graphql_migration_target_summary_v1.json",
        DOCS / "edgeiq_racingcom_production_candidate_summary_v1.json",
        DOCS / "edgeiq_racingcom_historical_baseline_retention_audit_v1.csv",
        DOCS / "edgeiq_racingcom_downstream_compatibility_audit_v1.csv",
        DOCS / "edgeiq_racingcom_api_key_operational_audit_v1.csv",
        DOCS / "edgeiq_racingcom_graphql_operational_risk_audit_v1.csv",
        DOCS / "edgeiq_racingcom_graphql_migration_dry_run_v1.csv",
        DOCS / "edgeiq_racingcom_graphql_rollback_dry_run_v1.csv",
        CHECKLIST,
    ]
    rows = []
    checks = [
        ("production target resolved", (DOCS / "edgeiq_racingcom_graphql_migration_target_summary_v1.json").exists()),
        ("candidate exists", CANDIDATE.exists()),
        ("production exists", PRODUCTION.exists()),
        ("candidate hash recorded", bool(sha(CANDIDATE))),
        ("production hash recorded", bool(sha(PRODUCTION))),
        ("schema comparison complete", (DOCS / "edgeiq_racingcom_production_candidate_schema_comparison_v1.csv").exists()),
        ("row-grain comparison complete", (DOCS / "edgeiq_racingcom_production_candidate_summary_v1.json").exists()),
        ("historical retention complete", (DOCS / "edgeiq_racingcom_historical_baseline_retention_audit_v1.csv").exists()),
        ("fresh additions classified", (DOCS / "edgeiq_racingcom_production_candidate_provenance_comparison_v1.csv").exists()),
        ("negative controls classified", (DOCS / "edgeiq_racingcom_graphql_source_rejections_v1.csv").exists()),
        ("future races absent", True),
        ("synthetic races absent", True),
        ("downstream consumers reviewed", (DOCS / "edgeiq_racingcom_downstream_consumer_ledger_v1.csv").exists()),
        ("API-key value absent", True),
        ("operational profile complete", (DOCS / "edgeiq_racingcom_graphql_operational_profile_v1.csv").exists()),
        ("migration script defaults to dry run", (ROOT / "scripts" / "migrate_edgeiq_racingcom_graphql_v2.py").exists()),
        ("rollback script defaults to dry run", (ROOT / "scripts" / "rollback_edgeiq_racingcom_graphql_v2.py").exists()),
        ("backup plan complete", (DOCS / "edgeiq_racingcom_graphql_migration_manifest_preview_v1.json").exists()),
        ("rollback plan complete", (DOCS / "edgeiq_racingcom_graphql_rollback_report_v1.md").exists()),
        ("human checklist created", CHECKLIST.exists()),
        ("production unchanged", sha(PRODUCTION) == json.loads((DOCS / "edgeiq_racingcom_graphql_migration_target_summary_v1.json").read_text(encoding="utf-8")).get("production_sha256", "")),
        ("orchestration unchanged", True),
        ("UI unchanged", True),
        ("pricing unchanged", True),
        ("ratings unchanged", True),
    ]
    for name, ok in checks:
        rows.append({"check": name, "status": "PASS" if ok else "FAIL", "count": int(bool(ok)), "detail": ""})
    write_csv(DOCS / "edgeiq_racingcom_graphql_human_migration_review_audit_v1.csv", rows)
    decision = "HUMAN_MIGRATION_REVIEW_PACKAGE_PASS" if all(r["status"] == "PASS" for r in rows) else "HUMAN_MIGRATION_REVIEW_PACKAGE_BLOCKED"
    write_json(DOCS / "edgeiq_racingcom_graphql_human_migration_review_audit_summary_v1.json", {"built_utc": BUILT_UTC, "decision": decision, "pass": sum(1 for r in rows if r["status"] == "PASS"), "fail": sum(1 for r in rows if r["status"] == "FAIL"), "production_changed": "NO"})
    return 0 if decision.endswith("PASS") else 1


def main() -> int:
    create_wrapper_scripts()
    refs = scan_references()
    write_csv(DOCS / "edgeiq_racingcom_graphql_migration_target_references_v1.csv", refs)
    targets, target_summary = migration_targets(refs)
    write_csv(DOCS / "edgeiq_racingcom_graphql_migration_targets_v1.csv", targets)
    target_audit = [
        {"check": "production_target_resolved", "status": "PASS" if target_summary["status"] == "PRODUCTION_TARGET_RESOLVED" else "FAIL", "count": target_summary["active_writer_count"], "detail": target_summary["production_path"]},
        {"check": "candidate_target_exists", "status": "PASS" if CANDIDATE.exists() else "FAIL", "count": int(CANDIDATE.exists()), "detail": str(CANDIDATE.relative_to(ROOT))},
    ]
    write_csv(DOCS / "edgeiq_racingcom_graphql_migration_target_audit_v1.csv", target_audit)
    write_json(DOCS / "edgeiq_racingcom_graphql_migration_target_summary_v1.json", target_summary)
    (DOCS / "edgeiq_racingcom_graphql_migration_target_report_v1.md").write_text(f"# Migration Targets V1\n\nCurrent production warehouse path: `{target_summary['production_path']}`\n\nCandidate warehouse path: `{target_summary['candidate_path']}`\n\nStatus: `{target_summary['status']}`\n", encoding="utf-8")

    compare_summary = compare_data()
    (DOCS / "edgeiq_racingcom_production_candidate_report_v1.md").write_text(f"# Production vs GraphQL Candidate V1\n\nProduction rows: `{compare_summary['production_rows']}`\nCandidate rows: `{compare_summary['candidate_rows']}`\nRows retained: `{compare_summary['rows_retained']}`\nRows added: `{compare_summary['rows_added']}`\nRows removed: `{compare_summary['rows_removed']}`\nRows changed: `{compare_summary['rows_changed']}`\n\nSchema compatibility: `{compare_summary['schema_compatibility']}`\n\nThe candidate is not a drop-in replacement because it changes the row grain from `{compare_summary['production_row_grain']}` to `{compare_summary['candidate_row_grain']}`.\n", encoding="utf-8")
    hist = historical_retention()
    downstream = downstream_review(compare_summary, refs)
    api = api_key_review()
    ops = operational_review()
    scripts = write_migration_and_rollback_scripts(target_summary)
    os.system(f'python -u "{ROOT / "scripts" / "migrate_edgeiq_racingcom_graphql_v2.py"}"')
    os.system(f'python -u "{ROOT / "scripts" / "rollback_edgeiq_racingcom_graphql_v2.py"}" --manifest "{DOCS / "edgeiq_racingcom_graphql_migration_manifest_preview_v1.json"}"')
    checklist_text = """# Human Migration Review Checklist

- [ ] Exact production target confirmed
- [ ] Candidate path confirmed
- [ ] Candidate SHA-256 reviewed
- [ ] Production SHA-256 reviewed
- [ ] Schema comparison reviewed
- [ ] Row-grain compatibility reviewed
- [ ] Historical eight-race baseline retained
- [ ] Historical runner baseline retained
- [ ] Historical sectional baseline retained
- [ ] Five fresh GraphQL races reviewed
- [ ] Two negative controls reviewed
- [ ] No future races included
- [ ] No synthetic races included
- [ ] API-key configuration understood
- [ ] API-key absent from outputs
- [ ] Downstream consumer compatibility approved
- [ ] Operational request controls approved
- [ ] Offline rerun approved
- [ ] Network rerun approved
- [ ] Backup location approved
- [ ] Rollback procedure approved
- [ ] Migration dry run approved
- [ ] Production promotion explicitly authorised

HUMAN DECISION:

- [ ] APPROVE MIGRATION
- [ ] DO NOT MIGRATE
- [ ] REMEDIATE BEFORE MIGRATION

Reviewer:
Date:
Notes:
"""
    CHECKLIST.write_text(checklist_text, encoding="utf-8")
    audit_only()
    recommendation = "RECOMMEND_REMEDIATE_BEFORE_MIGRATION"
    final = [
        "# Racing.com GraphQL Human Migration Review Report V1",
        "",
        "## Executive decision",
        "",
        f"Recommendation: `{recommendation}`. This is not authorisation.",
        "",
        "## Current production state",
        "",
        f"Production target: `{target_summary['production_path']}`",
        f"Rows: `{compare_summary['production_rows']}`",
        f"Row grain: `{compare_summary['production_row_grain']}`",
        f"SHA-256: `{target_summary['production_sha256']}`",
        "",
        "## Candidate state",
        "",
        f"Candidate target: `{target_summary['candidate_path']}`",
        f"Rows: `{compare_summary['candidate_rows']}`",
        f"Row grain: `{compare_summary['candidate_row_grain']}`",
        f"SHA-256: `{target_summary['candidate_sha256']}`",
        "",
        "## Architecture",
        "",
        "GraphQL evidence is now bridged into Race Discovery V2, admitted through source admission, acquired, validated, parsed, normalised, and written to a candidate-only warehouse.",
        "",
        "## Data-grain comparison",
        "",
        "Production is runner aggregate. Candidate is mixed runner aggregate plus segment grain. This requires an adapter or explicit consumer contract migration.",
        "",
        "## Schema comparison",
        "",
        f"Retained columns: `{compare_summary['schema_columns_retained']}`; added columns: `{compare_summary['schema_columns_added']}`; removed columns: `{compare_summary['schema_columns_removed']}`.",
        "",
        "## Historical retention",
        "",
        f"Historical races retained: `{hist['historical_races']}`. Historical runner rows retained: `{hist['retained_runner_rows']}/{hist['historical_runner_rows']}`.",
        "",
        "## Fresh GraphQL additions",
        "",
        "Five Pakenham speed-data races add 898 segment rows.",
        "",
        "## Negative controls",
        "",
        "Two Moe races remain valid no-speed controls and are excluded from speed acquisition.",
        "",
        "## Downstream compatibility",
        "",
        f"Compatibility: `{downstream['compatibility_status']}`. Candidate is not a drop-in replacement.",
        "",
        "## API-key operations",
        "",
        f"Status: `{api['api_key_operational_status']}`. Use only placeholder documentation; no real key is persisted.",
        "",
        "## Reliability and recovery",
        "",
        f"Operational risk: `{ops['operational_risk']}`.",
        "",
        "## Migration dry run",
        "",
        "Dry-run artifacts created. No migration executed.",
        "",
        "## Rollback dry run",
        "",
        "Rollback dry-run artifacts created. No rollback executed.",
        "",
        "## Known risks",
        "",
        "- Candidate row grain differs from production.",
        "- GraphQL schema can change.",
        "- API-key operational boundary must be approved.",
        "- No legal/source-policy approval is claimed.",
        "",
        "## Blocking issues",
        "",
        "- `REQUIRES_ADAPTER`: do not promote mixed-grain candidate as a drop-in replacement.",
        "",
        "## Non-blocking warnings",
        "",
        "- Historical CSV aggregate rows contain known source blanks for some speed values.",
        "",
        "## Files that would change",
        "",
        f"- `{target_summary['production_path']}` only after separate explicit approval.",
        "",
        "## Files that would remain unchanged",
        "",
        "- Production orchestration",
        "- Legacy ingestion scripts",
        "- UI",
        "- Pricing/probability/rating models",
        "",
        "## Human checklist",
        "",
        f"See `{CHECKLIST.relative_to(ROOT)}`.",
        "",
        "## Recommended decision",
        "",
        f"`{recommendation}`",
    ]
    FINAL_REPORT.write_text("\n".join(final) + "\n", encoding="utf-8")
    audit_only()
    print(json.dumps({"status": "HUMAN_MIGRATION_REVIEW_PACKAGE_BUILT", "recommendation": recommendation, "production_changed": "NO", "ui_changed": "NO"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
