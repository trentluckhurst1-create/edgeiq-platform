# EDGEIQ Race ERI Fact V1

## Status

Governed deterministic warehouse fact.

## Purpose

Race ERI Fact V1 publishes one governed EDGEiQ Race Index value per eligible
race.

ERI represents the projected strength of the complete governed eligible field.

ERI is a race-level measure.

It must not modify, replace, scale, weight, rank, or reinterpret any runner's
projected-performance value.

## Architecture

Race Entry Projected Performance Fact V1  
→ Race ERI Parameter Fact V1  
→ Race ERI Fact V1  
→ Future Race Entry ERI Context Fact  
→ Future EPI Component Facts  
→ Future Final EPI Fact

## Canonical inputs

### Projected performance

`public/data/edgeiq_race_entry_projected_performance_fact_v1.csv`

### ERI parameter

`public/data/edgeiq_race_eri_parameter_fact_v1.csv`

## Output grain

Exactly one governed row per eligible:

`race_id`

## V1 methodology

The only authorised V1 methodology is:

`FIELD_MEAN_PROJECTED_PERFORMANCE`

## Canonical calculation

For each eligible race:

`projected_performance_sum =`

`sum(projected_performance_value)`

`projected_performance_mean_unrounded =`

`projected_performance_sum / eligible_runner_count`

`eri_value =`

`projected_performance_mean_unrounded`

rounded to the governed parameter scale using the governed rounding mode.

V1 parameters are:

- output decimal places: `6`
- rounding mode: `ROUND_HALF_EVEN`
- minimum eligible runner count: `2`

## Input eligibility

Only projected-performance rows with all three governed states may enter ERI:

- `PROJECTED_PERFORMANCE_PUBLISHED`
- `PROJECTED_PERFORMANCE_RECONCILED`
- `GOVERNED_PROJECTED_PERFORMANCE`

Unsupported or mixed states are fatal.

## Race grouping

Rows are grouped by:

`race_id`

Each race must have exactly one:

- race date
- selected ERI parameter
- projected-performance row per race entry
- projected-performance row per projected-performance ID

## Complete-field interpretation

Race ERI Fact V1 consumes every governed projected-performance row published
for the race.

No governed projected-performance row may be dropped.

The source membership SHA-256 must be calculated from the complete sorted set
of projected-performance IDs.

The source evidence SHA-256 must be calculated from the complete sorted set of
projected-performance evidence hashes.

## Minimum field size

A race requires at least:

`2`

governed projected-performance rows.

Races below the minimum do not publish ERI.

They are counted as:

`BELOW_MINIMUM_FIELD_SIZE`

This is governed non-publication, not an estimated ERI.

## Descriptive statistics

The fact publishes:

- eligible runner count
- projected-performance sum
- projected-performance mean, unrounded
- projected-performance mean, governed scale
- projected-performance median
- projected-performance minimum
- projected-performance maximum
- projected-performance range
- ERI value

Only the governed arithmetic mean becomes ERI in V1.

The other statistics are descriptive and do not alter ERI.

## Median

For an odd field size:

`median = middle ordered value`

For an even field size:

`median = mean of the two middle ordered values`

Median arithmetic must use exact decimal values.

## Decimal policy

The following governed presentation values use the selected parameter scale and
rounding mode:

- projected-performance mean
- projected-performance median
- projected-performance minimum
- projected-performance maximum
- projected-performance range
- ERI value

The following fields preserve unrounded arithmetic:

- projected-performance sum
- projected-performance mean unrounded

## Parameter selection

For each race date, exactly one active global ERI parameter must apply.

A parameter is active when:

- `effective_from_date <= race_date`
- `effective_to_date` is blank, or
- `race_date <= effective_to_date`

The builder must fail when:

- no parameter applies
- multiple parameters apply
- the parameter scope is not `GLOBAL`
- the methodology is unsupported
- the rounding mode is unsupported
- the parameter decision is not authorised
- the parameter status is not governed

## Published decision

Published rows use:

`ERI_PUBLISHED`

## Published status

Published rows use:

`GOVERNED_RACE_ERI`

## Methodology reconciliation decision

Published rows use:

`ERI_METHOD_RECONCILED`

## Deterministic identity

`race_eri_id` is derived from:

- contract version
- race ID
- race date
- selected ERI parameter ID
- ERI publication decision

## Membership evidence

`source_projected_performance_id_set_sha256` is derived from the sorted complete
set of source projected-performance IDs.

`source_projected_performance_evidence_set_sha256` is derived from the sorted
complete set of source projected-performance evidence SHA-256 values.

## Fact evidence

`race_eri_evidence_sha256` is derived from:

- deterministic ERI ID
- race ID
- race date
- selected parameter identity and evidence
- complete source ID-set SHA-256
- complete source evidence-set SHA-256
- eligible runner count
- sum
- unrounded mean
- governed mean
- median
- minimum
- maximum
- range
- ERI value
- methodology
- publication decision
- reconciliation decision
- status

## Fail-closed rules

The builder must fail when:

- a required source file is missing
- a required source field is missing
- a race ID is blank
- a race date is blank or invalid
- a race contains conflicting dates
- a race-entry ID is blank
- a race-entry ID is duplicated within a race
- a projected-performance ID is blank
- a projected-performance ID is duplicated
- a projected-performance value is blank
- a projected-performance value is non-numeric
- a projected-performance value is non-finite
- source evidence is missing
- source builder lineage is missing
- an unsupported projected-performance state appears
- no ERI parameter applies
- multiple ERI parameters apply
- aggregate arithmetic is not exact
- deterministic identities collide

## Governed non-publication

A race below the minimum eligible runner count does not publish an ERI row.

The builder and audit report:

- projected race count
- eligible ERI race count
- below-minimum race count
- published ERI row count

## Prohibited behaviour

Race ERI Fact V1 must not:

- change projected-performance values
- calculate runner rankings
- calculate race rankings
- calculate EPI
- calculate probabilities
- calculate fair prices
- read market prices
- calculate market edge
- calculate confidence
- generate predictions
- generate forecasts
- apply hidden weighting
- apply market-derived weighting
- use machine-learning models
