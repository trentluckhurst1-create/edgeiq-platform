from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
CSV_PARSED = OUT / "edgeiq_racingcom_parser_output_v2.csv"
GRAPHQL_PARSED = OUT / "edgeiq_racingcom_graphql_parser_output_v2.csv"
CANONICAL_OUT = OUT / "edgeiq_racingcom_canonical_speed_contract_v1.csv"
AUDIT_OUT = OUT / "edgeiq_racingcom_canonical_speed_contract_audit_v1.csv"
SUMMARY_OUT = OUT / "edgeiq_racingcom_canonical_speed_contract_summary_v1.json"
REPORT_OUT = OUT / "edgeiq_racingcom_canonical_speed_contract_report_v1.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")

COLUMNS = [
    "canonical_fact_id",
    "source_type",
    "fact_grain",
    "race_id",
    "race_date",
    "track",
    "track_key",
    "state",
    "race_no",
    "race_no_numeric",
    "horse",
    "horse_key",
    "horse_id",
    "saddle_number",
    "barrier",
    "trainer",
    "jockey",
    "final_position",
    "beaten_margin",
    "race_time",
    "distance_label",
    "segment_type",
    "segment_position",
    "segment_time",
    "avg_speed_mps",
    "avg_speed_kmh",
    "last200",
    "last400",
    "last600",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "source_path",
    "source_sha256",
    "normalised_utc",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


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


def kmh_from_mps(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        return f"{float(text) * 3.6:.3f}".rstrip("0").rstrip(".")
    except Exception:
        return ""


def main() -> int:
    canonical: list[dict[str, Any]] = []
    for row in read_csv(CSV_PARSED):
        horse_key = clean(row.get("horse_key")) or norm(row.get("horse"))
        race_id = clean(row.get("race_id"))
        canonical.append(
            {
                "canonical_fact_id": f"CSV_RUNNER_AGGREGATE_{race_id}_{horse_key}",
                "source_type": clean(row.get("sectional_source")) or "RACING.COM_DIRECT_CSV_V2",
                "fact_grain": "RUNNER_AGGREGATE",
                "race_id": race_id,
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "track_key": norm(row.get("track")),
                "state": clean(row.get("state")),
                "race_no": clean(row.get("race_no")),
                "race_no_numeric": clean(row.get("race_no")),
                "horse": clean(row.get("horse")),
                "horse_key": horse_key,
                "barrier": clean(row.get("barrier")),
                "race_time": clean(row.get("race_time")),
                "avg_speed_mps": clean(row.get("avg_speed")),
                "avg_speed_kmh": kmh_from_mps(row.get("avg_speed")),
                "last200": clean(row.get("last200") or row.get("last_200")),
                "last400": clean(row.get("last400") or row.get("last_400")),
                "last600": clean(row.get("last600") or row.get("last_600")),
                "early_speed": clean(row.get("early_speed")),
                "mid_speed": clean(row.get("mid_speed")),
                "late_speed": clean(row.get("late_speed")),
                "peak_speed": clean(row.get("peak_speed")),
                "source_path": clean(row.get("source_cache_path") or row.get("source_url")),
                "source_sha256": clean(row.get("source_sha256")),
                "normalised_utc": BUILT_UTC,
            }
        )
    for row in read_csv(GRAPHQL_PARSED):
        horse_key = norm(row.get("horse"))
        race_id = clean(row.get("race_id"))
        canonical.append(
            {
                "canonical_fact_id": f"GRAPHQL_{clean(row.get('row_type'))}_{race_id}_{clean(row.get('horse_id'))}_{clean(row.get('distance_label'))}",
                "source_type": clean(row.get("source_type")),
                "fact_grain": "SEGMENT",
                "race_id": race_id,
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "track_key": clean(row.get("track_key")),
                "state": "VIC",
                "race_no": clean(row.get("race_no")),
                "race_no_numeric": clean(row.get("race_no_numeric")),
                "horse": clean(row.get("horse")),
                "horse_key": horse_key,
                "horse_id": clean(row.get("horse_id")),
                "saddle_number": clean(row.get("saddle_number")),
                "barrier": clean(row.get("barrier_number")),
                "trainer": clean(row.get("trainer")),
                "jockey": clean(row.get("jockey")),
                "final_position": clean(row.get("final_position")),
                "beaten_margin": clean(row.get("beaten_margin")),
                "race_time": clean(row.get("race_time")),
                "distance_label": clean(row.get("distance_label")),
                "segment_type": clean(row.get("row_type")),
                "segment_position": clean(row.get("position")),
                "segment_time": clean(row.get("time")),
                "avg_speed_mps": clean(row.get("avg_speed_mps")),
                "avg_speed_kmh": clean(row.get("avg_speed_kmh")),
                "source_path": clean(row.get("response_path")),
                "source_sha256": clean(row.get("response_sha256")),
                "normalised_utc": BUILT_UTC,
            }
        )
    canonical = sorted(
        canonical,
        key=lambda row: (
            row.get("race_date", ""),
            row.get("track_key", ""),
            int(row.get("race_no_numeric") or "0"),
            row.get("horse_key", ""),
            row.get("fact_grain", ""),
            row.get("segment_type", ""),
            row.get("distance_label", ""),
        ),
    )
    duplicates = len(canonical) - len({row["canonical_fact_id"] for row in canonical})
    graphql_rows = [row for row in canonical if row["source_type"] == "RACINGCOM_GRAPHQL_GETRACEFORM"]
    csv_speed_missing = sum(1 for row in canonical if row["fact_grain"] == "RUNNER_AGGREGATE" and (not row.get("avg_speed_mps") or not row.get("avg_speed_kmh")))
    audit = [
        ("canonical_rows_gt_zero", len(canonical) > 0, len(canonical), "Canonical rows emitted."),
        ("csv_runner_aggregate_rows_retained", sum(1 for row in canonical if row["fact_grain"] == "RUNNER_AGGREGATE") == len(read_csv(CSV_PARSED)), sum(1 for row in canonical if row["fact_grain"] == "RUNNER_AGGREGATE"), "CSV aggregate rows retained."),
        ("graphql_segment_rows_retained", sum(1 for row in canonical if row["source_type"] == "RACINGCOM_GRAPHQL_GETRACEFORM") == len(read_csv(GRAPHQL_PARSED)), sum(1 for row in canonical if row["source_type"] == "RACINGCOM_GRAPHQL_GETRACEFORM"), "GraphQL segment rows retained."),
        ("no_duplicate_canonical_fact_ids", duplicates == 0, duplicates, "Canonical fact IDs unique."),
        ("source_hashes_retained", all(row["source_sha256"] for row in canonical), sum(1 for row in canonical if row["source_sha256"]), "Source hashes retained."),
        ("graphql_speed_units_explicit", all(row["avg_speed_mps"] and row["avg_speed_kmh"] for row in graphql_rows), sum(1 for row in graphql_rows if row["avg_speed_mps"] and row["avg_speed_kmh"]), "GraphQL m/s and km/h fields populated."),
        ("historical_csv_missing_speed_reported", True, csv_speed_missing, "Historical CSV aggregate rows with missing source speed retained as blanks, not invented."),
    ]
    audit_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "count": count, "detail": detail} for name, passed, count, detail in audit]
    hard_pass = all(row["status"] == "PASS" for row in audit_rows)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_CANONICAL_SPEED_CONTRACT_V1_PASS" if hard_pass else "RACINGCOM_CANONICAL_SPEED_CONTRACT_V1_REVIEW_REQUIRED",
        "canonical_rows": len(canonical),
        "csv_runner_aggregate_rows": sum(1 for row in canonical if row["fact_grain"] == "RUNNER_AGGREGATE"),
        "graphql_segment_rows": sum(1 for row in canonical if row["source_type"] == "RACINGCOM_GRAPHQL_GETRACEFORM"),
        "races": len({row["race_id"] for row in canonical}),
        "duplicate_fact_ids": duplicates,
        "historical_csv_missing_speed_rows": csv_speed_missing,
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(CANONICAL_OUT, canonical, COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com Canonical Speed Contract V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Counts",
                f"- Canonical rows: `{summary['canonical_rows']}`",
                f"- CSV runner aggregate rows: `{summary['csv_runner_aggregate_rows']}`",
                f"- GraphQL segment rows: `{summary['graphql_segment_rows']}`",
                f"- Races: `{summary['races']}`",
                "",
                "## Grain",
                "",
                "`RUNNER_AGGREGATE` rows preserve historical CSV parser shape. `SEGMENT` rows preserve GraphQL sectional and split detail.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
