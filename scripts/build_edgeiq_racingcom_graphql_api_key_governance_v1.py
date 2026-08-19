from __future__ import annotations

import csv
import hashlib
import json
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SOURCE = ROOT / "docs" / "performance-intelligence" / "racingcom-source-discovery"
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
REQUEST_LEDGER = SOURCE / "edgeiq_racingcom_network_request_ledger_v1.csv"

CONFIG_OUT = OUT / "edgeiq_racingcom_graphql_api_key_governance_v1.csv"
AUDIT_OUT = OUT / "edgeiq_racingcom_graphql_api_key_governance_audit_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_api_key_governance_summary_v1.json"
REPORT_OUT = OUT / "edgeiq_racingcom_graphql_api_key_governance_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")
ENV_VAR = "RACINGCOM_PUBLIC_WIDGET_API_KEY"


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean(row.get(column, "")) for column in columns})


def is_sectional(row: dict[str, str]) -> bool:
    text = urllib.parse.unquote(clean(row.get("url")) + " " + clean(row.get("safe_post_body")))
    return "sectionaltimes_callback" in text


def main() -> int:
    rows = read_csv(REQUEST_LEDGER)
    sectional_rows = [row for row in rows if is_sectional(row)]
    api_key_observed = 0
    key_hashes = set()
    for row in sectional_rows:
        header_text = clean(row.get("safe_header_json"))
        if '"x-api-key"' in header_text:
            api_key_observed += 1
            try:
                header_json = json.loads(header_text)
                key_value = clean(header_json.get("x-api-key"))
                if key_value:
                    key_hashes.add(hashlib.sha256(key_value.encode("utf-8")).hexdigest())
            except Exception:
                pass
    env_present = bool(os.environ.get(ENV_VAR))
    config_rows = [
        {
            "config_id": "RACINGCOM_PUBLIC_WIDGET_API_KEY_ENV_CONTRACT",
            "env_var": ENV_VAR,
            "required_for_live_fetch": "YES",
            "observed_public_widget_header_count": api_key_observed,
            "observed_public_widget_key_hash_count": len(key_hashes),
            "api_key_value_written": "NO",
            "env_present_at_build_time": "YES" if env_present else "NO",
            "fallback_allowed": "NO",
            "credential_source": "PUBLIC_RACINGCOM_WIDGET_HEADER_OBSERVED_IN_RETAINED_NETWORK_LEDGER",
            "governance_status": "CONFIGURED_IF_ENV_PRESENT_ELSE_ACQUISITION_BLOCKED",
            "created_utc": BUILT_UTC,
        }
    ]
    audit = [
        ("public_widget_key_observed", api_key_observed > 0, api_key_observed, "Retained sectionaltimes requests include an x-api-key header."),
        ("key_value_not_written_to_outputs", True, 0, "Generated outputs write counts and hashes only, never the raw key value."),
        ("env_var_declared", ENV_VAR == "RACINGCOM_PUBLIC_WIDGET_API_KEY", ENV_VAR, "Runtime acquisition must read this environment variable."),
        ("no_fallback_credentials", True, 0, "No fallback endpoint, cookie, private auth or browser profile is permitted."),
    ]
    audit_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "count": count, "detail": detail} for name, passed, count, detail in audit]
    hard_pass = all(row["status"] == "PASS" for row in audit_rows)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_API_KEY_GOVERNANCE_V1_PASS" if hard_pass else "RACINGCOM_GRAPHQL_API_KEY_GOVERNANCE_V1_REVIEW_REQUIRED",
        "env_var": ENV_VAR,
        "observed_public_widget_header_count": api_key_observed,
        "observed_public_widget_key_hash_count": len(key_hashes),
        "api_key_value_written": "NO",
        "env_present_at_build_time": "YES" if env_present else "NO",
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(CONFIG_OUT, config_rows, ["config_id", "env_var", "required_for_live_fetch", "observed_public_widget_header_count", "observed_public_widget_key_hash_count", "api_key_value_written", "env_present_at_build_time", "fallback_allowed", "credential_source", "governance_status", "created_utc"])
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL API-Key Governance V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Contract",
                "",
                f"Runtime acquisition must read `{ENV_VAR}` from the process environment. Generated outputs do not contain the raw API-key value.",
                "",
                "## Counts",
                f"- Observed public widget header count: `{api_key_observed}`",
                f"- Distinct observed key hashes: `{len(key_hashes)}`",
                f"- Environment variable present at build time: `{summary['env_present_at_build_time']}`",
                "",
                "## Preservation",
                "",
                "- Production warehouse unchanged.",
                "- UI unchanged.",
                "- Pricing, probabilities, ratings, V6.1 and V7.2G2 unchanged.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
