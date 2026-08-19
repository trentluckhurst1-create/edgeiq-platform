# EDGEiQ Live Race-Entry Refresh Repair V1

Repair date: 2026-07-23

## Repair Applied

The existing Racing.com three-day race-list builder was repaired to capture `getRaceForm` payloads emitted by the live Racing.com form pages. The builder now keeps using the existing browser-based source path and enriches `form_entries_json` with full race-entry fields where Racing.com exposes them.

## Stage Row Accounting

- Calendar meetings: 4
- Racing.com race-list rows: 32
- Race-list full-entry races: 32
- Race-list entry rows: 649
- Product catalogue meetings: 4
- Product catalogue races: 32
- Product catalogue runners: 649
- Governed meeting-universe rows: 0
- Governed race-fields rows: 0

## Race Status Counts
- race_status `FinalFields`: 17
- race_status `Open`: 8
- race_status `Weights`: 7

## Meeting Status Counts
- meeting/full status `Results`: 25
- meeting/full status `Weights`: 7

## Governance Interpretation
- The live race-list/product-catalogue source is repaired and now provides current/future runner-level entries with barrier, weight, trainer, jockey where known, scratchings and source entry IDs.
- The downstream `edgeiq_vic_three_day_meeting_universe.csv` remains zero because its legacy field source list does not include the repaired product catalogue/race-list source.
- Canonical race-entry fact build should use the repaired product catalogue as authoritative input, with filters blocking resulted meetings and non-final field states where required.
- No model, pricing, probability, V6.1, V7.2G2 or UI logic changed.
