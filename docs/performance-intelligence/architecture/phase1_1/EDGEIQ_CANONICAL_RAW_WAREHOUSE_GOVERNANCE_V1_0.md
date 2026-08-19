# EDGEiQ Canonical Raw Warehouse Governance V1.0

## Warehouse boundary

The canonical raw warehouse contains immutable evidence only.

It does not contain:

- benchmarks
- ratings
- fingerprints
- patterns
- React calculations
- presentation fields

## Snapshot rule

Every warehouse snapshot is stored under its deterministic snapshot ID.

Existing snapshots are never overwritten.

A source byte change creates a new snapshot.

## Required assets

- canonical performance evidence
- canonical sectional evidence
- asset catalogue
- materialisation checks
- warehouse manifest
- integrity manifest

## Product separation

This warehouse is not connected directly to the production application.

Future query and intelligence engines consume governed snapshots and produce separately versioned outputs.
