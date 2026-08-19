# Racing.com Fresh Source Migration Readiness V1

Built UTC: 2026-07-22T09:41:04+00:00

## Final Decision

`RACINGCOM_INGESTION_V2_RESEARCH_ONLY`

This is a research-only result. A fresh source has been proven, but V2 orchestration and production warehouse migration have not been changed.

## Counts

- Checks: 19
- PASS: 18
- WARN: 1
- FAIL: 0
- Fixtures: 15
- Historical CSV races retained: 8
- Historical unique runners retained: 80
- Fresh visible races discovered: 5
- Fresh races acquired: 5
- Fresh normalised rows: 449
- Negative controls rejected: 2/2
- POC output SHA-256: `786fbb2590dd97c01aafff72e3fb03676cfbe9d35f4004baf6d6128cf4e0840a`

## Decision Rationale

- Fresh Racing.com Speed Data is delivered through GraphQL JSON for the tested recent pages, not direct fresh CSV.
- Historical CSV remains valid and retained for the eight V2 historical fixtures.
- The GraphQL candidate requires the public Racing.com widget `x-api-key` header observed in browser evidence; no user credentials or cookies are used.
- Negative controls are rejected without synthetic probing.
- A source-specific GraphQL parser is required before migration.
- Production V2 warehouse was not overwritten.

## Remaining Migration Blockers

- Build governed GraphQL source admission.
- Build source-specific GraphQL parser.
- Prove canonical equivalence with historical CSV intermediate.
- Run deterministic rerun inside the eventual V2 migration pipeline.
- Re-run final E2E regression after parser integration.

## Preserved

- V2 historical CSV warehouse architecture.
- Existing V2 parser and E2E docs.
- UI, pricing, probability, ratings, V6.1 and V7.2G2.
