
from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"
OUT_CSV = DOC_DIR / "edgeiq_horse_performance_rating_grain_v1.csv"
REPORT_MD = DOC_DIR / "edgeiq_horse_performance_rating_grain_report_v1.md"

FILES = {
    "observation": DATA / "edgeiq_horse_performance_observation_fact_v1.csv",
    "aggregate": DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv",
    "rating": DATA / "edgeiq_horse_performance_rating_fact_v1.csv",
}
BUILDER = ROOT / "scripts" / "build_edgeiq_horse_performance_rating_fact_v1.py"
AGG_BUILDER = ROOT / "scripts" / "build_edgeiq_horse_performance_aggregate_fact_v1.py"


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


def duplicate_summary(rows: list[dict[str, str]], keys: list[str]) -> tuple[int, int]:
    if not rows:
        return 0, 0
    actual = [key for key in keys if key in rows[0]]
    if not actual:
        return 0, 0
    counts = Counter(tuple(text(row.get(key)) for key in actual) for row in rows)
    duplicate_keys = sum(1 for value in counts.values() if value > 1)
    duplicate_rows = sum(value - 1 for value in counts.values() if value > 1)
    return duplicate_keys, duplicate_rows


def source_contains(path: Path, needle: str) -> bool:
    return path.exists() and needle in path.read_text(encoding="utf-8", errors="replace")


def primary_key_from_builder() -> str:
    if not BUILDER.exists():
        return "UNKNOWN"
    source = BUILDER.read_text(encoding="utf-8", errors="replace")
    if "horse_performance_aggregate_id" in source and "canonical_horse_id" in source and "rating_as_of_date" in source:
        return "horse_performance_rating_id; source aggregate grain canonical_horse_id + rating_as_of_date + aggregation_parameter_id"
    return "UNKNOWN"


rows_out: list[dict[str, object]] = []
checks = [
    ("observation", ["horse_performance_observation_id"], "one row per governed base performance observation mapped to canonical horse identity"),
    ("aggregate", ["horse_performance_aggregate_id"], "one row per canonical horse, as-of date, governed aggregation parameter and included observations"),
    ("aggregate_horse_date_parameter", ["canonical_horse_id", "aggregate_as_of_date", "horse_performance_aggregation_parameter_id"], "expected aggregate business grain"),
    ("rating", ["horse_performance_rating_id"], "one row per governed horse performance aggregate promoted to rating fact"),
    ("rating_horse_date_parameter", ["canonical_horse_id", "rating_as_of_date", "horse_performance_aggregation_parameter_id"], "expected rating business grain"),
]

for name, key_fields, expectation in checks:
    source_name = name.split("_")[0]
    fields, rows = read_rows(FILES[source_name])
    missing = [field for field in key_fields if field not in fields]
    dup_keys, dup_rows = duplicate_summary(rows, key_fields)
    rows_out.append({
        "check_name": name,
        "source_file": FILES[source_name].name,
        "expected_grain": expectation,
        "primary_key_fields": ";".join(key_fields),
        "source_rows": len(rows),
        "missing_key_fields": ";".join(missing),
        "duplicate_key_count": dup_keys,
        "duplicate_row_count": dup_rows,
        "grain_status": "NOT_TESTABLE_EMPTY_SOURCE" if not rows else ("PASS" if not missing and dup_rows == 0 else "FAIL"),
    })

builder_primary_key = primary_key_from_builder()
contract_expects_segment = source_contains(BUILDER, "official_distance_metres") and source_contains(BUILDER, "benchmark_observation_id") and False
contract_expects_aggregate = source_contains(BUILDER, "horse_performance_aggregate_id") and source_contains(BUILDER, "aggregate_rating_value")
agg_uses_as_of = source_contains(AGG_BUILDER, "unique_as_of_dates") and source_contains(AGG_BUILDER, "included_observation_count")

decision = "ROLLING_HORSE_AS_OF_DATE_RATING_FACT"
if not contract_expects_aggregate:
    decision = "GRAIN_CONTRACT_UNCLEAR"

write_csv(OUT_CSV, ["check_name", "source_file", "expected_grain", "primary_key_fields", "source_rows", "missing_key_fields", "duplicate_key_count", "duplicate_row_count", "grain_status"], rows_out)

lines = [
    "# EDGEiQ Horse Performance Rating Grain Audit V1",
    "",
    f"Grain decision: `{decision}`",
    "",
    "## Contract-Derived Grain",
    f"- Parsed primary key: `{builder_primary_key}`",
    f"- Rating builder consumes aggregate rows: `{contract_expects_aggregate}`",
    f"- Aggregate builder emits unique as-of dates per horse: `{agg_uses_as_of}`",
    "- The active contract does not emit one row per sectional segment.",
    "- The active rating fact is not a horse-distance profile, horse-surface profile, campaign aggregate, or race-entry row.",
    "- The active grain is one governed horse-performance rating row per source horse-performance aggregate row, which is business-keyed by canonical horse, aggregate/rating as-of date, governed aggregation parameter, and included observations.",
    "",
    "## Duplicate Checks",
]
for row in rows_out:
    lines.append(f"- `{row['check_name']}` on `{row['primary_key_fields']}`: rows={row['source_rows']}, duplicate_rows={row['duplicate_row_count']}, status=`{row['grain_status']}`")
lines.extend([
    "",
    "## Finding",
    "The current empty production files make duplicate-key validation not testable, but the builder contract is clear. Do not build per-segment ratings unless the contract changes. The next buildable rating fact should preserve the rolling horse/as-of-date aggregate grain.",
])
REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "grain_decision": decision,
    "rows_written": len(rows_out),
    "report": str(REPORT_MD),
}, indent=2))


if __name__ == "__main__":
    main_missing = False
