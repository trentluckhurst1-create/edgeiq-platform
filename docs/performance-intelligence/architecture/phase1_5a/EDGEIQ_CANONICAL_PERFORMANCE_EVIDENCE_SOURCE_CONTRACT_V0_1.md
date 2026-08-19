# EDGEiQ Canonical Performance Evidence Source Contract V0.1

## Purpose

The immutable raw warehouse currently contains canonical identity and lineage.

Phase 1.5A verifies the upstream evidence required to materialise official performance facts.

## Lineage rule

Every canonical performance fact must be traceable to:

- immutable performance ID
- source evidence ID
- source file
- source row number
- source file hash
- source field
- evidence version
- materialisation version

## Performance facts

Eligible raw facts include:

- distance
- class
- going
- rail
- official time
- finish position
- official margin
- barrier
- weight
- jockey
- trainer
- starting price

## Sectional evidence

Speed-derived fields and official split times are separate evidence types.

Speed estimates must not be relabelled as official sectional times.

If official split times are absent, the canonical warehouse records them as unavailable.

## Prohibited behaviour

The materialiser may not:

- estimate missing distance
- infer class from race name
- fabricate official time
- convert speed into an official split
- invent rail or going
- silently drop unavailable fields

## Next phase

Phase 1.5B may materialise only source fields that pass this contract.
