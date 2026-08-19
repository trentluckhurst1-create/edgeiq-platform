# EDGEiQ Horse Performance Identity Map Recovery V1

Status: IDENTITY_MAP_READY

## Scope

This recovery uses only exact Racing.com race-entry identifiers already present in the governed historical performance base. No fuzzy horse-name matching, threshold reduction, fabricated horse IDs, rating changes, V6.1 changes, V7.2G2 changes, pricing changes, or UI changes were made.

## Results

- Target source identifiers: 24
- Identity-ready identifiers: 24
- Missing identifiers: 0
- Conflicted identifiers: 0
- Candidate rows: 24
- Candidate duplicate source IDs: NO
- Governed config promoted: YES

## Method

The active performance base currently stores Racing.com race-entry IDs in the field consumed by the observation builder as `source_horse_name`. The recovery therefore maps each exact source ID to canonical Racing.com horse identity from authoritative raw GraphQL payload evidence.

The generated config follows the active consumer schema exactly:

`source_horse_name, canonical_horse_id, canonical_horse_name, identity_status, evidence_reference, evidence_sha256`

## Governance Note

This recovers the identity governance source only. It does not recover the missing normalisation or aggregation methodology parameters, so downstream horse performance ratings remain blocked until those methodological sources receive owner-approved provenance.
