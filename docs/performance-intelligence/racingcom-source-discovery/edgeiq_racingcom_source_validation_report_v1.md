# Racing.com Source Candidate Validation V1

Built UTC: 2026-07-22T09:36:58+00:00

## Status

`RACINGCOM_SOURCE_CANDIDATE_VALIDATION_V1_PASS`

## Candidate Decision

- Fresh source decision: `VALID_GRAPHQL_SOURCE`
- Historical CSV decision: `VALID_DIRECT_CSV_SOURCE`
- Fresh source: `graphql.rmdprod.racing.com` GraphQL query alias `sectionaltimes_callback: getRaceForm(meetCode, raceNumber)`
- Current source remains CSV: `NO` for recent Speed Data pages; CSV is retained for the eight historical V2 fixtures only.

## Evidence Counts

- Fixtures consumed: 15
- Recent visible-speed fixtures: 5
- Recent fixtures with GraphQL sectionals payload: 5
- Negative controls with GraphQL sectionals payload: 0
- GraphQL source races: 5
- GraphQL runners: 58
- GraphQL sectional rows: 449
- GraphQL numeric AvgSpeed values: 449
- Visible runner-name matches: 58/58
- Historical CSV caches retained: 8
- Public widget x-api-key header observed: 5

## Schema / Unit Findings

- GraphQL runner identity appears under `data.sectionaltimes_callback.Horses[]`.
- Sectional data appears under `Horses[].SectionalTimes[]`.
- Required sectional fields observed: `Distance`, `Position`, `Time`, `AvgSpeed`.
- `AvgSpeed` is source metres per second. The visible Racing.com speed table displays km/h after conversion.
- Fresh recent pages did not expose a direct CSV link in static or browser network evidence.
- A fresh parser should be JSON/GraphQL-specific and should preserve raw fields before canonical normalisation.

## Governance Findings

- The GraphQL candidate requires the public widget `x-api-key` header observed in the Racing.com browser request. No user cookie, user token, or private account credential is required or used.
- No signed or expiring URL was required for admitted GraphQL payloads.
- Analytics, advertising, CSS, JavaScript and ordinary page-layout payloads are rejected as speed-data sources.
- V2 historical CSV parser and warehouse architecture are preserved.
- Production warehouse was not overwritten.
- UI, pricing, probability, rating, V6.1 and V7.2G2 were not modified.

## Next Unit

Proceed to proof-of-concept acquisition using only the evidenced GraphQL sectionals request pattern and the retained historical CSV fixtures. Negative controls must remain rejected.
