from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

RAW = DATA / "racingcom_rendered_speed_data_raw_v1.csv"
NORMALISED = DATA / "racingcom_rendered_speed_data_normalised_v1.csv"
SPLITS = DATA / "racingcom_rendered_speed_data_splits_v1.csv"
HARVEST_AUDIT = DATA / "racingcom_rendered_speed_data_harvester_v1_audit.csv"
WAREHOUSE = DATA / "racingcom_sectional_warehouse_v1.csv"
WAREHOUSE_AUDIT = DATA / "racingcom_sectional_warehouse_v1_audit.csv"
WAREHOUSE_SCRIPT = SCRIPTS / "build_racingcom_sectional_warehouse_v1.py"
BATCH_DIR = DATA / "racingcom_rendered_speed_data_batches"

OUT = DATA / "racingcom_batch_persistence_v1.csv"
AUDIT_OUT = DATA / "racingcom_batch_persistence_v1_audit.csv"

# These counts are the only available evidence of previous overwritten batch outputs.
# They come from the task context because the prior batch CSV snapshots no longer exist.
REPORTED_BATCH_UNIQUE_RACES = {
    "250": 224,
    "500": 220,
    "750": 210,
    "1000": 196,
}

DETAIL_COLUMNS = [
    "check_name",
    "status",
    "evidence",
    "row_count",
    "unique_races",
    "file_path",
    "notes",
]

AUDIT_COLUMNS = [
    "overwrite_mode_detected",
    "append_mode_detected",
    "latest_batch_only_detected",
    "latest_batch_offset",
    "latest_batch_unique_races",
    "expected_races_if_accumulated",
    "actual_races_in_warehouse",
    "missing_races_estimate",
    "rendered_normalised_unique_races",
    "rendered_raw_unique_races",
    "rendered_splits_unique_races",
    "batch_archive_files_found",
    "warehouse_consumes_batch_archive",
    "warehouse_consumes_live_snapshot",
    "exact_behaviour",
    "recommendation",
    "final_status",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else re.sub(r"\s+", " ", text)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def race_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            clean(row.get("meeting_date") or row.get("race_date")),
            clean(row.get("track")).upper(),
            clean(row.get("race_no") or row.get("race_number")),
        ]
    )


def unique_races(path: Path) -> int:
    rows = read_csv(path)
    return len({race_key(row) for row in rows if race_key(row).replace("|", "")})


