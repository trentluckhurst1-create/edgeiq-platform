from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from datetime import datetime, timezone

from edgeiq_racing_com_public_adapter_v1 import FIELDS_SECTIONAL
from edgeiq_racing_com_public_common_v1 import ROOT, PROCESSED, sha_bytes, read_csv, write_csv, write_json, now

OP_ROOT = ROOT / "data" / "operational" / "racing-com-visible-v1"
VISIBLE_INPUT = OP_ROOT / "normalised_visible_sectionals_v1.csv"
VISIBLE_PROCESSED = PROCESSED / "visible_runner_sectional_fact_v1.csv"
TARGET = PROCESSED / "runner_sectional_fact.csv"


def map_to_target(row: dict) -> dict:
    source_url = row.get("source_url", "")
    key_source = "|".join([source_url, row.get("runner_name", ""), row.get("section_start_metres", ""), row.get("section_end_metres", "")])
    return {
        "source_provider": "RACING.COM",
        "source_endpoint": "visible public page rendered table",
        "source_resource_url_hash": sha_bytes(source_url.encode("utf-8", "ignore")),
        "source_meeting_id": row.get("meeting_code", ""),
        "source_race_id": "VISIBLE|" + row.get("meeting_date", "") + "|" + row.get("venue", "") + "|R" + row.get("race_number", ""),
        "source_runner_id": sha_bytes((row.get("runner_name", "") + "|" + row.get("saddlecloth_number", "")).encode("utf-8", "ignore"))[:16],
        "meeting_date": row.get("meeting_date", ""),
        "venue": row.get("venue", ""),
        "race_number": row.get("race_number", ""),
        "race_distance_metres": row.get("race_distance_metres", ""),
        "runner_name": row.get("runner_name", ""),
        "saddlecloth_number": row.get("saddlecloth_number", ""),
        "finish_position": row.get("finish_position", ""),
        "section_start_metres": row.get("section_start_metres", ""),
        "section_end_metres": row.get("section_end_metres", ""),
        "section_distance_metres": row.get("section_distance_metres", ""),
        "section_time_seconds": row.get("section_time_seconds", ""),
        "section_rank": row.get("section_rank", ""),
        "cumulative_time_seconds": row.get("cumulative_time_seconds", ""),
        "distance_from_finish_metres": row.get("section_end_metres", ""),
        "timing_unit_original": row.get("timing_unit_original", ""),
        "timing_unit_normalised": row.get("timing_unit_normalised", ""),
        "source_retrieved_at": row.get("source_retrieved_at", ""),
        "source_published_at": "",
        "response_hash": sha_bytes(key_source.encode("utf-8", "ignore")),
        "provenance_status": "VISIBLE_PUBLIC_PAGE_GOVERNED",
        "identity_status": "PASS" if row.get("identity_status") == "MATCHED" else "MISSING_IDENTITY",
        "validation_status": "PASS" if row.get("validation_status") == "PASS" and row.get("unit_semantics_status") == "PROVEN" else "REJECTED",
    }


def row_key(row: dict) -> tuple:
    return (row.get("source_race_id", ""), row.get("source_runner_id", ""), row.get("section_start_metres", ""), row.get("section_end_metres", ""), row.get("section_time_seconds", ""))


def import_visible(promote: bool = False) -> dict:
    source = read_csv(VISIBLE_INPUT)
    valid = [row for row in source if row.get("identity_status") == "MATCHED" and row.get("unit_semantics_status") == "PROVEN" and row.get("validation_status") == "PASS"]
    mapped = [map_to_target(row) for row in valid]
    write_csv(VISIBLE_PROCESSED, mapped, FIELDS_SECTIONAL)
    before = read_csv(TARGET)
    promoted = 0
    duplicate = 0
    if promote and mapped:
        seen = {row_key(row) for row in before}
        appended = []
        for row in mapped:
            key = row_key(row)
            if key in seen:
                duplicate += 1
                continue
            seen.add(key)
            appended.append(row)
        if appended:
            write_csv(TARGET, before + appended, FIELDS_SECTIONAL)
            promoted = len(appended)
    summary = {"source_rows": len(source), "valid_rows": len(valid), "processed_preview_rows": len(mapped), "promote_requested": bool(promote), "canonical_rows_before": len(before), "canonical_rows_promoted": promoted, "duplicate_rows_ignored": duplicate, "canonical_rows_after": len(read_csv(TARGET)), "status": "PROMOTED" if promoted else ("READY_FOR_IMPORT" if mapped else "NO_VALID_VISIBLE_SECTIONALS")}
    write_json(OP_ROOT / "visible_import_summary_v1.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    summary = import_visible(promote=args.promote)
    return 0 if summary.get("status") in {"PROMOTED", "READY_FOR_IMPORT", "NO_VALID_VISIBLE_SECTIONALS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
