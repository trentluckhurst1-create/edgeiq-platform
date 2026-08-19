# BETA-004 — Scratchings Tab
Status: LOCKED
Version: 1.0

## Purpose
Answers: **Who has come out, when, why, and how did the field change?**

## Governing rules
Inherits MASTER-001. Do not reinterpret approved hierarchy, columns, alignment, colour semantics or data ownership.


## Summary
`Total Scratchings | Races Affected | New Since [time] | Fields Materially Changed | Emergencies Promoted | Latest Update`

## Grouped table
Exact columns:
`RACE | NO | SILK | HORSE | TRAINER | JOCKEY | SCRATCHED AT | REASON | SOURCE | STATUS`
Official reason only. Statuses include scratched, late scratching, emergency promoted.

## Effective barriers
Original barrier immutable. Effective barrier is builder-owned after inside scratchings and refreshes MAP/race shape. React never calculates compression.

## Empty state
`No official scratchings have been received for this meeting.`

## Acceptance
Correct joins, source/timestamp retained, promotions correct, MAP refresh automatic.
