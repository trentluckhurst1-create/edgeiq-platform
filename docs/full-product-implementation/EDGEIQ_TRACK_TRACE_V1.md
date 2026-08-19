# EDGEiQ Track Trace V1

Status: implemented as the TRACK final-spec tranche.

## Canonical Inputs

- Current meeting and race context: `src/edgeiq-os/race/services/threeDayCatalog.ts`.
- Official track condition records: `public/data/edgeiq_vic_official_track_conditions_v1.json`.
- Curated track map manifest: `public/data/edgeiq_track_map_manifest_v1.csv`.
- Current true-track feed: `public/data/edgeiq_current_true_track_feed_v1.csv`.
- Historical track profile feeds: `public/data/edgeiq_track_profile_v2.csv` and `public/data/edgeiq_track_intelligence_profile_v2.csv`.
- Installed track maps are resolved by `src/edgeiq-os/race/services/trackMapAssets.ts`.

## Display Contract

- TRACK displays current track information, rail, condition, curated map, current operational profile, lane/settling-position evidence, historical profile and official/governed track notes.
- TRACK does not display source station IDs, internal registry labels, confidence, builder timestamps, source-state panels, track records, class records, official time records, margin records or venue-tourism copy.
- TRACK uses approved condition colours only for track condition values.

## Removed Development/Product Leakage

- Removed the TRACK fixture query path and missing-map/missing-history query paths from the meeting workspace.
- Removed the service fixture data builder.
- Removed the visible refresh-feed button, source-state rail and source labels from the component.

## Legitimate Gaps

- Separate Sandown Hillside and Sandown Lakeside image files are not present in `public/track-maps`; the existing curated registry contains `Sandown.png` only. EDGEiQ does not invent a replacement layout.
- Circumference/straight values are displayed only if supplied by governed sources.
