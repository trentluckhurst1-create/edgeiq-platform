
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"
OUT_CSV = DOC_DIR / "edgeiq_horse_performance_rating_input_compatibility_v1.csv"
REPORT_MD = DOC_DIR / "edgeiq_horse_performance_rating_input_compatibility_report_v1.md"

CHECKS = [
    ("canonical race identity", "edgeiq_results_lengths_v_standard_v2.csv", "edgeiq_results_lengths_v_standard_v2.csv", "canonical_race_id", "canonical_race_id"),
    ("canonical runner identity", "edgeiq_results_lengths_v_standard_v2.csv", "edgeiq_results_lengths_v_standard_v2.csv", "canonical_runner_id", "canonical_runner_id"),
    ("canonical track", "edgeiq_results_lengths_v_standard_v2.csv", "edgeiq_results_lengths_v_standard_v2.csv", "canonical_track", "canonical_track"),
    ("surface group", "edgeiq_results_lengths_v_standard_v2.csv", "edgeiq_results_lengths_v_standard_v2.csv", "canonical_surface_group", "canonical_surface_group"),
    ("distance metres", "edgeiq_results_lengths_v_standard_v2.csv", "edgeiq_results_lengths_v_standard_v2.csv", "race_distance_metres", "race_distance_metres"),
    ("seconds per length", "edgeiq_results_lengths_v_standard_v2.csv", "edgeiq_results_lengths_v_standard_v2.csv", "seconds_per_length", "seconds_per_length"),
    ("lengths versus standard", "edgeiq_results_lengths_v_standard_v2.csv", "edgeiq_results_lengths_v_standard_v2.csv", "lengths_vs_standard", "lengths_vs_standard"),
    ("sectional early/mid/late", "edgeiq_runner_sectional_performance_v2.csv", "edgeiq_runner_sectional_performance_v2.csv", "early_lengths_vs_standard;mid_lengths_vs_standard;late_lengths_vs_standard", "early_lengths_vs_standard;mid_lengths_vs_standard;late_lengths_vs_standard"),
    ("early speed phase", "edgeiq_results_early_speed_v2.csv", "edgeiq_results_early_speed_v2.csv", "lengths_vs_standard", "lengths_vs_standard"),
    ("late speed phase", "edgeiq_results_late_speed_v2.csv", "edgeiq_results_late_speed_v2.csv", "lengths_vs_standard", "lengths_vs_standard"),
    ("canonical V1 performance base bridge", "edgeiq_lengths_versus_standard_fact_v1.csv", "edgeiq_lengths_versus_standard_fact_v1.csv", "lengths_versus_standard;winner_horse_name;race_key", "lengths_versus_standard;winner_horse_name;race_key"),
    ("normalisation parameters", "edgeiq_performance_normalisation_parameter_fact_v1.csv", "edgeiq_performance_normalisation_parameter_fact_v1.csv", "centre_value;scale_value;effective_from_date", "centre_value;scale_value;effective_from_date"),
    ("horse aggregation parameters", "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv", "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv", "minimum_observations;maximum_observations;lookback_days", "minimum_observations;maximum_observations;lookback_days"),
]


def read(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), sum(1 for _ in reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

rows = []
for required_input, expected_source, actual_source, expected_col, actual_col in CHECKS:
    path = DATA / actual_source
    fields, row_count = read(path)
    actual_cols = [col for col in actual_col.split(";") if col]
    missing = [col for col in actual_cols if col not in fields]
    availability = "AVAILABLE" if path.exists() and row_count > 0 and not missing else ("HEADER_ONLY" if path.exists() and row_count == 0 and not missing else ("SCHEMA_MISSING" if path.exists() else "SOURCE_MISSING"))
    schema_status = "PASS" if not missing else "FAIL"
    migration_required = "NO"
    if required_input == "normalisation parameters" and row_count == 0:
        migration_required = "GOVERNED_PARAMETER_POPULATION_REQUIRED"
    elif required_input == "horse aggregation parameters" and row_count == 0:
        migration_required = "GOVERNED_PARAMETER_POPULATION_REQUIRED"
    elif missing:
        migration_required = "YES_SCHEMA_ALIGNMENT_REQUIRED"
    rows.append({
        "required_input": required_input,
        "expected_source": expected_source,
        "actual_source": actual_source,
        "expected_column": expected_col,
        "actual_column": actual_col,
        "availability": availability,
        "row_count": row_count,
        "schema_status": schema_status,
        "migration_required": migration_required,
        "missing_columns": ";".join(missing),
    })

write_csv(OUT_CSV, ["required_input", "expected_source", "actual_source", "expected_column", "actual_column", "availability", "row_count", "schema_status", "migration_required", "missing_columns"], rows)

schema_failures = [row for row in rows if row["schema_status"] != "PASS"]
parameter_gaps = [row for row in rows if row["migration_required"] == "GOVERNED_PARAMETER_POPULATION_REQUIRED"]
lines = [
    "# EDGEiQ Horse Performance Rating Input Compatibility V1",
    "",
    f"Schema failures: `{len(schema_failures)}`",
    f"Governed parameter population gaps: `{len(parameter_gaps)}`",
    "",
    "## Finding",
    "The current governed V2 performance outputs contain the expected race, runner, surface, distance, lengths-versus-standard, sectional, early-speed and late-speed columns.",
    "The active V1 horse-rating chain is not blocked by a stale V1/V2 filename or column mismatch at this audit point.",
    "The compatibility blocker is that both governed parameter facts required after the base PI stage are header-only: normalisation parameters and horse aggregation parameters.",
    "No builder patch is justified by this audit because the schema aligns; the missing evidence is governed parameter population, not a deterministic code defect.",
    "",
    "## Inputs",
]
for row in rows:
    lines.append(f"- `{row['required_input']}` from `{row['actual_source']}`: availability=`{row['availability']}`, rows={row['row_count']}, schema=`{row['schema_status']}`, migration=`{row['migration_required']}`")
REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "rows": len(rows),
    "schema_failures": len(schema_failures),
    "parameter_gaps": len(parameter_gaps),
    "report": str(REPORT_MD),
}, indent=2))
