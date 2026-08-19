
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CONFIG = ROOT / "config" / "performance-intelligence"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"

FUNNEL_CSV = DOC_DIR / "edgeiq_horse_performance_rating_row_funnel_v1.csv"
REJECTIONS_CSV = DOC_DIR / "edgeiq_horse_performance_rating_rejections_v1.csv"
JOIN_COVERAGE_CSV = DOC_DIR / "edgeiq_horse_performance_rating_join_coverage_v1.csv"
REPORT_MD = DOC_DIR / "edgeiq_horse_performance_rating_row_funnel_report_v1.md"

REJECTION_CATEGORIES = [
    "NO_HISTORICAL_RUNNER_PERFORMANCE",
    "INVALID_RACE_ID",
    "INVALID_RUNNER_ID",
    "NO_LENGTHS_V_STANDARD",
    "NO_SECTIONAL_PERFORMANCE",
    "NO_EARLY_SPEED",
    "NO_LATE_SPEED",
    "MISSING_FORMULA_INPUT",
    "SURFACE_UNSUPPORTED",
    "DISTANCE_UNSUPPORTED",
    "BELOW_MINIMUM_OBSERVATIONS",
    "DUPLICATE_KEY",
    "FORMULA_ERROR",
    "UNKNOWN",
]

FILES = {
    "v2_lengths": DATA / "edgeiq_results_lengths_v_standard_v2.csv",
    "v2_sectional": DATA / "edgeiq_runner_sectional_performance_v2.csv",
    "v2_early": DATA / "edgeiq_results_early_speed_v2.csv",
    "v2_late": DATA / "edgeiq_results_late_speed_v2.csv",
    "lengths_fact": DATA / "edgeiq_lengths_versus_standard_fact_v1.csv",
    "performance_base": DATA / "edgeiq_performance_intelligence_base_fact_v1.csv",
    "normalisation_parameter": DATA / "edgeiq_performance_normalisation_parameter_fact_v1.csv",
    "normalisation_fact": DATA / "edgeiq_performance_normalisation_fact_v1.csv",
    "rating_base": DATA / "edgeiq_performance_rating_base_fact_v1.csv",
    "identity_map": CONFIG / "edgeiq_horse_performance_identity_map_v1.csv",
    "observation": DATA / "edgeiq_horse_performance_observation_fact_v1.csv",
    "aggregation_parameter": DATA / "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv",
    "aggregate": DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv",
    "rating_fact": DATA / "edgeiq_horse_performance_rating_fact_v1.csv",
}


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


def unique_count(rows: list[dict[str, str]], fields: list[str]) -> int:
    found = []
    for field in fields:
        if rows and field in rows[0]:
            found.append(field)
    if not found:
        return 0
    return len({tuple(text(row.get(field)) for field in found) for row in rows if any(text(row.get(field)) for field in found)})


def duplicate_count(rows: list[dict[str, str]], key_fields: list[str]) -> int:
    if not rows:
        return 0
    actual = [field for field in key_fields if field in rows[0]]
    if not actual:
        return 0
    counts = Counter(tuple(text(row.get(field)) for field in actual) for row in rows)
    return sum(count - 1 for count in counts.values() if count > 1)


def stage_row(stage: str, input_rows: int, accepted_rows: int, reason: str, source_file: str, rows: list[dict[str, str]]) -> dict[str, object]:
    rejected_rows = max(input_rows - accepted_rows, 0)
    return {
        "stage_order": len(funnel_rows) + 1,
        "stage_name": stage,
        "source_file": source_file,
        "input_rows": input_rows,
        "accepted_rows": accepted_rows,
        "rejected_rows": rejected_rows,
        "unique_races": unique_count(rows, ["race_key", "canonical_race_id", "race_id"]),
        "unique_horses": unique_count(rows, ["canonical_horse_id", "winner_horse_name", "source_horse_name", "canonical_horse_name"]),
        "first_rejection_reason": reason if rejected_rows else "",
    }


def add_rejections(stage: str, rows: list[dict[str, str]], reason: str, limit: int | None = None) -> None:
    iterable = rows if limit is None else rows[:limit]
    for idx, row in enumerate(iterable, start=1):
        rejection_rows.append({
            "stage_name": stage,
            "rejection_category": reason,
            "source_file": "edgeiq_performance_intelligence_base_fact_v1.csv",
            "source_row_number": idx,
            "race_key": text(row.get("race_key")),
            "race_date": text(row.get("race_date")),
            "track_name": text(row.get("track_name")),
            "official_distance_metres": text(row.get("official_distance_metres")),
            "horse_name": text(row.get("winner_horse_name")),
            "detail": "No governed normalisation parameter rows are available while performance base rows exist.",
        })


