# EDGEiQ Navigation State Conformance Audit V1

Generated: 2026-07-20T15:48:34

| Check | Status | File | Description |
| --- | --- | --- | --- |
| NAVIGATION_AUDIT_MARKER | PASS | `src\edgeiq-os\race\RaceFileV3.tsx` | RaceFile has the explicit-selection navigation audit marker. |
| RESTORE_ONE_SHOT_GUARD | PASS | `src\edgeiq-os\race\RaceFileV3.tsx` | Persisted workspace restore cannot rerun after it has completed. |
| STALE_RESTORE_CANCELLED | PASS | `src\edgeiq-os\race\RaceFileV3.tsx` | Async persisted restore is ignored after explicit user selection. |
| DAY_CHANGE_CLEARS_MEETING | PASS | `src\edgeiq-os\race\RaceFileV3.tsx` | Changing day clears stale selected meeting context. |
| DAY_CHANGE_CLEARS_RACE | PASS | `src\edgeiq-os\race\RaceFileV3.tsx` | Changing day clears stale selected race context. |
| MEETING_SELECT_IS_NOT_OPEN | PASS | `src\edgeiq-os\race\components\MeetingsWorkspace.tsx` | Meetings table selection writes canonical selected meeting state. |
| RESTORE_LOADING_GUARD | PASS | `src\edgeiq-os\race\RaceFileV3.tsx` | Meeting workspace cannot mount before persisted selected meeting context is restored. |
| NO_STALE_OPEN_ON_ROW_SELECT | PASS | `src\edgeiq-os\race\components\MeetingsWorkspace.tsx` | Meetings table row selection must not call onOpenMeeting directly. |

Required browser regression sequence:

1. Open Meetings, select Flemington, open meeting, confirm header Flemington.
2. Return to Meetings, select Wangaratta, open meeting, confirm header Wangaratta.
3. Return to Meetings, select Flemington, open meeting, confirm header Flemington.
4. Refresh and confirm header remains Flemington.

Result: PASS
