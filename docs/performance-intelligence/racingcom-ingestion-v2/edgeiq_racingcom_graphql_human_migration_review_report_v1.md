# Racing.com GraphQL Human Migration Review Report V1

## Executive decision

Recommendation: `RECOMMEND_APPROVE_RUNNER_ADAPTER_MIGRATION`. This is not authorisation. No migration has been executed.

## Current production state

Production target: `public\data\edgeiq_racingcom_performance_warehouse_v2.csv`
Rows: `80`
Row grain: `RUNNER_AGGREGATE`
SHA-256: `25ea33aba489bb8f318edcaa3d414c4f7da566573045041ad6ffbe5bff826859`

## Runner adapter candidate state

Candidate target: `public\data\edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv`
Rows: `138`
Row grain: `RUNNER_AGGREGATE`
Core schema: `EXACT_PRODUCTION_35_COLUMNS`
SHA-256: `77803a32e3880598bb5fae3ba7aba49e1fb67931c2d729f567c36eeab873cfb8`

## Mixed candidate classification

Mixed candidate: `public\data\edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv`
Rows: `978`
Classification: `CANONICAL_SEGMENT_RESEARCH_WAREHOUSE`
SHA-256: `7cda463af111faf8f7c13179dfca758da2095187e5bba9047ea347683ebdbe2e`

## Architecture

`RAW GRAPHQL SEGMENTS -> CANONICAL SEGMENT CONTRACT -> RUNNER AGGREGATE ADAPTER -> PRODUCTION-COMPATIBLE CANDIDATE`

The mixed candidate is not a drop-in production warehouse. The runner adapter candidate is the production-compatible review target.

## Compatibility evidence

- Historical regression: `PASS`, changed production fields `0`.
- GraphQL runner aggregation: `PASS`, 898 source segment rows aggregated to 58 runner rows.
- Downstream drop-in compatibility: `PASS`, exact 35-column production order.
- Runner readiness decision: `RACINGCOM_RUNNER_CANDIDATE_READY_FOR_HUMAN_REVIEW`.

## Migration dry run

Dry-run manifest now points at the runner candidate. No migration executed.

## Rollback dry run

Rollback remains manifest-driven and requires explicit backup path after a separately approved migration.

## Recommended decision

`RECOMMEND_APPROVE_RUNNER_ADAPTER_MIGRATION`
