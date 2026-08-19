# EDGEiQ MARKET Trace V1

## Workspace intent

MARKET displays governed market and EDGEiQ price context for the selected race.

It is not a betting surface. It must not expose exchange controls, betting controls, stake controls, Back/Lay columns, invented movement, or confidence language.

## Governed inputs

- Selected race context: `threeDayCatalog` race book and field passed into `MarketWorkspace`.
- Terminal market feed: `public/data/edgeiq_market_terminal_feed_v1.csv`.
- EDGEiQ: `epi` from the terminal market feed.
- MARKET: current market price from the terminal market feed.
- FAIR: `edgeiq_price` from the terminal market feed.
- EDGE: governed `edge` from the terminal market feed.
- FLUC 60s %: governed `move` from the terminal market feed.
- STATUS: governed status from the terminal market feed or `Pending Market` fallback.

## Display rules implemented

- Main columns are exactly: NO, RUNNER, EDGEIQ, MARKET, FAIR, EDGE, FLUC 60s %, STATUS.
- React formats supplied values only; it does not calculate EDGE or FLUC.
- Missing prices render as `Pending Market` or empty formatted table values.
- No betting controls or exchange UI are rendered.

## Current governed-data limitation

The current terminal feed is loaded and row-safe, but it is price-sparse for the selected current window:

- `edgeiq_market_terminal_feed_v1.csv`: 250 rows.
- Current market values: 0 rows.
- EDGEiQ fair price values: 0 rows.
- EPI values: 0 rows.
- FLUC values: 0 rows.
- EDGE values: 0 rows.

The workspace therefore shows the full runner board with `Pending Market` status and does not invent prices.
