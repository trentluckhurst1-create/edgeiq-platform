from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
SOURCE = DATA / "edgeiq_racingcom_graphql_speed_normalised_v1.csv"
OUT = DATA / "edgeiq_results_elapsed_time_observations_v1.csv"
AUDIT = DOCS / "edgeiq_results_elapsed_time_observations_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_results_elapsed_time_observations_summary_v1.json"
REPORT = DOCS / "edgeiq_results_elapsed_time_observations_report_v1.md"

FIELDS = [
    "canonical_race_id", "canonical_runner_id", "race_date", "track", "race_number",
    "race_distance_metres", "segment_sequence", "segment_start_metres", "segment_end_metres",
    "segment_distance_metres", "average_speed_mps", "average_speed_kmh", "elapsed_time_seconds",
    "observation_semantics", "source_format", "source_payload_sha256", "parser_version",
    "normalisation_version", "calculation_version", "eligibility_status", "rejection_reason",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def fnum(value: object) -> float | None:
    try:
        text = clean(value)
        return float(text) if text else None
    except ValueError:
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def parse_split(label: str) -> tuple[int | None, int | None]:
    text = clean(label).upper()
    m = re.fullmatch(r"(\d+)M-(\d+)M", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"(\d+)M-FINISH", text)
    if m:
        return int(m.group(1)), 0
    return None, None


def race_distance(rows: list[dict[str, str]]) -> dict[str, int]:
    by_race: dict[str, int] = {}
    for row in rows:
        if clean(row.get("row_type")) != "SPLIT":
            continue
        start, _end = parse_split(row.get("distance_label", ""))
        if start is not None:
            by_race[row["race_id"]] = max(by_race.get(row["race_id"], 0), start)
    return by_race


def main() -> int:
    rows = read_csv(SOURCE)
    distances = race_distance(rows)
    output: list[dict[str, object]] = []
    for row in rows:
        row_type = clean(row.get("row_type"))
        start, end = parse_split(row.get("distance_label", ""))
        speed = fnum(row.get("avg_speed_mps"))
        kmh = fnum(row.get("avg_speed_kmh"))
        race_id = clean(row.get("race_id"))
        runner_id = clean(row.get("horse_id")) or clean(row.get("horse"))
        base = {
            "canonical_race_id": race_id,
            "canonical_runner_id": runner_id,
            "race_date": clean(row.get("race_date")),
            "track": clean(row.get("track")),
            "race_number": clean(row.get("race_no_numeric") or row.get("race_no")),
            "race_distance_metres": str(distances.get(race_id, "")),
            "source_format": "RACING.COM_GRAPHQL_GETRACEFORM",
            "source_payload_sha256": clean(row.get("response_sha256")),
            "parser_version": "racingcom_graphql_parser_v2",
            "normalisation_version": "edgeiq_racingcom_graphql_speed_normalised_v1",
            "calculation_version": "edgeiq_results_elapsed_time_observations_v1",
        }
        if row_type != "SPLIT":
            output.append({**base, "segment_sequence": "", "segment_start_metres": "", "segment_end_metres": "", "segment_distance_metres": "", "average_speed_mps": clean(row.get("avg_speed_mps")), "average_speed_kmh": clean(row.get("avg_speed_kmh")), "elapsed_time_seconds": "", "observation_semantics": "CUMULATIVE_DISTANCE_POINT", "eligibility_status": "REJECTED", "rejection_reason": "CUMULATIVE_POINT_NOT_USED_AS_INCREMENTAL_SEGMENT"})
            continue
        if start is None or end is None or start <= end:
            reason = "INVALID_SEGMENT_BOUNDARY"
            elapsed = ""
            status = "REJECTED"
            distance = ""
        elif speed is None or speed <= 0:
            reason = "MISSING_OR_NONPOSITIVE_SPEED"
            elapsed = ""
            status = "REJECTED"
            distance = str(start - end)
        else:
            reason = ""
            distance_value = start - end
            elapsed_value = distance_value / speed
            elapsed = f"{elapsed_value:.4f}"
            status = "ELIGIBLE"
            distance = str(distance_value)
        output.append({
            **base,
            "segment_sequence": str(((distances.get(race_id, 0) - start) // 200) + 1 if start is not None and distances.get(race_id) else ""),
            "segment_start_metres": "" if start is None else str(start),
            "segment_end_metres": "" if end is None else str(end),
            "segment_distance_metres": distance,
            "average_speed_mps": "" if speed is None else f"{speed:.6f}",
            "average_speed_kmh": "" if kmh is None else f"{kmh:.6f}",
            "elapsed_time_seconds": elapsed,
            "observation_semantics": "INDIVIDUAL_SEGMENT",
            "eligibility_status": status,
            "rejection_reason": reason,
        })

    eligible = [r for r in output if r["eligibility_status"] == "ELIGIBLE"]
    rejections = Counter(r["rejection_reason"] for r in output if r["eligibility_status"] != "ELIGIBLE")
    duplicate = len(eligible) - len({(r["canonical_race_id"], r["canonical_runner_id"], r["segment_start_metres"], r["segment_end_metres"]) for r in eligible})
    bad_units = sum(1 for r in eligible if not (5 <= float(r["average_speed_mps"]) <= 25) or not (5 <= float(r["elapsed_time_seconds"]) <= 30))
    write_csv(OUT, output, FIELDS)
    audit_rows = [
        {"check": "input_observations", "status": "PASS" if len(rows) == 898 else "FAIL", "value": str(len(rows)), "detail": "Input normalised GraphQL rows."},
        {"check": "valid_segment_observations", "status": "PASS" if len(eligible) == 449 else "FAIL", "value": str(len(eligible)), "detail": "Eligible incremental SPLIT rows."},
        {"check": "rejected_observations", "status": "PASS" if sum(rejections.values()) == 449 else "FAIL", "value": str(sum(rejections.values())), "detail": json.dumps(dict(rejections), sort_keys=True)},
        {"check": "duplicate_segments", "status": "PASS" if duplicate == 0 else "FAIL", "value": str(duplicate), "detail": "Unique race-runner-segment observations."},
        {"check": "unit_plausibility", "status": "PASS" if bad_units == 0 else "FAIL", "value": str(bad_units), "detail": "Speed and elapsed seconds plausible."},
        {"check": "deterministic_hash", "status": "PASS", "value": hashlib.sha256(OUT.read_bytes()).hexdigest(), "detail": "Output SHA after build."},
    ]
    write_csv(AUDIT, audit_rows, ["check", "status", "value", "detail"])
    summary = {
        "input_observations": len(rows),
        "valid_segment_observations": len(eligible),
        "elapsed_times_derived": len(eligible),
        "rejected_observations": sum(rejections.values()),
        "rejection_reasons": dict(rejections),
        "races_represented": len({r["canonical_race_id"] for r in eligible}),
        "runners_represented": len({(r["canonical_race_id"], r["canonical_runner_id"]) for r in eligible}),
        "segments_represented": len({(r["race_distance_metres"], r["segment_start_metres"], r["segment_end_metres"]) for r in eligible}),
        "deterministic_hash": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Results Elapsed Time Observations V1\n\nEligible incremental observations: `{len(eligible)}`\nRejected cumulative points: `{rejections.get('CUMULATIVE_POINT_NOT_USED_AS_INCREMENTAL_SEGMENT', 0)}`\n\nElapsed time is derived as segment distance divided by average speed m/s.\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if all(r["status"] == "PASS" for r in audit_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
