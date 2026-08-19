# ADR: Fresh Racing.com Speed Data Source

Date: 2026-07-22

Status: Proposed for governed staging, not migrated

Decision: admit fresh Racing.com Speed Data through a source-specific GraphQL acquisition and parser path, while retaining the existing historical CSV path.

## Context

Racing.com ingestion V2 previously passed its end-to-end gate for historical CSV files, but migration remained blocked because fresh completed-race Speed Data pages did not expose evidence-backed CSV links through static source discovery.

The fresh-source discovery investigation completed these governed units:

- Fixture contract: `RACINGCOM_SPEED_DATA_FIXTURE_CONTRACT_V1_PASS`
- Static source forensics: `RACINGCOM_STATIC_SOURCE_FORENSICS_V1_PASS`
- Browser network capture: `RACINGCOM_NETWORK_CAPTURE_V1_PASS`
- Source candidate validation: `RACINGCOM_SOURCE_CANDIDATE_VALIDATION_V1_PASS`
- Fresh-source proof of concept: `FRESH_SOURCE_POC_PASS`

## Selected Source

Fresh source:

```text
https://graphql.rmdprod.racing.com/
```

GraphQL request pattern:

```graphql
sectionaltimes_callback: getRaceForm(meetCode: "{meetCode}", raceNumber: {raceNumber}) {
  Horses: raceEntryTimes {
    id
    FullName: horseName
    SaddleNumber: saddleNumber
    Trainer: trainerName
    Jockey: jockeyName
    FinalPosition: finishPosition
    SectionalTimes: times {
      Distance: distance
      Position: rank
      Time: intermediateTime
      AvgSpeed: avgSpeed
    }
    SplitTimes: splitTimes {
      Distance: distance
      Position: position
      Time: time
      AvgSpeed: avgSpeed
    }
    DistanceRun: distanceTravelled
    Early: avgSpeedEarly
    Mid: avgSpeedMid
    Late: avgSpeedLate
    OverallPeakSpeed: overallPeakSpeed
    OverallAvgSpeed: overallAvgSpeed
  }
}
```

Required request context:

- Public Racing.com widget request headers observed in browser network capture.
- Public `x-api-key` header is required for direct replay.
- `Referer` is the public `https://dxp-static.racing.com/` sectionals widget.
- No user cookies, authorization headers, user tokens, account credentials, CAPTCHA bypass, or private session state are required or permitted.

## Evidence

Fixture evidence:

- 15 fixture rows.
- 8 historical CSV fixtures retained from V2.
- 5 recent completed Pakenham Synthetic races with visible Speed Data.
- 2 completed Moe races retained as negative controls.
- No future races admitted.

Network evidence:

- 1,910 request rows.
- 1,935 response rows.
- 134 JSON/GraphQL responses.
- 8 historical CSV responses.
- 5 recent sectionaltimes GraphQL payloads.
- 0 negative-control sectionaltimes GraphQL payloads.

Validation evidence:

- Fresh source decision: `VALID_GRAPHQL_SOURCE`.
- Historical CSV decision: `VALID_DIRECT_CSV_SOURCE`.
- 58 fresh GraphQL runners.
- 449 fresh GraphQL sectional rows.
- 58/58 fresh GraphQL runner names matched retained visible page text.
- No fresh CSV link observed behind recent Speed Data pages.

POC evidence:

- POC decision: `FRESH_SOURCE_POC_PASS`.
- 1,023 normalised POC rows.
- 449 fresh GraphQL rows.
- 574 historical CSV rows.
- 5/5 fresh GraphQL fixtures acquired.
- 8/8 historical CSV fixtures acquired.
- 2/2 negative controls rejected.
- 0 failed acquisitions.
- 0 identity failures.

Primary evidence files:

- `docs/performance-intelligence/racingcom-source-discovery/edgeiq_racingcom_speed_data_fixture_contract_v1.csv`
- `docs/performance-intelligence/racingcom-source-discovery/edgeiq_racingcom_network_response_ledger_v1.csv`
- `docs/performance-intelligence/racingcom-source-discovery/edgeiq_racingcom_source_candidate_validation_v1.csv`
- `docs/performance-intelligence/racingcom-source-discovery/edgeiq_racingcom_source_schema_profile_v1.csv`
- `docs/performance-intelligence/racingcom-source-discovery/edgeiq_racingcom_source_semantics_audit_v1.csv`
- `public/data/edgeiq_racingcom_fresh_speed_payload_poc_v1.csv`

