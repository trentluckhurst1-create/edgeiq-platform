# EDGEiQ Meetings Trace V1

## Scope

Workspace: MEETINGS

Purpose: primary operational meeting selector across the rolling three-day window.

## Source Trace

| Display field | Canonical source | Service path | Component path | Availability |
| --- | --- | --- | --- | --- |
| Day window | `public/data/edgeiq_three_day_window_v1.json` | `loadMeetingsWorkspaceViewModel` | `MeetingsWorkspace` day buttons | TODAY / TOMORROW / DAY +2 where supplied |
| Meetings | `loadThreeDayCatalog` current product catalog | `buildDay` / `buildMeetingSummary` | Meetings table | Available from catalog |
| Race count | Meeting races in catalog | `meeting.races` | `meeting.races` | Available |
| Declared runners | Current catalog runners | `declared` | `meeting.declared` | Available |
| Scratchings | Current catalog runner status | `scratchings` | `meeting.scratchings` | Available when catalog status supplies scratched runner state |
| Track condition | Meeting/race track condition fields | `trackRating` | `meeting.track` | Available where official/current source supplies condition |
| Rail | Meeting/race rail fields | `railPosition` | `meeting.rail` | Available where supplied |
| Weather / wind / temperature | Current meeting race weather fields | `weatherLabel`, `windLabel`, `tempLabel` | selected meeting rail | Available where supplied |
| Official update | Race build timestamp or catalog generated timestamp | `officialUpdate` | `meeting.officialUpdate` | Available where timestamp exists |
| Race list | Meeting races in catalog | `buildRaceSummary` | Race strip | Available |

## Legitimate Gaps

- Scratchings are zero when no runner in the current catalog is marked scratched.
- Weather values remain unavailable where the catalog does not supply current weather fields.
- Official update falls back to the catalog generated timestamp when a race timestamp is not supplied.

## Governance Notes

- React displays service fields only.
- React does not calculate racing metrics, rankings, market fields, speed, suitability, form momentum, or freshness.
- Track-condition colours are scoped to the condition value only.
- Generic meeting notes were removed from the visible workspace.
