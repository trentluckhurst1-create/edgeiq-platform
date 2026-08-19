# BETA-009 — MAP Workspace
Status: LOCKED
Version: 1.0

## Purpose
Answers: **How is the race expected to position from the barriers based on governed early-speed evidence?**

## Governing rules
Inherits MASTER-001. Do not reinterpret approved hierarchy, columns, alignment, colour semantics or data ownership.


## Orientation
Victorian right-to-left. Barriers right; barrier 1 bottom; highest effective barrier top. No direction arrow or barrier-group names.

## Geometry
Each line starts exactly at effective barrier and ends at projected early-speed value/position. All lines same EDGEiQ blue. No heat map, gradient or run-style colour.

## Labels
At projected value:
`[plain saddlecloth] [horse name] [speed value]`
Saddlecloth left of horse name and not inside lane. Name stays beside speed value.

## Scratchings
Builder calculates effective barrier. Original remains in data. React only renders.

## Runner table
`NO | HORSE | BARRIER | EFFECTIVE BARRIER | RUN STYLE | EARLY SPEED | PROJECTED POSITION`
No coloured runner blocks or run-style dots.

## Acceptance
Correct barrier order/compression, lines start at barrier, uniform blue, prohibited legends/heat maps absent.
