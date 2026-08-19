# EDGEiQ Ladbrokes Reference Inspection V1

Reference repository: https://github.com/Josh9456/Racing-Form-
Official API docs: https://nedscode.github.io/affiliate-feeds/

## Confirmed Contract

- Racing API examples use `https://api-affiliates.ladbrokes.com.au/affiliates/v1/racing`.
- Identification uses `From` and `X-Partner` headers.
- Documented racing endpoints are meetings, meeting-by-id, and event-by-id.
- Sports API is not available via the affiliates API.
- Race runners expose `odds.fixed_win`, `odds.fixed_place`, `is_scratched`, `scratch_time`, weights, barrier, jockey, trainer, runner number, and ordered `flucs`.
- Official docs describe `flucs` as ordered prices, not timestamped prices.

## EDGEiQ Decision

The public repository is treated as endpoint evidence only. EDGEiQ keeps its canonical IDs, market observation history, freshness contract, last-known-good protection, and public runtime feed.

## EDGEiQ Env Compatibility

Preferred EDGEiQ env: `EDGEIQ_LADBROKES_FROM`, `EDGEIQ_LADBROKES_X_PARTNER`. Legacy fallback remains supported: `EDGEIQ_LADBROKES_EMAIL`, `EDGEIQ_LADBROKES_PARTNER_NAME`.
