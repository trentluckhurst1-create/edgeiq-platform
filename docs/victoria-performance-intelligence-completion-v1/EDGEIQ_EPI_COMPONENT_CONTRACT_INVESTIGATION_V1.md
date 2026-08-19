# EDGEIQ EPI Component Contract Investigation V1

Built: 2026-07-30T00:04:18Z

## Status
BLOCKED_EPI_COMPONENT_CONTRACT

## Snapshot Rows
5

## Performance Context Rows
5

## Complete Context Eligible Rows
5

## Complete Context Ineligible Rows
0

## Projected Performance Rows
0

## Suitability Aggregate Rows
0

## Eri Context Rows
0

## Epi Component Rows
0

## Epi Rows
0

## Mandatory Epi Inputs
```json
{
  "HISTORICAL_PERFORMANCE": "public/data/edgeiq_race_entry_projected_performance_fact_v1.csv",
  "RACE_CONTEXT": "public/data/edgeiq_race_entry_eri_context_fact_v1.csv",
  "SUITABILITY": "public/data/edgeiq_race_entry_suitability_aggregate_fact_v1.csv"
}
```

## First Failing Stage
CONTEXT_PARAMETER_SELECTION

## First Failing Join
race_entry_horse_performance_snapshot -> race_entry_performance_context -> context eligibility now succeeds; exact governed context parameter selection fails closed because no governed context parameter registry rows are available

## Primary Rejection Reason
PARAMETER_NOT_AVAILABLE

## Rejection Counts
```json
{
  "PARAMETER_NOT_AVAILABLE": 5
}
```

## Method Repair Applied
```json
[
  "Current race-entry schema adapter added to performance context builder",
  "Empty-input guard added to parameter selection builder",
  "Empty-input guard added to context adjustment builder",
  "Official visible-page race context source added for race_class_code and rail_position",
  "Header-only governed context parameter registry added so missing empirical parameters fail closed without fabricated adjustments"
]
```

## No Components Fabricated
True

## Pricing Probability V6 V7 Changed
False
