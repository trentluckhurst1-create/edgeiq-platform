# Race Entry Projection Row Funnel V1

First zero-row stage: `historical performance loaded`

## Stage Counts

- current race entries loaded: accepted `204` from `public\data\edgeiq_race_entry_fact_v1.csv` ()
- historical performance loaded: accepted `0` from `public\data\edgeiq_horse_performance_rating_fact_v1.csv` (NO_HISTORICAL_PERFORMANCE)
- historical observations date-filtered: accepted `0` from `public\data\edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv` (FUTURE_OR_SAME_RACE_OBSERVATION)
- declared context loaded: accepted `0` from `public\data\edgeiq_race_entry_performance_context_fact_v1.csv` (MISSING_REQUIRED_FIELD)
- context eligibility applied: accepted `0` from `public\data\edgeiq_race_entry_context_eligibility_fact_v1.csv` (MISSING_REQUIRED_FIELD)
- context parameter selection: accepted `0` from `public\data\edgeiq_race_entry_context_parameter_selection_fact_v1.csv` (BELOW_MINIMUM_HISTORY)
- context adjustment: accepted `0` from `public\data\edgeiq_race_entry_context_adjustment_fact_v1.csv` (MISSING_REQUIRED_FIELD)
- context adjusted performance: accepted `0` from `public\data\edgeiq_race_entry_context_adjusted_performance_fact_v1.csv` (MISSING_REQUIRED_FIELD)
- suitability components: accepted `0` from `public\data\edgeiq_race_entry_suitability_component_fact_v1.csv` (MISSING_REQUIRED_FIELD)
- projection aggregation: accepted `0` from `public\data\edgeiq_race_entry_suitability_aggregate_fact_v1.csv` (MISSING_REQUIRED_FIELD)
- final output validation: accepted `0` from `public\data\edgeiq_race_entry_projected_performance_fact_v1.csv` (UNKNOWN)
- EPI components: accepted `0` from `public\data\edgeiq_race_entry_epi_component_fact_v1.csv` (UNKNOWN)
- EPI output: accepted `0` from `public\data\edgeiq_race_entry_epi_fact_v1.csv` (UNKNOWN)

## History Depth Distribution

- 0 prior eligible runs: `204`
- 1 prior eligible runs: `0`
- 2 prior eligible runs: `0`
- 3 prior eligible runs: `0`
- 4 prior eligible runs: `0`
- 5+ prior eligible runs: `0`

Conclusion: canonical current race-entry and/or canonical horse rating source availability is the blocker when their accepted rows are zero. No projected-performance formula change is indicated by this funnel.
