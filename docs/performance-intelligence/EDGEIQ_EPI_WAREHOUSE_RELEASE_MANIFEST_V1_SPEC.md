# EDGEiQ EPI Warehouse Release Manifest V1

## Status

Final governed release-control layer for the canonical EDGEiQ EPI Warehouse V1.

## Purpose

The EPI Warehouse Release Manifest V1 verifies, inventories and cryptographically
records the complete governed EPI publication chain.

It does not calculate EPI.

It does not change any source fact.

It does not create synthetic warehouse records.

## Governed warehouse chain

1. Race Entry EPI Fact V1
2. Race EPI Distribution Fact V1
3. Race Entry EPI Relative Context Fact V1
4. Race Entry EPI Ordering Fact V1
5. Race EPI Ordering Summary Fact V1
6. Race Entry EPI Publication Snapshot Fact V1
7. Race EPI Publication Snapshot Fact V1

## Required artifacts per governed layer

Each layer must expose:

- approved specification
- governed contract
- deterministic builder
- independent auditor
- published fact
- PASS audit

## Required verification

For every governed layer:

- all six artifacts must exist
- source fact must have a CSV header
- audit JSON must parse
- audit status must equal `PASS`
- contract JSON must parse
- contract name must match the governed layer
- every artifact must be tracked by Git
- every artifact must be unmodified relative to the current Git index and HEAD
- each artifact must receive a SHA256 hash
- fact row count must be recorded
- fact column count must be recorded
- audit counts must be retained
- source commit must be recorded

## Terminal reconciliation

The final release must establish:

- Race Entry EPI Fact population equals Race Entry EPI Publication Snapshot
  population.
- Race Entry EPI Ordering Fact population equals Race Entry EPI Publication
  Snapshot population.
- Race EPI Distribution Fact population equals Race EPI Ordering Summary Fact
  population.
- Race EPI Distribution Fact population equals Race EPI Publication Snapshot
  population.
- Race Entry EPI Publication Snapshot race population equals Race EPI
  Publication Snapshot population.
- Natural race-entry identities are unique in the runner publication snapshot.
- Natural race identities are unique in the race publication snapshot.
- Every runner publication race exists in the race publication snapshot.
- Every race publication race has at least one runner publication row.

## Source Git state

The builder records:

- source HEAD commit
- source branch
- source commit timestamp
- source repository root
- governed source artifact cleanliness

The release-manifest commit itself is created after the manifest is built and
audited. Therefore, `source_git_head` represents the final governed warehouse
source commit immediately before the release-manifest commit.

## Manifest identity

`epi_warehouse_release_id` is deterministic from:

- manifest contract version
- warehouse name
- warehouse version
- source Git HEAD
- ordered governed-layer evidence
- terminal reconciliation evidence
- release decision

## Release governance

A successful manifest uses:

- `EPI_WAREHOUSE_V1_RELEASED`
- `EPI_WAREHOUSE_V1_RECONCILED`
- `GOVERNED_EPI_WAREHOUSE_RELEASE`

## Prohibited behaviour

The manifest must not publish or calculate:

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
- tip
- bet
- staking
- bookmaker comparison
- value classification

## Release decision

The warehouse is release-ready only when every required validation passes.

Any missing artifact, failed audit, dirty governed source, duplicate natural
key, population mismatch or hash mismatch must fail the release.

## Mandatory non-empty release control

A governed warehouse release requires at least one row in every governed EPI
fact and publication layer.

An entirely empty but internally consistent chain is not a releasable
warehouse. Vacuous reconciliation is prohibited.

The release builder and independent auditor must fail when:

- runner publication rows equal zero
- race publication rows equal zero
- runner publication race count equals zero
- any required governed source fact contains zero rows