## Rejected Alternatives

Direct fresh CSV:

- Rejected for current fresh pages.
- Static page forensics found no fresh CSV links.
- Browser network capture found no fresh CSV response for recent visible-speed pages.
- Historical CSV remains valid only for the eight retained V2 fixtures.

Static embedded payload:

- Rejected.
- No embedded page state or static HTML payload contained the governed race-runner-sectional source data for fresh pages.

Analytics, advertising, CSS and JavaScript assets:

- Rejected.
- These responses do not provide governed race identity, runner identity and sectional/speed schema.

Ordinary Racing.com race-form GraphQL:

- Not selected as the speed source.
- It can identify race/runner context, but the admitted speed-data source is the `sectionaltimes_callback` query returning `raceEntryTimes` with `SectionalTimes`.

## Schema And Units

Fresh GraphQL source:

- Runner identity: `Horses[].FullName`, `Horses[].SaddleNumber`, `Horses[].id`.
- Connections context: `Horses[].Trainer`, `Horses[].Jockey`.
- Result context: `Horses[].FinalPosition`.
- Sectional data: `Horses[].SectionalTimes[]`.
- Split data: `Horses[].SplitTimes[]`.
- Speed fields: `AvgSpeed`, `Early`, `Mid`, `Late`, `OverallPeakSpeed`, `OverallAvgSpeed`.
- Source speed unit: metres per second.
- Display km/h conversion: `source_mps * 3.6`.

Historical CSV source:

- No header row.
- First line is race metadata.
- Runner rows are semicolon-delimited.
- Runner identity is positional field 0.
- Sectional triples are distance, speed in metres per second, time string.

## Parser Implications

Do not force GraphQL payloads through the historical CSV parser.

Required V2 parser shape:

```text
Verified Race Contract
  -> Source Discovery
  -> Source Admission
  -> Payload Acquisition
  -> Raw Cache + Evidence Ledger
  -> Source-Specific Parser
      - historical CSV parser
      - fresh GraphQL sectionals parser
  -> Canonical Speed-Data Normalisation
  -> Performance Warehouse V2
```

The canonical intermediate must retain:

- `source_format`
- `source_parser_version`
- source URL
- source cache path
- source SHA-256
- source fixture/race identity
- raw section record
- raw runner record or source payload pointer
- source units
- conversion rules

## Caching And Provenance

Raw payloads must be cached under repository-local evidence paths such as:

```text
outputs/performance-intelligence/racingcom-source-discovery/raw/
```

Every acquisition row must retain:

- requested URL
- status
- content type
- response size
- timestamp
- SHA-256
- cache path
- source fixture ID
- parser version

## Retry And Pacing

Use conservative request pacing.

Recommended defaults:

- single-threaded acquisition unless a later governance review approves otherwise;
- bounded timeout;
- retry only transient 429/5xx responses;
- no retry on 401/403 without explicit governance review;
- negative controls must not be probed with synthetic source URLs.

## Authentication And Access Constraints

The fresh GraphQL candidate is public-widget gated:

- Public `x-api-key` header observed in the Racing.com browser request is required.
- No user authentication, cookies, session tokens, authorization headers or private credentials are used.
- If this public header stops working, acquisition must fail closed and return to source validation.

## Signed URL Handling

No signed or expiring GraphQL URL was observed for the admitted fresh source.

Historical CSV CloudFront URLs may have normal CDN metadata but no signed URL requirement was observed in this investigation.

## Migration Implications

Do not migrate yet solely from this ADR.

Before production migration:

- build source admission for GraphQL requests;
- build fresh GraphQL parser;
- prove deterministic rerun;
- prove negative controls remain rejected;
- prove canonical equivalence to V2 warehouse semantics;
- run final migration-readiness audit.

## Rollback

Rollback is straightforward because production V2 warehouse and orchestration are untouched.

If GraphQL acquisition or parser validation fails:

- keep existing historical CSV V2 architecture;
- disable fresh GraphQL source admission;
- retain raw evidence and POC artifacts for forensic review;
- do not overwrite production warehouse outputs.

## Current Migration Decision

`RACINGCOM_INGESTION_V2_RESEARCH_ONLY`

The fresh source is proven, but no production migration has been performed.
