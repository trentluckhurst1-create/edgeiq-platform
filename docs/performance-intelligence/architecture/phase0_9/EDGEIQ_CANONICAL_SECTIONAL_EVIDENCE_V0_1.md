# EDGEiQ Canonical Sectional Evidence V0.1

## Purpose

This prototype creates immutable canonical sectional-evidence rows from only the strongest validated linkage method.

## Promotion rule

A source sectional row is eligible only when:

1. It has a deterministic `performance_id`.
2. It was linked using `DATE_TRACK_RACE_HORSE_NORMALISED`.
3. Date, canonical track, race number and canonical horse all validate against the performance identity record.
4. The source row is preserved unchanged through `raw_*` fields.
5. A source file SHA-256 is recorded.
6. A deterministic `performance_sectional_id` is generated.
7. Evidence version, linkage version and migration version are recorded.

## Excluded from this prototype

The following remain outside canonical migration:

- conditional date-track-horse links
- conditional date-race-horse links
- date-horse-only research links
- ambiguous links
- unlinked rows
- validation mismatches

## Track aliases added

- `VALLEY` and `THE VALLEY` become `MOONEEVALLEY`
- `PARK HILLSIDE` becomes `SANDOWNHILLSIDE`
- `PARK LAKESIDE` becomes `SANDOWNLAKESIDE`
- `PARK KILMORE` becomes `KILMORE`
- synthetic course aliases are normalised explicitly

No fuzzy matching is permitted.
