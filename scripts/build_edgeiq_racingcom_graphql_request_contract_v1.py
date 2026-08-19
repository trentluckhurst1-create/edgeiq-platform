from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
ADMISSION = OUT / "edgeiq_racingcom_graphql_source_admission_v1.csv"
REQUEST_CONTRACT = OUT / "edgeiq_racingcom_graphql_request_contract_v1.csv"
AUDIT_OUT = OUT / "edgeiq_racingcom_graphql_request_contract_audit_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_request_contract_summary_v1.json"
REPORT_OUT = OUT / "edgeiq_racingcom_graphql_request_contract_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")
GRAPHQL_ENDPOINT = "https://graphql.rmdprod.racing.com/"
API_KEY_ENV = "RACINGCOM_PUBLIC_WIDGET_API_KEY"
PIPELINE_VERSION = "edgeiq_racingcom_graphql_request_contract_v1"

QUERY = """query {
  sectionaltimes_callback: getRaceForm(meetCode: "%(meet_code)s", raceNumber:%(race_no)s) {
    Horses: raceEntryTimes {
      id
      Comment: comment
      FinalPosition: finishPosition
      FinalPositionAbbreviation: finishPositionAbv
      FullName: horseName
      SaddleNumber: saddleNumber
      HorseUrl: horseUrl
      SilkUrl: silkUrl
      Trainer: trainerName
      TrainerUrl: trainerUrl
      Jockey: jockeyName
      JockeyUrl: jockeyUrl
      SectionalTimes: times {
        Distance: distance
        Position: rank
        Time: intermediateTime
        AvgSpeed: avgSpeed
      }
      SplitTimes: splitTimes {
        Distance: distance
        Position: position
        Time: time
        AvgSpeed: avgSpeed
      }
      StartPosition: startPosition
      BarrierNumber: barrierNumber
      RaceTime: finishTime
      TimeVarToWinner: timeVarToWinner
      BeatenMargin: beatenMargin
      DistanceRun: distanceTravelled
      DistanceVarToWinner: distanceVarToWinner
      SixHundredMetresTime: sixHundredMetresTime
      TwoHundredMetresTime: twoHundredMetresTime
    }
  }
}"""

COLUMNS = [
    "request_contract_id",
    "admission_id",
    "race_id",
    "meeting_id",
    "race_date",
    "track",
    "track_key",
    "meet_code",
    "race_no",
    "race_no_numeric",
    "graphql_endpoint",
    "graphql_host",
    "graphql_operation",
    "graphql_resolver",
    "request_method",
    "content_type",
    "referer",
    "api_key_env_var",
    "api_key_value_written",
    "variables_json",
    "query_sha256",
    "query_template_id",
    "request_status",
    "request_reason",
    "created_utc",
    "pipeline_version",
]


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


def main() -> int:
    admitted = [row for row in read_csv(ADMISSION) if clean(row.get("admission_status")) == "ADMITTED_GRAPHQL_SPEED_DATA"]
    contract: list[dict[str, str]] = []
    for row in sorted(admitted, key=lambda item: (item.get("race_date", ""), item.get("track_key", ""), int(clean(item.get("race_no_numeric")) or "0"))):
        meet_code = clean(row.get("meet_code"))
        rno = clean(row.get("race_no_numeric"))
        rendered_query = QUERY % {"meet_code": meet_code, "race_no": rno}
        variables = {"meetCode": meet_code, "raceNumber": int(rno)}
        contract.append(
            {
                "request_contract_id": f"GRAPHQL_REQUEST_{clean(row.get('race_id'))}",
                "admission_id": clean(row.get("admission_id")),
                "race_id": clean(row.get("race_id")),
                "meeting_id": clean(row.get("meeting_id")),
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "track_key": clean(row.get("track_key")),
                "meet_code": meet_code,
                "race_no": rno,
                "race_no_numeric": rno,
                "graphql_endpoint": GRAPHQL_ENDPOINT,
                "graphql_host": clean(row.get("source_host")),
                "graphql_operation": clean(row.get("graphql_operation")),
                "graphql_resolver": clean(row.get("graphql_resolver")),
                "request_method": "POST",
                "content_type": "application/json",
                "referer": "https://dxp-static.racing.com/",
                "api_key_env_var": API_KEY_ENV,
                "api_key_value_written": "NO",
                "variables_json": json.dumps(variables, separators=(",", ":"), ensure_ascii=True),
                "query_sha256": hashlib.sha256(rendered_query.encode("utf-8")).hexdigest(),
                "query_template_id": "RACINGCOM_SECTIONALTIMES_CALLBACK_GETRACEFORM_V1",
                "request_status": "READY_FOR_GOVERNED_ACQUISITION",
                "request_reason": "Built only from admitted GraphQL speed-data race evidence.",
                "created_utc": BUILT_UTC,
                "pipeline_version": PIPELINE_VERSION,
            }
        )
    audit = [
        ("five_request_contract_rows", len(contract) == 5, len(contract), "Only five admitted speed races should produce requests."),
        ("no_negative_controls_in_request_queue", all("MOE" not in row["race_id"] for row in contract), sum(1 for row in contract if "MOE" in row["race_id"]), "No no-speed controls may enter acquisition queue."),
        ("all_have_meet_code", all(row["meet_code"] for row in contract), sum(1 for row in contract if row["meet_code"]), "Every request has directly evidenced meet code."),
        ("all_have_numeric_race_number", all(row["race_no_numeric"].isdigit() for row in contract), sum(1 for row in contract if row["race_no_numeric"].isdigit()), "Every request has numeric race number."),
        ("api_key_not_written", all(row["api_key_value_written"] == "NO" for row in contract), sum(1 for row in contract if row["api_key_value_written"] != "NO"), "No API key values are written to the request contract."),
        ("deterministic_ordering", contract == sorted(contract, key=lambda item: (item["race_date"], item["track_key"], int(item["race_no_numeric"]))), int(contract == sorted(contract, key=lambda item: (item["race_date"], item["track_key"], int(item["race_no_numeric"])))), "Request rows are deterministic."),
    ]
    audit_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "count": count, "detail": detail} for name, passed, count, detail in audit]
    hard_pass = all(row["status"] == "PASS" for row in audit_rows)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_REQUEST_CONTRACT_V1_PASS" if hard_pass else "RACINGCOM_GRAPHQL_REQUEST_CONTRACT_V1_REVIEW_REQUIRED",
        "request_rows": len(contract),
        "api_key_value_written": "NO",
        "negative_controls_in_queue": sum(1 for row in contract if "MOE" in row["race_id"]),
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(REQUEST_CONTRACT, contract, COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL Request Contract V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Counts",
                f"- Request rows: `{summary['request_rows']}`",
                f"- Negative controls in queue: `{summary['negative_controls_in_queue']}`",
                f"- API key value written: `{summary['api_key_value_written']}`",
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
