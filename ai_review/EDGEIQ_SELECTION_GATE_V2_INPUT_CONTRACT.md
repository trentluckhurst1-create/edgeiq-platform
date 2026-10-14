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
- missing source/provider, missing odds, nonpositive odds, invalid available amounts, or uncertified quotes fail closed for the affected side
- partial quote snapshots are allowed only when the missing side remains fail-closed; for example, a certified bookmaker fixed-win BACK quote may qualify the BACK side while the LAY side fails with `LAY_QUOTE_INVALID` and `LAY_REQUIRES_BETFAIR_EXCHANGE`

## Readiness Adapter Inputs

The research readiness command `scripts/research/run_edgeiq_selection_gate_v2_readiness.py` builds this contract from two upstream files. It does not score a model, place bets, read outcomes, or claim profitability.

Required Stage011 scorer-output fields:

- `race_id`
- `runner_id`
- `scoring_timestamp`
- `scheduled_start_time`
- `stage011_probability`
- `champion_model_sha256`

The adapter also requires the frozen research model artifact manifest. It verifies the Stage011 model digest, computes a feature-manifest digest from the recorded feature list, checks race probability mass, and emits blockers instead of certifying rows when provenance is incomplete.

Required raw quote-snapshot fields:

- `race_id`
- `runner_id`
- `quote_snapshot_id`
- `quote_timestamp`
- `scheduled_start_time`
- `market_source`
- `provider`
- `quote_side`
- `quote_type`
- `odds`
- `available_amount`
- `commission_rate`
- `market_status`
- `in_play`
- `suspended`

Supported raw quote sides:

- `BACK`
- `LAY`

Supported raw quote types:

- `BETFAIR_BACK`
- `BOOKMAKER_FIXED_WIN`
- `BETFAIR_LAY`

Quote snapshots are not certified when markets are suspended, in-play, closed, stale relative to the race start, duplicated at the same side grain, missing provider/source, or mismatched between quote side and quote type. SP/BSP substitutions are not supported.

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
