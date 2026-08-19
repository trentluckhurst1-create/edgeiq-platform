from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, getcontext
from pathlib import Path

from edgeiq_length_conversion_method_v1 import resolve_length_conversion


getcontext().prec = 28

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
OBSERVATIONS = DATA / "edgeiq_results_elapsed_time_observations_v1.csv"
STANDARD_TIMES = DATA / "edgeiq_results_standard_times_v1.csv"
CANDIDATE = DATA / "edgeiq_results_lengths_v_standard_v1_CANDIDATE.csv"
FINAL = DATA / "edgeiq_results_lengths_v_standard_v1.csv"
BACKUP = DATA / "edgeiq_results_lengths_v_standard_v1_PRE_METHOD_V1_BACKUP.csv"
SUMMARY = DOCS / "edgeiq_results_lengths_v_standard_build_summary_v1.json"
REPORT = DOCS / "edgeiq_results_lengths_v_standard_build_report_v1.md"

FIELDS = [
    "benchmark_group_id",
    "canonical_race_id",
    "canonical_runner_id",
    "race_date",
    "track",
    "race_number",
    "race_distance_metres",
    "segment_sequence",
    "segment_start_metres",
    "segment_end_metres",
    "segment_distance_metres",
    "actual_elapsed_seconds",
    "standard_elapsed_seconds",
    "time_difference_seconds",
    "surface",
    "track_condition_number",
    "track_condition_group",
    "lengths_per_second",
    "seconds_per_length",
    "lengths_vs_standard",
    "conversion_method",
    "conversion_version",
    "conversion_status",
    "conversion_reason",
    "source_hash",
    "audit_status",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def benchmark_group_id(row: dict[str, str]) -> str:
    key = "|".join([
        clean(row.get("track")).upper().replace(" ", ""),
        clean(row.get("race_distance_metres")),
        clean(row.get("segment_start_metres")),
        clean(row.get("segment_end_metres")),
        clean(row.get("segment_distance_metres")),
    ])
    return "RSTG1-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16].upper()


def infer_surface(row: dict[str, str]) -> str:
    for field in ["surface", "track_surface", "course_surface"]:
        if clean(row.get(field)):
            return clean(row.get(field)).upper()
    track = clean(row.get("track")).upper()
    if any(token in track for token in ["SYNTHETIC", "POLY", "TAPETA", "FIBRE", "FIBER"]):
        return "SYNTHETIC"
    return "TURF"


def infer_condition(row: dict[str, str], standard: dict[str, str]) -> str:
    for field in [
        "track_condition_number",
        "condition_number",
        "track_rating_number",
        "track_condition",
        "condition",
        "going",
    ]:
        if clean(row.get(field)):
            return clean(row.get(field))
        if clean(standard.get(field)):
            return clean(standard.get(field))
    return ""


def decimal_text(value: Decimal, places: str = "0.000000") -> str:
    return f"{value.quantize(Decimal(places))}"


def main() -> int:
    observations = [row for row in read_csv(OBSERVATIONS) if clean(row.get("eligibility_status")) == "ELIGIBLE"]
    standards = {clean(row.get("benchmark_group_id")): row for row in read_csv(STANDARD_TIMES)}
    output: list[dict[str, object]] = []
    for row in observations:
        group_id = benchmark_group_id(row)
        standard = standards.get(group_id)
        if not standard:
            continue
        actual = Decimal(clean(row.get("elapsed_time_seconds")))
        standard_elapsed = Decimal(clean(standard.get("standard_elapsed_seconds")))
        time_difference = standard_elapsed - actual
        surface = infer_surface(row)
        condition = infer_condition(row, standard)
        resolved = resolve_length_conversion(surface, condition)
        base = {
            "benchmark_group_id": group_id,
            "canonical_race_id": clean(row.get("canonical_race_id")),
            "canonical_runner_id": clean(row.get("canonical_runner_id")),
            "race_date": clean(row.get("race_date")),
            "track": clean(row.get("track")),
            "race_number": clean(row.get("race_number")),
            "race_distance_metres": clean(row.get("race_distance_metres")),
            "segment_sequence": clean(row.get("segment_sequence")),
            "segment_start_metres": clean(row.get("segment_start_metres")),
            "segment_end_metres": clean(row.get("segment_end_metres")),
            "segment_distance_metres": clean(row.get("segment_distance_metres")),
            "actual_elapsed_seconds": decimal_text(actual),
            "standard_elapsed_seconds": decimal_text(standard_elapsed),
            "time_difference_seconds": decimal_text(time_difference),
            "surface": surface,
            "track_condition_number": condition,
            "track_condition_group": resolved["track_condition_group"],
            "lengths_per_second": resolved["lengths_per_second"],
            "seconds_per_length": resolved["seconds_per_length"],
            "conversion_method": "EDGEIQ_GOING_DEPENDENT_LENGTHS_PER_SECOND_V1",
            "conversion_version": resolved["method_version"],
            "conversion_status": resolved["status"],
            "conversion_reason": resolved["reason"],
            "source_hash": clean(row.get("source_payload_sha256")),
        }
        if resolved["status"] == "AVAILABLE":
            lengths = time_difference * Decimal(resolved["lengths_per_second"])
            output.append({
                **base,
                "lengths_vs_standard": decimal_text(lengths),
                "audit_status": "CALCULATED",
            })
        else:
            output.append({
                **base,
                "lengths_vs_standard": "",
                "audit_status": resolved["status"],
            })
    write_csv(CANDIDATE, output, FIELDS)
    if FINAL.exists() and not BACKUP.exists():
        BACKUP.write_bytes(FINAL.read_bytes())
    FINAL.write_bytes(CANDIDATE.read_bytes())
    converted = [row for row in output if row["audit_status"] == "CALCULATED"]
    unsupported = [row for row in output if row["audit_status"] != "CALCULATED"]
    summary = {
        "matched_observations": len(output),
        "converted_observations": len(converted),
        "unsupported_observations": len(unsupported),
        "missing_condition_observations": sum(1 for row in unsupported if row["conversion_reason"] == "MISSING_TRACK_CONDITION_NUMBER"),
        "firm_conversions": sum(1 for row in converted if row["track_condition_group"] == "FIRM"),
        "good_conversions": sum(1 for row in converted if row["track_condition_group"] == "GOOD"),
        "soft_conversions": sum(1 for row in converted if row["track_condition_group"] == "SOFT"),
        "heavy_conversions": sum(1 for row in converted if row["track_condition_group"] == "HEAVY"),
        "candidate_hash": hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
        "final_hash": hashlib.sha256(FINAL.read_bytes()).hexdigest(),
        "status": "LENGTHS_V_STANDARD_PRODUCED_WITH_UNSUPPORTED_SCOPE_BLOCKS" if output else "NO_MATCHED_STANDARD_TIME_OBSERVATIONS",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Lengths v Standard Build V1\n\n"
        f"Status: `{summary['status']}`\n\n"
        f"Matched observations: `{summary['matched_observations']}`\n\n"
        f"Converted observations: `{summary['converted_observations']}`\n\n"
        f"Unsupported observations: `{summary['unsupported_observations']}`\n\n"
        "Rows outside the approved Turf condition scope are preserved and blocked, not converted.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
