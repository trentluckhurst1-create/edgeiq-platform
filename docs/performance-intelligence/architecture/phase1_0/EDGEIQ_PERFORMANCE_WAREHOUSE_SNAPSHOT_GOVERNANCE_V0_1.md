# EDGEiQ Performance Warehouse Snapshot Governance V0.1

## Snapshot identity

A warehouse snapshot receives one deterministic `warehouse_snapshot_id`.

The natural key contains:

- snapshot specification version
- canonical performance identity file SHA-256
- canonical sectional evidence file SHA-256

Any byte-level change creates a different snapshot identity.

## Mandatory snapshot manifest

Every snapshot records:

- snapshot ID
- source file paths
- source SHA-256 values
- row counts
- schema columns
- date coverage
- primary-key results
- foreign-key results
- deterministic-ID results
- quality-state contract results
- audit version
- generated timestamp

## Promotion rule

A snapshot cannot be promoted when any mandatory audit check fails.

## Immutability

Existing snapshot manifests are never overwritten.

A new source or engine run creates a new snapshot manifest.

## Product separation

This snapshot is not a React feed.

React and application services must consume governed query products built downstream from canonical evidence.
