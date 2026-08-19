from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PRODUCTION = ROOT / "public" / "data" / "edgeiq_racingcom_performance_warehouse_v2.csv"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")

SCHEMA = DOCS / "edgeiq_racingcom_production_runner_schema_v1.csv"
KEY_PROFILE = DOCS / "edgeiq_racingcom_production_runner_key_profile_v1.csv"
NULL_PROFILE = DOCS / "edgeiq_racingcom_production_runner_null_profile_v1.csv"
UNIT_PROFILE = DOCS / "edgeiq_racingcom_production_runner_unit_profile_v1.csv"
AUDIT = DOCS / "edgeiq_racingcom_production_runner_contract_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_production_runner_contract_summary_v1.json"
REPORT = DOCS / "edgeiq_racingcom_production_runner_contract_report_v1.md"


IDENTITY = {"warehouse_record_id", "race_id", "race_date", "track", "state", "race_no", "distance", "horse", "horse_key", "barrier"}
SPEED = {"early_speed", "mid_speed", "late_speed", "peak_speed", "avg_speed"}
SECTIONAL = {"last200", "last400", "last600", "last_200", "last_400", "last_600", "race_time"}
PROVENANCE = {"sectional_source", "source_csv_url", "source_cache_path", "source_sha256", "acquisition_timestamp", "parser_version", "pipeline_version", "meeting_discovery_version", "race_discovery_version", "admission_version", "warehouse_built_utc"}
STATUS = {"tempo_grade", "pace_profile"}


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(rows[0].keys()) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean(row.get(column, "")) for column in columns})


def infer_type(values: list[str]) -> str:
    vals = [clean(v) for v in values if clean(v)]
    if not vals:
        return "ALL_NULL"
    int_ok = True
    num_ok = True
    iso_date_ok = True
    for value in vals:
        if not re.fullmatch(r"-?\d+", value):
            int_ok = False
        try:
            float(value)
        except Exception:
            num_ok = False
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value):
            iso_date_ok = False
    if iso_date_ok:
        return "DATE"
    if int_ok:
        return "INTEGER"
    if num_ok:
        return "NUMBER"
    return "TEXT"


def classify(column: str) -> str:
    if column in IDENTITY:
        return "IDENTITY"
    if column in SPEED or column in SECTIONAL:
        return "SOURCE_VALUE" if column in SECTIONAL else "AGGREGATE_VALUE"
    if column in PROVENANCE:
        return "PROVENANCE"
    if column in STATUS:
        return "STATUS"
    return "UNRESOLVED"


def unit_rule(column: str) -> str:
    if column in {"early_speed", "mid_speed", "late_speed", "peak_speed", "avg_speed"}:
        return "M_PER_SECOND"
    if column in {"last200", "last400", "last600", "last_200", "last_400", "last_600"}:
        return "SECONDS"
    if column == "distance":
        return "METRES"
    if column == "race_time":
        return "SOURCE_TIME_STRING"
    return "NOT_APPLICABLE"


