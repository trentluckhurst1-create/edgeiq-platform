from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUTS = ROOT / "outputs"

BATCH_DIR = DATA / "racingcom_rendered_speed_data_batches"
RECOVERY_AUDIT = DATA / "racingcom_batch_recovery_v1.csv"

LIVE_RAW = DATA / "racingcom_rendered_speed_data_raw_v1.csv"
LIVE_NORMALISED = DATA / "racingcom_rendered_speed_data_normalised_v1.csv"
LIVE_SPLITS = DATA / "racingcom_rendered_speed_data_splits_v1.csv"
LIVE_AUDIT = DATA / "racingcom_rendered_speed_data_harvester_v1_audit.csv"
TMP_OUTPUT = OUTPUTS / "tmp" / "build_racingcom_rendered_speed_data_harvester_v1_output.json"

OUT = DATA / "racingcom_historical_batches_recovered_v1.csv"
AUDIT_OUT = DATA / "racingcom_historical_batches_recovered_v1_audit.csv"

DETAIL_COLUMNS = [
    "offset",
    "recovery_action",
    "raw_output",
    "normalised_output",
    "splits_output",
    "audit_output",
    "raw_rows",
    "normalised_rows",
    "split_rows",
    "status",
    "notes",
]

AUDIT_COLUMNS = [
    "recoverable_offsets",
    "archives_created",
    "archives_already_present",
    "archives_failed",
    "raw_rows_recovered",
    "normalised_rows_recovered",
    "split_rows_recovered",
    "final_status",
]


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


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


def batch_file(offset: str, kind: str) -> Path:
    return BATCH_DIR / f"batch_{int(offset):04d}_{kind}.csv"


def row_count(path: Path) -> int:
    return len(read_csv(path))


def live_offset() -> str:
    rows = read_csv(LIVE_AUDIT)
    return clean(rows[0].get("offset")) if rows else ""


def recoverable_offsets() -> list[str]:
    offsets: list[str] = []
    for row in read_csv(RECOVERY_AUDIT):
        if clean(row.get("can_reconstruct")).upper() == "TRUE":
            offsets.append(clean(row.get("offset")))
    return offsets


def copy_if_needed(source: Path, target: Path) -> str:
    if target.exists() and target.stat().st_size > 0:
        return "ALREADY_PRESENT"
    if not source.exists() or source.stat().st_size == 0:
        return "SOURCE_MISSING"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return "CREATED"


def write_tmp_json_archive(offset: str) -> tuple[str, str]:
    if not TMP_OUTPUT.exists():
        return "TMP_MISSING", "No temp JSON output exists."
    if offset != live_offset():
        return "TMP_OFFSET_MISMATCH", "Temp JSON can only be safely tied to the current live audit offset."
    try:
        payload = json.loads(TMP_OUTPUT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return "TMP_PARSE_FAILED", str(exc)
    if not payload.get("normalisedRows"):
        return "TMP_NO_ROWS", "Temp JSON has no normalisedRows."

    def write_rows(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
        write_csv(path, rows, columns)

    raw_columns = list((payload.get("rawRows") or [{}])[0].keys()) if payload.get("rawRows") else []
    normalised_columns = list((payload.get("normalisedRows") or [{}])[0].keys()) if payload.get("normalisedRows") else []
    split_columns = list((payload.get("splitRows") or [{}])[0].keys()) if payload.get("splitRows") else []
    if raw_columns:
        write_rows(batch_file(offset, "raw"), payload.get("rawRows") or [], raw_columns)
    if normalised_columns:
        write_rows(batch_file(offset, "normalised"), payload.get("normalisedRows") or [], normalised_columns)
    if split_columns:
        write_rows(batch_file(offset, "splits"), payload.get("splitRows") or [], split_columns)
    copy_if_needed(LIVE_AUDIT, batch_file(offset, "audit"))
    return "CREATED_FROM_TMP_JSON", "Batch archive rebuilt from surviving temp JSON output."


def recover_offset(offset: str) -> dict[str, Any]:
    raw_target = batch_file(offset, "raw")
    normalised_target = batch_file(offset, "normalised")
    splits_target = batch_file(offset, "splits")
    audit_target = batch_file(offset, "audit")

    if all(path.exists() and path.stat().st_size > 0 for path in (raw_target, normalised_target, splits_target, audit_target)):
        action = "VERIFY_EXISTING_ARCHIVE"
        status = "RECOVERY_ALREADY_PRESENT"
        notes = "Full batch archive already exists."
    elif offset == live_offset():
        raw_result = copy_if_needed(LIVE_RAW, raw_target)
        normalised_result = copy_if_needed(LIVE_NORMALISED, normalised_target)
        splits_result = copy_if_needed(LIVE_SPLITS, splits_target)
        audit_result = copy_if_needed(LIVE_AUDIT, audit_target)
        if "SOURCE_MISSING" in {raw_result, normalised_result, splits_result, audit_result}:
            tmp_status, tmp_notes = write_tmp_json_archive(offset)
            action = tmp_status
            notes = tmp_notes
        else:
            action = "COPY_FROM_LIVE_SNAPSHOT"
            notes = "Batch archive rebuilt from surviving live snapshot files."
        status = "RECOVERY_WRITTEN" if all(path.exists() and path.stat().st_size > 0 for path in (raw_target, normalised_target, splits_target, audit_target)) else "RECOVERY_FAILED"
    else:
        action = "NO_SOURCE_AVAILABLE"
        status = "RECOVERY_FAILED"
        notes = "No offset-specific archive, live snapshot, or temp JSON exists for this batch."

    return {
        "offset": offset,
        "recovery_action": action,
        "raw_output": str(raw_target),
        "normalised_output": str(normalised_target),
        "splits_output": str(splits_target),
        "audit_output": str(audit_target),
        "raw_rows": row_count(raw_target),
        "normalised_rows": row_count(normalised_target),
        "split_rows": row_count(splits_target),
        "status": status,
        "notes": notes,
    }


def main() -> None:
    offsets = recoverable_offsets()
    detail = [recover_offset(offset) for offset in offsets]
    created = [row for row in detail if clean(row.get("status")) == "RECOVERY_WRITTEN"]
    present = [row for row in detail if clean(row.get("status")) == "RECOVERY_ALREADY_PRESENT"]
    failed = [row for row in detail if clean(row.get("status")) == "RECOVERY_FAILED"]
    final_status = "NO_RECOVERABLE_BATCHES"
    if failed:
        final_status = "BATCH_RECOVERY_PARTIAL"
    elif detail:
        final_status = "BATCH_RECOVERY_READY"

    audit = [
        {
            "recoverable_offsets": ";".join(offsets),
            "archives_created": len(created),
            "archives_already_present": len(present),
            "archives_failed": len(failed),
            "raw_rows_recovered": sum(int(row.get("raw_rows") or 0) for row in detail),
            "normalised_rows_recovered": sum(int(row.get("normalised_rows") or 0) for row in detail),
            "split_rows_recovered": sum(int(row.get("split_rows") or 0) for row in detail),
            "final_status": final_status,
        }
    ]
    write_csv(OUT, detail, DETAIL_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    row = audit[0]
    print("Racing.com historical batch recovery V1 complete")
    print(f"recoverable_offsets={row['recoverable_offsets']}")
    print(f"archives_created={row['archives_created']}")
    print(f"archives_already_present={row['archives_already_present']}")
    print(f"archives_failed={row['archives_failed']}")
    print(f"normalised_rows_recovered={row['normalised_rows_recovered']}")
    print(f"final_status={row['final_status']}")


if __name__ == "__main__":
    main()
