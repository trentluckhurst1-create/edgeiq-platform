from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
OBSERVATIONS = DATA / "edgeiq_results_elapsed_time_observations_v1.csv"
STANDARDS = DATA / "edgeiq_results_standard_times_v1.csv"
OUT = DATA / "edgeiq_results_lengths_v_standard_v1_CANDIDATE.csv"
SUMMARY = DOCS / "edgeiq_results_lengths_v_standard_candidate_summary_v1.json"
REPORT = DOCS / "edgeiq_results_lengths_v_standard_candidate_report_v1.md"

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
    "seconds_per_length",
    "lengths_vs_standard",
    "conversion_method",
    "conversion_version",
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


def group_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        clean(row.get("track")).upper().replace(" ", ""),
        clean(row.get("race_distance_metres")),
        clean(row.get("segment_start_metres")),
        clean(row.get("segment_end_metres")),
        clean(row.get("segment_distance_metres")),
    )


def benchmark_group_id(row: dict[str, str]) -> str:
    key = "|".join(group_key(row))
    return "RSTG1-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16].upper()


def main() -> int:
    observations = [row for row in read_csv(OBSERVATIONS) if clean(row.get("eligibility_status")) == "ELIGIBLE"]
    standards = {clean(row.get("benchmark_group_id")): row for row in read_csv(STANDARDS)}
    output: list[dict[str, object]] = []
    for row in observations:
        group_id = benchmark_group_id(row)
        standard = standards.get(group_id)
        if not standard:
            continue
        actual = clean(row.get("elapsed_time_seconds"))
        standard_elapsed = clean(standard.get("standard_elapsed_seconds"))
        try:
            time_difference = float(actual) - float(standard_elapsed)
            time_diff_text = f"{time_difference:.4f}"
        except Exception:
            time_diff_text = ""
        output.append({
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
            "actual_elapsed_seconds": actual,
            "standard_elapsed_seconds": standard_elapsed,
            "time_difference_seconds": time_diff_text,
            "seconds_per_length": "",
            "lengths_vs_standard": "",
            "conversion_method": "NO_GOVERNED_METHOD_SELECTED",
            "conversion_version": "EDGEIQ_SECONDS_PER_LENGTH_METHOD_DECISION_V1",
            "source_hash": clean(row.get("source_payload_sha256")),
            "audit_status": "BLOCKED_MISSING_GOVERNED_SECONDS_PER_LENGTH_METHOD",
        })
    write_csv(OUT, output, FIELDS)
    summary = {
        "input_elapsed_observations": len(observations),
        "standard_time_matched_observations": len(output),
        "converted_observations": 0,
        "blocked_observations": len(output),
        "races": len({row["canonical_race_id"] for row in output}),
        "runners": len({(row["canonical_race_id"], row["canonical_runner_id"]) for row in output}),
        "benchmark_groups": len({row["benchmark_group_id"] for row in output}),
        "status": "LENGTHS_V_STANDARD_BLOCKED_BY_LENGTH_METHOD",
        "deterministic_hash": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Lengths v Standard Candidate V1\n\n"
        f"Status: `{summary['status']}`\n\n"
        f"Standard-time matched observations: `{summary['standard_time_matched_observations']}`\n\n"
        f"Converted observations: `{summary['converted_observations']}`\n\n"
        "The candidate preserves actual and standard elapsed seconds, but does not calculate lengths because no governed seconds-per-length method exists.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
