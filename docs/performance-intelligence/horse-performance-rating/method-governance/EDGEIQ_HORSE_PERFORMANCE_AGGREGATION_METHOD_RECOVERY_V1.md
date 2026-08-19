# EDGEiQ Horse Performance Aggregation Method Recovery V1

Decision: `EXISTING_AGGREGATION_METHOD_PARTIALLY_RECOVERED`

## Recovered Logic
- Active aggregate builder: `scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py`
- Active rating fact builder: `scripts/build_edgeiq_horse_performance_rating_fact_v1.py`
- Rating method after aggregation: `DIRECT_HISTORICAL_AGGREGATE_VALUE`
- Aggregate formula: `aggregate_rating_value = weighted_sum(rating_base_value * weight) / total_weight`

## Historical Window
- Controlled by `lookback_days` from the governed aggregation parameter source.
- Current governed value: `UNRECOVERED`.

## Observation Ordering
- Observations are grouped by `canonical_horse_id`.
- Unique `race_date` values become as-of dates.
- Eligible observations are sorted descending by `race_date` and observation id.
- The newest observations are included up to `maximum_observations`.

## Eligibility And Minimums
- `rating_status` must be `OBSERVED_NORMALISED_GOVERNED`.
- `identity_status` must be `IDENTIFIED_GOVERNED`.
- Minimum observations are controlled by `minimum_observations` from source policy.
- Current governed minimum: `UNRECOVERED`.

## Weight Calculation
- `ARITHMETIC_MEAN` uses weight `1`.
- `WEIGHTED_ARITHMETIC_MEAN` with `EXPONENTIAL_HALF_LIFE` uses `0.5 ** (age_days / recency_half_life_days)`.
- Recency half-life value is governed source data and is currently unrecovered.

## Surface And Distance Treatment
No active surface or distance weighting/filter is applied by this aggregate builder. Surface/distance support is governed upstream by the performance/standard-time chain.

## Null And Temporal Treatment
- Required date/numeric/status/evidence fields fail hard if invalid.
- Future observations relative to an as-of date fail hard.
- As-of date includes observations on or before the as-of date in the aggregate builder. Predictive consumers must apply their stricter target-date rule later.

## Current Counts
- Horse observation rows: `0`
- Aggregation parameter fact rows: `0`
- Aggregation parameter source exists: `NO`
- Aggregation parameter source rows: `0`

## Unresolved Semantics
- The selected aggregation method is not recovered.
- `maximum_observations`, `lookback_days`, `minimum_observations`, recency method and half-life are not recovered.
- No historical governed source file was recovered from active repository paths or Git path history.

## Candidate Decision
No candidate aggregation parameter source was created. The executable formula is recovered, but its policy values are not fully governed.
