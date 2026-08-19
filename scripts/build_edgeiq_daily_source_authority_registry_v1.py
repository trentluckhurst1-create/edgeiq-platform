from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "daily-operations-engine-v1"
DATA = ROOT / "public" / "data"

FIELDS = [
    "source_name", "source_authority_level", "source_identity", "data_types_provided",
    "publication_timing", "update_timing", "historical_reach", "request_method",
    "authentication_requirement", "rate_limit_expectations", "evidence_retention_method",
    "parser_status", "schema", "current_builder", "canonical_consumer", "known_gaps",
    "failure_behaviour", "terms_or_access_constraints_noted", "source_status",
    "evidence_file", "evidence_sha256",
]

CANDIDATES = [
    {
        "source_name": "RACINGCOM_THREE_DAY_PRODUCT_CATALOG",
        "source_authority_level": "SCHEDULE_DECLARATION_CURRENT_WINDOW",
        "source_identity": "public/data/edgeiq_three_day_product_catalog_v1.json; public/data/edgeiq_vic_three_day_race_list_v1.csv; public/data/edgeiq_vic_three_day_race_fields.csv",
        "data_types_provided": "meetings,races,declared_runners,barriers,weights,jockeys,trainers,current_conditions",
        "publication_timing": "pre-race current window",
        "update_timing": "current-day refresh",
        "historical_reach": "rolling current window",
        "request_method": "existing repository collector output",
        "authentication_requirement": "NONE_OBSERVED_IN_REPOSITORY_OUTPUTS",
        "rate_limit_expectations": "use existing collector cadence; no new unrestricted scrape",
        "evidence_retention_method": "public/data outputs plus outputs/performance-intelligence/racingcom-v2 raw evidence where available",
        "parser_status": "SUPPORTED_LOCAL_OUTPUT",
        "schema": "three_day_product_catalog_v1/race_list_v1/race_fields",
        "current_builder": "scripts/build_edgeiq_three_day_product_catalog_v1.py; scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py",
        "canonical_consumer": "daily race discovery; current Victoria runtime feeds",
        "known_gaps": "not official result authority; current-window only",
        "failure_behaviour": "SOURCE_UNAVAILABLE or NOT_PUBLISHED",
        "terms_or_access_constraints_noted": "repository evidence only; no credentials stored",
        "source_status": "SUPPORTED",
        "evidence_file": "public/data/edgeiq_vic_three_day_race_list_v1.csv",
    },
    {
        "source_name": "RACINGCOM_GRAPHQL_HISTORICAL_RESULTS",
        "source_authority_level": "HISTORICAL_RESULTS_WAREHOUSE",
        "source_identity": "public/data/edgeiq_historical_results_warehouse_v2_graphql.csv",
        "data_types_provided": "historical_results,official_race_times,placings,margins,track_conditions,runners,jockeys,trainers,weights,barriers",
        "publication_timing": "historical/backfill",
        "update_timing": "repository collector dependent",
        "historical_reach": "2000+ per existing warehouse",
        "request_method": "existing GraphQL collector output",
        "authentication_requirement": "NONE_OBSERVED_IN_REPOSITORY_OUTPUTS",
        "rate_limit_expectations": "use existing harvested files; no new unrestricted scrape",
        "evidence_retention_method": "public/data warehouse plus outputs/performance-intelligence/racingcom-v2/raw",
        "parser_status": "SUPPORTED_LOCAL_OUTPUT",
        "schema": "historical_results_warehouse_v2_graphql",
        "current_builder": "repository historical GraphQL builders discovered under scripts and outputs/performance-intelligence",
        "canonical_consumer": "official results ingestion; official timing ingestion; canonical timing warehouse update",
        "known_gaps": "source freshness depends on collector coverage; unsupported timing units rejected",
        "failure_behaviour": "SOURCE_DELAYED, SOURCE_UNAVAILABLE, TIMING_UNIT_UNSUPPORTED",
        "terms_or_access_constraints_noted": "repository evidence only; no hidden access controls bypassed",
        "source_status": "SUPPORTED",
        "evidence_file": "public/data/edgeiq_historical_results_warehouse_v2_graphql.csv",
    },
    {
        "source_name": "RACING_AUSTRALIA_RESULTS_OUTPUTS",
        "source_authority_level": "OFFICIAL_RESULTS_CANDIDATE",
        "source_identity": "public/data/ra_calendar_official_results.csv; public/data/ra_extracted_results.csv; public/data/racing_australia_*",
        "data_types_provided": "official_results,placings,margins,conditions,metadata",
        "publication_timing": "post-race",
        "update_timing": "collector dependent",
        "historical_reach": "limited repository outputs",
        "request_method": "existing repository collector output",
        "authentication_requirement": "NONE_OBSERVED_IN_REPOSITORY_OUTPUTS",
        "rate_limit_expectations": "use existing outputs only unless operator runs supported collector",
        "evidence_retention_method": "public/data RA outputs",
        "parser_status": "SUPPORTED_LOCAL_OUTPUT_WITH_GAPS",
        "schema": "racing_australia normalized result outputs",
        "current_builder": "scripts containing racing_australia/ra results collectors",
        "canonical_consumer": "official results ingestion candidate fallback",
        "known_gaps": "coverage and canonical identity joins vary by meeting",
        "failure_behaviour": "SOURCE_UNAVAILABLE, IDENTITY_PENDING, AMBIGUOUS_IDENTITY",
        "terms_or_access_constraints_noted": "repository evidence only",
        "source_status": "SUPPORTED_PARTIAL",
        "evidence_file": "public/data/ra_calendar_official_results.csv",
    },
    {
        "source_name": "RACINGCOM_SPEED_DATA_OUTPUTS",
        "source_authority_level": "DELAYED_SPEED_DATA_CANDIDATE",
        "source_identity": "public/data/racingcom_rendered_speed_data_*.csv; public/data/edgeiq_racingcom_runner_speed_fact_v1.csv; public/data/edgeiq_racingcom_runner_sectional_fact_v1.csv",
        "data_types_provided": "speed_summaries,sectionals,splits,runner_speed_metrics",
        "publication_timing": "delayed post-race",
        "update_timing": "speed refresh/backfill",
        "historical_reach": "repository harvest coverage",
        "request_method": "existing rendered/browser/CSV acquisition outputs",
        "authentication_requirement": "NONE_OBSERVED_IN_REPOSITORY_OUTPUTS",
        "rate_limit_expectations": "hourly maximum for delayed-speed refresh; no unsupported access controls",
        "evidence_retention_method": "public/data speed outputs and outputs/performance-intelligence raw acquisitions",
        "parser_status": "SUPPORTED_LOCAL_OUTPUT_WITH_DELAY",
        "schema": "racingcom_runner_speed_fact/sectional_fact/rendered_speed_data",
        "current_builder": "scripts/build or audit racingcom speed data collectors",
        "canonical_consumer": "delayed speed data ingestion; lifecycle speed status",
        "known_gaps": "speed data may be late or absent; identity resolution may fail",
        "failure_behaviour": "SPEED_DATA_NOT_YET_PUBLISHED, SPEED_DATA_SOURCE_UNAVAILABLE",
        "terms_or_access_constraints_noted": "no hidden/unsupported access controls",
        "source_status": "SUPPORTED_PARTIAL",
        "evidence_file": "public/data/edgeiq_racingcom_runner_speed_fact_v1.csv",
    },
    {
        "source_name": "GOVERNED_TRACK_CONDITION_WEATHER_REGISTRY",
        "source_authority_level": "CONDITION_SUPPORT_AND_WEATHER_CONTEXT_NOT_OFFICIAL_TIMING",
        "source_identity": "docs/weather-intelligence; public/data/edgeiq_victorian_track_weather_v1.json; track-source-audit",
        "data_types_provided": "weather,wind,rainfall,track-condition source evidence,operator-condition candidates",
        "publication_timing": "current-day/live where collector available",
        "update_timing": "weather refresh",
        "historical_reach": "limited live registry/output snapshots",
        "request_method": "existing weather/source collectors",
        "authentication_requirement": "NONE_OBSERVED_IN_REPOSITORY_OUTPUTS",
        "rate_limit_expectations": "respect existing BOM/operator collectors",
        "evidence_retention_method": "docs/weather-intelligence and data/weather-source-*",
        "parser_status": "SUPPORTED_FOR_EVIDENCE; WEATHER_NOT_USED_TO_INFER_CONDITION",
        "schema": "weather registry and condition source audits",
        "current_builder": "scripts/build_edgeiq_victorian_weather_registry_v1.py and related weather scripts",
        "canonical_consumer": "condition evidence ingestion where official condition is present; weather context only otherwise",
        "known_gaps": "weather cannot infer official track condition",
        "failure_behaviour": "CONDITION_REJECTED or SOURCE_UNAVAILABLE",
        "terms_or_access_constraints_noted": "no weather-derived official condition inference",
        "source_status": "SUPPORTED_PARTIAL",
        "evidence_file": "public/data/edgeiq_victorian_track_weather_v1.json",
    },
]

