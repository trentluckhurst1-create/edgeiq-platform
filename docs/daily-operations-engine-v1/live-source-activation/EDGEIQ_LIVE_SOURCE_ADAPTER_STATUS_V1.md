# EDGEiQ Live Source Adapter Status V1

Run ID: `LIVE-SOURCE-DB47F27C0776`
Built UTC: `2026-07-29T01:39:06Z`

Overall acceptance: `BLOCKED_EXTERNAL`

## Zero-Race Discovery Root Cause

Previous-day zero-race discovery was caused by date-window/source-scope mismatch: DAILY queried 2026-07-28, while the live Racing.com three-day catalog retained 2026-07-29..2026-07-31 after refresh and the local historical/RA result sources have no 2026-07-28 official rows. It is not a Racing.com calendar endpoint outage.

## Adapter Status

### RACINGCOM_THREE_DAY_PRODUCT_CATALOG
- Status: `WORKING`
- Classification: `PASS`
- Current response: `HTTP_200`
- Rows available: `33`
- Post-cutoff rows: `33`
- Latest source date: `2026-07-31`
- Root cause: Discovery source works but is current/future window, not previous-day result history.
- Recommended action: Keep for CURRENT_DAY discovery; do not use alone for previous-day official result acceptance.

### RACINGCOM_GRAPHQL_DIRECT_SPEED_TIMING
- Status: `BLOCKED`
- Classification: `AUTH_REQUIRED`
- Current response: `HTTP_401`
- Rows available: `0`
- Post-cutoff rows: `0`
- Latest source date: `2026-07-01`
- Root cause: Direct GraphQL source rejects unauthenticated requests; environment key missing.
- Recommended action: Set RACINGCOM_PUBLIC_WIDGET_API_KEY from approved source contract, then rerun acquisition/parser.

### RACING_AUSTRALIA_RESULTS_OUTPUTS
- Status: `BLOCKED`
- Classification: `AUTH_REQUIRED`
- Current response: `HTTP_403`
- Rows available: `15265`
- Post-cutoff rows: `0`
- Latest source date: `2026-05-12`
- Root cause: Remote source returns HTTP 403 for current official results/calendar requests from this environment.
- Recommended action: Resolve approved access/header/cookie contract or use an existing retained official result feed; do not fabricate.

### RACINGCOM_SPEED_DATA_OUTPUTS
- Status: `PENDING`
- Classification: `NO_SPEED_AVAILABLE`
- Current response: `LOCAL_FILE`
- Rows available: `392`
- Post-cutoff rows: `0`
- Latest source date: `2026-07-01`
- Root cause: Local speed warehouse has no post-cutoff rows; direct GraphQL acquisition is auth-gated.
- Recommended action: Leave lifecycle SPEED_PENDING until approved speed source/key publishes accessible rows.

### GOVERNED_TRACK_CONDITION_EVIDENCE
- Status: `WORKING`
- Classification: `PASS`
- Current response: `LOCAL_FILE`
- Rows available: `8`
- Post-cutoff rows: `8`
- Latest source date: `2026-07-29`
- Root cause: Condition adapter accepts race-level Racing.com condition evidence; no weather-derived inference used.
- Recommended action: Keep active.