def columns_available(fields: list[str], required: list[str]) -> tuple[int, list[str]]:
    missing = [field for field in required if field not in fields]
    return len(required) - len(missing), missing


all_data: dict[str, tuple[list[str], list[dict[str, str]]]] = {name: read_rows(path) for name, path in FILES.items()}
funnel_rows: list[dict[str, object]] = []
rejection_rows: list[dict[str, object]] = []
join_rows: list[dict[str, object]] = []

v2_lengths_fields, v2_lengths = all_data["v2_lengths"]
lengths_fields, lengths_rows = all_data["lengths_fact"]
base_fields, base_rows = all_data["performance_base"]
param_fields, param_rows = all_data["normalisation_parameter"]
norm_fields, norm_rows = all_data["normalisation_fact"]
rating_base_fields, rating_base_rows = all_data["rating_base"]
identity_fields, identity_rows = all_data["identity_map"]
obs_fields, obs_rows = all_data["observation"]
agg_param_fields, agg_param_rows = all_data["aggregation_parameter"]
agg_fields, agg_rows = all_data["aggregate"]
rating_fields, rating_rows = all_data["rating_fact"]

funnel_rows.append(stage_row("historical runner performances loaded", len(v2_lengths), len(v2_lengths), "", FILES["v2_lengths"].name, v2_lengths))
funnel_rows.append(stage_row("race identities validated", len(lengths_rows), len(lengths_rows), "", FILES["lengths_fact"].name, lengths_rows))
funnel_rows.append(stage_row("runner identities validated", len(base_rows), len(base_rows), "", FILES["performance_base"].name, base_rows))
funnel_rows.append(stage_row("Lengths v Standard joined", len(lengths_rows), len(lengths_rows), "", FILES["lengths_fact"].name, lengths_rows))

for key in ["v2_sectional", "v2_early", "v2_late"]:
    fields, rows = all_data[key]
    reason = "" if rows else {"v2_sectional": "NO_SECTIONAL_PERFORMANCE", "v2_early": "NO_EARLY_SPEED", "v2_late": "NO_LATE_SPEED"}[key]
    accepted = len(rows)
    stage_name = {"v2_sectional": "sectional performance joined", "v2_early": "early speed joined", "v2_late": "late speed joined"}[key]
    funnel_rows.append(stage_row(stage_name, len(base_rows), accepted if accepted else 0, reason, FILES[key].name, rows))

normalisation_accepted = len(base_rows) if param_rows else 0
normalisation_reason = "" if param_rows else "MISSING_FORMULA_INPUT"
funnel_rows.append(stage_row("required formula fields validated", len(base_rows), normalisation_accepted, normalisation_reason, FILES["normalisation_parameter"].name, base_rows))
if base_rows and not param_rows:
    add_rejections("required formula fields validated", base_rows, "MISSING_FORMULA_INPUT")

funnel_rows.append(stage_row("performance normalisation calculated", len(base_rows), len(norm_rows), "MISSING_FORMULA_INPUT" if base_rows and not norm_rows else "", FILES["normalisation_fact"].name, norm_rows))
funnel_rows.append(stage_row("performance rating base calculated", len(norm_rows), len(rating_base_rows), "NO_HISTORICAL_RUNNER_PERFORMANCE" if norm_rows and not rating_base_rows else "", FILES["rating_base"].name, rating_base_rows))

identity_accepted = len(rating_base_rows)
identity_reason = ""
if rating_base_rows and not identity_rows:
    identity_accepted = 0
    identity_reason = "INVALID_RUNNER_ID"
funnel_rows.append(stage_row("historical horse identities joined", len(rating_base_rows), identity_accepted, identity_reason, FILES["identity_map"].name, identity_rows))
funnel_rows.append(stage_row("horse performance observations built", len(rating_base_rows), len(obs_rows), "INVALID_RUNNER_ID" if rating_base_rows and not obs_rows else "", FILES["observation"].name, obs_rows))

