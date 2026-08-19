# Racing.com Runner Adapter V2 Idempotence Audit

Decision: `RACINGCOM_RUNNER_ADAPTER_V2_IDEMPOTENT_PASS`

The adapter now reads only historical CSV rows from the current production warehouse before appending GraphQL runner aggregates, so a post-promotion rebuild remains 138 rows rather than duplicating GraphQL records.
