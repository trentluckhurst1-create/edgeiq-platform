# EDGEiQ Horse Rating Governance Source Recovery Final Report V1

Final status: EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD

## Executive Finding

The missing horse identity governance source was recovered safely. The methodological sources needed to normalise raw performance and aggregate observations were not recoverable from repository or git evidence. Creating them now would require new owner-approved architecture, not source recovery.

## What Was Recovered

- `edgeiq_horse_performance_identity_map_v1.csv`: recovered and promoted.
- Identity coverage: 24/24 current historical source identifiers.
- Identity validation: PASS.
- Recovery method: exact Racing.com race-entry IDs from governed historical performance base mapped to canonical Racing.com horse IDs/names from raw GraphQL payloads.
- Fuzzy matching used: NO.

## What Remains Blocked

### Performance Normalisation

Active formula recovered:

`normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value`

Blocked because `centre_value`, `scale_value`, effective date ranges, and approval provenance were not recovered.

### Horse Performance Aggregation

Active aggregate contract recovered as arithmetic or half-life weighted arithmetic mean.

Blocked because aggregation policy values were not recovered: method, lookback days, min/max observations, recency method, and half-life days.

## Current Row Funnel

- Historical PI base rows: 168
- Normalisation fact rows: 0
- Rating-base fact rows: 0
- Horse observation rows: 0
- Horse aggregate rows: 0
- Horse performance rating rows: 0

The first unresolved zero-row stage is performance normalisation.

## Decisions

- Normalisation parameter candidate built: NO.
- Aggregation parameter candidate built: NO.
- Reason: source rows and methodological values were not recovered; any candidate would fabricate parameters.
- Identity map candidate built: YES.
- Identity map promoted: YES.

## Required Owner Approval Before Unblocking

1. Approve a performance normalisation parameter source with explicit centre/scale methodology and provenance.
2. Approve a horse performance aggregation parameter source with explicit lookback, observation, and recency policy.
3. Re-run the guarded builders in order after approval.

## Safety Confirmations

- Production pricing changed: NO
- Probability engine changed: NO
- V6.1 changed: NO
- V7.2G2 changed: NO
- UI changed: NO
- EPI redesigned: NO
- Thresholds reduced: NO
- Fabricated ratings/parameters: NO
- Current/future leakage introduced: NO

## Validation Commands

- Python compile: PASS
- TypeScript compile (`npx.cmd tsc -b`): PASS
- `npm run build`: TIMEOUT after 300 seconds and again after 600 seconds; no build error text was returned before timeout.
- Timed-out npm/vite build processes were cleaned up; the MCP node process was left running.

Validation command ledger: `edgeiq_horse_rating_governance_validation_commands_v1.csv`
