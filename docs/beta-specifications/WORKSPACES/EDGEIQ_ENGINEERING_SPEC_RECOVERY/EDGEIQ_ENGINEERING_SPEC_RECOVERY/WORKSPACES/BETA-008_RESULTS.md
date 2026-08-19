# BETA-008 — Results and Individual Race Results
Status: LOCKED
Version: 1.0

## Purpose
Answers: **What happened, and how did every runner perform against EDGEiQ standards?**

## Governing rules
Inherits MASTER-001. Do not reinterpret approved hierarchy, columns, alignment, colour semantics or data ownership.


## Meeting results
Exact columns:
`RACE | TIME | WINNER | JOCKEY | TRAINER | SP (TAB) | MARGIN | TIME | TRACK | STATUS | OPEN`
No decorative winner colour.

## Individual result
Header with race identity/conditions/status; full official finishing order.
Remove replay, EPI-vs-SP and race-tempo panels.
Snapshot: `Winning SP | Runners | Starters | Track Rating | Rail | Penetrometer | Official Race Time`.

## Runner Performance hero
Largest lower section:
`NO | HORSE | JOCKEY | BAR | WT | SP | FINISH | MARGIN | [distance-specific benchmark segments] | EPI | ERI`
Position-in-running and benchmark sectionals separate.

## Sectionals
Primary display in benchmark lengths. Negative green, positive red, zero neutral. Raw seconds only tooltip/drill-down.

## Lifecycle
EPI/ERI blank or Pending speed data until governed speed feed. Builder calculates and view updates automatically.
Stewards pending until report, then ingest with meeting/race/runner safeguards and source timestamp.

## Acceptance
Hero dominance; prohibited panels absent; signs/colours correct; no React conversion.
