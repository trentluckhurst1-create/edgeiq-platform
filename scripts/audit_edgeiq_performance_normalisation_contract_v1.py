
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
DOC_DIR.mkdir(parents=True, exist_ok=True)
OUT_DOC = DOC_DIR / "EDGEIQ_PERFORMANCE_NORMALISATION_METHOD_RECOVERY_V1.md"
OUT_CSV = DOC_DIR / "edgeiq_performance_normalisation_contract_v1.csv"

BASE = DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
PARAM = DATA / "edgeiq_performance_normalisation_parameter_fact_v1.csv"
SOURCE = ROOT / "config" / "performance-intelligence" / "edgeiq_performance_normalisation_parameter_source_v1.csv"
BUILDER = ROOT / "scripts" / "build_edgeiq_performance_normalisation_fact_v1.py"
PARAM_BUILDER = ROOT / "scripts" / "build_edgeiq_performance_normalisation_parameter_fact_v1.py"


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))

rows = [{
    "raw_input_fields": "raw_performance_lengths;race_date",
    "normalised_output_fields": "normalised_performance_value;normalisation_method;normalisation_status",
    "grouping_dimensions": "effective date range only in active lookup; no surface/distance/track/condition/segment grouping consumed",
    "parameter_lookup_keys": "race_date between effective_from_date and effective_to_date; normalisation_method LINEAR_CENTRE_AND_SCALE; parameter_status AVAILABLE",
    "formula": "normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value",
    "centre_parameter": "centre_value",
    "spread_parameter": "scale_value",
    "minimum_population": "NOT_GOVERNED_IN_ACTIVE_CODE_OR_RECOVERED_SOURCE",
    "fallback_behaviour": "hard fail if base rows exist and no effective parameter matches; header-only output only when base rows are empty",
    "precision": "Decimal quantized to 0.000001",
    "outlier_handling": "finite numeric validation only; no trimming/winsorisation recovered",
    "missing_group_behaviour": "no matching effective parameter raises RuntimeError",
    "decision": "EXISTING_NORMALISATION_METHOD_PARTIALLY_RECOVERED",
}]
with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

lines = [
    "# EDGEiQ Performance Normalisation Method Recovery V1",
    "",
    "Decision: `EXISTING_NORMALISATION_METHOD_PARTIALLY_RECOVERED`",
    "",
    "## Recovered Method",
    "- Active builder: `scripts/build_edgeiq_performance_normalisation_fact_v1.py`",
    "- Parameter source builder: `scripts/build_edgeiq_performance_normalisation_parameter_fact_v1.py`",
    "- Method constant: `LINEAR_CENTRE_AND_SCALE`",
    "- Formula: `normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value`",
    "- Precision: Decimal values are formatted to six decimal places.",
    "",
    "## Raw Input Fields",
    "- `raw_performance_lengths` from `edgeiq_performance_intelligence_base_fact_v1.csv`",
    "- `race_date` for effective-date parameter lookup",
    "- race/track/distance fields are carried through but are not active lookup dimensions.",
    "",
    "## Normalised Output Fields",
    "- `normalised_performance_value`",
    "- `normalisation_method`",
    "- `normalisation_status`",
    "- source evidence hashes and builder/contract versions",
    "",
    "## Grouping Dimensions",
    "The active code only uses effective date and method/status as lookup criteria. It does not currently consume surface, distance, track, condition, segment, benchmark group, population mean/median/stddev, robust spread, or min/max dimensions from the parameter source schema.",
    "",
    "## Parameter Contract",
    "- Source schema: `normalisation_method, centre_value, scale_value, normalisation_model_version, parameter_status, effective_from_date, effective_to_date, evidence_reference, evidence_sha256`",
    "- Fact schema proven by contract: `edgeiq_performance_normalisation_parameter_fact_v1_contract.json`",
    "",
    "## Current Counts",
    f"- Historical PI base rows: `{row_count(BASE)}`",
    f"- Normalisation parameter fact rows: `{row_count(PARAM)}`",
    f"- Normalisation parameter source exists: `{'YES' if SOURCE.exists() else 'NO'}`",
    f"- Normalisation parameter source rows: `{row_count(SOURCE)}`",
    "",
    "## Unresolved Semantics",
    "- Actual governed `centre_value` is not recovered.",
    "- Actual governed `scale_value` is not recovered.",
    "- Minimum population/provenance for those parameters is not recovered.",
    "- No evidence was recovered that permits reconstructing these values from current 24-runner data.",
    "",
    "## Candidate Decision",
    "No candidate normalisation parameter source was created. The formula is recovered, but the parameter values and provenance are not fully governed.",
]
OUT_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"decision": "EXISTING_NORMALISATION_METHOD_PARTIALLY_RECOVERED", "report": str(OUT_DOC)}, indent=2))
