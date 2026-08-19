# EDGEIQ Suitability V2 Method

## Baseline

The baseline is the horse's mean governed historical performance value using only observations strictly before the target race date.

## Components

- Track: exact canonical-track match.
- Distance: historical distance within 200 metres of today's distance.
- Surface: exact surface-group match.
- Track condition: historical condition number within one point.
- Barrier: historical barrier within two positions.
- Weight: historical carried weight within 2.0 kilograms.

For each component:

`component delta = matched historical mean - horse historical baseline mean`

The composite is the arithmetic mean of available component deltas.

Missing components remain blank and are never replaced with zero, market data, field averages or manual values.

This stage does not calculate Projected Performance or EPI.
