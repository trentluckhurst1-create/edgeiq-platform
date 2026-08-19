# EDGEiQ Performance Identity Natural Key V0.2

## Failure corrected

The V0.1 performance identity relied on provider race and runner identities that were reused across separate meetings.

This created 89 false performance collisions.

## V0.2 natural key

A performance identity now contains:

- official race date
- jurisdiction or state
- canonical track
- official race number
- provider race identity
- provider runner identity
- canonical horse identity

## Permanent rule

A provider identifier is evidence, not automatically a globally permanent canonical identity.

No two different race dates or race numbers may share one canonical performance ID.

## Legacy lineage

The former performance ID remains stored as `legacy_performance_id`.

Every V0.1-to-V0.2 mapping is preserved in the remap table.

No historical source row is deleted.
