# Racing.com Speed Data Fixture Contract V1

Built UTC: 2026-07-22T09:12:23+00:00

## Status

`RACINGCOM_SPEED_DATA_FIXTURE_CONTRACT_V1_PASS`

## Counts

- Fixture rows: 15
- Historical proven CSV races: 8
- Recent visible speed-data fixtures: 5
- Negative controls: 2
- Candidate meetings scanned: 10
- Candidate races observed from Racing.com race-list evidence: 70
- Browser checked races: 14
- Future races admitted: 0

## Evidence Basis

Historical fixtures come from the V2 CSV admission contract. Recent and negative-control fixtures come from cached Racing.com `GetMeetsByMonth` meeting evidence plus `getNoCacheRacesForMeet` race-list payloads captured for those observed meetings. Speed-data page visibility was checked with a governed Playwright browser pass and retained body text evidence under `outputs/performance-intelligence/racingcom-source-discovery/raw/fixture-selection`.

No fixed race-number probing or unsupported generated race identities are admitted into this fixture contract.
