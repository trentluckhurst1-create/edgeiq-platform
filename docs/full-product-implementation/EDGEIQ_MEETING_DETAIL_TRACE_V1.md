# EDGEiQ Meeting Detail Trace V1

## Scope

Workspace: MEETING DETAIL

Purpose: operational bridge between selected meeting and race-level workspaces.

## Source Trace

| Display field | Canonical source | Service path | Component path | Availability |
| --- | --- | --- | --- | --- |
| Meeting identity | Three-day product catalog meeting | `buildMeetingDetailViewModel` | `MeetingWorkspace` hero | Available |
| Date | Three-day product catalog meeting date | `formatDateLong` | Hero and summary | Available |
| State | Meeting catalog source state | `buildMeetingSummary` | Summary strip | Available where supplied |
| Track condition | Race/meeting condition fields | `buildConditionStrip` | Condition strip | Available where supplied |
| Rail | Race/meeting rail fields | `railPosition` | Condition strip and selected-race details | Available where supplied |
| Weather | Race/meeting current weather fields | `buildConditionStrip` | Condition strip | Available where supplied |
| Race list | Meeting races in catalog | `buildRaceRows` | Race table | Available |
| Declared runners | Current catalog race runners | `buildMeetingSummary` | Summary strip and race table | Available |
| Scratchings | Current catalog runner status | `scratchedCount` | Summary strip and race table | Available when status is supplied |
| Official update | Current race/meeting timestamp fields | `buildMeetingSummary` / `buildConditionStrip` | Summary strip | Available where supplied |

## Legitimate Gaps

- Race prize money, age/sex and weight conditions remain `Not supplied` where not present in the selected race row.
- Weather remains unavailable where current meeting/race weather fields are not supplied.
- Scratchings remain zero when no runner is marked scratched in the current catalog.

## Governance Notes

- React displays the meeting-detail service view model only.
- No pricing, EPI, ERI, EPF, weather freshness or governed model logic is changed.
- Weather sub-workspace and live-weather v1.2 integration are preserved.
