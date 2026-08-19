# EDGEIQ Race-Entry Context V2 Audit

Status: `EDGEIQ_RACE_ENTRY_CONTEXT_V2_AUDIT_PASS`

## Population

- Race-entry rows: `204`
- Stage 1 snapshot rows: `204`
- Context rows: `204`

## Participation

- `ACTIVE_ENTRY`: `188`
- `EMERGENCY`: `10`
- `SCRATCHED`: `6`

## Context Status

- `RACE_CONTEXT_AVAILABLE`: `198`
- `RACE_CONTEXT_RECORDED_ENTRY_INACTIVE`: `6`

## Audit Checks

- `race_entry_schema_valid`: `PASS`
- `stage_1_snapshot_schema_valid`: `PASS`
- `one_context_per_race_entry`: `PASS`
- `natural_keys_unique`: `PASS`
- `context_ids_unique`: `PASS`
- `snapshot_population_join_exact`: `PASS`
- `field_sizes_positive`: `PASS`
- `active_field_not_above_declared`: `PASS`
- `no_fake_historical_rating`: `PASS`
- `evidence_complete`: `PASS`
- `deterministic_rerun`: `PASS`

## Governance

- Builder: `EDGEIQ_RACE_ENTRY_CONTEXT_V2`
- Method: `FACTUAL_DECLARED_RACE_CONTEXT_ONLY_V1`
- This stage records factual race context only.
- Class and rail remain explicitly unavailable because they are absent from the current canonical race-entry schema.
- No context value is estimated or inferred.
- No suitability, projected performance or EPI is calculated in this stage.
- Candidate SHA256: `06f91ce9e800fceaae5e6674fd1bdb90ec6b312ab223923af69f1f7f0f86e59a`
