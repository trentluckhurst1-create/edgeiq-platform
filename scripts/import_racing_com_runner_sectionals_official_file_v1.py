from __future__ import annotations

import argparse
import json
from pathlib import Path

from edgeiq_racing_com_public_adapter_v1 import FIELDS_SECTIONAL
from edgeiq_racing_com_public_common_v1 import *

COMPLETION = DOC / "completion"
OUTDIR = COMPLETION / "official-import"


def iter_json_horses(obj: object) -> list[dict]:
    if isinstance(obj, dict):
        data = obj.get("data") if isinstance(obj.get("data"), dict) else {}
        callback = data.get("sectionaltimes_callback") if isinstance(data, dict) else None
        if isinstance(callback, dict) and isinstance(callback.get("Horses"), list):
            return callback.get("Horses") or []
        if isinstance(obj.get("Horses"), list):
            return obj.get("Horses") or []
    return []


def normalise_json(path: Path) -> list[dict]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = []
    for horse in iter_json_horses(obj):
        runner = str(horse.get("FullName") or horse.get("horseName") or "").strip()
        runner_id = str(horse.get("id") or "").strip()
        saddle = str(horse.get("SaddleNumber") or horse.get("saddleNumber") or "").strip()
        finish = str(horse.get("FinalPosition") or horse.get("finishPosition") or "").strip()
        for split in horse.get("SplitTimes") or horse.get("splitTimes") or []:
            label = str(split.get("Distance") or split.get("distance") or "").strip()
            start, end, dist = split_bounds(label)
            seconds = parse_time_seconds(split.get("Time") or split.get("time"))
            rows.append({"source_provider": "RACING.COM_OFFICIAL_IMPORT", "source_endpoint": "operator supplied official JSON export", "source_resource_url_hash": sha_file(path), "source_meeting_id": "", "source_race_id": "", "source_runner_id": runner_id, "meeting_date": "", "venue": "", "race_number": "", "race_distance_metres": "", "runner_name": runner, "saddlecloth_number": saddle, "finish_position": finish, "section_start_metres": start, "section_end_metres": end, "section_distance_metres": dist, "section_time_seconds": "" if seconds is None else seconds, "section_rank": str(split.get("Position") or split.get("position") or "").strip(), "cumulative_time_seconds": "", "distance_from_finish_metres": end, "timing_unit_original": "official export metres-from-finish split label", "timing_unit_normalised": "section_start_metres_to_section_end_metres_from_finish", "source_retrieved_at": now(), "source_published_at": "", "response_hash": sha_file(path), "provenance_status": "OFFICIAL_OPERATOR_IMPORT_NOT_CANONICAL", "identity_status": "PASS" if runner else "MISSING_IDENTITY", "validation_status": "PASS" if runner and start and end and seconds and seconds > 0 else "REJECTED_INCOMPLETE_OR_AMBIGUOUS"})
    return rows


def normalise_csv(path: Path) -> list[dict]:
    rows = []
    for row in read_csv(path):
        label = first(row, ["Distance", "distance", "split_distance", "section"])
        start, end, dist = split_bounds(label)
        seconds = parse_time_seconds(first(row, ["Time", "time", "split_time_seconds", "section_time_seconds"]))
        runner = first(row, ["FullName", "horseName", "runner_name", "horse"])
        rows.append({"source_provider": "RACING.COM_OFFICIAL_IMPORT", "source_endpoint": "operator supplied official CSV export", "source_resource_url_hash": sha_file(path), "source_meeting_id": first(row, ["meetCode", "meeting_code"]), "source_race_id": first(row, ["race_id", "race_key"]), "source_runner_id": first(row, ["id", "runner_id"]), "meeting_date": first(row, ["race_date", "meeting_date"]), "venue": first(row, ["track", "venue"]), "race_number": first(row, ["race_number", "race_no"]), "race_distance_metres": first(row, ["race_distance_metres", "distance_metres"]), "runner_name": runner, "saddlecloth_number": first(row, ["SaddleNumber", "saddleNumber", "saddlecloth_number"]), "finish_position": first(row, ["FinalPosition", "finish_position"]), "section_start_metres": start, "section_end_metres": end, "section_distance_metres": dist, "section_time_seconds": "" if seconds is None else seconds, "section_rank": first(row, ["Position", "position", "section_rank"]), "cumulative_time_seconds": first(row, ["cumulative_time_seconds"]), "distance_from_finish_metres": end, "timing_unit_original": "official export metres-from-finish split label", "timing_unit_normalised": "section_start_metres_to_section_end_metres_from_finish", "source_retrieved_at": now(), "source_published_at": "", "response_hash": sha_file(path), "provenance_status": "OFFICIAL_OPERATOR_IMPORT_NOT_CANONICAL", "identity_status": "PASS" if runner else "MISSING_IDENTITY", "validation_status": "PASS" if runner and start and end and seconds and seconds > 0 else "REJECTED_INCOMPLETE_OR_AMBIGUOUS"})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", default=str(DOC / "fixtures" / "public_200_meeting_with_sectionals.json"))
    parser.add_argument("--output-root", default=str(OUTDIR))
    args = parser.parse_args()
    ensure()
    outdir = Path(args.output_root)
    outdir.mkdir(parents=True, exist_ok=True)
    source = Path(args.input_file)
    if not source.exists():
        summary = {"status": "OFFICIAL_IMPORT_INPUT_MISSING", "input_file": str(source), "rows": 0, "valid_rows": 0, "canonical_rows_promoted": 0}
        write_json(outdir / "official_import_summary.json", summary)
        print(json.dumps(summary, indent=2))
        return 2
    rows = normalise_csv(source) if source.suffix.lower() == ".csv" else normalise_json(source)
    valid = [row for row in rows if row["validation_status"] == "PASS"]
    write_csv(outdir / "official_runner_sectional_fact_preview.csv", rows, FIELDS_SECTIONAL)
    input_name = str(source.relative_to(ROOT)) if source.resolve().is_relative_to(ROOT.resolve()) else str(source)
    summary = {"status": "PASS_OFFICIAL_IMPORT_READY" if valid else "BLOCKED_OFFICIAL_IMPORT_SCHEMA", "input_file": input_name, "rows": len(rows), "valid_rows": len(valid), "canonical_rows_promoted": 0, "canonical_admission": "NO_PREVIEW_ONLY"}
    write_json(outdir / "official_import_summary.json", summary)
    report = f"""# Racing.com Official Sectionals Import Path

Status: `{summary['status']}`

Rows parsed: {len(rows)}

Valid rows: {len(valid)}

This fallback validates and normalises official operator-supplied files only. It does not promote rows canonically.
"""
    write_text(outdir / "official_import_report.md", report)
    print(json.dumps(summary, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
