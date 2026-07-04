from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUTS = ROOT / "outputs"

BATCH_DIR = DATA / "racingcom_rendered_speed_data_batches"
LIVE_RAW = DATA / "racingcom_rendered_speed_data_raw_v1.csv"
LIVE_NORMALISED = DATA / "racingcom_rendered_speed_data_normalised_v1.csv"
LIVE_SPLITS = DATA / "racingcom_rendered_speed_data_splits_v1.csv"
LIVE_AUDIT = DATA / "racingcom_rendered_speed_data_harvester_v1_audit.csv"
WAREHOUSE_V1 = DATA / "racingcom_sectional_warehouse_v1.csv"
WAREHOUSE_V2 = DATA / "racingcom_sectional_warehouse_v2.csv"
TMP_OUTPUT = OUTPUTS / "tmp" / "build_racingcom_rendered_speed_data_harvester_v1_output.json"

OUT = DATA / "racingcom_batch_recovery_v1.csv"
AUDIT_OUT = DATA / "racingcom_batch_recovery_v1_audit.csv"

EXPECTED_OFFSETS = ("0", "250", "500", "750", "1000")
REPORTED_BATCH_UNIQUE_RACES = {
    "0": 209,
    "250": 224,
    "500": 220,
    "750": 210,
    "1000": 196,
}
REPORTED_BATCH_UNIQUE_HORSES = {
    "0": 1695,
}
REPORTED_BATCH_ROWS = {
    "0": 2354,
}

DETAIL_COLUMNS = [
    "offset",
    "recovery_status",
    "can_reconstruct",
    "evidence_sources",
    "raw_file_found",
    "normalised_file_found",
    "splits_file_found",
    "audit_file_found",
    "manifest_found",
    "warehouse_evidence_found",
    "tmp_output_match_found",
    "recoverable_races",
    "recoverable_horses",
    "recoverable_rows",
    "lost_races_estimate",
    "lost_horses_estimate",
    "lost_rows_estimate",
    "notes",
]

