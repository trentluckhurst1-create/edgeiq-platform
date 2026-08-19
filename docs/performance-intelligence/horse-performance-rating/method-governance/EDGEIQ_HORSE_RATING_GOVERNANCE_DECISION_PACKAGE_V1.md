# EDGEiQ Horse Rating Governance Decision Package V1

## Objective

Recover or certify the governed sources required to build horse-level historical performance ratings without fabricating parameters, reducing thresholds, changing the EPI method, or introducing current/future leakage.

## Proven Inputs

- Historical performance intelligence base rows: 168
- Historical runner identities eligible for rating aggregation: 24
- Horses/race-entry IDs with 5+ eligible segments: 24/24
- Identity map coverage after recovery: 24/24
- Normalisation parameter source rows: 0
- Aggregation parameter source rows: 0

## Recovered Consumer Contracts

### Performance Normalisation

Active formula:

`normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value`

Recovered fields include `centre_value`, `scale_value`, effective date range, method, status, evidence reference, and evidence hash.

Unresolved methodology values:

- `centre_value`
- `scale_value`
- effective date ranges
- parameter approval provenance
- minimum population/source evidence requirements

### Horse Performance Aggregation

Recovered aggregate shape:

- Arithmetic mean with weight `1`, or
- Weighted arithmetic mean using exponential half-life weights: `0.5 ** (age_days / recency_half_life_days)`

Unresolved methodology values:

- aggregation method
- lookback days
- minimum observation count
- maximum observation count
- recency weight method
- recency half-life days
- effective date ranges
- parameter approval provenance

### Horse Identity Map

Recovered independently from authoritative Racing.com raw GraphQL payloads using exact source race-entry IDs. No fuzzy matching was used.

## Owner Decision Required

Normalisation and aggregation methodology source rows cannot be reconstructed from repository evidence. Any new parameter source would be a new architectural/methodological approval, not a recovered source.

## Options Requiring Approval

### Option A: Historical Population Normalisation

Define centre/scale from a governed historical population of `raw_performance_lengths`.

Status: NEW METHODOLOGY REQUIRING OWNER APPROVAL.

### Option B: Segment-Class Normalisation

Define centre/scale by governed segment/distance/surface/class buckets.

Status: NEW METHODOLOGY REQUIRING OWNER APPROVAL.

### Option C: Direct Raw-Length Aggregate

Skip normalisation and aggregate raw lengths directly.

Status: NEW METHODOLOGY REQUIRING OWNER APPROVAL and active builder redesign; not permitted under this directive.

## Recommendation

Do not build horse performance ratings until the owner approves a normalisation parameter source and aggregation parameter source with documented provenance. The identity map is ready, but the methodology remains blocked.

## Explicit Non-Changes

- Production pricing changed: NO
- Probability engine changed: NO
- V6.1 changed: NO
- V7.2G2 changed: NO
- UI changed: NO
- EPI redesigned: NO
- Production runner warehouse changed: NO
