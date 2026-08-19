# EDGEIQ Race Entry Context Adjustment Fact V1

## Status

Governed deterministic context-adjustment application layer.

## Purpose

Race Entry Context Adjustment Fact V1 applies the exact governed context
parameter selected by Race Entry Context Parameter Selection Fact V1.

It preserves the historical rating unchanged and publishes each governed
adjustment component separately.

## Architecture

Race Entry Performance Context Fact V1  
+ Race Entry Context Parameter Selection Fact V1  
+ Context Parameter Registry V1  
→ Race Entry Context Adjustment Fact V1  
→ Future Context-Adjusted Performance Fact  
→ Future Suitability Facts  
→ Future EPI Engine

## Canonical inputs

### Selection input

`public/data/edgeiq_race_entry_context_parameter_selection_fact_v1.csv`

### Performance-context input

`public/data/edgeiq_race_entry_performance_context_fact_v1.csv`

### Governed parameter registry

`public/data/edgeiq_context_parameter_registry_v1.csv`

The performance-context input and parameter registry are required only when
selection rows exist.

When the selection input contains zero rows:

- downstream inputs are not required
- output contains its governed header
- output contains zero data rows
- audit must PASS

## Output grain

Exactly one context-adjustment decision row per governed parameter-selection
row.

Natural key:

`race_entry_context_parameter_selection_id`

## Historical rating

The source historical rating is preserved as:

`historical_rating_value`

It must not be overwritten.

## Governed adjustment components

V1 permits:

- distance_adjustment
- class_adjustment
- track_adjustment
- track_configuration_adjustment
- track_condition_adjustment
- surface_adjustment
- barrier_adjustment
- weight_adjustment
- field_size_adjustment

## Total context adjustment

When an exact governed parameter is selected:

`total_context_adjustment`

is the exact decimal sum of the nine governed adjustment components.

No hidden component is permitted.

## Context-adjusted rating

This fact does not publish a context-adjusted rating.

That belongs in a separate future fact.

## Application decisions

`context_adjustment_application_decision` uses:

- `ADJUSTMENT_APPLIED`
- `PARAMETER_NOT_AVAILABLE`
- `CONTEXT_INELIGIBLE`

## Application statuses

- `GOVERNED_CONTEXT_ADJUSTMENT_APPLIED`
- `GOVERNED_CONTEXT_PARAMETER_NOT_AVAILABLE`
- `CONTEXT_NOT_ELIGIBLE_FOR_ADJUSTMENT`

## Parameter-selected rows

When the source decision is `PARAMETER_SELECTED`:

- the selected parameter must exist
- the selected parameter must be governed
- the parameter ID must match exactly
- all nine adjustment components must be finite decimals
- total context adjustment is calculated as their exact sum
- application decision is `ADJUSTMENT_APPLIED`

## Parameter-not-available rows

When the source decision is `PARAMETER_NOT_AVAILABLE`:

- no registry lookup is performed
- all adjustment fields are blank
- application decision remains `PARAMETER_NOT_AVAILABLE`

## Context-ineligible rows

When the source decision is `CONTEXT_INELIGIBLE`:

- no registry lookup is performed
- all adjustment fields are blank
- application decision remains `CONTEXT_INELIGIBLE`

## Missing and invalid parameter behaviour

The builder must fail closed when a selected parameter:

- is absent
- is duplicated
- is not governed
- lacks lineage
- contains a blank adjustment component
- contains a non-numeric adjustment component
- contains a non-finite adjustment component

## Deterministic identity

`race_entry_context_adjustment_id` is derived from:

- contract version
- race-entry context parameter-selection ID
- selected parameter ID or explicit absence token
- application decision

## Evidence identity

The evidence SHA-256 is derived from:

- deterministic adjustment ID
- source selection evidence SHA-256
- source context evidence SHA-256
- source parameter evidence SHA-256
- historical rating value
- every adjustment component
- total context adjustment
- application decision
- application status

## Prohibited behaviour

The builder must not:

- calculate suitability
- calculate EPI
- calculate ERI
- calculate runner rank
- calculate race rank
- calculate fair price
- use market price
- calculate market edge
- calculate predictions
- calculate a context-adjusted rating
- invent an adjustment
- estimate an adjustment
- interpolate an adjustment
- select a nearest parameter
- use a generic fallback parameter
- silently replace a missing value
- use future horse performances
