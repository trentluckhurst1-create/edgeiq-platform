# Racing.com Race Discovery V2 Fixture Gap Diagnosis V1

Built UTC: `2026-07-22T18:06:56+00:00`
Status: `RACINGCOM_RACE_DISCOVERY_V2_FIXTURE_GAP_DIAGNOSIS_PASS`

## Finding

The five fresh Pakenham speed fixtures have retained browser-network, getRaceForm response, and validated payload evidence, but the active Race Discovery V2 builder does not consume the source-discovery evidence family. It currently combines local structured races, completed payload probe rows, and historical CSV success rows.

The two Moe negative controls also have race-level GraphQL evidence, but their speed-data eligibility must remain negative. Race existence and speed-source admission are separate decisions.

## Counts
- Fixture races reviewed: `7`
- Valid fresh speed fixtures: `5`
- Negative controls: `2`
- Valid fresh fixtures missing from current V2 discovery: `5`
- Negative controls missing from current V2 discovery: `2`

## Decision

`PASS`: proceed to a governed GraphQL race-evidence adapter. Do not weaken GraphQL source admission and do not manually insert races into admission output.

## Preservation

- Production warehouse unchanged.
- UI unchanged.
- Pricing, probabilities, ratings, V6.1 and V7.2G2 unchanged.
