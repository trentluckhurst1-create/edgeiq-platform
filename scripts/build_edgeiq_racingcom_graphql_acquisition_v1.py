from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
RAW_OUT = ROOT / "outputs" / "performance-intelligence" / "racingcom-ingestion-v2" / "raw" / "graphql-acquisition"
REQUEST_CONTRACT = OUT / "edgeiq_racingcom_graphql_request_contract_v1.csv"
ACQUISITION_OUT = OUT / "edgeiq_racingcom_graphql_acquisition_v1.csv"
REJECTIONS_OUT = OUT / "edgeiq_racingcom_graphql_acquisition_rejections_v1.csv"
AUDIT_OUT = OUT / "edgeiq_racingcom_graphql_acquisition_audit_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_acquisition_summary_v1.json"
REPORT_OUT = OUT / "edgeiq_racingcom_graphql_acquisition_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")
ENV_VAR = "RACINGCOM_PUBLIC_WIDGET_API_KEY"

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


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", clean(value)).strip("_")


def fetch(row: dict[str, str], api_key: str) -> tuple[int, str, bytes]:
    query = QUERY % {"meet_code": clean(row.get("meet_code")), "race_no": clean(row.get("race_no_numeric"))}
    body = json.dumps({"query": query}, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        clean(row.get("graphql_endpoint")),
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "referer": clean(row.get("referer")) or "https://dxp-static.racing.com/",
            "user-agent": "EDGEiQ-Racing/1.0 governed-graphql-acquisition",
            "x-api-key": api_key,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
        return int(response.status), clean(response.headers.get("content-type")), payload


def main() -> int:
    api_key = clean(os.environ.get(ENV_VAR))
    requests = read_csv(REQUEST_CONTRACT)
    acquisition_rows: list[dict[str, Any]] = []
    rejection_rows: list[dict[str, Any]] = []

    if not api_key:
        for row in requests:
            rejection_rows.append(
                {
                    "request_contract_id": clean(row.get("request_contract_id")),
                    "race_id": clean(row.get("race_id")),
                    "rejection_status": "BLOCKED_MISSING_API_KEY_ENV",
                    "rejection_reason": f"{ENV_VAR} is not present in the process environment.",
                }
            )
    else:
        RAW_OUT.mkdir(parents=True, exist_ok=True)
        for row in requests:
            try:
                status, content_type, payload = fetch(row, api_key)
                digest = hashlib.sha256(payload).hexdigest()
                cache_path = RAW_OUT / f"{safe_filename(row.get('race_id'))}_{digest[:16]}.json"
                cache_path.write_bytes(payload)
                acquisition_rows.append(
                    {
                        "request_contract_id": clean(row.get("request_contract_id")),
                        "race_id": clean(row.get("race_id")),
                        "race_date": clean(row.get("race_date")),
                        "track": clean(row.get("track")),
                        "track_key": clean(row.get("track_key")),
                        "meet_code": clean(row.get("meet_code")),
                        "race_no": clean(row.get("race_no")),
                        "race_no_numeric": clean(row.get("race_no_numeric")),
                        "http_status": status,
                        "content_type": content_type,
                        "response_size": len(payload),
                        "response_sha256": digest,
                        "response_path": str(cache_path.relative_to(ROOT)),
                        "acquisition_status": "ACQUIRED_GRAPHQL_RESPONSE" if status == 200 else "HTTP_REVIEW_REQUIRED",
                        "api_key_value_written": "NO",
                        "acquired_utc": BUILT_UTC,
                    }
                )
                time.sleep(0.2)
            except Exception as exc:
                rejection_rows.append(
                    {
                        "request_contract_id": clean(row.get("request_contract_id")),
                        "race_id": clean(row.get("race_id")),
                        "rejection_status": "FETCH_FAILED",
                        "rejection_reason": str(exc),
                    }
                )

    audit = [
        ("request_rows_seen", len(requests) == 5, len(requests), "Expected five request contract rows."),
        ("all_requests_acquired", len(acquisition_rows) == 5, len(acquisition_rows), "All five GraphQL responses acquired."),
        ("no_rejections", len(rejection_rows) == 0, len(rejection_rows), "No acquisition rejections."),
        ("api_key_value_not_written", all(row.get("api_key_value_written") == "NO" for row in acquisition_rows), sum(1 for row in acquisition_rows if row.get("api_key_value_written") != "NO"), "Raw API key never written to outputs."),
        ("response_hashes_retained", all(row.get("response_sha256") for row in acquisition_rows), sum(1 for row in acquisition_rows if row.get("response_sha256")), "Response hashes retained."),
    ]
    audit_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "count": count, "detail": detail} for name, passed, count, detail in audit]
    hard_pass = all(row["status"] == "PASS" for row in audit_rows)
    status = "RACINGCOM_GRAPHQL_ACQUISITION_V1_PASS" if hard_pass else ("RACINGCOM_GRAPHQL_ACQUISITION_V1_BLOCKED_BY_CONFIG" if not api_key else "RACINGCOM_GRAPHQL_ACQUISITION_V1_REVIEW_REQUIRED")
    summary = {
        "built_utc": BUILT_UTC,
        "status": status,
        "request_rows": len(requests),
        "acquired_rows": len(acquisition_rows),
        "rejections": len(rejection_rows),
        "api_key_env_present": "YES" if bool(api_key) else "NO",
        "api_key_value_written": "NO",
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(ACQUISITION_OUT, acquisition_rows, ["request_contract_id", "race_id", "race_date", "track", "track_key", "meet_code", "race_no", "race_no_numeric", "http_status", "content_type", "response_size", "response_sha256", "response_path", "acquisition_status", "api_key_value_written", "acquired_utc"])
    write_csv(REJECTIONS_OUT, rejection_rows, ["request_contract_id", "race_id", "rejection_status", "rejection_reason"])
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL Acquisition V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Counts",
                f"- Request rows: `{summary['request_rows']}`",
                f"- Acquired rows: `{summary['acquired_rows']}`",
                f"- Rejections: `{summary['rejections']}`",
                f"- API key env present: `{summary['api_key_env_present']}`",
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
