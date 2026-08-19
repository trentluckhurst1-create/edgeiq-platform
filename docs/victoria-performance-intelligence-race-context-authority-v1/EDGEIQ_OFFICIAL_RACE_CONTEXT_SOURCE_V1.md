# EDGEiQ Official Race Context Source V1

Status: OFFICIAL_RACE_CONTEXT_SOURCE_BUILT
Target races: 2
Complete races: 2
Blocked races: 0

## Method
Public Racing.com form pages were opened in a normal browser session. The builder captured visible-page GraphQL responses for getMeeting and getNoCacheRacesForMeet. No credentials, hidden tokens or access-control bypasses are used.

## Governed fields
- rail_position comes from getMeeting.railPosition.
- race_class_code comes from getNoCacheRacesForMeet.rdcClass, with nameForm only as a direct official source fallback if rdcClass is blank.
- No race-name, prize-money or rail inference is used.