def first_row(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    return rows[0] if rows else {}


def file_row_count(path: Path) -> int:
    return len(read_csv(path))


def script_contains(path: Path, text: str) -> bool:
    if not path.exists():
        return False
    return text.lower() in path.read_text(encoding="utf-8", errors="ignore").lower()


def bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def main() -> None:
    harvester = first_row(HARVEST_AUDIT)
    warehouse_audit = first_row(WAREHOUSE_AUDIT)
    latest_offset = clean(harvester.get("offset"))
    latest_unique = int(float(clean(harvester.get("unique_races")) or "0"))
    expected_accumulated = sum(REPORTED_BATCH_UNIQUE_RACES.values())
    actual_warehouse = int(float(clean(warehouse_audit.get("warehouse_unique_races")) or "0")) or unique_races(WAREHOUSE)

    normalised_unique = unique_races(NORMALISED)
    raw_unique = unique_races(RAW)
    splits_unique = unique_races(SPLITS)
    batch_files = list(BATCH_DIR.glob("batch_*_normalised.csv")) if BATCH_DIR.exists() else []

    warehouse_consumes_live = script_contains(WAREHOUSE_SCRIPT, "racingcom_rendered_speed_data_normalised_v1.csv")
    warehouse_consumes_batches = script_contains(WAREHOUSE_SCRIPT, "racingcom_rendered_speed_data_batches")
    harvester_script = SCRIPTS / "build_racingcom_rendered_speed_data_harvester_v1.py"
    harvester_writes_batch_archive = script_contains(harvester_script, "racingcom_rendered_speed_data_batches")
    overwrite_mode = bool(latest_offset and normalised_unique == latest_unique and warehouse_consumes_live)
    append_mode = bool(batch_files and harvester_writes_batch_archive)
    latest_only = bool(warehouse_consumes_live and not warehouse_consumes_batches)
    missing_estimate = max(0, expected_accumulated - actual_warehouse)

    detail_rows = [
        {
            "check_name": "harvester_latest_audit",
            "status": "LATEST_BATCH_AUDIT_FOUND" if harvester else "MISSING",
            "evidence": f"offset={latest_offset}; batch_size={clean(harvester.get('batch_size'))}; unique_races={latest_unique}",
            "row_count": "",
            "unique_races": latest_unique,
            "file_path": str(HARVEST_AUDIT),
            "notes": "Harvester audit is a single latest-run file, not a historical audit log.",
        },
        {
            "check_name": "rendered_normalised_snapshot",
            "status": "LIVE_SNAPSHOT_FILE",
            "evidence": f"rows={file_row_count(NORMALISED)}; unique_races={normalised_unique}",
            "row_count": file_row_count(NORMALISED),
            "unique_races": normalised_unique,
            "file_path": str(NORMALISED),
            "notes": "File name has no batch offset and matches latest audit race count.",
        },
        {
            "check_name": "rendered_raw_snapshot",
            "status": "LIVE_SNAPSHOT_FILE",
            "evidence": f"rows={file_row_count(RAW)}; unique_races={raw_unique}",
            "row_count": file_row_count(RAW),
            "unique_races": raw_unique,
            "file_path": str(RAW),
            "notes": "Raw rendered rows are also stored in a single live file.",
        },
        {
            "check_name": "rendered_splits_snapshot",
            "status": "LIVE_SNAPSHOT_FILE",
            "evidence": f"rows={file_row_count(SPLITS)}; unique_races={splits_unique}",
            "row_count": file_row_count(SPLITS),
            "unique_races": splits_unique,
            "file_path": str(SPLITS),
            "notes": "Split metrics are stored in a single live file.",
        },
        {
            "check_name": "batch_archive_directory",
            "status": "NO_BATCH_ARCHIVE_FOUND" if not batch_files else "BATCH_ARCHIVE_FOUND",
            "evidence": f"batch_normalised_files={len(batch_files)}",
            "row_count": len(batch_files),
            "unique_races": "",
            "file_path": str(BATCH_DIR),
            "notes": "No archive files means prior batches cannot be accumulated by the warehouse.",
        },
        {
            "check_name": "warehouse_v1_input_mode",
            "status": "LATEST_BATCH_ONLY" if warehouse_consumes_live and not warehouse_consumes_batches else "BATCH_AWARE",
            "evidence": f"consumes_live_snapshot={bool_text(warehouse_consumes_live)}; consumes_batch_archive={bool_text(warehouse_consumes_batches)}",
            "row_count": file_row_count(WAREHOUSE),
            "unique_races": actual_warehouse,
            "file_path": str(WAREHOUSE_SCRIPT),
            "notes": "Warehouse V1 reads current live rendered files directly.",
        },
        {
            "check_name": "reported_overwritten_batch_total",
            "status": "USER_REPORTED_PRIOR_BATCH_COUNTS",
            "evidence": "; ".join(f"offset_{offset}={count}" for offset, count in REPORTED_BATCH_UNIQUE_RACES.items()),
            "row_count": "",
            "unique_races": expected_accumulated,
            "file_path": "",
            "notes": "These race counts cannot be reconstructed from current live files because earlier batches were overwritten.",
        },
    ]

    exact_behaviour = (
        "Rendered-speed raw, normalised, and splits CSVs are overwritten on each harvester run. "
        "Warehouse V1 consumes those live snapshot files, so it only sees the latest batch plus legacy CSV/history sources, "
        "not the accumulated set of harvested batches."
    )
    audit_row = {
        "overwrite_mode_detected": bool_text(overwrite_mode),
        "append_mode_detected": bool_text(append_mode),
        "latest_batch_only_detected": bool_text(latest_only),
        "latest_batch_offset": latest_offset,
        "latest_batch_unique_races": latest_unique,
        "expected_races_if_accumulated": expected_accumulated,
        "actual_races_in_warehouse": actual_warehouse,
        "missing_races_estimate": missing_estimate,
        "rendered_normalised_unique_races": normalised_unique,
        "rendered_raw_unique_races": raw_unique,
        "rendered_splits_unique_races": splits_unique,
        "batch_archive_files_found": len(batch_files),
        "warehouse_consumes_batch_archive": bool_text(warehouse_consumes_batches),
        "warehouse_consumes_live_snapshot": bool_text(warehouse_consumes_live),
        "exact_behaviour": exact_behaviour,
        "recommendation": "BUILD_BATCH_ARCHIVE_AND_WAREHOUSE_V2" if overwrite_mode else "NO_ARCHITECTURE_CHANGE_REQUIRED",
        "final_status": "OVERWRITE_CONFIRMED_BATCH_ARCHIVE_PRESENT" if overwrite_mode and append_mode else ("OVERWRITE_CONFIRMED" if overwrite_mode else "OVERWRITE_NOT_CONFIRMED"),
    }

    write_csv(OUT, detail_rows, DETAIL_COLUMNS)
    write_csv(AUDIT_OUT, [audit_row], AUDIT_COLUMNS)

    print("Racing.com batch persistence audit V1 built")
    print(f"overwrite_mode_detected={audit_row['overwrite_mode_detected']}")
    print(f"append_mode_detected={audit_row['append_mode_detected']}")
    print(f"latest_batch_only_detected={audit_row['latest_batch_only_detected']}")
    print(f"expected_races_if_accumulated={expected_accumulated}")
    print(f"actual_races_in_warehouse={actual_warehouse}")
    print(f"missing_races_estimate={missing_estimate}")
    print(f"final_status={audit_row['final_status']}")


if __name__ == "__main__":
    main()
