# EDGEiQ Horse Performance Rating Grain Audit V1

Grain decision: `ROLLING_HORSE_AS_OF_DATE_RATING_FACT`

## Contract-Derived Grain
- Parsed primary key: `horse_performance_rating_id; source aggregate grain canonical_horse_id + rating_as_of_date + aggregation_parameter_id`
- Rating builder consumes aggregate rows: `True`
- Aggregate builder emits unique as-of dates per horse: `True`
- The active contract does not emit one row per sectional segment.
- The active rating fact is not a horse-distance profile, horse-surface profile, campaign aggregate, or race-entry row.
- The active grain is one governed horse-performance rating row per source horse-performance aggregate row, which is business-keyed by canonical horse, aggregate/rating as-of date, governed aggregation parameter, and included observations.

## Duplicate Checks
- `observation` on `horse_performance_observation_id`: rows=0, duplicate_rows=0, status=`NOT_TESTABLE_EMPTY_SOURCE`
- `aggregate` on `horse_performance_aggregate_id`: rows=0, duplicate_rows=0, status=`NOT_TESTABLE_EMPTY_SOURCE`
- `aggregate_horse_date_parameter` on `canonical_horse_id;aggregate_as_of_date;horse_performance_aggregation_parameter_id`: rows=0, duplicate_rows=0, status=`NOT_TESTABLE_EMPTY_SOURCE`
- `rating` on `horse_performance_rating_id`: rows=0, duplicate_rows=0, status=`NOT_TESTABLE_EMPTY_SOURCE`
- `rating_horse_date_parameter` on `canonical_horse_id;rating_as_of_date;horse_performance_aggregation_parameter_id`: rows=0, duplicate_rows=0, status=`NOT_TESTABLE_EMPTY_SOURCE`

## Finding
The current empty production files make duplicate-key validation not testable, but the builder contract is clear. Do not build per-segment ratings unless the contract changes. The next buildable rating fact should preserve the rolling horse/as-of-date aggregate grain.
