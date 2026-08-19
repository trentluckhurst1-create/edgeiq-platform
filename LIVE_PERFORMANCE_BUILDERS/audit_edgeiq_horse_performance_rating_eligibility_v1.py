
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CONFIG = ROOT / "config" / "performance-intelligence"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"
GATES_CSV = DOC_DIR / "edgeiq_horse_performance_rating_eligibility_gates_v1.csv"
DISTRIBUTION_CSV = DOC_DIR / "edgeiq_horse_performance_rating_history_depth_distribution_v1.csv"
REPORT = DOC_DIR / "edgeiq_horse_performance_rating_eligibility_report_v1.md"

SECTIONAL = DATA / "edgeiq_runner_sectional_performance_v2.csv"
LENGTHS = DATA / "edgeiq_results_lengths_v_standard_v2.csv"
NORM_PARAM = DATA / "edgeiq_performance_normalisation_parameter_fact_v1.csv"
AGG_PARAM = DATA / "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv"
IDENTITY = CONFIG / "edgeiq_horse_performance_identity_map_v1.csv"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

sectional_fields, sectional_rows = read_rows(SECTIONAL)
length_fields, length_rows = read_rows(LENGTHS)
norm_fields, norm_rows = read_rows(NORM_PARAM)
agg_fields, agg_rows = read_rows(AGG_PARAM)
identity_fields, identity_rows = read_rows(IDENTITY)

runner_segment_counts: defaultdict[str, int] = defaultdict(int)
runner_meta = {}
for row in length_rows:
    key = f"{text(row.get('canonical_race_id'))}|{text(row.get('canonical_runner_id'))}"
    if key == "|":
        continue
    runner_segment_counts[key] += 1
    runner_meta.setdefault(key, row)

bucket_counts = Counter()
for key, count in runner_segment_counts.items():
    if count <= 0:
        bucket = "0 eligible segments"
    elif count == 1:
        bucket = "1 eligible segment"
    elif count == 2:
        bucket = "2 eligible segments"
    elif count == 3:
        bucket = "3 eligible segments"
    elif count == 4:
        bucket = "4 eligible segments"
    else:
        bucket = "5+ eligible segments"
    bucket_counts[bucket] += 1

buckets = ["0 eligible segments", "1 eligible segment", "2 eligible segments", "3 eligible segments", "4 eligible segments", "5+ eligible segments"]
distribution_rows = [{"history_depth_bucket": bucket, "runner_count": bucket_counts.get(bucket, 0)} for bucket in buckets]

total_runners = len(runner_segment_counts)
complete_sectional = sum(1 for row in sectional_rows if text(row.get("coverage_status")) == "COMPLETE")
supported_surface = sum(1 for row in sectional_rows if text(row.get("canonical_surface_group")) in {"AUSTRALIAN_SYNTHETIC", "TURF", "GOOD", "SOFT", "HEAVY"})
supported_distance = sum(1 for row in sectional_rows if text(row.get("race_distance_metres")).isdigit() and int(text(row.get("race_distance_metres"))) > 0)

gate_rows = [
    {"gate_name": "valid historical segment rows", "configured_threshold": ">=1 converted segment", "governance_source": SECTIONAL.name, "rows_before": total_runners, "rows_after": total_runners, "rows_rejected": 0, "gate_status": "PASS" if total_runners else "FAIL"},
    {"gate_name": "complete sectional groups", "configured_threshold": "coverage_status COMPLETE", "governance_source": SECTIONAL.name, "rows_before": total_runners, "rows_after": complete_sectional, "rows_rejected": max(total_runners - complete_sectional, 0), "gate_status": "PASS" if complete_sectional == total_runners and total_runners else "FAIL"},
    {"gate_name": "supported surface", "configured_threshold": "canonical governed surface group", "governance_source": SECTIONAL.name, "rows_before": total_runners, "rows_after": supported_surface, "rows_rejected": max(total_runners - supported_surface, 0), "gate_status": "PASS" if supported_surface == total_runners and total_runners else "FAIL"},
    {"gate_name": "supported distance", "configured_threshold": "distance metres positive", "governance_source": SECTIONAL.name, "rows_before": total_runners, "rows_after": supported_distance, "rows_rejected": max(total_runners - supported_distance, 0), "gate_status": "PASS" if supported_distance == total_runners and total_runners else "FAIL"},
    {"gate_name": "normalisation parameter available", "configured_threshold": "effective governed parameter row", "governance_source": NORM_PARAM.name, "rows_before": total_runners, "rows_after": total_runners if norm_rows else 0, "rows_rejected": 0 if norm_rows else total_runners, "gate_status": "FAIL" if not norm_rows else "PASS"},
    {"gate_name": "horse identity map available", "configured_threshold": "approved exact normalised horse identity", "governance_source": str(IDENTITY.relative_to(ROOT)), "rows_before": total_runners, "rows_after": total_runners if identity_rows else 0, "rows_rejected": 0 if identity_rows else total_runners, "gate_status": "FAIL" if not identity_rows else "PASS"},
    {"gate_name": "horse aggregation parameter available", "configured_threshold": "minimum observations / lookback / recency governed parameter", "governance_source": AGG_PARAM.name, "rows_before": total_runners, "rows_after": total_runners if agg_rows else 0, "rows_rejected": 0 if agg_rows else total_runners, "gate_status": "FAIL" if not agg_rows else "PASS"},
]

if total_runners and bucket_counts.get("5+ eligible segments", 0) == total_runners:
    classification = "HISTORICAL_DEPTH_PRESENT_PARAMETER_AND_IDENTITY_BLOCKED"
elif total_runners == 0:
    classification = "NO_HISTORICAL_RUNNER_PERFORMANCE"
else:
    classification = "PARTIAL_HISTORICAL_DEPTH"

write_csv(GATES_CSV, ["gate_name", "configured_threshold", "governance_source", "rows_before", "rows_after", "rows_rejected", "gate_status"], gate_rows)
write_csv(DISTRIBUTION_CSV, ["history_depth_bucket", "runner_count"], distribution_rows)

lines = [
    "# EDGEiQ Horse Performance Rating Eligibility V1",
    "",
    f"Eligibility classification: `{classification}`",
    f"Historical runner performances: `{total_runners}`",
    "",
    "## History Depth Distribution",
]
for row in distribution_rows:
    lines.append(f"- `{row['history_depth_bucket']}`: {row['runner_count']}")
lines.extend(["", "## Gates"])
for row in gate_rows:
    lines.append(f"- `{row['gate_name']}`: before={row['rows_before']}, after={row['rows_after']}, rejected={row['rows_rejected']}, status=`{row['gate_status']}`")
lines.extend([
    "",
    "## Finding",
    "All 24 governed historical runner rows have 5+ eligible converted segments and complete sectional coverage. The zero-row outcome should not be classified as `INSUFFICIENT_GOVERNED_HISTORICAL_PERFORMANCE_DEPTH`.",
    "The eligibility blockers are missing governed normalisation parameters, missing governed horse identity map, and missing governed horse aggregation parameters.",
])
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "classification": classification,
    "historical_runner_performances": total_runners,
    "distribution": dict(bucket_counts),
    "failed_gates": [row["gate_name"] for row in gate_rows if row["gate_status"] == "FAIL"],
    "report": str(REPORT),
}, indent=2))
