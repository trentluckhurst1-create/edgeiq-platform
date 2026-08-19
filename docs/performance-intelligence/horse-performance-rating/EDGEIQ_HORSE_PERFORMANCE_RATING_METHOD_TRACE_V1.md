# EDGEiQ Horse Performance Rating Method Trace V1

Decision: `EXISTING_GOVERNED_FORMULA_FOUND`

## Formula Identifier
- Horse rating fact builder: `edgeiq_horse_performance_rating_fact_v1.0.0`
- Horse rating method: `DIRECT_HISTORICAL_AGGREGATE_VALUE`
- Aggregate builder: `edgeiq_horse_performance_aggregate_fact_v1.0.0`
- Observation builder: `edgeiq_horse_performance_observation_fact_v1.0.0`
- Base rating builder: `edgeiq_performance_rating_base_fact_v1.0.0`
- Normalisation builder: `edgeiq_performance_normalisation_fact_v1.0.0`
- Base PI builder: `edgeiq_performance_intelligence_base_fact_v1.0.0`
- Contract version: `1.0.0`

## Governed Method Chain
1. `edgeiq_lengths_versus_standard_fact_v1.csv` is converted into `edgeiq_performance_intelligence_base_fact_v1.csv` using `DIRECT_GOVERNED_LENGTHS_VERSUS_STANDARD`.
2. `raw_performance_lengths` is normalised by `LINEAR_CENTRE_AND_SCALE`: `(raw_performance_lengths - centre_value) / scale_value`.
3. `edgeiq_performance_rating_base_fact_v1.csv` uses `DIRECT_NORMALISED_PERFORMANCE_VALUE`, where `rating_base_value = normalised_performance_value`.
4. `edgeiq_horse_performance_observation_fact_v1.csv` maps the source `winner_horse_name` to a governed canonical horse identity and carries `rating_base_value` forward as an observed governed horse-performance observation.
5. `edgeiq_horse_performance_aggregate_fact_v1.csv` groups observations by canonical horse and as-of date, applies the governed aggregation parameter effective on that date, and calculates `aggregate_rating_value`.
6. `edgeiq_horse_performance_rating_fact_v1.csv` uses `DIRECT_HISTORICAL_AGGREGATE_VALUE`, where `horse_performance_rating_value = aggregate_rating_value`.

## Required Inputs
- Lengths versus standard: `lengths_versus_standard`, race time, standard time, seconds per length, race key/date/track/distance, winner horse name, governed evidence hash.
- Normalisation parameters: `centre_value`, `scale_value`, method `LINEAR_CENTRE_AND_SCALE`, effective date range, parameter evidence hash.
- Horse identity map: exact normalised source horse name to canonical horse id/name with approved status and evidence hash.
- Horse aggregation parameters: aggregation method, maximum observations, lookback days, minimum observations, recency weighting method, optional recency half-life, effective date range, parameter evidence hash.

## Optional Inputs
- No optional inputs are consumed by the active horse rating fact builder itself.
- The aggregate builder supports `ARITHMETIC_MEAN/NONE` and `WEIGHTED_ARITHMETIC_MEAN/EXPONENTIAL_HALF_LIFE` parameter combinations when governed parameters are available.

## Normalisation Method
- `LINEAR_CENTRE_AND_SCALE` in `build_edgeiq_performance_normalisation_fact_v1.py`.
- Formula: `(raw_performance_lengths - centre_value) / scale_value`.

## Sign Convention
- Positive `lengths_versus_standard` is interpreted as `FASTER_THAN_STANDARD`.
- Negative `lengths_versus_standard` is interpreted as `SLOWER_THAN_STANDARD`.
- Zero is interpreted as `EQUAL_TO_STANDARD`.
- Higher normalised values therefore mean stronger historical performance versus standard.

## Rating Scale
- The active rating scale is the normalised performance scale produced by `LINEAR_CENTRE_AND_SCALE` and then passed through to the horse aggregate and rating fact.
- No market price, finish-position rank, prize money, live entry, pricing, V6.1 or V7.2G2 value is used by this governed horse-performance rating fact chain.

## Missing-Input Handling
- Missing canonical input files raise hard failures.
- Missing required schema fields raise hard failures.
- Empty upstream rows write header-only downstream outputs for base/normalisation/observation/aggregate/rating stages.
- Missing horse identity map rows raise hard failures when base rows exist.
- Missing effective aggregation parameters raise hard failures when observations exist.

## Minimum Observation Requirement
- Controlled by `edgeiq_horse_performance_aggregation_parameter_fact_v1.csv` field `minimum_observations`.
- Current parameter file rows: `0`.
- Current parameter file fields: `horse_performance_aggregation_parameter_id, aggregation_method, maximum_observations, lookback_days, minimum_observations, recency_weighting_method, recency_half_life_days, aggregation_model_version, parameter_status, effective_from_date, effective_to_date, evidence_reference, source_evidence_sha256, parameter_evidence_sha256, builder_version, contract_version, built_at_utc`.
- Because the parameter file is currently header-only, the governed threshold value is not available in data even though the builder supports it.

## Outlier Handling
- No separate outlier trimming is implemented in the active horse rating fact or aggregate builder.
- Numeric values must be finite; non-finite values fail the build.

## Surface Treatment
- The active horse rating fact builder has no explicit surface filter.
- Surface compatibility is governed upstream by the lengths-versus-standard and standard-time chain.

## Distance Treatment
- The active horse rating fact builder has no explicit distance filter.
- Distance is required upstream and sorted/validated as positive metres in base builders.
- Distance support is governed upstream by standard-time and lengths-versus-standard availability.

## Governance Finding
An existing governed method is present and recoverable from active scripts. The current zero-row state is not caused by an absent formula. The critical dependency risk is upstream data/parameter availability, especially empty horse aggregation parameters and empty base/observation/aggregate files.
