# Racing.com Historical Runner Aggregation Semantics V1

Status: `RACINGCOM_HISTORICAL_RUNNER_AGGREGATION_SEMANTICS_PASS`

The production V2 warehouse is a runner aggregate contract. Historical CSV parser rows are already one row per race-runner; the builder preserves source split and speed aggregate fields and adds ID/provenance metadata.

## Key Finding
No segment-to-runner conversion occurs in the historical production builder. GraphQL segment rows therefore require a separate runner aggregate adapter before any production-compatible candidate can be reviewed.
