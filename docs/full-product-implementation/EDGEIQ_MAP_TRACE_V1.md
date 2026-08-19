# EDGEiQ MAP Trace V1

## Workspace intent

MAP answers: How will this race be run?

The workspace is a governed speed-position display. It is not a replay, a barrier heat map, a coloured lane diagram, or a position simulation.

## Governed inputs

- Selected race context: `threeDayCatalog` race book and field passed into `MapWorkspace`.
- Runner identity: official race runners from the selected race context.
- Barrier and effective barrier: `edgeiq_map_terminal_feed_v1.csv` where matched, otherwise selected-race official barrier from catalog.
- Run style, early speed and projected position: `edgeiq_map_terminal_feed_v1.csv`.
- Scratchings: existing governed runner status fields from catalog/source status/market text. The service filters scratched runners before display and keeps supplied effective barriers; React does not recalculate official barriers.
- Track map asset: `trackMapAssets.ts` using the selected meeting/track name.

## Display rules implemented

- Victorian orientation is marked with `data-map-orientation="victorian-right-to-left"`.
- Barriers render on the right.
- Rows are sorted by effective barrier descending, so barrier 1 renders at the bottom where present.
- Runner lanes are straight blue horizontal lines.
- Runner labels contain saddlecloth number, governed speed value when available, and horse name.
- Saddlecloth numbers are neutral text chips, not coloured backgrounds.
- Runners without speed/run-style/projected-position evidence stay at the barrier side and draw no lane.

## Known governed-data gaps

- If `edgeiq_map_terminal_feed_v1.csv` has no early speed for a runner, the label shows `No speed`.
- If no curated track map resolves for a meeting, the workspace shows an honest unavailable track-map state.
- No official sectional times are exposed in MAP.
