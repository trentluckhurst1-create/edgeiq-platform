# Production vs GraphQL Candidate V1

Production rows: `80`
Candidate rows: `978`
Rows retained: `80`
Rows added: `898`
Rows removed: `0`
Rows changed: `0`

Schema compatibility: `REQUIRES_ADAPTER`

The candidate is not a drop-in replacement because it changes the row grain from `RUNNER_AGGREGATE` to `MIXED_RUNNER_AGGREGATE_AND_SEGMENT`.
