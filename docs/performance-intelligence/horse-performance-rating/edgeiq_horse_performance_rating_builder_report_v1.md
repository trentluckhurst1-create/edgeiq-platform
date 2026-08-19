# EDGEiQ Horse Performance Rating Builder Trace V1

Required classification: `ACTIVE_BUILDER_INPUT_EMPTY`

## Active Builder
- Path: `scripts\build_edgeiq_horse_performance_rating_fact_v1.py`
- Entry function: `main`
- Input sources: `edgeiq_horse_performance_aggregate_fact_v1.csv`
- Production path: `edgeiq_horse_performance_rating_fact_v1.csv`
- Candidate path: `NOT_DEFINED`
- Formula version: `edgeiq_horse_performance_rating_fact_v1.0.0`
- Rating method: `DIRECT_HISTORICAL_AGGREGATE_VALUE`
- Contract version: `1.0.0`

## Source Row Counts
- `edgeiq_performance_rating_base_fact_v1.csv`: exists=YES, rows=0, size=526 bytes
- `edgeiq_horse_performance_observation_fact_v1.csv`: exists=YES, rows=0, size=576 bytes
- `edgeiq_horse_performance_aggregate_fact_v1.csv`: exists=YES, rows=0, size=633 bytes
- `edgeiq_horse_performance_rating_fact_v1.csv`: exists=YES, rows=0, size=511 bytes
- `edgeiq_race_entry_projected_performance_fact_v1.csv`: exists=YES, rows=0, size=947 bytes

## Required Builder Fields

- `horse_performance_aggregate_id`
- `canonical_horse_id`
- `canonical_horse_name`
- `aggregate_as_of_date`
- `horse_performance_aggregation_parameter_id`
- `aggregation_method`
- `included_observation_count`
- `aggregate_rating_value`
- `aggregate_status`
- `aggregation_model_version`
- `horse_performance_aggregate_evidence_sha256`
- `builder_version`

## Role Counts
- `ACTIVE_RATING_AUDIT`: 1
- `ACTIVE_RATING_BUILDER`: 1
- `CONTRACT_OR_SCHEMA`: 9
- `DOWNSTREAM_PROJECTED_PERFORMANCE_AUDIT`: 2
- `DOWNSTREAM_PROJECTED_PERFORMANCE_BUILDER`: 1
- `KEYWORD_REFERENCE`: 2
- `PROJECTED_PERFORMANCE_REFERENCE`: 12
- `REFERENCE`: 13
- `UPSTREAM_HORSE_PERFORMANCE_AUDIT`: 5
- `UPSTREAM_HORSE_PERFORMANCE_BUILDER`: 4

## Finding
The governed active rating builder exists and writes `edgeiq_horse_performance_rating_fact_v1.csv` from `edgeiq_horse_performance_aggregate_fact_v1.csv` using `DIRECT_HISTORICAL_AGGREGATE_VALUE`.
The current zero-row production rating fact is explained at trace level by an empty upstream aggregate input, not by a missing active rating builder.
The next required checkpoint is therefore the row funnel through performance rating base, horse observation, and horse aggregate builders to identify the first zero-row stage.
