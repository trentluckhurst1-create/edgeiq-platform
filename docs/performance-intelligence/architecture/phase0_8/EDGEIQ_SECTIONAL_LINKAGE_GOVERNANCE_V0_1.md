# EDGEiQ Sectional Linkage Governance V0.1

## Automatic promotion

Only the following linkage may become automatically eligible for canonical migration review:

`DATE_TRACK_RACE_HORSE_NORMALISED`

It must also pass direct validation against the selected canonical performance record.

## Conditional linkage

The following may be retained as linkage evidence but require secondary evidence before canonical promotion:

- `DATE_TRACK_HORSE_NORMALISED`
- `DATE_RACE_HORSE_NORMALISED`

Secondary evidence may include:

- provider runner identity
- provider race identity
- official race distance
- official finish position
- trainer
- jockey
- barrier
- official sectional payload reference

## Research-only linkage

`DATE_HORSE_ONLY_UNIQUE`

This method may support research and gap analysis but must not automatically create canonical sectional evidence.

## Unresolved evidence

Rows remain unresolved when:

- no result date exists
- the horse is absent from the result date
- the track cannot be reconciled
- the race number differs
- the horse identity differs within the same race
- multiple candidate performances remain

No fuzzy name match or alias candidate may be automatically promoted.