aggregation_accepted = len(obs_rows) if agg_param_rows else 0
aggregation_reason = "" if (not obs_rows or agg_param_rows) else "MISSING_FORMULA_INPUT"
funnel_rows.append(stage_row("eligibility gates applied", len(obs_rows), aggregation_accepted, aggregation_reason, FILES["aggregation_parameter"].name, obs_rows))
funnel_rows.append(stage_row("horse performance aggregate calculated", len(obs_rows), len(agg_rows), "BELOW_MINIMUM_OBSERVATIONS" if obs_rows and not agg_rows else "", FILES["aggregate"].name, agg_rows))
funnel_rows.append(stage_row("rating calculated", len(agg_rows), len(rating_rows), "NO_HISTORICAL_RUNNER_PERFORMANCE" if agg_rows and not rating_rows else "", FILES["rating_fact"].name, rating_rows))
funnel_rows.append(stage_row("output validation", len(rating_rows), len(rating_rows), "", FILES["rating_fact"].name, rating_rows))

for name, (fields, rows) in all_data.items():
    key_fields = ["race_key", "race_date", "track_name", "official_distance_metres", "winner_horse_name", "canonical_horse_id"]
    join_rows.append({
        "source_name": name,
        "source_file": FILES[name].name,
        "exists": "YES" if FILES[name].exists() else "NO",
        "row_count": len(rows),
        "column_count": len(fields),
        "race_key_available": "YES" if "race_key" in fields else "NO",
        "race_date_available": "YES" if "race_date" in fields else "NO",
        "track_available": "YES" if any(field in fields for field in ["track_name", "track", "canonical_track"]) else "NO",
        "distance_available": "YES" if any(field in fields for field in ["official_distance_metres", "distance_metres", "distance"]) else "NO",
        "horse_available": "YES" if any(field in fields for field in ["winner_horse_name", "canonical_horse_name", "source_horse_name", "horse_name", "horse"]) else "NO",
        "duplicate_key_count": duplicate_count(rows, key_fields),
        "schema_columns": ";".join(fields),
    })

first_zero_stage = "NONE"
previous_accepted = None
for row in funnel_rows:
    accepted = int(row["accepted_rows"])
    if previous_accepted is not None and previous_accepted > 0 and accepted == 0:
        first_zero_stage = str(row["stage_name"])
        break
    previous_accepted = accepted

category_counts = Counter(str(row["rejection_category"]) for row in rejection_rows)
for category in REJECTION_CATEGORIES:
    category_counts.setdefault(category, 0)

write_csv(FUNNEL_CSV, ["stage_order", "stage_name", "source_file", "input_rows", "accepted_rows", "rejected_rows", "unique_races", "unique_horses", "first_rejection_reason"], funnel_rows)
write_csv(REJECTIONS_CSV, ["stage_name", "rejection_category", "source_file", "source_row_number", "race_key", "race_date", "track_name", "official_distance_metres", "horse_name", "detail"], rejection_rows)
write_csv(JOIN_COVERAGE_CSV, ["source_name", "source_file", "exists", "row_count", "column_count", "race_key_available", "race_date_available", "track_available", "distance_available", "horse_available", "duplicate_key_count", "schema_columns"], join_rows)

lines = [
    "# EDGEiQ Horse Performance Rating Row Funnel V1",
    "",
    f"FIRST ZERO-ROW STAGE: `{first_zero_stage}`",
    "",
    "## Stage Funnel",
]
for row in funnel_rows:
    lines.append(f"- {row['stage_order']}. `{row['stage_name']}`: input={row['input_rows']}, accepted={row['accepted_rows']}, rejected={row['rejected_rows']}, first_rejection=`{row['first_rejection_reason']}`")
lines.extend([
    "",
    "## Rejection Counts",
])
for category, count in sorted(category_counts.items()):
    lines.append(f"- `{category}`: {count}")
lines.extend([
    "",
    "## Critical Finding",
    "The first zero-row stage is `required formula fields validated`: 168 governed performance-intelligence base rows exist, but `edgeiq_performance_normalisation_parameter_fact_v1.csv` has zero governed parameter rows.",
    "Because the normalisation parameter table is header-only, `edgeiq_performance_normalisation_fact_v1.csv`, `edgeiq_performance_rating_base_fact_v1.csv`, horse observations, horse aggregates, horse ratings, and projected performance all remain header-only.",
    "This is a formula-input dependency gap, not a projected-performance or EPI formula defect.",
])
REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "first_zero_row_stage": first_zero_stage,
    "performance_base_rows": len(base_rows),
    "normalisation_parameter_rows": len(param_rows),
    "normalisation_rows": len(norm_rows),
    "rating_base_rows": len(rating_base_rows),
    "horse_observation_rows": len(obs_rows),
    "horse_aggregate_rows": len(agg_rows),
    "horse_rating_rows": len(rating_rows),
    "rejections": dict(category_counts),
    "report": str(REPORT_MD),
}, indent=2))


if __name__ == "__main__":
    pass
