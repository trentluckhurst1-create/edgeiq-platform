# EDGEIQ_EPI_WORKSPACE_FEED_ORCHESTRATION_AUDIT_V1

- Generated UTC: `2026-07-28T01:13:01.022308+00:00`
- Verdict: **CANONICAL_WRITER_NOT_PROVEN**
- Canonical feed: `public/data/edgeiq_epi_workspace_terminal_feed_v1.csv`
- Canonical rows: `246`
- Canonical SHA-256: `f32b71ed20c2ac22f095d4a59500dd7c0731f8ebcb35b73e7db02460ac26b725`
- Active writer paths: `0`
- Active reader paths: `4`
- React consumer paths: `2`
- Exact-name copies: `4`
- Different-hash exact-name copies: `3`

## Active Writers

- No active writer identified.

## Active Readers

- `scripts/audit_edgeiq_data_coverage_report_v1.py`
- `scripts/audit_edgeiq_end_to_end_validation_v1.py`
- `scripts/audit_edgeiq_governed_field_trace_v1.py`
- `scripts/repair_edgeiq_beta_readiness_e2e_best_race_v1.py`

## React Consumers

- `src/edgeiq-os/race/services/epiWorkspaceFeed.ts`
- `src/edgeiq-os/race/services/epiWorkspaceFeed_CHECKPOINT_BEFORE_RACE_KEY_NORMALISATION_20260721_052533.ts`

## Findings

- 2 React consumer path(s) identified.
- 3 checkpoint/archive copies of the exact feed were identified.

## Warnings

- No active runtime writer was identified for the canonical feed.
- 3 exact-name feed copy or copies differ from the current canonical feed hash.
