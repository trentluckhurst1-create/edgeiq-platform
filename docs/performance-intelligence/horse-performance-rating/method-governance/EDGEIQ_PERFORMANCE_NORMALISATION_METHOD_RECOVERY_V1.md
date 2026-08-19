# EDGEiQ Performance Normalisation Method Recovery V1

Decision: `EXISTING_NORMALISATION_METHOD_PARTIALLY_RECOVERED`

## Recovered Method
- Active builder: `scripts/build_edgeiq_performance_normalisation_fact_v1.py`
- Parameter source builder: `scripts/build_edgeiq_performance_normalisation_parameter_fact_v1.py`
- Method constant: `LINEAR_CENTRE_AND_SCALE`
- Formula: `normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value`
- Precision: Decimal values are formatted to six decimal places.

## Raw Input Fields
- `raw_performance_lengths` from `edgeiq_performance_intelligence_base_fact_v1.csv`
- `race_date` for effective-date parameter lookup
- race/track/distance fields are carried through but are not active lookup dimensions.

## Normalised Output Fields
- `normalised_performance_value`
- `normalisation_method`
- `normalisation_status`
- source evidence hashes and builder/contract versions

## Grouping Dimensions
The active code only uses effective date and method/status as lookup criteria. It does not currently consume surface, distance, track, condition, segment, benchmark group, population mean/median/stddev, robust spread, or min/max dimensions from the parameter source schema.

## Parameter Contract
- Source schema: `normalisation_method, centre_value, scale_value, normalisation_model_version, parameter_status, effective_from_date, effective_to_date, evidence_reference, evidence_sha256`
- Fact schema proven by contract: `edgeiq_performance_normalisation_parameter_fact_v1_contract.json`

## Current Counts
- Historical PI base rows: `168`
- Normalisation parameter fact rows: `0`
- Normalisation parameter source exists: `NO`
- Normalisation parameter source rows: `0`

## Unresolved Semantics
- Actual governed `centre_value` is not recovered.
- Actual governed `scale_value` is not recovered.
- Minimum population/provenance for those parameters is not recovered.
- No evidence was recovered that permits reconstructing these values from current 24-runner data.

## Candidate Decision
No candidate normalisation parameter source was created. The formula is recovered, but the parameter values and provenance are not fully governed.
