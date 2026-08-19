# Racing.com Race Discovery V2 Evidence Extension Contract V1

Built UTC: `2026-07-22T18:07:59+00:00`
Status: `RACINGCOM_RACE_DISCOVERY_V2_EVIDENCE_EXTENSION_CONTRACT_DEFINED`

## Governance

Race discovery proves race existence. Speed-source admission separately proves whether speed data may be acquired.

No race may be admitted from URL construction, fixed race-number expansion, or a vague manual fixture status.

## Canonical Identity

- `race_date`
- `track_key`
- `race_no_numeric`

## Supported Discovery Methods
- `VALIDATED_GRAPHQL_RACE_PAYLOAD` precedence `1`: Validated getRaceForm GraphQL payload with runner and sectional populations.
- `OBSERVED_GRAPHQL_REQUEST` precedence `2`: Captured Racing.com GraphQL getRaceForm request tied to an observed race page.
- `OBSERVED_SPEED_DATA_PAGE` precedence `3`: Browser-observed Racing.com speed-data page for a completed race.
- `OBSERVED_RACE_PAGE` precedence `4`: Browser-observed completed Racing.com race page.
- `HISTORICAL_SUCCESS_RACE` precedence `5`: Previously fetched and parsed historical source race.
- `OBSERVED_STRUCTURED_RACE` precedence `6`: Race observed in a retained structured source without generated race-number expansion.

## Deduplication Precedence

`VALIDATED_GRAPHQL_RACE_WITH_SPEED`, `VALIDATED_GRAPHQL_RACE_NO_SPEED`, `HISTORICAL_SUCCESS_RACE`, `OBSERVED_STRUCTURED_RACE`, `OBSERVED_RACE_PAGE`

## Required Output Fields

`race_id`, `meeting_id`, `race_date`, `track`, `track_key`, `state`, `meet_code`, `race_no`, `race_no_numeric`, `race_url`, `speed_data_url`, `discovery_method`, `evidence_strength`, `source_url`, `source_artifact`, `source_record_id`, `source_request_id`, `source_response_id`, `source_payload_path`, `source_sha256`, `observed_in_source`, `race_status`, `completed_status`, `is_future`, `has_speed_data`, `speed_data_status`, `provenance`, `discovered_utc`, `pipeline_version`

## Preservation

- Production warehouse unchanged.
- UI unchanged.
- Pricing, probabilities, ratings, V6.1 and V7.2G2 unchanged.
