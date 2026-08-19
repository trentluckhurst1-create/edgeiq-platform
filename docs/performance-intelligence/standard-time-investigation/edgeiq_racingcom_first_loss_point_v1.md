# EDGEIQ Racing.com First Loss Point V1

Generated UTC: `2026-07-22T07:19:07.774138+00:00`

## Governance boundary

- Read-only forensic diagnostic.
- Raw full-payload directory only.
- No builder modified.
- No governed output modified.
- No threshold modified.
- No benchmark data fabricated.

## Raw payload population

- Files: **602**
- Unique hashes: **236**
- Duplicate copies: **366**

## Structural classification

- NON_JSON_NO_IDENTITY: **123**
- VALID_JSON_COMPLETE_IDENTITY: **65**
- VALID_JSON_NO_IDENTITY: **3**
- VALID_JSON_PARTIAL_IDENTITY: **45**

## Distinct extracted identities

- Complete race identities: **59**
- Partial race identities: **10**
- Payloads with no identity: **126**

## Governed facts

- `edgeiq_racingcom_runner_speed_fact_v1.csv` ? FOUND ? rows=392 ? distinct source files=39
- `edgeiq_racingcom_runner_sectional_fact_v1.csv` ? FOUND ? rows=2854 ? distinct source files=39
- `edgeiq_racingcom_runner_split_fact_v1.csv` ? FOUND ? rows=2682 ? distinct source files=39
- `edgeiq_racingcom_race_speed_summary_v1.csv` ? FOUND ? rows=39 ? distinct source files=39

## Preliminary interpretation

**RAW_FILES_CONTAIN_MORE_THAN_39_COMPLETE_RACE_IDENTITIES**

The raw directory contains identifiable race evidence beyond the 39 governed races. The next diagnostic must execute the active parser against each unique payload and record exact admission or rejection reasons.
