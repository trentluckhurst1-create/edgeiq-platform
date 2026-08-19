# EDGEIQ Race EPI Publication Snapshot Fact V1

## Status

Governed canonical race-level EPI publication snapshot.

## Purpose

Race EPI Publication Snapshot Fact V1 combines the final governed race-level
EPI distribution record with the final governed race-level EPI ordering
summary.

The snapshot publishes one deterministic row per race.

## Canonical inputs

- `edgeiq_race_epi_distribution_fact_v1.csv`
- `edgeiq_race_epi_ordering_summary_fact_v1.csv`

## Output grain

One row per:

`race_id + race_date`

## Distribution schema preservation

The existing governed Race EPI Distribution Fact may contain a larger metric
surface than this terminal publication layer needs to name individually.

To avoid guessing, renaming, omitting or silently changing governed
distribution metrics, the complete source distribution row is preserved as:

`source_distribution_record_json`

The JSON must be:

- complete
- deterministic
- UTF-8
- sorted by key
- compact
- derived directly from the governed source row

Its SHA256 is published as:

`source_distribution_record_sha256`

## Directly published ordering-summary fields

- ordered EPI population count
- distinct EPI count
- unique-EPI entry count
- tied-EPI entry count
- tie-group count
- largest tie-group size
- top EPI
- second distinct EPI availability
- second distinct EPI
- top-to-second EPI-gap availability
- top-to-second EPI gap
- top-EPI tie-group size
- top-EPI tie status

## Reconciliation requirements

- distribution and ordering-summary race populations must match exactly
- one distribution row must exist per race
- one ordering-summary row must exist per race
- race identity and race date must match
- population counts must reconcile where the distribution source exposes a
  recognised population-count field
- all source identities and evidence hashes must be complete
- all source publication, reconciliation and status fields must be governed
- ordering-summary metrics must remain unchanged
- source distribution JSON must reconstruct the complete source row exactly

## Recognised distribution population fields

The builder checks these names in order:

- `eligible_epi_population_count`
- `epi_population_count`
- `race_epi_population_count`
- `distribution_population_count`
- `runner_count`
- `entry_count`

If none exists, population reconciliation is recorded as:

`NOT_EXPOSED_BY_SOURCE_CONTRACT`

No population value is invented.

## Governance

Published rows use:

- `RACE_EPI_SNAPSHOT_PUBLISHED`
- `RACE_EPI_SNAPSHOT_RECONCILED`
- `GOVERNED_RACE_EPI_PUBLICATION_SNAPSHOT`

## Deterministic identity

`race_epi_publication_snapshot_id` is derived from:

- contract version
- race identity
- race date
- distribution source identity
- ordering-summary source identity
- publication decision

## Deterministic evidence

Evidence includes:

- snapshot identity
- race identity
- race date
- complete distribution record hash
- source distribution identity
- source distribution evidence
- source ordering-summary identity
- source ordering-summary evidence
- all directly published ordering-summary metrics
- population reconciliation status
- governance decisions
- source lineage

## Prohibited behaviour

This fact must not calculate or publish:

- probability
- implied probability
- fair price
- market price
- market edge
- expected value
- confidence
- prediction
- recommendation
- selection
- betting advice
- staking
- bookmaker comparison
- value classification

## Empty-source handling

Both canonical sources may be empty only when both are empty.

If one source is empty and the other is not, the build must fail closed.

No synthetic races may be created.
