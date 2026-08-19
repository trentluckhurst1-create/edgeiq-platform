from __future__ import annotations

import csv
import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path
from statistics import median


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
CANDIDATE = DATA / "edgeiq_results_lengths_v_standard_v2_CANDIDATE.csv"
FINAL = DATA / "edgeiq_results_lengths_v_standard_v2.csv"
AUDIT = DOCS / "edgeiq_results_lengths_v_standard_v2_audit.csv"
SUMMARY = DOCS / "edgeiq_results_lengths_v_standard_v2_audit_summary.json"
REPORT = DOCS / "edgeiq_results_lengths_v_standard_v2_audit_report.md"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def pct(values: list[Decimal], q: Decimal) -> Decimal:
    if not values:
        return Decimal("0")
    ordered = sorted(values)
    index = int((Decimal(len(ordered) - 1) * q).to_integral_value(rounding="ROUND_HALF_UP"))
    return ordered[index]


def main() -> int:
    rows = read_csv(CANDIDATE)
    converted = [row for row in rows if clean(row.get("audit_status")) == "CALCULATED"]
    blocked = [row for row in rows if clean(row.get("audit_status")) != "CALCULATED"]
    synth = [row for row in converted if clean(row.get("canonical_surface_group")) == "AUSTRALIAN_SYNTHETIC"]
    checks: list[dict[str, object]] = []
    keys: set[tuple[str, str, str]] = set()
    duplicate_count = 0
    arithmetic_failures = 0
    nonfinite_failures = 0
    for row in converted:
        key = (clean(row.get("canonical_race_id")), clean(row.get("canonical_runner_id")), clean(row.get("segment_sequence")))
        if key in keys:
            duplicate_count += 1
        keys.add(key)
        try:
            actual = Decimal(clean(row.get("actual_elapsed_seconds")))
            standard = Decimal(clean(row.get("standard_elapsed_seconds")))
            lps = Decimal(clean(row.get("lengths_per_second")))
            lengths = Decimal(clean(row.get("lengths_vs_standard")))
            expected = (standard - actual) * lps
            if abs(expected - lengths) > Decimal("0.000001"):
                arithmetic_failures += 1
            if not lengths.is_finite():
                nonfinite_failures += 1
        except Exception:
            arithmetic_failures += 1
    checks.append({"check": "candidate_exists", "status": "PASS" if rows else "FAIL", "value": len(rows)})
    checks.append({"check": "all_matched_rows_converted", "status": "PASS" if rows and len(blocked) == 0 else "FAIL", "value": len(converted)})
    checks.append({"check": "current_synthetic_resolves", "status": "PASS" if synth and len(synth) == len(converted) else "FAIL", "value": len(synth)})
    checks.append({"check": "method_version", "status": "PASS" if all(clean(row.get("conversion_version")) == "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2" for row in converted) else "FAIL", "value": "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2"})
    checks.append({"check": "synthetic_lps_6", "status": "PASS" if all(clean(row.get("lengths_per_second")) in {"6.000000000", "6.0"} for row in synth) else "FAIL", "value": len(synth)})
    checks.append({"check": "seconds_per_length", "status": "PASS" if all(clean(row.get("seconds_per_length")) == "0.166666667" for row in synth) else "FAIL", "value": "1/6"})
    checks.append({"check": "no_nan_or_infinite", "status": "PASS" if nonfinite_failures == 0 else "FAIL", "value": nonfinite_failures})
    checks.append({"check": "no_duplicate_observation_keys", "status": "PASS" if duplicate_count == 0 else "FAIL", "value": duplicate_count})
    checks.append({"check": "arithmetic_integrity", "status": "PASS" if arithmetic_failures == 0 else "FAIL", "value": arithmetic_failures})
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "value"])
        writer.writeheader()
        writer.writerows(checks)
    values = [Decimal(clean(row.get("lengths_vs_standard"))) for row in converted]
    status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"
    if status == "PASS":
        shutil.copyfile(CANDIDATE, FINAL)
    payload = {
        "status": "LENGTHS_V_STANDARD_V2_AUDIT_PASS" if status == "PASS" else "LENGTHS_V_STANDARD_V2_AUDIT_FAIL",
        "matched_observations": len(rows),
        "converted_observations": len(converted),
        "blocked_observations": len(blocked),
        "turf_converted_observations": sum(1 for row in converted if clean(row.get("canonical_surface_group")) == "TURF"),
        "australian_synthetic_converted_observations": len(synth),
        "races": len({clean(row.get("canonical_race_id")) for row in converted}),
        "runners": len({clean(row.get("canonical_runner_id")) for row in converted}),
        "benchmark_groups": len({clean(row.get("benchmark_group_id")) for row in converted}),
        "minimum_lvs": f"{min(values):.6f}" if values else "",
        "maximum_lvs": f"{max(values):.6f}" if values else "",
        "median_lvs": f"{median(values):.6f}" if values else "",
        "p05": f"{pct(values, Decimal('0.05')):.6f}" if values else "",
        "p95": f"{pct(values, Decimal('0.95')):.6f}" if values else "",
        "positive_rows": sum(1 for value in values if value > 0),
        "zero_rows": sum(1 for value in values if value == 0),
        "negative_rows": sum(1 for value in values if value < 0),
        "candidate_hash": hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() if CANDIDATE.exists() else "",
        "final_hash": hashlib.sha256(FINAL.read_bytes()).hexdigest() if FINAL.exists() else "",
    }
    SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Lengths v Standard V2 Audit\n\n"
        f"Status: `{payload['status']}`\n\n"
        f"Matched observations: `{payload['matched_observations']}`\n\n"
        f"Converted observations: `{payload['converted_observations']}`\n\n"
        f"Blocked observations: `{payload['blocked_observations']}`\n\n"
        f"Australian Synthetic rows: `{payload['australian_synthetic_converted_observations']}`\n\n"
        f"Final hash: `{payload['final_hash']}`\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
