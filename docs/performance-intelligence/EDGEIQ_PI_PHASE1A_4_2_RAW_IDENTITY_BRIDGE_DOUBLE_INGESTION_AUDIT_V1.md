# EDGEIQ Performance Intelligence

## Phase 1A.4.2 Audit V1

**Overall status: FAIL**

- **PASS** — `required_file_availability`: all six governed target files available
- **PARTIAL** — `raw_identity_extraction`: graphql_missing=0; observation_missing=11080; performance_missing=0; performance_parse_failures=0
- **FAIL** — `observation_double_ingestion_check`: raw identities present in both monthly files and consolidated warehouse=814236
- **PASS** — `graphql_observation_raw_identity_overlap`: intersection=879695; graphql_only=0; observation_only=1885
- **PASS** — `graphql_performance_bridge`: intersection=879695; graphql_only=0; performance_only=0
- **PASS** — `snapshot_source_row_lineage`: valid_rows=879784; invalid_rows=0; sha_matches=879784; sha_mismatches=0
- **PASS** — `epi_parent_population`: epi_rows=533387; unique_ids=533387; missing_ids=0; not_in_parent=0
