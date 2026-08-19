# EDGEIQ Performance Intelligence

## Phase 1A.4.3 Observation Residual and Missing Identity Forensics V1

- Overall status: **PARTIAL**
- GraphQL unique keys: 879695
- Observation unique keys: 881580
- Observation-only keys: 1885
- Missing identity rows: 11080

## Audit

- **PASS** — `required_files`: GraphQL and observation files available
- **PASS** — `known_graphql_population_preserved`: graphql_unique=879695; observation_contains=879695; graphql_missing_from_observation=0
- **PASS** — `observation_residual_classified`: observation_only_unique_keys=1885
- **PASS** — `missing_identity_rows_classified`: missing_identity_rows=11080
- **PARTIAL** — `residual_source_resolution`: residual_keys_from_other_classes=1263

## Governance

- No production data was modified.
- No observation was removed.
- No source was excluded.
- No corrected warehouse was built.
