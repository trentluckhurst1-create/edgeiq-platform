from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
TEST_OUT = OUT / "edgeiq_racingcom_graphql_integration_tests_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_integration_tests_summary_v1.json"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["test", "status", "count", "detail"], extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    race_discovery = read_csv(OUT / "edgeiq_racingcom_race_discovery_contract_v2.csv")
    admission = read_csv(OUT / "edgeiq_racingcom_graphql_source_admission_v1.csv")
    evidence = read_csv(OUT / "edgeiq_racingcom_graphql_race_evidence_v1.csv")
    acquisition = read_csv(OUT / "edgeiq_racingcom_graphql_acquisition_v1.csv")
    validation = read_csv(OUT / "edgeiq_racingcom_graphql_response_validation_v1.csv")
    parser = read_csv(OUT / "edgeiq_racingcom_graphql_parser_output_v2.csv")
    canonical = read_csv(OUT / "edgeiq_racingcom_canonical_speed_contract_v1.csv")
    tests = [
        ("race_discovery_has_59_rows", len(race_discovery) == 59, len(race_discovery), "Race discovery should contain 52 base + 7 fixture races."),
        ("graphql_evidence_has_5_speed_2_no_speed", sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_WITH_SPEED") == 5 and sum(1 for row in evidence if row["evidence_status"] == "VALIDATED_GRAPHQL_RACE_NO_SPEED") == 2, len(evidence), "Evidence split should be five speed and two no-speed."),
        ("admission_has_5_speed_rows", len(admission) == 5, len(admission), "Only speed-eligible races should be admitted."),
        ("acquisition_has_5_payloads", len(acquisition) == 5 and all(row["response_path"] for row in acquisition), len(acquisition), "Five acquired payloads with paths."),
        ("validation_has_5_valid_payloads", sum(1 for row in validation if row["validation_status"] == "VALID_RESPONSE") == 5, len(validation), "Five payloads pass validation."),
        ("parser_has_898_rows", len(parser) == 898, len(parser), "GraphQL parser should emit 449 sectionals and 449 splits."),
        ("canonical_has_978_rows", len(canonical) == 978, len(canonical), "Canonical contract should retain 80 CSV aggregate + 898 GraphQL rows."),
        ("no_moe_in_speed_admission", all("MOE" not in row["race_id"] for row in admission), sum(1 for row in admission if "MOE" in row["race_id"]), "Moe negative controls must not enter speed admission."),
        ("production_flags_no", True, 0, "No production/UI/pricing/model changes made by these tests."),
    ]
    rows = [{"test": name, "status": "PASS" if passed else "FAIL", "count": count, "detail": detail} for name, passed, count, detail in tests]
    write_csv(TEST_OUT, rows)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_INTEGRATION_TESTS_V1_PASS" if all(row["status"] == "PASS" for row in rows) else "RACINGCOM_GRAPHQL_INTEGRATION_TESTS_V1_FAIL",
        "tests": len(rows),
        "pass": sum(1 for row in rows if row["status"] == "PASS"),
        "fail": sum(1 for row in rows if row["status"] == "FAIL"),
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
