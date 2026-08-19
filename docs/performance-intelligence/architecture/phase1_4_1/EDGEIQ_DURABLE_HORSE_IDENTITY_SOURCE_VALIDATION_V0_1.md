# EDGEiQ Durable Horse Identity Source Validation V0.1

## Candidate source

`public/data/horses_master.csv`

## Required durable evidence

A valid registration identity record contains:

- horse code
- horse name
- date of birth
- sire
- dam

Sex and country are retained where available.

## Validation rules

A horse code may be promoted only when:

1. The horse code is non-empty.
2. All rows for the horse code describe the same identity.
3. Horse name, DOB, sire and dam do not conflict.
4. Duplicate source rows are exact identity duplicates only.
5. The source row remains preserved.
6. Historical result linkage is deterministic by horse code.

## Name rule

Horse names are descriptive attributes, not primary identities.

One normalised horse name may legitimately map to multiple horse codes.

No name-only merge is permitted.

## Current phase boundary

Phase 1.4.1 validates the source.

It does not create canonical horse IDs.

Canonical horse materialisation requires a separate audited phase.
