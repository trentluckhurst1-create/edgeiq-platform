# EDGEIQ Racing.com Candidate Legitimacy V1

Generated UTC: `2026-07-22T07:40:54.656087+00:00`

## Governance boundary

- Read-only forensic diagnostic.
- No network access.
- Production ingestion builder not executed.
- No candidate, cache or governed output modified.

## Candidate population

- Candidate URLs: **1296**
- Candidate meeting groups: **104**
- Historically fetched and parsed URLs: **8**

### Candidate legitimacy

- `BEYOND_EVIDENCED_RACE_LIMIT`: **12**
- `DERIVED_WITHIN_EVIDENCED_LIMIT`: **24**
- `DERIVED_WITHOUT_RACE_LIMIT_EVIDENCE`: **1248**
- `DIRECT_URL_NOT_HISTORICALLY_FETCHED`: **4**
- `HISTORICALLY_FETCHED_AND_PARSED`: **8**

### Discovery methods

- `KNOWN_DIRECT_CSV_MEETING`: **12**
- `MEETCODE_DERIVED_CLOUDFRONT`: **1284**

## First-50 admission cohort

- URLs: **50**

- `BEYOND_EVIDENCED_RACE_LIMIT`: **7**
- `DERIVED_WITHIN_EVIDENCED_LIMIT`: **17**
- `DERIVED_WITHOUT_RACE_LIMIT_EVIDENCE`: **14**
- `DIRECT_URL_NOT_HISTORICALLY_FETCHED`: **4**
- `HISTORICALLY_FETCHED_AND_PARSED`: **8**

## Ordering defect

- Meeting groups affected by lexical race-number ordering: **104**

Lexical ordering produces sequences such as:

`1,10,11,12,2,3...`

rather than:

`1,2,3...10,11,12`

## Interpretation boundary

A meetcode-derived URL is not treated as proof that a CSV exists.

The strongest classes are:

1. `HISTORICALLY_FETCHED_AND_PARSED`
2. source-supported candidates inside an evidenced race limit
3. direct URLs not yet historically fetched
4. derived URLs without meeting race-limit evidence
5. candidates beyond an evidenced race limit

No production remediation has been applied.

## Decision

**CANDIDATE_LEGITIMACY_EVIDENCE_CREATED**

## Artifacts

- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_candidate_legitimacy_ledger_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_candidate_meeting_profile_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_source_column_inventory_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_candidate_legitimacy_v1.json`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_candidate_legitimacy_v1.md`
