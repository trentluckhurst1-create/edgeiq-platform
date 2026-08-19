
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
DOC_DIR.mkdir(parents=True, exist_ok=True)
OUT_DOC = DOC_DIR / "EDGEIQ_HORSE_PERFORMANCE_AGGREGATION_METHOD_RECOVERY_V1.md"
OUT_CSV = DOC_DIR / "edgeiq_horse_performance_aggregation_contract_v1.csv"

OBS = DATA / "edgeiq_horse_performance_observation_fact_v1.csv"
PARAM = DATA / "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv"
SOURCE = ROOT / "config" / "performance-intelligence" / "edgeiq_horse_performance_aggregation_parameter_source_v1.csv"
BUILDER = ROOT / "scripts" / "build_edgeiq_horse_performance_aggregate_fact_v1.py"
RATING_BUILDER = ROOT / "scripts" / "build_edgeiq_horse_performance_rating_fact_v1.py"


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))

rows = [{
    "aggregation_method": "ARITHMETIC_MEAN or WEIGHTED_ARITHMETIC_MEAN as supplied by governed parameter",
    "historical_window": "lookback_days as supplied by governed parameter",
    "observation_ordering": "eligible observations sorted by race_date and observation id descending; included newest first up to maximum_observations",
    "observation_eligibility": "same canonical_horse_id, race_date between as_of_date-lookback_days and as_of_date inclusive, governed observed normalised status, identified governed identity",
    "minimum_observations": "minimum_observations from governed parameter; current value unrecovered",
    "maximum_observations": "maximum_observations from governed parameter; current value unrecovered",
    "weight_calculation": "1 for ARITHMETIC_MEAN; 0.5 ** (age_days / recency_half_life_days) for WEIGHTED_ARITHMETIC_MEAN with EXPONENTIAL_HALF_LIFE",
    "recency_treatment": "NONE or EXPONENTIAL_HALF_LIFE from governed parameter",
    "surface_treatment": "no active surface weighting/filter in aggregate builder",
    "distance_treatment": "no active distance weighting/filter in aggregate builder",
    "null_treatment": "required numeric/date/status fields fail hard; insufficient observations skipped",
    "as_of_date_semantics": "one aggregate is considered for each unique horse observation race_date; includes observations on or before as_of_date only",
    "formula": "aggregate_rating_value = weighted_sum(rating_base_value * weight) / total_weight",
    "rounding": "Decimal quantized to 0.000001",
    "decision": "EXISTING_AGGREGATION_METHOD_PARTIALLY_RECOVERED",
}]
with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

lines = [
    "# EDGEiQ Horse Performance Aggregation Method Recovery V1",
    "",
    "Decision: `EXISTING_AGGREGATION_METHOD_PARTIALLY_RECOVERED`",
    "",
    "## Recovered Logic",
    "- Active aggregate builder: `scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py`",
    "- Active rating fact builder: `scripts/build_edgeiq_horse_performance_rating_fact_v1.py`",
    "- Rating method after aggregation: `DIRECT_HISTORICAL_AGGREGATE_VALUE`",
    "- Aggregate formula: `aggregate_rating_value = weighted_sum(rating_base_value * weight) / total_weight`",
    "",
    "## Historical Window",
    "- Controlled by `lookback_days` from the governed aggregation parameter source.",
    "- Current governed value: `UNRECOVERED`.",
    "",
    "## Observation Ordering",
    "- Observations are grouped by `canonical_horse_id`.",
    "- Unique `race_date` values become as-of dates.",
    "- Eligible observations are sorted descending by `race_date` and observation id.",
    "- The newest observations are included up to `maximum_observations`.",
    "",
    "## Eligibility And Minimums",
    "- `rating_status` must be `OBSERVED_NORMALISED_GOVERNED`.",
    "- `identity_status` must be `IDENTIFIED_GOVERNED`.",
    "- Minimum observations are controlled by `minimum_observations` from source policy.",
    "- Current governed minimum: `UNRECOVERED`.",
    "",
    "## Weight Calculation",
    "- `ARITHMETIC_MEAN` uses weight `1`.",
    "- `WEIGHTED_ARITHMETIC_MEAN` with `EXPONENTIAL_HALF_LIFE` uses `0.5 ** (age_days / recency_half_life_days)`.",
    "- Recency half-life value is governed source data and is currently unrecovered.",
    "",
    "## Surface And Distance Treatment",
    "No active surface or distance weighting/filter is applied by this aggregate builder. Surface/distance support is governed upstream by the performance/standard-time chain.",
    "",
    "## Null And Temporal Treatment",
    "- Required date/numeric/status/evidence fields fail hard if invalid.",
    "- Future observations relative to an as-of date fail hard.",
    "- As-of date includes observations on or before the as-of date in the aggregate builder. Predictive consumers must apply their stricter target-date rule later.",
    "",
    "## Current Counts",
    f"- Horse observation rows: `{row_count(OBS)}`",
    f"- Aggregation parameter fact rows: `{row_count(PARAM)}`",
    f"- Aggregation parameter source exists: `{'YES' if SOURCE.exists() else 'NO'}`",
    f"- Aggregation parameter source rows: `{row_count(SOURCE)}`",
    "",
    "## Unresolved Semantics",
    "- The selected aggregation method is not recovered.",
    "- `maximum_observations`, `lookback_days`, `minimum_observations`, recency method and half-life are not recovered.",
    "- No historical governed source file was recovered from active repository paths or Git path history.",
    "",
    "## Candidate Decision",
    "No candidate aggregation parameter source was created. The executable formula is recovered, but its policy values are not fully governed.",
]
OUT_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"decision": "EXISTING_AGGREGATION_METHOD_PARTIALLY_RECOVERED", "report": str(OUT_DOC)}, indent=2))
