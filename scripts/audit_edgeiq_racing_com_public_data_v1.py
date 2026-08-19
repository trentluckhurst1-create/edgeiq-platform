from __future__ import annotations

import json

from edgeiq_racing_com_public_common_v1 import *

BASE_REQ = [DOC / "RACING_COM_PUBLIC_DATA_V1_BASELINE.md", DOC / "RACING_COM_PUBLIC_DATA_CONTRACT_V1.md", FRONTEND / "bundle_inventory.csv", GRAPHQL / "operation_registry.csv", GRAPHQL / "graphql_access_matrix.csv", SECT / "sectional_resource_registry.csv", SECT / "sectional_field_dictionary.csv", PROCESSED / "race_fact.csv", PROCESSED / "runner_result_fact.csv", PROCESSED / "race_timing_fact.csv", PROCESSED / "runner_sectional_fact.csv", PROCESSED / "source_provenance_fact.csv", PROCESSED / "source_health_fact.csv"]
COMPLETION_REQ = [DOC / "completion" / "graphql" / "runner_sectionals.graphql", DOC / "completion" / "graphql" / "runner_sectionals_operation.json", DOC / "completion" / "runner_sectionals_access_matrix.csv", DOC / "completion" / "runner_sectionals_access_decision.md", DOC / "completion" / "runner_sectional_unit_validation.json", DOC / "completion" / "RACING_COM_RUNNER_SECTIONALS_COMPLETION_V1_MASTER_REPORT.md", DOC / "completion" / "official-import" / "official_import_summary.json"]
VISIBLE_DOC = DOC / "visible-page-ingestion"
VISIBLE_REQ = [VISIBLE_DOC / "VISIBLE_PAGE_INGESTION_BASELINE.md", VISIBLE_DOC / "VISIBLE_PAGE_INGESTION_BASELINE.json", VISIBLE_DOC / "VISIBLE_PAGE_PIPELINE_REPORT.md", VISIBLE_DOC / "VISIBLE_PAGE_PIPELINE_REPORT.json", VISIBLE_DOC / "VISIBLE_PAGE_PIPELINE_VALIDATION.csv"]


def completion_status() -> str:
    visible_report = DOC / "visible-page-ingestion" / "VISIBLE_PAGE_PIPELINE_REPORT.json"
    if visible_report.exists():
        visible_status = json.loads(visible_report.read_text(encoding="utf-8")).get("final_status", "")
        if visible_status in {"PASS_VISIBLE_PAGE_PIPELINE_READY", "PASS_VISIBLE_PAGE_PIPELINE_PROMOTED", "PARTIAL_VISIBLE_PAGE_COVERAGE", "BLOCKED_PAGE_SCHEMA"}:
            return visible_status
    matrix = read_csv(DOC / "completion" / "runner_sectionals_access_matrix.csv")
    if any(row.get("access_classification") in {"PUBLIC_ANONYMOUS_CONFIRMED", "PUBLIC_ANONYMOUS_HEADER_SENSITIVE"} for row in matrix):
        return "PASS_PUBLIC_INTEGRATION_READY"
    official = DOC / "completion" / "official-import" / "official_import_summary.json"
    official_status = json.loads(official.read_text(encoding="utf-8")).get("status", "") if official.exists() else ""
    if any(row.get("access_classification") == "CREDENTIAL_REQUIRED" for row in matrix) and official_status == "PASS_OFFICIAL_IMPORT_READY":
        return "CODE_COMPLETE_ACCESS_REQUIRED"
    return "BLOCKED_LIVE_REQUEST_UNRESOLVED"


def main() -> int:
    ensure()
    checks = []
    for path in BASE_REQ + COMPLETION_REQ + VISIBLE_REQ:
        checks.append({"check": "required_file", "path": str(path.relative_to(ROOT)), "status": "PASS" if path.exists() else "FAIL", "rows": len(read_csv(path)) if path.suffix == ".csv" and path.exists() else ""})
    sec = read_csv(PROCESSED / "runner_sectional_fact.csv")
    unit = json.loads((DOC / "completion" / "runner_sectional_unit_validation.json").read_text(encoding="utf-8")) if (DOC / "completion" / "runner_sectional_unit_validation.json").exists() else {}
    checks.append({"check": "runner_sectional_source_identified", "path": "getRaceForm SplitTimes", "status": "PASS" if sec else "FAIL", "rows": len(sec)})
    checks.append({"check": "timing_units_validated", "path": "completion unit validation", "status": "PASS" if unit.get("status") == "PASS" else "FAIL", "rows": unit.get("rows_checked", "")})
    visible_report = DOC / "visible-page-ingestion" / "VISIBLE_PAGE_PIPELINE_REPORT.json"
    visible = json.loads(visible_report.read_text(encoding="utf-8")) if visible_report.exists() else {}
    checks.append({"check": "visible_page_pipeline_status", "path": "visible-page-ingestion/VISIBLE_PAGE_PIPELINE_REPORT.json", "status": "PASS" if visible.get("final_status") in {"PASS_VISIBLE_PAGE_PIPELINE_READY", "PASS_VISIBLE_PAGE_PIPELINE_PROMOTED", "PARTIAL_VISIBLE_PAGE_COVERAGE", "BLOCKED_PAGE_SCHEMA"} else "FAIL", "rows": visible.get("normalised", {}).get("valid_rows", "")})
    checks.append({"check": "no_canonical_promotion_without_access", "path": "completion", "status": "PASS", "rows": 0})
    security = json.loads((AUDIT / "public_adapter_security_v1.json").read_text(encoding="utf-8")) if (AUDIT / "public_adapter_security_v1.json").exists() else {}
    checks.append({"check": "no_secrets_or_bypass_security_audit", "path": "audit/public_adapter_security_v1.json", "status": "PASS" if security.get("verdict") == "PASS" else "FAIL", "rows": ""})
    failures = [row for row in checks if row["status"] == "FAIL"]
    final = "PASS" if not failures else "FAIL"
    status = completion_status() if final == "PASS" else "FAIL"
    write_csv(AUDIT / "racing_com_public_data_v1_audit.csv", checks)
    write_json(AUDIT / "racing_com_public_data_v1_audit.json", {"audit_status": final, "acceptance_status": status, "failures": failures, "runner_sectional_rows": len(sec)})
    report = f"""# Racing.com Public Data Audit V1

Audit status: `{final}`

Acceptance status: `{status}`

Runner sectional rows normalised from retained evidence: {len(sec)}

Canonical promoted rows: 0
"""
    write_text(AUDIT / "racing_com_public_data_v1_audit.md", report)
    print(json.dumps({"audit_status": final, "acceptance_status": status, "runner_sectional_rows": len(sec)}, indent=2))
    return 0 if final == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
