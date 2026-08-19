# EDGEIQ Performance Intelligence

## Phase 1A.4.4 Residual Authority and Corrected Population Preview V1

- Overall status: **PARTIAL**
- Consolidated GraphQL unique runner keys: 879695

## Authority Decisions

- `WEEK1_2025_GRAPHQL` — **REQUIRES_RESULT_VALIDATION**: GraphQL-labelled result source, but completed-result evidence or identity novelty is incomplete.
- `RUNNER_SPEED_V2_1` — **ENRICHMENT_ONLY**: Speed or sectional source. May enrich a governed historical runner fact but must not independently establish result authority.
- `GRAPHQL_SPEED_NORMALISED` — **ENRICHMENT_ONLY**: Speed or sectional source. May enrich a governed historical runner fact but must not independently establish result authority.
- `SPEED_CHECKPOINT` — **ENRICHMENT_ONLY**: Speed or sectional source. May enrich a governed historical runner fact but must not independently establish result authority.

## Corrected Population Preview

- `CONSERVATIVE_GRAPHQL_AUTHORITY_ONLY`: 879695 unique runner identities
- `GRAPHQL_PLUS_VERIFIED_WEEK1_CANDIDATE`: 879695 unique runner identities

## Audit

- **PASS** — `graphql_authority_available`: rows=879784; unique_runner_keys=879695
- **PASS** — `residual_sources_available`: unavailable=NONE
- **PARTIAL** — `week1_result_authority`: decision=REQUIRES_RESULT_VALIDATION; raw_only=0; new_race_ids=0; completed_evidence_rows=630
- **PASS** — `speed_sources_classified_as_enrichment`: invalid_authority_sources=NONE

## Governance

- No production dataset was changed.
- No source was admitted automatically.
- No residual identity was deleted.
- Preview counts are advisory only.