def main() -> int:
    rows, columns = read_csv(PRODUCTION)
    schema_rows = []
    null_rows = []
    unit_rows = []
    for index, column in enumerate(columns, start=1):
        values = [row.get(column, "") for row in rows]
        nonblank = sum(1 for value in values if clean(value))
        blanks = len(values) - nonblank
        schema_rows.append(
            {
                "ordinal": index,
                "column_name": column,
                "column_classification": classify(column),
                "inferred_type": infer_type(values),
                "nonblank_count": nonblank,
                "blank_count": blanks,
                "nullable": "YES" if blanks else "NO",
                "example_values": " | ".join(list(dict.fromkeys(clean(v) for v in values if clean(v)))[:5]),
            }
        )
        null_rows.append({"column_name": column, "rows": len(rows), "nonblank_count": nonblank, "blank_count": blanks, "nullability_pct": round((blanks / len(rows) * 100) if rows else 0, 4)})
        unit_rows.append({"column_name": column, "unit_rule": unit_rule(column), "rounding_rule": "PRESERVE_SOURCE_STRING", "production_role": classify(column)})

    key_candidates = [
        ("warehouse_record_id", lambda r: clean(r.get("warehouse_record_id"))),
        ("race_id+horse_key", lambda r: f"{clean(r.get('race_id'))}::{clean(r.get('horse_key'))}"),
        ("race_date+track+race_no+horse_key", lambda r: f"{clean(r.get('race_date'))}::{clean(r.get('track'))}::{clean(r.get('race_no'))}::{clean(r.get('horse_key'))}"),
    ]
    key_rows = []
    for name, fn in key_candidates:
        keys = [fn(row) for row in rows]
        counts = Counter(keys)
        key_rows.append({"key_candidate": name, "rows": len(rows), "unique_keys": len(counts), "duplicate_keys": sum(1 for key, count in counts.items() if count > 1), "blank_keys": sum(1 for key in keys if not clean(key)), "is_exact_key": "YES" if len(counts) == len(rows) and all(clean(k) for k in keys) else "NO"})

    sorted_rows = sorted(rows, key=lambda r: (clean(r.get("race_date")), clean(r.get("track")), int(float(clean(r.get("race_no")) or "9999")), clean(r.get("horse_key"))))
    duplicate_records = len(rows) - len({row.get("warehouse_record_id", "") for row in rows})
    duplicate_runner_keys = len(rows) - len({f"{row.get('race_id','')}::{row.get('horse_key','')}" for row in rows})
    unresolved = [row for row in schema_rows if row["column_classification"] == "UNRESOLVED"]
    checks = [
        ("production_exists", PRODUCTION.exists(), int(PRODUCTION.exists()), str(PRODUCTION.relative_to(ROOT))),
        ("row_count_80", len(rows) == 80, len(rows), "Production has 80 runner aggregate rows."),
        ("column_count_35", len(columns) == 35, len(columns), "Production has 35 fixed columns."),
        ("warehouse_record_id_unique", duplicate_records == 0, duplicate_records, "warehouse_record_id is unique."),
        ("race_id_horse_key_unique", duplicate_runner_keys == 0, duplicate_runner_keys, "race_id+horse_key is unique."),
        ("sorting_rule_confirmed", rows == sorted_rows, int(rows == sorted_rows), "Rows sorted by race_date, track, race_no, horse_key."),
        ("no_unresolved_columns", len(unresolved) == 0, len(unresolved), "Every production column classified."),
    ]
    audit_rows = [{"check": n, "status": "PASS" if p else "FAIL", "count": c, "detail": d} for n, p, c, d in checks]
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_PRODUCTION_RUNNER_CONTRACT_PROFILE_PASS" if all(r["status"] == "PASS" for r in audit_rows) else "RACINGCOM_PRODUCTION_RUNNER_CONTRACT_PROFILE_REVIEW_REQUIRED",
        "production_path": str(PRODUCTION.relative_to(ROOT)),
        "rows": len(rows),
        "columns": len(columns),
        "canonical_key": "warehouse_record_id",
        "secondary_key": "race_id+horse_key",
        "row_grain": "RUNNER_AGGREGATE",
        "duplicate_records": duplicate_records,
        "duplicate_runner_keys": duplicate_runner_keys,
        "sorting_rule": "race_date, track, numeric race_no, horse_key",
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(SCHEMA, schema_rows)
    write_csv(KEY_PROFILE, key_rows)
    write_csv(NULL_PROFILE, null_rows)
    write_csv(UNIT_PROFILE, unit_rows)
    write_csv(AUDIT, audit_rows)
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT.write_text(
        "\n".join(
            [
                "# Racing.com Production Runner Contract Profile V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Contract",
                "",
                "- Row grain: `RUNNER_AGGREGATE`",
                "- Exact production row key: `warehouse_record_id`",
                "- Secondary semantic key: `race_id + horse_key`",
                "- Column count: `35`",
                "- Sorting: `race_date, track, numeric race_no, horse_key`",
                "",
                "## Unit Rules",
                "",
                "- Speed fields: source m/s.",
                "- Split fields: source seconds.",
                "- Race time: source time string.",
                "- Rounding: preserve source string.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if summary["status"].endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
