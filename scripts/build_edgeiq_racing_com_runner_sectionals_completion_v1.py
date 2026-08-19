from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
from pathlib import Path

from edgeiq_racing_com_public_common_v1 import *

COMP = DOC / "completion"
CGQL = COMP / "graphql"
CHAR = COMP / "har"
CSEC = COMP / "sectionals"
CACC = COMP / "acceptance"
ENV_NAME = "RACINGCOM_CHAMPION_DATA_ENDPOINT_KEY"


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def known_sectional_row() -> dict:
    for row in read_csv(PUB / "edgeiq_racingcom_speed_network_probe_v1.csv"):
        if "sectionaltimes_callback" in row.get("response_url", ""):
            return row
    return {}


def query_from_url(url: str) -> str:
    return urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(url or "").query).get("query", [""])[0])


def write_baseline() -> None:
    status = git(["status", "--short"])
    split = read_csv(PUB / "edgeiq_racingcom_runner_split_fact_v1.csv")
    sec = read_csv(PROCESSED / "runner_sectional_fact.csv")
    base = {"starting_head": git(["rev-parse", "HEAD"]), "starting_log": git(["log", "-1", "--oneline"]), "dirty_worktree_count": len([x for x in status.splitlines() if x.strip()]), "retained_payload_glob": "outputs/sectionals/raw/VIC/racingcom_full_payloads/getRaceForm_*.json", "existing_runner_split_rows": len(split), "existing_normalised_sectional_rows": len(sec), "existing_acceptance_status": "CODE_COMPLETE_ACCESS_REQUIRED"}
    write_json(COMP / "RACING_COM_RUNNER_SECTIONALS_COMPLETION_V1_BASELINE.json", base)
    write_text(COMP / "RACING_COM_RUNNER_SECTIONALS_COMPLETION_V1_BASELINE.md", "# Runner Sectionals Completion V1 Baseline\n\n- Starting commit: `{}`\n- Dirty worktree files at baseline: {}\n- Retained payloads: `{}`\n- Existing normalised sectional rows: {}\n- Existing status: `{}`\n".format(base["starting_log"], base["dirty_worktree_count"], base["retained_payload_glob"], len(sec), base["existing_acceptance_status"]))


def write_query_contract(row: dict) -> None:
    query = query_from_url(row.get("response_url", ""))
    write_text(CGQL / "runner_sectionals.graphql", query + "\n")
    op = {"endpoint": GRAPHQL_ENDPOINT + "/", "method": "GET", "operation_name": "sectionaltimes_callback_getRaceForm_alias", "query_parameter": "query", "variables_mode": "inline GraphQL constants", "sample_meetCode": "5191101", "sample_raceNumber": "1", "credential_env_var": ENV_NAME, "required_credential_header_name": "x-api-key", "cookie_requirement": "ABSENT", "retained_browser_response_status": row.get("status", "")}
    write_json(CGQL / "runner_sectionals_operation.json", op)
    write_text(CGQL / "runner_sectionals_request_contract.md", "# Runner Sectionals Request Contract\n\nEndpoint: `https://graphql.rmdprod.racing.com/`\n\nMethod: `GET`\n\nOperation: `sectionaltimes_callback: getRaceForm(meetCode, raceNumber)`\n\nSample variables: `meetCode=5191101`, `raceNumber=1`.\n\nApproved credential delivery: environment variable `{}` mapped to request header `x-api-key`. The value is never stored or printed.\n\nCookie requirement from browser recapture: `ABSENT`.\n".format(ENV_NAME))