AUDIT_COLUMNS = [
    "recoverable_batches",
    "recoverable_races",
    "recoverable_horses",
    "recoverable_rows",
    "lost_batches",
    "lost_races_estimate",
    "lost_horses_estimate",
    "lost_rows_estimate",
    "full_recovery_available",
    "partial_recovery_available",
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
    return len({race_key(row) for row in read_csv(path) if race_key(row).replace("|", "")})


def unique_horses(path: Path) -> int:
    return len({clean(row.get("horse_key")) for row in read_csv(path) if clean(row.get("horse_key"))})


def file_count(path: Path) -> int:
    return len(read_csv(path))


def batch_path(offset: str, kind: str) -> Path:
    return BATCH_DIR / f"batch_{int(offset):04d}_{kind}.csv"


def live_audit_offset() -> str:
    rows = read_csv(LIVE_AUDIT)
    return clean(rows[0].get("offset")) if rows else ""


def tmp_output_offsets() -> set[str]:
    if not TMP_OUTPUT.exists():
        return set()
    try:
        payload = json.loads(TMP_OUTPUT.read_text(encoding="utf-8"))
    except Exception:
        return set()
    urls = [clean(row.get("source_url")) for row in payload.get("pages", []) if clean(row.get("source_url"))]
    if not urls:
        return set()
    # Temp output does not store offset, so it can only be tied to the current live audit offset.
    return {live_audit_offset()} if live_audit_offset() else set()


def warehouse_has_offset_evidence(offset: str) -> bool:
    needle = f"batch_{int(offset):04d}_"
    for path in (WAREHOUSE_V1, WAREHOUSE_V2):
        if not path.exists():
            continue
        for row in read_csv(path):
            if needle in clean(row.get("source_file")):
                return True
    return False


def estimate_lost_horses(offset: str, races: int) -> int:
    if offset in REPORTED_BATCH_UNIQUE_HORSES:
        return REPORTED_BATCH_UNIQUE_HORSES[offset]
    # Conservative estimate from recoverable offset 0: unique horses per unique race.
    base_races = REPORTED_BATCH_UNIQUE_RACES.get("0") or 1
    base_horses = REPORTED_BATCH_UNIQUE_HORSES.get("0") or 0
    return round(races * (base_horses / base_races)) if base_horses else 0


def estimate_lost_rows(offset: str, races: int) -> int:
    if offset in REPORTED_BATCH_ROWS:
        return REPORTED_BATCH_ROWS[offset]
    base_races = REPORTED_BATCH_UNIQUE_RACES.get("0") or 1
    base_rows = REPORTED_BATCH_ROWS.get("0") or 0
    return round(races * (base_rows / base_races)) if base_rows else 0


def build_detail_rows() -> list[dict[str, Any]]:
    tmp_offsets = tmp_output_offsets()
    live_offset = live_audit_offset()
    rows: list[dict[str, Any]] = []

    for offset in EXPECTED_OFFSETS:
        raw = batch_path(offset, "raw")
        normalised = batch_path(offset, "normalised")
        splits = batch_path(offset, "splits")
        audit = batch_path(offset, "audit")
        raw_found = raw.exists()
        normalised_found = normalised.exists()
        splits_found = splits.exists()
        audit_found = audit.exists()
        warehouse_evidence = warehouse_has_offset_evidence(offset)
        tmp_match = offset in tmp_offsets
        live_match = offset == live_offset

        sources: list[str] = []
        if raw_found:
            sources.append(raw.name)
        if normalised_found:
            sources.append(normalised.name)
        if splits_found:
            sources.append(splits.name)
        if audit_found:
            sources.append(audit.name)
        if tmp_match:
            sources.append(TMP_OUTPUT.name)
        if live_match:
            sources.extend([LIVE_RAW.name, LIVE_NORMALISED.name, LIVE_SPLITS.name, LIVE_AUDIT.name])
        if warehouse_evidence:
            sources.append("warehouse_source_file_evidence")

        can_reconstruct = raw_found and normalised_found and splits_found and audit_found
        recoverable_races = unique_races(normalised) if normalised_found else (unique_races(LIVE_NORMALISED) if live_match else 0)
        recoverable_horses = unique_horses(normalised) if normalised_found else (unique_horses(LIVE_NORMALISED) if live_match else 0)
        recoverable_rows = file_count(normalised) if normalised_found else (file_count(LIVE_NORMALISED) if live_match else 0)
        reported_races = REPORTED_BATCH_UNIQUE_RACES.get(offset, 0)
        lost_races = 0 if can_reconstruct else reported_races
        lost_horses = 0 if can_reconstruct else estimate_lost_horses(offset, reported_races)
        lost_rows = 0 if can_reconstruct else estimate_lost_rows(offset, reported_races)

        status = "RECOVERABLE_FULL_BATCH" if can_reconstruct else "LOST_NO_FILE_LEVEL_RECOVERY"
        notes = "Raw, normalised, split, and audit files exist." if can_reconstruct else "No offset-specific raw/normalised/split/audit files found; warehouse/manifests cannot recreate batch-level files."

        rows.append(
            {
                "offset": offset,
                "recovery_status": status,
                "can_reconstruct": "TRUE" if can_reconstruct else "FALSE",
                "evidence_sources": ";".join(dict.fromkeys(sources)),
                "raw_file_found": "TRUE" if raw_found else "FALSE",
                "normalised_file_found": "TRUE" if normalised_found else "FALSE",
                "splits_file_found": "TRUE" if splits_found else "FALSE",
                "audit_file_found": "TRUE" if audit_found else "FALSE",
                "manifest_found": "FALSE",
                "warehouse_evidence_found": "TRUE" if warehouse_evidence else "FALSE",
                "tmp_output_match_found": "TRUE" if tmp_match else "FALSE",
                "recoverable_races": recoverable_races if can_reconstruct else 0,
                "recoverable_horses": recoverable_horses if can_reconstruct else 0,
                "recoverable_rows": recoverable_rows if can_reconstruct else 0,
                "lost_races_estimate": lost_races,
                "lost_horses_estimate": lost_horses,
                "lost_rows_estimate": lost_rows,
                "notes": notes,
            }
        )

    return rows


def build_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recoverable = [row for row in rows if clean(row.get("can_reconstruct")) == "TRUE"]
    lost = [row for row in rows if clean(row.get("can_reconstruct")) != "TRUE"]
    recoverable_batches = len(recoverable)
    lost_batches = len(lost)
    final_status = "NO_RECOVERY_AVAILABLE"
    if recoverable_batches == len(rows):
        final_status = "FULL_RECOVERY_AVAILABLE"
    elif recoverable_batches:
        final_status = "PARTIAL_RECOVERY_AVAILABLE"

    return [
        {
            "recoverable_batches": recoverable_batches,
            "recoverable_races": sum(int(row.get("recoverable_races") or 0) for row in recoverable),
            "recoverable_horses": sum(int(row.get("recoverable_horses") or 0) for row in recoverable),
            "recoverable_rows": sum(int(row.get("recoverable_rows") or 0) for row in recoverable),
            "lost_batches": lost_batches,
            "lost_races_estimate": sum(int(row.get("lost_races_estimate") or 0) for row in lost),
            "lost_horses_estimate": sum(int(row.get("lost_horses_estimate") or 0) for row in lost),
            "lost_rows_estimate": sum(int(row.get("lost_rows_estimate") or 0) for row in lost),
            "full_recovery_available": "TRUE" if recoverable_batches == len(rows) else "FALSE",
            "partial_recovery_available": "TRUE" if recoverable_batches and recoverable_batches < len(rows) else "FALSE",
            "final_status": final_status,
        }
    ]


def main() -> None:
    detail = build_detail_rows()
    audit = build_audit(detail)
    write_csv(OUT, detail, DETAIL_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    summary = audit[0]
    print("Racing.com batch recovery audit V1 built")
    print(f"recoverable_batches={summary['recoverable_batches']}")
    print(f"recoverable_races={summary['recoverable_races']}")
    print(f"recoverable_horses={summary['recoverable_horses']}")
    print(f"recoverable_rows={summary['recoverable_rows']}")
    print(f"lost_batches={summary['lost_batches']}")
    print(f"lost_races_estimate={summary['lost_races_estimate']}")
    print(f"lost_horses_estimate={summary['lost_horses_estimate']}")
    print(f"lost_rows_estimate={summary['lost_rows_estimate']}")
    print(f"final_status={summary['final_status']}")


if __name__ == "__main__":
    main()
