# EDGEiQ Racing.com Race Discovery V2

Built UTC: `2026-07-22T19:21:34+00:00`
Status: `RACINGCOM_RACE_DISCOVERY_V2_PASS`

## Counts
- Race rows: `59`
- Canonical races: `59`
- Base canonical races before GraphQL extension: `52`
- GraphQL race evidence rows consumed: `7`
- Fresh GraphQL speed races: `5`
- Negative-control no-speed races: `2`
- Fixed race expansion used: `NO`
- Constructed unsupported race URLs: `0`
- Constructed unsupported speed-data URLs: `0`

## Source Counts
- `COMPLETED_PAYLOAD_RACE`: `4`
- `HISTORICAL_SUCCESS_RACE`: `8`
- `OBSERVED_GRAPHQL_REQUEST`: `2`
- `OBSERVED_STRUCTURED_RACE`: `40`
- `VALIDATED_GRAPHQL_RACE_PAYLOAD`: `5`

## Audit
- `output_rows_gt_zero`: `PASS` (59) - Race rows emitted.
- `no_future_races_admitted`: `PASS` (0) - No future races admitted.
- `no_fixed_1_12_expansion_code`: `PASS` (0) - No executable fixed one-to-twelve race expansion.
- `no_synthetic_race_expansion`: `PASS` (0) - Builder consumes retained rows only; no generated race ranges.
- `no_duplicate_canonical_races`: `PASS` (0) - Duplicate race_id count.
- `numeric_race_ordering`: `PASS` (0) - race_no_numeric valid and deterministic numeric ordering.
- `all_race_numbers_directly_evidenced`: `PASS` (0) - All output race numbers came from retained source rows.
- `all_meeting_codes_directly_evidenced_or_null`: `PASS` (7) - Rows with meet_code; empty is allowed for historical sources.
- `all_five_fresh_graphql_races_present`: `PASS` (5) - Five fresh Pakenham races present.
- `both_negative_control_races_present`: `PASS` (2) - Two Moe controls present as races.
- `five_fresh_races_classified_with_speed_data`: `PASS` (5) - Fresh fixtures classified with validated GraphQL speed data.
- `two_negative_controls_classified_without_speed_data`: `PASS` (2) - Controls classified as valid no-speed races.
- `source_payload_hashes_retained`: `PASS` (5) - Five speed payload hashes retained.
- `source_evidence_paths_retained`: `PASS` (7) - GraphQL fixture evidence paths retained.
- `historical_52_rows_retained_or_explained`: `PASS` (52) - Base V2 canonical races before GraphQL extension.
- `every_race_tied_to_direct_evidence`: `PASS` (0) - Rows missing observed source evidence.
- `no_unsupported_race_identities`: `PASS` (0) - No unsupported race identities emitted.
- `future_completed_status_explicit`: `PASS` (0) - Future races cannot be historical acquisition eligible.
- `meeting_contract_overlap_reported`: `PASS` (17) - Rows whose meeting_id is not present in meeting discovery V2 contract.
- `exact_1_12_groups_reported_not_assumed`: `PASS` (0) - Exact 1-12 groups present only as observed evidence groups, not generated.
- `deterministic_output`: `PASS` (1) - Output ordering is deterministic.
- `production_unchanged`: `PASS` (0) - Research/staging discovery only; production warehouse unchanged.

## Preservation

- Production warehouse unchanged.
- UI unchanged.
- Pricing, probabilities, ratings, V6.1 and V7.2G2 unchanged.
- Historical CSV pathway retained.
