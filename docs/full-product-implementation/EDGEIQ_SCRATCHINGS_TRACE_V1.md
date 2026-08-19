# EDGEiQ Scratchings Trace V1

## Scope

Workspace: SCRATCHINGS

Purpose: official current scratchings for the selected meeting.

## Source Trace

| Display field | Canonical source | Service path | Component path | Availability |
| --- | --- | --- | --- | --- |
| Scratched runner | Current meeting race runners | `normaliseStatus` / `buildRecordsForRace` | Scratchings table | Available where runner status flags are supplied |
| Runner number | Current catalog official runner number | `runnerNumber` | `NO` | Available where supplied |
| Silk | Current catalog silk URL | `silkUrl` | `SILK` | Available where supplied |
| Trainer / jockey | Current catalog official runner fields | `buildRecordsForRace` | Scratchings table | Available where supplied |
| Status | Current catalog runner status | `normaliseStatus` | `STATUS` | Available where supplied |
| Original barrier | Current catalog runner barrier | `originalBarrier` | `BAR` | Available where supplied |
| Effective barrier | Service barrier-compression helper | `calculateEffectiveBarriers` | `EFFECTIVE BAR` | Available where original barriers are resolvable |
| Field before / after | Current race runner count and scratching status | `buildRaceGroups` / `buildRecordsForRace` | `FIELD` | Available where runner rows are supplied |
| Official update | Scratch timestamp where supplied | `officialUpdatedAt` | Header | Available where official scratch time exists |

## Legitimate Gaps

- Empty state is shown when no official scratching status is present in the current meeting catalog.
- Effective barrier is unavailable when original barrier data is unavailable or internally inconsistent.

## Governance Notes

- React displays service fields only.
- Fixture/development scratchings are removed from the product path.
- No reasons, rumours, source names, builder labels, or debug freshness panels are displayed.
