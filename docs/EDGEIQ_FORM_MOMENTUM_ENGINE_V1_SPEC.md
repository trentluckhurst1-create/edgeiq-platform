# EDGEIQ Form Momentum Engine V1

## Purpose

Form Momentum answers whether the runner's current performance trajectory is improving, holding or declining at the point of the selected race.

## Point-In-Time Definition

Only historical rows with `race_date < selected race_date` are eligible. Selected-race results and future results are excluded.

## Evidence Windows

V1 uses the latest as-of runs, with a preferred window of five starts. It compares the most recent two valid evidence runs with the older valid evidence in that window.

## Approved Evidence

Selected evidence families are:

- Historical EPI trajectory where `epi_post` exists.
- Benchmark-adjusted sectional finish trajectory where available.
- Margin trajectory.
- Recency and spacing.
- Comparable distance and condition context.

Finishing position alone is never sufficient.

## Minimum Runs

At least three as-of historical runs are required, with at least two valid numeric performance evidence points from EPI, benchmarked sectionals or margin. First starters remain blank.

## Output Scale

The public value is centred around 0:

- Positive means improving.
- Near zero means holding.
- Negative means declining.

The direction labels are `IMPROVING`, `HOLDING` and `DECLINING`.

## Missing Data

Missing values are ignored and never converted to zero. A runner is blank when insufficient valid evidence exists.

## As-Of Protections

The builder records future/selected rows excluded and emits an as-of audit. React does not calculate momentum.

## Exclusions

Form Momentum is not last-five finishing positions, not a market move, not current EPI, not one last-start rating and not a subjective confidence score.