def sha(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    t = Path(tmp)
    try:
        with t.open("w", encoding="utf-8", newline="") as h:
            w = csv.DictWriter(h, fieldnames=FIELDS)
            w.writeheader(); w.writerows(rows)
        os.replace(t, path)
    finally:
        if t.exists(): t.unlink()

def main() -> int:
    rows=[]
    for row in CANDIDATES:
        out=dict(row)
        ep = ROOT / row["evidence_file"]
        out["evidence_sha256"] = sha(ep)
        if not ep.exists() and out["source_status"] == "SUPPORTED":
            out["source_status"] = "EXTERNAL_ACCESS_REQUIRED_OR_SOURCE_MISSING"
            out["failure_behaviour"] = "BLOCKED_EXTERNAL_ACCESS"
        rows.append({k: str(out.get(k, "")) for k in FIELDS})
    csv_path = DOCS / "EDGEIQ_DAILY_SOURCE_AUTHORITY_REGISTRY_V1.csv"
    json_path = DOCS / "EDGEIQ_DAILY_SOURCE_AUTHORITY_REGISTRY_V1.json"
    md_path = DOCS / "EDGEIQ_DAILY_SOURCE_AUTHORITY_DECISION_V1.md"
    write_csv(csv_path, rows)
    payload = {
        "registry_version": "EDGEIQ_DAILY_SOURCE_AUTHORITY_REGISTRY_V1",
        "built_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sources": rows,
        "decision": "Use repository-supported local outputs first. Live access without a governed existing collector is EXTERNAL_ACCESS_REQUIRED, not fabricated.",
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = ["# EDGEiQ Daily Source Authority Decision V1", "", payload["decision"], "", "## Supported Sources"]
    for r in rows:
        md.append(f"- {r['source_name']}: {r['source_status']} ({r['data_types_provided']})")
    md.append("")
    md.append("Weather may support context but must not infer official track condition. Final SP/market data is not used as a predictive feature here.")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"status":"PASS","sources":len(rows),"outputs":[str(csv_path),str(json_path),str(md_path)]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
