# EDGEiQ Standard Time Observation Contract V1

## Purpose

This contract prevents Standard Time from mixing incompatible racing observations. The production runner warehouse remains a runner-aggregate compatibility contract. Standard Time uses detailed Results/segment observations only when the source grain is semantically valid.

## Observation Grain

The governed observation grain is one elapsed observation per race-runner per incremental sectional segment.

Only Racing.com `SPLIT` rows with valid segment boundaries and valid average speed are eligible. Racing.com `SECTIONAL` rows are cumulative distance points and are rejected for Standard Time unless a future governed builder explicitly converts them into non-overlapping incremental segments.

## Benchmark Key

The benchmark group is:

```text
track | race_distance_metres | segment_start_metres | segment_end_metres | segment_distance_metres
```

This key prevents a closing 200m segment from being grouped with a whole-race performance or a longer sectional interval.

## Minimum Sample Rule

The governed minimum sample remains 20 observations per benchmark group. The threshold is not changed in this recovery.

## Units

Distances are metres. Speed is metres per second. Elapsed time is seconds. Kilometres per hour may only be used after deterministic conversion to metres per second.

## Eligibility Rules

- Include only incremental segment observations.
- Require a stable race identity and runner identity.
- Require positive segment distance.
- Require positive average speed.
- Require plausible speed and elapsed-time units.
- Reject cumulative points, unresolved semantics, missing speed, missing boundaries, duplicate race-runner-segment rows, and synthetic rows.

## Contribution Limits

Each runner may contribute at most one observation to a benchmark group for the same race-runner-segment key. Multiple runners from the same race may contribute to the same benchmark group, but source race count must be reported for every Standard Time.

## Duplicate And Null Rules

Duplicate race-runner-segment observations are audit failures. Null track, race distance, segment boundaries, speed, or elapsed time make an observation ineligible.

## Normalisation Rules

Track names are uppercased and whitespace-normalised for benchmark keys. Segment labels are parsed as `STARTm-ENDm` or `STARTm-FINISH`, where finish is zero metres.

## Outlier Rules

Outlier handling is audit-first. This contract does not fabricate replacements. Invalid or implausible units are rejected or reported; the statistical Standard Time method is not changed merely to manufacture coverage.
