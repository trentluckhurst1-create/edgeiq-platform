from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
CSV_OUT = OUT_DIR / "edgeiq_racingcom_race_discovery_v2_evidence_extension_contract_v1.csv"
JSON_OUT = OUT_DIR / "edgeiq_racingcom_race_discovery_v2_evidence_extension_contract_v1.json"
REPORT_OUT = OUT_DIR / "edgeiq_racingcom_race_discovery_v2_evidence_extension_contract_v1.md"
SUMMARY_OUT = OUT_DIR / "edgeiq_racingcom_race_discovery_v2_evidence_extension_summary_v1.json"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")


FIELDS = [
    "race_id",
    "meeting_id",
    "race_date",
    "track",
    "track_key",
    "state",
    "meet_code",
    "race_no",
    "race_no_numeric",
    "race_url",
    "speed_data_url",
    "discovery_method",
    "evidence_strength",
    "source_url",
    "source_artifact",
    "source_record_id",
    "source_request_id",
    "source_response_id",
    "source_payload_path",
    "source_sha256",
    "observed_in_source",
    "race_status",
    "completed_status",
    "is_future",
    "has_speed_data",
    "speed_data_status",
    "provenance",
    "discovered_utc",
    "pipeline_version",
]

METHODS = [
    {
        "discovery_method": "VALIDATED_GRAPHQL_RACE_PAYLOAD",
        "precedence": 1,
        "description": "Validated getRaceForm GraphQL payload with runner and sectional populations.",
        "race_existence": "YES",
        "speed_eligibility": "YES_WHEN_SECTIONAL_POPULATION_PRESENT",
    },
    {
        "discovery_method": "OBSERVED_GRAPHQL_REQUEST",
        "precedence": 2,
        "description": "Captured Racing.com GraphQL getRaceForm request tied to an observed race page.",
        "race_existence": "YES",
        "speed_eligibility": "NO_UNLESS_VALIDATED_SPEED_PAYLOAD_EXISTS",
    },
    {
        "discovery_method": "OBSERVED_SPEED_DATA_PAGE",
        "precedence": 3,
        "description": "Browser-observed Racing.com speed-data page for a completed race.",
        "race_existence": "YES",
        "speed_eligibility": "NO_UNLESS_VALIDATED_SPEED_PAYLOAD_EXISTS",
    },
    {
        "discovery_method": "OBSERVED_RACE_PAGE",
        "precedence": 4,
        "description": "Browser-observed completed Racing.com race page.",
        "race_existence": "YES",
        "speed_eligibility": "NO",
    },
    {
        "discovery_method": "HISTORICAL_SUCCESS_RACE",
        "precedence": 5,
        "description": "Previously fetched and parsed historical source race.",
        "race_existence": "YES",
        "speed_eligibility": "YES_WHEN_HISTORICAL_SOURCE_IS_SPEED_DATA",
    },
    {
        "discovery_method": "OBSERVED_STRUCTURED_RACE",
        "precedence": 6,
        "description": "Race observed in a retained structured source without generated race-number expansion.",
        "race_existence": "YES",
        "speed_eligibility": "NO_UNLESS_SUPPORTED_BY_SPEED_SOURCE",
    },
]

DEDUP_PRECEDENCE = [
    "VALIDATED_GRAPHQL_RACE_WITH_SPEED",
    "VALIDATED_GRAPHQL_RACE_NO_SPEED",
    "HISTORICAL_SUCCESS_RACE",
    "OBSERVED_STRUCTURED_RACE",
    "OBSERVED_RACE_PAGE",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean(row.get(column, "")) for column in columns})


def main() -> int:
    columns = ["discovery_method", "precedence", "description", "race_existence", "speed_eligibility"]
    write_csv(CSV_OUT, METHODS, columns)
    payload = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_RACE_DISCOVERY_V2_EVIDENCE_EXTENSION_CONTRACT_DEFINED",
        "canonical_identity": ["race_date", "track_key", "race_no_numeric"],
        "required_fields": FIELDS,
        "supported_discovery_methods": METHODS,
        "dedup_precedence": DEDUP_PRECEDENCE,
        "governance": {
            "race_existence_is_separate_from_speed_data_eligibility": True,
            "manual_fixture_status_allowed": False,
            "synthetic_race_number_expansion_allowed": False,
            "graphql_admission_semantics_unchanged": True,
        },
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    SUMMARY_OUT.write_text(
        json.dumps(
            {
                "built_utc": BUILT_UTC,
                "status": payload["status"],
                "supported_discovery_methods": len(METHODS),
                "required_fields": len(FIELDS),
                "manual_fixture_status_allowed": "NO",
                "production_changed": "NO",
                "ui_changed": "NO",
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    lines = [
        "# Racing.com Race Discovery V2 Evidence Extension Contract V1",
        "",
        f"Built UTC: `{BUILT_UTC}`",
        f"Status: `{payload['status']}`",
        "",
        "## Governance",
        "",
        "Race discovery proves race existence. Speed-source admission separately proves whether speed data may be acquired.",
        "",
        "No race may be admitted from URL construction, fixed race-number expansion, or a vague manual fixture status.",
        "",
        "## Canonical Identity",
        "",
        "- `race_date`",
        "- `track_key`",
        "- `race_no_numeric`",
        "",
        "## Supported Discovery Methods",
    ]
    for method in METHODS:
        lines.append(f"- `{method['discovery_method']}` precedence `{method['precedence']}`: {method['description']}")
    lines.extend(
        [
            "",
            "## Deduplication Precedence",
            "",
            ", ".join(f"`{item}`" for item in DEDUP_PRECEDENCE),
            "",
            "## Required Output Fields",
            "",
            ", ".join(f"`{field}`" for field in FIELDS),
            "",
            "## Preservation",
            "",
            "- Production warehouse unchanged.",
            "- UI unchanged.",
            "- Pricing, probabilities, ratings, V6.1 and V7.2G2 unchanged.",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "supported_discovery_methods": len(METHODS), "required_fields": len(FIELDS)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
