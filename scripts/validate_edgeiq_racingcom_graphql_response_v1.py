from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
ACQUISITION = OUT / "edgeiq_racingcom_graphql_acquisition_v1.csv"
VALIDATION_OUT = OUT / "edgeiq_racingcom_graphql_response_validation_v1.csv"
AUDIT_OUT = OUT / "edgeiq_racingcom_graphql_response_validation_audit_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_response_validation_summary_v1.json"
REPORT_OUT = OUT / "edgeiq_racingcom_graphql_response_validation_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean(row.get(column, "")) for column in columns})


def load_payload(path_text: str) -> dict[str, Any]:
    path = ROOT / clean(path_text)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    rows = read_csv(ACQUISITION)
    validation_rows: list[dict[str, Any]] = []
    for row in rows:
        status = "VALID_RESPONSE"
        reason = "Payload contains sectionaltimes_callback Horses with sectional rows."
        horse_count = sectional_count = split_count = avg_speed_count = graph_errors = 0
        data_present = "NO"
        try:
            payload = load_payload(row.get("response_path", ""))
            graph_errors = len(payload.get("errors") or [])
            container = (payload.get("data") or {}).get("sectionaltimes_callback") or {}
            horses = container.get("Horses") or []
            horse_count = len(horses)
            for horse in horses:
                sectionals = horse.get("SectionalTimes") or []
                splits = horse.get("SplitTimes") or []
                sectional_count += len(sectionals)
                split_count += len(splits)
                avg_speed_count += sum(1 for item in sectionals + splits if item.get("AvgSpeed") is not None)
            data_present = "YES" if horse_count > 0 else "NO"
            if graph_errors:
                status = "INVALID_GRAPHQL_ERRORS"
                reason = "Payload contains GraphQL errors."
            elif horse_count <= 0 or sectional_count <= 0:
                status = "INVALID_EMPTY_SECTIONALS"
                reason = "Payload does not contain horse and sectional populations."
        except Exception as exc:
            status = "INVALID_JSON_OR_MISSING_FILE"
            reason = str(exc)
        validation_rows.append(
            {
                "request_contract_id": clean(row.get("request_contract_id")),
                "race_id": clean(row.get("race_id")),
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "response_path": clean(row.get("response_path")),
                "response_sha256": clean(row.get("response_sha256")),
                "data_present": data_present,
                "graphql_error_count": graph_errors,
                "horse_count": horse_count,
                "sectional_count": sectional_count,
                "split_count": split_count,
                "avg_speed_count": avg_speed_count,
                "speed_unit_source": "M_PER_SECOND",
                "ui_speed_conversion": "KMH_EQUALS_AVGSPEED_TIMES_3_6",
                "validation_status": status,
                "validation_reason": reason,
                "validated_utc": BUILT_UTC,
            }
        )
    valid = [row for row in validation_rows if row["validation_status"] == "VALID_RESPONSE"]
    audit = [
        ("five_responses_validated", len(validation_rows) == 5, len(validation_rows), "Five acquired responses should be validated."),
        ("all_valid_responses", len(valid) == 5, len(valid), "All five responses should pass schema/content validation."),
        ("no_graphql_errors", sum(int(row["graphql_error_count"]) for row in validation_rows) == 0, sum(int(row["graphql_error_count"]) for row in validation_rows), "No GraphQL errors allowed."),
        ("runner_population_present", all(int(row["horse_count"]) > 0 for row in validation_rows), sum(1 for row in validation_rows if int(row["horse_count"]) > 0), "Every response has horse population."),
        ("sectional_population_present", all(int(row["sectional_count"]) > 0 for row in validation_rows), sum(1 for row in validation_rows if int(row["sectional_count"]) > 0), "Every response has sectional rows."),
        ("avg_speed_present", all(int(row["avg_speed_count"]) > 0 for row in validation_rows), sum(1 for row in validation_rows if int(row["avg_speed_count"]) > 0), "Every response has AvgSpeed values."),
    ]
    audit_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "count": count, "detail": detail} for name, passed, count, detail in audit]
    hard_pass = all(row["status"] == "PASS" for row in audit_rows)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_RESPONSE_VALIDATION_V1_PASS" if hard_pass else "RACINGCOM_GRAPHQL_RESPONSE_VALIDATION_V1_REVIEW_REQUIRED",
        "responses_validated": len(validation_rows),
        "valid_responses": len(valid),
        "total_horses": sum(int(row["horse_count"]) for row in validation_rows),
        "total_sectionals": sum(int(row["sectional_count"]) for row in validation_rows),
        "total_splits": sum(int(row["split_count"]) for row in validation_rows),
        "speed_unit_source": "M_PER_SECOND",
        "ui_speed_conversion": "KMH_EQUALS_AVGSPEED_TIMES_3_6",
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(VALIDATION_OUT, validation_rows, ["request_contract_id", "race_id", "race_date", "track", "race_no", "response_path", "response_sha256", "data_present", "graphql_error_count", "horse_count", "sectional_count", "split_count", "avg_speed_count", "speed_unit_source", "ui_speed_conversion", "validation_status", "validation_reason", "validated_utc"])
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL Response Validation V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Counts",
                f"- Responses validated: `{summary['responses_validated']}`",
                f"- Valid responses: `{summary['valid_responses']}`",
                f"- Total horses: `{summary['total_horses']}`",
                f"- Total sectionals: `{summary['total_sectionals']}`",
                f"- Total splits: `{summary['total_splits']}`",
                "",
                "## Speed Semantics",
                "",
                "`AvgSpeed` is retained as source m/s. Customer-facing km/h conversion is `AvgSpeed * 3.6`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
