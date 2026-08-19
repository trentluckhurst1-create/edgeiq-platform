from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
ACQUISITION = OUT / "edgeiq_racingcom_graphql_acquisition_v1.csv"
PARSED_OUT = OUT / "edgeiq_racingcom_graphql_parser_output_v2.csv"
REJECTIONS_OUT = OUT / "edgeiq_racingcom_graphql_parser_rejections_v2.csv"
AUDIT_OUT = OUT / "edgeiq_racingcom_graphql_parser_v2_audit.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_graphql_parser_v2_summary.json"
REPORT_OUT = OUT / "edgeiq_racingcom_graphql_parser_v2_report.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")

OUTPUT_COLUMNS = [
    "source_type",
    "race_id",
    "race_date",
    "track",
    "track_key",
    "race_no",
    "race_no_numeric",
    "horse_id",
    "horse",
    "saddle_number",
    "trainer",
    "jockey",
    "final_position",
    "final_position_abbreviation",
    "comment",
    "barrier_number",
    "start_position",
    "race_time",
    "beaten_margin",
    "distance_run",
    "time_var_to_winner",
    "distance_var_to_winner",
    "six_hundred_metres_time",
    "two_hundred_metres_time",
    "row_type",
    "distance_label",
    "position",
    "time",
    "avg_speed_mps",
    "avg_speed_kmh",
    "response_path",
    "response_sha256",
    "parsed_utc",
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean(row.get(column, "")) for column in columns})


def parse_float(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        return f"{float(text):.6f}".rstrip("0").rstrip(".")
    except Exception:
        return ""


def speed_kmh(value: Any) -> str:
    text = parse_float(value)
    if not text:
        return ""
    return f"{float(text) * 3.6:.3f}".rstrip("0").rstrip(".")


def parse_int(value: Any) -> str:
    text = clean(value)
    match = re.search(r"-?\d+", text)
    return str(int(match.group(0))) if match else ""


def main() -> int:
    acquisition_rows = read_csv(ACQUISITION)
    parsed: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for race in acquisition_rows:
        path = ROOT / clean(race.get("response_path"))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            horses = ((payload.get("data") or {}).get("sectionaltimes_callback") or {}).get("Horses") or []
            if not horses:
                raise ValueError("No Horses population in GraphQL response.")
            for horse in horses:
                base = {
                    "source_type": "RACINGCOM_GRAPHQL_GETRACEFORM",
                    "race_id": clean(race.get("race_id")),
                    "race_date": clean(race.get("race_date")),
                    "track": clean(race.get("track")),
                    "track_key": clean(race.get("track_key")),
                    "race_no": clean(race.get("race_no")),
                    "race_no_numeric": clean(race.get("race_no_numeric")),
                    "horse_id": clean(horse.get("id")),
                    "horse": clean(horse.get("FullName")),
                    "saddle_number": clean(horse.get("SaddleNumber")),
                    "trainer": clean(horse.get("Trainer")),
                    "jockey": clean(horse.get("Jockey")),
                    "final_position": parse_int(horse.get("FinalPosition")),
                    "final_position_abbreviation": clean(horse.get("FinalPositionAbbreviation")),
                    "comment": clean(horse.get("Comment")),
                    "barrier_number": clean(horse.get("BarrierNumber")),
                    "start_position": clean(horse.get("StartPosition")),
                    "race_time": clean(horse.get("RaceTime")),
                    "beaten_margin": parse_float(horse.get("BeatenMargin")),
                    "distance_run": parse_float(horse.get("DistanceRun")),
                    "time_var_to_winner": parse_float(horse.get("TimeVarToWinner")),
                    "distance_var_to_winner": clean(horse.get("DistanceVarToWinner")),
                    "six_hundred_metres_time": clean(horse.get("SixHundredMetresTime")),
                    "two_hundred_metres_time": clean(horse.get("TwoHundredMetresTime")),
                    "response_path": clean(race.get("response_path")),
                    "response_sha256": clean(race.get("response_sha256")),
                    "parsed_utc": BUILT_UTC,
                }
                for row_type, rows in [("SECTIONAL", horse.get("SectionalTimes") or []), ("SPLIT", horse.get("SplitTimes") or [])]:
                    for item in rows:
                        speed = parse_float(item.get("AvgSpeed"))
                        parsed.append(
                            {
                                **base,
                                "row_type": row_type,
                                "distance_label": clean(item.get("Distance")),
                                "position": parse_int(item.get("Position")),
                                "time": clean(item.get("Time")),
                                "avg_speed_mps": speed,
                                "avg_speed_kmh": speed_kmh(speed),
                            }
                        )
        except Exception as exc:
            rejections.append(
                {
                    "race_id": clean(race.get("race_id")),
                    "response_path": clean(race.get("response_path")),
                    "rejection_status": "PARSER_REJECTED_RESPONSE",
                    "rejection_reason": str(exc),
                }
            )
    sectionals = [row for row in parsed if row["row_type"] == "SECTIONAL"]
    splits = [row for row in parsed if row["row_type"] == "SPLIT"]
    audit = [
        ("parsed_rows_gt_zero", len(parsed) > 0, len(parsed), "Parser emitted rows."),
        ("five_races_parsed", len({row["race_id"] for row in parsed}) == 5, len({row["race_id"] for row in parsed}), "Five races parsed."),
        ("sectional_rows_match_validation", len(sectionals) == 449, len(sectionals), "Sectional rows match validation count."),
        ("split_rows_match_validation", len(splits) == 449, len(splits), "Split rows match validation count."),
        ("no_parser_rejections", len(rejections) == 0, len(rejections), "No parser rejections."),
        ("avg_speed_mps_retained", all(row["avg_speed_mps"] for row in parsed), sum(1 for row in parsed if row["avg_speed_mps"]), "Source AvgSpeed retained in m/s."),
        ("avg_speed_kmh_derived", all(row["avg_speed_kmh"] for row in parsed), sum(1 for row in parsed if row["avg_speed_kmh"]), "km/h display value derived explicitly."),
    ]
    audit_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "count": count, "detail": detail} for name, passed, count, detail in audit]
    hard_pass = all(row["status"] == "PASS" for row in audit_rows)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_PARSER_V2_PASS" if hard_pass else "RACINGCOM_GRAPHQL_PARSER_V2_REVIEW_REQUIRED",
        "parsed_rows": len(parsed),
        "races": len({row["race_id"] for row in parsed}),
        "horses": len({(row["race_id"], row["horse_id"]) for row in parsed}),
        "sectional_rows": len(sectionals),
        "split_rows": len(splits),
        "rejections": len(rejections),
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(PARSED_OUT, parsed, OUTPUT_COLUMNS)
    write_csv(REJECTIONS_OUT, rejections, ["race_id", "response_path", "rejection_status", "rejection_reason"])
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL Parser V2",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Counts",
                f"- Parsed rows: `{summary['parsed_rows']}`",
                f"- Races: `{summary['races']}`",
                f"- Horses: `{summary['horses']}`",
                f"- Sectional rows: `{summary['sectional_rows']}`",
                f"- Split rows: `{summary['split_rows']}`",
                "",
                "## Speed Semantics",
                "",
                "Source `AvgSpeed` is retained as m/s and `avg_speed_kmh` is derived as m/s * 3.6.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
