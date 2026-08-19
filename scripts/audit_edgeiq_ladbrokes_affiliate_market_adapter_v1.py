from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "market-intelligence" / "ladbrokes"

RUNTIME_CSV = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_runtime_v1.csv"
RUNTIME_JSON = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_runtime_v1.json"
SUMMARY_CSV = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_adapter_v1_summary.csv"
REQUEST_AUDIT = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_adapter_v1_audit.csv"
PROOF_CSV = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_current_match_proof_v1.csv"
REFERENCE_JSON = DOCS / "edgeiq_ladbrokes_reference_inspection_v1.json"
TERMS_JSON = DOCS / "edgeiq_ladbrokes_api_terms_assessment_v1.json"
SCHEMA_CSV = DOCS / "edgeiq_ladbrokes_provider_schema_v1.csv"

OUT_CSV = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_adapter_v1_quality_audit.csv"
OUT_SUMMARY = PUBLIC_DATA / "edgeiq_ladbrokes_affiliate_market_adapter_v1_quality_summary.csv"
OUT_REPORT = DOCS / "edgeiq_ladbrokes_affiliate_market_adapter_v1_quality_report.md"

REQUIRED_RUNTIME_COLUMNS = [
    "fixed_win",
    "fixed_place",
    "price_timestamp",
    "opening_price",
    "high_price",
    "low_price",
    "recent_price",
    "flucs_with_timestamp",
    "is_scratched",
    "market_status",
    "race_status",
    "advertised_start",
    "actual_start",
    "provider_runner_id",
    "provider_race_id",
    "provider_meeting_id",
    "market_availability_status",
    "fluctuation_status",
    "price_movement_status",
    "raw_publication_status",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def text(value: Any) -> str:
    return str(value or "").strip()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    runtime = read_csv(RUNTIME_CSV)
    summary = {row.get("metric"): row.get("value") for row in read_csv(SUMMARY_CSV)}
    request_audit = read_csv(REQUEST_AUDIT)
    proof = read_csv(PROOF_CSV)
    reference = load_json(REFERENCE_JSON)
    terms = load_json(TERMS_JSON)
    schema = read_csv(SCHEMA_CSV)

    runtime_columns = set(runtime[0].keys()) if runtime else set()
    rows: list[dict[str, Any]] = []

    def add(check: str, status: str, detail: Any) -> None:
        rows.append({"check": check, "status": status, "detail": detail})

    add("runtime_csv_exists", "PASS" if RUNTIME_CSV.exists() else "FAIL", str(RUNTIME_CSV))
    add("runtime_json_exists", "PASS" if RUNTIME_JSON.exists() else "FAIL", str(RUNTIME_JSON))
    add("reference_docs_exist", "PASS" if REFERENCE_JSON.exists() else "FAIL", str(REFERENCE_JSON))
    add("terms_docs_exist", "PASS" if TERMS_JSON.exists() else "FAIL", str(TERMS_JSON))
    add("provider_schema_exists", "PASS" if SCHEMA_CSV.exists() else "FAIL", str(SCHEMA_CSV))
    add("runtime_rows_nonzero", "PASS" if len(runtime) > 0 else "FAIL", len(runtime))
    add("no_market_workspace_wiring", "PASS" if summary.get("market_workspace_wired") == "NO" else "FAIL", summary.get("market_workspace_wired"))
    add("production_pricing_unchanged", "PASS" if summary.get("production_pricing_changed") == "NO" else "FAIL", summary.get("production_pricing_changed"))
    add("credential_values_not_written", "PASS" if terms.get("credential_values_written_to_outputs") == "NO" else "FAIL", terms.get("credential_values_written_to_outputs"))
    add("raw_payload_not_public", "PASS" if terms.get("raw_payload_publication") == "NO_RAW_PAYLOADS_WRITTEN_TO_PUBLIC_DATA" else "FAIL", terms.get("raw_payload_publication"))

    for column in REQUIRED_RUNTIME_COLUMNS:
        add(f"runtime_column_{column}", "PASS" if column in runtime_columns else "FAIL", column)

    add("official_endpoints_recorded", "PASS" if reference.get("official_docs_confirmation", {}).get("supported_racing_endpoints") else "FAIL", reference.get("official_docs_confirmation", {}))
    add("auth_contract_headers_recorded", "PASS" if reference.get("reference_auth_contract", {}).get("headers") == ["From", "X-Partner"] else "FAIL", reference.get("reference_auth_contract", {}))
    add("sports_api_not_used", "PASS" if reference.get("official_docs_confirmation", {}).get("sports_api_available_via_affiliates") is False else "FAIL", reference.get("official_docs_confirmation", {}))

    fixed_win_rows = sum(1 for row in runtime if text(row.get("fixed_win")))
    matched_rows = sum(1 for row in runtime if row.get("join_status") == "MATCHED")
    movement_rows = sum(1 for row in runtime if row.get("price_movement_status") == "DERIVED_FROM_EDGEIQ_OBSERVATION_HISTORY")
    auth_required = summary.get("adapter_status") == "AUTH_REQUIRED"
    if auth_required:
        readiness = "AUTH_REQUIRED_NOT_WIRED"
    elif fixed_win_rows and matched_rows:
        readiness = "READY_FOR_REPEAT_OBSERVATION_PROOF"
    else:
        readiness = "PROVIDER_DATA_INCOMPLETE"

    add("proof_rows_available", "PASS" if auth_required or len(proof) > 0 else "FAIL", len(proof))
    add("request_audit_available", "PASS" if len(request_audit) > 0 else "FAIL", len(request_audit))
    add("fixed_win_rows", "INFO", fixed_win_rows)
    add("matched_rows", "INFO", matched_rows)
    add("movement_rows", "INFO", movement_rows)
    add("readiness", "INFO", readiness)

    failures = sum(1 for row in rows if row["status"] == "FAIL")
    final_status = "PASS" if failures == 0 else "REVIEW_REQUIRED"
    write_csv(OUT_CSV, rows, ["check", "status", "detail"])
    write_csv(
        OUT_SUMMARY,
        [
            {"metric": "quality_status", "value": final_status},
            {"metric": "checks", "value": len(rows)},
            {"metric": "failures", "value": failures},
            {"metric": "readiness", "value": readiness},
            {"metric": "runtime_rows", "value": len(runtime)},
            {"metric": "fixed_win_rows", "value": fixed_win_rows},
            {"metric": "matched_rows", "value": matched_rows},
        ],
        ["metric", "value"],
    )
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(
        "\n".join(
            [
                "# EDGEiQ Ladbrokes Affiliate Market Adapter V1 Quality Report",
                "",
                f"Quality status: {final_status}",
                f"Readiness: {readiness}",
                f"Runtime rows: {len(runtime)}",
                f"Fixed-win rows: {fixed_win_rows}",
                f"Matched rows: {matched_rows}",
                "",
                "The MARKET workspace remains unwired until current-meeting proof and repeated observation movement proof pass.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"quality_status": final_status, "readiness": readiness, "failures": failures}, indent=2))


if __name__ == "__main__":
    main()
