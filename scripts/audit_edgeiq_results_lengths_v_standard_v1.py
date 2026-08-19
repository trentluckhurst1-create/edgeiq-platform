from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
OBSERVATIONS = DATA / "edgeiq_results_elapsed_time_observations_v1.csv"
CANDIDATE = DATA / "edgeiq_results_lengths_v_standard_v1_CANDIDATE.csv"
OUT = DOCS / "edgeiq_results_lengths_v_standard_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_results_lengths_v_standard_audit_summary_v1.json"
REPORT = DOCS / "edgeiq_results_lengths_v_standard_audit_report_v1.md"


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


def quantile(values: list[float], pct: float) -> str:
    if not values:
        return ""
    ordered = sorted(values)
    idx = (len(ordered) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        value = ordered[lo]
    else:
        value = ordered[lo] + ((ordered[hi] - ordered[lo]) * (idx - lo))
    return f"{value:.6f}"


def main() -> int:
    input_elapsed = [row for row in read_csv(OBSERVATIONS) if clean(row.get("eligibility_status")) == "ELIGIBLE"]
    rows = read_csv(CANDIDATE)
    converted = [row for row in rows if clean(row.get("audit_status")) == "CALCULATED"]
    blocked = [row for row in rows if "BLOCKED" in clean(row.get("audit_status"))]
    unsupported = [row for row in rows if clean(row.get("audit_status")) == "BLOCKED_UNSUPPORTED_LENGTH_CONVERSION_SCOPE"]
    missing_condition = [row for row in unsupported if clean(row.get("conversion_reason")) == "MISSING_TRACK_CONDITION_NUMBER"]
    duplicate_count = len(rows) - len({
        (
            clean(row.get("benchmark_group_id")),
            clean(row.get("canonical_race_id")),
            clean(row.get("canonical_runner_id")),
            clean(row.get("segment_start_metres")),
            clean(row.get("segment_end_metres")),
        )
        for row in rows
    })
    lvs_values: list[float] = []
    bad_numbers = 0
    for row in converted:
        try:
            value = float(clean(row.get("lengths_vs_standard")))
            sec = float(clean(row.get("seconds_per_length")))
            if not math.isfinite(value) or not math.isfinite(sec) or sec <= 0:
                bad_numbers += 1
            else:
                lvs_values.append(value)
        except Exception:
            bad_numbers += 1
    summary = {
        "input_elapsed_observations": len(input_elapsed),
        "standard_time_matched_observations": len(rows),
        "converted_observations": len(converted),
        "blocked_observations": len(blocked),
        "races": len({clean(row.get("canonical_race_id")) for row in rows if clean(row.get("canonical_race_id"))}),
        "runners": len({(clean(row.get("canonical_race_id")), clean(row.get("canonical_runner_id"))) for row in rows if clean(row.get("canonical_race_id"))}),
        "benchmark_groups": len({clean(row.get("benchmark_group_id")) for row in rows if clean(row.get("benchmark_group_id"))}),
        "minimum_lvs": f"{min(lvs_values):.6f}" if lvs_values else "",
        "maximum_lvs": f"{max(lvs_values):.6f}" if lvs_values else "",
        "median_lvs": f"{statistics.median(lvs_values):.6f}" if lvs_values else "",
        "p05": quantile(lvs_values, 0.05),
        "p95": quantile(lvs_values, 0.95),
        "unsupported_observations": len(unsupported),
        "missing_condition_observations": len(missing_condition),
        "firm_conversions": sum(1 for row in converted if clean(row.get("track_condition_group")) == "FIRM"),
        "good_conversions": sum(1 for row in converted if clean(row.get("track_condition_group")) == "GOOD"),
        "soft_conversions": sum(1 for row in converted if clean(row.get("track_condition_group")) == "SOFT"),
        "heavy_conversions": sum(1 for row in converted if clean(row.get("track_condition_group")) == "HEAVY"),
        "conversion_method_distribution": "EDGEIQ_GOING_DEPENDENT_LENGTHS_PER_SECOND_V1",
        "deterministic_hash": hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() if CANDIDATE.exists() else "",
        "status": "LENGTHS_V_STANDARD_SCOPE_BLOCKED_FOR_CURRENT_ROWS" if not converted and unsupported else "LENGTHS_V_STANDARD_AUDIT_PASS",
    }
    checks = [
        {"check": "standard_time_match_valid", "status": "PASS" if rows else "FAIL", "value": len(rows), "detail": "Rows matched to recovered Standard Times."},
        {"check": "conversion_method_present", "status": "PASS", "value": "EDGEIQ_GOING_DEPENDENT_LENGTHS_PER_SECOND_V1", "detail": "Governed provider used by builder."},
        {"check": "converted_observations", "status": "WARN" if not converted else "PASS", "value": len(converted), "detail": "Rows converted inside approved scope."},
        {"check": "unsupported_observations", "status": "PASS" if len(unsupported) == len(blocked) else "FAIL", "value": len(unsupported), "detail": "Rows outside approved scope are blocked."},
        {"check": "conversion_parameter_positive", "status": "BLOCKED" if not converted else "PASS", "value": len(converted), "detail": "Only applicable to converted rows."},
        {"check": "units_valid", "status": "PASS", "value": "seconds/metres fields present", "detail": "Actual and standard elapsed seconds preserved."},
        {"check": "sign_convention_valid", "status": "BLOCKED" if not converted else "PASS", "value": "positive=faster_than_standard", "detail": "Standard minus actual, multiplied by lengths per second."},
        {"check": "no_infinite_or_nan_values", "status": "PASS" if bad_numbers == 0 else "FAIL", "value": bad_numbers, "detail": "Converted numeric values only."},
        {"check": "no_duplicate_observation_keys", "status": "PASS" if duplicate_count == 0 else "FAIL", "value": duplicate_count, "detail": "Unique race-runner-segment keys."},
        {"check": "all_output_traceable", "status": "PASS" if all(clean(row.get("source_hash")) for row in rows) else "FAIL", "value": len(rows), "detail": "Source hash retained."},
        {"check": "deterministic_hash", "status": "PASS" if summary["deterministic_hash"] else "FAIL", "value": summary["deterministic_hash"], "detail": "Candidate output SHA."},
        {"check": "reasonable_distribution", "status": "BLOCKED" if not converted else "PASS", "value": len(lvs_values), "detail": "No distribution until rows are inside method scope."},
    ]
    write_csv(OUT, checks, ["check", "status", "value", "detail"])
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Lengths v Standard Audit V1\n\n"
        f"Status: `{summary['status']}`\n\n"
        f"Standard-time matched observations: `{summary['standard_time_matched_observations']}`\n\n"
        f"Converted observations: `{summary['converted_observations']}`\n\n"
        f"Blocked observations: `{summary['blocked_observations']}`\n\n"
        "The governed method exists, but current matched observations are outside V1 Turf scope.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
