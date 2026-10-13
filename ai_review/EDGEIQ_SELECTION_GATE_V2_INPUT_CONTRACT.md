# EDGEiQ Selection Gate V2 Input Contract

Version: `EDGEIQ_SELECTION_GATE_V2_INPUT_CONTRACT_2026-10-13`

Purpose: qualify prospective research-only BACK WIN and LAY WIN candidates from certified Stage011-style model probabilities and timestamped market quotes. This contract is not a betting-execution interface.

## Required Grain

One row per runner per immutable decision snapshot.

Required unique key:

- `snapshot_id`

Duplicate `snapshot_id` values fail closed.

## Required Identity And Timing Fields

- `race_id`
- `runner_id`
- `snapshot_id`
- `snapshot_time`
- `scheduled_start_time`
- `quote_timestamp`

Rules:

- `quote_timestamp <= snapshot_time < scheduled_start_time`
- quote age must be less than or equal to the configured maximum age
- invalid, missing, stale, or future quote timestamps fail closed

## Required Model Fields

- `model_id`
- `model_version`
- `model_snapshot_id`
- `model_snapshot_sha256`
- `feature_manifest_sha256`
- `model_probability`
- `probability_certified`
- `data_certified`

Rules:

- `0 < model_probability < 1`
- probability and source data must be explicitly certified
- model snapshot and feature manifest hashes must be present
- market odds are never model features

## Required Market Quote Fields

- `market_source`
- `provider`
- `quote_certified`
- `commission_rate`
- `back_quote_type`
- `back_odds`
- `back_available`
- `lay_quote_type`
- `lay_odds`
- `lay_available`

Supported BACK quote types:

- `BETFAIR_BACK`
- `BOOKMAKER_FIXED_WIN`

Supported LAY quote types:

- `BETFAIR_LAY`

Rules:

- LAY qualification requires `market_source = BETFAIR_EXCHANGE`
- bookmaker fixed-win quotes can support BACK qualification only
- exchange quotes fail closed when crossed, meaning `back_odds >= lay_odds`
- missing source/provider, missing odds, nonpositive odds, invalid available amounts, or uncertified quotes fail closed

## Outputs

The gate emits:

- independent `back_status` and `lay_status`
- independent reason-code columns
- expected value per back stake
- expected value per lay liability
- immutable `paper_event_id`
- `execution_authorized = False`
- `research_only = True`

No output authorizes live betting or claims profitability.
