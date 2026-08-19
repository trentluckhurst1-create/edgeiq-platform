# Racing.com Fresh Source POC V1

Built UTC: 2026-07-22T09:37:42+00:00

## Decision

`FRESH_SOURCE_POC_PASS`

## Counts

- Fixtures consumed: 15
- Normalised rows: 1023
- Fresh GraphQL fixtures acquired: 5
- Historical CSV fixtures acquired: 8
- Negative controls rejected: 2
- Fresh GraphQL rows: 449
- Historical CSV rows: 574
- Unique fresh runners: 58
- Unique historical runners: 80
- Failed acquisitions: 0
- Identity failures: 0

## Source Handling

- Fresh recent Speed Data pages were acquired through the evidenced GraphQL request `sectionaltimes_callback: getRaceForm(meetCode, raceNumber)`.
- Fresh GraphQL replay uses only public widget headers captured in the browser request ledger, including the public `x-api-key`; no cookies, authorization headers, user tokens, credentials or account state are used.
- Historical V2 CSV fixtures were retained as `HISTORICAL_DIRECT_CSV`.
- Negative controls were not queried with synthetic sectionals requests; they are rejected because no admitted sectionals request was observed in the browser evidence.
- Raw payloads are cached under `outputs/performance-intelligence/racingcom-source-discovery/raw/fresh-source-poc`.
- The normalised POC output preserves raw section records, raw runner context, source URL, cache path and SHA-256.

## Governance

- Production warehouse was not overwritten.
- V2 architecture was not modified.
- UI, pricing, probability, rating, V6.1 and V7.2G2 were not modified.
- This is proof-of-concept evidence only; no migration has been performed.
