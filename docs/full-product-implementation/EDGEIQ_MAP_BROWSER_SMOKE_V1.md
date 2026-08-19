# EDGEiQ MAP Browser Smoke V1

## Route tested

- Local app: `http://127.0.0.1:5176/`
- Meeting: Flemington
- Date: Saturday 18 July 2026
- Race: R5
- Workspace: MAP

## Screenshots

- `docs/full-product-implementation/screenshots/map-final-spec-v1-flemington-r5.png`
- `docs/full-product-implementation/screenshots/map-final-spec-v1-flemington-r5-after-label-width.png`
- `docs/full-product-implementation/screenshots/map-final-spec-v1-flemington-r5-viewport.png`

## Browser smoke result

- MAP question rendered: PASS
- White theme preserved: PASS
- Victorian orientation marker rendered: PASS
- Curated Flemington track asset rendered: PASS
- Product-facing Confidence copy absent: PASS
- Heatmap copy absent: PASS
- Neutral saddlecloth number chip styling: PASS
- Runner label includes number, speed/unavailable state, and horse: PASS

## Governed data limitation

The selected current race cannot visually prove barrier 1 at bottom or straight blue lanes because the governed inputs contain no usable MAP values:

- `public/data/edgeiq_map_terminal_feed_v1.csv`: 250 rows, 0 rows with barrier, 0 rows with early speed, 0 rows with run style.
- `public/data/edgeiq_three_day_product_catalog_v1.json`: Flemington R5 runners have no official barrier, jockey, trainer, weight or market values.

The UI therefore renders the honest unavailable state:

- active runners remain visible
- position reads = 0
- awaiting evidence = 17
- no speed lane is drawn
- no stale July 10 map source was used for the July 18 current race

## Refresh observation

Browser reload from the MAP route returned to the Meetings workspace instead of preserving the selected Flemington R5 MAP state. This remains a cross-product route-persistence gap for the final audit.
