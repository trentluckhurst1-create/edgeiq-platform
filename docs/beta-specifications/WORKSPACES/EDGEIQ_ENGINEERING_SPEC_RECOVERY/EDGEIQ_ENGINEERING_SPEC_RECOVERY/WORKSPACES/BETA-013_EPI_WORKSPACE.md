# BETA-013 — EPI Workspace
Status: LOCKED
Version: 1.0

## Purpose
Answers: **How has each horse’s EPI evolved across previous starts in the context of each result and race strength?**

## Governing rules
Inherits MASTER-001. Do not reinterpret approved hierarchy, columns, alignment, colour semantics or data ownership.


## Scope
Race-level comparison across all current runners; previous 10 official starts.

## Heat-map matrix
One row per current runner, up to 10 starts. Each tile displays historical EPI.
Tile colour must use a builder-owned comparison rule relative to the result/context of that same race, not an arbitrary promotional scale.
Missing start = blank neutral cell, never zero.

## Hover/focus card
Date, track, meeting/race, distance, class, condition, barrier, weight, jockey, trainer, finish, margin, SP, EPI, ERI, benchmark sectionals, source, version. No replay until implemented/licensed.

## Runner summary
Current EPI, race rank, field average, difference, peak last 10, average last 10 and governed trend.

## Interaction
Tile click synchronises to detailed historical row/panel. Horse opens dossier while preserving race context. Keyboard focus equals hover.

## Data contract
Historical records keyed by meeting + race + runner/run identity with all displayed fields. React never calculates heat class, averages or trend.

## Acceptance
Last 10 values, documented builder heat rule, complete hover, missing blank, no cross-race joins.
