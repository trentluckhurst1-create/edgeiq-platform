from __future__ import annotations

import csv
import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
BASE_COMMIT = "5ba1197"

RESTORE_ONLY = [
    "edgeiq_horse_performance_aggregate_fact_v1.csv",
    "edgeiq_horse_performance_rating_fact_v1.csv",
    "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
    "edgeiq_race_entry_performance_context_fact_v1.csv",
    "edgeiq_race_entry_context_eligibility_fact_v1.csv",
    "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",
    "edgeiq_race_entry_context_adjustment_fact_v1.csv",
    "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv",
    "edgeiq_race_entry_projected_performance_fact_v1.csv",
    "edgeiq_race_entry_epi_component_fact_v1.csv",
    "edgeiq_race_entry_epi_fact_v1.csv",
]

MERGE_CURRENT = {
    "edgeiq_performance_normalisation_fact_v1.csv": "performance_normalisation_id",
    "edgeiq_performance_rating_base_fact_v1.csv": "performance_rating_base_id",
    "edgeiq_horse_performance_observation_fact_v1.csv": "horse_performance_observation_id",
}


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_csv_path(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def read_csv_from_git(filename: str) -> tuple[list[str], list[dict[str, str]]]:
    payload = subprocess.check_output(
        ["git", "show", f"{BASE_COMMIT}:public/data/{filename}"],
        cwd=ROOT,
    ).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(payload))
    return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def is_current(row: dict[str, str]) -> bool:
    return text(row.get("race_date") or row.get("performance_date")) >= "2026-07-20"


def main() -> None:
    report_rows: list[dict[str, Any]] = []
    for filename, key_field in MERGE_CURRENT.items():
        path = DATA / filename
        fields_base, base_rows = read_csv_from_git(filename)
        fields_current, current_rows = read_csv_path(path)
        fieldnames = list(fields_base)
        for field in fields_current:
            if field not in fieldnames:
                fieldnames.append(field)
        by_key = {text(row.get(key_field)): row for row in base_rows if text(row.get(key_field))}
        added = 0
        for row in current_rows:
            if not is_current(row):
                continue
            key = text(row.get(key_field))
            if key and key not in by_key:
                by_key[key] = row
                added += 1
        merged = list(by_key.values())
        merged.sort(key=lambda r: (text(r.get("race_date") or r.get("performance_date")), text(r.get(key_field))))
        write_csv(path, fieldnames, merged)
        report_rows.append({"file": filename, "action": "RESTORE_BASE_AND_APPEND_CURRENT_ROWS", "base_rows": len(base_rows), "current_rows_added": added, "output_rows": len(merged)})

    for filename in RESTORE_ONLY:
        path = DATA / filename
        fields, rows = read_csv_from_git(filename)
        write_csv(path, fields, rows)
        report_rows.append({"file": filename, "action": "RESTORE_BASELINE_PUBLICATION", "base_rows": len(rows), "current_rows_added": 0, "output_rows": len(rows)})

    report_path = ROOT / "docs" / "performance-intelligence-context-parameter-methodology-v1" / "EDGEIQ_HISTORICAL_PUBLICATION_REPAIR_AFTER_CURRENT_REFRESH_V1.csv"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(report_path, ["file", "action", "base_rows", "current_rows_added", "output_rows"], report_rows)
    for row in report_rows:
        print(f"{row['file']} {row['action']} output_rows={row['output_rows']} current_rows_added={row['current_rows_added']}")


if __name__ == "__main__":
    main()
