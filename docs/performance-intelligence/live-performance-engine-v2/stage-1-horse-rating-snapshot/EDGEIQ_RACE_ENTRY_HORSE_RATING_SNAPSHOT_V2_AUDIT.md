# EDGEIQ Race-Entry Horse Rating Snapshot V2 Audit

Status: `EDGEIQ_RACE_ENTRY_HORSE_RATING_SNAPSHOT_V2_AUDIT_PASS`

## Row Counts

- Race-entry rows: `204`
- Active entries: `198`
- Horse-rating source rows: `24`
- Valid horse-rating rows: `24`
- Snapshot rows: `204`

## Snapshot Status Counts

- `ENTRY_INACTIVE`: `6`
- `POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE`: `1`
- `SNAPSHOT_UNAVAILABLE`: `197`

## Audit Checks

- `required_fields_present`: `PASS`
- `row_population_exact`: `PASS`
- `natural_keys_unique`: `PASS`
- `snapshot_ids_unique`: `PASS`
- `strictly_prior_temporal_rule`: `PASS`
- `selected_values_finite`: `PASS`
- `available_rows_complete`: `PASS`
- `unavailable_rows_have_no_fake_rating`: `PASS`
- `evidence_complete`: `PASS`
- `candidate_hash_matches`: `PASS`
- `deterministic_rerun`: `PASS`

## Governance

- Builder: `EDGEIQ_RACE_ENTRY_HORSE_RATING_SNAPSHOT_V2`
- Method: `STRICTLY_PRIOR_LATEST_GOVERNED_HORSE_RATING_V1`
- Temporal rule: rating date must be strictly prior to target race date.
- Missing ratings remain explicitly unavailable.
- No zero, field-average, market-derived or manual rating is created.

- Candidate SHA256: `7b92fd0b0195165bd1858dfc5fd353ac1ff0bd0ee21dc697289ae860629977d7`
