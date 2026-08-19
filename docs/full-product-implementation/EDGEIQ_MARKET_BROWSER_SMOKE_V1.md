# EDGEiQ MARKET Browser Smoke V1

## Route tested

- Local app: `http://127.0.0.1:5176/`
- Meeting: Flemington
- Date: Saturday 18 July 2026
- Race: R5
- Workspace: MARKET

## Screenshot

- `docs/full-product-implementation/screenshots/market-final-spec-v1-flemington-r5-viewport.png`

## Browser smoke result

- Locked table headers rendered: PASS
  - NO
  - RUNNER
  - EDGEIQ
  - MARKET
  - FAIR
  - EDGE
  - FLUC 60s %
  - STATUS
- Pending Market state rendered: PASS
- Product-facing Confidence copy absent: PASS
- Back/Lay language absent: PASS
- Betting/stake/place-bet controls absent: PASS
- White theme preserved: PASS

## Governed data limitation

The current market terminal feed is available and row-safe, but price-sparse:

- `edgeiq_market_terminal_feed_v1.csv`: 250 rows.
- Current market values: 0 rows.
- EDGEiQ fair price values: 0 rows.
- EPI values: 0 rows.
- FLUC values: 0 rows.
- EDGE values: 0 rows.

The workspace therefore shows the correct runner rows with unavailable price cells and governed `Pending Market` status.
