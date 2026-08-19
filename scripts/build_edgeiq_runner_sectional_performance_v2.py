from __future__ import annotations

import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
LVS = DATA / "edgeiq_results_lengths_v_standard_v2.csv"
ELAPSED = DATA / "edgeiq_results_elapsed_time_observations_v1.csv"
OUT = DATA / "edgeiq_runner_sectional_performance_v2.csv"
SUMMARY = DOCS / "edgeiq_runner_sectional_performance_v2_summary.json"
REPORT = DOCS / "edgeiq_runner_sectional_performance_v2_report.md"

FIELDS = [
    "canonical_race_id", "canonical_runner_id", "canonical_surface_group", "race_date", "track", "race_number", "race_distance_metres",
    "early_lengths_vs_standard", "mid_lengths_vs_standard", "late_lengths_vs_standard", "final_segment_lengths_vs_standard",
    "best_segment_lengths_vs_standard", "worst_segment_lengths_vs_standard", "converted_segment_count", "eligible_segment_count",
    "coverage_status", "method_version",
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


def bucket(row: dict[str, str]) -> str:
    race_distance = Decimal(clean(row.get("race_distance_metres")) or "0")
    start = Decimal(clean(row.get("segment_start_metres")) or "0")
    end = Decimal(clean(row.get("segment_end_metres")) or "0")
    if end == 0:
        return "final"
    midpoint_from_start = race_distance - ((start + end) / Decimal("2"))
    ratio = midpoint_from_start / race_distance if race_distance else Decimal("0")
    if ratio <= Decimal("0.34"):
        return "early"
    if ratio <= Decimal("0.67"):
        return "mid"
    return "late"


def avg(values: list[Decimal]) -> str:
    if not values:
        return ""
    return f"{(sum(values) / Decimal(len(values))).quantize(Decimal('0.000001'))}"


def main() -> int:
    elapsed = [row for row in read_csv(ELAPSED) if clean(row.get("eligibility_status")) == "ELIGIBLE"]
    eligible_counts = defaultdict(int)
    for row in elapsed:
        eligible_counts[(clean(row.get("canonical_race_id")), clean(row.get("canonical_runner_id")))] += 1
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(LVS):
        grouped[(clean(row.get("canonical_race_id")), clean(row.get("canonical_runner_id")))].append(row)
    output: list[dict[str, object]] = []
    for (race_id, runner_id), rows in sorted(grouped.items()):
        calculated = [row for row in rows if clean(row.get("audit_status")) == "CALCULATED"]
        values = [Decimal(clean(row.get("lengths_vs_standard"))) for row in calculated if clean(row.get("lengths_vs_standard"))]
        by_bucket: dict[str, list[Decimal]] = defaultdict(list)
        for row in calculated:
            if clean(row.get("lengths_vs_standard")):
                by_bucket[bucket(row)].append(Decimal(clean(row.get("lengths_vs_standard"))))
        first = rows[0]
        output.append({
            "canonical_race_id": race_id,
            "canonical_runner_id": runner_id,
            "canonical_surface_group": clean(first.get("canonical_surface_group")),
            "race_date": clean(first.get("race_date")),
            "track": clean(first.get("track")),
            "race_number": clean(first.get("race_number")),
            "race_distance_metres": clean(first.get("race_distance_metres")),
            "early_lengths_vs_standard": avg(by_bucket["early"]),
            "mid_lengths_vs_standard": avg(by_bucket["mid"]),
            "late_lengths_vs_standard": avg(by_bucket["late"]),
            "final_segment_lengths_vs_standard": avg(by_bucket["final"]),
            "best_segment_lengths_vs_standard": f"{max(values).quantize(Decimal('0.000001'))}" if values else "",
            "worst_segment_lengths_vs_standard": f"{min(values).quantize(Decimal('0.000001'))}" if values else "",
            "converted_segment_count": len(calculated),
            "eligible_segment_count": eligible_counts.get((race_id, runner_id), 0),
            "coverage_status": "COMPLETE" if len(calculated) == eligible_counts.get((race_id, runner_id), 0) else ("PARTIAL" if calculated else "MISSING"),
            "method_version": "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2",
        })
    write_csv(OUT, output, FIELDS)
    payload = {
        "input_lvs_rows": len(read_csv(LVS)),
        "runner_rows": len(output),
        "races": len({row["canonical_race_id"] for row in output}),
        "early_rows": sum(1 for row in output if row["early_lengths_vs_standard"]),
        "mid_rows": sum(1 for row in output if row["mid_lengths_vs_standard"]),
        "late_rows": sum(1 for row in output if row["late_lengths_vs_standard"]),
        "final_rows": sum(1 for row in output if row["final_segment_lengths_vs_standard"]),
        "complete_coverage": sum(1 for row in output if row["coverage_status"] == "COMPLETE"),
        "partial_coverage": sum(1 for row in output if row["coverage_status"] == "PARTIAL"),
        "status": "RUNNER_SECTIONAL_PERFORMANCE_V2_BUILT",
    }
    SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text("# Runner Sectional Performance V2\n\n" + "\n".join(f"{k}: `{v}`" for k, v in payload.items()) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
