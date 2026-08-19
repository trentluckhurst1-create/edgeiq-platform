# EDGEiQ Performance Warehouse Snapshot Governance V0.2

## Corrected identity foundation

Performance IDs are generated from full race context:

- race date
- jurisdiction
- track
- race number
- provider race ID
- provider runner ID
- canonical horse ID

Provider identifiers are evidence and are not assumed to be globally unique.

## Snapshot requirements

A valid snapshot must have:

- unique performance IDs
- unique sectional evidence IDs
- deterministic ID reproducibility
- complete sectional foreign keys
- preserved legacy performance IDs
- all 89 known V0.1 collisions split
- valid evidence quality states
- immutable SHA-256 asset hashes

## Promotion

A successful snapshot remains unpromoted until Phase 1.1 explicitly materialises the canonical raw warehouse.