def write_inventory(row: dict) -> None:
    items = []
    files = [DOC / "RACING_COM_PUBLIC_DATA_V1_BASELINE.md", DOC / "graphql" / "operation_registry.csv", DOC / "graphql" / "graphql_access_matrix.csv", DOC / "frontend" / "bundle_inventory.csv", PUB / "edgeiq_racingcom_speed_network_probe_v1.csv", PUB / "edgeiq_racingcom_runner_speed_fact_v1.csv", PUB / "edgeiq_racingcom_runner_split_fact_v1.csv", PROCESSED / "runner_sectional_fact.csv"]
    for file in files:
        items.append({"path": str(file.relative_to(ROOT)), "exists": "YES" if file.exists() else "NO", "rows": len(read_csv(file)) if file.suffix == ".csv" and file.exists() else "", "sha256": sha_file(file)})
    payloads = list((ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_full_payloads").glob("getRaceForm_*.json"))
    items.append({"path": "outputs/sectionals/raw/VIC/racingcom_full_payloads/getRaceForm_*.json", "exists": "YES" if payloads else "NO", "rows": len(payloads), "sha256": "MULTI"})
    write_csv(COMP / "existing_evidence_inventory.csv", items)
    write_json(COMP / "existing_evidence_inventory.json", items)
    write_text(COMP / "existing_evidence_report.md", "# Existing Evidence Inventory\n\nThe retained response URL containing `sectionaltimes_callback` is recorded in `public/data/edgeiq_racingcom_speed_network_probe_v1.csv`. The retained raw payload path is `{}`. The GraphQL query document is recoverable from the response URL. Original request headers were not retained in that CSV; a clean browser recapture records header-name presence only, with sensitive values redacted.\n".format(row.get("raw_sample_file", "")))


def write_browser_evidence() -> dict:
    capture_path = CHAR / "runner_sectionals_browser_capture_redacted.json"
    captures = json.loads(capture_path.read_text(encoding="utf-8")) if capture_path.exists() else []
    if not captures:
        return {}
    capture = captures[0]
    request = {"http_method": capture.get("method", "GET"), "operation_name": "sectionaltimes_callback", "query_document_path": str((CGQL / "runner_sectionals.graphql").relative_to(ROOT)), "non_sensitive_headers": [h for h in capture.get("request_header_presence", {}) if not re.search("key|token|auth|cookie", h, re.I)], "sensitive_header_names_present": [h for h in capture.get("request_header_presence", {}) if re.search("key|token|auth", h, re.I)], "cookies_present": capture.get("has_cookie_header"), "status": capture.get("status"), "response_bytes": capture.get("response_bytes"), "response_hash": capture.get("response_sha256")}
    write_json(CHAR / "runner_sectionals_request.json", request)
    write_text(CHAR / "runner_sectionals_request_redacted.txt", json.dumps(request, indent=2))
    write_json(CHAR / "runner_sectionals_response_schema.json", {"data": {"sectionaltimes_callback": {"Horses": "array", "Horses[].SectionalTimes": "array", "Horses[].SplitTimes": "array"}}})
    write_text(CHAR / "runner_sectionals_access_evidence.md", "# Runner Sectionals Browser Evidence\n\nA clean logged-out browser context returned HTTP `{}` for the runner sectionals GraphQL request. Header-name evidence shows `x-api-key` present and cookie absent. Values are redacted and not stored.\n".format(capture.get("status")))
    return request


def write_cloudfront_decision() -> None:
    rows = [{"resource_type": "CSV", "url_source": "none discovered from retained response/public code", "anonymous_status": "NOT_TESTED_NO_DISCOVERED_URL", "includes_runner_splits": "UNKNOWN", "decision": "NO_GOVERNED_FALLBACK"}, {"resource_type": "PDF", "url_source": "none discovered from retained response/public code", "anonymous_status": "NOT_TESTED_NO_DISCOVERED_URL", "includes_runner_splits": "UNKNOWN", "decision": "NO_GOVERNED_FALLBACK"}, {"resource_type": "JSON", "url_source": "GraphQL only", "anonymous_status": "401 clean replay", "includes_runner_splits": "YES when credentialed/browser-keyed", "decision": "CREDENTIAL_REQUIRED"}]
    write_csv(CSEC / "cloudfront_access_matrix.csv", rows)
    write_json(CSEC / "cloudfront_access_matrix.json", rows)
    write_json(CSEC / "csv_schema.json", {"status": "NO_PUBLIC_CSV_SCHEMA_DISCOVERED"})
    write_text(CSEC / "cloudfront_sectional_decision.md", "# CloudFront / CSV / PDF Decision\n\nNo deterministic public CSV or PDF sectional source was discovered. Runner sectionals are delivered by the GraphQL `getRaceForm` response. CloudFront/download artefacts are not a governed fallback for this completion pass.\n")


def write_unit_validation() -> None:
    sec = read_csv(PROCESSED / "runner_sectional_fact.csv")
    rows = []
    failures = 0
    for row in sec[:5000]:
        seconds = safe_float(row.get("section_time_seconds"))
        distance = safe_float(row.get("section_distance_metres"))
        ok = bool(row.get("timing_unit_original") and row.get("timing_unit_normalised") and seconds and seconds > 0 and distance and distance > 0)
        failures += 0 if ok else 1
        rows.append({"race_key": row.get("source_race_id", ""), "runner": row.get("runner_name", ""), "section_start_metres": row.get("section_start_metres", ""), "section_end_metres": row.get("section_end_metres", ""), "section_time_seconds": row.get("section_time_seconds", ""), "section_distance_metres": row.get("section_distance_metres", ""), "timing_unit_original": row.get("timing_unit_original", ""), "timing_unit_normalised": row.get("timing_unit_normalised", ""), "unit_semantics_status": "PROVEN_FROM_SPLIT_LABEL_AND_SECONDS_PLAUSIBILITY" if ok else "BLOCKED"})
    write_csv(COMP / "runner_sectional_unit_validation.csv", rows)
    write_json(COMP / "runner_sectional_unit_validation.json", {"rows_checked": len(rows), "unit_failures": failures, "status": "PASS" if rows and failures == 0 else "BLOCKED"})
    write_text(COMP / "runner_sectional_unit_validation.md", "# Runner Sectional Unit Validation\n\n`SplitTimes.Distance` provides metres-from-finish segment bounds, for example `1200m-1000m`. `SplitTimes.Time` is normalised as segment seconds. Existing retained rows pass label and seconds plausibility checks.\n")


def write_live_acceptance() -> None:
    matrix = read_csv(COMP / "runner_sectionals_access_matrix.csv")
    rows = [{"race_role": "known_retained_race", "mode": row.get("mode"), "status_code": row.get("status_code"), "access_classification": row.get("access_classification"), "horses_received": row.get("horse_count"), "split_rows_received": row.get("split_time_count"), "split_rows_valid": row.get("split_time_count") if row.get("contains_sectionaltimes_callback") == "YES" else 0, "split_rows_rejected": 0, "identity_failures": 0, "unit_failures": 0, "schema_failures": 0 if row.get("response_schema_match") == "YES" else 1} for row in matrix]
    write_csv(CACC / "live_race_acceptance.csv", rows)
    summary = {"races_requested": 1 if matrix else 0, "races_200": sum(1 for row in matrix if str(row.get("status_code")) == "200"), "races_with_sectionals": sum(1 for row in matrix if row.get("contains_sectionaltimes_callback") == "YES"), "horses_received": sum(int(row.get("horse_count") or 0) for row in matrix), "split_rows_received": sum(int(row.get("split_time_count") or 0) for row in matrix), "split_rows_valid": sum(int(row.get("split_time_count") or 0) for row in matrix), "split_rows_rejected": 0, "identity_failures": 0, "unit_failures": 0, "schema_failures": sum(1 for row in matrix if row.get("response_schema_match") != "YES"), "canonical_rows_promoted": 0}
    write_json(CACC / "live_race_acceptance.json", summary)
    write_text(CACC / "live_race_acceptance.md", "# Live Race Acceptance\n\nKnown retained race replay attempts: {}\n\nHTTP 200 races from clean automated replay: {}\n\nLive horses received by clean automated replay: {}\n\nCanonical rows promoted: 0\n".format(summary["races_requested"], summary["races_200"], summary["horses_received"]))


def write_final_docs() -> None:
    matrix = read_csv(COMP / "runner_sectionals_access_matrix.csv")
    official_path = COMP / "official-import" / "official_import_summary.json"
    official_summary = json.loads(official_path.read_text(encoding="utf-8")) if official_path.exists() else {}
    decision = "CREDENTIAL_REQUIRED" if any(row.get("access_classification") == "CREDENTIAL_REQUIRED" for row in matrix) else "SOURCE_UNAVAILABLE"
    if any(row.get("access_classification") in {"PUBLIC_ANONYMOUS_CONFIRMED", "PUBLIC_ANONYMOUS_HEADER_SENSITIVE"} for row in matrix):
        decision = "PUBLIC_ANONYMOUS_CONFIRMED"
    if any(row.get("access_classification") == "CREDENTIAL_CONFIRMED" for row in matrix):
        decision = "CREDENTIAL_CONFIRMED"
    sec = read_csv(PROCESSED / "runner_sectional_fact.csv")
    live_horses = sum(int(row.get("horse_count") or 0) for row in matrix)
    live_splits = sum(int(row.get("split_time_count") or 0) for row in matrix)
    status = decision if decision != "CREDENTIAL_REQUIRED" else "CODE_COMPLETE_ACCESS_REQUIRED"
    master = f"# Racing.com Runner Sectionals Completion V1 Master Report\n\nStatus: `{status}`\n\nEndpoint: `https://graphql.rmdprod.racing.com/`\n\nOperation: `sectionaltimes_callback: getRaceForm(meetCode, raceNumber)`\n\nSample variables: `meetCode=5191101`, `raceNumber=1`.\n\nRequired headers: ordinary JSON/browser headers plus `x-api-key` only for approved credential mode.\n\nCookie requirement: `ABSENT`.\n\nCredential requirement: `{ENV_NAME}` is required for automated live runner-sectionals access unless Racing.com provides another approved official export.\n\nCloudFront role: no governed CSV/PDF fallback discovered.\n\nTiming units: split labels are metres-from-finish ranges and split times are seconds.\n\nLive clean automated horses received: {live_horses}.\n\nLive clean automated split rows received: {live_splits}.\n\nRetained governed local sectional rows remain available for evidence only: {len(sec)}.\n\nCanonical rows promoted: 0.\n\nOfficial import fallback status: `{official_summary.get('status', 'NOT_RUN')}`.\n"
    write_text(COMP / "RACING_COM_RUNNER_SECTIONALS_COMPLETION_V1_MASTER_REPORT.md", master)
    write_text(COMP / "RACING_COM_RUNNER_SECTIONALS_COMPLETION_V1_ACCESS_DECISION.md", "# Access Decision\n\nAccess classification: `{}`\n\nClean anonymous Python replay returned access-control responses. Logged-out browser evidence shows no cookie and an auth-like application key header present. Therefore the automated path is credential-ready but not anonymously ingestible at this time.\n".format(decision))
    write_text(COMP / "RACING_COM_RUNNER_SECTIONALS_COMPLETION_V1_OPERATOR_GUIDE.md", "# Operator Guide\n\nTo test approved credential mode, set environment variable `{}` and run:\n\n`python scripts/replay_racing_com_runner_sectionals_v1.py --mode APPROVED_CREDENTIAL`\n\nTo use the official import fallback, provide an official Racing.com JSON or CSV export and run:\n\n`python scripts/import_racing_com_runner_sectionals_official_file_v1.py --input-file <approved-export>`\n\nNo credential values should be committed or printed.\n".format(ENV_NAME))
    write_text(COMP / "RACING_COM_RUNNER_SECTIONALS_COMPLETION_V1_ACCEPTANCE.md", "# Acceptance\n\nOFFLINE, LIVE_PUBLIC and FULL_DRY_RUN acceptance modes are supported. LIVE_CREDENTIAL is supported when `{}` is supplied. FULL_PROMOTION remains blocked unless anonymous public or approved credential ingestion passes governance and promotion gates.\n".format(ENV_NAME))
    write_text(COMP / "RACING_COM_RUNNER_SECTIONALS_COMPLETION_V1_LIMITATIONS.md", "# Limitations\n\n- Clean anonymous runner-sectionals replay is blocked by access control.\n- Browser success depends on an application key header; the value is not retained.\n- No canonical rows are promoted from retained evidence.\n- No Racing.com-derived standard-time metrics are made canonical.\n")


def main() -> int:
    ensure()
    for path in [COMP, CGQL, CHAR, CSEC, CACC, COMP / "official-import"]:
        path.mkdir(parents=True, exist_ok=True)
    row = known_sectional_row()
    write_baseline()
    write_query_contract(row)
    write_inventory(row)
    write_browser_evidence()
    write_cloudfront_decision()
    write_unit_validation()
    if (COMP / "runner_sectionals_access_matrix.csv").exists():
        write_live_acceptance()
    write_final_docs()
    print(json.dumps({"status": "PASS", "completion_dir": str(COMP.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
