# EDGEiQ Gear Changes Trace V1

Status: implemented as the GEAR CHANGES final-spec tranche.

## Canonical Inputs

- Current meeting and race context: `src/edgeiq-os/race/services/threeDayCatalog.ts`.
- Gear terminal rows: `public/data/edgeiq_gear_terminal_feed_v1.csv`, loaded by `src/edgeiq-os/race/services/gearChangesFeed.ts`.
- Runner identity, number, silk, trainer and jockey: selected `ThreeDayMeeting` runner fields.

## Display Contract

- GEAR CHANGES shows official current gear changes only.
- The workspace displays race, number, silk, horse, trainer, jockey, previous gear where supplied, today gear, official change, first-time indicator where supplied, and update time where supplied.
- No gear impact, positive/negative label, score, price, tip, or confidence is generated in React.
- When no current gear changes are matched, the workspace renders an honest compact unavailable/no-change state.

## Removed Development/Product Leakage

- Removed the GEAR CHANGES fixture query path.
- Removed development fixture rows from the service.
- Removed visible SOURCE columns, DATA FRESHNESS panels, builder/feed labels, and source confidence values from the product UI.

## Legitimate Gaps

- If the governed gear feed does not supply previous gear or update timestamp, EDGEiQ displays `Unavailable` rather than inventing values.
- If the selected meeting has no matched gear rows, EDGEiQ states that no official gear changes have been received for the meeting.
