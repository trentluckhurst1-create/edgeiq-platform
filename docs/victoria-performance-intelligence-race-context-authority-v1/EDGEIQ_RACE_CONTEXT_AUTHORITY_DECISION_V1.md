# EDGEiQ Race Context Authority Decision V1

Status: PASS_VICTORIA_PERFORMANCE_INTELLIGENCE_COMPLETE

## Decision
A canonical Race Context Authority fact has been created. It only admits race_class_code and rail_position when an exact official evidence row matches race_date, normalised track and race number. No race name or prize-money inference is used, and no rail default is applied.

## Current EPI blocker
Target races: 2
Complete official context races: 2
Partial/blocked races: 0
Primary blocker: NONE

## Source inventory counts
- FOUND: 3
- NOT_FOUND: 2
- PARTIAL: 5

## Race context status counts
- COMPLETE_OFFICIAL_RACE_CONTEXT: 2

## Governance
- race_class_code is not derived from race name or prize money.
- rail_position is not defaulted or estimated.
- missing official values remain blank with MISSING_OFFICIAL_SOURCE status.
- EPI mandatory component requirements are unchanged.

